"""Saved canonical direction is source text, not bounded authored intent input."""
from typing import Literal

from pydantic import Field

from .domain import CamelModel
from .managed_media import VisualIntentInput


class StoryboardIntentSource(CamelModel):
    kind: Literal["saved_storyboard"] = "saved_storyboard"
    entity_revision_id: str
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    shot_id: str


class SourceEndorsedIntent(CamelModel):
    role: Literal["shot_keyframe"] = "shot_keyframe"
    composition_intent: str
    source_refs: list[str] = Field(min_length=1, max_length=1)
    source_endorsement: StoryboardIntentSource


def parse_saved_intent(raw):
    model = SourceEndorsedIntent if "sourceEndorsement" in raw else VisualIntentInput
    return model.model_validate(raw)
