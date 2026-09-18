"""F3A routes: frozen art handoff, inspection, explicit acceptance, and reopen."""
from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse

from ..art_contracts import ArtAcceptRequest, ArtCandidate, ArtCandidatePreparation, ArtReopenRequest, ArtReviewState, ArtSaveRequest
from ..image_job_contracts import (
    ArtReferenceProposalCancellationRequest,
    ArtReferenceProposalRequest,
    ImageJobError,
)
from ..managed_media import publish_import


def register_project_folder_art_routes(app: FastAPI, opened_project: Callable[[str], Any]) -> None:
    def preparation(store: Any, candidate: ArtCandidate, request: Any) -> ArtCandidatePreparation:
        paths = store.creative_handoff_exchange().write_package(request)
        return ArtCandidatePreparation.model_validate(candidate.model_dump(mode="python", by_alias=False) | {"package_path": paths["packagePath"], "delivery_path": paths["deliveryPath"], "assignment": f"Plotloom art assignment for {request.job_id}: read {paths['packagePath']}/request.json and follow its COPY_ASSIGNMENT.txt. Write only art.json, report.html, and completion.json under {paths['deliveryPath']}. This cannot accept or alter project canon."})

    @app.get("/api/v2/projects/{project_id}/art", response_model=ArtReviewState)
    def get_art(project_id: str) -> ArtReviewState:
        with opened_project(project_id) as store: return store.art_state()

    @app.post("/api/v2/projects/{project_id}/art/candidates", response_model=ArtCandidatePreparation, status_code=status.HTTP_201_CREATED)
    def prepare_art(project_id: str) -> ArtCandidatePreparation:
        with opened_project(project_id) as store:
            candidate, request = store.prepare_art_candidate(f"ch_{uuid4().hex}")
            return preparation(store, candidate, request)

    @app.get("/api/v2/projects/{project_id}/art/candidates/{job_id}/handoff", response_model=ArtCandidatePreparation)
    def recover_art_handoff(project_id: str, job_id: str) -> ArtCandidatePreparation:
        with opened_project(project_id) as store:
            state = store.art_state()
            candidate = state.candidate
            if candidate is None or candidate.job_id != job_id or candidate.status != "prepared":
                raise HTTPException(status_code=409, detail="only the current prepared art handoff can be recovered")
            return preparation(store, candidate, store.art_candidate_request(job_id))

    @app.post("/api/v2/projects/{project_id}/art/candidates/{job_id}/refresh", response_model=ArtCandidate)
    def refresh_art(project_id: str, job_id: str) -> ArtCandidate:
        with opened_project(project_id) as store:
            delivery = store.creative_handoff_exchange().read_delivery(store.art_candidate_request(job_id))
            if delivery is None: raise HTTPException(status_code=409, detail="the specialist delivery is not present yet")
            return store.admit_art_delivery(delivery)

    @app.post("/api/v2/projects/{project_id}/art/candidates/{job_id}/cancel", response_model=ArtReviewState)
    def cancel_art(project_id: str, job_id: str) -> ArtReviewState:
        with opened_project(project_id) as store: return store.cancel_art_candidate(job_id)

    @app.get("/api/v2/projects/{project_id}/art/candidates/{job_id}/report", response_class=HTMLResponse)
    def art_report(project_id: str, job_id: str) -> HTMLResponse:
        with opened_project(project_id) as store: report = store.art_candidate_report(job_id)
        return HTMLResponse(report, headers={"Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:;", "X-Content-Type-Options": "nosniff"})

    @app.post("/api/v2/projects/{project_id}/art/accept", response_model=ArtReviewState)
    def accept_art(project_id: str, body: ArtAcceptRequest) -> ArtReviewState:
        with opened_project(project_id) as store: return store.accept_art_candidate(body)

    @app.post("/api/v2/projects/{project_id}/art/reopen", response_model=ArtReviewState)
    def reopen_art(project_id: str, body: ArtReopenRequest) -> ArtReviewState:
        with opened_project(project_id) as store: return store.reopen_art(body)

    @app.post("/api/v2/projects/{project_id}/art/save", response_model=ArtReviewState)
    def save_art(project_id: str, body: ArtSaveRequest) -> ArtReviewState:
        with opened_project(project_id) as store: return store.save_reopened_art(body)

    @app.get("/api/v2/projects/{project_id}/art-reference-proposals")
    def get_art_reference_proposals(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {"configured": True, "proposals": store.media.list_art_reference_proposals(project_id)}

    @app.post("/api/v2/projects/{project_id}/art-reference-proposals", status_code=status.HTTP_201_CREATED)
    def prepare_art_reference_proposal(project_id: str, body: ArtReferenceProposalRequest) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.prepare_art_reference_proposal(
                project_id, **body.model_dump(mode="python", by_alias=False)
            )

    @app.post("/api/v2/projects/{project_id}/art-reference-proposals/{proposal_id}/copy")
    def copy_art_reference_proposal(project_id: str, proposal_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            source = store.media.art_reference_proposal_package_sources(project_id, proposal_id)
            proposal = source["proposal"]
            package = store.image_exchange_for(proposal).write_package(
                job_id=proposal_id, request=proposal["request"], request_hash=proposal["requestHash"], references=[]
            )
            proposal = store.media.mark_art_reference_proposal_exported(project_id, proposal_id)
            return {
                "proposal": proposal,
                "assignment": f"Codex F3B {proposal['subjectType']} reference-study assignment for {proposal_id}: read {package['packagePath']}/request.json; use built-in imagegen; write JPEG/PNG outputs and completion.json only under {package['deliveryPath']}. This cannot accept art or select a production asset.",
                "packagePath": package["packagePath"], "deliveryPath": package["deliveryPath"],
            }

    @app.post("/api/v2/projects/{project_id}/art-reference-proposals/{proposal_id}/cancel")
    def cancel_art_reference_proposal(
        project_id: str, proposal_id: str, body: ArtReferenceProposalCancellationRequest,
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.cancel_art_reference_proposal(project_id, proposal_id, body.reason)

    @app.post("/api/v2/projects/{project_id}/art-reference-proposals/{proposal_id}/refresh")
    def refresh_art_reference_proposal(project_id: str, proposal_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            repository = store.media
            context = repository.art_reference_proposal_delivery_context(project_id, proposal_id)
            exchange = store.image_exchange_for(context)
            try:
                exchange.verify_package(job_id=proposal_id, request=context["request"], request_hash=context["requestHash"], references=[])
                delivery = exchange.read_delivery(
                    job_id=proposal_id, request_hash=context["requestHash"],
                    require_executor_provenance=True,
                    require_executor_pin=context["request"].get("specialistPreflight", {}).get("version") == "p1.5-pin.v1",
                    expected_executor_skill_version=context["request"].get("specialistPreflight", {}).get("skillVersion"),
                )
            except ImageJobError as error:
                if error.code not in {"image_exchange_not_configured", "image_exchange_invalid", "invalid_job_id", "delivery_manifest_secret"}:
                    repository.record_art_reference_proposal_rejection(project_id, proposal_id, error.code)
                raise
            if delivery is None:
                return {"state": "awaiting_delivery", "candidates": [], "idempotent": False}
            outputs = [{
                "filename": output.filename, "role": output.role,
                "originalHash": output.observed.content_hash, "displayHash": output.observed.display_hash,
                "mimeType": output.observed.mime_type, "byteSize": output.observed.byte_size,
                "width": output.observed.width, "height": output.observed.height,
                "content": output.content, "observed": output.observed,
            } for output in delivery.outputs]
            return repository.record_art_reference_proposal_delivery(
                project_id, proposal_id, delivery_id=delivery.manifest.delivery_id,
                manifest=delivery.manifest.model_dump(mode="json", by_alias=True), manifest_hash=delivery.manifest_hash,
                outputs=outputs, publish=lambda output: publish_import(store.artifacts, output["content"], output["observed"]),
            )
