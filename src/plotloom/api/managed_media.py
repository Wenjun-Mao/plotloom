from __future__ import annotations

from hashlib import sha256
import json
from typing import Annotated, Any, Callable, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from ..exceptions import (
    NotFoundError,
)
from ..persistence import SQLiteRepository, stable_hash
from ..managed_media import (
    ImportDeclaration,
    ManagedMediaError,
    KeyframeCenterCropRequest,
    PreviewRequest,
    ReviewedSelectionRequest,
    VisualIntentInput,
    inspect_import_image,
    publish_import,
)
from ..keyframe_preparation import center_crop_png


def register_managed_media_routes(
    app: FastAPI,
    repo: SQLiteRepository,
    selectable_h3_target: Callable[[str], dict[str, Any]],
) -> None:
    def preview_view(project_id: str, preview: dict[str, Any]) -> dict[str, Any]:
        """Derived applicability never mutates the frozen preview manifest."""

        state = "current"
        manifest = preview["manifest"]
        if stable_hash(manifest) != preview["manifestHash"]:
            state = "corrupt"
        if state == "current":
            try:
                closure = repo.get_approval_closure(str(manifest["approvalId"]))
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
                if state == "current" and not closure.active:
                    state = (
                        "revoked"
                        if repo.approval_is_revoked(closure.decision.id)
                        else "stale"
                    )
            except NotFoundError:
                state = "stale"
        for frame in manifest["frames"]:
            # A receipt whose manifest no longer verifies is already unsafe to
            # interpret. Do not let a secondary storage observation mask that
            # stronger integrity failure with a different derived state.
            if state == "corrupt":
                break
            try:
                if (
                    state == "current"
                    and not repo.reviewed_preview_dependencies_current(
                        project_id, frame
                    )
                ):
                    state = "stale"
                stored = repo.get_managed_asset_storage(project_id, frame["assetId"])
                if stored["displayHash"] != frame["displayHash"]:
                    state = "corrupt"
                    break
                content = app.state.artifact_store.get(stored["displayUri"])
                if sha256(content).hexdigest() != frame["displayHash"]:
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
    async def import_managed_asset(
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
        limits = app.state.managed_media_limits
        content = await image.read(limits.max_import_bytes + 1)
        observed = inspect_import_image(content, limits)

        def publish_under_admission() -> tuple[str, str]:
            try:
                return publish_import(app.state.artifact_store, content, observed)
            except (OSError, KeyError, ValueError) as error:
                raise ManagedMediaError(
                    "corrupt_existing_blob", "stored media could not be verified"
                ) from error

        return repo.record_managed_import(
            project_id,
            original_hash=observed.content_hash,
            display_hash=observed.display_hash,
            mime_type=observed.mime_type,
            byte_size=observed.byte_size,
            width=observed.width,
            height=observed.height,
            declaration=declaration.model_dump(mode="json", by_alias=True),
            publish=publish_under_admission,
        )

    @app.get("/api/v2/projects/{project_id}/managed-assets")
    def get_managed_assets(project_id: str) -> dict[str, Any]:
        return {
            "assets": repo.list_managed_assets(project_id),
            "selectionRevision": repo.visual_selection_revision(project_id),
        }

    @app.get("/api/v2/projects/{project_id}/managed-assets/{asset_id}/{variant}")
    def serve_managed_asset(
        project_id: str, asset_id: str, variant: Literal["display", "original"]
    ) -> Response:
        stored = repo.get_managed_asset_storage(project_id, asset_id)
        uri = stored["displayUri"] if variant == "display" else stored["originalUri"]
        try:
            content = app.state.artifact_store.get(uri)
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
        "/api/v2/projects/{project_id}/reviewed-keyframes/{binding_id}/center-crops",
        status_code=status.HTTP_201_CREATED,
    )
    def create_reviewed_keyframe_center_crop(
        project_id: str, binding_id: str, body: KeyframeCenterCropRequest
    ) -> dict[str, Any]:
        """Create an unselected deterministic crop for later creator review."""

        target = selectable_h3_target(body.target_profile_id)
        source = repo.reviewed_keyframe_crop_source(
            project_id,
            binding_id=binding_id,
            expected_selection_revision=body.expected_selection_revision,
        )
        try:
            content = app.state.artifact_store.get(source["originalUri"])
        except (FileNotFoundError, KeyError):
            raise HTTPException(
                status_code=410, detail={"code": "managed_asset_missing"}
            )
        except (ValueError, OSError):
            raise HTTPException(
                status_code=409, detail={"code": "managed_asset_corrupt"}
            )
        if sha256(content).hexdigest() != source["originalHash"]:
            raise HTTPException(
                status_code=409, detail={"code": "managed_asset_corrupt"}
            )
        try:
            transformed = center_crop_png(
                content, target_width=target["width"], target_height=target["height"]
            )
            observed = inspect_import_image(transformed, app.state.managed_media_limits)
        except (OSError, ValueError, ManagedMediaError) as error:
            if isinstance(error, ManagedMediaError):
                raise
            raise ManagedMediaError(
                "keyframe_crop_failed", "selected keyframe could not be cropped safely"
            ) from error
        if (observed.width, observed.height) != (target["width"], target["height"]):
            raise ManagedMediaError(
                "keyframe_crop_failed", "derived crop did not match the frozen profile"
            )

        def publish_under_admission() -> tuple[str, str]:
            try:
                return publish_import(app.state.artifact_store, transformed, observed)
            except (OSError, KeyError, ValueError) as error:
                raise ManagedMediaError(
                    "delivery_storage_failed", "derived keyframe could not be stored"
                ) from error

        asset = repo.record_reviewed_keyframe_center_crop(
            project_id,
            source=source,
            target_profile=target,
            expected_selection_revision=body.expected_selection_revision,
            original_hash=observed.content_hash,
            display_hash=observed.display_hash,
            mime_type=observed.mime_type,
            byte_size=observed.byte_size,
            width=observed.width,
            height=observed.height,
            publish=publish_under_admission,
        )
        return {"asset": asset}

    @app.post(
        "/api/v2/projects/{project_id}/managed-assets/{asset_id}/visual-intents",
        status_code=status.HTTP_201_CREATED,
    )
    def add_visual_intent(
        project_id: str, asset_id: str, body: VisualIntentInput
    ) -> dict[str, Any]:
        return repo.create_visual_intent(
            project_id, asset_id, body.model_dump(mode="json", by_alias=True)
        )

    @app.post(
        "/api/v2/projects/{project_id}/reviewed-keyframes",
        status_code=status.HTTP_201_CREATED,
    )
    def select_reviewed_keyframe(
        project_id: str, body: ReviewedSelectionRequest
    ) -> dict[str, Any]:
        return repo.select_reviewed_keyframe(
            project_id, **body.model_dump(mode="python", by_alias=False)
        )

    @app.post(
        "/api/v2/projects/{project_id}/still-previews",
        status_code=status.HTTP_201_CREATED,
    )
    def create_still_preview(project_id: str, body: PreviewRequest) -> dict[str, Any]:
        preview = repo.create_still_preview(
            project_id, **body.model_dump(mode="python", by_alias=False)
        )
        return preview_view(project_id, preview)

    @app.get("/api/v2/projects/{project_id}/still-previews")
    def get_still_previews(project_id: str) -> dict[str, Any]:
        return {
            "previews": [
                preview_view(project_id, preview)
                for preview in repo.list_still_previews(project_id)
            ]
        }

    @app.get("/api/v2/projects/{project_id}/visual-workbench")
    def get_visual_workbench(project_id: str) -> dict[str, Any]:
        return {
            "assets": repo.list_managed_assets(project_id),
            "selectionRevision": repo.visual_selection_revision(project_id),
            "visualIntents": repo.list_visual_intents(project_id),
            "reviewedKeyframes": repo.list_current_reviewed_keyframes(project_id),
            "characterReferences": repo.list_character_reference_decisions(project_id),
            "samePersonReviews": repo.list_same_person_reviews(project_id),
            "previews": [
                preview_view(project_id, preview)
                for preview in repo.list_still_previews(project_id)
            ],
        }
