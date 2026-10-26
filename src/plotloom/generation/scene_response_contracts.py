"""Model-authored Scene Beats response contracts; trusted binding lives in fragment_binding."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, model_validator

from ..canonical_schema import NonBlankText
from plotloom.domain_base import CamelModel
from plotloom.canonical_schema import ContinuityStateV2, DialogueDeliveryPace


class DramaticSceneContent(CamelModel):
    """Model-authored scene fields, without the selector-owned story-node ID."""

    local_scene_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    location_id: str | None
    character_ids: list[str]
    # This is a relative creative weight, not an authored clock value.  The
    # trusted binder partitions the node's frozen millisecond cap.
    duration_weight: int = Field(default=1, ge=1, le=1_000)
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2


class BeatContent(CamelModel):
    """Model-authored beat fields, with only local scene correlation."""

    local_beat_id: str = Field(min_length=1)
    scene_local_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    description: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    visible_event: str
    immediate_result: str
    dramatic_change: str
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2
    continuity_anchors: list[str]
    continuity_delta: dict[str, Any]


class DialogueCueContent(CamelModel):
    """Model-authored dialogue tied to a local beat before trusted ID binding."""

    local_cue_id: str = Field(min_length=1)
    beat_local_id: str = Field(min_length=1)
    order: int = Field(
        ge=1,
        description="One-based contiguous dialogue order within this cue's beatLocalId.",
    )
    speaker_id: Annotated[
        str | None,
        Field(
            description=(
                "Story Bible character ID for spoken dialogue, or null for voice-over; "
                "exactly one of speakerId and voiceOver must be non-null."
            )
        ),
    ]
    voice_over: Annotated[
        NonBlankText | None,
        Field(
            description=(
                "Non-blank voice-over identity when speakerId is null, otherwise null; "
                "exactly one of speakerId and voiceOver must be non-null."
            )
        ),
    ]
    # Canonical timing is deliberately absent.  Trusted binding derives it
    # from these semantic values under a frozen versioned policy; the model is
    # never asked to count Unicode code points or perform timing arithmetic.
    text: NonBlankText
    language: NonBlankText
    delivery: DialogueDeliveryPace
    performance_notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_voice_source(self) -> "DialogueCueContent":
        if (self.speaker_id is None) == (self.voice_over is None):
            raise ValueError(
                "DialogueCue requires exactly one of speakerId or voiceOver"
            )
        if self.voice_over is not None and not self.voice_over.strip():
            raise ValueError(
                "DialogueCue voiceOver must be a non-blank identity or label"
            )
        return self


class SceneBeatsFragmentOutput(CamelModel):
    """Model content for one node; trusted code injects selector-owned parents."""

    scenes: list[DramaticSceneContent] = Field(min_length=1)
    beats: list[BeatContent] = Field(min_length=1)
    dialogue_cues: list[DialogueCueContent]
