"""Creator-owned character-reference selection request contract."""

from plotloom.image_job_contracts import CharacterReferenceDecisionRequest


def test_character_reference_selection_does_not_require_a_reviewer_or_reason() -> None:
    """Selection authority is the asset/context/CAS tuple, not fabricated prose."""

    request = CharacterReferenceDecisionRequest.model_validate({
        "characterId": "cast-hero",
        "authority": "cast",
        "primaryAssetId": "a" * 36,
        "complementaryAssetIds": [],
        "expectedReferenceRevision": 2,
    })

    assert request.reviewer is None
    assert request.notes is None
