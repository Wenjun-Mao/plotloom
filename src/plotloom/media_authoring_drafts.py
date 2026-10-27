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
    source_refs: list[str] = Field(default_factory=list, max_length=64_000)
    source_refs_text: str | None = Field(default=None, max_length=64_000, exclude_if=lambda value: value is None)
    source_binding_id: str | None = Field(default=None, min_length=1, max_length=36, exclude_if=lambda value: value is None)
    retained_visual_intent_id: str | None = Field(default=None, min_length=1, max_length=36, exclude_if=lambda value: value is None)

    @field_validator("source_refs")
    @classmethod
    def bound_working_source_refs(cls, value: list[str]) -> list[str]:
        if sum(len(item) for item in value) > 64_000:
            raise ValueError("working visual-intent references exceed their text bound")
        return value



class ImageDirectionDraftPayload(CamelModel):
    shot_id: str = Field(min_length=1, max_length=100)
    target_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    context_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    presentation_change: str = Field(max_length=2_000)
