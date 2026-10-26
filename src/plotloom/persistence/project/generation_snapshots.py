"""Immutable generation snapshot and enqueue-time planning persistence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER,
    CanonicalSnapshot,
    GenerationRun,
    ProjectBrief,
    RunKind,
    RunStatus,
    StageName,
    StagePayload,
    StageStatus,
    upstream_stages,
    validate_public_provider_snapshot,
)
from ...exceptions import (
    InvalidTransitionError,
    NotFoundError,
    RevisionConflictError,
    SchemaResetRequiredError,
    StagePrerequisiteError,
)
from plotloom.generation.planning_contracts import DEFAULT_STAGE_BUDGETS, GenerationPlan, StageBudget
from plotloom.generation.enqueue_planning import create_generation_plan
from ...generation.prompts import canonical_json
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology
from plotloom.generation.story_graph_topology import plan_story_graph_topology
from ...provider_profiles import (
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    is_v2_snapshot,
    is_v3_snapshot,
)
from ..codec import stable_hash
from ..schema import (
    EntityRevisionRow,
    GenerationPlanRow,
    GenerationRunRow,
    StageHeadRow,
    StoryGraphTopologyRow,
)
from .generation_access import GenerationPersistenceAccess


class ProjectGenerationSnapshots:
    """Own frozen authoring inputs, run rows, and enqueue-time plan evidence."""

    def __init__(self, access: GenerationPersistenceAccess) -> None:
        self._access = access

    @staticmethod
    def snapshot_fingerprint(project_revision: int, brief: Any, heads: Sequence[Any]) -> dict[str, Any]:
        return {
            "projectRevision": project_revision,
            "brief": brief.model_dump(mode="json", by_alias=True),
            "stages": {
                head.stage.value: {
                    "status": head.status.value,
                    "revision": head.revision,
                    "entityRevisionId": head.entity_revision_id,
                    "inputRevisions": {key.value: value for key, value in head.input_revisions.items()},
                }
                for head in heads
            },
        }

    def snapshot_in_session(self, session: Session, project_id: str) -> CanonicalSnapshot:
        access = self._access
        project = access.codecs.project(access.rows.project(session, project_id))
        rows = session.scalars(select(StageHeadRow).where(StageHeadRow.project_id == project_id)).all()
        by_stage = {StageName(row.stage): access.codecs.stage_head(row) for row in rows}
        heads = [by_stage[stage] for stage in STAGE_ORDER]
        brief = ProjectBrief.require_confirmed(project.brief)
        return CanonicalSnapshot(
            project_id=project_id,
            project_revision=project.revision,
            brief=brief,
            stage_heads={head.stage: head for head in heads},
            snapshot_hash=stable_hash(self.snapshot_fingerprint(project.revision, brief, heads)),
        )

    def capture_snapshot(self, project_id: str) -> CanonicalSnapshot:
        with self._access.leases.read() as session:
            return self.snapshot_in_session(session, project_id)

    def snapshot_is_current(self, snapshot: CanonicalSnapshot) -> bool:
        try:
            current = self.capture_snapshot(snapshot.project_id)
        except NotFoundError:
            return False
        return current.snapshot_hash == snapshot.snapshot_hash

    @staticmethod
    def relevant_input_stages(requested: Sequence[StageName]) -> set[StageName]:
        return set(requested) | {
            upstream for requested_stage in requested for upstream in upstream_stages(requested_stage)
        }

    def assert_run_inputs_current_in_session(
        self, session: Session, row: GenerationRunRow
    ) -> CanonicalSnapshot:
        access = self._access
        if RunStatus(row.status) not in {RunStatus.QUEUED, RunStatus.RUNNING}:
            raise InvalidTransitionError(f"run input preflight is not valid from {row.status}")
        if row.result_revision_ids:
            raise InvalidTransitionError("run input preflight must occur before output installation")
        snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
        project = access.rows.project(session, row.project_id)
        if project.revision != snapshot.project_revision:
            raise RevisionConflictError("project", snapshot.project_revision, project.revision)
        requested = [StageName(value) for value in row.requested_stages]
        for stage in self.relevant_input_stages(requested):
            current = access.rows.stage(session, row.project_id, stage)
            expected = snapshot.stage_heads[stage]
            if current.revision != expected.revision or current.entity_revision_id != expected.entity_revision_id:
                raise RevisionConflictError(f"stage:{stage.value}", expected.revision, current.revision)
            if current.status != expected.status.value:
                raise InvalidTransitionError(f"stage {stage.value} status changed after the run was enqueued")
            if stage not in requested and current.status != StageStatus.READY.value:
                requested_stage = next(item for item in requested if stage in upstream_stages(item))
                raise StagePrerequisiteError(requested_stage, stage, current.status)
        return snapshot

    def assert_run_inputs_current(self, run_id: str) -> CanonicalSnapshot:
        with self._access.leases.read() as session:
            return self.assert_run_inputs_current_in_session(
                session, self._access.rows.run(session, run_id)
            )

    def get_snapshot_stage_payload(self, run_id: str, stage: StageName) -> StagePayload:
        """Read a historical stage through the exact frozen run snapshot."""
        access = self._access
        with access.leases.read() as session:
            row = access.rows.run(session, run_id)
            snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
            head = snapshot.stage_heads[stage]
            if head.entity_revision_id is None:
                raise StagePrerequisiteError(stage, stage, head.status.value)
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None or revision.project_id != row.project_id or revision.stage != stage.value:
                raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
            if revision.schema_version != head.schema_version:
                raise SchemaResetRequiredError(stage=stage, schema_version=head.schema_version)
            return access.codecs.decode_stage_payload(stage, revision.payload, head.schema_version)

    def run_plan_inputs_in_session(
        self, session: Session, snapshot: CanonicalSnapshot, requested_stages: Sequence[StageName]
    ) -> dict[StageName, StagePayload]:
        access = self._access
        first = STAGE_ORDER.index(requested_stages[0])
        inputs: dict[StageName, StagePayload] = {}
        for stage in STAGE_ORDER[:first]:
            head = snapshot.stage_heads[stage]
            if head.status != StageStatus.READY or head.entity_revision_id is None:
                continue
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None:
                raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
            inputs[stage] = access.codecs.decode_current_stage_payload(
                stage, revision.payload, revision.schema_version
            )
        return inputs

    def create_run(
        self, project_id: str, kind: RunKind, requested_stages: Sequence[StageName], *,
        instructions: str | None = None,
        provider_snapshot: dict[str, Any] | None = None, run_id: str | None = None,
    ) -> GenerationRun:
        if kind == RunKind.REPAIR:
            raise InvalidTransitionError(
                "scope-less stage repair is retired; use exact work-unit repair admission"
            )
        access = self._access
        normalized_provider_snapshot = validate_public_provider_snapshot(provider_snapshot)
        supplied_stages = list(requested_stages)
        requested_set = set(supplied_stages)
        ordered_stages = [stage for stage in STAGE_ORDER if stage in requested_set]
        if not ordered_stages:
            raise ValueError("a generation run must request at least one stage")
        first_index = STAGE_ORDER.index(ordered_stages[0])
        expected_range = list(STAGE_ORDER[first_index:first_index + len(ordered_stages)])
        if supplied_stages != ordered_stages or ordered_stages != expected_range:
            raise InvalidTransitionError("requested stages must be unique, ordered, and form one contiguous canonical range")
        with access.leases.lifecycle_write() as session:
            access.admission.assert_new_run_profile_enabled(session, normalized_provider_snapshot)
            project_row = access.rows.project(session, project_id)
            access.admission.assert_active_project(project_row)
            snapshot = self.snapshot_in_session(session, project_id)
            run = GenerationRun(
                **({"id": run_id} if run_id is not None else {}),
                project_id=project_id,
                kind=kind,
                parent_run_id=None,
                repair_stage=None,
                repair_source=None,
                provider_snapshot=normalized_provider_snapshot,
                requested_stages=ordered_stages,
                canonical_snapshot=snapshot,
                instructions=instructions,
                legacy_unsealed=False,
            )
            session.add(GenerationRunRow(id=run.id, project_id=project_id, kind=kind.value,
                parent_run_id=None, repair_stage=None,
                repair_source=None,
                work_unit_repair_scope_id=None, provider_snapshot=run.provider_snapshot,
                requested_stages=[stage.value for stage in ordered_stages], status=run.status.value,
                canonical_snapshot=snapshot.model_dump(mode="json", by_alias=False), instructions=instructions,
                legacy_unsealed=False, result_revision_ids=[], error=None, created_at=run.created_at,
                started_at=None, finished_at=None))
            session.flush()
            topology = (plan_story_graph_topology(project_id=project_id, brief=snapshot.brief,
                max_downstream_work_units=128) if StageName.STORY_GRAPH in ordered_stages else None)
            profile_hash = str(run.provider_snapshot.get("profileHash") or stable_hash(run.provider_snapshot))
            stage_budgets: dict[StageName, StageBudget] | None = None
            if is_v2_snapshot(run.provider_snapshot) or is_v3_snapshot(run.provider_snapshot):
                profile = (TextProviderProfileSnapshotV3.model_validate(run.provider_snapshot)
                    if is_v3_snapshot(run.provider_snapshot) else TextProviderProfileSnapshot.model_validate(run.provider_snapshot))
                stage_budgets = {stage: StageBudget(**{**DEFAULT_STAGE_BUDGETS[stage].model_dump(mode="python"),
                    "max_output_tokens": profile.stage_max_output_tokens.for_stage(stage.value)}) for stage in ordered_stages}
            plan = create_generation_plan(run_id=run.id, requested_stages=ordered_stages,
                provider_profile_hash=profile_hash, story_graph_topology_hash=topology.topology_hash if topology else None,
                canonical_inputs=self.run_plan_inputs_in_session(session, snapshot, ordered_stages),
                stage_budgets=stage_budgets, max_concurrency=int(run.provider_snapshot.get("textMaxConcurrency") or 1),
                canonical_snapshot_hash=snapshot.snapshot_hash,
                canonical_snapshot_bytes=len(canonical_json(snapshot.model_dump(mode="json", by_alias=True)).encode("utf-8")),
                instructions=instructions, context_window_tokens=int(run.provider_snapshot.get("textContextWindowTokens") or 32_768),
                provider_output_token_ceiling=int(run.provider_snapshot.get("textMaxOutputTokens") or 8_192))
            session.add(GenerationPlanRow(run_id=run.id, plan_hash=plan.plan_hash,
                plan=plan.model_dump(mode="json", by_alias=False), created_at=run.created_at))
            if topology is not None:
                session.add(StoryGraphTopologyRow(run_id=run.id, generation_plan_hash=plan.plan_hash,
                    topology_hash=topology.topology_hash, topology=topology.model_dump(mode="json", by_alias=True),
                    created_at=run.created_at))
            return run

    def get_run(self, run_id: str) -> GenerationRun:
        with self._access.leases.read() as session:
            return self._access.codecs.run(self._access.rows.run(session, run_id))

    def get_generation_plan(self, run_id: str) -> GenerationPlan:
        with self._access.leases.read() as session:
            self._access.rows.run(session, run_id)
            row = session.get(GenerationPlanRow, run_id)
            if row is None:
                raise NotFoundError(f"generation plan not found for run: {run_id}")
            return GenerationPlan.model_validate(row.plan)

    def get_story_graph_topology(self, run_id: str) -> StoryGraphTopology | None:
        access = self._access
        with access.leases.read() as session:
            access.rows.run(session, run_id)
            row = session.get(StoryGraphTopologyRow, run_id)
            if row is None:
                return None
            topology = StoryGraphTopology.model_validate(row.topology)
            if topology.topology_hash != row.topology_hash:
                raise InvalidTransitionError("stored Story Graph topology hash is inconsistent")
            plan = session.get(GenerationPlanRow, run_id)
            if plan is None or row.generation_plan_hash != plan.plan_hash:
                raise InvalidTransitionError("Story Graph topology is bound to a different GenerationPlan")
            return topology
