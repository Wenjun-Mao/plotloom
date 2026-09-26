"""F1A project-folder routes for source, candidate review, and acceptance."""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse

from ..creative_handoff_contracts import CreativeHandoffRequest
from ..source_outline_contracts import (
    OutlineAcceptRequest,
    OutlineCandidate,
    OutlineCandidatePreparation,
    OutlineReopenRequest,
    SectionMapGraphInstallRequest,
    SectionMapSaveRequest,
    SourceOutlineReviewState,
    SourceSaveRequest,
)


def _outline_assignment(candidate: OutlineCandidate, paths: dict[str, str]) -> OutlineCandidatePreparation:
    payload = candidate.model_dump(mode="python", by_alias=False)
    payload.update(
        package_path=paths["packagePath"],
        delivery_path=paths["deliveryPath"],
        assignment=(
            f"请执行这份 Plotloom 大纲任务（{candidate.job_id}）。\n"
            f"先阅读 {paths['packagePath']}/request.json，\n"
            f"并遵循 {paths['packagePath']}/COPY_ASSIGNMENT.txt 中的要求。\n"
            "只交付候选大纲、派生报告和完成回执，文件名、格式及验证要求以任务文件为准。\n"
            f"所有交付文件只写入 {paths['deliveryPath']}。\n"
            "不要替我接受大纲，不要修改已确认内容或项目状态。完成后报告交付位置和验证结果。"
        ),
    )
    return OutlineCandidatePreparation.model_validate(payload)


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
                    "author source. Preserve the adaptation intent and any supplied attribution "
                    "or rights metadata without inventing missing claims. Do not claim approval, "
                    "rights clearance, or edit project canon."
                ),
            )
            candidate = store.prepare_outline_candidate(request)
            exchange = store.creative_handoff_exchange()
            paths = exchange.write_package(request)
            # The assignment is deliberately returned only after project state
            # reserves the exact job identity; the specialist cannot choose it.
            return _outline_assignment(candidate, paths)

    @app.get(
        "/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/assignment",
        response_model=OutlineCandidatePreparation,
    )
    def get_source_outline_assignment(project_id: str, job_id: str) -> OutlineCandidatePreparation:
        with opened_project(project_id) as store:
            candidate = store.source_outline_state().candidate
            if candidate is None or candidate.job_id != job_id:
                raise HTTPException(status_code=404, detail="outline handoff not found")
            if candidate.status != "prepared":
                raise HTTPException(status_code=409, detail="outline handoff is no longer awaiting execution")
            request = store.outline_candidate_request(job_id)
            paths = store.creative_handoff_exchange().verified_package_paths(request)
            return _outline_assignment(candidate, paths)

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

    @app.post(
        "/api/v2/projects/{project_id}/source-outline/candidates/{job_id}/cancel",
        response_model=SourceOutlineReviewState,
    )
    def cancel_source_outline_candidate(
        project_id: str, job_id: str
    ) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.cancel_outline_candidate(job_id)

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
                "Content-Security-Policy": (
                    "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; "
                    "style-src 'unsafe-inline'; img-src data:; connect-src 'none'; "
                    "form-action 'none'; base-uri 'none'; frame-src 'none'; "
                    "object-src 'none'; frame-ancestors 'self';"
                ),
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
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

    @app.put(
        "/api/v2/projects/{project_id}/source-outline/section-map",
        response_model=SourceOutlineReviewState,
    )
    def save_source_outline_section_map(
        project_id: str, body: SectionMapSaveRequest
    ) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.save_section_map(body)

    @app.post(
        "/api/v2/projects/{project_id}/source-outline/section-map/install-graph",
        response_model=SourceOutlineReviewState,
    )
    def install_source_outline_section_map_graph(
        project_id: str, body: SectionMapGraphInstallRequest
    ) -> SourceOutlineReviewState:
        with opened_project(project_id) as store:
            return store.install_section_map_graph(body)
