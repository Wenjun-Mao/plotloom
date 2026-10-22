"""Suggestion evidence does not advance or project an author-owned proposal."""
from ...creative_handoff_contracts import CreativeHandoffRequest
from ...domain import utc_now
from ...exceptions import InvalidTransitionError
from ...native_bridge_presentation_contract import native_presentation_suggestions


class ProductionBridgePresentationCandidatePersistence:
    def finish_presentation(self, project_id: str, job_id: str, *, candidate: dict,
                            response_evidence: dict, response_hash: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            job = self._job(session, project_id, job_id)
            request = CreativeHandoffRequest.model_validate(job.native_request)
            validated = native_presentation_suggestions(request, candidate)
            if job.transport != "codex_native" or request.project_id != project_id or request.job_id != job_id:
                raise InvalidTransitionError("presentation candidate identity differs from its job")
            if job.status not in {"dispatched", "cancelled", "outcome_unknown", "stale"}:
                return
            job.response_evidence, job.response_hash = response_evidence, response_hash
            job.candidate = validated.model_dump(mode="json", by_alias=True)
            job.updated_at = utc_now()
            if job.status in {"cancelled", "stale"}:
                return
            head = self._bridge._head(session, project_id)
            row = self._revision(session, project_id, job.proposal_revision)
            if (head.status == "accepted" or head.revision != job.proposal_revision
                    or row.content_hash != job.proposal_content_hash
                    or self._bridge._proposal_stale(session, project_id, row)):
                job.status = "stale"
            else:
                job.status = "ready"
