"""Retained stage metadata for terminal specialist reconciliation only."""

from ...creative_handoff_contracts import (
    CreativeHandoffError,
    CreativeHandoffRequest,
    CreativeStage,
)
from ...exceptions import NotFoundError
from ..schema import (
    ArtCandidateRow,
    CastCandidateRow,
    ScriptCandidateRow,
    SourceOutlineCandidateRow,
    StoryboardReviewCandidateRow,
)
from .access import ProjectPersistenceAccess
from .creative_execution_pins import execution_pin_for_candidate

CANDIDATE_ROWS = {
    "outline": SourceOutlineCandidateRow,
    "branches": SourceOutlineCandidateRow,
    "characters": CastCandidateRow,
    "art": ArtCandidateRow,
    "script": ScriptCandidateRow,
    "storyboard": StoryboardReviewCandidateRow,
}


class ProjectCreativeTerminalPersistence:
    def __init__(self, access: ProjectPersistenceAccess):
        self._access = access

    def retained_request(self, project_id: str, stage: CreativeStage, job_id: str) -> CreativeHandoffRequest:
        """Read terminal request authority from its stage row, never the package."""
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            row = session.get(CANDIDATE_ROWS[stage], job_id)
            if row is None or row.project_id != project_id or row.status not in {"cancelled", "ready", "accepted"}:
                raise NotFoundError("retained terminal creative candidate is unavailable")
            request = CreativeHandoffRequest.model_validate(row.request)
            if (request.project_id, request.stage, request.job_id) != (project_id, stage, job_id):
                raise CreativeHandoffError("request_identity_mismatch", "retained creative request does not match its project, stage and job")
            execution_pin_for_candidate(session, request)
            return request

    def run_request(self, project_id, stage, job_id):
        """Exact original run request, including a prepared inactive attempt."""
        from ...autopilot_contracts import OperationScope
        from .autopilot_authority import require_machine_scope
        require_machine_scope(self._access, OperationScope.EVIDENCE)
        with self._access.leases.read() as session:
            row = session.get(CANDIDATE_ROWS[stage], job_id)
            if row is None or row.project_id != project_id:
                raise NotFoundError("original run creative request is unavailable")
            request = CreativeHandoffRequest.model_validate(row.request)
            if (request.project_id, request.stage, request.job_id) != (project_id, stage, job_id):
                raise CreativeHandoffError("request_identity_mismatch", "original run request identity changed")
            execution_pin_for_candidate(session, request)
            return request

    def retain_run_receipt(self, project_id, delivery):
        """Retain validated late evidence without readiness, adoption or heads."""
        from ...autopilot_contracts import OperationScope
        from plotloom.contract_identity import utc_now
        from .autopilot_authority import require_machine_scope
        require_machine_scope(self._access, OperationScope.EVIDENCE)
        request = delivery.request
        with self._access.leases.lifecycle_write() as session:
            row = session.get(CANDIDATE_ROWS[request.stage], request.job_id)
            if row is None or row.project_id != project_id or row.request != request.model_dump(mode="json", by_alias=True):
                raise CreativeHandoffError("delivery_identity_mismatch", "late receipt differs from retained run request")
            if row.manifest_hash is not None:
                if row.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "late receipt cannot replace native evidence")
                return
            field = {"outline": "outline", "branches": "outline", "characters": "cast", "art": "art", "script": "script", "storyboard": "storyboard"}[request.stage]
            row.manifest_hash = delivery.manifest_hash
            row.delivery_id = delivery.manifest.delivery_id
            setattr(row, field, delivery.candidate)
            row.report_html = delivery.report.decode("utf-8")
            row.delivered_at = utc_now()
