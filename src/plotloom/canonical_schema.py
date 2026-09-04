"""Versioned, provider-neutral authoring schemas.

The original models in :mod:`plotloom.domain` are intentionally retained as
the V1 read model.  This module owns the non-compatible V2 authoring contract:
it uses integer time units and never derives structured production semantics
from V1 free text.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class V2Model(BaseModel):
    """Strict V2 wire models, kept separate from the V1 compatibility shape."""

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
# domain entity.  V1 has no such restriction because it is historical read
# evidence, not current authoring input.
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


class DialogueDeliveryPace(str, Enum):
    """The bounded timing input; expressive direction belongs in notes."""

    MEASURED = "measured"
    NATURAL = "natural"
    BRISK = "brisk"


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


class StoryEdgeV2(V2Model):
    id: StableId
    source_node_id: StableId
    target_node_id: StableId
    kind: V2StoryEdgeKind
    choice_text: NonBlankText | None
    state_effects: dict[str, Any]

    @model_validator(mode="after")
    def _choice_edges_have_copy(self) -> StoryEdgeV2:
        if self.kind == V2StoryEdgeKind.CHOICE and not self.choice_text:
            raise ValueError("choice edges require choice_text")
        if self.kind == V2StoryEdgeKind.CONTINUATION and self.choice_text is not None:
            raise ValueError("continuation edges must not define choice_text")
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


class RequiredEntityState(V2Model):
    entity_type: EntityType
    entity_id: StableId
    state: Annotated[str, Field(min_length=1)]


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


class DialogueTimingRule(V2Model):
    """One explicit language/delivery estimate rule in integer time units."""

    model_config = V2Model.model_config | {"frozen": True}

    language: Annotated[str, Field(min_length=1)]
    delivery: DialogueDeliveryPace
    units_per_character: Annotated[int, Field(ge=1)]


class DialogueTimingProfile(V2Model):
    """Versioned timing policy; no evaluator owns an implicit CPS constant."""

    model_config = V2Model.model_config | {"frozen": True}

    version: Annotated[str, Field(min_length=1)]
    rules: Annotated[list[DialogueTimingRule], Field(min_length=1)]

    @model_validator(mode="after")
    def _rules_are_unique(self) -> DialogueTimingProfile:
        pairs = [(rule.language, rule.delivery) for rule in self.rules]
        if len(pairs) != len(set(pairs)):
            raise ValueError("dialogue timing rules must be unique by language and delivery")
        return self

    def rule_for(
        self,
        *,
        language: str,
        delivery: DialogueDeliveryPace,
    ) -> DialogueTimingRule | None:
        """Return the one versioned rule governing a language/pace pair.

        This is deliberately the sole language/delivery selection path.  The
        validator and correction evidence must never independently reimplement
        its exact-language then wildcard fallback semantics.
        """

        matching = next(
            (
                rule
                for rule in self.rules
                if rule.language == language and rule.delivery == delivery
            ),
            None,
        )
        fallback = next(
            (
                rule
                for rule in self.rules
                if rule.language == "*" and rule.delivery == delivery
            ),
            None,
        )
        return matching or fallback

    def estimate_text_duration_units(
        self,
        *,
        text: str,
        language: str,
        delivery: DialogueDeliveryPace,
    ) -> int | None:
        """Estimate text without requiring a canonical cue identity.

        Generation fragments use response-local correlation handles until the
        trusted binder assigns canonical IDs.  Timing therefore depends only
        on the three values that actually govern the versioned policy.
        """

        rule = self.rule_for(language=language, delivery=delivery)
        if rule is not None:
            return len(text.strip()) * rule.units_per_character
        return None

    def estimate_duration_units(self, cue: DialogueCue) -> int | None:
        return self.estimate_text_duration_units(
            text=cue.text,
            language=cue.language,
            delivery=cue.delivery,
        )


DEFAULT_DIALOGUE_TIMING_PROFILE = DialogueTimingProfile(
    version="dialogue.default.v1",
    rules=[
        DialogueTimingRule(language="zh-CN", delivery=DialogueDeliveryPace.MEASURED, units_per_character=420),
        DialogueTimingRule(language="zh-CN", delivery=DialogueDeliveryPace.NATURAL, units_per_character=330),
        DialogueTimingRule(language="zh-CN", delivery=DialogueDeliveryPace.BRISK, units_per_character=260),
        DialogueTimingRule(language="en", delivery=DialogueDeliveryPace.MEASURED, units_per_character=75),
        DialogueTimingRule(language="en", delivery=DialogueDeliveryPace.NATURAL, units_per_character=60),
        DialogueTimingRule(language="en", delivery=DialogueDeliveryPace.BRISK, units_per_character=45),
        DialogueTimingRule(language="*", delivery=DialogueDeliveryPace.MEASURED, units_per_character=85),
        DialogueTimingRule(language="*", delivery=DialogueDeliveryPace.NATURAL, units_per_character=70),
        DialogueTimingRule(language="*", delivery=DialogueDeliveryPace.BRISK, units_per_character=55),
    ],
)


def default_dialogue_timing_profile() -> DialogueTimingProfile:
    """Return the explicit multilingual fallback policy used by V2 gates."""

    return DEFAULT_DIALOGUE_TIMING_PROFILE.model_copy(deep=True)


# Compatibility exports for callers written during the first M1-12A slice.
DEFAULT_ZH_CN_DIALOGUE_TIMING_PROFILE = DEFAULT_DIALOGUE_TIMING_PROFILE


def default_zh_cn_dialogue_timing_profile() -> DialogueTimingProfile:
    """Deprecated alias for :func:`default_dialogue_timing_profile`."""

    return default_dialogue_timing_profile()


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
