"""Model-authored Storyboard response contracts, before trusted ID and coverage binding."""

from __future__ import annotations

from pydantic import Field

from ..canonical_schema import AudioKind, V2ShotSize
from plotloom.domain_base import CamelModel
from plotloom.canonical_schema import ContinuityStateV2, RequiredEntityState


class AudioEventContent(CamelModel):
    """Model-authored audio semantics, without a canonical event identifier."""

    kind: AudioKind
    description: str = Field(min_length=1)
    start_offset_units: int = Field(ge=0)
    duration_units: int = Field(ge=1)


class AudioPlanContent(CamelModel):
    """Model-facing audio events; the binder owns stable event IDs."""

    events: list[AudioEventContent]


class ShotContent(CamelModel):
    """Model-authored shot fields, without the selected dramatic-scene ID."""

    local_shot_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    title: str = Field(min_length=1)
    shot_size: V2ShotSize
    duration_units: int = Field(ge=1)
    camera_angle: str
    camera_movement: str
    composition: str
    visual_intent: str
    motion_intent: str
    action: str
    transition: str
    cue_ids: list[str]
    audio_plan: AudioPlanContent
    character_ids: list[str]
    location_id: str | None
    prop_ids: list[str]
    required_entity_states: list[RequiredEntityState]
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2


class SupportingBeatLinkContent(CamelModel):
    """Optional non-primary coverage; the binder owns its fixed role."""

    shot_local_id: str = Field(min_length=1)
    beat_id: str = Field(min_length=1)
    coverage_weight: float = Field(gt=0, le=1)


class StoryboardFragmentOutput(CamelModel):
    """Model content for one scene; trusted code owns parent and PRIMARY links."""

    shots: list[ShotContent] = Field(min_length=1)
    primary_shot_local_id_by_beat: dict[str, str] = Field(min_length=1)
    supporting_beat_links: list[SupportingBeatLinkContent] = Field(default_factory=list)
