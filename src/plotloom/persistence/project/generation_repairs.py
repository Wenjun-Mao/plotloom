"""Exact repair scope, eligibility, and immutable repair-run persistence."""

from __future__ import annotations

from typing import Any
from ...domain import ArtifactKind, AttemptStatus, CanonicalSnapshot, GenerationRun, RepairSource, RunKind, RunStatus, StageName, StagePayload, WorkUnitRepairEligibility, WorkUnitRepairRunCreation, WorkUnitRepairScope
from ...generation.planning import DEFAULT_STAGE_BUDGETS, GenerationPlan, StageBudget, create_generation_plan
from ..schema import GenerationPlanRow, GenerationRunRow, GenerationWorkUnitRow, StagePlanRow, StoryGraphTopologyRow, WorkUnitRepairIdempotencyRow, WorkUnitRepairScopeRow
from ...exceptions import InvalidTransitionError, NotFoundError, RepairEligibilityError
from ...generation.story_graph_topology import StoryGraphTopology, plan_story_graph_topology
from ...provider_profiles import TextProviderProfileSnapshot, TextProviderProfileSnapshotV3, is_v2_snapshot, is_v3_snapshot
from ...generation.prompts import canonical_json
from sqlalchemy import select
from ..codec import stable_hash

from .generation_access import GenerationPersistenceAccess
from .generation_plans import ProjectGenerationPlanningPersistence
from .generation_repair_eligibility import GenerationRepairEligibility
from .generation_repair_scope import GenerationRepairScopePolicy
from .generation_snapshots import ProjectGenerationSnapshots
from .generation_evidence import ProjectGenerationEvidencePersistence


class ProjectGenerationRepairPersistence:
    """Exact repair scope, eligibility, and immutable repair-run persistence."""

    def __init__(
        self,
        access: GenerationPersistenceAccess,
        plans: ProjectGenerationPlanningPersistence,
        repair_scope: GenerationRepairScopePolicy,
        eligibility: GenerationRepairEligibility,
        snapshots: ProjectGenerationSnapshots,
        evidence: ProjectGenerationEvidencePersistence,
    ) -> None:
        self._access = access
        self._plans = plans
        self._repair_scope = repair_scope
        self._eligibility = eligibility
        self._snapshots = snapshots
        self._evidence = evidence

    def get_repair_stage_dependencies(
        self,
        child_run_id: str,
        stage: StageName,
    ) -> dict[StageName, StagePayload]:
        access = self._access
        with access.leases.read() as session:
            child = access.rows.run(session, child_run_id)
            return self._repair_scope.dependencies(session, child, stage)
    def create_repair_run(
        self,
        source_run_id: str,
        *,
        stage: StageName | None = None,
        instructions: str | None = None,
        provider_snapshot: dict[str, Any] | None = None,
    ) -> GenerationRun:
        access = self._access
        source = self._snapshots.get_run(source_run_id)
        if source.status != RunStatus.QUARANTINED:
            raise InvalidTransitionError("repairs may only be created from a quarantined run")
        source_trace = self._evidence.get_run_trace(source_run_id)
        if not source_trace.snapshot_is_current:
            raise InvalidTransitionError(
                "repair source inputs changed after quarantine; start a fresh rebuild from current canonical heads"
            )
        if stage is not None and stage not in source.requested_stages:
            raise InvalidTransitionError("repair stage must belong to the source run's requestedStages")
        failed_attempts = [
            attempt
            for attempt in source_trace.attempts
            if attempt.status == AttemptStatus.FAILED
        ]
        if not failed_attempts:
            raise InvalidTransitionError(
                "repair requires a failed model attempt with rejected response evidence; start a rebuild instead"
            )
        failed_attempt = failed_attempts[-1]
        if failed_attempt.work_unit_id is not None:
            raise InvalidTransitionError(
                "exact work-unit repair is not implemented; start a rebuild from the failed stage instead"
            )
        failed_stage = failed_attempt.stage
        attempt_artifacts = [
            artifact
            for artifact in source_trace.artifacts
            if artifact.attempt_id == failed_attempt.id and artifact.stage == failed_stage
        ]
        response = next(
            (artifact for artifact in attempt_artifacts if artifact.kind == ArtifactKind.RESPONSE),
            None,
        )
        validation = next(
            (artifact for artifact in attempt_artifacts if artifact.kind == ArtifactKind.VALIDATION),
            None,
        )
        rejected = (
            validation is not None
            and isinstance(validation.content, dict)
            and validation.content.get("accepted") is False
        )
        if response is None or not rejected:
            raise InvalidTransitionError(
                "repair requires the failed attempt's response and rejected validation artifacts"
            )
        if stage is not None and stage != failed_stage:
            raise InvalidTransitionError(
                f"repair stage must match the quarantined attempt stage {failed_stage.value}"
            )
        target = failed_stage
        requested = source.requested_stages
        reused_candidate_artifact_ids: dict[StageName, str] = {}
        repair_index = requested.index(target)
        for reused_stage in requested[:repair_index]:
            candidate = next(
                (
                    artifact
                    for artifact in reversed(source_trace.artifacts)
                    if artifact.stage == reused_stage and artifact.kind == ArtifactKind.CANDIDATE
                ),
                None,
            )
            if candidate is None:
                raise InvalidTransitionError(
                    f"repair source has no accepted candidate for {reused_stage.value}"
                )
            reused_candidate_artifact_ids[reused_stage] = candidate.id
        repair_source = RepairSource(
            failed_attempt_id=failed_attempt.id,
            response_artifact_id=response.id,
            validation_artifact_id=validation.id,
            reused_candidate_artifact_ids=reused_candidate_artifact_ids,
        )
        return self._snapshots.create_run(
            source.project_id,
            RunKind.REPAIR,
            requested,
            instructions=instructions,
            parent_run_id=source.id,
            repair_stage=target,
            repair_source=repair_source,
            provider_snapshot=provider_snapshot,
        )
    def get_repair_eligible_work_units(self, run_id: str) -> list[WorkUnitRepairEligibility]:
        """Return server-owned exact-repair decisions for one source run."""
        access = self._access

        with access.leases.read() as session:
            source = access.rows.run(session, run_id)
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            return [
                self._eligibility.eligibility(session, source=source, unit=unit)
                for unit in units
            ]
    def create_work_unit_repair_run(
        self,
        source_run_id: str,
        work_unit_id: str,
        *,
        idempotency_key: str,
        instructions: str | None = None,
    ) -> WorkUnitRepairRunCreation:
        """Create one immutable exact-repair child without changing model contract.

        The source run's frozen provider snapshot, canonical snapshot,
        requested range, and instructions are copied verbatim.  An exact
        repair therefore cannot quietly turn into a model switch or a new
        prompt request.  Callers may only supply ``None`` for instructions;
        the parameter exists so the HTTP boundary can reject accidental UI
        additions explicitly rather than silently dropping them.
        """
        access = self._access

        key = idempotency_key.strip()
        if not 1 <= len(key) <= 255:
            raise ValueError("idempotency key must contain between 1 and 255 characters")
        if instructions is not None:
            raise RepairEligibilityError(
                "repair.instructions_override_forbidden",
                "exact work-unit repairs inherit frozen instructions and cannot override them",
            )
        fingerprint = stable_hash(
            {"parentRunId": source_run_id, "targetWorkUnitId": work_unit_id}
        )
        with access.leases.lifecycle_write() as session:
            prior = session.get(WorkUnitRepairIdempotencyRow, key)
            if prior is not None:
                if prior.request_fingerprint != fingerprint:
                    raise RepairEligibilityError(
                        "repair.idempotency_conflict",
                        "Idempotency-Key has already been used for a different exact repair",
                    )
                return WorkUnitRepairRunCreation(
                    run=access.codecs.run(access.rows.run(session, prior.child_run_id)), created=False
                )

            source = access.rows.run(session, source_run_id)
            access.admission.assert_new_run_profile_enabled(session, source.provider_snapshot)
            target = session.get(GenerationWorkUnitRow, work_unit_id)
            if target is None:
                raise NotFoundError(f"generation work unit not found: {work_unit_id}")
            eligibility = self._eligibility.eligibility(
                session, source=source, unit=target
            )
            if not eligibility.eligible:
                self._eligibility.raise_ineligible(eligibility)
            rejected = self._eligibility.latest_rejected_evidence(
                session, source=source, unit=target
            )
            assert rejected is not None
            failed_attempt, response, validation = rejected
            source_plan_row = session.get(GenerationPlanRow, source.id)
            source_stage_plan = session.get(StagePlanRow, target.stage_plan_id)
            if source_plan_row is None or source_stage_plan is None:
                raise RepairEligibilityError("repair.parent_evidence_invalid", "source plan evidence is missing")
            parent_contract_code = self._eligibility.exact_parent_contract_code(
                session,
                source=source,
                target=target,
            )
            if parent_contract_code is not None:
                raise RepairEligibilityError(
                    parent_contract_code,
                    "exact repair parent no longer satisfies the current frozen planning contract",
                )
            source_plan = GenerationPlan.model_validate(source_plan_row.plan)
            project = access.rows.project(session, source.project_id)
            access.admission.assert_active_project(project)
            requested = [StageName(value) for value in source.requested_stages]
            snapshot = CanonicalSnapshot.model_validate(source.canonical_snapshot)
            child = GenerationRun(
                project_id=source.project_id,
                kind=RunKind.REPAIR,
                parent_run_id=source.id,
                repair_stage=StageName(target.stage),
                repair_source=None,
                work_unit_repair_scope_id="pending",  # replaced by child ID before persistence
                provider_snapshot=dict(source.provider_snapshot),
                requested_stages=requested,
                canonical_snapshot=snapshot,
                instructions=source.instructions,
                legacy_unsealed=False,
            )
            # The scope ID is intentionally the child run ID.  It is a stable
            # one-to-one foreign identity, not an inferred JSON convention.
            child = child.model_copy(update={"work_unit_repair_scope_id": child.id})
            session.add(
                GenerationRunRow(
                    id=child.id,
                    project_id=child.project_id,
                    kind=child.kind.value,
                    parent_run_id=child.parent_run_id,
                    repair_stage=child.repair_stage.value if child.repair_stage else None,
                    repair_source=None,
                    work_unit_repair_scope_id=child.work_unit_repair_scope_id,
                    provider_snapshot=child.provider_snapshot,
                    requested_stages=[stage.value for stage in child.requested_stages],
                    status=child.status.value,
                    canonical_snapshot=child.canonical_snapshot.model_dump(mode="json", by_alias=False),
                    instructions=child.instructions,
                    legacy_unsealed=False,
                    result_revision_ids=[],
                    error=None,
                    failure_code=None,
                    failed_stage=None,
                    created_at=child.created_at,
                    started_at=None,
                    finished_at=None,
                )
            )
            session.flush()

            # A child run intentionally has a distinct plan hash and work-unit
            # identities.  It keeps the parent profile/topology values as
            # immutable inputs while making new aggregate seals unambiguous.
            topology: StoryGraphTopology | None = None
            if StageName.STORY_GRAPH in requested:
                topology = plan_story_graph_topology(
                    project_id=child.project_id,
                    brief=snapshot.brief,
                    max_downstream_work_units=128,
                )
                source_topology = session.get(StoryGraphTopologyRow, source.id)
                if source_topology is not None and source_topology.topology_hash != topology.topology_hash:
                    raise RepairEligibilityError(
                        "repair.parent_evidence_invalid",
                        "source Story Graph topology no longer matches the deterministic planner",
                    )
            profile_hash = str(child.provider_snapshot.get("profileHash") or stable_hash(child.provider_snapshot))
            stage_budgets: dict[StageName, StageBudget] | None = None
            if is_v2_snapshot(child.provider_snapshot) or is_v3_snapshot(child.provider_snapshot):
                v2_profile = (
                    TextProviderProfileSnapshotV3.model_validate(child.provider_snapshot)
                    if is_v3_snapshot(child.provider_snapshot)
                    else TextProviderProfileSnapshot.model_validate(child.provider_snapshot)
                )
                stage_budgets = {
                    stage: StageBudget(
                        **{
                            **DEFAULT_STAGE_BUDGETS[stage].model_dump(mode="python"),
                            "max_output_tokens": v2_profile.stage_max_output_tokens.for_stage(stage.value),
                        }
                    )
                    for stage in requested
                }
            plan = create_generation_plan(
                run_id=child.id,
                requested_stages=requested,
                provider_profile_hash=profile_hash,
                story_graph_topology_hash=topology.topology_hash if topology is not None else None,
                canonical_inputs=self._snapshots.run_plan_inputs_in_session(session, snapshot, requested),
                stage_budgets=stage_budgets,
                max_concurrency=int(child.provider_snapshot.get("textMaxConcurrency") or 1),
                canonical_snapshot_hash=snapshot.snapshot_hash,
                canonical_snapshot_bytes=len(
                    canonical_json(snapshot.model_dump(mode="json", by_alias=True)).encode("utf-8")
                ),
                instructions=child.instructions,
                context_window_tokens=int(child.provider_snapshot.get("textContextWindowTokens") or 32_768),
                provider_output_token_ceiling=int(child.provider_snapshot.get("textMaxOutputTokens") or 8_192),
            )
            session.add(
                GenerationPlanRow(
                    run_id=child.id,
                    plan_hash=plan.plan_hash,
                    plan=plan.model_dump(mode="json", by_alias=False),
                    created_at=child.created_at,
                )
            )
            if topology is not None:
                session.add(
                    StoryGraphTopologyRow(
                        run_id=child.id,
                        generation_plan_hash=plan.plan_hash,
                        topology_hash=topology.topology_hash,
                        topology=topology.model_dump(mode="json", by_alias=True),
                        created_at=child.created_at,
                    )
                )

            reuse_sources = self._eligibility.frozen_reuse_sources(
                session, source=source, target=target
            )
            source_topology_row = session.get(StoryGraphTopologyRow, source.id)
            unsigned_scope: dict[str, Any] = {
                "childRunId": child.id,
                "parentRunId": source.id,
                "targetWorkUnitId": target.id,
                "stage": target.stage,
                "sourceGenerationPlanHash": source_plan_row.plan_hash,
                "sourceProviderProfileHash": source_plan.provider_profile_hash,
                "sourceStoryGraphTopologyHash": (
                    source_topology_row.topology_hash if source_topology_row is not None else None
                ),
                "sourceStagePlanId": source_stage_plan.id,
                "sourceStagePlanHash": source_stage_plan.stage_plan_hash,
                "sourceCanonicalSnapshotHash": snapshot.snapshot_hash,
                "targetSelector": dict(target.selector),
                "targetDependencyHash": target.dependency_hash,
                "targetUnitDependencyHash": target.unit_dependency_hash,
                "targetInputHash": target.input_hash,
                "failedAttemptId": failed_attempt.id,
                "responseArtifactId": response.id,
                "validationArtifactId": validation.id,
                "reuseSources": [item.model_dump(mode="json", by_alias=True) for item in reuse_sources],
                "createdAt": child.created_at.isoformat(),
            }
            unsigned_scope["scopeHash"] = "pending"
            provisional_scope = WorkUnitRepairScope(
                **unsigned_scope,
            )
            scope_hash = stable_hash(
                self._repair_scope.hash_payload(
                    provisional_scope.model_dump(mode="json", by_alias=True)
                )
            )
            scope = provisional_scope.model_copy(update={"scope_hash": scope_hash})
            session.add(
                WorkUnitRepairScopeRow(
                    child_run_id=child.id,
                    parent_run_id=source.id,
                    target_work_unit_id=target.id,
                    stage=target.stage,
                    scope_hash=scope.scope_hash,
                    scope=scope.model_dump(mode="json", by_alias=True),
                    created_at=scope.created_at,
                )
            )
            session.add(
                WorkUnitRepairIdempotencyRow(
                    idempotency_key=key,
                    request_fingerprint=fingerprint,
                    parent_run_id=source.id,
                    target_work_unit_id=target.id,
                    child_run_id=child.id,
                    created_at=child.created_at,
                )
            )
            return WorkUnitRepairRunCreation(run=child, created=True)
    def get_work_unit_repair_scope(self, child_run_id: str) -> WorkUnitRepairScope:
        access = self._access
        with access.leases.read() as session:
            row = session.get(WorkUnitRepairScopeRow, child_run_id)
            if row is None:
                raise NotFoundError(f"exact work-unit repair scope not found for run: {child_run_id}")
            return access.codecs.repair_scope(row)
