"""Explicit presentation suggestion operations; no automatic creative acceptance."""
from fastapi import status
from fastapi.responses import HTMLResponse

from ..image_job_contracts import ImageJobError
from ..production_bridge_contracts import ProductionBridgeAcceptRequest
from .production_bridge_state import ProductionBridgeRuntimeState


def register_native_presentation_routes(app, service, response):
    @app.post("/api/v2/projects/{project_id}/production-bridge/native-presentation-jobs", response_model=ProductionBridgeRuntimeState, status_code=status.HTTP_202_ACCEPTED)
    def prepare(project_id: str, body: ProductionBridgeAcceptRequest):
        service.create(project_id, expected_revision=body.expected_proposal_revision, expected_hash=body.expected_content_hash)
        return response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-presentation-jobs/{job_id}/send", response_model=ProductionBridgeRuntimeState)
    def send(project_id: str, job_id: str):
        try:
            service.send(project_id, job_id)
        except ImageJobError as error:
            if error.code not in {"image_dispatch_outcome_unknown", "image_dispatch_wake_unconfirmed"}:
                raise
        return response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-presentation-jobs/{job_id}/check", response_model=ProductionBridgeRuntimeState)
    def check(project_id: str, job_id: str):
        service.check(project_id, job_id)
        return response(project_id)

    @app.post("/api/v2/projects/{project_id}/production-bridge/native-presentation-jobs/{job_id}/cancel", response_model=ProductionBridgeRuntimeState)
    def cancel(project_id: str, job_id: str):
        service.cancel(project_id, job_id)
        return response(project_id)

    @app.get("/api/v2/projects/{project_id}/production-bridge/native-presentation-jobs/{job_id}/report", response_class=HTMLResponse)
    def report(project_id: str, job_id: str):
        return HTMLResponse(service.report(project_id, job_id), headers={
            "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;",
            "X-Content-Type-Options": "nosniff",
        })
