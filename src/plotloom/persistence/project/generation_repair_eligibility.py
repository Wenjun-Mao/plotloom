"""Exact work-unit repair eligibility and immutable source selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    ArtifactKind, AttemptStatus, CanonicalSnapshot, FragmentReuseKind, FrozenFragmentReuseSource,
    ProjectLifecycleStatus, RunStatus, STAGE_ORDER, StageName,
    WorkUnitRepairEligibility, WorkUnitStatus,
)
from ...exceptions import RepairEligibilityError
from ...generation.planning import GenerationPlan, PLANNING_POLICY_VERSION
from ...generation.scene_timing_allocation import (
    SCENE_TIMING_ALLOCATION_VERSION, SceneTimingAllocation,
)
from ...join_state_values import JOIN_STATE_VALUE_CONTRACT_VERSION
from ...edge_entry_states import EDGE_ENTRY_STATE_CONTRACT_VERSION
from ..codec import stable_hash
from ..schema import (
    ArtifactRow, GenerationAttemptRow, GenerationPlanRow, GenerationRunRow,
    GenerationWorkUnitRow, SealedStageAggregateRow, StagePlanRow,
    WorkUnitRepairScopeRow,
)
from .generation_access import GenerationPersistenceAccess
from .generation_integrity import GenerationWorkUnitIntegrity
from .generation_plans import ProjectGenerationPlanningPersistence

if TYPE_CHECKING:
    from .generation_snapshots import ProjectGenerationSnapshots


class GenerationRepairEligibility:
    """Server-owned repair decisions; callers cannot override this evidence."""

    def __init__(
        self,
        access: GenerationPersistenceAccess,
        plans: ProjectGenerationPlanningPersistence,
        integrity: GenerationWorkUnitIntegrity,
        snapshots: ProjectGenerationSnapshots,
    ) -> None:
        self._access = access
        self._plans = plans
        self._integrity = integrity
        self._snapshots = snapshots

    def source_snapshot_is_current(self, session: Session, source: GenerationRunRow) -> bool:
        snapshot = self._snapshots.snapshot_in_session(session, source.project_id)
        return snapshot.snapshot_hash == CanonicalSnapshot.model_validate(
            source.canonical_snapshot
        ).snapshot_hash

    @staticmethod
    def latest_rejected_evidence(
        session: Session,
        *,
        source: GenerationRunRow,
        unit: GenerationWorkUnitRow,
    ) -> tuple[GenerationAttemptRow, ArtifactRow, ArtifactRow] | None:
        attempts = session.scalars(select(GenerationAttemptRow).where(
            GenerationAttemptRow.work_unit_id == unit.id
        ).order_by(GenerationAttemptRow.attempt_number.desc())).all()
        for attempt in attempts:
            if (
                attempt.run_id != source.id or attempt.stage != unit.stage
                or AttemptStatus(attempt.status) != AttemptStatus.FAILED
                or attempt.outcome_unknown or attempt.response_persisted_at is None
                or not attempt.outcome_code
            ):
                continue
            evidence = session.scalars(select(ArtifactRow).where(
                ArtifactRow.attempt_id == attempt.id
            ).order_by(ArtifactRow.created_at, ArtifactRow.id)).all()
            response = next((row for row in evidence if row.kind == ArtifactKind.RESPONSE.value), None)
            validation = next((row for row in evidence if row.kind == ArtifactKind.VALIDATION.value), None)
            if (
                response is not None and validation is not None
                and response.run_id == source.id and validation.run_id == source.id
                and response.work_unit_id == unit.id and validation.work_unit_id == unit.id
                and isinstance(validation.content, dict) and validation.content.get("accepted") is False
                and response.content_hash == stable_hash(response.content)
                and validation.content_hash == stable_hash(validation.content)
            ):
                return attempt, response, validation
        return None

    def exact_parent_contract_code(
        self, session: Session, *, source: GenerationRunRow, target: GenerationWorkUnitRow
    ) -> str | None:
        row = session.get(GenerationPlanRow, source.id)
        if row is None:
            return "repair.parent_plan_obsolete"
        try:
            plan = GenerationPlan.model_validate(row.plan)
        except ValueError:
            return "repair.parent_plan_obsolete"
        if plan.planning_policy_version != PLANNING_POLICY_VERSION:
            return "repair.parent_plan_obsolete"
        requested = [StageName(value) for value in source.requested_stages]
        target_stage = StageName(target.stage)
        for stage, code in (
            (StageName.SCENE_BEATS, "repair.parent_stage_plan_obsolete"),
            (StageName.STORYBOARD, "repair.parent_stage_plan_obsolete"),
        ):
            if stage not in requested or STAGE_ORDER.index(stage) > STAGE_ORDER.index(target_stage):
                continue
            stage_plan = self._plans._stage_plan_row(session, source.id, stage)
            if stage_plan is None:
                return code
            if stage == StageName.STORYBOARD:
                invalid = self._plans._storyboard_stage_plan_contract_code(stage_plan)
            else:
                invalid = self._scene_beats_contract_code(stage_plan)
            if invalid is not None:
                return code
        return None

    @staticmethod
    def _scene_beats_contract_code(stage_plan: object) -> str | None:
        from ...generation.dialogue_capacity import DIALOGUE_CAPACITY_POLICY_VERSION
        from ...generation.planning import StagePlan

        plan_data = getattr(stage_plan, "plan")
        allocation = plan_data.get("scene_timing_allocation")
        if not isinstance(allocation, dict):
            return "recovery.scene_timing_contract_obsolete"
        try:
            parsed_allocation = SceneTimingAllocation.model_validate(allocation)
            parsed_plan = StagePlan.model_validate(plan_data)
        except ValueError:
            return "recovery.scene_timing_contract_obsolete"
        if (
            parsed_allocation.allocation_version != SCENE_TIMING_ALLOCATION_VERSION
            or parsed_plan.dialogue_timing_profile is None
            or parsed_plan.dialogue_capacity_plan is None
            or parsed_plan.dialogue_capacity_plan.policy_version != DIALOGUE_CAPACITY_POLICY_VERSION
        ):
            return "recovery.scene_timing_contract_obsolete"
        if (
            parsed_plan.join_state_value_contract_version != JOIN_STATE_VALUE_CONTRACT_VERSION
            or parsed_plan.join_state_value_contract_hash is None
        ):
            return "recovery.join_state_value_contract_obsolete"
        if (
            parsed_plan.edge_entry_state_contract_version != EDGE_ENTRY_STATE_CONTRACT_VERSION
            or parsed_plan.edge_entry_state_contract_hash is None
        ):
            return "recovery.edge_entry_state_contract_obsolete"
        return None

    def eligibility(
        self,
        session: Session,
        *,
        source: GenerationRunRow,
        unit: GenerationWorkUnitRow,
        check_existing_scope: bool = True,
    ) -> WorkUnitRepairEligibility:
        stage = StageName(unit.stage)
        def reject(code: str) -> WorkUnitRepairEligibility:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code=code
            )
        if RunStatus(source.status) != RunStatus.QUARANTINED:
            return reject("repair.source_not_quarantined")
        if source.legacy_unsealed or session.get(GenerationPlanRow, source.id) is None:
            return reject("repair.source_legacy_unsealed")
        if unit.run_id != source.id or stage.value not in source.requested_stages:
            return reject("repair.target_not_in_source_run")
        if code := self.exact_parent_contract_code(session, source=source, target=unit):
            return reject(code)
        project = self._access.rows.project(session, source.project_id)
        if ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return reject("repair.project_archived")
        if not self.source_snapshot_is_current(session, source):
            return reject("repair.snapshot_stale")
        if self._integrity.is_sealed(session, unit):
            return reject("repair.target_sealed")
        if WorkUnitStatus(unit.status) == WorkUnitStatus.OUTCOME_UNKNOWN:
            return reject("repair.target_outcome_unknown")
        if WorkUnitStatus(unit.status) != WorkUnitStatus.QUARANTINED:
            return reject("repair.target_not_quarantined")
        if self.latest_rejected_evidence(session, source=source, unit=unit) is None:
            return reject("repair.target_not_rejected_model_output")
        if check_existing_scope and session.scalar(select(WorkUnitRepairScopeRow.child_run_id).where(
            WorkUnitRepairScopeRow.target_work_unit_id == unit.id
        )) is not None:
            return reject("repair.already_exists")
        return WorkUnitRepairEligibility(work_unit_id=unit.id, stage=stage, eligible=True)

    @staticmethod
    def raise_ineligible(eligibility: WorkUnitRepairEligibility) -> None:
        assert eligibility.reason_code is not None
        raise RepairEligibilityError(
            eligibility.reason_code,
            f"work unit {eligibility.work_unit_id} is not eligible for exact repair: {eligibility.reason_code}",
        )

    def frozen_reuse_source(
        self, session: Session, *, source: GenerationRunRow, unit: GenerationWorkUnitRow,
        kind: FragmentReuseKind, expected_candidate_id: str | None = None,
    ) -> FrozenFragmentReuseSource:
        plan = session.get(StagePlanRow, unit.stage_plan_id)
        if plan is None or plan.run_id != source.id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "source work unit has no matching StagePlan")
        candidates = session.scalars(select(ArtifactRow).where(
            ArtifactRow.run_id == source.id, ArtifactRow.work_unit_id == unit.id,
            ArtifactRow.kind == ArtifactKind.CANDIDATE.value,
        )).all()
        if expected_candidate_id is not None:
            candidates = [candidate for candidate in candidates if candidate.id == expected_candidate_id]
        if len(candidates) != 1:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "source reusable unit requires one immutable candidate")
        candidate, attempt, evidence = self._integrity.required_unit_evidence(
            session, run_id=source.id, stage=StageName(unit.stage), unit=unit, candidate_id=candidates[0].id
        )
        by_kind = {row.kind: row for row in evidence}
        return FrozenFragmentReuseSource(
            kind=kind, stage=StageName(unit.stage), source_work_unit_id=unit.id,
            source_stage_plan_id=plan.id, source_stage_plan_hash=plan.stage_plan_hash,
            source_generation_plan_hash=unit.generation_plan_hash, source_selector=dict(unit.selector),
            source_dependency_hash=unit.dependency_hash, source_unit_dependency_hash=unit.unit_dependency_hash,
            source_input_hash=unit.input_hash, source_producer_attempt_id=attempt.id,
            source_response_artifact_id=by_kind[ArtifactKind.RESPONSE.value].id,
            source_validation_artifact_id=by_kind[ArtifactKind.VALIDATION.value].id,
            source_candidate_artifact_id=candidate.id, source_candidate_content_hash=candidate.content_hash,
        )

    @staticmethod
    def _sealed_candidate_ids(
        aggregate: SealedStageAggregateRow, units: list[GenerationWorkUnitRow]
    ) -> dict[str, str]:
        if aggregate.manifest_hash != stable_hash(aggregate.manifest):
            raise RepairEligibilityError(
                "repair.parent_evidence_invalid",
                "sealed source aggregate manifest hash does not match immutable content",
            )
        manifest_units = aggregate.manifest.get("units") if isinstance(aggregate.manifest, dict) else None
        if not isinstance(manifest_units, list):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "sealed source aggregate has no unit manifest")
        candidate_ids: dict[str, str] = {}
        for item in manifest_units:
            if not isinstance(item, dict):
                raise RepairEligibilityError("repair.parent_evidence_invalid", "sealed source aggregate has malformed unit manifest")
            work_unit_id = item.get("workUnitId")
            candidate_id = item.get("candidateArtifactId")
            if not isinstance(work_unit_id, str) or not isinstance(candidate_id, str) or work_unit_id in candidate_ids:
                raise RepairEligibilityError("repair.parent_evidence_invalid", "sealed source aggregate has ambiguous candidate identity")
            candidate_ids[work_unit_id] = candidate_id
        if set(candidate_ids) != {unit.id for unit in units}:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "sealed source aggregate does not cover its work units")
        return candidate_ids

    def frozen_reuse_sources(
        self, session: Session, *, source: GenerationRunRow, target: GenerationWorkUnitRow
    ) -> list[FrozenFragmentReuseSource]:
        requested = [StageName(value) for value in source.requested_stages]
        target_index = requested.index(StageName(target.stage))
        reusable: list[FrozenFragmentReuseSource] = []
        for stage in requested[:target_index]:
            plan = self._plans._stage_plan_row(session, source.id, stage)
            if plan is None:
                raise RepairEligibilityError("repair.parent_evidence_invalid", f"source upstream stage {stage.value} is not sealed")
            aggregate = session.scalar(select(SealedStageAggregateRow).where(
                SealedStageAggregateRow.stage_plan_id == plan.id
            ))
            if aggregate is None:
                raise RepairEligibilityError("repair.parent_evidence_invalid", f"source upstream stage {stage.value} is not sealed")
            units = session.scalars(select(GenerationWorkUnitRow).where(
                GenerationWorkUnitRow.stage_plan_id == plan.id
            ).order_by(GenerationWorkUnitRow.sequence)).all()
            candidate_ids = self._sealed_candidate_ids(aggregate, units)
            reusable.extend(
                self.frozen_reuse_source(
                    session,
                    source=source,
                    unit=unit,
                    kind=FragmentReuseKind.UPSTREAM,
                    expected_candidate_id=candidate_ids[unit.id],
                )
                for unit in units
            )
        target_plan = self._plans._stage_plan_row(session, source.id, StageName(target.stage))
        if target_plan is None or target_plan.id != target.stage_plan_id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "target source StagePlan is inconsistent")
        siblings = session.scalars(select(GenerationWorkUnitRow).where(
            GenerationWorkUnitRow.stage_plan_id == target_plan.id
        ).order_by(GenerationWorkUnitRow.sequence)).all()
        for unit in siblings:
            if unit.id == target.id:
                continue
            status = WorkUnitStatus(unit.status)
            if status == WorkUnitStatus.SUCCEEDED:
                reusable.append(
                    self.frozen_reuse_source(
                        session, source=source, unit=unit, kind=FragmentReuseKind.SIBLING
                    )
                )
            elif status != WorkUnitStatus.QUEUED:
                raise RepairEligibilityError(
                    "repair.parent_evidence_invalid",
                    "source sibling is not a completed reusable fragment or undispatched pending work",
                )
        return reusable

    def pending_sibling_work_unit_ids(
        self, session: Session, *, source: GenerationRunRow, target: GenerationWorkUnitRow
    ) -> list[str]:
        plan = self._plans._stage_plan_row(session, source.id, StageName(target.stage))
        if plan is None or plan.id != target.stage_plan_id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "target source StagePlan is inconsistent")
        siblings = session.scalars(select(GenerationWorkUnitRow).where(
            GenerationWorkUnitRow.stage_plan_id == plan.id
        ).order_by(GenerationWorkUnitRow.sequence)).all()
        pending: list[str] = []
        for unit in siblings:
            if unit.id == target.id:
                continue
            status = WorkUnitStatus(unit.status)
            if status == WorkUnitStatus.QUEUED:
                pending.append(unit.id)
            elif status != WorkUnitStatus.SUCCEEDED:
                raise RepairEligibilityError(
                    "repair.parent_evidence_invalid",
                    "source sibling is not a completed reusable fragment or undispatched pending work",
                )
        return pending
