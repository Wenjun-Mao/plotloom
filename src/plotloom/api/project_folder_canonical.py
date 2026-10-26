from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, status
from fastapi.responses import Response

from plotloom.api.contracts import (
    AuthoringDraftDiscardRequest,
    AuthoringDraftUpsertRequest,
    ProjectPatchRequest,
    StageEnvelopesResponse,
    StagePatchRequest,
)
from plotloom.project_contracts import Project
from plotloom.stage_contracts import AuthoringDraft, StageHead, StageName

from .draft_scope import assert_canonical_draft_scope


def register_project_canonical_routes(app: FastAPI, opened_project: Callable) -> None:
    @app.patch("/api/v2/projects/{project_id}", response_model=Project)
    def patch_project(
        project_id: str,
        body: ProjectPatchRequest,
        response: Response,
    ) -> Project:
        with opened_project(project_id) as store:
            assert_canonical_draft_scope(body.consumed_draft, required_scope="brief")
            if body.consumed_draft is None:
                updated = store.update_brief(
                    body.brief, expected_revision=body.expected_revision
                )
            else:
                updated = store.update_brief_consuming_authoring_draft(
                    body.brief,
                    expected_revision=body.expected_revision,
                    entity_id=body.consumed_draft.entity_id,
                    expected_draft_revision=body.consumed_draft.draft_revision,
                )
                # The repository consumed this receipt in the same SQLite
                # transaction that installed canonical content.
                response.headers["X-Plotloom-Draft-Consumed-Revision"] = str(
                    body.consumed_draft.draft_revision
                )
            return updated

    @app.get(
        "/api/v2/projects/{project_id}/stages", response_model=StageEnvelopesResponse
    )
    def get_stages(project_id: str) -> StageEnvelopesResponse:
        with opened_project(project_id) as store:
            return StageEnvelopesResponse(
                stages=store.authoring.list_stage_envelopes(project_id)
            )

    @app.patch("/api/v2/projects/{project_id}/stages/{stage}", response_model=StageHead)
    def patch_stage(
        project_id: str,
        stage: StageName,
        body: StagePatchRequest,
        response: Response,
    ) -> StageHead:
        with opened_project(project_id) as store:
            assert_canonical_draft_scope(
                body.consumed_draft, required_scope=stage.value
            )
            if body.consumed_draft is None:
                updated = store.update_stage(
                    stage, body.payload, expected_revision=body.expected_revision
                )
            else:
                updated = store.update_stage_consuming_authoring_draft(
                    stage,
                    body.payload,
                    expected_revision=body.expected_revision,
                    entity_id=body.consumed_draft.entity_id,
                    expected_draft_revision=body.consumed_draft.draft_revision,
                )
                response.headers["X-Plotloom-Draft-Consumed-Revision"] = str(
                    body.consumed_draft.draft_revision
                )
            return updated

    @app.get(
        "/api/v2/projects/{project_id}/authoring-drafts",
        response_model=list[AuthoringDraft],
    )
    def list_authoring_drafts(project_id: str) -> list[AuthoringDraft]:
        with opened_project(project_id) as store:
            return store.authoring_drafts()

    @app.put(
        "/api/v2/projects/{project_id}/authoring-drafts", response_model=AuthoringDraft
    )
    def save_authoring_draft(
        project_id: str,
        body: AuthoringDraftUpsertRequest,
    ) -> AuthoringDraft:
        with opened_project(project_id) as store:
            return store.save_authoring_draft(
                editor_scope=body.editor_scope,
                entity_id=body.entity_id,
                base_canonical_revision=body.base_canonical_revision,
                expected_draft_revision=body.expected_draft_revision,
                payload=body.payload,
            )

    @app.delete(
        "/api/v2/projects/{project_id}/authoring-drafts",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def discard_authoring_draft(
        project_id: str,
        body: AuthoringDraftDiscardRequest,
    ) -> Response:
        with opened_project(project_id) as store:
            consumed = store.discard_authoring_draft(
                editor_scope=body.editor_scope,
                entity_id=body.entity_id,
                expected_draft_revision=body.expected_draft_revision,
            )
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers={
                "X-Plotloom-Draft-Consumed-Revision": str(body.expected_draft_revision)
                if consumed
                else "",
            },
        )
