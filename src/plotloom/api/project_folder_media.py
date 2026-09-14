from __future__ import annotations

from hashlib import sha256
import json
from typing import Annotated, Any, Callable, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response

from ..exceptions import NotFoundError
from ..image_job_contracts import ImageJobError
from ..managed_media import (
    ImportDeclaration,
    ManagedMediaError,
    ManagedMediaLimits,
    PreviewRequest,
    ReviewedSelectionRequest,
    inspect_import_image,
    publish_import,
)
from ..persistence import stable_hash
from .models import ProjectFolderVisualIntentRequest


def register_project_folder_media_routes(
    app: FastAPI,
    opened_project: Callable[[str], Any],
    *,
    require_media_draft_scope: Callable[..., Any],
) -> None:
    """Register direct-storage asset, preview, and workbench routes."""

    @app.exception_handler(ManagedMediaError)
    async def managed_media_error_handler(
        _request: Request, error: ManagedMediaError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ImageJobError)
    async def image_job_error_handler(
        _request: Request, error: ImageJobError
    ) -> JSONResponse:
        conflict_codes = {
            "package_conflict",
            "delivery_conflict",
            "delivery_finalized",
            "delivery_geometry_mismatch",
            "delivery_geometry_contract_invalid",
        }
        return JSONResponse(
            status_code=(
                status.HTTP_409_CONFLICT
                if error.code in conflict_codes
                else status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            content={"code": error.code, "message": str(error)},
        )

    def preview_view(
        store: Any, project_id: str, preview: dict[str, Any]
    ) -> dict[str, Any]:
        """Derive preview applicability without mutating the frozen receipt."""

        repository = store.repository
        state = "current"
        manifest = preview["manifest"]
        if stable_hash(manifest) != preview["manifestHash"]:
            state = "corrupt"
        if state == "current":
            try:
                closure = repository.get_approval_closure(str(manifest["approvalId"]))
                expected_inputs = {
                    stage.value: revision
                    for stage, revision in closure.decision.canonical_input_revisions
                }
                if (
                    manifest.get("approvalGateSetVersion")
                    != closure.decision.gate_set_version
                    or manifest.get("canonicalInputRevisions") != expected_inputs
                ):
                    state = "corrupt"
                elif not closure.active:
                    state = (
                        "revoked"
                        if repository.approval_is_revoked(closure.decision.id)
                        else "stale"
                    )
            except NotFoundError:
                state = "stale"
        for frame in manifest["frames"]:
            if state == "corrupt":
                break
            try:
                if (
                    state == "current"
                    and not repository.reviewed_preview_dependencies_current(
                        project_id, frame
                    )
                ):
                    state = "stale"
                stored = repository.get_managed_asset_storage(
                    project_id, frame["assetId"]
                )
                if (
                    stored["displayHash"] != frame["displayHash"]
                    or sha256(store.artifacts.get(stored["displayUri"])).hexdigest()
                    != frame["displayHash"]
                ):
                    state = "corrupt"
                    break
            except (FileNotFoundError, KeyError):
                state = "missing"
                break
            except (ValueError, OSError):
                state = "corrupt"
                break
        return {**preview, "state": state}

    @app.post(
        "/api/v2/projects/{project_id}/managed-assets",
        status_code=status.HTTP_201_CREATED,
    )
    async def import_project_managed_asset(
        project_id: str,
        image: Annotated[UploadFile, File(description="JPEG or PNG original bytes")],
        origin: Annotated[str, Form(min_length=1, max_length=2_000)],
        rights: Annotated[Literal["known", "unknown"], Form()] = "unknown",
        rights_note: Annotated[str | None, Form(max_length=2_000)] = None,
        declared_additions_json: Annotated[str | None, Form()] = None,
    ) -> dict[str, Any]:
        try:
            additions = (
                json.loads(declared_additions_json) if declared_additions_json else []
            )
        except json.JSONDecodeError as error:
            raise ManagedMediaError(
                "invalid_declaration", "declared additions must be JSON"
            ) from error
        declaration = ImportDeclaration(
            origin=origin,
            rights=rights,
            rights_note=rights_note,
            declared_additions=additions,
        )
        limits = ManagedMediaLimits()
        content = await image.read(limits.max_import_bytes + 1)
        observed = inspect_import_image(content, limits)
        with opened_project(project_id) as store:
            return store.repository.record_managed_import(
                project_id,
                original_hash=observed.content_hash,
                display_hash=observed.display_hash,
                mime_type=observed.mime_type,
                byte_size=observed.byte_size,
                width=observed.width,
                height=observed.height,
                declaration=declaration.model_dump(mode="json", by_alias=True),
                publish=lambda: publish_import(store.artifacts, content, observed),
            )

    @app.get("/api/v2/projects/{project_id}/managed-assets")
    def get_project_managed_assets(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {
                "assets": store.repository.list_managed_assets(project_id),
                "selectionRevision": store.repository.visual_selection_revision(
                    project_id
                ),
            }

    @app.get("/api/v2/projects/{project_id}/managed-assets/{asset_id}/{variant}")
    def serve_project_managed_asset(
        project_id: str, asset_id: str, variant: Literal["display", "original"]
    ) -> Response:
        with opened_project(project_id) as store:
            stored = store.repository.get_managed_asset_storage(project_id, asset_id)
            try:
                content = store.artifacts.get(
                    stored["displayUri"]
                    if variant == "display"
                    else stored["originalUri"]
                )
            except (FileNotFoundError, KeyError):
                raise HTTPException(
                    status_code=410, detail={"code": "managed_asset_missing"}
                )
            except (ValueError, OSError):
                raise HTTPException(
                    status_code=409, detail={"code": "managed_asset_corrupt"}
                )
            return Response(
                content=content,
                media_type="image/png" if variant == "display" else stored["mimeType"],
            )

    @app.post(
        "/api/v2/projects/{project_id}/managed-assets/{asset_id}/visual-intents",
        status_code=status.HTTP_201_CREATED,
    )
    def add_project_visual_intent(
        project_id: str, asset_id: str, body: ProjectFolderVisualIntentRequest
    ) -> dict[str, Any]:
        required_entity_id = f"{body.shot_id}:{asset_id}"
        require_media_draft_scope(
            body.consumed_draft,
            required_scope="visual_intent",
            required_entity_id=required_entity_id,
        )
        intent = body.model_dump(
            mode="json", by_alias=True, exclude={"shot_id", "consumed_draft"}
        )
        draft_payload = {"assetId": asset_id, "shotId": body.shot_id, **intent}
        with opened_project(project_id) as store:
            return store.repository.create_visual_intent(
                project_id,
                asset_id,
                intent,
                consumed_draft=(
                    body.consumed_draft.entity_id,
                    body.consumed_draft.draft_revision,
                    draft_payload,
                ),
            )

    @app.post(
        "/api/v2/projects/{project_id}/reviewed-keyframes",
        status_code=status.HTTP_201_CREATED,
    )
    def select_project_reviewed_keyframe(
        project_id: str, body: ReviewedSelectionRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.repository.select_reviewed_keyframe(
                project_id, **body.model_dump(mode="python", by_alias=False)
            )

    @app.post(
        "/api/v2/projects/{project_id}/still-previews",
        status_code=status.HTTP_201_CREATED,
    )
    def create_project_still_preview(
        project_id: str, body: PreviewRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            preview = store.repository.create_still_preview(
                project_id, **body.model_dump(mode="python", by_alias=False)
            )
            return preview_view(store, project_id, preview)

    @app.get("/api/v2/projects/{project_id}/still-previews")
    def get_project_still_previews(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {
                "previews": [
                    preview_view(store, project_id, item)
                    for item in store.repository.list_still_previews(project_id)
                ]
            }

    @app.get("/api/v2/projects/{project_id}/visual-workbench")
    def get_project_visual_workbench(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            repository = store.repository
            return {
                "assets": repository.list_managed_assets(project_id),
                "selectionRevision": repository.visual_selection_revision(project_id),
                "visualIntents": repository.list_visual_intents(project_id),
                "reviewedKeyframes": repository.list_current_reviewed_keyframes(
                    project_id
                ),
                "characterReferences": repository.list_character_reference_decisions(
                    project_id
                ),
                "samePersonReviews": repository.list_same_person_reviews(project_id),
                "previews": [
                    preview_view(store, project_id, item)
                    for item in repository.list_still_previews(project_id)
                ],
            }
