"""Named atomic workflows that span project authoring capabilities."""

from __future__ import annotations

from typing import Any

from ...domain import StageHead, StageName, StagePayload, stage_payload_model, utc_now
from ...exceptions import RevisionConflictError
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from .access import ProjectPersistenceAccess


class ProjectAuthoringWorkflow:
    """Own cross-capability authoring writes without exposing sessions to callers."""

    def __init__(self, access: ProjectPersistenceAccess, drafts: Any, canonical: Any) -> None:
        self._access = access
        self._drafts = drafts
        self._canonical = canonical

    def update_stage_consuming_authoring_draft(
        self,
        project_id: str,
        stage: StageName,
        expected_revision: int,
        payload: StagePayload | dict[str, Any],
        *,
        entity_id: str,
        expected_draft_revision: int,
    ) -> StageHead:
        """Install a canonical stage and consume its exact draft in one lease."""

        parsed = stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(payload)
        canonical_payload = parsed.model_dump(mode="json", by_alias=True)
        with self._access.leases.lifecycle_write() as session:
            project_row = self._access.rows.project(session, project_id)
            self._access.guards.active(project_row)
            head = self._access.rows.stage(session, project_id, stage)
            if head.revision != expected_revision:
                raise RevisionConflictError(f"stage:{stage.value}", expected_revision, head.revision)
            self._drafts._consume_exact_authoring_draft_in_session(
                session,
                project_row,
                editor_scope=stage.value,
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
                canonical_base_revision=head.revision,
                canonical_payload=canonical_payload,
            )
            updated, _ = self._canonical._install_stage_in_session(
                session,
                project_row,
                stage,
                parsed,
                expected_revision=expected_revision,
                now=utc_now(),
                allow_noop=True,
            )
            return updated
