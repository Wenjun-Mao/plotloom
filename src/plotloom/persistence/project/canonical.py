from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...canonical_schema import StoryGraphV2
from ...domain import (
    STAGE_ORDER, AuthoringDraft, AuthoringDraftScope, DialogueTimingProfile,
    EntityRevision, GateEvaluation, GateEvidence, GateResult, InitialStage,
    LatestRunSummary, Project, ProjectBrief, ProjectCreation, ProjectDuplicateResult,
    ProjectLifecycleStatus, ProjectSummary, StageEnvelope, StageHead, StageName,
    StagePayload, StageStatus, downstream_stages, new_id, stage_payload_model,
    utc_now, upstream_stages, validate_initial_stage_prefix,
)
from ...exceptions import (
    IdempotencyConflictError, InvalidTransitionError, NotFoundError, ProjectBusyError,
    ProjectManagedAssetsPresentError, RevisionConflictError, SchemaResetRequiredError,
    StagePrerequisiteError,
)
from ...validation import STORYBOARD_GATE_SET_VERSION, validate_stage_payload
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ApprovalDecisionRow, AuthoringDraftRow, EntityRevisionRow, GateResultRow,
    GenerationRunRow, GenerationWorkUnitRow, ManagedAssetRow, MediaTaskRow,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectRow,
    StageHeadRow,
)
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from .access import ProjectPersistenceAccess

class ProjectCanonicalPersistence:
    """Typed project persistence collaborator; the facade owns compatibility only."""

    def __init__(self, access: ProjectPersistenceAccess, gates: Any) -> None:
        self._access = access
        self._gates = gates

    def _load_stage_payload(self, session: Session, project_id: str, stage: StageName) -> StagePayload:
        head = self._access.rows.stage(session, project_id, stage)
        if head.entity_revision_id is None:
            raise StagePrerequisiteError(stage, stage, head.status)
        revision = session.get(EntityRevisionRow, head.entity_revision_id)
        if revision is None:
            raise NotFoundError(f"entity revision not found: {head.entity_revision_id}")
        if head.schema_version != revision.schema_version:
            raise SchemaResetRequiredError(stage=stage, schema_version=head.schema_version)
        return self._access.codecs.decode_current_stage_payload(
            stage, revision.payload, revision.schema_version
        )

    def get_stage_payload(self, project_id: str, stage: StageName) -> StagePayload:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            return self._load_stage_payload(session, project_id, stage)

    def _mark_downstream_stale(self, session: Session, project_id: str, stage: StageName, now: datetime) -> None:
        for downstream in downstream_stages(stage):
            row = self._access.rows.stage(session, project_id, downstream)
            if row.status != StageStatus.MISSING.value:
                row.status = StageStatus.STALE.value
                row.stale_reasons = [f"upstream stage {stage.value} revision changed"]
                row.updated_at = now

    def _install_stage_in_session(
        self,
        session: Session,
        project_row: ProjectRow,
        stage: StageName,
        payload: StagePayload,
        *,
        expected_revision: int,
        now: datetime,
        allow_noop: bool,
        dialogue_timing_profile: DialogueTimingProfile | None = None,
        source_map_graph_admission: bool = False,
    ) -> tuple[StageHead, EntityRevisionRow | None]:
        """Validate and install one canonical revision in the caller's transaction."""

        head = self._access.rows.stage(session, project_row.id, stage)
        if head.revision != expected_revision:
            raise RevisionConflictError(f"stage:{stage.value}", expected_revision, head.revision)

        input_revisions: dict[StageName, int] = {}
        upstream_payloads: dict[StageName, StagePayload] = {}
        if source_map_graph_admission:
            if stage != StageName.STORY_GRAPH or not isinstance(payload, StoryGraphV2):
                raise TypeError("source-map admission only installs StoryGraphV2")
            from ...source_outline_contracts import validate_section_map_graph

            validate_section_map_graph(payload, ProjectBrief.model_validate(project_row.brief))
        else:
            for upstream in upstream_stages(stage):
                upstream_head = self._access.rows.stage(session, project_row.id, upstream)
                if upstream_head.status != StageStatus.READY.value:
                    raise StagePrerequisiteError(stage, upstream, upstream_head.status)
                input_revisions[upstream] = upstream_head.revision
                upstream_payloads[upstream] = self._load_stage_payload(session, project_row.id, upstream)

        if source_map_graph_admission:
            gate_evaluation = None
        else:
            brief = ProjectBrief.model_validate(project_row.brief)
            gate_evaluation = validate_stage_payload(
                stage,
                payload,
                schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                brief=brief,
                bible=upstream_payloads.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
                graph=upstream_payloads.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
                scene_beats=upstream_payloads.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
                dialogue_timing_profile=dialogue_timing_profile,
            )
        payload_data = payload.model_dump(mode="json", by_alias=False)
        content_hash = stable_hash(payload_data)
        next_inputs = {key.value: value for key, value in input_revisions.items()}
        if (
            allow_noop
            and head.status == StageStatus.READY.value
            and head.content_hash == content_hash
            and dict(head.input_revisions) == next_inputs
        ):
            if gate_evaluation is not None and head.entity_revision_id is not None:
                current_revision = session.get(EntityRevisionRow, head.entity_revision_id)
                if current_revision is None:
                    raise NotFoundError(
                        f"entity revision not found: {head.entity_revision_id}"
                    )
                self._gates._record_gate_evaluation_in_session(
                    session,
                    project_row.id,
                    current_revision,
                    gate_evaluation,
                    now=now,
                )
            return self._access.codecs.stage_head(head), None

        revision = EntityRevision(
            project_id=project_row.id,
            stage=stage,
            revision=head.revision + 1,
            parent_revision_id=head.entity_revision_id,
            content_hash=content_hash,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            input_revisions=input_revisions,
            payload=payload_data,
            created_at=now,
        )
        revision_row = EntityRevisionRow(
            id=revision.id,
            project_id=revision.project_id,
            stage=stage.value,
            revision=revision.revision,
            parent_revision_id=revision.parent_revision_id,
            content_hash=revision.content_hash,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            input_revisions=next_inputs,
            payload=payload_data,
            created_at=now,
        )
        session.add(revision_row)
        if gate_evaluation is not None:
            # The models intentionally have no ORM relationships, so flush the
            # new immutable revision before inserting its gate receipts.
            session.flush()
            self._gates._record_gate_evaluation_in_session(
                session,
                project_row.id,
                revision_row,
                gate_evaluation,
                now=now,
            )
        head.status = StageStatus.READY.value
        head.revision = revision.revision
        head.entity_revision_id = revision.id
        head.content_hash = content_hash
        head.schema_version = CURRENT_STAGE_SCHEMA_VERSION
        head.input_revisions = next_inputs
        head.stale_reasons = []
        head.updated_at = now
        self._mark_downstream_stale(session, project_row.id, stage, now)
        return self._access.codecs.stage_head(head), revision_row

    def install_source_map_graph_in_session(
        self, session: Session, project_row: ProjectRow, graph: StoryGraphV2, *,
        expected_revision: int, now: datetime,
    ) -> StageHead:
        """Install the one F1B graph admission inside its binding transaction."""

        head, _ = self._install_stage_in_session(
            session,
            project_row,
            StageName.STORY_GRAPH,
            graph,
            expected_revision=expected_revision,
            now=now,
            allow_noop=False,
            source_map_graph_admission=True,
        )
        return head

    def update_stage(
        self,
        project_id: str,
        stage: StageName,
        expected_revision: int,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        parsed = stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(payload)
        with self._access.leases.lifecycle_write() as session:
            project_row = self._access.rows.project(session, project_id)
            self._access.guards.active(project_row)
            head, _ = self._install_stage_in_session(
                session,
                project_row,
                stage,
                parsed,
                expected_revision=expected_revision,
                now=utc_now(),
                allow_noop=True,
            )
            return head
