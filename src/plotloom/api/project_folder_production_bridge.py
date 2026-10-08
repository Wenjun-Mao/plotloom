"""User-reachable, explicit F5 proposal review and canonical installation."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse

from ..production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentGenerateRequest,
    ProductionBridgeIntentUpdateRequest,
    ProductionBridgePrepareRequest,
    ProductionBridgeState,
)
from ..production_bridge_intent_service import ProductionBridgeIntentService
from ..native_bridge_intent_service import NativeBridgeIntentService
from ..image_job_contracts import ImageJobError
from ..production_presentation import ProductionPresentationUpdateRequest
from .production_bridge_state import (
    BridgeIntentAvailable,
    BridgeIntentUnavailable,
    BridgeIntentUnavailableError,
    ProductionBridgeRuntimeState,
)
from .text_admission import TextAdmissionService


def register_project_folder_production_bridge_routes(
    app: FastAPI, opened_project: Callable[[str], Any], *,
    intent_service: ProductionBridgeIntentService | None = None,
    text_admission: TextAdmissionService | None = None,
    simulation_label: str | None = None,
    native_intent_service: NativeBridgeIntentService | None = None,
) -> None:
    def response(state: ProductionBridgeState, project_id: str) -> ProductionBridgeRuntimeState:
        result = ProductionBridgeRuntimeState(**{
            **state.model_dump(), "simulation_label": simulation_label,
            "intent_generation": BridgeIntentAvailable() if intent_service is not None and text_admission is not None else BridgeIntentUnavailable(),
            "native_intent_generation": BridgeIntentAvailable() if native_intent_service is not None and native_intent_service.configured() else BridgeIntentUnavailable(),
        })
        if state.intent_job is not None and state.intent_job.transport == "codex_native" and native_intent_service is not None:
            result.native_intent_task = native_intent_service.status(project_id, state.intent_job.id)
        return result

    @app.exception_handler(BridgeIntentUnavailableError)
    async def unavailable_intent_handler(_request: Request, _error: BridgeIntentUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={
            "code": "bridge_intent_not_configured", "reason": "not_configured",
            "message": "当前服务未配置戏剧意图推断。可逐项填写作者意图并保存整包；不会自动配置或重试模型。",
        })

    def require_intent_service() -> tuple[ProductionBridgeIntentService, TextAdmissionService]:
        if intent_service is None or text_admission is None:
            raise BridgeIntentUnavailableError()
        return intent_service, text_admission

    def native() -> NativeBridgeIntentService:
        if native_intent_service is None:
            raise BridgeIntentUnavailableError()
        return native_intent_service

    def native_response(project_id: str) -> ProductionBridgeRuntimeState:
        with opened_project(project_id) as store:
            return response(store.production_bridge_state(), project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-intent-jobs", response_model=ProductionBridgeRuntimeState, status_code=status.HTTP_202_ACCEPTED)
    def prepare_native_intent(project_id: str, body: ProductionBridgeAcceptRequest):
        native().create(project_id, expected_revision=body.expected_proposal_revision, expected_hash=body.expected_content_hash)
        return native_response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-intent-jobs/{job_id}/send", response_model=ProductionBridgeRuntimeState)
    def send_native_intent(project_id: str, job_id: str):
        try:
            native().send(project_id, job_id)
        except ImageJobError as error:
            if error.code not in {"image_dispatch_outcome_unknown", "image_dispatch_wake_unconfirmed"}:
                raise
        return native_response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-intent-jobs/{job_id}/check", response_model=ProductionBridgeRuntimeState)
    def check_native_intent(project_id: str, job_id: str):
        native().check(project_id, job_id)
        return native_response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-intent-jobs/{job_id}/cancel", response_model=ProductionBridgeRuntimeState)
    def cancel_native_intent(project_id: str, job_id: str):
        native().cancel(project_id, job_id)
        return native_response(project_id)

    @app.get("/api/v2/projects/{project_id}/production-bridge/native-intent-jobs/{job_id}/report", response_class=HTMLResponse)
    def native_intent_report(project_id: str, job_id: str):
        return HTMLResponse(native().report(project_id, job_id), headers={
            "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;",
            "X-Content-Type-Options": "nosniff",
        })

    @app.get("/api/v2/projects/{project_id}/production-bridge", response_model=ProductionBridgeRuntimeState)
    def get_production_bridge(project_id: str) -> ProductionBridgeState:
        if intent_service is not None:
            intent_service.inspect(project_id)
        return native_response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/proposals", response_model=ProductionBridgeRuntimeState)
    def prepare_production_bridge(project_id: str, body: ProductionBridgePrepareRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.prepare_production_bridge(body), project_id)

    @app.put("/api/v2/projects/{project_id}/production-bridge/proposals/intent", response_model=ProductionBridgeRuntimeState)
    def update_production_bridge_intent(project_id: str, body: ProductionBridgeIntentUpdateRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.update_production_bridge_intent_package(body), project_id)

    @app.put("/api/v2/projects/{project_id}/production-bridge/proposals/presentation", response_model=ProductionBridgeRuntimeState)
    def update_production_presentation(project_id: str, body: ProductionPresentationUpdateRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.update_production_bridge_presentation(body), project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/accept", response_model=ProductionBridgeRuntimeState)
    def accept_production_bridge(project_id: str, body: ProductionBridgeAcceptRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.accept_production_bridge(body), project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/intent-jobs", response_model=ProductionBridgeRuntimeState, status_code=status.HTTP_202_ACCEPTED)
    def generate_bridge_intent(project_id: str, body: ProductionBridgeIntentGenerateRequest, request: Request) -> ProductionBridgeState:
        service, admission = require_intent_service()
        snapshot = admission.provider_snapshot(body.provider_profile_id)
        session_key = admission.text_submission_session_key(snapshot, request)
        service.create(project_id, expected_revision=body.expected_proposal_revision,
                       expected_hash=body.expected_content_hash, profile_snapshot=snapshot,
                       session_api_key=session_key)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state(), project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/intent-jobs/{job_id}/resume", response_model=ProductionBridgeRuntimeState, status_code=status.HTTP_202_ACCEPTED)
    def resume_bridge_intent(project_id: str, job_id: str, request: Request) -> ProductionBridgeState:
        service, admission = require_intent_service()
        with opened_project(project_id) as store:
            snapshot = store.repository.production_bridge_intent.load_job(project_id, job_id)["profile"]
        session_key = admission.text_submission_session_key(snapshot, request)
        service.submit(project_id, job_id, session_api_key=session_key)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state(), project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/intent-jobs/{job_id}/cancel", response_model=ProductionBridgeRuntimeState)
    def cancel_bridge_intent(project_id: str, job_id: str) -> ProductionBridgeState:
        service, _admission = require_intent_service()
        service.cancel(project_id, job_id)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state(), project_id)
