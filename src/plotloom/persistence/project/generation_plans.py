"""Generation persistence capability extracted from the retained repository."""

from __future__ import annotations

from ...domain import CanonicalSnapshot, GenerationWorkUnitTrace, RunStatus, StageName, StagePayload, WorkUnitStatus, new_id, utc_now
from ...generation.planning import GenerationPlan, PLANNING_POLICY_VERSION, PlanningError, StagePlan, plan_stage
from ..schema import GenerationPlanRow, GenerationWorkUnitRow, StagePlanRow, StoryGraphTopologyRow
from ...exceptions import InvalidTransitionError
from sqlalchemy import select
from ..codec import stable_hash

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository


class ProjectGenerationPlanningPersistence:
    """Own the named generation persistence operations without facade bounce-backs."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

    def get_or_create_stage_plan(
        self,
        run_id: str,
        stage: StageName,
        *,
        dependencies: dict[StageName, StagePayload] | None = None,
    ) -> StagePlan:
        """Durably freeze one exact stage plan once all inputs are available.

        Supplying dependencies is intentionally an assertion, not an override:
        the repository compares them to the frozen snapshot/sealed aggregates
        before planning.  This prevents a caller from manufacturing shard
        selectors from mutable or unrelated JSON.
        """
        repository = self._repository

        with repository._write() as session:
            run = repository._run_row(session, run_id)
            if run.legacy_unsealed:
                raise InvalidTransitionError("legacy/unsealed runs cannot create StagePlans")
            if RunStatus(run.status) not in {RunStatus.QUEUED, RunStatus.RUNNING}:
                raise InvalidTransitionError(
                    f"cannot create a StagePlan while run is {run.status}"
                )
            plan_row = session.get(GenerationPlanRow, run_id)
            if plan_row is None:
                raise InvalidTransitionError("run has no durable GenerationPlan")
            generation_plan = GenerationPlan.model_validate(plan_row.plan)
            # Startup recovery is not the only path into a durable runner:
            # a live worker can also reach this repository command directly.
            # Do not let it create a current StagePlan from an older frozen
            # GenerationPlan, because that would silently substitute current
            # selector/context/prompt semantics for historical evidence.
            if generation_plan.planning_policy_version != PLANNING_POLICY_VERSION:
                raise PlanningError(
                    "frozen GenerationPlan uses an obsolete planning policy and cannot be executed",
                    code="planning.generation_planning_policy_obsolete",
                    stage=stage,
                )
            if stage == StageName.STORY_GRAPH:
                topology_row = session.get(StoryGraphTopologyRow, run_id)
                if topology_row is None:
                    raise InvalidTransitionError(
                        "new Story Graph stage has no frozen deterministic topology"
                    )
                if (
                    generation_plan.story_graph_topology_hash != topology_row.topology_hash
                    or topology_row.generation_plan_hash != generation_plan.plan_hash
                ):
                    raise InvalidTransitionError(
                        "Story Graph topology does not match the frozen GenerationPlan"
                    )
            expected = (
                repository._repair_stage_dependencies_in_session(session, run, stage)
                if run.work_unit_repair_scope_id is not None
                else repository._expected_stage_dependencies_in_session(session, run, stage)
            )
            if dependencies is not None:
                if set(dependencies) != set(expected) or any(
                    stable_hash(dependencies[name]) != stable_hash(expected[name]) for name in expected
                ):
                    raise InvalidTransitionError(
                        "StagePlan dependencies must exactly match frozen canonical or sealed inputs"
                    )
            existing = repository._stage_plan_row(session, run_id, stage)
            if (
                stage == StageName.STORYBOARD
                and existing is not None
                and repository._storyboard_stage_plan_contract_code(existing) is not None
            ):
                # Do not recalculate an already durable plan under a new
                # default.  Exact repair uses this same command, so this also
                # prevents a child repair from inheriting an unprovable timing
                # policy after a restart or a tampering incident.
                raise PlanningError(
                    "frozen Storyboard timing provenance is missing or invalid",
                    code="planning.storyboard_timing_provenance_missing",
                    stage=stage,
                )
            snapshot = CanonicalSnapshot.model_validate(run.canonical_snapshot)
            repair_storyboard_profile = (
                repository._repair_storyboard_timing_profile_in_session(session, run)
                if (
                    run.work_unit_repair_scope_id is not None
                    and stage == StageName.STORYBOARD
                )
                else None
            )
            repair_scene_beats_profile = (
                repository._repair_scene_beats_timing_profile_in_session(session, run)
                if (
                    run.work_unit_repair_scope_id is not None
                    and stage == StageName.SCENE_BEATS
                )
                else None
            )
            proposed = plan_stage(
                generation_plan,
                stage=stage,
                dependencies=expected,
                brief=snapshot.brief,
                scene_beats_dialogue_timing_profile=repair_scene_beats_profile,
                storyboard_dialogue_timing_profile=repair_storyboard_profile,
            )
            if existing is not None:
                if existing.stage_plan_hash != proposed.stage_plan_hash:
                    raise InvalidTransitionError(
                        f"StagePlan for {stage.value} is immutable and differs from this request"
                    )
                return StagePlan.model_validate(existing.plan)

            stage_row = StagePlanRow(
                id=new_id(),
                run_id=run_id,
                stage=stage.value,
                generation_plan_hash=proposed.generation_plan_hash,
                dependency_hash=proposed.dependency_hash,
                stage_plan_hash=proposed.stage_plan_hash,
                plan=proposed.model_dump(mode="json", by_alias=False),
                created_at=utc_now(),
            )
            session.add(stage_row)
            # Work units reference the StagePlan directly by its durable ID.
            # Keep the FK order explicit for the same reason as run/plan.
            session.flush()
            for unit in proposed.work_units:
                session.add(
                    GenerationWorkUnitRow(
                        id=unit.unit_id,
                        run_id=run_id,
                        stage_plan_id=stage_row.id,
                        stage=stage.value,
                        sequence=unit.sequence,
                        selector=unit.selector.model_dump(mode="json", by_alias=False),
                        generation_plan_hash=unit.generation_plan_hash,
                        dependency_hash=unit.dependency_hash,
                        unit_dependency_hash=unit.unit_dependency_hash,
                        input_hash=unit.input_hash,
                        budget=unit.budget.model_dump(mode="json", by_alias=False),
                        estimated_input_tokens=unit.estimated_input_tokens,
                        context_window_tokens=unit.context_window_tokens,
                        status=WorkUnitStatus.QUEUED.value,
                        created_at=stage_row.created_at,
                    )
                )
            return proposed
    def get_or_create_repair_stage_plan(
        self,
        child_run_id: str,
        stage: StageName,
        *,
        dependencies: dict[StageName, StagePayload] | None = None,
    ) -> StagePlan:
        """Create a child-local plan against repository-resolved repair inputs."""
        repository = self._repository

        with repository._read() as session:
            repository._repair_scope_row_in_session(session, repository._run_row(session, child_run_id))
        return self.get_or_create_stage_plan(child_run_id, stage, dependencies=dependencies)
    def list_stage_plans(self, run_id: str) -> list[StagePlan]:
        repository = self._repository
        with repository._read() as session:
            repository._run_row(session, run_id)
            rows = session.scalars(
                select(StagePlanRow)
                .where(StagePlanRow.run_id == run_id)
                .order_by(StagePlanRow.created_at, StagePlanRow.stage)
            ).all()
            return [StagePlan.model_validate(row.plan) for row in rows]
    def list_generation_work_units(self, run_id: str) -> list[GenerationWorkUnitTrace]:
        repository = self._repository
        with repository._read() as session:
            repository._run_row(session, run_id)
            rows = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            return [repository._work_unit_trace(row) for row in rows]
