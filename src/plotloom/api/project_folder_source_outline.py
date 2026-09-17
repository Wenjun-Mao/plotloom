"""F1A project-folder routes for source, candidate review, and acceptance."""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse

from ..creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ..source_outline_contracts import (
    OutlineAcceptRequest,
    OutlineCandidate,
    OutlineCandidatePreparation,
    OutlineReopenRequest,
    SourceOutlineReviewState,
    SourceSaveRequest,
)


def register_project_folder_source_outline_routes(
    app: FastAPI, opened_project: Callable[[str], Any]
) -> None:
    """Expose the exact F1A manual-review lifecycle, without a job runner."""

    @app.get(
        "/api/v2/projects/{project_id}/source-outline",
        response_model=SourceOutlineReviewState,
    )
    def get_source_outline(project_id: str) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.source_outline_state()

    @app.put(
        "/api/v2/projects/{project_id}/source-outline/source",
        response_model=SourceOutlineReviewState,
    )
    def save_source_outline_source(
        project_id: str, body: SourceSaveRequest
    ) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.save_source_material(
                expected_source_revision=body.expected_source_revision,
                material=body.material,
            )

    @app.post(
        "/api/v2/projects/{project_id}/source-outline/candidates",
        response_model=OutlineCandidatePreparation,
        status_code=status.HTTP_201_CREATED,
    )
    def prepare_source_outline_candidate(project_id: str) -> OutlineCandidatePreparation:
        with opened_project(project_id) as store:
            state = store.source_outline_state()
            if state.source is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="save an accepted source before preparing an outline candidate",
                )
            request = CreativeHandoffRequest(
                job_id=f"ch_{uuid4().hex}",
                project_id=project_id,
                section_id="story",
                stage="outline",
                expected_stage_revision=state.accepted_outline.revision if state.accepted_outline else 0,
                source=state.source.material.model_dump(mode="json", by_alias=True),
                input_artifacts={},
                creative_brief=(
                    "Create one reviewable upstream outline.json candidate from the accepted "
                    "author source. Preserve source attribution and adaptation intent as supplied; "
                    "do not claim approval or edit project canon."
                ),
            )
            candidate = store.prepare_outline_candidate(request)
            exchange = store.creative_handoff_exchange()
            paths = exchange.write_package(request)
            # The assignment is deliberately returned only after project state
            # reserves the exact job identity; the specialist cannot choose it.
            candidate_payload = candidate.model_dump(mode="python", by_alias=False)
            candidate_payload["package_path"] = paths["packagePath"]
            candidate_payload["delivery_path"] = paths["deliveryPath"]
            candidate_payload["assignment"] = (
                f"Plotloom outline assignment for {request.job_id}: read "
                f"{paths['packagePath']}/request.json and follow its COPY_ASSIGNMENT.txt. "
                f"Write only the candidate, derived report, and completion receipt under "
                f"{paths['deliveryPath']}. This cannot accept or alter project canon."
            )
            return OutlineCandidatePreparation.model_validate(candidate_payload)

    @app.post(
        "/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/refresh",
        response_model=OutlineCandidate,
    )
    def refresh_source_outline_candidate(project_id: str, job_id: str) -> OutlineCandidate:
        with opened_project(project_id) as store:
            request = store.outline_candidate_request(job_id)
            delivery = store.creative_handoff_exchange().read_delivery(request)
            if delivery is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="the specialist delivery is not present yet",
                )
            return store.admit_outline_delivery(delivery)

    @app.get(
        "/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/report",
        response_class=HTMLResponse,
    )
    def get_source_outline_candidate_report(project_id: str, job_id: str) -> HTMLResponse:
        with opened_project(project_id) as store:
            report = store.outline_candidate_report(job_id)
        return HTMLResponse(
            report,
            headers={
                "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.post(
        "/api/v2/projects/{project_id}/source-outline/accept",
        response_model=SourceOutlineReviewState,
    )
    def accept_source_outline_candidate(
        project_id: str, body: OutlineAcceptRequest
    ) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.accept_outline_candidate(body)

    @app.post(
        "/api/v2/projects/{project_id}/source-outline/reopen",
        response_model=SourceOutlineReviewState,
    )
    def reopen_source_outline(
        project_id: str, body: OutlineReopenRequest
    ) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.reopen_outline(body)
