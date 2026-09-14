"""Startup reconciliation for frozen generation lifecycle evidence."""

from __future__ import annotations

from ...domain import STAGE_ORDER, AttemptStatus, MediaTaskStatus, RunStatus, StageName, StartupRecoveryPlan, WorkUnitStatus, utc_now
from ..schema import GenerationAttemptRow, GenerationRunRow, GenerationWorkUnitRow, MediaTaskRow
from sqlalchemy import select

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository


class ProjectGenerationRecoveryPersistence:
    """Startup reconciliation for frozen generation lifecycle evidence."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

    def reconcile_startup_jobs(self) -> StartupRecoveryPlan:
        """Reconcile jobs left nonterminal by the previous local process.

        Legacy runs remain conservative.  New work-unit runs are resumed only
        when no provider boundary was crossed (or every requested stage is
        already sealed and only the atomic commit remains).  A dispatch marker
        without a durable response is an ambiguous provider outcome and is
        never resubmitted.
        """
        repository = self._repository

        interrupted_run_error = (
            "Generation run was interrupted by a process restart and was not "
            "retried automatically"
        )
        legacy_media_error = (
            "production_pipeline_not_ready: legacy media tasks have no immutable "
            "ProductionSnapshot and cannot be resumed after restart"
        )
        obsolete_scene_timing_error = (
            "This run uses an obsolete Scene Beats timing contract and cannot be "
            "resumed safely. Submit a new run to regenerate Scene Beats under "
            "the current trusted timing and dialogue-capacity contract."
        )
        obsolete_join_state_error = (
            "This run uses an obsolete Scene Beats join-state contract and cannot "
            "be resumed safely. Submit a new run to regenerate Scene Beats under "
            "the current trusted join-entry value contract."
        )
        obsolete_generation_planning_error = (
            "This run uses an obsolete generation planning policy and cannot be "
            "resumed safely. Submit a new run under the current executable "
            "planning contract."
        )
        obsolete_storyboard_timing_provenance_error = (
            "This run has no valid frozen Storyboard dialogue timing profile and cannot "
            "be resumed safely. Submit a new Storyboard run under the current "
            "provenance contract."
        )
        now = utc_now()
        resubmit_run_ids: list[str] = []
        resubmit_media_task_ids: list[str] = []
        resume_media_poll_task_ids: list[str] = []
        terminated_run_ids: list[str] = []
        terminated_media_task_ids: list[str] = []

        with repository._write() as session:
            run_rows = session.scalars(
                select(GenerationRunRow)
                .where(
                    GenerationRunRow.status.in_(
                        [
                            RunStatus.QUEUED.value,
                            RunStatus.RUNNING.value,
                            RunStatus.CANCEL_REQUESTED.value,
                        ]
                    )
                )
                .order_by(GenerationRunRow.created_at)
            ).all()
            for row in run_rows:
                attempts = session.scalars(
                    select(GenerationAttemptRow).where(
                        GenerationAttemptRow.run_id == row.id
                    )
                ).all()
                units = session.scalars(
                    select(GenerationWorkUnitRow).where(
                        GenerationWorkUnitRow.run_id == row.id
                    )
                ).all()
                running_attempts = [
                    attempt
                    for attempt in attempts
                    if AttemptStatus(attempt.status) == AttemptStatus.RUNNING
                ]
                status = RunStatus(row.status)
                # Existing attempt-only execution has no work-unit lifecycle,
                # even if it was created after the migration for compatibility.
                # Preserve the old no-replay policy for that shape.
                legacy_execution = row.legacy_unsealed or any(
                    attempt.work_unit_id is None for attempt in attempts
                )
                if status == RunStatus.CANCEL_REQUESTED:
                    row.status = RunStatus.CANCELLED.value
                    row.error = None
                    row.failure_code = None
                    row.failed_stage = None
                    row.finished_at = now
                    repository._cancel_run_work_units_in_session(
                        session,
                        row.id,
                        now=now,
                        attempt_error="Generation attempt cancelled during startup recovery",
                    )
                    terminated_run_ids.append(row.id)
                    continue

                obsolete_contract_code = (
                    repository._obsolete_generation_planning_policy_recovery_code_in_session(
                        session, row
                    )
                    if not legacy_execution
                    else None
                )
                if obsolete_contract_code is not None:
                    # A plan created before its complete executable contract
                    # was frozen has different dependency, unit, prompt, or
                    # binder rules. Replanning it would rewrite immutable
                    # historical evidence; replaying it would silently execute
                    # a different request. Terminalize only nonterminal state.
                    error = (
                        obsolete_scene_timing_error
                        if obsolete_contract_code
                        == "recovery.scene_timing_contract_obsolete"
                        else (
                            obsolete_join_state_error
                            if obsolete_contract_code
                            == "recovery.join_state_value_contract_obsolete"
                            else (
                                obsolete_storyboard_timing_provenance_error
                                if obsolete_contract_code
                                == "recovery.storyboard_timing_provenance_missing"
                                else obsolete_generation_planning_error
                            )
                        )
                    )
                    row.status = RunStatus.FAILED.value
                    row.error = error
                    row.failure_code = obsolete_contract_code
                    row.failed_stage = repository._recovery_obsolete_contract_stage(
                        session, row, obsolete_contract_code
                    ).value
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    for attempt in running_attempts:
                        attempt.status = AttemptStatus.FAILED.value
                        attempt.error = error
                        attempt.outcome_code = row.failure_code
                        attempt.finished_at = now
                    for unit in units:
                        if WorkUnitStatus(unit.status) in {
                            WorkUnitStatus.QUEUED,
                            WorkUnitStatus.RUNNING,
                        }:
                            unit.status = WorkUnitStatus.FAILED.value
                    terminated_run_ids.append(row.id)
                    continue

                pristine_queue = (
                    status == RunStatus.QUEUED
                    and row.started_at is None
                    and not row.result_revision_ids
                    and not attempts
                )
                if pristine_queue and not legacy_execution:
                    row.failure_code = None
                    row.failed_stage = None
                    resubmit_run_ids.append(row.id)
                    continue

                if legacy_execution:
                    row.status = RunStatus.FAILED.value
                    row.error = interrupted_run_error
                    row.failure_code = "recovery.legacy_interrupted"
                    row.failed_stage = min(
                        (attempt.stage for attempt in attempts),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                        default=None,
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    for attempt in running_attempts:
                        attempt.status = AttemptStatus.FAILED.value
                        attempt.error = interrupted_run_error
                        attempt.outcome_code = "recovery.legacy_interrupted"
                        attempt.finished_at = now
                    terminated_run_ids.append(row.id)
                    continue

                if repository._all_requested_stage_aggregates_are_sealed_in_session(session, row):
                    # The runner will see the complete immutable seals and run
                    # only commit_sealed_run; no provider request is eligible.
                    row.status = RunStatus.QUEUED.value
                    row.started_at = None
                    row.finished_at = None
                    row.error = None
                    row.failure_code = None
                    row.failed_stage = None
                    resubmit_run_ids.append(row.id)
                    continue

                dispatched_without_response = [
                    attempt
                    for attempt in running_attempts
                    if attempt.dispatched_at is not None and attempt.response_persisted_at is None
                ]
                if dispatched_without_response:
                    for attempt in dispatched_without_response:
                        attempt.status = AttemptStatus.FAILED.value
                        attempt.error = (
                            "Provider dispatch completed before startup recovery but no durable response "
                            "was recorded; outcome is unknown and replay is forbidden"
                        )
                        attempt.outcome_unknown = True
                        attempt.outcome_code = "provider.outcome_unknown"
                        attempt.finished_at = now
                        unit = session.get(GenerationWorkUnitRow, attempt.work_unit_id)
                        if unit is not None:
                            unit.status = WorkUnitStatus.OUTCOME_UNKNOWN.value
                    row.status = RunStatus.FAILED.value
                    row.error = (
                        "Generation run has a provider dispatch without a durable response; "
                        "its outcome is unknown and automatic replay is forbidden"
                    )
                    row.failure_code = "provider.outcome_unknown"
                    row.failed_stage = min(
                        (attempt.stage for attempt in dispatched_without_response),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    terminated_run_ids.append(row.id)
                    continue

                nonrecoverable_units = [
                    unit
                    for unit in units
                    if WorkUnitStatus(unit.status)
                    in {
                        WorkUnitStatus.FAILED,
                        WorkUnitStatus.QUARANTINED,
                        WorkUnitStatus.OUTCOME_UNKNOWN,
                        WorkUnitStatus.CANCELLED,
                    }
                ]
                if nonrecoverable_units:
                    statuses = {
                        WorkUnitStatus(unit.status) for unit in nonrecoverable_units
                    }
                    terminal_unit_ids = {unit.id for unit in nonrecoverable_units}
                    failed_attempts = [
                        attempt
                        for attempt in session.scalars(
                            select(GenerationAttemptRow).where(
                                GenerationAttemptRow.run_id == row.id,
                                GenerationAttemptRow.status
                                == AttemptStatus.FAILED.value,
                                GenerationAttemptRow.outcome_code.is_not(None),
                            )
                        ).all()
                        if attempt.work_unit_id in terminal_unit_ids
                    ]
                    latest = max(
                        failed_attempts,
                        key=lambda attempt: (
                            attempt.attempt_number,
                            attempt.finished_at or attempt.started_at,
                        ),
                        default=None,
                    )
                    only_quarantined = statuses == {WorkUnitStatus.QUARANTINED}
                    row.status = (
                        RunStatus.QUARANTINED.value
                        if only_quarantined
                        else RunStatus.FAILED.value
                    )
                    row.error = (
                        "Generation run contains a durably rejected model response"
                        if only_quarantined
                        else "Generation run has terminal work-unit evidence that cannot be replayed automatically"
                    )
                    if WorkUnitStatus.OUTCOME_UNKNOWN in statuses:
                        row.failure_code = "provider.outcome_unknown"
                    elif only_quarantined:
                        row.failure_code = (
                            latest.outcome_code
                            if latest is not None
                            else "recovery.quarantined_work_unit"
                        )
                    elif WorkUnitStatus.FAILED in statuses and latest is not None:
                        row.failure_code = latest.outcome_code
                    else:
                        row.failure_code = "recovery.nonrecoverable_work_unit"
                    row.failed_stage = min(
                        (unit.stage for unit in nonrecoverable_units),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    terminated_run_ids.append(row.id)
                    continue

                # Keep safe in-flight identities intact. A pre-dispatch
                # attempt may continue to the provider boundary; an attempt
                # with a durable response may continue local parsing,
                # validation, and sealing. Neither path spends another
                # correction slot or replays a provider call.
                running_unit_ids = {
                    attempt.work_unit_id for attempt in running_attempts
                }
                orphan_running_units = [
                    unit
                    for unit in units
                    if WorkUnitStatus(unit.status) == WorkUnitStatus.RUNNING
                    and unit.id not in running_unit_ids
                ]
                if orphan_running_units:
                    row.status = RunStatus.FAILED.value
                    row.error = (
                        "Generation run has a running work unit without an active attempt; "
                        "automatic recovery cannot prove a safe continuation"
                    )
                    row.failure_code = "recovery.orphan_running_work_unit"
                    row.failed_stage = min(
                        (unit.stage for unit in orphan_running_units),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    for unit in orphan_running_units:
                        unit.status = WorkUnitStatus.FAILED.value
                    terminated_run_ids.append(row.id)
                    continue
                row.status = RunStatus.QUEUED.value
                row.started_at = None
                row.finished_at = None
                row.error = None
                row.failure_code = None
                row.failed_stage = None
                resubmit_run_ids.append(row.id)

            media_rows = session.scalars(
                select(MediaTaskRow)
                .where(
                    MediaTaskRow.status.in_(
                        [MediaTaskStatus.QUEUED.value, MediaTaskStatus.RUNNING.value]
                    )
                )
                .order_by(MediaTaskRow.created_at)
            ).all()
            for row in media_rows:
                # M1-12A introduces Approval/ProductionSnapshot as the only
                # valid media boundary.  Every existing task predates that
                # immutable input contract, including a queued task that never
                # reached a provider.  Preserve terminal history untouched,
                # but never resume or poll these nonterminal legacy rows.
                row.status = MediaTaskStatus.FAILED.value
                row.started_at = row.started_at or now
                row.finished_at = now
                row.updated_at = now
                row.output_uri = None
                row.error = legacy_media_error
                terminated_media_task_ids.append(row.id)

        return StartupRecoveryPlan(
            resubmit_run_ids=resubmit_run_ids,
            resubmit_media_task_ids=resubmit_media_task_ids,
            resume_media_poll_task_ids=resume_media_poll_task_ids,
            terminated_run_ids=terminated_run_ids,
            terminated_media_task_ids=terminated_media_task_ids,
        )
