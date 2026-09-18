"""F2A routes: prepare/copy, refresh, ordinary review, and explicit cast acceptance."""
from __future__ import annotations
from typing import Any, Callable
from uuid import uuid4
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from ..cast_contracts import CastAcceptRequest, CastBinding, CastCandidate, CastCandidatePreparation, CastReopenRequest, CastReviewState
from ..creative_handoff_contracts import CreativeHandoffRequest

def register_project_folder_cast_routes(app: FastAPI, opened_project: Callable[[str], Any]) -> None:
    @app.get("/api/v2/projects/{project_id}/cast", response_model=CastReviewState)
    def get_cast(project_id: str) -> CastReviewState:
        with opened_project(project_id) as store: return store.cast_state()

    @app.post("/api/v2/projects/{project_id}/cast/candidates", response_model=CastCandidatePreparation, status_code=status.HTTP_201_CREATED)
    def prepare_cast(project_id: str) -> CastCandidatePreparation:
        with opened_project(project_id) as store:
            source=store.source_outline_state()
            if source.source is None or source.accepted_outline is None or source.accepted_section_map is None or source.outline_status != "accepted" or source.section_map_status != "current":
                raise HTTPException(status_code=409, detail="accept current source, outline, and section map before preparing cast")
            mapping=source.accepted_section_map
            binding=CastBinding(source_revision=source.source.revision, source_content_hash=source.source.content_hash,
                outline_revision=source.accepted_outline.revision, outline_content_hash=source.accepted_outline.content_hash,
                section_map_revision=mapping.revision, section_map_content_hash=mapping.content_hash, section_ids=[item.section_id for item in mapping.mapping.sections])
            cast=store.cast_state().accepted_cast
            request=CreativeHandoffRequest(job_id=f"ch_{uuid4().hex}", project_id=project_id, section_id="shared-cast", stage="characters",
                expected_stage_revision=cast.revision if cast else 0, source=source.source.material.model_dump(mode="json",by_alias=True),
                input_artifacts={"outline.json":source.accepted_outline.outline, "section-map.json":mapping.mapping.model_dump(mode="json",by_alias=True)},
                creative_brief="Create one upstream-shaped cast.json candidate for the accepted source, outline, and stable section context. Shared characters are authored once; preserve stable character IDs and make section presence/context explicit. This is a candidate only, not voice evidence, media generation, or project canon.")
            candidate=store.prepare_cast_candidate(request,binding); paths=store.creative_handoff_exchange().write_package(request)
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
