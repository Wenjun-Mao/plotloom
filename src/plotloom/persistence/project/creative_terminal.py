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
