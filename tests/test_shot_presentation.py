"""Author review and exact literal provenance, with no provider calls."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from plotloom.shot_presentation import (
    ShotPresentationRequest,
    message_direction,
    reviewed_projection,
    source_package,
)


def source():
    text = {"text": "今晚不去了，明天见。", "sourceCoordinates": {"flowIndex": 3}, "sourceContentHash": "b" * 64}
    before = {"id": "draft", "visibleTexts": [text]}
    shot = {"id": "send", "action": "Send from the phone.", "composition": "A phone.", "visibleTexts": []}
    return source_package(shot, {"beats": []}, before)


def request(package):
    return ShotPresentationRequest.model_validate({
        "expectedRevision": 0, "sourceHash": package["sourceHash"], "approvalId": "approved",
        "storyboardRevision": 1, "physical": {"action": "Tap send, then show the sent state.",
        "composition": "A popped-out complete unsent draft preview.", "visualIntent": "", "motionIntent": "", "cameraMovement": "Following shot."},
        "literalSources": [{"shotId": "draft", "index": 0}], "messagePresentation": "popped_out_send",
        "reason": "The author approved the preview and a separate send action.", "reviewed": True,
    })


def test_predecessor_literal_keeps_exact_characters_and_provenance():
    package = source(); original = deepcopy(package)
    projected = reviewed_projection(package, request(package))
    assert projected["visibleTexts"] == package["predecessor"]["visibleTexts"]
    assert package == original
    assert "Send from the phone." not in projected["action"]


@pytest.mark.parametrize("mutation", ["unrelated", "missing", "changed", "invented", "unreviewed", "duplicate", "no_message"])
def test_review_refuses_wrong_literal_or_source_authority(mutation):
    package = source(); body = request(package).model_dump(mode="json", by_alias=True)
    if mutation == "unrelated": body["literalSources"][0]["shotId"] = "another-scene"
    elif mutation == "missing": body["literalSources"][0]["index"] = 1
    elif mutation == "changed": body["sourceHash"] = "a" * 64
    elif mutation == "invented": body["literalSources"][0]["text"] = "Invented reply"
    elif mutation == "unreviewed": body["reviewed"] = False
    elif mutation == "duplicate": body["literalSources"].append(body["literalSources"][0])
    elif mutation == "no_message": body["literalSources"] = []
    with pytest.raises((ValueError, ValidationError)):
        reviewed_projection(package, ShotPresentationRequest.model_validate(body))


def test_message_states_have_distinct_first_frame_and_send_contracts():
    draft = message_direction({"review": {"messagePresentation": "popped_out_draft"}})
    send = message_direction({"review": {"messagePresentation": "popped_out_send"}})
    assert "first frame" in draft and "first frame" in send
    assert "do not animate character-by-character" in draft
    assert "deliberate send action" in send and "sent-message state afterward" in send
    assert message_direction(None) == ""


@pytest.mark.parametrize("mode", ["source", "popped_out_draft", "popped_out_send"])
@pytest.mark.parametrize("utterance", ["今晚不去了，明天见。", "我说：今晚不去了，明天见。"])
def test_nonspoken_literal_cannot_override_canonical_dialogue(mode, utterance):
    original = source()
    package = source_package(original["shot"], {"dialogueCues": [{"text": utterance}]}, original["predecessor"])
    review = request(package).model_copy(update={"message_presentation": mode})
    before = deepcopy(package)
    with pytest.raises(ValueError, match="overlaps authored dialogue"):
        reviewed_projection(package, review)
    assert package == before


def test_unrelated_dialogue_is_preserved_by_nonspoken_presentation():
    original = source()
    package = source_package(original["shot"], {"dialogueCues": [{"text": "雨停了。"}]}, original["predecessor"])
    before = deepcopy(package)
    assert reviewed_projection(package, request(package))["visibleTexts"] == package["predecessor"]["visibleTexts"]
    assert package == before
