"""Explicit per-character uncertainty decisions never become implicit PASS."""

import pytest
from pydantic import ValidationError

from plotloom.same_person_review_contracts import SamePersonReviewRequest
from plotloom.persistence.project.media_same_person_reviews import SamePersonReviewPersistence


def _item(character_id="one", judgment="pass", **fields):
    return {"characterId": character_id, "judgment": judgment,
            "identityNotes": "Visible comparison", "stateNotes": "Authored shot state", **fields}


@pytest.mark.parametrize("items,eligible", [
    ([_item(), _item("two")], True),
    ([_item(), _item("two", "unassessable", productionDecision="authorize", uncertaintyReason="Intentional hand-only framing; identity is uncertain.")], True),
    ([_item(), _item("two", "fail")], False),
    ([_item(), _item("two", "unassessable", productionDecision="hold", uncertaintyReason="Identity uncertainty is not accepted.")], False),
    ([_item("one", "unassessable", productionDecision="authorize", uncertaintyReason="   ")], False),
    ([], False),
])
def test_all_involved_characters_must_independently_authorize(items, eligible):
    assert SamePersonReviewPersistence.comparisons_authorize_production(items) is eligible


@pytest.mark.parametrize("item", [
    _item(judgment=""), _item(judgment="unassessable"),
    _item(judgment="unassessable", productionDecision="authorize"),
    _item(judgment="unassessable", uncertaintyReason="Framing is intentionally unidentifiable."),
    _item(judgment="unassessable", productionDecision="authorize", uncertaintyReason=" "),
    _item(judgment="fail", productionDecision="authorize", uncertaintyReason="Cannot override failure."),
    _item(identityNotes=" "), _item(stateNotes=" "),
])
def test_missing_or_incompatible_explicit_decisions_are_rejected(item):
    with pytest.raises(ValidationError):
        SamePersonReviewRequest.model_validate({"bindingId": "binding", "expectedReviewRevision": 0,
                                               "reviewer": "Human", "notes": "Reviewed", "comparisons": [item]})


def test_pass_fail_wire_meanings_and_old_comparison_bytes_remain_supported():
    for judgment in ["pass", "fail"]:
        original = _item(judgment=judgment)
        request = SamePersonReviewRequest.model_validate({"bindingId": "binding", "expectedReviewRevision": 0,
                                                        "reviewer": "Human", "notes": "Reviewed", "comparisons": [original]})
        assert request.comparisons[0].model_dump(by_alias=True, exclude_none=True) == original
