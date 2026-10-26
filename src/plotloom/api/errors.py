from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..creative_handoff_contracts import CreativeHandoffError
from ..exceptions import (
    BootstrapContentionError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
    ProjectManagedAssetsPresentError,
    RevisionConflictError,
)
from ..exceptions import ProjectBusyError as LifecycleProjectBusyError
from ..graph_safety_diagnostics import transition_error_content
from ..image_job_contracts import ImageJobError
from ..managed_media import ManagedMediaError
from ..project_storage import (
    ProjectBusyError,
    ProjectClosedError,
    ProjectStorageConflictError,
    ProjectStorageError,
)
from ..validation import DomainValidationError
from .production_bridge_state import BridgeIntentUnavailableError


def register_api_error_handlers(app: FastAPI) -> None:
    """Install the canonical project-folder HTTP policy, leaving native validation intact."""

    @app.exception_handler(ProjectStorageConflictError)
    async def project_storage_conflict_handler(
        _request: Request, error: ProjectStorageConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "revision_conflict", "message": str(error)},
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        _request: Request, error: IdempotencyConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "idempotency_conflict", "message": str(error)},
        )

    @app.exception_handler(BootstrapContentionError)
    async def bootstrap_contention_handler(
        _request: Request, error: BootstrapContentionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"code": "bootstrap_contention", "message": str(error)},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )

    @app.exception_handler(ProjectBusyError)
    async def project_busy_handler(
        _request: Request, error: ProjectBusyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "project_busy", "message": str(error)},
        )

    @app.exception_handler(LifecycleProjectBusyError)
    async def persisted_project_busy_handler(
        _request: Request, error: LifecycleProjectBusyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "project_busy", "message": str(error)},
        )

    @app.exception_handler(ProjectClosedError)
    async def project_closed_handler(
        _request: Request, error: ProjectClosedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "project_closed", "message": str(error)},
        )

    @app.exception_handler(NotFoundError)
    async def project_folder_not_found_handler(
        _request: Request, error: NotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": "not_found", "message": str(error)},
        )

    @app.exception_handler(InvalidTransitionError)
    async def project_folder_transition_handler(
        _request: Request, error: InvalidTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=transition_error_content(error),
        )

    @app.exception_handler(CreativeHandoffError)
    async def project_folder_creative_handoff_handler(
        _request: Request, error: CreativeHandoffError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=(
                status.HTTP_409_CONFLICT
                if error.code
                in {
                    "delivery_stale",
                    "delivery_conflict",
                    "delivery_identity_mismatch",
                    "request_identity_mismatch",
                    "package_conflict",
                    "delivery_cancelled",
                }
                else status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ProjectManagedAssetsPresentError)
    async def project_folder_managed_assets_handler(
        _request: Request, error: ProjectManagedAssetsPresentError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ProjectStorageError)
    async def project_storage_error_handler(
        _request: Request, error: ProjectStorageError
    ) -> JSONResponse:
        missing = str(error).startswith("project not found")
        if missing:
            response_status = status.HTTP_404_NOT_FOUND
            code = "not_found"
        else:
            response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
            code = "project_storage_error"
        return JSONResponse(
            status_code=response_status,
            content={"code": code, "message": str(error)},
        )

    @app.exception_handler(RevisionConflictError)
    async def authoring_revision_conflict_handler(
        _request: Request, error: RevisionConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "revision_conflict", "message": str(error)},
        )

    @app.exception_handler(DomainValidationError)
    async def project_folder_domain_validation_handler(
        _request: Request, error: DomainValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "code": "domain_validation",
                "message": str(error),
                "issues": error.issues,
            },
        )

    @app.exception_handler(ValueError)
    async def authoring_validation_handler(
        _request: Request, error: ValueError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"code": "authoring_draft_invalid", "message": str(error)},
        )

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
            # These mean a previously accepted immutable identity conflicts.
            # Untrusted delivery shape/content (including geometry) is 422.
            "package_conflict",
            "delivery_conflict",
            "delivery_finalized",
            "specialist_busy",
            "specialist_already_sent",
            "image_dispatch_busy",
            "image_dispatch_already_attempted",
        }
        return JSONResponse(
            status_code=(
                status.HTTP_409_CONFLICT
                if error.code in conflict_codes
                else status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(BridgeIntentUnavailableError)
    async def unavailable_intent_handler(
        _request: Request, _error: BridgeIntentUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "bridge_intent_not_configured",
                "reason": "not_configured",
                "message": "当前服务未配置戏剧意图推断。可逐项填写作者意图并保存整包；不会自动配置或重试模型。",
            },
        )
