"""F5A routes for source-bound upstream storyboard review revisions."""
from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse

from ..storyboard_review_contracts import (
    StoryboardReviewAcceptRequest, StoryboardReviewCandidate,
    StoryboardReviewCandidatePreparation, StoryboardReviewState,
)


def register_project_folder_storyboard_review_routes(app: FastAPI, opened_project: Callable[[str], Any]) -> None:
    def preparation(store: Any, candidate: StoryboardReviewCandidate, request: Any) -> StoryboardReviewCandidatePreparation:
        paths = store.creative_handoff_exchange().write_package(request)
        return StoryboardReviewCandidatePreparation.model_validate(candidate.model_dump(mode="python", by_alias=False) | {"package_path": paths["packagePath"], "delivery_path": paths["deliveryPath"], "assignment": f"Plotloom F5A storyboard review assignment for {request.job_id}: read {paths['packagePath']}/request.json and COPY_ASSIGNMENT.txt. Write only storyboard.json, report.html, and completion.json under {paths['deliveryPath']}. This cannot install canonical shots, media, or approvals."})

    @app.get("/api/v2/projects/{project_id}/storyboard-source-review", response_model=StoryboardReviewState)
    def get_storyboard_review(project_id: str) -> StoryboardReviewState:
        with opened_project(project_id) as store:
            return store.storyboard_review_state()

    @app.post("/api/v2/projects/{project_id}/storyboard-source-review/candidates", response_model=StoryboardReviewCandidatePreparation, status_code=status.HTTP_201_CREATED)
    def prepare_storyboard_review(project_id: str) -> StoryboardReviewCandidatePreparation:
        with opened_project(project_id) as store:
            candidate, request = store.prepare_storyboard_review_candidate(f"ch_{uuid4().hex}")
            return preparation(store, candidate, request)

    @app.get("/api/v2/projects/{project_id}/storyboard-source-review/candidates/{job_id}/handoff", response_model=StoryboardReviewCandidatePreparation)
    def recover_storyboard_review_handoff(project_id: str, job_id: str) -> StoryboardReviewCandidatePreparation:
        with opened_project(project_id) as store:
            candidate = store.storyboard_review_state().candidate
            if candidate is None or candidate.job_id != job_id or candidate.status != "prepared":
                raise HTTPException(status_code=409, detail="only the current prepared storyboard review handoff can be recovered")
            return preparation(store, candidate, store.storyboard_review_candidate_request(job_id))

    @app.post("/api/v2/projects/{project_id}/storyboard-source-review/candidates/{job_id}/refresh", response_model=StoryboardReviewCandidate)
    def refresh_storyboard_review(project_id: str, job_id: str) -> StoryboardReviewCandidate:
        with opened_project(project_id) as store:
            delivery = store.creative_handoff_exchange().read_delivery(store.storyboard_review_candidate_request(job_id))
            if delivery is None:
                raise HTTPException(status_code=409, detail="the specialist delivery is not present yet")
            return store.admit_storyboard_review_delivery(delivery)

    @app.post("/api/v2/projects/{project_id}/storyboard-source-review/candidates/{job_id}/cancel", response_model=StoryboardReviewState)
    def cancel_storyboard_review(project_id: str, job_id: str) -> StoryboardReviewState:
        with opened_project(project_id) as store:
            return store.cancel_storyboard_review_candidate(job_id)

    @app.get("/api/v2/projects/{project_id}/storyboard-source-review/candidates/{job_id}/report", response_class=HTMLResponse)
    def storyboard_review_report(project_id: str, job_id: str) -> HTMLResponse:
        with opened_project(project_id) as store:
            report = store.storyboard_review_candidate_report(job_id)
        return HTMLResponse(report, headers={"Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;", "X-Content-Type-Options": "nosniff"})

    @app.post("/api/v2/projects/{project_id}/storyboard-source-review/accept", response_model=StoryboardReviewState)
    def accept_storyboard_review(project_id: str, body: StoryboardReviewAcceptRequest) -> StoryboardReviewState:
        with opened_project(project_id) as store:
            return store.accept_storyboard_review_candidate(body)
