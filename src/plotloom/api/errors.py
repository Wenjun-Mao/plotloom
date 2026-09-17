from __future__ import annotations

from typing import Any, Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..exceptions import (
    BootstrapContentionError,
    IdempotencyConflictError,
    InvalidTransitionError,
    KeyframeAspectMismatchError,
    LifecycleContentionError,
    NotFoundError,
    ProductionPipelineNotReadyError,
    ProjectBusyError,
    ProjectManagedAssetsPresentError,
    RepairEligibilityError,
    RevisionConflictError,
    SchemaResetRequiredError,
    StagePrerequisiteError,
)
from ..managed_media import (
    ManagedMediaError,
)
from ..image_job_contracts import (
    ImageJobError,
)
from ..creative_handoff_contracts import CreativeHandoffError
from ..generation.story_graph_topology import StoryGraphTopologyError
from ..validation import DomainValidationError, pydantic_issues


def register_api_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(
        _request: Request, error: NotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"code": "not_found", "message": str(error)}
        )

    @app.exception_handler(RevisionConflictError)
    async def revision_conflict_handler(
        _request: Request, error: RevisionConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "revision_conflict",
                "message": str(error),
                "resource": error.resource,
                "expectedRevision": error.expected_revision,
                "actualRevision": error.actual_revision,
            },
        )

    @app.exception_handler(StagePrerequisiteError)
    async def prerequisite_handler(
        _request: Request, error: StagePrerequisiteError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "stage_prerequisite",
                "message": str(error),
                "stage": error.stage.value,
                "prerequisite": error.prerequisite.value,
                "status": error.status,
            },
        )

    @app.exception_handler(InvalidTransitionError)
    async def transition_handler(
        _request: Request, error: InvalidTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": "invalid_transition", "message": str(error)},
        )

    @app.exception_handler(KeyframeAspectMismatchError)
    async def keyframe_aspect_mismatch_handler(
        _request: Request, error: KeyframeAspectMismatchError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "code": error.code,
                "message": str(error),
                "source": {"width": error.source_width, "height": error.source_height},
                "target": {"width": error.target_width, "height": error.target_height},
            },
        )

    @app.exception_handler(SchemaResetRequiredError)
    async def schema_reset_required_handler(
        _request: Request, error: SchemaResetRequiredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": error.code,
                "message": str(error),
                "stage": error.stage.value,
                "schemaVersion": error.schema_version,
            },
        )

    @app.exception_handler(RepairEligibilityError)
    async def repair_eligibility_handler(
        _request: Request, error: RepairEligibilityError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ProductionPipelineNotReadyError)
    async def production_pipeline_not_ready_handler(
        _request: Request, error: ProductionPipelineNotReadyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ProjectBusyError)
    async def project_busy_handler(
        _request: Request, error: ProjectBusyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409, content={"code": "project_busy", "message": str(error)}
        )

    @app.exception_handler(ProjectManagedAssetsPresentError)
    async def project_managed_assets_present_handler(
        _request: Request, error: ProjectManagedAssetsPresentError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409, content={"code": error.code, "message": str(error)}
        )

    @app.exception_handler(ManagedMediaError)
    async def managed_media_handler(
        _request: Request, error: ManagedMediaError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"code": error.code, "message": str(error)}
        )

    @app.exception_handler(ImageJobError)
    async def image_job_handler(
        _request: Request, error: ImageJobError
    ) -> JSONResponse:
        status_code = (
            409
            if error.code
            in {
                "image_exchange_not_configured",
                "image_exchange_invalid",
                "package_conflict",
                "delivery_conflict",
                "delivery_finalized",
                "request_integrity",
            }
            else 422
        )
        return JSONResponse(
            status_code=status_code, content={"code": error.code, "message": str(error)}
        )

    @app.exception_handler(CreativeHandoffError)
    async def creative_handoff_handler(
        _request: Request, error: CreativeHandoffError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=(
                status.HTTP_409_CONFLICT
                if error.code in {"delivery_stale", "delivery_conflict", "delivery_identity_mismatch", "request_identity_mismatch", "package_conflict"}
                else status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(LifecycleContentionError)
    async def lifecycle_contention_handler(
        _request: Request, error: LifecycleContentionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"code": "lifecycle_contention", "message": str(error)},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        _request: Request, error: IdempotencyConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": "idempotency_conflict", "message": str(error)},
        )

    @app.exception_handler(BootstrapContentionError)
    async def bootstrap_contention_handler(
        _request: Request, error: BootstrapContentionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"code": "bootstrap_contention", "message": str(error)},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_handler(
        _request: Request, error: DomainValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "domain_validation",
                "message": str(error),
                "issues": error.issues,
            },
        )

    def schema_validation_response(issues: list[Mapping[str, Any]]) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "schema_validation",
                "message": "validated payload does not match its current schema",
                "issues": issues,
            },
        )

    @app.exception_handler(ValidationError)
    async def canonical_schema_validation_handler(
        _request: Request, error: ValidationError
    ) -> JSONResponse:
        return schema_validation_response(pydantic_issues(error))

    @app.exception_handler(RequestValidationError)
    async def request_schema_validation_handler(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        # FastAPI's default response includes each rejected ``input`` value.
        # That is unsafe for endpoints which defensively reject API-key-shaped
        # fields, and it also bypasses the workbench's stable issue contract.
        # Project only the three public fields we own and remove FastAPI's
        # transport-level ``body`` prefix from author-facing paths.
        issues = []
        for item in error.errors():
            location = [str(part) for part in item.get("loc", ())]
            if location and location[0] == "body":
                location = location[1:]
            issues.append(
                {
                    "code": "schema_validation",
                    "path": ".".join(location),
                    "message": str(item.get("msg") or "invalid request value"),
                }
            )
        return schema_validation_response(issues)

    @app.exception_handler(StoryGraphTopologyError)
    async def topology_planning_handler(
        _request: Request, error: StoryGraphTopologyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": error.code, "message": str(error)},
        )
