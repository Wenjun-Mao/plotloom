"""Sealed aggregate persistence with immutable evidence manifests."""

from __future__ import annotations

from typing import Any
from ..project.constants import CURRENT_STAGE_SCHEMA_VERSION
from ...domain import CanonicalSnapshot, RunStatus, StageName, SealedStageAggregateTrace, WorkUnitStatus, new_id, utc_now
from ..schema import FragmentReuseBindingRow, GenerationWorkUnitRow, SealedStageAggregateRow
from ...exceptions import InvalidTransitionError, RepairEligibilityError
from ...generation.planning import StagePlan
from ...generation.aggregation import aggregate_stage_fragments
from sqlalchemy import select
from ..codec import stable_hash

from .generation_access import GenerationPersistenceAccess
from .generation_plans import ProjectGenerationPlanningPersistence
from .generation_integrity import GenerationWorkUnitIntegrity
from .generation_lifecycle import ProjectGenerationLifecyclePersistence
from .generation_repair_scope import GenerationRepairScopePolicy


class ProjectGenerationAggregatePersistence:
    """Sealed aggregate persistence with immutable evidence manifests."""

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

    def seal_stage_aggregate(
        self,
        run_id: str,
        stage: StageName,
        *,
        candidate_artifact_ids: list[str],
    ) -> SealedStageAggregateTrace:
        """Seal exactly one ordered fragment per StagePlan unit.

        This repository command owns the aggregate boundary: callers may name
        candidate artifact IDs but cannot provide an arbitrary aggregate JSON
        document, omit evidence, or install a partial stage.
        """
        access = self._access

        with access.leases.write() as session:
            run = access.rows.run(session, run_id)
            if run.legacy_unsealed:
                raise InvalidTransitionError("legacy/unsealed runs cannot seal stage aggregates")
            if RunStatus(run.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot seal a stage aggregate while run is {run.status}"
                )
            plan_row = self._plans._stage_plan_row(session, run_id, stage)
            if plan_row is None:
                raise InvalidTransitionError(f"cannot seal {stage.value} without a StagePlan")
            stage_plan = StagePlan.model_validate(plan_row.plan)
            existing = session.scalar(
                select(SealedStageAggregateRow).where(
                    SealedStageAggregateRow.stage_plan_id == plan_row.id
                )
            )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == plan_row.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            if [unit.id for unit in units] != [unit.unit_id for unit in stage_plan.work_units]:
                raise InvalidTransitionError("persisted work units do not match the immutable StagePlan")
            if len(candidate_artifact_ids) != len(units) or len(set(candidate_artifact_ids)) != len(units):
                raise InvalidTransitionError("seal requires exactly one distinct candidate artifact per work unit")

            fragments: list[Any] = []
            manifest_units: list[dict[str, Any]] = []
            for unit, candidate_id in zip(units, candidate_artifact_ids, strict=True):
                candidate, attempt, evidence = self._integrity.required_unit_evidence(
                    session,
                    run_id=run_id,
                    stage=stage,
                    unit=unit,
                    candidate_id=candidate_id,
                )
                fragment = self._integrity.fragment_from_artifact(stage, candidate)
                if (
                    fragment.work_unit_id != unit.id
                    or fragment.stage_plan_hash != stage_plan.stage_plan_hash
                ):
                    raise InvalidTransitionError("candidate fragment is not bound to this immutable StagePlan unit")
                fragments.append(fragment)
                manifest_units.append(
                    {
                        "workUnitId": unit.id,
                        "attemptId": attempt.id,
                        "candidateArtifactId": candidate.id,
                        "candidateContentHash": candidate.content_hash,
                        "evidence": [
                            {"artifactId": row.id, "kind": row.kind, "contentHash": row.content_hash}
                            for row in evidence
                        ],
                    }
                )

            dependencies = self._plans._expected_stage_dependencies_in_session(session, run, stage)
            snapshot = CanonicalSnapshot.model_validate(run.canonical_snapshot)
            # Storyboard consumes only its own frozen timing provenance.
            # Reading it while sealing an upstream Story Bible/Graph would
            # incorrectly require a future StagePlan that cannot exist yet.
            dialogue_timing_profile = (
                ProjectGenerationLifecyclePersistence._frozen_dialogue_timing_profile_from_stage_plan(stage_plan)
                if stage == StageName.STORYBOARD
                else None
            )
            payload = aggregate_stage_fragments(
                stage_plan,
                fragments,
                brief=snapshot.brief,
                bible=dependencies.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
                graph=dependencies.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
                scene_beats=dependencies.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
                dialogue_timing_profile=dialogue_timing_profile,
            )
            payload_data = payload.model_dump(mode="json", by_alias=False)
            manifest = {
                "stagePlanHash": stage_plan.stage_plan_hash,
                "generationPlanHash": stage_plan.generation_plan_hash,
                "dependencyHash": stage_plan.dependency_hash,
                "units": manifest_units,
                "aggregatePayloadHash": stable_hash(payload_data),
            }
            manifest_hash = stable_hash(manifest)
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise InvalidTransitionError("sealed stage aggregates are immutable")
                return access.codecs.sealed_aggregate_trace(existing)
            aggregate = SealedStageAggregateRow(
                id=new_id(),
                run_id=run_id,
                stage_plan_id=plan_row.id,
                stage=stage.value,
                manifest_hash=manifest_hash,
                manifest=manifest,
                payload=payload_data,
                schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                created_at=utc_now(),
            )
            session.add(aggregate)
            for unit in units:
                unit.status = WorkUnitStatus.SUCCEEDED.value
            return access.codecs.sealed_aggregate_trace(aggregate)
    def seal_repair_stage_aggregate(
        self,
        child_run_id: str,
        stage: StageName,
        *,
        candidate_artifact_ids: list[str],
    ) -> SealedStageAggregateTrace:
        """Seal a child stage with verified child evidence and explicit reuses.

        This is intentionally separate from :meth:`seal_stage_aggregate`.
        The normal method still requires every candidate to be produced by a
        succeeded attempt in that same run and work unit.
        """
        access = self._access

        with access.leases.write() as session:
            child = access.rows.run(session, child_run_id)
            scope = self._repair_scope.validate(session, child, require_source_current=True)
            if RunStatus(child.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot seal a repair stage aggregate while run is {child.status}"
                )
            plan_row = self._plans._stage_plan_row(session, child_run_id, stage)
            if plan_row is None:
                raise InvalidTransitionError(f"cannot seal {stage.value} without a child StagePlan")
            stage_plan = StagePlan.model_validate(plan_row.plan)
            existing = session.scalar(
                select(SealedStageAggregateRow).where(
                    SealedStageAggregateRow.stage_plan_id == plan_row.id
                )
            )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == plan_row.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            if [unit.id for unit in units] != [unit.unit_id for unit in stage_plan.work_units]:
                raise InvalidTransitionError("persisted child work units do not match the immutable StagePlan")
            if len(candidate_artifact_ids) != len(units) or len(set(candidate_artifact_ids)) != len(units):
                raise InvalidTransitionError("repair seal requires one distinct candidate per child work unit")

            bindings = session.scalars(
                select(FragmentReuseBindingRow).where(
                    FragmentReuseBindingRow.child_run_id == child_run_id,
                    FragmentReuseBindingRow.child_stage_plan_id == plan_row.id,
                )
            ).all()
            binding_units = {row.child_work_unit_id for row in bindings}
            expected_reuse = {
                stable_hash(item.source_selector)
                for item in scope.reuse_sources
                if item.stage == stage
            }
            actual_reuse = {
                stable_hash(unit.selector)
                for unit in units
                if unit.id in binding_units
            }
            if actual_reuse != expected_reuse:
                raise RepairEligibilityError(
                    "repair.scope_hash_mismatch", "child StagePlan has not bound every frozen reusable source"
                )

            fragments: list[Any] = []
            manifest_units: list[dict[str, Any]] = []
            for unit, candidate_id in zip(units, candidate_artifact_ids, strict=True):
                candidate, attempt_id, evidence, binding = self._repair_scope.required_repair_evidence(
                    session,
                    child_run_id=child_run_id,
                    scope=scope,
                    stage=stage,
                    unit=unit,
                    candidate_id=candidate_id,
                )
                fragment = self._integrity.fragment_from_artifact(stage, candidate)
                if fragment.work_unit_id != unit.id or fragment.stage_plan_hash != stage_plan.stage_plan_hash:
                    raise InvalidTransitionError("repair candidate fragment is not bound to this child StagePlan unit")
                fragments.append(fragment)
                unit_manifest: dict[str, Any] = {
                    "workUnitId": unit.id,
                    "attemptId": attempt_id,
                    "candidateArtifactId": candidate.id,
                    "candidateContentHash": candidate.content_hash,
                    "evidence": [
                        {"artifactId": row.id, "kind": row.kind, "contentHash": row.content_hash}
                        for row in evidence
                    ],
                }
                if binding is not None:
                    unit_manifest["reuseBindingId"] = binding.id
                    unit_manifest["reuseBindingHash"] = binding.binding_hash
                    unit_manifest["sourceRunId"] = binding.source_run_id
                    unit_manifest["sourceCandidateArtifactId"] = binding.source_candidate_artifact_id
                manifest_units.append(unit_manifest)

            dependencies = self._repair_scope.dependencies(session, child, stage)
            snapshot = CanonicalSnapshot.model_validate(child.canonical_snapshot)
            dialogue_timing_profile = (
                ProjectGenerationLifecyclePersistence._frozen_dialogue_timing_profile_from_stage_plan(stage_plan)
                if stage == StageName.STORYBOARD
                else None
            )
            payload = aggregate_stage_fragments(
                stage_plan,
                fragments,
                brief=snapshot.brief,
                bible=dependencies.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
                graph=dependencies.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
                scene_beats=dependencies.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
                dialogue_timing_profile=dialogue_timing_profile,
            )
            payload_data = payload.model_dump(mode="json", by_alias=False)
            manifest = {
                "stagePlanHash": stage_plan.stage_plan_hash,
                "generationPlanHash": stage_plan.generation_plan_hash,
                "dependencyHash": stage_plan.dependency_hash,
                "units": manifest_units,
                "aggregatePayloadHash": stable_hash(payload_data),
            }
            manifest_hash = stable_hash(manifest)
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise InvalidTransitionError("sealed repair stage aggregates are immutable")
                return access.codecs.sealed_aggregate_trace(existing)
            aggregate = SealedStageAggregateRow(
                id=new_id(),
                run_id=child_run_id,
                stage_plan_id=plan_row.id,
                stage=stage.value,
                manifest_hash=manifest_hash,
                manifest=manifest,
                payload=payload_data,
                schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                created_at=utc_now(),
            )
            session.add(aggregate)
            for unit in units:
                unit.status = WorkUnitStatus.SUCCEEDED.value
            return access.codecs.sealed_aggregate_trace(aggregate)
