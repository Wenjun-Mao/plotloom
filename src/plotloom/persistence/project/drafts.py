from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER, AuthoringDraft, AuthoringDraftScope, DialogueTimingProfile,
    EntityRevision, GateEvaluation, GateEvidence, GateResult, InitialStage,
    LatestRunSummary, Project, ProjectBrief, ProjectCreation, ProjectDuplicateResult,
    ProjectLifecycleStatus, ProjectSummary, StageEnvelope, StageHead, StageName,
    StagePayload, StageStatus, VisualIntentDraftPayload, ImageDirectionDraftPayload,
    downstream_stages, new_id, stage_payload_model,
    contains_secret_setting, contains_secret_value, utc_now, upstream_stages,
    validate_initial_stage_prefix,
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

class ProjectDraftPersistence:
    """Typed project persistence collaborator; the facade owns compatibility only."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: Any) -> None:
        self._access = access
        self._canonical = canonical

    def update_project(self, project_id: str, expected_revision: int, brief: ProjectBrief) -> Project:
        with self._access.leases.lifecycle_write() as session:
            row = self._access.rows.project(session, project_id)
            self._access.guards.active(row)
            if row.revision != expected_revision:
                raise RevisionConflictError("project", expected_revision, row.revision)
            brief_data = brief.model_dump(mode="json", by_alias=False)
            if row.brief == brief_data:
                return self._access.codecs.project(row)
            row.brief = brief_data
            row.revision += 1
            row.updated_at = utc_now()
            for stage in STAGE_ORDER:
                head = self._access.rows.stage(session, project_id, stage)
                if head.status != StageStatus.MISSING.value:
                    head.status = StageStatus.STALE.value
                    head.stale_reasons = ["project brief revision changed"]
                    head.updated_at = row.updated_at
            return self._access.codecs.project(row)

    def _consume_exact_authoring_draft_in_session(
        self,
        session: Session,
        project: ProjectRow,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        expected_draft_revision: int,
        canonical_base_revision: int,
        canonical_payload: dict[str, Any],
    ) -> None:
        """Bind canonical Save to the precise acknowledged authoring buffer.

        A draft revision is a receipt for both its canonical input revision and
        its validated editor payload. Checking all three in the same write
        transaction prevents a request from consuming an unrelated buffer.
        """

        row = session.scalar(
            select(AuthoringDraftRow).where(
                AuthoringDraftRow.project_id == project.id,
                AuthoringDraftRow.editor_scope == editor_scope,
                AuthoringDraftRow.entity_id == entity_id,
            )
        )
        actual_revision = row.draft_revision if row is not None else 0
        if row is None or row.draft_revision != expected_draft_revision:
            raise RevisionConflictError(
                f"authoring draft {editor_scope}/{entity_id}",
                expected_draft_revision,
                actual_revision,
            )
        if row.base_canonical_revision != canonical_base_revision:
            raise RevisionConflictError(
                f"authoring draft canonical base {editor_scope}",
                canonical_base_revision,
                row.base_canonical_revision,
            )
        if row.payload != canonical_payload:
            raise RevisionConflictError(
                f"authoring draft payload {editor_scope}/{entity_id}",
                expected_draft_revision,
                row.draft_revision,
            )
        session.delete(row)

    def update_project_consuming_authoring_draft(
        self,
        project_id: str,
        expected_revision: int,
        brief: ProjectBrief,
        *,
        entity_id: str,
        expected_draft_revision: int,
    ) -> Project:
        """Atomically save a brief and consume the exact acknowledged draft."""

        canonical_payload = brief.model_dump(mode="json", by_alias=True)
        with self._access.leases.lifecycle_write() as session:
            row = self._access.rows.project(session, project_id)
            self._access.guards.active(row)
            if row.revision != expected_revision:
                raise RevisionConflictError("project", expected_revision, row.revision)
            self._consume_exact_authoring_draft_in_session(
                session,
                row,
                editor_scope="brief",
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
                canonical_base_revision=row.revision,
                canonical_payload=canonical_payload,
            )
            brief_data = brief.model_dump(mode="json", by_alias=False)
            if row.brief != brief_data:
                row.brief = brief_data
                row.revision += 1
                row.updated_at = utc_now()
                for stage in STAGE_ORDER:
                    head = self._access.rows.stage(session, project_id, stage)
                    if head.status != StageStatus.MISSING.value:
                        head.status = StageStatus.STALE.value
                        head.stale_reasons = ["project brief revision changed"]
                        head.updated_at = row.updated_at
            return self._access.codecs.project(row)

    @staticmethod
    def _authoring_draft(row: AuthoringDraftRow) -> AuthoringDraft:
        return AuthoringDraft(
            project_id=row.project_id,
            editor_scope=row.editor_scope,
            entity_id=row.entity_id,
            base_canonical_revision=row.base_canonical_revision,
            draft_revision=row.draft_revision,
            payload=row.payload,
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _validate_authoring_draft_payload(
        editor_scope: AuthoringDraftScope,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Keep draft storage at the authoring contract, never UI/session shape."""

        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ValueError("authoring drafts must not contain credentials or secret-shaped values")
        if editor_scope == "brief":
            return ProjectBrief.model_validate(payload).model_dump(mode="json", by_alias=True)
        if editor_scope == "visual_intent":
            return VisualIntentDraftPayload.model_validate(payload).model_dump(mode="json", by_alias=True)
        if editor_scope == "image_direction":
            return ImageDirectionDraftPayload.model_validate(payload).model_dump(mode="json", by_alias=True)
        stage = StageName(editor_scope)
        return stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(
            payload
        ).model_dump(mode="json", by_alias=True)

    def _authoring_draft_base_revision(
        self,
        session: Session,
        project: ProjectRow,
        editor_scope: AuthoringDraftScope,
    ) -> int:
        if editor_scope == "brief":
            return project.revision
        if editor_scope in {"visual_intent", "image_direction"}:
            return self._access.rows.stage(session, project.id, StageName.STORYBOARD).revision
        return self._access.rows.stage(session, project.id, StageName(editor_scope)).revision

    def list_authoring_drafts(self, project_id: str) -> list[AuthoringDraft]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(AuthoringDraftRow)
                .where(AuthoringDraftRow.project_id == project_id)
                .order_by(AuthoringDraftRow.editor_scope, AuthoringDraftRow.entity_id)
            ).all()
            return [self._authoring_draft(row) for row in rows]

    def upsert_authoring_draft(
        self,
        project_id: str,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        base_canonical_revision: int,
        expected_draft_revision: int,
        payload: dict[str, Any],
    ) -> AuthoringDraft:
        """CAS one bounded editor buffer against its exact canonical owner."""

        validated_payload = self._validate_authoring_draft_payload(editor_scope, payload)
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            if editor_scope in {"visual_intent", "image_direction"}:
                # Media drafts are deliberately bound to the current authored
                # storyboard, not just to a browser-supplied opaque key.  This
                # keeps a copied or stale tab from retaining direction for a
                # foreign asset/shot while still leaving the draft noncanonical.
                storyboard = self._canonical._load_stage_payload(
                    session, project_id, StageName.STORYBOARD
                )
                draft_shot_id = str(validated_payload["shotId"])
                if not any(shot.id == draft_shot_id for shot in storyboard.shots):
                    raise ValueError("media authoring draft targets no current storyboard shot")
                if editor_scope == "visual_intent":
                    draft_asset_id = str(validated_payload["assetId"])
                    asset = session.get(ManagedAssetRow, draft_asset_id)
                    if asset is None or asset.project_id != project_id:
                        raise ValueError("visual-intent draft targets no project-owned asset")
                    expected_entity_id = f"{draft_shot_id}:{draft_asset_id}"
                else:
                    expected_entity_id = f"{draft_shot_id}:{validated_payload['targetId']}"
                if entity_id != expected_entity_id:
                    raise ValueError("media authoring draft identity does not match its bounded payload")
            current_base = self._authoring_draft_base_revision(session, project, editor_scope)
            if base_canonical_revision != current_base:
                raise RevisionConflictError(
                    f"authoring draft canonical base {editor_scope}",
                    base_canonical_revision,
                    current_base,
                )
            row = session.scalar(
                select(AuthoringDraftRow).where(
                    AuthoringDraftRow.project_id == project_id,
                    AuthoringDraftRow.editor_scope == editor_scope,
                    AuthoringDraftRow.entity_id == entity_id,
                )
            )
            current_draft_revision = row.draft_revision if row is not None else 0
            if expected_draft_revision != current_draft_revision:
                raise RevisionConflictError(
                    f"authoring draft {editor_scope}/{entity_id}",
                    expected_draft_revision,
                    current_draft_revision,
                )
            now = utc_now()
            if row is None:
                row = AuthoringDraftRow(
                    id=new_id(),
                    project_id=project_id,
                    editor_scope=editor_scope,
                    entity_id=entity_id,
                    base_canonical_revision=base_canonical_revision,
                    draft_revision=1,
                    payload=validated_payload,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.base_canonical_revision = base_canonical_revision
                row.draft_revision += 1
                row.payload = validated_payload
                row.updated_at = now
            session.flush()
            return self._authoring_draft(row)

    def discard_authoring_draft(
        self,
        project_id: str,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        expected_draft_revision: int,
    ) -> bool:
        """Consume only one exact acknowledged draft; preserve newer typing."""

        with self._access.leases.lifecycle_write() as session:
            self._access.rows.project(session, project_id)
            row = session.scalar(
                select(AuthoringDraftRow).where(
                    AuthoringDraftRow.project_id == project_id,
                    AuthoringDraftRow.editor_scope == editor_scope,
                    AuthoringDraftRow.entity_id == entity_id,
                )
            )
            if row is None or row.draft_revision != expected_draft_revision:
                return False
            session.delete(row)
            return True
