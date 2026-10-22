"""Recoverable media authoring payloads, independent of UI state."""
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain_base import CamelModel
from .delegated_qa_contracts import AgentQaAttribution


class VisualIntentDraftPayload(CamelModel):
    attribution: AgentQaAttribution | None = Field(default=None, exclude_if=lambda value: value is None)
    asset_id: str = Field(min_length=1, max_length=36)
    shot_id: str = Field(min_length=1, max_length=100)
    role: Literal["protagonist_reference", "location_reference", "shot_keyframe"]
    identity_intent: str | None = Field(default=None, max_length=2_000)
    composition_intent: str | None = Field(default=None, max_length=2_000)
    style_intent: str | None = Field(default=None, max_length=2_000)
    source_refs: list[str] = Field(min_length=1, max_length=32)
    source_binding_id: str | None = Field(default=None, min_length=1, max_length=36, exclude_if=lambda value: value is None)
    retained_visual_intent_id: str | None = Field(default=None, min_length=1, max_length=36, exclude_if=lambda value: value is None)

    @field_validator("source_refs")
    @classmethod
    def normalize_source_refs(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item or len(item) > 2_000 for item in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("visual-intent draft source refs must be unique, nonblank, and bounded")
        return normalized

    @model_validator(mode="after")
    def require_direction(self) -> "VisualIntentDraftPayload":
        if not any(value and value.strip() for value in (self.identity_intent, self.composition_intent, self.style_intent)):
            raise ValueError("visual-intent draft requires authored direction")
        return self


class ImageDirectionDraftPayload(CamelModel):
    shot_id: str = Field(min_length=1, max_length=100)
    target_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    context_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    presentation_change: str = Field(min_length=1, max_length=2_000)

    @field_validator("presentation_change")
    @classmethod
    def normalize_direction(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("image-direction draft must not be blank")
        return normalized
