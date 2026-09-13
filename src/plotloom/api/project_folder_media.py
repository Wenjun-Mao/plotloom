from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..exceptions import (
    NotFoundError,
)
from ..persistence import stable_hash
from ..managed_media import (
    ManagedMediaError,
)
from ..image_job_contracts import (
    ImageJobError,
)




def register_project_folder_media_routes(
    app: FastAPI, opened_project: Callable[[str], Any], *,
    project_h3_target: Callable[[str], dict[str, Any]],
    assert_canonical_draft_scope: Callable[..., None],
    require_media_draft_scope: Callable[..., Any],
) -> None:
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
            "package_conflict", "delivery_conflict", "delivery_finalized",
            "delivery_geometry_mismatch", "delivery_geometry_contract_invalid",
        }
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT if error.code in conflict_codes else status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"code": error.code, "message": str(error)},
        )

    def preview_view(store: Any, project_id: str, preview: dict[str, Any]) -> dict[str, Any]:
        """Derive preview applicability without mutating the frozen receipt."""

        repository = store.repository
        state = "current"
        manifest = preview["manifest"]
        if stable_hash(manifest) != preview["manifestHash"]:
            state = "corrupt"
        if state == "current":
            try:
                closure = repository.get_approval_closure(str(manifest["approvalId"]))
                expected_inputs = {stage.value: revision for stage, revision in closure.decision.canonical_input_revisions}
                if (
                    manifest.get("approvalGateSetVersion") != closure.decision.gate_set_version
                    or manifest.get("canonicalInputRevisions") != expected_inputs
                ):
                    state = "corrupt"
                elif not closure.active:
                    state = "revoked" if repository.approval_is_revoked(closure.decision.id) else "stale"
            except NotFoundError:
                state = "stale"
        for frame in manifest["frames"]:
            if state == "corrupt":
                break
            try:
                if state == "current" and not repository.reviewed_preview_dependencies_current(project_id, frame):
                    state = "stale"
                stored = repository.get_managed_asset_storage(project_id, frame["assetId"])
                if stored["displayHash"] != frame["displayHash"] or sha256(store.artifacts.get(stored["displayUri"])).hexdigest() != frame["displayHash"]:
                    state = "corrupt"
                    break
            except (FileNotFoundError, KeyError):
                state = "missing"
                break
            except (ValueError, OSError):
                state = "corrupt"
                break
        return {**preview, "state": state}

