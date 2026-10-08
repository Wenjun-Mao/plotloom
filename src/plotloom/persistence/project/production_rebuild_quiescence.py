"""Refuse authority changes while current external work can still deliver."""
from sqlalchemy import select

from ...exceptions import InvalidTransitionError
from ..schema import (
    ArtCandidateRow,
    ArtReferenceProposalRow,
    CastCandidateRow,
    CharacterReferenceProposalRow,
    ImageJobRow,
    ProductionBridgeIntentJobRow,
    ScriptCandidateRow,
    SourceOutlineCandidateRow,
    StoryboardReviewCandidateRow,
    VideoJobRow,
)


def assert_production_quiescent(access, session, project_id):
    if access.guards.busy(session, project_id):
        raise InvalidTransitionError("active project work prevents production rebuild")
    owners = (
        (ProductionBridgeIntentJobRow, "status", ("queued", "dispatched", "outcome_unknown")),
        (VideoJobRow, "state", ("prepared", "dispatching", "submitted", "retrieve_needed", "outcome_unknown")),
        (ImageJobRow, "state", ("prepared", "exported")),
        (CharacterReferenceProposalRow, "state", ("prepared", "exported")),
        (ArtReferenceProposalRow, "state", ("prepared", "exported")),
        *((owner, "status", ("prepared",)) for owner in (
            SourceOutlineCandidateRow, CastCandidateRow, ArtCandidateRow,
            ScriptCandidateRow, StoryboardReviewCandidateRow,
        )),
    )
    for owner, field, states in owners:
        if session.scalar(select(owner).where(
            owner.project_id == project_id, getattr(owner, field).in_(states),
        ).limit(1)) is not None:
            raise InvalidTransitionError("unresolved publication or execution prevents production rebuild")
