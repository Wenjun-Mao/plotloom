import pytest

from plotloom.cast_writing_contract import cast_writing_contract, validate_cast_notes


def test_contract_and_notes_keep_prose_as_authored():
    contract = cast_writing_contract()
    assert contract["requiredCharacterExtension"]["reviewNotes"] == {"sourceNotes": "string", "performanceGuidance": "string"}
    cast = {"characters": [{"reviewNotes": {"sourceNotes": "外观是推断", "performanceGuidance": ""}, "persona": {"appearance": "推断不是禁用词"}}]}
    validate_cast_notes(cast, required=True)
    assert cast["characters"][0]["persona"]["appearance"] == "推断不是禁用词"


@pytest.mark.parametrize("notes", [None, {}, {"sourceNotes": ""}, {"sourceNotes": [], "performanceGuidance": ""}, {"sourceNotes": "", "performanceGuidance": "", "extra": ""}])
def test_rejects_malformed_notes(notes):
    with pytest.raises(ValueError, match="reviewNotes"):
        validate_cast_notes({"characters": [{"reviewNotes": notes}]})


def test_retained_candidate_needs_no_retroactive_rewrite():
    cast = {"characters": [{"persona": {"appearance": "原文未描述，细节为推断。"}}]}
    validate_cast_notes(cast)
    with pytest.raises(ValueError, match="reviewNotes"):
        validate_cast_notes(cast, required=True)


def test_author_cannot_drop_notes_but_unannotated_retained_characters_stay_valid():
    previous = {"characters": [{"id": "A", "reviewNotes": {"sourceNotes": "", "performanceGuidance": ""}}, {"id": "B"}]}
    validate_cast_notes(previous, previous=previous)
    with pytest.raises(ValueError, match="reviewNotes"):
        validate_cast_notes({"characters": [{"id": "A"}, {"id": "B"}]}, previous=previous)
