"""F2A routes: prepare/copy, refresh, ordinary review, and explicit cast acceptance."""
from __future__ import annotations
from typing import Any, Callable
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from ..cast_contracts import CastAcceptRequest, CastCancelReopenRequest, CastCandidate, CastCandidatePreparation, CastReopenRequest, CastReviewState, CastSaveRequest

def register_project_folder_cast_routes(app: FastAPI, opened_project: Callable[[str], Any]) -> None:
    @app.get("/api/v2/projects/{project_id}/cast", response_model=CastReviewState)
    def get_cast(project_id: str) -> CastReviewState:
        with opened_project(project_id) as store: return store.cast_state()

    @app.post("/api/v2/projects/{project_id}/cast/candidates", response_model=CastCandidatePreparation, status_code=status.HTTP_201_CREATED)
    def prepare_cast(project_id: str) -> CastCandidatePreparation:
        with opened_project(project_id) as store:
            candidate, request = store.prepare_cast_candidate(f"ch_{uuid4().hex}")
            paths = store.creative_handoff_exchange().write_package(request)
            payload=candidate.model_dump(mode="python",by_alias=False)|{"package_path":paths["packagePath"],"delivery_path":paths["deliveryPath"],"assignment":f"Plotloom characters assignment for {request.job_id}: read {paths['packagePath']}/request.json and follow its COPY_ASSIGNMENT.txt. Write only cast.json, report.html, and completion.json under {paths['deliveryPath']}. This cannot accept or alter project canon."}
            return CastCandidatePreparation.model_validate(payload)

    @app.post("/api/v2/projects/{project_id}/cast/candidates/{job_id}/refresh", response_model=CastCandidate)
    def refresh_cast(project_id: str, job_id: str) -> CastCandidate:
        with opened_project(project_id) as store:
            delivery=store.creative_handoff_exchange().read_delivery(store.cast_candidate_request(job_id))
            if delivery is None: raise HTTPException(status_code=409, detail="the specialist delivery is not present yet")
            return store.admit_cast_delivery(delivery)

    @app.post("/api/v2/projects/{project_id}/cast/candidates/{job_id}/cancel", response_model=CastReviewState)
    def cancel_cast(project_id: str,job_id: str) -> CastReviewState:
        with opened_project(project_id) as store: return store.cancel_cast_candidate(job_id)

    @app.get("/api/v2/projects/{project_id}/cast/candidates/{job_id}/report", response_class=HTMLResponse)
    def cast_report(project_id: str,job_id: str) -> HTMLResponse:
        with opened_project(project_id) as store: report=store.cast_candidate_report(job_id)
        return HTMLResponse(report,headers={"Content-Security-Policy":"sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;", "X-Content-Type-Options":"nosniff"})

    @app.post("/api/v2/projects/{project_id}/cast/accept",response_model=CastReviewState)
    def accept_cast(project_id: str,body: CastAcceptRequest) -> CastReviewState:
        with opened_project(project_id) as store: return store.accept_cast_candidate(body)

    @app.post("/api/v2/projects/{project_id}/cast/reopen",response_model=CastReviewState)
    def reopen_cast(project_id: str,body: CastReopenRequest) -> CastReviewState:
        with opened_project(project_id) as store: return store.reopen_cast(body)

    @app.post("/api/v2/projects/{project_id}/cast/reopen/cancel", response_model=CastReviewState)
    def cancel_reopened_cast(project_id: str, body: CastCancelReopenRequest) -> CastReviewState:
        with opened_project(project_id) as store: return store.cancel_reopened_cast(body)

    @app.post("/api/v2/projects/{project_id}/cast/save", response_model=CastReviewState)
    def save_reopened_cast(project_id: str, body: CastSaveRequest) -> CastReviewState:
        with opened_project(project_id) as store: return store.save_reopened_cast(body)
