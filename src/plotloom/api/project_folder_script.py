"""F4 routes: one frozen whole-pilot handoff and section-scoped script edits."""
from __future__ import annotations
from typing import Any, Callable
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from ..script_contracts import ScriptAcceptRequest, ScriptCandidate, ScriptCandidatePreparation, ScriptReopenRequest, ScriptReviewState, ScriptSectionSaveRequest


def register_project_folder_script_routes(app: FastAPI, opened_project: Callable[[str], Any]) -> None:
    def preparation(store: Any, candidate: ScriptCandidate, request: Any) -> ScriptCandidatePreparation:
        paths = store.creative_handoff_exchange().write_package(request)
        return ScriptCandidatePreparation.model_validate(candidate.model_dump(mode="python", by_alias=False) | {"package_path": paths["packagePath"], "delivery_path": paths["deliveryPath"], "assignment": f"Plotloom F4 script assignment for {request.job_id}: read {paths['packagePath']}/request.json and COPY_ASSIGNMENT.txt. Write only script.json, report.html, and completion.json under {paths['deliveryPath']}. This cannot accept or alter project canon."})

    @app.get("/api/v2/projects/{project_id}/script", response_model=ScriptReviewState)
    def get_script(project_id: str) -> ScriptReviewState:
        with opened_project(project_id) as store: return store.script_state()

    @app.post("/api/v2/projects/{project_id}/script/candidates", response_model=ScriptCandidatePreparation, status_code=status.HTTP_201_CREATED)
    def prepare_script(project_id: str) -> ScriptCandidatePreparation:
        with opened_project(project_id) as store:
            candidate, request = store.prepare_script_candidate(f"ch_{uuid4().hex}")
            return preparation(store, candidate, request)

    @app.get("/api/v2/projects/{project_id}/script/candidates/{job_id}/handoff", response_model=ScriptCandidatePreparation)
    def recover_script_handoff(project_id: str, job_id: str) -> ScriptCandidatePreparation:
        with opened_project(project_id) as store:
            candidate = store.script_state().candidate
            if candidate is None or candidate.job_id != job_id or candidate.status != "prepared": raise HTTPException(status_code=409, detail="only the current prepared script handoff can be recovered")
            return preparation(store, candidate, store.script_candidate_request(job_id))

    @app.post("/api/v2/projects/{project_id}/script/candidates/{job_id}/refresh", response_model=ScriptCandidate)
    def refresh_script(project_id: str, job_id: str) -> ScriptCandidate:
        with opened_project(project_id) as store:
            delivery = store.creative_handoff_exchange().read_delivery(store.script_candidate_request(job_id))
            if delivery is None: raise HTTPException(status_code=409, detail="the specialist delivery is not present yet")
            return store.admit_script_delivery(delivery)

    @app.post("/api/v2/projects/{project_id}/script/candidates/{job_id}/cancel", response_model=ScriptReviewState)
    def cancel_script(project_id: str, job_id: str) -> ScriptReviewState:
        with opened_project(project_id) as store: return store.cancel_script_candidate(job_id)

    @app.get("/api/v2/projects/{project_id}/script/candidates/{job_id}/report", response_class=HTMLResponse)
    def script_report(project_id: str, job_id: str) -> HTMLResponse:
        with opened_project(project_id) as store: report = store.script_candidate_report(job_id)
        return HTMLResponse(report, headers={"Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;", "X-Content-Type-Options": "nosniff"})

    @app.post("/api/v2/projects/{project_id}/script/accept", response_model=ScriptReviewState)
    def accept_script(project_id: str, body: ScriptAcceptRequest) -> ScriptReviewState:
        with opened_project(project_id) as store: return store.accept_script_candidate(body)

    @app.post("/api/v2/projects/{project_id}/script/reopen", response_model=ScriptReviewState)
    def reopen_script(project_id: str, body: ScriptReopenRequest) -> ScriptReviewState:
        with opened_project(project_id) as store: return store.reopen_script(body)

    @app.post("/api/v2/projects/{project_id}/script/sections/save", response_model=ScriptReviewState)
    def save_script_section(project_id: str, body: ScriptSectionSaveRequest) -> ScriptReviewState:
        with opened_project(project_id) as store: return store.save_script_section(body)
