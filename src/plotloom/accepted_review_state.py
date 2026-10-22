"""Accepted evidence never inherits a replacement candidate's authority."""
from typing import Literal

from .domain import CamelModel
from .review_context_diagnostics import ReviewContextDiagnostic


class AcceptedReviewState(CamelModel):
    status: Literal["missing", "current", "reopened", "retained"]
    stale_reasons: list[ReviewContextDiagnostic]


def accepted_review_state(
    *, exists: bool, candidate_active: bool, head_status: str,
    stale_reasons: list[ReviewContextDiagnostic],
) -> AcceptedReviewState:
    """Project binding and lifecycle eligibility without changing stored evidence."""
    if not exists:
        return AcceptedReviewState(status="missing", stale_reasons=[])
    if candidate_active or stale_reasons:
        status = "retained"
    elif head_status == "reopened":
        status = "reopened"
    elif head_status == "accepted":
        status = "current"
    else:
        status = "retained"
    return AcceptedReviewState(status=status, stale_reasons=stale_reasons)
