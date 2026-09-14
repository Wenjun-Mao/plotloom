"""Read-only generation trace and progress projections."""

from __future__ import annotations

from ...domain import ArtifactKind, AttemptStatus, GenerationAttemptKind, ProjectLifecycleStatus, RunProgress, RunProgressActions, RunProgressAttempt, RunProgressStage, RunProgressUnit, RunExecutionTrace, RunStatus, StageName, WorkUnitStatus
from ..schema import ArtifactRow, GenerationAttemptRow, GenerationPlanRow, GenerationWorkUnitRow, SealedStageAggregateRow, StagePlanRow, StoryGraphTopologyRow
from ..codec import _stored_utc
from sqlalchemy import select

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository


class ProjectGenerationProgressPersistence:
    """Read-only generation trace and progress projections."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

    def get_run_execution_trace(self, run_id: str) -> RunExecutionTrace:
        """Return only durable plan/work-unit/seal evidence for a run.

        The existing ``RunTrace`` is intentionally left compact and compatible;
        callers that need shard-level diagnostics use this additive endpoint.
        """
        repository = self._repository

        with repository._read() as session:
            repository._run_row(session, run_id)
            plan = session.get(GenerationPlanRow, run_id)
            topology = session.get(StoryGraphTopologyRow, run_id)
            stage_plans = session.scalars(
                select(StagePlanRow)
                .where(StagePlanRow.run_id == run_id)
                .order_by(StagePlanRow.created_at, StagePlanRow.stage)
            ).all()
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            aggregates = session.scalars(
                select(SealedStageAggregateRow)
                .where(SealedStageAggregateRow.run_id == run_id)
                .order_by(SealedStageAggregateRow.created_at, SealedStageAggregateRow.stage)
            ).all()
            return RunExecutionTrace(
                generation_plan=repository._generation_plan_trace(plan) if plan is not None else None,
                story_graph_topology=(
                    repository._story_graph_topology_trace(topology)
                    if topology is not None
                    else None
                ),
                stage_plans=[repository._stage_plan_trace(row) for row in stage_plans],
                work_units=[repository._work_unit_trace(row) for row in units],
                sealed_aggregates=[repository._sealed_aggregate_trace(row) for row in aggregates],
            )
    def get_run_progress(self, run_id: str) -> RunProgress:
        """Return a compact, secret-free polling projection for the workbench."""
        repository = self._repository

        with repository._read() as session:
            run = repository._run_row(session, run_id)
            plans = {
                StageName(row.stage): row
                for row in session.scalars(
                    select(StagePlanRow).where(StagePlanRow.run_id == run_id)
                ).all()
            }
            sealed_plan_ids = set(
                session.scalars(
                    select(SealedStageAggregateRow.stage_plan_id).where(
                        SealedStageAggregateRow.run_id == run_id
                    )
                ).all()
            )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            attempts = session.scalars(
                select(GenerationAttemptRow)
                .where(GenerationAttemptRow.run_id == run_id)
                .order_by(GenerationAttemptRow.work_unit_id, GenerationAttemptRow.attempt_number.desc())
            ).all()
            latest_by_unit: dict[str, GenerationAttemptRow] = {}
            for attempt in attempts:
                if attempt.work_unit_id is not None and attempt.work_unit_id not in latest_by_unit:
                    latest_by_unit[attempt.work_unit_id] = attempt
            response_usage_by_attempt: dict[str, tuple[int | None, int | None]] = {}
            response_rows = session.scalars(
                select(ArtifactRow).where(
                    ArtifactRow.run_id == run_id,
                    ArtifactRow.kind == ArtifactKind.RESPONSE.value,
                    ArtifactRow.attempt_id.is_not(None),
                )
            ).all()
            for response in response_rows:
                if not isinstance(response.content, dict) or response.attempt_id is None:
                    continue
                usage = response.content.get("usage")
                if not isinstance(usage, dict):
                    continue
                input_tokens = usage.get("inputTokens")
                output_tokens = usage.get("outputTokens")
                response_usage_by_attempt[response.attempt_id] = (
                    input_tokens if isinstance(input_tokens, int) and input_tokens >= 0 else None,
                    output_tokens if isinstance(output_tokens, int) and output_tokens >= 0 else None,
                )
            eligibility_by_unit = {
                item.work_unit_id: item
                for item in (
                    [
                        repository._work_unit_repair_eligibility_in_session(session, source=run, unit=unit)
                        for unit in units
                    ]
                    if RunStatus(run.status) == RunStatus.QUARANTINED
                    else []
                )
            }
            max_attempts = repository._run_max_attempts(run)
            progress_units: list[RunProgressUnit] = []
            for unit in units:
                attempt = latest_by_unit.get(unit.id)
                latest: RunProgressAttempt | None = None
                if attempt is not None:
                    duration_ms: int | None = None
                    if attempt.finished_at is not None:
                        duration_ms = max(
                            0,
                            int((attempt.finished_at - attempt.started_at).total_seconds() * 1000),
                        )
                    input_tokens, output_tokens = response_usage_by_attempt.get(
                        attempt.id, (None, None)
                    )
                    latest = RunProgressAttempt(
                        attempt_id=attempt.id,
                        attempt_number=attempt.attempt_number,
                        attempt_kind=GenerationAttemptKind(attempt.attempt_kind),
                        source_attempt_id=attempt.source_attempt_id,
                        status=AttemptStatus(attempt.status),
                        outcome_code=attempt.outcome_code,
                        outcome_unknown=attempt.outcome_unknown,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        duration_ms=duration_ms,
                        started_at=_stored_utc(attempt.started_at),
                        finished_at=(
                            _stored_utc(attempt.finished_at) if attempt.finished_at is not None else None
                        ),
                    )
                eligibility = eligibility_by_unit.get(unit.id)
                progress_units.append(
                    RunProgressUnit(
                        work_unit_id=unit.id,
                        stage=StageName(unit.stage),
                        sequence=unit.sequence,
                        status=WorkUnitStatus(unit.status),
                        max_attempts=max_attempts,
                        latest_attempt=latest,
                        sealed=unit.stage_plan_id in sealed_plan_ids,
                        repair_eligible=eligibility.eligible if eligibility is not None else False,
                        repair_reason_code=eligibility.reason_code if eligibility is not None else None,
                    )
                )
            stage_progress: list[RunProgressStage] = []
            for stage_name in [StageName(value) for value in run.requested_stages]:
                plan = plans.get(stage_name)
                stage_units = [unit for unit in progress_units if unit.stage == stage_name]
                stage_progress.append(
                    RunProgressStage(
                        stage=stage_name,
                        stage_plan_id=plan.id if plan is not None else None,
                        stage_plan_hash=plan.stage_plan_hash if plan is not None else None,
                        sealed=plan.id in sealed_plan_ids if plan is not None else False,
                        unit_count=len(stage_units),
                        completed_unit_count=sum(
                            unit.status == WorkUnitStatus.SUCCEEDED for unit in stage_units
                        ),
                        quarantined_unit_count=sum(
                            unit.status == WorkUnitStatus.QUARANTINED for unit in stage_units
                        ),
                        repair_eligible_unit_ids=[
                            unit.work_unit_id for unit in stage_units if unit.repair_eligible
                        ],
                    )
                )
            status = RunStatus(run.status)
            has_repair = any(unit.repair_eligible for unit in progress_units)
            project_is_active = (
                ProjectLifecycleStatus(repository._project_row(session, run.project_id).lifecycle_status)
                == ProjectLifecycleStatus.ACTIVE
            )
            return RunProgress(
                run_id=run.id,
                status=status,
                failure_code=run.failure_code,
                failed_stage=StageName(run.failed_stage) if run.failed_stage else None,
                stage_progress=stage_progress,
                work_units=progress_units,
                actions=RunProgressActions(
                    can_resume=project_is_active and status in {RunStatus.QUEUED, RunStatus.RUNNING},
                    can_cancel=status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCEL_REQUESTED},
                    can_rebuild_stage=project_is_active and status == RunStatus.QUARANTINED,
                    repair_eligible=has_repair,
                ),
            )
