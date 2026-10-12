"""Stage-specific views over schema-neutral durable bridge attempts."""
from sqlalchemy import or_, select

from ...creative_handoff_contracts import CreativeHandoffRequest
from ...creative_handoff_exchange import request_hash
from ...native_bridge_presentation_contract import native_presentation_suggestions
from ...production_bridge_contracts import ProductionBridgeIntentJob
from ...production_presentation import PresentationCandidate, PresentationUpdate
from ..schema.project_production_bridge import ProductionBridgeIntentJobRow


def bridge_job_views(session, project_id, proposal, status, stale):
    def latest(condition):
        return session.scalar(select(ProductionBridgeIntentJobRow).where(
            ProductionBridgeIntentJobRow.project_id == project_id, condition,
        ).order_by(ProductionBridgeIntentJobRow.created_at.desc(), ProductionBridgeIntentJobRow.id.desc()).limit(1))

    def view(job):
        if job is None:
            return None
        return ProductionBridgeIntentJob(id=job.id, transport=job.transport, status=job.status,
            proposal_revision=job.proposal_revision, proposal_content_hash=job.proposal_content_hash,
            profile_id=job.profile_snapshot.get("profileId"), profile_version=job.profile_snapshot.get("profileVersion"),
            prompt_version=job.prompt_trace["prompt_version"], created_at=job.created_at, updated_at=job.updated_at,
            error_code=job.error_code, error_message=job.error_message, result_proposal_revision=job.result_proposal_revision,
            provider_request_id=job.provider_request_id, response_hash=job.response_hash)

    intent = latest(or_(ProductionBridgeIntentJobRow.transport == "text_api",
        ProductionBridgeIntentJobRow.native_request["stage"].as_string() == "bridge-intent"))
    presentation = latest(ProductionBridgeIntentJobRow.native_request["stage"].as_string() == "bridge-presentation")
    presentation_view, candidate = view(presentation), None
    if presentation and presentation.status == "ready":
        current = (proposal is not None and status != "accepted" and not stale
            and proposal.revision == presentation.proposal_revision
            and proposal.content_hash == presentation.proposal_content_hash)
        if current:
            request = CreativeHandoffRequest.model_validate(presentation.native_request)
            suggestions = native_presentation_suggestions(request, presentation.candidate)
            candidate = PresentationCandidate(job_id=presentation.id, proposal_revision=presentation.proposal_revision,
                proposal_content_hash=presentation.proposal_content_hash, source_hash=proposal.presentation.source_hash,
                entries=[PresentationUpdate(id=entry.id, spans=entry.spans) for entry in suggestions.entries],
                provenance={"requestHash": request_hash(request), "responseHash": presentation.response_hash,
                    "manifestHash": presentation.response_evidence["manifestHash"],
                    "executorProvenance": presentation.response_evidence["manifest"]["executorProvenance"]})
        else:
            presentation_view.status = "stale"
    return view(intent), presentation_view, candidate
