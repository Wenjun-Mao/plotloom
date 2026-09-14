"""Run lifecycle and atomic canonical output installation persistence."""

from __future__ import annotations

from typing import Any
from ...domain import TERMINAL_RUN_STATUSES, GenerationRun, RunStatus, StageHead, StageName, StagePayload, utc_now
from ..schema import GenerationRunRow, SealedStageAggregateRow, StagePlanRow
from ...exceptions import InvalidTransitionError, NotFoundError
from collections.abc import Sequence
from sqlalchemy import select
from ..codec import stable_hash

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository


class ProjectGenerationLifecyclePersistence:
    """Run lifecycle and atomic canonical output installation persistence."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

    def list_project_runs(self, project_id: str, *, limit: int = 50) -> list[GenerationRun]:
        repository = self._repository
        if not 1 <= limit <= 200:
            raise ValueError("run list limit must be between 1 and 200")
        with repository._read() as session:
            repository._project_row(session, project_id)
            rows = session.scalars(
                select(GenerationRunRow)
                .where(GenerationRunRow.project_id == project_id)
                .order_by(GenerationRunRow.created_at.desc())
                .limit(limit)
            ).all()
            return [repository._run(row) for row in rows]
    def start_run(self, run_id: str) -> GenerationRun:
        repository = self._repository
        with repository._write() as session:
            row = repository._run_row(session, run_id)
            status = RunStatus(row.status)
            if status == RunStatus.CANCEL_REQUESTED:
                row.status = RunStatus.CANCELLED.value
                row.finished_at = utc_now()
                return repository._run(row)
            if status != RunStatus.QUEUED:
                raise InvalidTransitionError(f"cannot start run from {status.value}")
            row.status = RunStatus.RUNNING.value
            row.started_at = utc_now()
            return repository._run(row)
    def install_generated_stage(
        self,
        run_id: str,
        stage: StageName,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        repository = self._repository
        _, heads = repository._commit_run_outputs(run_id, {stage: payload})
        return heads[0]
    def install_generated_stages(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> list[StageHead]:
        repository = self._repository
        _, heads = repository._commit_run_outputs(run_id, payloads)
        return heads
    def commit_run_outputs(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> GenerationRun:
        repository = self._repository
        run, _ = repository._commit_run_outputs(run_id, payloads)
        return run
    def commit_sealed_run(
        self,
        run_id: str,
        *,
        sealed_aggregate_ids: list[str],
    ) -> GenerationRun:
        """Atomically install a complete requested range from verified seals only.

        Unlike the legacy compatibility method ``commit_run_outputs``, this
        command accepts no caller-owned stage payload dictionary.  Each payload
        is read from its immutable exact-manifest aggregate inside the same
        transaction that performs canonical installation.
        """
        repository = self._repository

        with repository._lifecycle_write() as session:
            run_row = repository._run_row(session, run_id)
            if run_row.legacy_unsealed:
                raise InvalidTransitionError("legacy/unsealed runs cannot commit sealed aggregates")
            requested = [StageName(value) for value in run_row.requested_stages]
            if len(sealed_aggregate_ids) != len(requested) or len(set(sealed_aggregate_ids)) != len(requested):
                raise InvalidTransitionError(
                    "commit_sealed_run requires exactly one distinct aggregate ID per requested stage"
                )
            rows = [session.get(SealedStageAggregateRow, aggregate_id) for aggregate_id in sealed_aggregate_ids]
            if any(row is None for row in rows):
                raise NotFoundError("one or more sealed stage aggregates were not found")
            aggregates = [row for row in rows if row is not None]
            if [StageName(row.stage) for row in aggregates] != requested:
                raise InvalidTransitionError(
                    "sealed aggregates must be supplied in the run's exact requested stage order"
                )
            if any(row.run_id != run_id for row in aggregates):
                raise InvalidTransitionError("sealed aggregates must belong to the declared run")
            for aggregate in aggregates:
                if aggregate.manifest_hash != stable_hash(aggregate.manifest):
                    raise InvalidTransitionError("sealed aggregate manifest hash does not match immutable content")
                if aggregate.manifest.get("aggregatePayloadHash") != stable_hash(aggregate.payload):
                    raise InvalidTransitionError("sealed aggregate payload hash does not match immutable content")
                plan = session.get(StagePlanRow, aggregate.stage_plan_id)
                if (
                    plan is None
                    or plan.run_id != run_id
                    or plan.stage != aggregate.stage
                    or aggregate.manifest.get("stagePlanHash") != plan.stage_plan_hash
                ):
                    raise InvalidTransitionError("sealed aggregate is not bound to the declared immutable StagePlan")
            dialogue_timing_profile = repository._frozen_dialogue_timing_profile_for_sealed_commit_in_session(
                session,
                run_row,
            )
            payloads = {
                StageName(aggregate.stage): repository._decode_current_stage_payload(
                    StageName(aggregate.stage), aggregate.payload, aggregate.schema_version
                )
                for aggregate in aggregates
            }
            run, _ = repository._commit_parsed_run_outputs_in_session(
                session,
                run_row,
                payloads,
                dialogue_timing_profile=dialogue_timing_profile,
            )
            return run
    def finish_run(
        self,
        run_id: str,
        *,
        result_revision_ids: Sequence[str] | None = None,
        error: str | None = None,
        quarantine_reason: str | None = None,
        failure_code: str | None = None,
        failed_stage: StageName | None = None,
    ) -> GenerationRun:
        repository = self._repository
        with repository._write() as session:
            row = repository._run_row(session, run_id)
            if RunStatus(row.status) in TERMINAL_RUN_STATUSES:
                return repository._run(row)
            if result_revision_ids is not None:
                row.result_revision_ids = list(result_revision_ids)
            status = RunStatus(row.status)
            if status == RunStatus.CANCEL_REQUESTED:
                row.status = RunStatus.CANCELLED.value
                repository._cancel_run_work_units_in_session(
                    session,
                    row.id,
                    now=utc_now(),
                    attempt_error="Generation attempt cancelled before run completion",
                )
            elif status != RunStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish run from {status.value}")
            elif error is not None:
                row.status = RunStatus.FAILED.value
                row.error = error
                row.failure_code = failure_code
                row.failed_stage = failed_stage.value if failed_stage else None
            elif quarantine_reason is not None:
                row.status = RunStatus.QUARANTINED.value
                row.error = quarantine_reason
                row.failure_code = failure_code
                row.failed_stage = failed_stage.value if failed_stage else None
            else:
                row.status = (
                    RunStatus.SUCCEEDED.value
                    if repository._run_outputs_are_current(session, row)
                    else RunStatus.QUARANTINED.value
                )
                if row.status == RunStatus.QUARANTINED.value:
                    row.error = "canonical inputs changed or requested outputs were not installed"
                    row.failure_code = "commit.snapshot_changed"
                else:
                    row.error = None
                    row.failure_code = None
                    row.failed_stage = None
            row.finished_at = utc_now()
            return repository._run(row)
    def cancel_run(self, run_id: str) -> GenerationRun:
        repository = self._repository
        with repository._write() as session:
            row = repository._run_row(session, run_id)
            status = RunStatus(row.status)
            if status == RunStatus.QUEUED:
                row.status = RunStatus.CANCELLED.value
                now = utc_now()
                row.finished_at = now
                repository._cancel_run_work_units_in_session(
                    session,
                    row.id,
                    now=now,
                    attempt_error="Generation attempt cancelled before dispatch",
                )
            elif status == RunStatus.RUNNING:
                if row.result_revision_ids and repository._run_outputs_are_current(session, row):
                    # Canonical installation is the commit point. A cancellation that
                    # arrives after it must not label installed output as cancelled.
                    row.status = RunStatus.SUCCEEDED.value
                    row.finished_at = utc_now()
                else:
                    row.status = RunStatus.CANCEL_REQUESTED.value
            elif status == RunStatus.CANCEL_REQUESTED:
                pass
            elif status in TERMINAL_RUN_STATUSES:
                return repository._run(row)
            return repository._run(row)
