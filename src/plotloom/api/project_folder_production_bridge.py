"""User-reachable, explicit F5 proposal review and canonical installation."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, status

from ..production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeIntentGenerateRequest, ProductionBridgeIntentUpdateRequest, ProductionBridgeState
from ..production_bridge_intent_service import ProductionBridgeIntentService
from .text_admission import TextAdmissionService


def register_project_folder_production_bridge_routes(
    app: FastAPI, opened_project: Callable[[str], Any], *,
    intent_service: ProductionBridgeIntentService | None = None,
    text_admission: TextAdmissionService | None = None,
    simulation_label: str | None = None,
) -> None:
    def response(state: ProductionBridgeState) -> ProductionBridgeState:
        return state.model_copy(update={"simulation_label": simulation_label}) if simulation_label else state

    def require_intent_service() -> tuple[ProductionBridgeIntentService, TextAdmissionService]:
        if intent_service is None or text_admission is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="bridge text inference is not configured")
        return intent_service, text_admission

    @app.get("/api/v2/projects/{project_id}/production-bridge", response_model=ProductionBridgeState)
    def get_production_bridge(project_id: str) -> ProductionBridgeState:
        if intent_service is not None:
            intent_service.inspect(project_id)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state())

    @app.post("/api/v2/projects/{project_id}/production-bridge/proposals", response_model=ProductionBridgeState)
    def prepare_production_bridge(project_id: str) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.prepare_production_bridge())

    @app.put("/api/v2/projects/{project_id}/production-bridge/proposals/intent", response_model=ProductionBridgeState)
    def update_production_bridge_intent(project_id: str, body: ProductionBridgeIntentUpdateRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.update_production_bridge_intent_package(body))

    @app.post("/api/v2/projects/{project_id}/production-bridge/accept", response_model=ProductionBridgeState)
    def accept_production_bridge(project_id: str, body: ProductionBridgeAcceptRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return response(store.accept_production_bridge(body))

    @app.post("/api/v2/projects/{project_id}/production-bridge/intent-jobs", response_model=ProductionBridgeState, status_code=status.HTTP_202_ACCEPTED)
    def generate_bridge_intent(project_id: str, body: ProductionBridgeIntentGenerateRequest, request: Request) -> ProductionBridgeState:
        service, admission = require_intent_service()
        snapshot = admission.provider_snapshot(body.provider_profile_id)
        session_key = admission.text_submission_session_key(snapshot, request)
        service.create(project_id, expected_revision=body.expected_proposal_revision,
                       expected_hash=body.expected_content_hash, profile_snapshot=snapshot,
                       session_api_key=session_key)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state())

    @app.post("/api/v2/projects/{project_id}/production-bridge/intent-jobs/{job_id}/resume", response_model=ProductionBridgeState, status_code=status.HTTP_202_ACCEPTED)
    def resume_bridge_intent(project_id: str, job_id: str, request: Request) -> ProductionBridgeState:
        service, admission = require_intent_service()
        with opened_project(project_id) as store:
            snapshot = store.repository.production_bridge_intent.load_job(project_id, job_id)["profile"]
        session_key = admission.text_submission_session_key(snapshot, request)
        service.submit(project_id, job_id, session_api_key=session_key)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state())

    @app.post("/api/v2/projects/{project_id}/production-bridge/intent-jobs/{job_id}/cancel", response_model=ProductionBridgeState)
    def cancel_bridge_intent(project_id: str, job_id: str) -> ProductionBridgeState:
        service, _admission = require_intent_service()
        service.cancel(project_id, job_id)
        with opened_project(project_id) as store:
            return response(store.production_bridge_state())
