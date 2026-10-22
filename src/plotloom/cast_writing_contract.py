"""Frozen character-writing extension; prose judgment stays with the author."""
from typing import Any

CONTRACT_FILENAME = "cast-writing-contract.json"


def cast_writing_contract() -> dict[str, Any]:
    return {
        "version": 1,
        "requiredCharacterExtension": {
            "reviewNotes": {"sourceNotes": "string", "performanceGuidance": "string"},
        },
        "instructions": [
            "Each character must have at least one nonblank string in persona.personality and a nonblank persona.appearance. Supply an upstream-complete candidate for review. Plotloom author confirmation requires these two design fields; supplementary temperament and voice direction are not confirmation requirements.",
            "Keep persona and voice descriptions descriptive, without inline inference labels or source commentary.",
            "Put source qualifications, inference rationale and proposed production choices in reviewNotes.sourceNotes; identify each affected field/detail. Preserve verbatim persona.evidence.",
            "Put scene-specific acting directions and branch-performance constraints in reviewNotes.performanceGuidance, not temperament or voice identity.",
            "Both note fields are required strings; use an empty string when no note is needed. Notes are reviewable proposals, not author approval.",
            "This placement overrides upstream instructions to append inference markers; do not omit the inference disclosure itself. Preserve every other upstream requirement.",
        ],
    }


def validate_cast_notes(cast: dict[str, Any], *, required: bool = False, previous: dict[str, Any] | None = None) -> None:
    noted_ids = {item.get("id") for item in (previous or {}).get("characters", []) if isinstance(item, dict) and "reviewNotes" in item}
    for character in cast.get("characters", []):
        if not isinstance(character, dict):
            continue  # Stable-ID validation owns the surrounding shape.
        if "reviewNotes" not in character and not required and character.get("id") not in noted_ids:
            continue
        notes = character.get("reviewNotes")
        if not isinstance(notes, dict) or set(notes) != {"sourceNotes", "performanceGuidance"}:
            raise ValueError("each character reviewNotes must contain sourceNotes and performanceGuidance")
        if not all(isinstance(value, str) for value in notes.values()):
            raise ValueError("character reviewNotes values must be strings")
