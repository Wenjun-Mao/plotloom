"""Versioned, provider-neutral authoring schemas.

This module owns the current authoring contract with explicit footage membership
and integer time units. Retired schemas are not executable.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from .dialogue_timing_policy import (
    DEFAULT_DIALOGUE_TIMING_PROFILE as DEFAULT_DIALOGUE_TIMING_PROFILE,
    DialogueDeliveryPace as DialogueDeliveryPace, DialogueTimingProfile as DialogueTimingProfile,
    DialogueTimingRule as DialogueTimingRule, default_dialogue_timing_profile as default_dialogue_timing_profile,
)


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class V2Model(BaseModel):
    """Strict current canonical wire models."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
        validate_assignment=True,
    )


def _strip_string(value: object) -> object:
    """Normalize human-entered scalar text before enforcing V2 wire rules."""

    return value.strip() if isinstance(value, str) else value


# IDs appear in gate identities, dotted issue paths, and persisted rows.  Keep
# them concise and delimiter-free so an ID always denotes one unambiguous
# domain entity.
StableId = Annotated[
    str,
    BeforeValidator(_strip_string),
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
]
NonBlankText = Annotated[str, BeforeValidator(_strip_string), Field(min_length=1)]


class V2StoryNodeKind(str, Enum):
    START = "start"
    SCENE = "scene"
    DECISION = "decision"
    JOIN = "join"
    ENDING = "ending"


class V2StoryEdgeKind(str, Enum):
    CONTINUATION = "continuation"
    CHOICE = "choice"


class V2CoverageRole(str, Enum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"


class V2ShotSize(str, Enum):
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    INSERT = "insert"


class EntityType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    PROP = "prop"


class AudioKind(str, Enum):
    AMBIENCE = "ambience"
    SOUND_EFFECT = "sound_effect"
    DIEGETIC_SOUND = "diegetic_sound"
    DIEGETIC_MUSIC = "diegetic_music"
    SCORE = "score"


class EntitySpecV2(V2Model):
    id: StableId
    name: Annotated[str, Field(min_length=1)]
    description: str
    visual_anchors: list[Annotated[str, Field(min_length=1)]]
    sound_anchors: list[Annotated[str, Field(min_length=1)]]
    allowed_states: list[Annotated[str, Field(min_length=1)]]
    continuity_rules: list[Annotated[str, Field(min_length=1)]]

    @model_validator(mode="after")
    def _allowed_states_are_unique(self) -> EntitySpecV2:
        if len(self.allowed_states) != len(set(self.allowed_states)):
            raise ValueError("allowedStates must not contain duplicates")
        return self


class CharacterV2(EntitySpecV2):
    role: str | None
    goal: str
    traits: list[str]
    voice_anchors: list[Annotated[str, Field(min_length=1)]]


class LocationV2(EntitySpecV2):
    pass


class PropV2(EntitySpecV2):
    pass


class StoryBibleV2(V2Model):
    logline: Annotated[str, Field(min_length=1)]
    premise: Annotated[str, Field(min_length=1)]
    genre: str
    tone: str
    audience: str
    narrative_promise: str
    visual_language: str
    themes: list[str]
    world_rules: list[str]
    known_facts: list[str]
    open_questions: list[str]
    source_notes: list[str]
    characters: list[CharacterV2]
    locations: list[LocationV2]
    props: list[PropV2]

    @model_validator(mode="after")
    def _entity_ids_are_unique_per_kind(self) -> StoryBibleV2:
        for label, entities in (
            ("character", self.characters),
            ("location", self.locations),
            ("prop", self.props),
        ):
            ids = [entity.id for entity in entities]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {label} ids")
        return self


class StoryNodeV2(V2Model):
    id: StableId
    title: Annotated[str, Field(min_length=1)]
    summary: Annotated[str, Field(min_length=1)]
    kind: V2StoryNodeKind
    footage_mode: Literal["footage", "route_only"]

    @model_validator(mode="after")
    def require_footage_for_story_content(self) -> "StoryNodeV2":
        if self.footage_mode == "route_only" and self.kind not in {
            V2StoryNodeKind.DECISION, V2StoryNodeKind.JOIN,
        }:
            raise ValueError("only decision/join nodes may be route-only")
        return self


class RequiredEntityState(V2Model):
    """One explicit Story Bible entity-state assignment or requirement."""

    entity_type: EntityType
    entity_id: StableId
    state: Annotated[str, Field(min_length=1)]


class StoryEdgeV2(V2Model):
    id: StableId
    source_node_id: StableId
    target_node_id: StableId
    kind: V2StoryEdgeKind
    choice_text: NonBlankText | None
    # Arbitrary finite JSON story facts remain separate from Bible-owned
    # entity state vocabulary.  No key-name convention bridges these fields.
    state_effects: dict[str, Any]
    entity_state_effects: list[RequiredEntityState] = Field(default_factory=list)

    @model_validator(mode="after")
    def _choice_edges_have_copy(self) -> StoryEdgeV2:
        if self.kind == V2StoryEdgeKind.CHOICE and not self.choice_text:
            raise ValueError("choice edges require choice_text")
        if self.kind == V2StoryEdgeKind.CONTINUATION and self.choice_text is not None:
            raise ValueError("continuation edges must not define choice_text")
        keys = [(item.entity_type, item.entity_id) for item in self.entity_state_effects]
        if len(keys) != len(set(keys)):
            raise ValueError("entityStateEffects must name each entity at most once")
        return self


class JoinContractV2(V2Model):
    id: StableId
    join_node_id: StableId
    incoming_node_ids: Annotated[list[StableId], Field(min_length=2)]
    required_state_keys: list[NonBlankText]
    allowed_differences: list[NonBlankText]
    reconciliation: str
    notes: str

    @model_validator(mode="after")
    def _join_keys_are_unambiguous(self) -> JoinContractV2:
        lists = (
            ("incomingNodeIds", self.incoming_node_ids),
            ("requiredStateKeys", self.required_state_keys),
            ("allowedDifferences", self.allowed_differences),
        )
        for label, values in lists:
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must not contain duplicates")
        if not set(self.allowed_differences) <= set(self.required_state_keys):
            raise ValueError("allowedDifferences must be contained in requiredStateKeys")
        return self


class StoryGraphV2(V2Model):
    start_node_id: StableId
    nodes: Annotated[list[StoryNodeV2], Field(min_length=1)]
    edges: list[StoryEdgeV2]
    join_contracts: list[JoinContractV2]


class ContinuityStateV2(V2Model):
    facts: dict[str, Any]
    entity_states: list[RequiredEntityState]
    screen_direction: str | None
    lighting: str | None
    sound: Annotated[
        str | None,
        Field(
            description=(
                "Persistent sound or ambience at this exact continuity boundary; "
                "transient action-local foley does not belong here."
            )
        ),
    ]
    notes: list[str]

    @model_validator(mode="after")
    def _entity_states_are_unambiguous(self) -> ContinuityStateV2:
        keys = [(state.entity_type, state.entity_id) for state in self.entity_states]
        if len(keys) != len(set(keys)):
            raise ValueError("continuity entityStates must name each entity at most once")
        return self


class DramaticSceneV2(V2Model):
    id: StableId
    story_node_id: StableId
    order: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1)]
    objective: Annotated[str, Field(min_length=1)]
    location_id: StableId | None
    character_ids: list[StableId]
    beat_ids: Annotated[list[StableId], Field(min_length=1)]
    duration_budget_units: Annotated[int, Field(ge=1)]
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2

    @model_validator(mode="after")
    def _references_are_unique(self) -> DramaticSceneV2:
        if len(self.character_ids) != len(set(self.character_ids)):
            raise ValueError("characterIds must not contain duplicates")
        if len(self.beat_ids) != len(set(self.beat_ids)):
            raise ValueError("beatIds must not contain duplicates")
        return self


class BeatV2(V2Model):
    id: StableId
    scene_id: StableId
    order: Annotated[int, Field(ge=1)]
    description: Annotated[str, Field(min_length=1)]
    purpose: Annotated[str, Field(min_length=1)]
    visible_event: str
    immediate_result: str
    dramatic_change: str
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2
    continuity_anchors: list[str]
    continuity_delta: dict[str, Any]


class DialogueCue(V2Model):
    """The one canonical dialogue line.  It is owned by exactly one beat."""

    id: StableId
    beat_id: StableId
    order: Annotated[int, Field(ge=1)]
    speaker_id: StableId | None
    voice_over: NonBlankText | None
    text: NonBlankText
    language: NonBlankText
    delivery: DialogueDeliveryPace
    performance_notes: str
    estimated_duration_units: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def _exactly_one_voice_source(self) -> DialogueCue:
        if (self.speaker_id is None) == (self.voice_over is None):
            raise ValueError("DialogueCue requires exactly one of speakerId or voiceOver")
        return self


class SceneBeatPlanV2(V2Model):
    scenes: list[DramaticSceneV2]
    beats: list[BeatV2]
    dialogue_cues: list[DialogueCue]


class AudioEvent(V2Model):
    id: StableId
    kind: AudioKind
    description: Annotated[str, Field(min_length=1)]
    start_offset_units: Annotated[int, Field(ge=0)]
    duration_units: Annotated[int, Field(ge=1)]


class AudioPlan(V2Model):
    events: list[AudioEvent]

    @model_validator(mode="after")
    def _event_ids_are_unique(self) -> AudioPlan:
        if len({event.id for event in self.events}) != len(self.events):
            raise ValueError("audio event ids must be unique within an AudioPlan")
        return self


class AuthoredVisibleText(V2Model):
    """Exact nonspoken words, with source evidence retained independently."""
    text: Annotated[str, Field(strict=True, min_length=1, pattern=r"\S")]
    source_coordinates: dict[str, Any]
    source_content_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ShotV2(V2Model):
    id: StableId
    scene_id: StableId
    order: Annotated[int, Field(ge=1)]
    title: Annotated[str, Field(min_length=1)]
    shot_size: V2ShotSize
    duration_units: Annotated[int, Field(ge=1)]
    camera_angle: str
    camera_movement: str
    composition: str
    visual_intent: str
    motion_intent: str
    action: str
    visible_texts: list[AuthoredVisibleText] = Field(default_factory=list)
    transition: str
    cue_ids: list[StableId]
    audio_plan: AudioPlan
    character_ids: list[StableId]
    location_id: StableId | None
    prop_ids: list[StableId]
    required_entity_states: list[RequiredEntityState]
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2

    @model_validator(mode="after")
    def _references_are_unambiguous(self) -> ShotV2:
        if len(self.cue_ids) != len(set(self.cue_ids)):
            raise ValueError("cueIds must not contain duplicates")
        if len(self.character_ids) != len(set(self.character_ids)):
            raise ValueError("characterIds must not contain duplicates")
        if len(self.prop_ids) != len(set(self.prop_ids)):
            raise ValueError("propIds must not contain duplicates")
        state_keys = [
            (state.entity_type, state.entity_id)
            for state in self.required_entity_states
        ]
        if len(state_keys) != len(set(state_keys)):
            raise ValueError("requiredEntityStates must name each entity at most once")
        return self


class ShotBeatLinkV2(V2Model):
    shot_id: StableId
    beat_id: StableId
    role: V2CoverageRole
    coverage_weight: Annotated[float, Field(gt=0, le=1)]


class StoryboardV2(V2Model):
    shots: list[ShotV2]
    shot_beat_links: list[ShotBeatLinkV2]
