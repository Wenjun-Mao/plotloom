"""Immutable exact-repair scope validation and dependency resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    CanonicalSnapshot, DialogueTimingProfile, RunKind, RunStatus, STAGE_ORDER,
    StageName, StagePayload, StageStatus, WorkUnitRepairScope, WorkUnitStatus,
    upstream_stages,
)
from ...exceptions import (
    InvalidTransitionError, NotFoundError, RepairEligibilityError, StagePrerequisiteError,
)
from ...generation.planning import GenerationPlan, StagePlan
from ..codec import stable_hash
from ..schema import (
    ArtifactRow, EntityRevisionRow, FragmentReuseBindingRow, GenerationAttemptRow, GenerationPlanRow, GenerationRunRow,
    GenerationWorkUnitRow, SealedStageAggregateRow, StagePlanRow,
    StoryGraphTopologyRow, WorkUnitRepairScopeRow,
)
from .generation_access import GenerationPersistenceAccess
from .generation_integrity import GenerationWorkUnitIntegrity
from .generation_repair_eligibility import GenerationRepairEligibility

if TYPE_CHECKING:
    from .generation_plans import ProjectGenerationPlanningPersistence


class GenerationRepairScopePolicy:
    """Validate scope identity before any repair plan, reuse, seal, or commit."""

    def __init__(
        self, access: GenerationPersistenceAccess, plans: ProjectGenerationPlanningPersistence,
        integrity: GenerationWorkUnitIntegrity, eligibility: GenerationRepairEligibility,
    ) -> None:
        self._access = access
        self._plans = plans
        self._integrity = integrity
        self._eligibility = eligibility

    def scope_row(self, session: Session, child: GenerationRunRow) -> WorkUnitRepairScopeRow:
        if (
            RunKind(child.kind) != RunKind.REPAIR or not child.work_unit_repair_scope_id
            or child.work_unit_repair_scope_id != child.id
        ):
            raise InvalidTransitionError("run is not an exact work-unit repair")
        row = session.get(WorkUnitRepairScopeRow, child.id)
        if row is None:
            raise InvalidTransitionError("exact repair run has no immutable repair scope")
        if row.parent_run_id != child.parent_run_id or row.stage != child.repair_stage:
            raise InvalidTransitionError("exact repair scope does not match its child run")
        self._access.codecs.repair_scope(row)
        return row

    def validate(
        self, session: Session, child: GenerationRunRow, *, require_source_current: bool,
    ) -> WorkUnitRepairScope:
        scope = self._access.codecs.repair_scope(self.scope_row(session, child))
        source = self._access.rows.run(session, scope.parent_run_id)
        plan_row = session.get(GenerationPlanRow, source.id)
        source_stage_plan = session.get(StagePlanRow, scope.source_stage_plan_id)
        target = session.get(GenerationWorkUnitRow, scope.target_work_unit_id)
        if (
            plan_row is None or source_stage_plan is None or target is None
            or RunStatus(source.status) != RunStatus.QUARANTINED
            or plan_row.plan_hash != scope.source_generation_plan_hash
            or GenerationPlan.model_validate(plan_row.plan).provider_profile_hash != scope.source_provider_profile_hash
            or source_stage_plan.run_id != source.id or source_stage_plan.stage_plan_hash != scope.source_stage_plan_hash
            or target.run_id != source.id or target.stage_plan_id != source_stage_plan.id
            or target.stage != scope.stage.value or target.selector != scope.target_selector
            or target.dependency_hash != scope.target_dependency_hash
            or target.unit_dependency_hash != scope.target_unit_dependency_hash
            or target.input_hash != scope.target_input_hash
            or CanonicalSnapshot.model_validate(source.canonical_snapshot).snapshot_hash != scope.source_canonical_snapshot_hash
            or child.provider_snapshot != source.provider_snapshot
            or child.canonical_snapshot != source.canonical_snapshot
            or child.instructions != source.instructions
        ):
            raise RepairEligibilityError("repair.scope_hash_mismatch", "exact repair scope no longer matches frozen run contract")
        if self._integrity.is_sealed(session, target):
            raise RepairEligibilityError("repair.target_sealed", "exact repair target was sealed in its source run")
        if WorkUnitStatus(target.status) == WorkUnitStatus.OUTCOME_UNKNOWN:
            raise RepairEligibilityError("repair.target_outcome_unknown", "exact repair target has ambiguous provider outcome")
        if WorkUnitStatus(target.status) != WorkUnitStatus.QUARANTINED:
            raise RepairEligibilityError("repair.target_not_quarantined", "exact repair target is no longer quarantined")
        source_stage_units = session.scalars(select(GenerationWorkUnitRow).where(
            GenerationWorkUnitRow.stage_plan_id == source_stage_plan.id
        )).all()
        sibling_sources = [
            item for item in scope.reuse_sources
            if item.stage == scope.stage and item.kind.value == "sibling"
        ]
        reusable_sibling_ids = {item.source_work_unit_id for item in sibling_sources}
        pending_sibling_ids = set(scope.pending_sibling_work_unit_ids)
        expected_sibling_ids = {
            target.id,
            *reusable_sibling_ids,
            *pending_sibling_ids,
        }
        if (
            len(expected_sibling_ids) != 1 + len(sibling_sources) + len(scope.pending_sibling_work_unit_ids)
            or expected_sibling_ids != {unit.id for unit in source_stage_units}
            or any(
                WorkUnitStatus(unit.status) != WorkUnitStatus.SUCCEEDED
                for unit in source_stage_units
                if unit.id in reusable_sibling_ids
            )
            or any(
                WorkUnitStatus(unit.status) != WorkUnitStatus.QUEUED
                for unit in source_stage_units
                if unit.id in pending_sibling_ids
            )
        ):
            raise RepairEligibilityError(
                "repair.parent_evidence_invalid",
                "repair sibling sources no longer match the frozen reuse and pending-work contract",
            )
        topology = session.get(StoryGraphTopologyRow, source.id)
        if (topology.topology_hash if topology is not None else None) != scope.source_story_graph_topology_hash:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "exact repair topology binding changed")
        rejected = self._eligibility.latest_rejected_evidence(session, source=source, unit=target)
        if rejected is None or (rejected[0].id, rejected[1].id, rejected[2].id) != (
            scope.failed_attempt_id, scope.response_artifact_id, scope.validation_artifact_id,
        ):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "exact repair rejection evidence changed")
        if require_source_current:
            project = self._access.rows.project(session, source.project_id)
            if project.lifecycle_status != "active":
                raise RepairEligibilityError("repair.project_archived", "archived projects cannot execute exact repairs")
            if not self._eligibility.source_snapshot_is_current(session, source):
                raise RepairEligibilityError("repair.snapshot_stale", "repair source inputs changed after quarantine")
        return scope

    def dependencies(
        self, session: Session, child: GenerationRunRow, stage: StageName,
    ) -> dict[StageName, StagePayload]:
        scope = self.validate(session, child, require_source_current=True)
        source = self._access.rows.run(session, scope.parent_run_id)
        requested = {StageName(value) for value in child.requested_stages}
        if stage not in requested:
            raise InvalidTransitionError(f"{stage.value} is not requested by this repair run")
        target_index = STAGE_ORDER.index(scope.stage)
        result: dict[StageName, StagePayload] = {}
        snapshot = CanonicalSnapshot.model_validate(child.canonical_snapshot)
        for dependency in upstream_stages(stage):
            if dependency not in requested:
                head = snapshot.stage_heads[dependency]
                if head.status != StageStatus.READY or head.entity_revision_id is None:
                    raise StagePrerequisiteError(stage, dependency, head.status.value)
                revision = session.get(EntityRevisionRow, head.entity_revision_id)
                if revision is None:
                    raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
                result[dependency] = self._access.codecs.decode_current_stage_payload(dependency, revision.payload, revision.schema_version)
                continue
            child_plan = self._plans._stage_plan_row(session, child.id, dependency)
            if child_plan is not None and session.scalar(select(SealedStageAggregateRow.id).where(
                SealedStageAggregateRow.stage_plan_id == child_plan.id
            )) is not None:
                result[dependency] = self._plans._sealed_payload_in_session(session, child.id, dependency)
                continue
            if STAGE_ORDER.index(stage) > target_index:
                raise InvalidTransitionError(f"cannot plan downstream repair stage {stage.value} before child {dependency.value} is sealed")
            parent_plan = self._plans._stage_plan_row(session, source.id, dependency)
            if parent_plan is None:
                raise RepairEligibilityError("repair.parent_evidence_invalid", f"repair source has no sealed {dependency.value} StagePlan")
            aggregate = session.scalar(select(SealedStageAggregateRow).where(
                SealedStageAggregateRow.stage_plan_id == parent_plan.id
            ))
            if aggregate is None:
                raise RepairEligibilityError("repair.parent_evidence_invalid", f"repair source {dependency.value} aggregate is not sealed")
            result[dependency] = self._access.codecs.decode_current_stage_payload(dependency, aggregate.payload, aggregate.schema_version)
        return result

    def timing_profile(self, session: Session, child: GenerationRunRow, stage: StageName) -> DialogueTimingProfile:
        if stage == StageName.STORYBOARD:
            scene = self._plans._stage_plan_row(session, child.id, StageName.SCENE_BEATS)
            if scene is not None and session.scalar(select(SealedStageAggregateRow.id).where(
                SealedStageAggregateRow.stage_plan_id == scene.id
            )) is not None:
                return self._frozen_profile(scene, "repaired Scene Beats")
        if child.parent_run_id is None:
            raise RepairEligibilityError("repair.parent_stage_plan_obsolete", f"{stage.value} repair has no parent timing provenance")
        parent = self._access.rows.run(session, child.parent_run_id)
        row = self._plans._stage_plan_row(session, parent.id, stage)
        if row is None:
            raise RepairEligibilityError("repair.parent_stage_plan_obsolete", f"{stage.value} repair parent has no valid frozen timing provenance")
        if stage == StageName.STORYBOARD:
            invalid = self._plans._storyboard_stage_plan_contract_code(row)
        else:
            invalid = self._eligibility._scene_beats_contract_code(row)
        if invalid is not None:
            raise RepairEligibilityError("repair.parent_stage_plan_obsolete", f"{stage.value} repair parent has no valid frozen timing provenance")
        return self._frozen_profile(row, f"{stage.value} repair parent")

    @staticmethod
    def _frozen_profile(row: StagePlanRow, description: str) -> DialogueTimingProfile:
        try:
            plan = StagePlan.model_validate(row.plan)
        except ValueError as exc:
            raise RepairEligibilityError("repair.parent_stage_plan_obsolete", f"{description} has invalid frozen timing provenance") from exc
        profile = plan.storyboard_dialogue_timing_profile if plan.stage == StageName.STORYBOARD else plan.dialogue_timing_profile
        if profile is None:
            raise RepairEligibilityError("repair.parent_stage_plan_obsolete", f"{description} has invalid frozen timing provenance")
        return profile

    def validate_frozen_source(
        self, session: Session, *, scope: WorkUnitRepairScope, frozen: Any,
    ) -> tuple[GenerationWorkUnitRow, ArtifactRow, GenerationAttemptRow, list[ArtifactRow]]:
        source = self._access.rows.run(session, scope.parent_run_id)
        if not self._eligibility.source_snapshot_is_current(session, source):
            raise RepairEligibilityError("repair.snapshot_stale", "repair source inputs changed after quarantine")
        unit = session.get(GenerationWorkUnitRow, frozen.source_work_unit_id)
        plan = session.get(StagePlanRow, frozen.source_stage_plan_id)
        if (
            unit is None or plan is None or unit.run_id != source.id or unit.stage_plan_id != plan.id
            or unit.stage != frozen.stage.value or plan.run_id != source.id
            or plan.stage_plan_hash != frozen.source_stage_plan_hash
            or unit.generation_plan_hash != frozen.source_generation_plan_hash
            or unit.selector != frozen.source_selector or unit.dependency_hash != frozen.source_dependency_hash
            or unit.unit_dependency_hash != frozen.source_unit_dependency_hash or unit.input_hash != frozen.source_input_hash
        ):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "frozen reusable source no longer matches parent evidence")
        candidate, attempt, evidence = self._integrity.required_unit_evidence(session, run_id=source.id, stage=frozen.stage, unit=unit, candidate_id=frozen.source_candidate_artifact_id)
        by_kind = {row.kind: row for row in evidence}
        if (candidate.content_hash != frozen.source_candidate_content_hash or attempt.id != frozen.source_producer_attempt_id
            or by_kind["response"].id != frozen.source_response_artifact_id
            or by_kind["validation"].id != frozen.source_validation_artifact_id):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "frozen reusable evidence IDs or hashes changed")
        return unit, candidate, attempt, evidence

    def required_repair_evidence(
        self, session: Session, *, child_run_id: str, scope: WorkUnitRepairScope,
        stage: StageName, unit: GenerationWorkUnitRow, candidate_id: str,
    ) -> tuple[ArtifactRow, str, list[ArtifactRow], Any | None]:
        candidate = session.get(ArtifactRow, candidate_id)
        if candidate is None:
            raise NotFoundError(f"candidate artifact not found: {candidate_id}")
        if candidate.source_artifact_id is None:
            normal, attempt, evidence = self._integrity.required_unit_evidence(
                session, run_id=child_run_id, stage=stage, unit=unit, candidate_id=candidate_id
            )
            return normal, attempt.id, evidence, None
        if (
            candidate.run_id != child_run_id or candidate.stage != stage.value
            or candidate.kind != "candidate" or candidate.work_unit_id != unit.id
            or candidate.attempt_id is not None or candidate.content_hash != stable_hash(candidate.content)
        ):
            raise InvalidTransitionError("reused candidate does not belong to the declared child run/stage/work unit")
        binding_row = session.scalar(select(FragmentReuseBindingRow).where(
            FragmentReuseBindingRow.child_run_id == child_run_id,
            FragmentReuseBindingRow.child_work_unit_id == unit.id,
        ))
        if binding_row is None:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "reused candidate has no exact child binding")
        binding = self._access.codecs.reuse_binding(binding_row)
        if binding.stage != stage or binding.source_candidate_artifact_id != candidate.source_artifact_id:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "reused candidate does not match its binding")
        frozen = next((item for item in scope.reuse_sources if item.source_candidate_artifact_id == binding.source_candidate_artifact_id and item.source_work_unit_id == binding.source_work_unit_id), None)
        if frozen is None:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "binding is absent from immutable repair scope")
        _, source_candidate, source_attempt, evidence = self.validate_frozen_source(session, scope=scope, frozen=frozen)
        if source_candidate.id != candidate.source_artifact_id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "reused source candidate identity changed")
        return candidate, source_attempt.id, evidence, binding

    @staticmethod
    def hash_payload(scope_data: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in scope_data.items() if key != "scopeHash"}
