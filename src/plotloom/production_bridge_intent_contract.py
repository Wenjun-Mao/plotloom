"""The model's deliberately narrow bridge-intent response contract."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_INTENT_TARGETS = 64
MAX_INTENT_CONTEXT_CHARACTERS = 60_000


class IntentSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    suggested_text: str = Field(alias="suggestedText", min_length=1, max_length=800)

    @field_validator("suggested_text")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("dramatic-intent suggestion cannot be blank")
        return cleaned


class IntentSuggestions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[IntentSuggestion] = Field(min_length=1, max_length=MAX_INTENT_TARGETS)


def intent_response_schema(expected_ids: list[str]) -> dict[str, Any]:
    if not expected_ids or len(expected_ids) > MAX_INTENT_TARGETS or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("bridge inference needs a bounded, unique target set")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["entries"],
        "properties": {
            "entries": {
                "type": "array",
                "minItems": len(expected_ids),
                "maxItems": len(expected_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "suggestedText"],
                    "properties": {
                        "id": {"type": "string", "enum": expected_ids},
                        "suggestedText": {"type": "string", "minLength": 1, "maxLength": 800},
                    },
                },
            }
        },
    }


def bind_intent_suggestions(value: Any, expected_ids: list[str]) -> dict[str, str]:
    """Reject extras, duplicates, omissions, and caller-authored provenance."""

    parsed = IntentSuggestions.model_validate(value)
    received = [entry.id for entry in parsed.entries]
    if len(received) != len(expected_ids) or len(set(received)) != len(received) or set(received) != set(expected_ids):
        raise ValueError("bridge inference must return each trusted target exactly once")
    return {entry.id: entry.suggested_text for entry in parsed.entries}
