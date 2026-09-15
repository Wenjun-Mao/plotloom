"""Immutable fragment reuse binding and child materialization persistence."""

from __future__ import annotations

from ...domain import STAGE_ORDER, Artifact, ArtifactKind, FragmentReuseBinding, StageName, WorkUnitStatus, new_id
from ..schema import ArtifactRow, FragmentReuseBindingRow, GenerationWorkUnitRow, StagePlanRow
from ...exceptions import InvalidTransitionError, NotFoundError, RepairEligibilityError
from sqlalchemy import select
from ..codec import stable_hash

from .generation_access import GenerationPersistenceAccess
from .generation_plans import ProjectGenerationPlanningPersistence
from .generation_integrity import GenerationWorkUnitIntegrity
from .generation_repair_scope import GenerationRepairScopePolicy


class ProjectGenerationReusePersistence:
    """Immutable fragment reuse binding and child materialization persistence."""

    def __init__(
        self,
        access: GenerationPersistenceAccess,
        plans: ProjectGenerationPlanningPersistence,
        integrity: GenerationWorkUnitIntegrity,
        repair_scope: GenerationRepairScopePolicy,
    ) -> None:
        self._access = access
        self._plans = plans
        self._integrity = integrity
        self._repair_scope = repair_scope

    def get_fragment_reuse_bindings(self, child_run_id: str) -> list[FragmentReuseBinding]:
        access = self._access
        with access.leases.read() as session:
            self._repair_scope.scope_row(session, access.rows.run(session, child_run_id))
            rows = session.scalars(
                select(FragmentReuseBindingRow)
                .where(FragmentReuseBindingRow.child_run_id == child_run_id)
                .order_by(FragmentReuseBindingRow.stage, FragmentReuseBindingRow.created_at, FragmentReuseBindingRow.id)
            ).all()
            return [access.codecs.reuse_binding(row) for row in rows]
    def prepare_repair_stage_reuse(
        self,
        child_run_id: str,
        stage: StageName,
    ) -> list[FragmentReuseBinding]:
        """Bind the scope's frozen parent candidates to planned child units.

        It creates no candidate artifact.  This separation lets the runner
        make every durable child-local materialization visible and idempotent.
        """
        access = self._access

        with access.leases.write() as session:
            child = access.rows.run(session, child_run_id)
            scope = self._repair_scope.validate(session, child, require_source_current=True)
            child_plan = self._plans._stage_plan_row(session, child_run_id, stage)
            if child_plan is None:
                raise InvalidTransitionError(f"cannot prepare reuse before child {stage.value} StagePlan exists")
            child_units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == child_plan.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            by_selector = {stable_hash(unit.selector): unit for unit in child_units}
            if len(by_selector) != len(child_units):
                raise InvalidTransitionError("child StagePlan contains duplicate selectors")
            frozen_sources = [item for item in scope.reuse_sources if item.stage == stage]
            frozen_selector_hashes = {stable_hash(item.source_selector) for item in frozen_sources}
            child_selector_hashes = set(by_selector)
            if STAGE_ORDER.index(stage) < STAGE_ORDER.index(scope.stage):
                # Exact repair may never send a new provider request for an
                # upstream stage.  A planner or stored-plan drift that adds
                # even one selector would otherwise turn this into a hidden
                # partial rebuild.
                if child_selector_hashes != frozen_selector_hashes:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "upstream repair StagePlan selectors must exactly equal frozen reuse selectors",
                    )
            elif STAGE_ORDER.index(stage) > STAGE_ORDER.index(scope.stage):
                if frozen_sources:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "downstream repair stages cannot carry frozen reuse selectors",
                    )
            if stage == scope.stage:
                target_child = by_selector.get(stable_hash(scope.target_selector))
                source_target = session.get(GenerationWorkUnitRow, scope.target_work_unit_id)
                if (
                    target_child is None
                    or source_target is None
                    or source_target.run_id != scope.parent_run_id
                    or source_target.selector != scope.target_selector
                    or source_target.dependency_hash != scope.target_dependency_hash
                    or source_target.unit_dependency_hash != scope.target_unit_dependency_hash
                    or source_target.input_hash != scope.target_input_hash
                ):
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "target child selector no longer matches the immutable repair scope",
                    )
                pending_selector_hashes = {
                    stable_hash(session.get(GenerationWorkUnitRow, work_unit_id).selector)
                    for work_unit_id in scope.pending_sibling_work_unit_ids
                }
                unbound_selector_hashes = child_selector_hashes - frozen_selector_hashes
                if unbound_selector_hashes != {
                    stable_hash(scope.target_selector), *pending_selector_hashes
                }:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "repair StagePlan must leave exactly the target and frozen pending selectors unresolved",
                    )
            bindings: list[FragmentReuseBinding] = []
            for frozen in frozen_sources:
                self._repair_scope.validate_frozen_source(session, scope=scope, frozen=frozen)
                child_unit = by_selector.get(stable_hash(frozen.source_selector))
                if child_unit is None:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "child StagePlan no longer contains the frozen reusable selector",
                    )
                existing = session.scalar(
                    select(FragmentReuseBindingRow).where(
                        FragmentReuseBindingRow.child_work_unit_id == child_unit.id
                    )
                )
                unsigned = {
                    "childRunId": child_run_id,
                    "childStagePlanId": child_plan.id,
                    "childStagePlanHash": child_plan.stage_plan_hash,
                    "childWorkUnitId": child_unit.id,
                    "stage": stage,
                    "kind": frozen.kind,
                    "sourceRunId": scope.parent_run_id,
                    "sourceWorkUnitId": frozen.source_work_unit_id,
                    "sourceStagePlanId": frozen.source_stage_plan_id,
                    "sourceCandidateArtifactId": frozen.source_candidate_artifact_id,
                    "sourceCandidateContentHash": frozen.source_candidate_content_hash,
                    "sourceStagePlanHash": frozen.source_stage_plan_hash,
                    "sourceSelector": frozen.source_selector,
                    "sourceDependencyHash": frozen.source_dependency_hash,
                    "sourceUnitDependencyHash": frozen.source_unit_dependency_hash,
                    "sourceInputHash": frozen.source_input_hash,
                    "sourceProducerAttemptId": frozen.source_producer_attempt_id,
                    "sourceResponseArtifactId": frozen.source_response_artifact_id,
                    "sourceValidationArtifactId": frozen.source_validation_artifact_id,
                    "childSelector": dict(child_unit.selector),
                    "childDependencyHash": child_unit.dependency_hash,
                    "childUnitDependencyHash": child_unit.unit_dependency_hash,
                    "childInputHash": child_unit.input_hash,
                    "createdAt": scope.created_at.isoformat(),
                }
                provisional_binding = FragmentReuseBinding(
                    id=new_id(),
                    **unsigned,
                    binding_hash="pending",
                )
                binding_hash = stable_hash(
                    {
                        key: value
                        for key, value in provisional_binding.model_dump(mode="json", by_alias=True).items()
                        if key not in {"id", "bindingHash"}
                    }
                )
                if existing is not None:
                    binding = access.codecs.reuse_binding(existing)
                    if binding.binding_hash != binding_hash:
                        raise RepairEligibilityError(
                            "repair.scope_hash_mismatch", "existing child reuse binding differs from frozen scope"
                        )
                    bindings.append(binding)
                    continue
                binding = provisional_binding.model_copy(update={"binding_hash": binding_hash})
                session.add(
                    FragmentReuseBindingRow(
                        id=binding.id,
                        child_run_id=binding.child_run_id,
                        child_stage_plan_id=binding.child_stage_plan_id,
                        child_work_unit_id=binding.child_work_unit_id,
                        stage=binding.stage.value,
                        kind=binding.kind.value,
                        source_run_id=binding.source_run_id,
                        source_work_unit_id=binding.source_work_unit_id,
                        source_stage_plan_id=binding.source_stage_plan_id,
                        source_candidate_artifact_id=binding.source_candidate_artifact_id,
                        binding_hash=binding.binding_hash,
                        binding=binding.model_dump(mode="json", by_alias=True),
                        created_at=binding.created_at,
                    )
                )
                bindings.append(binding)
            return bindings
    def materialize_fragment_reuse_binding(
        self,
        child_run_id: str,
        binding_id: str,
    ) -> Artifact:
        """Create one child-owned, metadata-rebound candidate from a binding."""
        access = self._access

        with access.leases.write() as session:
            child = access.rows.run(session, child_run_id)
            scope = self._repair_scope.validate(session, child, require_source_current=True)
            row = session.get(FragmentReuseBindingRow, binding_id)
            if row is None or row.child_run_id != child_run_id:
                raise NotFoundError(f"fragment reuse binding not found for child run: {binding_id}")
            binding = access.codecs.reuse_binding(row)
            frozen = next(
                (
                    item
                    for item in scope.reuse_sources
                    if item.source_candidate_artifact_id == binding.source_candidate_artifact_id
                    and item.source_work_unit_id == binding.source_work_unit_id
                ),
                None,
            )
            if frozen is None:
                raise RepairEligibilityError("repair.scope_hash_mismatch", "binding is absent from immutable repair scope")
            _, source_candidate, _, _ = self._repair_scope.validate_frozen_source(
                session, scope=scope, frozen=frozen
            )
            child_unit = session.get(GenerationWorkUnitRow, binding.child_work_unit_id)
            child_plan = session.get(StagePlanRow, binding.child_stage_plan_id)
            if (
                child_unit is None
                or child_plan is None
                or child_unit.run_id != child_run_id
                or child_unit.stage_plan_id != child_plan.id
                or child_unit.stage != binding.stage.value
                or child_plan.stage_plan_hash != binding.child_stage_plan_hash
                or child_unit.selector != binding.child_selector
                or child_unit.dependency_hash != binding.child_dependency_hash
                or child_unit.unit_dependency_hash != binding.child_unit_dependency_hash
                or child_unit.input_hash != binding.child_input_hash
            ):
                raise RepairEligibilityError("repair.scope_hash_mismatch", "child work unit no longer matches reuse binding")
            self._integrity.assert_unsealed(session, child_unit)
            existing = session.scalar(
                select(ArtifactRow).where(
                    ArtifactRow.run_id == child_run_id,
                    ArtifactRow.work_unit_id == child_unit.id,
                    ArtifactRow.kind == ArtifactKind.CANDIDATE.value,
                    ArtifactRow.source_artifact_id == source_candidate.id,
                )
            )
            source_fragment = self._integrity.fragment_from_artifact(binding.stage, source_candidate)
            rebound = source_fragment.model_copy(
                update={"stage_plan_hash": child_plan.stage_plan_hash, "work_unit_id": child_unit.id}
            )
            content = rebound.model_dump(mode="json", by_alias=False)
            content_hash = stable_hash(content)
            if existing is not None:
                if existing.content_hash != content_hash or existing.attempt_id is not None:
                    raise RepairEligibilityError("repair.scope_hash_mismatch", "existing child reuse candidate differs from binding")
                if WorkUnitStatus(child_unit.status) == WorkUnitStatus.QUEUED:
                    child_unit.status = WorkUnitStatus.SUCCEEDED.value
                return access.codecs.artifact(existing)
            if WorkUnitStatus(child_unit.status) != WorkUnitStatus.QUEUED:
                raise InvalidTransitionError(
                    f"cannot materialize reuse while child work unit is {child_unit.status}"
                )
            artifact = Artifact(
                run_id=child_run_id,
                attempt_id=None,
                work_unit_id=child_unit.id,
                source_artifact_id=source_candidate.id,
                stage=binding.stage,
                kind=ArtifactKind.CANDIDATE,
                content=content,
                content_hash=content_hash,
            )
            session.add(
                ArtifactRow(
                    id=artifact.id,
                    run_id=artifact.run_id,
                    attempt_id=None,
                    work_unit_id=artifact.work_unit_id,
                    source_artifact_id=artifact.source_artifact_id,
                    stage=artifact.stage.value if artifact.stage else None,
                    kind=artifact.kind.value,
                    media_type=artifact.media_type,
                    content=content,
                    content_hash=artifact.content_hash,
                    created_at=artifact.created_at,
                )
            )
            child_unit.status = WorkUnitStatus.SUCCEEDED.value
            return artifact
    def materialize_reused_fragment(self, child_run_id: str, binding_id: str) -> Artifact:
        """Compatibility spelling for the explicit fragment-binding command."""
        access = self._access

        return self.materialize_fragment_reuse_binding(child_run_id, binding_id)
