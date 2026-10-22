"""Candidate lifecycle must not grant retained accepted evidence authority."""
import pytest
from pydantic import ValidationError

from plotloom.accepted_review_state import accepted_review_state
from plotloom.art_contracts import ArtReviewState
from plotloom.cast_contracts import CastReviewState
from plotloom.review_context_diagnostics import ReviewContextDiagnostic
from plotloom.script_contracts import ScriptReviewState
from plotloom.storyboard_review_contracts import StoryboardReviewState


DIAGNOSTIC = ReviewContextDiagnostic(
    code="binding_revision_changed", owner="art", field="art_revision",
    technical_message="accepted art revision changed",
)


@pytest.mark.parametrize("exists,candidate,head,stale,status", [
    (False, False, "missing", False, "missing"),
    (False, True, "prepared", False, "missing"),
    (True, False, "accepted", False, "current"),
    (True, False, "reopened", False, "reopened"),
    (True, True, "prepared", False, "retained"),
    (True, True, "candidate_ready", True, "retained"),
    (True, True, "reopened", False, "retained"),
    (True, False, "accepted", True, "retained"),
    (True, False, "reopened", True, "retained"),
    (True, False, "prepared", False, "retained"),
])
def test_projection_truth_table(exists, candidate, head, stale, status):
    reasons = [DIAGNOSTIC] if stale else []
    result = accepted_review_state(
        exists=exists, candidate_active=candidate, head_status=head, stale_reasons=reasons,
    )
    assert result.status == status
    assert result.stale_reasons == (reasons if exists else [])


@pytest.mark.parametrize("model", [CastReviewState, ArtReviewState, ScriptReviewState, StoryboardReviewState])
def test_current_read_contract_requires_independent_accepted_projection(model):
    with pytest.raises(ValidationError, match="acceptedReviewState"):
        model.model_validate({"status": "missing", "candidate": None, "staleReasons": []})
