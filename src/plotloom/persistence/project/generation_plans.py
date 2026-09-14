"""Generation persistence capability extracted from the retained repository."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...domain import (
    CanonicalSnapshot, GenerationWorkUnitTrace, RunStatus, StageName,
    StagePayload, StageStatus, WorkUnitStatus, new_id, upstream_stages, utc_now,
)
from ...generation.planning import GenerationPlan, PLANNING_POLICY_VERSION, PlanningError, StagePlan, plan_stage
from ..schema import (
    EntityRevisionRow, GenerationPlanRow, GenerationRunRow,
    GenerationWorkUnitRow, SealedStageAggregateRow, StagePlanRow,
    StoryGraphTopologyRow,
)
from ...exceptions import InvalidTransitionError, NotFoundError, StagePrerequisiteError
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..codec import stable_hash

from .generation_access import GenerationPersistenceAccess
if TYPE_CHECKING:
    from .generation_repair_scope import GenerationRepairScopePolicy


class ProjectGenerationPlanningPersistence:
    """Own the named generation persistence operations without facade bounce-backs."""

    def __init__(self, access: GenerationPersistenceAccess) -> None:
        self._access = access
        self._repair_scope: GenerationRepairScopePolicy | None = None

    def bind_repair_scope(self, repair_scope: GenerationRepairScopePolicy) -> None:
        self._repair_scope = repair_scope

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
        access = self._access

        with access.leases.write() as session:
            run = access.rows.run(session, run_id)
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
                self._repair_scope_or_raise().dependencies(session, run, stage)
                if run.work_unit_repair_scope_id is not None
                else self._expected_stage_dependencies_in_session(session, run, stage)
            )
            if dependencies is not None:
                if set(dependencies) != set(expected) or any(
                    stable_hash(dependencies[name]) != stable_hash(expected[name]) for name in expected
                ):
                    raise InvalidTransitionError(
                        "StagePlan dependencies must exactly match frozen canonical or sealed inputs"
                    )
            existing = self._stage_plan_row(session, run_id, stage)
            if (
                stage == StageName.STORYBOARD
                and existing is not None
                and self._storyboard_stage_plan_contract_code(existing) is not None
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
                self._repair_scope_or_raise().timing_profile(session, run, StageName.STORYBOARD)
                if (
                    run.work_unit_repair_scope_id is not None
                    and stage == StageName.STORYBOARD
                )
                else None
            )
            repair_scene_beats_profile = (
                self._repair_scope_or_raise().timing_profile(session, run, StageName.SCENE_BEATS)
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
        access = self._access
        with access.leases.read() as session:
            self._repair_scope_or_raise().scope_row(session, access.rows.run(session, child_run_id))
        return self.get_or_create_stage_plan(child_run_id, stage, dependencies=dependencies)
    def list_stage_plans(self, run_id: str) -> list[StagePlan]:
        access = self._access
        with access.leases.read() as session:
            access.rows.run(session, run_id)
            rows = session.scalars(
                select(StagePlanRow)
                .where(StagePlanRow.run_id == run_id)
                .order_by(StagePlanRow.created_at, StagePlanRow.stage)
            ).all()
            return [StagePlan.model_validate(row.plan) for row in rows]
    def list_generation_work_units(self, run_id: str) -> list[GenerationWorkUnitTrace]:
        access = self._access
        with access.leases.read() as session:
            access.rows.run(session, run_id)
            rows = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            return [access.codecs.work_unit_trace(row) for row in rows]

    @staticmethod
    def _stage_plan_row(
        session: Session,
        run_id: str,
        stage: StageName,
    ) -> StagePlanRow | None:
        return session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run_id,
                StagePlanRow.stage == stage.value,
            )
        )

    def _sealed_payload_in_session(
        self,
        session: Session,
        run_id: str,
        stage: StageName,
    ) -> StagePayload:
        plan = self._stage_plan_row(session, run_id, stage)
        if plan is None:
            raise InvalidTransitionError(
                f"cannot use {stage.value} as a dependency before its StagePlan exists"
            )
        aggregate = session.scalar(
            select(SealedStageAggregateRow).where(
                SealedStageAggregateRow.stage_plan_id == plan.id
            )
        )
        if aggregate is None:
            raise InvalidTransitionError(
                f"cannot use {stage.value} as a dependency before its aggregate is sealed"
            )
        return self._access.codecs.decode_current_stage_payload(
            stage, aggregate.payload, aggregate.schema_version
        )

    def _expected_stage_dependencies_in_session(
        self,
        session: Session,
        run: GenerationRunRow,
        stage: StageName,
    ) -> dict[StageName, StagePayload]:
        """Resolve immutable normal-run dependencies from seals or the snapshot."""

        snapshot = CanonicalSnapshot.model_validate(run.canonical_snapshot)
        requested = {StageName(value) for value in run.requested_stages}
        dependencies: dict[StageName, StagePayload] = {}
        for dependency in upstream_stages(stage):
            if dependency in requested:
                dependencies[dependency] = self._sealed_payload_in_session(
                    session, run.id, dependency
                )
                continue
            head = snapshot.stage_heads[dependency]
            if head.status != StageStatus.READY or head.entity_revision_id is None:
                raise StagePrerequisiteError(stage, dependency, head.status.value)
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None:
                raise NotFoundError(
                    f"snapshot entity revision not found: {head.entity_revision_id}"
                )
            dependencies[dependency] = self._access.codecs.decode_current_stage_payload(
                dependency, revision.payload, revision.schema_version
            )
        return dependencies

    @staticmethod
    def _storyboard_stage_plan_contract_code(
        storyboard_plan: StagePlanRow,
    ) -> str | None:
        try:
            parsed_plan = StagePlan.model_validate(storyboard_plan.plan)
        except ValueError:
            return "recovery.storyboard_timing_provenance_missing"
        if (
            parsed_plan.stage != StageName.STORYBOARD
            or parsed_plan.storyboard_dialogue_timing_profile is None
        ):
            return "recovery.storyboard_timing_provenance_missing"
        return None

    def _repair_scope_or_raise(self) -> GenerationRepairScopePolicy:
        if self._repair_scope is None:
            raise RuntimeError("generation repair scope was not composed")
        return self._repair_scope
