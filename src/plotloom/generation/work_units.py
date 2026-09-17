"""Pure prompt and response contracts for bounded generation work units.

This module is intentionally provider-, repository-, and pipeline-free.  It
turns an immutable ``GenerationWorkUnit`` into a rendered request, and turns a
model's *unbound* fragment response into a fragment safely bound by trusted
runtime metadata.  A model never receives nor returns stage-plan hashes,
work-unit IDs, or input hashes.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Mapping, TypeAlias
from uuid import NAMESPACE_URL, uuid5

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from ..domain import (
    AudioEvent,
    AudioPlan,
    CanonicalSnapshot,
    BeatV2,
    CamelModel,
    ContinuityStateV2,
    DialogueCue,
    DialogueDeliveryPace,
    DialogueTimingProfile,
    DramaticSceneV2,
    EntityType,
    ProjectBrief,
    SceneBeatPlanV2,
    ShotV2,
    ShotBeatLinkV2,
    StageName,
    StoryBibleV2,
    StoryGraphV2,
)
from ..json_value_contract import (
    CanonicalJsonValueError,
    finite_canonical_json,
    finite_json_values_equal,
)
from ..validation import DomainValidationError, validate_story_graph
from ..canonical_schema import NonBlankText, V2CoverageRole
from .contracts import RenderedPrompt, ValidationIssue, ValidationReport
from .correction_contract import (
    CORRECTION_DIRECTIVE_REGISTRY_VERSION,
    CORRECTION_EVIDENCE_PROJECTION_VERSION,
    CORRECTION_ISSUE_SELECTION_VERSION,
    CORRECTION_POLICY_VERSION,
    CORRECTION_RESPONSE_SCHEMA_VERSION,
)
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
    DialogueCapacityPlanningError,
    dialogue_timing_profile_hash,
    plan_dialogue_capacity,
)
from .fragments import SceneBeatsFragment, StageFragment, StoryboardFragment
from .fragment_semantics import (
    FragmentSemanticContextError,
    allowed_entity_states,
    continuity_sequence_repair_boundaries,
    continuity_sequence_is_compatible,
    continuity_state_from_context,
    continuity_state_issues,
    cue_canonical_order_key,
    cue_duration_units,
    required_entity_is_in_shot,
)
from .json_schema import explicit_presence_json_schema, inline_local_json_references
from .planning import (
    GenerationPlan,
    GenerationWorkUnit,
    PlanningError,
    StagePlan,
    WorkUnitSelectorKind,
    assert_work_unit_input_contract,
    content_hash,
    work_unit_context,
)
from .prompts import PromptRenderer, canonical_json, sha256_text
from .scene_timing_allocation import (
    SceneTimingAllocation,
    SceneTimingAllocationError,
    plan_scene_timing_allocation,
)
from .scene_beats_edge_entry import (
    EdgeEntryEntityStateRepairFact,
    edge_entry_entity_state_repair_facts,
    edge_entry_state_requirements,
    first_scene_entry_issues,
    require_first_scene_entity_state_values,
)
from .story_graph_topology import (
    STORY_GRAPH_CONTENT_FILL_SCHEMA_ID,
    StoryGraphContentBindingError,
    StoryGraphContentFill,
    StoryGraphJoinContentFill,
    StoryGraphTopology,
    bind_story_graph_content_fill,
    story_graph_content_fill_join_diagnostic_issues,
    story_graph_content_fill_manifest,
    story_graph_content_fill_schema,
)
from .storyboard_timing_repair import (
    StoryboardCueTimingGuidance,
    StoryboardTimingGuidance,
    StoryboardTimingInfeasibleError,
    StoryboardTimingRepairPlanFact,
    build_storyboard_timing_guidance,
    build_storyboard_timing_repair_plan,
    storyboard_timing_guidance_hash,
)
from .storyboard_presence_repair import (
    AudioEventContent,
    AudioPlanContent,
    RequiredEntityPresenceRepairFact,
    ShotContent,
    StoryboardFragmentOutput,
    SupportingBeatLinkContent,
    storyboard_required_entity_presence_repair_facts,
    assert_required_entity_presence_repair_fact_matches_source,
)
from .validation import CanonicalStageValidationAdapter, SemanticValidationContext, ValidationAdapter


WORK_UNIT_PROMPT_CONTRACT_VERSION = "m1.14"
FRAGMENT_ID_BINDING_VERSION = "fragment_ids.v1"
AUDIO_EVENT_ID_BINDING_VERSION = "audio_event_ids.v1"
STORYBOARD_PRIMARY_COVERAGE_BINDING_VERSION = "storyboard_primary_coverage.v1"
SCENE_BEATS_FRAGMENT_SCHEMA_ID = "scene_beats.fragment.v13"
STORYBOARD_FRAGMENT_SCHEMA_ID = "storyboard.fragment.v6"


class WorkUnitContractError(ValueError):
    """A planned unit cannot be rendered or bound at the trusted boundary."""

    def __init__(self, message: str, *, code: str = "contract.work_unit_invalid") -> None:
        self.code = code
        super().__init__(message)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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
            raise ValueError("DialogueCue requires exactly one of speakerId or voiceOver")
        if self.voice_over is not None and not self.voice_over.strip():
            raise ValueError("DialogueCue voiceOver must be a non-blank identity or label")
        return self


class SceneBeatsFragmentOutput(CamelModel):
    """Model content for one node; trusted code injects selector-owned parents."""

    scenes: list[DramaticSceneContent] = Field(min_length=1)
    beats: list[BeatContent] = Field(min_length=1)
    dialogue_cues: list[DialogueCueContent]


class DialogueTimingRepairFact(CamelModel):
    """Trusted, compact evidence for repairing one dialogue timing rejection.

    The fact intentionally contains derived quantities only.  In particular it
    never copies dialogue text, a validator's free-form message, model
    reasoning, credentials, or any other provider evidence into a new prompt.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.cue_duration_underestimated"]
    path: tuple[str | int, ...]
    timing_profile_version: str = Field(min_length=1, max_length=128)
    matched_rule_language: str = Field(min_length=1, max_length=32)
    delivery: DialogueDeliveryPace
    text_character_count: int = Field(ge=1)
    units_per_character: int = Field(ge=1)
    minimum_duration_units: int = Field(ge=1)
    current_estimated_duration_units: int = Field(ge=1)
    scene_duration_budget_units: int | None = Field(default=None, ge=1)
    scene_cue_estimated_total_units: int | None = Field(default=None, ge=0)
    scene_cue_minimum_total_units: int | None = Field(default=None, ge=0)
    minimum_fits_scene_budget: bool | None = None


class DialogueCapacityDeliveryLimit(CamelModel):
    """One frozen delivery option made safe by the portable schema cap."""

    model_config = CamelModel.model_config | {"frozen": True}

    delivery: DialogueDeliveryPace
    max_text_codepoints: int = Field(ge=0)


class DialogueCapacityRepairFact(CamelModel):
    """Exact, non-prose authority for one rejected Scene Beats cue.

    The fact never copies the cue text.  It makes the one trusted capacity cap
    and compatible delivery choices directly visible to a bounded correction,
    rather than asking a provider to traverse a larger contract and recreate
    Unicode arithmetic.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.dialogue_cue_capacity_exceeded"]
    path: tuple[str | int, ...]
    authoring_language: NonBlankText
    language: NonBlankText
    delivery: DialogueDeliveryPace
    current_text_codepoints: int = Field(ge=1)
    max_text_codepoints: int = Field(ge=0)
    compatible_delivery_limits: tuple[DialogueCapacityDeliveryLimit, ...] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_issue_identity_and_limits(self) -> "DialogueCapacityRepairFact":
        if (
            len(self.path) != 3
            or self.path[0] != "dialogueCues"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "text"
        ):
            raise ValueError("path must identify one dialogueCues text value")
        if self.language != self.authoring_language:
            raise ValueError("capacity facts only authorize the frozen authoring language")
        deliveries = [item.delivery for item in self.compatible_delivery_limits]
        if len(deliveries) != len(set(deliveries)):
            raise ValueError("compatible delivery limits must be unique")
        current = next(
            (item for item in self.compatible_delivery_limits if item.delivery == self.delivery),
            None,
        )
        if current is None or current.max_text_codepoints != self.max_text_codepoints:
            raise ValueError("current delivery must carry the exact text cap")
        return self


class DialogueNodeBudgetRemainingCue(CamelModel):
    """One retained cue's deterministic post-deletion order."""

    model_config = CamelModel.model_config | {"frozen": True}

    local_cue_id: NonBlankText
    beat_local_id: NonBlankText
    expected_order: int = Field(ge=1)


class DialogueNodeBudgetRepairFact(CamelModel):
    """A complete, text-free repair plan for an over-budget dialogue node.

    The model cannot reliably count CJK code points or recompute a frozen
    timing profile.  This fact therefore selects the smallest deterministic
    deletion set and the only required renumbering.  It remains a correction
    instruction, never a server-side mutation of the rejected response.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.dialogue_exceeds_node_budget"]
    path: tuple[str | int, ...]
    node_id: NonBlankText
    node_duration_budget_units: int = Field(ge=1)
    current_minimum_duration_units: int = Field(ge=1)
    remove_local_cue_ids: tuple[NonBlankText, ...] = Field(min_length=1)
    remaining_cues: tuple[DialogueNodeBudgetRemainingCue, ...]
    remaining_minimum_duration_units: int = Field(ge=0)
    repair_strategy: Literal["remove_and_renumber"] = "remove_and_renumber"

    @model_validator(mode="after")
    def validate_deterministic_plan(self) -> "DialogueNodeBudgetRepairFact":
        if self.path != ("dialogueCues",):
            raise ValueError("path must identify the complete dialogueCues collection")
        if self.current_minimum_duration_units <= self.node_duration_budget_units:
            raise ValueError("dialogue node budget fact requires an actual overage")
        if self.remaining_minimum_duration_units > self.node_duration_budget_units:
            raise ValueError("deterministic deletion plan must fit the frozen node budget")
        if len(self.remove_local_cue_ids) != len(set(self.remove_local_cue_ids)):
            raise ValueError("removeLocalCueIds must be unique")
        retained_ids = [item.local_cue_id for item in self.remaining_cues]
        if len(retained_ids) != len(set(retained_ids)):
            raise ValueError("remaining cue IDs must be unique")
        if set(self.remove_local_cue_ids) & set(retained_ids):
            raise ValueError("a cue cannot be both removed and retained")
        by_beat: dict[str, list[int]] = {}
        for item in self.remaining_cues:
            by_beat.setdefault(item.beat_local_id, []).append(item.expected_order)
        if any(sorted(orders) != list(range(1, len(orders) + 1)) for orders in by_beat.values()):
            raise ValueError("remaining cue orders must be contiguous within each beat")
        return self


class CueOrderRepairAssignment(CamelModel):
    """One response-local cue's exact beat ownership and repaired order."""

    model_config = CamelModel.model_config | {"frozen": True}

    # Fragment-local handles are the only stable identities available before
    # trusted canonical binding.  Canonical cue IDs intentionally cannot be
    # used here because their derivation includes the mutable cue order.
    local_cue_id: NonBlankText
    beat_local_id: NonBlankText
    expected_order: int = Field(ge=1)


class CueOrderRepairFact(CamelModel):
    """Complete, identity-preserving renumbering for Scene Beats dialogue.

    The aggregate semantic issue has no individual cue path.  This fact makes
    every response-local cue identity, its existing beat ownership, and its
    exact contiguous replacement order explicit without carrying dialogue
    text or validator prose.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.cue_order"]
    path: tuple[str | int, ...]
    assignments: tuple[CueOrderRepairAssignment, ...] = Field(min_length=1)
    repair_strategy: Literal["preserve_membership_and_renumber"] = (
        "preserve_membership_and_renumber"
    )

    @model_validator(mode="after")
    def validate_complete_renumbering(self) -> "CueOrderRepairFact":
        if self.path != ("dialogueCues",):
            raise ValueError("path must identify the complete dialogueCues collection")
        cue_ids = [item.local_cue_id for item in self.assignments]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("cue-order assignment local cue IDs must be unique")
        expected_sort = tuple(
            sorted(self.assignments, key=lambda item: item.local_cue_id)
        )
        if self.assignments != expected_sort:
            raise ValueError("cue-order assignments must use canonical local cue ID order")
        by_beat: dict[str, list[int]] = {}
        for item in self.assignments:
            by_beat.setdefault(item.beat_local_id, []).append(item.expected_order)
        if any(
            sorted(orders) != list(range(1, len(orders) + 1))
            for orders in by_beat.values()
        ):
            raise ValueError("cue-order assignments must be contiguous within each beat")
        return self


class ShotDurationBudgetRepairFact(CamelModel):
    """Exact aggregate overage for one Storyboard fragment."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.shot_duration_budget_exceeded"]
    path: tuple[str | int, ...]
    scene_id: NonBlankText
    scene_duration_budget_units: int = Field(ge=1)
    current_total_duration_units: int = Field(ge=1)
    required_reduction_units: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_overage(self) -> "ShotDurationBudgetRepairFact":
        if self.path != ("shots",):
            raise ValueError("path must identify the complete shots collection")
        if self.current_total_duration_units - self.scene_duration_budget_units != self.required_reduction_units:
            raise ValueError("required reduction must equal the frozen scene overage")
        return self


class CueDurationFitRepairFact(CamelModel):
    """Exact cue-duration witness for one overfull shot."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.cue_duration_exceeds_shot"]
    path: tuple[str | int, ...]
    shot_local_id: NonBlankText
    current_shot_duration_units: int = Field(ge=1)
    scheduled_cue_ids: tuple[NonBlankText, ...] = Field(min_length=1)
    scheduled_cue_duration_units: tuple[int, ...] = Field(min_length=1)
    minimum_required_duration_units: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_cue_fit(self) -> "CueDurationFitRepairFact":
        if (
            len(self.path) != 3
            or self.path[0] != "shots"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "cueIds"
        ):
            raise ValueError("path must identify one shot cueIds list")
        if len(self.scheduled_cue_ids) != len(self.scheduled_cue_duration_units):
            raise ValueError("cue IDs and durations must have the same cardinality")
        if len(self.scheduled_cue_ids) != len(set(self.scheduled_cue_ids)):
            raise ValueError("scheduled cue IDs must be unique")
        if sum(self.scheduled_cue_duration_units) != self.minimum_required_duration_units:
            raise ValueError("minimum required duration must equal the scheduled cue total")
        if self.minimum_required_duration_units <= self.current_shot_duration_units:
            raise ValueError("cue-fit fact requires an overfull shot")
        return self


class JoinIncomingEdgeRepairTarget(CamelModel):
    """Frozen direct incoming edge identity, never a model-selected endpoint."""

    model_config = CamelModel.model_config | {"frozen": True}

    edge_id: NonBlankText
    source_node_id: NonBlankText


class JoinNewRequiredKeyIncomingEdges(CamelModel):
    """Edges that must receive a key promoted into a join requirement."""

    model_config = CamelModel.model_config | {"frozen": True}

    state_key: NonBlankText
    incoming_edges: tuple[JoinIncomingEdgeRepairTarget, ...] = Field(min_length=2)


class JoinAllowedDifferencesRepairFact(CamelModel):
    """Complete, intent-preserving replacement arrays for one join contract.

    A reconstruction correction must not infer the pre-existing required keys
    or allowed differences from the previous untrusted response. This fact
    therefore carries both complete arrays after the safe subset repair, while
    retaining the exact missing keys as auditable derivation evidence.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.join_allowed_differences_must_be_required"]
    path: tuple[str | int, ...]
    join_contract_id: str = Field(min_length=1)
    missing_required_state_keys: tuple[NonBlankText, ...] = Field(min_length=1)
    # Absent only when parsing legacy persisted evidence created before
    # bounded_correction.v9. New derivation always writes both complete arrays.
    expected_required_state_keys: tuple[NonBlankText, ...] | None = Field(
        default=None,
        min_length=1,
    )
    expected_allowed_differences: tuple[NonBlankText, ...] | None = Field(
        default=None,
        min_length=1,
    )
    # Added in bounded_correction.v13.  Historical evidence deliberately
    # omits it; current facts make the same correction turn aware that a key
    # promoted into requiredStateKeys must also be written on every immutable
    # direct incoming edge.
    new_required_key_incoming_edges: tuple[JoinNewRequiredKeyIncomingEdges, ...] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_issue_identity_and_missing_keys(self) -> "JoinAllowedDifferencesRepairFact":
        expected_path = (
            "joinContracts",
            self.join_contract_id,
            "allowedDifferences",
        )
        if self.path != expected_path:
            raise ValueError(
                "path must identify allowedDifferences for joinContractId"
            )
        if len(self.missing_required_state_keys) != len(
            set(self.missing_required_state_keys)
        ):
            raise ValueError("missingRequiredStateKeys must be unique")
        has_expected_required = self.expected_required_state_keys is not None
        has_expected_allowed = self.expected_allowed_differences is not None
        if has_expected_required != has_expected_allowed:
            raise ValueError("complete expected join arrays must be set together")
        if not has_expected_required:
            return self
        assert self.expected_required_state_keys is not None
        assert self.expected_allowed_differences is not None
        if len(self.expected_required_state_keys) != len(
            set(self.expected_required_state_keys)
        ):
            raise ValueError("expectedRequiredStateKeys must be unique")
        if len(self.expected_allowed_differences) != len(
            set(self.expected_allowed_differences)
        ):
            raise ValueError("expectedAllowedDifferences must be unique")
        required = set(self.expected_required_state_keys)
        allowed = set(self.expected_allowed_differences)
        missing = set(self.missing_required_state_keys)
        if not allowed <= required:
            raise ValueError(
                "expectedAllowedDifferences must be a subset of expectedRequiredStateKeys"
            )
        if not missing <= allowed:
            raise ValueError(
                "missingRequiredStateKeys must belong to expectedAllowedDifferences"
            )
        if self.new_required_key_incoming_edges is not None:
            targets = {item.state_key: item for item in self.new_required_key_incoming_edges}
            if set(targets) != missing:
                raise ValueError(
                    "newRequiredKeyIncomingEdges must name exactly the promoted keys"
                )
            for item in targets.values():
                edge_ids = [edge.edge_id for edge in item.incoming_edges]
                if len(edge_ids) != len(set(edge_ids)):
                    raise ValueError("incoming edge targets must be unique")
        return self


class JoinPreservedIncomingStateEffect(CamelModel):
    """One source-validated state value retained on a frozen incoming edge."""

    model_config = CamelModel.model_config | {"frozen": True}

    edge_id: NonBlankText
    expected_value: Any

    @model_validator(mode="after")
    def validate_expected_value(self) -> "JoinPreservedIncomingStateEffect":
        finite_canonical_json(self.expected_value)
        return self


class JoinPreservedStateEffect(CamelModel):
    """One still-valid required key and its exact values on every incoming edge."""

    model_config = CamelModel.model_config | {"frozen": True}

    state_key: NonBlankText
    incoming_effects: tuple[JoinPreservedIncomingStateEffect, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_incoming_effects(self) -> "JoinPreservedStateEffect":
        edge_ids = [effect.edge_id for effect in self.incoming_effects]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("preserved incoming edge effects must be unique")
        return self


class JoinStateEffectRepairFact(CamelModel):
    """Path-bound join edge repair guidance derived from frozen topology."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.join_state_effect_missing",
        "semantic.join_state_effect_conflict",
    ]
    path: tuple[str | int, ...]
    join_contract_id: NonBlankText
    join_node_id: NonBlankText
    state_key: NonBlankText
    mode: Literal["convergent", "variant"]
    incoming_edges: tuple[JoinIncomingEdgeRepairTarget, ...] = Field(min_length=2)
    repair_action: Literal[
        "set_missing",
        "make_all_equal",
    ]
    # JSON null is a legitimate exact state value, so absence cannot be
    # represented by ``expectedValue is None`` alone.
    has_expected_value: bool = False
    expected_value: Any | None = None
    # Sibling keys are authority only when this rejected response already
    # satisfies their full join contract. Keys with their own repairable issue
    # are deliberately absent, so simultaneous repairs never freeze invalid
    # fields or contradict one another.
    preserved_state_effects: tuple[JoinPreservedStateEffect, ...] = ()

    @model_validator(mode="after")
    def validate_join_effect_target(self) -> "JoinStateEffectRepairFact":
        edge_ids = [edge.edge_id for edge in self.incoming_edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("incoming edge targets must be unique")
        if self.code == "semantic.join_state_effect_conflict":
            if self.path != (
                "joinContracts",
                self.join_contract_id,
                "requiredStateKeys",
                self.state_key,
            ):
                raise ValueError("conflict path must identify one join requiredStateKey")
        elif (
            len(self.path) != 4
            or self.path[0] != "edges"
            or not isinstance(self.path[1], str)
            or self.path[1] not in edge_ids
            or self.path[2] != "stateEffects"
            or self.path[3] != self.state_key
        ):
            raise ValueError("path must identify one direct incoming edge state effect")
        if self.repair_action == "make_all_equal" and self.mode != "convergent":
            raise ValueError("only convergent join keys may require equal values")
        if self.has_expected_value:
            finite_canonical_json(self.expected_value)
        elif "expected_value" in self.model_fields_set:
            # ``null`` is an authorized state value only when the explicit
            # presence bit says so.  Accepting an explicit null here would
            # turn absence of repair authority into an ambiguous instruction.
            raise ValueError("expectedValue requires hasExpectedValue=true")
        preserved_keys = [effect.state_key for effect in self.preserved_state_effects]
        if len(preserved_keys) != len(set(preserved_keys)):
            raise ValueError("preservedStateEffects must use unique state keys")
        if self.state_key in preserved_keys:
            raise ValueError("preservedStateEffects cannot constrain the repaired state key")
        incoming_edge_ids = tuple(edge.edge_id for edge in self.incoming_edges)
        for effect in self.preserved_state_effects:
            if tuple(item.edge_id for item in effect.incoming_effects) != incoming_edge_ids:
                raise ValueError(
                    "preservedStateEffects must cover the exact ordered incoming edge set"
                )
        return self


CONTINUITY_SEQUENCE_OWNERSHIP_POLICY_VERSION = "continuity_sequence.boundary_owner.v1"


class ContinuityStateEndpoint(CamelModel):
    """One state boundary identified without relying on an array index."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["scene", "beat", "shot"]
    id: NonBlankText
    id_scope: Literal["response_local", "canonical_context"]
    state: Literal["entry", "exit"]


class ContinuityFactAssignment(CamelModel):
    """Copy one finite JSON fact from a prior boundary to its successor."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["fact"]
    key: NonBlankText
    expected_value: Any

    @model_validator(mode="after")
    def validate_finite_expected_value(self) -> "ContinuityFactAssignment":
        finite_canonical_json(self.expected_value)
        return self


class ContinuityEntityStateAssignment(CamelModel):
    """Copy an already-valid entity state without changing its identity."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["entity_state"]
    entity_type: EntityType
    entity_id: NonBlankText
    expected_state: NonBlankText


class ContinuityScalarAssignment(CamelModel):
    """Copy one shared visual/audio scalar at an incompatible boundary."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["scalar"]
    field: Literal["screenDirection", "lighting", "sound"]
    expected_value: NonBlankText


ContinuityRepairAssignment: TypeAlias = Annotated[
    ContinuityFactAssignment
    | ContinuityEntityStateAssignment
    | ContinuityScalarAssignment,
    Field(discriminator="kind"),
]


class ContinuityBoundaryRepair(CamelModel):
    """All exact assignments at one left-to-right sequence boundary."""

    model_config = CamelModel.model_config | {"frozen": True}

    source: ContinuityStateEndpoint
    target: ContinuityStateEndpoint
    assignments: tuple[ContinuityRepairAssignment, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_direction_and_unique_targets(self) -> "ContinuityBoundaryRepair":
        if self.source == self.target:
            raise ValueError("continuity boundary source and target must differ")
        keys: list[tuple[str, str, str]] = []
        for assignment in self.assignments:
            if isinstance(assignment, ContinuityFactAssignment):
                keys.append(("fact", assignment.key, ""))
            elif isinstance(assignment, ContinuityEntityStateAssignment):
                keys.append(("entity_state", assignment.entity_type.value, assignment.entity_id))
            else:
                keys.append(("scalar", assignment.field, ""))
        if len(keys) != len(set(keys)):
            raise ValueError("continuity boundary assignments must not overlap")
        return self


class ContinuitySequenceRepairFact(CamelModel):
    """A complete exact repair plan for one incompatible local sequence.

    The versioned ownership rule uses sequence order for Scene Beats.  For
    Storyboard, frozen canonical scene context owns both outer boundaries.
    It is deliberately a correction-only policy; canonical validation
    continues to reject a mismatched response before any plan is derived.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.continuity_beat_sequence_mismatch",
        "semantic.continuity_shot_sequence_mismatch",
    ]
    path: tuple[str | int, ...]
    ownership_policy_version: Literal[CONTINUITY_SEQUENCE_OWNERSHIP_POLICY_VERSION] = (
        CONTINUITY_SEQUENCE_OWNERSHIP_POLICY_VERSION
    )
    sequence_kind: Literal["beat", "shot"]
    owner: ContinuityStateEndpoint
    ordered_item_ids: tuple[NonBlankText, ...] = Field(min_length=1)
    boundaries: tuple[ContinuityBoundaryRepair, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_issue_identity_and_direction(self) -> "ContinuitySequenceRepairFact":
        if len(self.ordered_item_ids) != len(set(self.ordered_item_ids)):
            raise ValueError("continuity sequence item IDs must be unique")
        if self.code == "semantic.continuity_beat_sequence_mismatch":
            if (
                self.sequence_kind != "beat"
                or len(self.path) != 2
                or self.path[0] != "scenes"
                or not isinstance(self.path[1], int)
                or isinstance(self.path[1], bool)
                or self.path[1] < 0
                or self.owner.kind != "scene"
                or self.owner.id_scope != "response_local"
                or self.owner.state != "entry"
            ):
                raise ValueError("beat continuity repair must identify one response-local scene")
        elif (
            self.sequence_kind != "shot"
            or self.path != ("shots",)
            or self.owner.kind != "scene"
            or self.owner.id_scope != "canonical_context"
            or self.owner.state != "entry"
        ):
            raise ValueError("shot continuity repair must identify the canonical selected scene")
        legal_boundaries = _legal_continuity_repair_boundaries(
            sequence_kind=self.sequence_kind,
            owner=self.owner,
            ordered_item_ids=self.ordered_item_ids,
        )
        for boundary in self.boundaries:
            if (boundary.source, boundary.target) not in legal_boundaries:
                raise ValueError(
                    "continuity repair boundary is not adjacent in its owned sequence"
                )
        targets = [(boundary.target.kind, boundary.target.id, boundary.target.state) for boundary in self.boundaries]
        if len(targets) != len(set(targets)):
            raise ValueError("continuity sequence boundaries must not share a target state")
        return self


def _legal_continuity_repair_boundaries(
    *,
    sequence_kind: Literal["beat", "shot"],
    owner: ContinuityStateEndpoint,
    ordered_item_ids: tuple[str, ...],
) -> set[tuple[ContinuityStateEndpoint, ContinuityStateEndpoint]]:
    item_scope: Literal["response_local"] = "response_local"
    item_entries = [
        ContinuityStateEndpoint(
            kind=sequence_kind,
            id=item_id,
            id_scope=item_scope,
            state="entry",
        )
        for item_id in ordered_item_ids
    ]
    item_exits = [
        ContinuityStateEndpoint(
            kind=sequence_kind,
            id=item_id,
            id_scope=item_scope,
            state="exit",
        )
        for item_id in ordered_item_ids
    ]
    legal = {
        (item_exits[index], item_entries[index + 1])
        for index in range(len(ordered_item_ids) - 1)
    }
    legal.add((owner, item_entries[0]))
    if sequence_kind == "beat":
        legal.add(
            (
                item_exits[-1],
                ContinuityStateEndpoint(
                    kind="scene",
                    id=owner.id,
                    id_scope="response_local",
                    state="exit",
                ),
            )
        )
    else:
        legal.add(
            (
                ContinuityStateEndpoint(
                    kind="scene",
                    id=owner.id,
                    id_scope="canonical_context",
                    state="exit",
                ),
                item_exits[-1],
            )
        )
    return legal


class EdgeStateEffectJsonRepairFact(CamelModel):
    """One frozen topology edge whose state value must become finite JSON.

    Finite-JSON is a graph-wide invariant, not a special property of join
    edges.  The correction boundary therefore binds the selected edge to its
    topology-owned endpoints, while deliberately withholding a guessed
    replacement value.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.state_effect_not_json"]
    path: tuple[str | int, ...]
    edge_id: NonBlankText
    source_node_id: NonBlankText
    target_node_id: NonBlankText
    state_key: NonBlankText
    repair_action: Literal["replace_with_finite_json"] = "replace_with_finite_json"

    @model_validator(mode="after")
    def validate_edge_state_effect_target(self) -> "EdgeStateEffectJsonRepairFact":
        if self.path != ("edges", self.edge_id, "stateEffects", self.state_key):
            raise ValueError("path must identify the frozen edge state effect")
        return self

class JoinReconciliationRepairFact(CamelModel):
    """Typed non-prose authority for a missing required reconciliation."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.join_allowed_difference_without_reconciliation"]
    path: tuple[str | int, ...]
    join_contract_id: NonBlankText
    allowed_difference_keys: tuple[NonBlankText, ...] = Field(min_length=1)
    repair_action: Literal["write_non_blank_reconciliation"] = "write_non_blank_reconciliation"

    @model_validator(mode="after")
    def validate_reconciliation_target(self) -> "JoinReconciliationRepairFact":
        if self.path != ("joinContracts", self.join_contract_id, "reconciliation"):
            raise ValueError("path must identify the join reconciliation")
        if len(self.allowed_difference_keys) != len(set(self.allowed_difference_keys)):
            raise ValueError("allowed difference keys must be unique")
        return self


class JoinEntryStateValueRepairFact(CamelModel):
    """Exact join-entry value compiled from sealed incoming edge effects."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.join_entry_state_value_missing",
        "semantic.join_entry_state_value_mismatch",
        "semantic.join_entry_state_value_not_json",
    ]
    path: tuple[str | int, ...]
    contract_version: str = Field(min_length=1)
    contract_hash: str = Field(min_length=64, max_length=64)
    state_key: NonBlankText
    expected_value: Any

    @model_validator(mode="after")
    def validate_exact_join_entry_path(self) -> "JoinEntryStateValueRepairFact":
        if (
            len(self.path) != 5
            or self.path[0] != "scenes"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "entryState"
            or self.path[3] != "facts"
            or self.path[4] != self.state_key
        ):
            raise ValueError("path must identify one scene entryState fact")
        # Ensure the frozen repair authority uses the same finite JSON
        # identity as the compiler and both validators before it is rendered.
        finite_canonical_json(self.expected_value)
        return self


class AudioTimingRepairFact(CamelModel):
    """One deterministic, path-bound correction for a timed audio event.

    Audio timing relates two sibling model fields and cannot be expressed by
    the portable provider JSON Schema subset.  The semantic validator owns the
    relationship, then supplies one exact replacement or removal action rather
    than asking a model to redo timing arithmetic from an error message.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.audio_timing"]
    path: tuple[str | int, ...]
    shot_local_id: NonBlankText
    event_index: int = Field(ge=0)
    start_offset_units: int = Field(ge=0)
    duration_units: int = Field(ge=1)
    shot_duration_units: int = Field(ge=1)
    repair_action: Literal["replace_duration", "remove_event"]
    replacement_duration_units: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_exact_timing_action(self) -> "AudioTimingRepairFact":
        # The shot index is intentionally not duplicated as an independently
        # mutable field.  It is the second component of the immutable issue
        # path, while ``event_index`` is the final selected event component.
        if (
            len(self.path) != 6
            or self.path[0] != "shots"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "audioPlan"
            or self.path[3] != "events"
            or self.path[4] != self.event_index
            or self.path[5] != "durationUnits"
        ):
            raise ValueError("path must identify one audioPlan event duration")
        remaining = self.shot_duration_units - self.start_offset_units
        if self.start_offset_units + self.duration_units <= self.shot_duration_units:
            raise ValueError("audio timing fact requires an out-of-bounds event")
        if remaining >= 1:
            if (
                self.repair_action != "replace_duration"
                or self.replacement_duration_units != remaining
            ):
                raise ValueError("replace_duration must use the exact remaining shot duration")
        elif (
            self.repair_action != "remove_event"
            or self.replacement_duration_units is not None
        ):
            raise ValueError("an event starting at or after shot end must be removed")
        return self


class RequiredEntityStateRepairFact(CamelModel):
    """Trusted Story Bible choices for one invalid Storyboard state.

    The model-authored invalid value and validator prose are deliberately not
    carried forward.  A correction receives only the immutable entity identity
    and the exact allowed values from the frozen Story Bible dependency.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.invalid_required_entity_state"]
    path: tuple[str | int, ...]
    entity_type: EntityType
    entity_id: NonBlankText
    allowed_states: tuple[NonBlankText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_issue_identity_and_allowed_states(
        self,
    ) -> "RequiredEntityStateRepairFact":
        if (
            len(self.path) != 5
            or self.path[0] != "shots"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "requiredEntityStates"
            or not isinstance(self.path[3], int)
            or isinstance(self.path[3], bool)
            or self.path[3] < 0
            or self.path[4] != "state"
        ):
            raise ValueError(
                "path must identify one requiredEntityStates state value"
            )
        if len(self.allowed_states) != len(set(self.allowed_states)):
            raise ValueError("allowedStates must be unique")
        return self


class ContinuityEntityStateRepairFact(CamelModel):
    """One source-bound Bible vocabulary repair at a continuity boundary.

    This fact deliberately names both the original response array path and
    its response-local parent identity.  A correction cannot evade the
    rejected assignment by deleting, replacing, or moving that entry.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.invalid_continuity_entity_state"]
    path: tuple[str | int, ...]
    target: ContinuityStateEndpoint
    entity_state_index: int = Field(ge=0)
    entity_type: EntityType
    entity_id: NonBlankText
    allowed_states: tuple[NonBlankText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_exact_response_target(self) -> "ContinuityEntityStateRepairFact":
        collections = {
            "scenes": ("scene", "localSceneId"),
            "beats": ("beat", "localBeatId"),
            "shots": ("shot", "localShotId"),
        }
        if (
            len(self.path) != 6
            or self.path[0] not in collections
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] not in {"entryState", "exitState"}
            or self.path[3] != "entityStates"
            or self.path[4] != self.entity_state_index
            or self.path[5] != "state"
        ):
            raise ValueError("path must identify one continuity entityStates state value")
        expected_kind, _identity = collections[self.path[0]]
        if (
            self.target.kind != expected_kind
            or self.target.id_scope != "response_local"
            or self.target.state != ("entry" if self.path[2] == "entryState" else "exit")
        ):
            raise ValueError("target must identify the exact response-local continuity boundary")
        if len(self.allowed_states) != len(set(self.allowed_states)):
            raise ValueError("allowedStates must be unique")
        return self


class LegacyStoryboardTimingRepairPlanFact(CamelModel):
    """Read-only v15 timing-plan evidence.

    The previous timing-plan shape predates a binding to the source guidance.
    It remains parseable so terminal traces retain their original JSON, but is
    deliberately outside the current discriminated union and is rejected if a
    nonterminal correction ever tries to execute it.
    """

    model_config = CamelModel.model_config | {"frozen": True, "extra": "allow"}

    code: Literal[
        "semantic.shot_duration_budget_exceeded",
        "semantic.cue_duration_exceeds_shot",
    ]
    path: tuple[str | int, ...]
    plan: dict[str, Any]
    plan_hash: str = Field(min_length=1)


CurrentSemanticRepairFact: TypeAlias = Annotated[
    DialogueCapacityRepairFact
    | DialogueNodeBudgetRepairFact
    | CueOrderRepairFact
    | StoryboardTimingRepairPlanFact
    | JoinAllowedDifferencesRepairFact
    | JoinStateEffectRepairFact
    | ContinuitySequenceRepairFact
    | EdgeStateEffectJsonRepairFact
    | JoinReconciliationRepairFact
    | JoinEntryStateValueRepairFact
    | EdgeEntryEntityStateRepairFact
    | AudioTimingRepairFact
    | RequiredEntityStateRepairFact
    | RequiredEntityPresenceRepairFact
    | ContinuityEntityStateRepairFact,
    Field(discriminator="code"),
]
# Timing witnesses are intentionally outside the current discriminated union:
# their legacy codes now identify executable plans.  The parser below keeps
# sealed historical evidence readable without letting old facts enter a new
# correction contract.
SemanticRepairFact: TypeAlias = (
    CurrentSemanticRepairFact
    | DialogueTimingRepairFact
    | ShotDurationBudgetRepairFact
    | CueDurationFitRepairFact
    | LegacyStoryboardTimingRepairPlanFact
)
_SEMANTIC_REPAIR_FACT_ADAPTER = TypeAdapter(CurrentSemanticRepairFact)


FragmentOutput: TypeAlias = SceneBeatsFragmentOutput | StoryboardFragmentOutput


class StoryGraphContentFillValidationAdapter(ValidationAdapter[StoryGraphV2]):
    """Validate model prose against a frozen topology before canonicalizing it."""

    schema_id = STORY_GRAPH_CONTENT_FILL_SCHEMA_ID

    def __init__(self, *, topology: StoryGraphTopology, brief: ProjectBrief, bible: StoryBibleV2 | None = None) -> None:
        self.topology = topology
        self.brief = brief
        self.bible = bible

    def json_schema(self) -> dict[str, Any]:
        return story_graph_content_fill_schema(self.topology)

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        if context.stage != StageName.STORY_GRAPH.value:
            raise ValueError("Story Graph content fill received a different stage context")
        presence_issues = _presence_issues(value, self.json_schema())
        if presence_issues:
            return ValidationReport(accepted=False, issues=presence_issues)
        try:
            fill = StoryGraphContentFill.model_validate(value, by_alias=True, by_name=False)
        except ValidationError as exc:
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code=f"schema.{error['type']}",
                        message=error["msg"],
                        path=tuple(error.get("loc") or ()),
                    )
                    for error in exc.errors(include_url=False, include_context=False)
                ),
            )
        try:
            if self.bible is None and any(item.entity_state_effects for item in fill.edges):
                return ValidationReport(
                    accepted=False,
                    issues=(ValidationIssue(
                        code="context.story_bible_required",
                        message="typed graph entity-state effects require a sealed story bible",
                        path=("edges",),
                    ),),
                )
            graph = bind_story_graph_content_fill(
                self.topology, fill, brief=self.brief, bible=self.bible
            )
        except StoryGraphContentBindingError as exc:
            binding_issues = tuple(
                ValidationIssue(
                    code=issue["code"],
                    message=issue["message"],
                    path=tuple(part for part in issue["path"].split(".") if part),
                )
                for issue in exc.issues
            )
            diagnostic_issues: tuple[ValidationIssue, ...] = ()
            if any(
                issue.code == "semantic.join_allowed_differences_must_be_required"
                for issue in binding_issues
            ):
                # Normal binding cannot construct a canonical join when an
                # allowed key is absent from requiredStateKeys.  Its
                # normalized diagnostic view reuses the join-state compiler
                # to reveal independent pre-existing join defects without
                # accepting or changing the rejected response.
                diagnostic_issues = tuple(
                    ValidationIssue(
                        code=issue["code"],
                        message=issue["message"],
                        path=tuple(part for part in issue["path"].split(".") if part),
                    )
                    for issue in story_graph_content_fill_join_diagnostic_issues(
                        self.topology,
                        fill,
                    )
                )
            return ValidationReport(
                accepted=False,
                issues=(*binding_issues, *diagnostic_issues),
            )
        finite_json_issues: list[ValidationIssue] = []
        for edge in graph.edges:
            for state_key, state_value in edge.state_effects.items():
                try:
                    finite_canonical_json(state_value)
                except (TypeError, ValueError):
                    # ``model_dump(mode=\"json\")`` would coerce NaN to null,
                    # which erases the rejection before a correction fact can
                    # bind it. Validate the trusted binder's still-native
                    # value first and preserve the edge-local evidence.
                    finite_json_issues.append(
                        ValidationIssue(
                            code="semantic.state_effect_not_json",
                            message="story edge state effects must be finite canonical JSON values",
                            path=("edges", edge.id, "stateEffects", state_key),
                        )
                    )
        if finite_json_issues:
            return ValidationReport(accepted=False, issues=tuple(finite_json_issues))
        # The topology binder remains the deterministic graph authority.  Its
        # result is projected into the explicit V2 authoring schema only after
        # that topology contract has been checked.
        try:
            canonical_graph = StoryGraphV2.model_validate(
                graph.model_dump(mode="json", by_alias=True)
            )
        except ValidationError as exc:
            # The binder already verifies the complete V2 projection.  Keep a
            # defensive conversion here so future V2 additions cannot turn a
            # model-content mistake into ``validation.internal_error``.
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code="semantic.v2_projection_invalid",
                        message=error["msg"],
                        path=tuple(error.get("loc") or ()),
                    )
                    for error in exc.errors(include_url=False, include_context=False)
                ),
            )
        try:
            # The primary adapter is the first boundary at which a response
            # can enter a correction loop.  Run the same strict graph
            # semantics used by canonical installation here; otherwise an
            # ordinary non-finite edge value can bypass fact projection until
            # a later stage, where no exact graph correction exists.
            validate_story_graph(canonical_graph, self.brief, strict_v2=True, bible=self.bible)
        except DomainValidationError as exc:
            return ValidationReport(accepted=False, issues=exc.issues)
        return ValidationReport(accepted=True, value=canonical_graph)


class WorkUnitPromptContract(_FrozenModel):
    """Compact public provenance for a compiled unit request.

    The fields identify the exact public prompt/schema contract without
    duplicating user text or server-managed canonical objects into traces.
    Scene Beats additionally carries its small deterministic capacity guidance
    so a later bounded correction can obey the same frozen limits.
    """

    contract_version: str = WORK_UNIT_PROMPT_CONTRACT_VERSION
    correction_policy_version: str = CORRECTION_POLICY_VERSION
    # Optional so terminal historical contracts round-trip without injecting
    # identities that did not exist when they were sealed.  Current contracts
    # set all four explicitly, including primary attempts, so a later
    # correction cannot silently execute under a changed compiler.
    correction_directive_registry_version: str | None = None
    correction_evidence_projection_version: str | None = None
    correction_issue_selection_version: str | None = None
    correction_response_schema_version: str | None = None
    # These hashes are correction-variant provenance.  Primary attempts have
    # no selected directives/evidence overlay; correction attempts require all
    # four and bind the exact issue selection, prompt projection, and narrowed
    # response schema.
    correction_directive_set_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_evidence_projection_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_issue_selection_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_response_schema_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_ordinal: int | None = Field(default=None, ge=1, le=2)
    correction_strategy: Literal[
        "repair_previous_final", "reconstruct_from_schema"
    ] | None = None
    stage_plan_hash: str = Field(min_length=1)
    work_unit_id: str = Field(min_length=1)
    stage: StageName
    selector_kind: WorkUnitSelectorKind
    selector_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_spec_hash: str = Field(min_length=1)
    schema_id: str = Field(min_length=1)
    schema_hash: str = Field(min_length=1)
    variables_hash: str = Field(min_length=1)
    rendered_hash: str = Field(min_length=1)
    work_unit_input_hash: str = Field(min_length=1)
    dependency_hash: str = Field(min_length=1)
    dialogue_timing_profile_version: str | None = None
    dialogue_timing_profile_hash: str | None = None
    scene_timing_allocation_version: str | None = None
    scene_timing_allocation_hash: str | None = None
    node_duration_budget_units: int | None = Field(default=None, ge=1)
    dialogue_capacity_policy_version: str | None = None
    dialogue_capacity_plan_hash: str | None = None
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None = None
    join_state_value_contract_version: str | None = None
    join_state_value_contract_hash: str | None = None
    edge_entry_state_contract_version: str | None = None
    edge_entry_state_contract_hash: str | None = None
    # Current Storyboard corrections require a tiny projection of sealed cue
    # timings and the selected scene cap.  It contains no dialogue text,
    # provider response, secret, or mutable project data.
    storyboard_timing_guidance: StoryboardTimingGuidance | None = None
    unit_dependency_hash: str = Field(min_length=1)
    fragment_id_binding_version: str = FRAGMENT_ID_BINDING_VERSION
    # Optional solely so historical prompt evidence can be parsed and hashed
    # without injecting a field it never contained.  Audio IDs are a distinct
    # binding namespace and must not perturb existing scene/beat/shot IDs.
    audio_event_id_binding_version: str | None = None
    storyboard_primary_coverage_binding_version: str | None = None

    def snapshot_dump(self) -> dict[str, Any]:
        """Serialize only the fields that belonged to the sealed contract.

        Historical trace readers may parse an older contract for inspection,
        but they must not inject later optional defaults when comparing or
        hashing that evidence.  Current compilers explicitly set every current
        identity field, so ``exclude_unset`` loses nothing for new attempts.
        """

        return self.model_dump(
            mode="json",
            by_alias=True,
            exclude_unset=True,
        )

    @model_validator(mode="after")
    def validate_correction_schedule(self) -> WorkUnitPromptContract:
        """Keep primary and correction provenance structurally unambiguous."""

        has_ordinal = self.correction_ordinal is not None
        has_strategy = self.correction_strategy is not None
        if has_ordinal != has_strategy:
            raise ValueError(
                "correction_ordinal and correction_strategy must be set together"
            )
        if has_ordinal:
            expected_strategy = {
                1: "repair_previous_final",
                2: "reconstruct_from_schema",
            }[self.correction_ordinal]
            if self.correction_strategy != expected_strategy:
                raise ValueError(
                    "correction_strategy does not match correction_ordinal"
                )
        correction_versions = (
            self.correction_directive_registry_version,
            self.correction_evidence_projection_version,
            self.correction_issue_selection_version,
            self.correction_response_schema_version,
        )
        if self.contract_version == WORK_UNIT_PROMPT_CONTRACT_VERSION:
            if self.correction_policy_version != CORRECTION_POLICY_VERSION:
                raise ValueError(
                    "current work-unit contracts require the current correction policy"
                )
            expected_versions = (
                CORRECTION_DIRECTIVE_REGISTRY_VERSION,
                CORRECTION_EVIDENCE_PROJECTION_VERSION,
                CORRECTION_ISSUE_SELECTION_VERSION,
                CORRECTION_RESPONSE_SCHEMA_VERSION,
            )
            if correction_versions != expected_versions:
                raise ValueError(
                    "current work-unit contracts require the current correction compiler versions"
                )
        correction_hashes = (
            self.correction_directive_set_hash,
            self.correction_evidence_projection_hash,
            self.correction_issue_selection_hash,
            self.correction_response_schema_hash,
        )
        has_all_correction_hashes = all(value is not None for value in correction_hashes)
        if any(value is not None for value in correction_hashes) != has_all_correction_hashes:
            raise ValueError("correction compiler hashes must be set together")
        if has_ordinal != has_all_correction_hashes:
            raise ValueError(
                "correction attempts and correction compiler hashes must be set together"
            )
        has_timing_version = self.dialogue_timing_profile_version is not None
        has_timing_hash = self.dialogue_timing_profile_hash is not None
        if has_timing_version != has_timing_hash:
            raise ValueError(
                "dialogue timing profile version and hash must be set together"
            )
        if self.stage == StageName.SCENE_BEATS and not has_timing_version:
            raise ValueError("Scene Beats contracts require a dialogue timing profile")
        if self.stage != StageName.SCENE_BEATS and has_timing_version:
            raise ValueError("dialogue timing profiles only belong to Scene Beats")
        timing_allocation_values = (
            self.scene_timing_allocation_version,
            self.scene_timing_allocation_hash,
            self.node_duration_budget_units,
        )
        has_timing_allocation = all(value is not None for value in timing_allocation_values)
        if any(value is not None for value in timing_allocation_values) != has_timing_allocation:
            raise ValueError("scene timing allocation fields must be set together")
        if self.stage == StageName.SCENE_BEATS and not has_timing_allocation:
            raise ValueError("Scene Beats contracts require a scene timing allocation")
        if self.stage != StageName.SCENE_BEATS and has_timing_allocation:
            raise ValueError("scene timing allocations only belong to Scene Beats")
        capacity_values = (
            self.dialogue_capacity_policy_version,
            self.dialogue_capacity_plan_hash,
            self.dialogue_capacity_guidance,
        )
        has_capacity = all(value is not None for value in capacity_values)
        if any(value is not None for value in capacity_values) != has_capacity:
            raise ValueError("dialogue capacity fields must be set together")
        if self.stage == StageName.SCENE_BEATS and not has_capacity:
            raise ValueError("Scene Beats contracts require dialogue capacity")
        if self.stage != StageName.SCENE_BEATS and has_capacity:
            raise ValueError("dialogue capacity only belongs to Scene Beats")
        if has_capacity:
            assert self.dialogue_capacity_guidance is not None
            if self.dialogue_capacity_guidance.node_id != self.selector_id:
                raise ValueError(
                    "dialogue capacity guidance must match the selected Story Graph node"
                )
        has_join_version = self.join_state_value_contract_version is not None
        has_join_hash = self.join_state_value_contract_hash is not None
        if has_join_version != has_join_hash:
            raise ValueError(
                "join state value contract version and hash must be set together"
            )
        has_join_contract = has_join_version and has_join_hash
        if (
            self.stage == StageName.SCENE_BEATS
            and self.contract_version == WORK_UNIT_PROMPT_CONTRACT_VERSION
            and not has_join_contract
        ):
            raise ValueError(
                "current Scene Beats contracts require exact join state values"
            )
        if self.stage != StageName.SCENE_BEATS and has_join_contract:
            raise ValueError(
                "join state value contracts only belong to Scene Beats"
            )
        has_edge_entry_version = self.edge_entry_state_contract_version is not None
        has_edge_entry_hash = self.edge_entry_state_contract_hash is not None
        if has_edge_entry_version != has_edge_entry_hash:
            raise ValueError(
                "edge entry state contract version and hash must be set together"
            )
        has_edge_entry_contract = has_edge_entry_version and has_edge_entry_hash
        if (
            self.stage == StageName.SCENE_BEATS
            and self.contract_version == WORK_UNIT_PROMPT_CONTRACT_VERSION
            and not has_edge_entry_contract
        ):
            raise ValueError(
                "current Scene Beats contracts require exact typed edge-entry states"
            )
        if self.stage != StageName.SCENE_BEATS and has_edge_entry_contract:
            raise ValueError(
                "edge entry state contracts only belong to Scene Beats"
            )
        if (
            self.stage == StageName.STORYBOARD
            and self.contract_version == WORK_UNIT_PROMPT_CONTRACT_VERSION
            and self.storyboard_timing_guidance is None
        ):
            raise ValueError("current Storyboard contracts require timing guidance")
        if self.stage != StageName.STORYBOARD and self.storyboard_timing_guidance is not None:
            raise ValueError("Storyboard timing guidance only belongs to Storyboard")
        if (
            self.storyboard_timing_guidance is not None
            and self.storyboard_timing_guidance.scene_id != self.selector_id
        ):
            raise ValueError("Storyboard timing guidance must match the selected scene")
        has_audio_event_binding = self.audio_event_id_binding_version is not None
        if (
            self.stage == StageName.STORYBOARD
            and self.contract_version == WORK_UNIT_PROMPT_CONTRACT_VERSION
            and not has_audio_event_binding
        ):
            raise ValueError(
                "current Storyboard contracts require audio event ID provenance"
            )
        if self.stage != StageName.STORYBOARD and has_audio_event_binding:
            raise ValueError(
                "audio event ID provenance only belongs to Storyboard"
            )
        if (
            self.contract_version == WORK_UNIT_PROMPT_CONTRACT_VERSION
            and has_audio_event_binding
            and self.audio_event_id_binding_version != AUDIO_EVENT_ID_BINDING_VERSION
        ):
            raise ValueError("unsupported audio event ID binding version")
        return self


@dataclass(frozen=True)
class CompiledWorkUnitRequest:
    """Pure hand-off object consumed later by Pipeline/Provider adapters."""

    rendered: RenderedPrompt
    validator: ValidationAdapter[Any]
    contract: WorkUnitPromptContract
    response_schema: dict[str, Any]
    # Audit-only correction selection. The runner persists this beside the
    # rendered messages but never sends it through a provider adapter.
    audit_issue_selection: dict[str, Any] | None = None
    # Executable exact facts are retained only in memory so trusted
    # application validation can enforce them even when a provider does not
    # support native JSON Schema. Recovery re-derives them from immutable
    # validation evidence; they are never silently reconstructed from prose.
    correction_repair_facts: tuple[SemanticRepairFact, ...] = ()


class WorkUnitFragmentValidationAdapter(ValidationAdapter[StageFragment]):
    """Presence-strict schema and selector-scoped semantic validation.

    The adapter validates the model-facing fragment first, then the trusted
    binder attaches the immutable StagePlan and work-unit IDs.  The binder is
    deliberately not part of the generated schema.
    """

    def __init__(
        self,
        *,
        stage_plan: StagePlan,
        work_unit: GenerationWorkUnit,
        brief: ProjectBrief,
        bible: StoryBibleV2,
        scoped_context: Mapping[str, Any],
        dialogue_timing_profile: DialogueTimingProfile | None,
        dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
        storyboard_timing_guidance: StoryboardTimingGuidance | None,
    ) -> None:
        if work_unit.stage not in {StageName.SCENE_BEATS, StageName.STORYBOARD}:
            raise WorkUnitContractError("fragment adapter only supports sharded stages")
        self.stage_plan = stage_plan
        self.work_unit = work_unit
        self.brief = brief
        self.bible = bible
        self.scoped_context = dict(scoped_context)
        self.dialogue_timing_profile = dialogue_timing_profile
        self.dialogue_capacity_guidance = dialogue_capacity_guidance
        self.storyboard_timing_guidance = storyboard_timing_guidance
        self.model_type: type[FragmentOutput]
        if work_unit.stage == StageName.SCENE_BEATS:
            if dialogue_timing_profile is None:
                raise WorkUnitContractError(
                    "Scene Beats fragment adapter requires a dialogue timing profile"
                )
            if stage_plan.scene_timing_allocation is None:
                raise WorkUnitContractError(
                    "Scene Beats fragment adapter requires a frozen scene timing allocation"
                )
            if dialogue_capacity_guidance is None:
                raise WorkUnitContractError(
                    "Scene Beats fragment adapter requires frozen dialogue capacity guidance"
                )
            self.model_type = SceneBeatsFragmentOutput
            self.schema_id = SCENE_BEATS_FRAGMENT_SCHEMA_ID
        else:
            if dialogue_capacity_guidance is not None:
                raise WorkUnitContractError(
                    "dialogue capacity guidance only belongs to Scene Beats"
                )
            if storyboard_timing_guidance is None:
                raise WorkUnitContractError(
                    "Storyboard fragment adapter requires frozen timing guidance"
                )
            self.model_type = StoryboardFragmentOutput
            self.schema_id = STORYBOARD_FRAGMENT_SCHEMA_ID

    def json_schema(self) -> dict[str, Any]:
        schema = explicit_presence_json_schema(
            self.model_type.model_json_schema(by_alias=True)
        )
        _bind_fragment_foreign_keys(
            schema,
            work_unit=self.work_unit,
            brief=self.brief,
            bible=self.bible,
            scoped_context=self.scoped_context,
            dialogue_capacity_guidance=self.dialogue_capacity_guidance,
            storyboard_timing_guidance=self.storyboard_timing_guidance,
        )
        return inline_local_json_references(schema)

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        if context.stage != self.work_unit.stage.value:
            raise ValueError(
                f"Validation context stage {context.stage!r} does not match "
                f"work-unit stage {self.work_unit.stage.value!r}"
            )
        issues = _presence_issues(value, self.json_schema())
        if issues:
            return ValidationReport(accepted=False, issues=issues)
        try:
            parsed = self.model_type.model_validate(
                _canonicalize_model_local_ids(value, stage=self.work_unit.stage),
                by_alias=True,
                by_name=False,
            )
        except ValidationError as exc:
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code=f"schema.{error['type']}",
                        message=error["msg"],
                        path=tuple(error.get("loc") or ()),
                    )
                    for error in exc.errors(include_url=False, include_context=False)
                ),
            )
        semantic_issues = _fragment_semantic_issues(
            parsed,
            work_unit=self.work_unit,
            brief=self.brief,
            bible=self.bible,
            scoped_context=self.scoped_context,
            dialogue_timing_profile=self.dialogue_timing_profile,
            dialogue_capacity_guidance=self.dialogue_capacity_guidance,
        )
        if semantic_issues:
            return ValidationReport(accepted=False, issues=semantic_issues)
        # Model-controlled fields are made canonical-compatible by the closed
        # response models and semantic checks above.  Any exception in this
        # trusted binder is therefore a program/plan fault and must cross the
        # runner's fail-closed validation boundary rather than authorize a
        # model correction.
        fragment = _bind_fragment(
            parsed,
            stage_plan=self.stage_plan,
            work_unit=self.work_unit,
            dialogue_timing_profile=self.dialogue_timing_profile,
            scene_timing_allocation=self.stage_plan.scene_timing_allocation,
        )
        return ValidationReport(accepted=True, value=fragment)


def compile_work_unit_request(
    *,
    generation_plan: GenerationPlan,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    brief: ProjectBrief,
    canonical_snapshot: BaseModel | Mapping[str, Any],
    instructions: str = "",
    stage_constraints: Mapping[str, Any] | None = None,
    story_graph_topology: StoryGraphTopology | None = None,
    renderer: PromptRenderer | None = None,
) -> CompiledWorkUnitRequest:
    """Compile one immutable work unit without a provider or persistence call.

    ``canonical_snapshot`` and ``instructions`` are checked against the
    enqueue-time GenerationPlan.  ``dependencies`` are rebuilt through
    ``planning.work_unit_context`` and checked against the unit hash.  Thus a
    prompt cannot quietly widen from one node/scene into a full later-stage
    aggregate.
    """

    _assert_unit_membership(generation_plan, stage_plan, work_unit)
    if work_unit.stage == StageName.SCENE_BEATS:
        graph = dependencies.get(StageName.STORY_GRAPH)
        if not isinstance(graph, StoryGraphV2):
            raise WorkUnitContractError(
                "Scene Beats compilation requires a sealed StoryGraph"
            )
        try:
            expected_timing = plan_scene_timing_allocation(graph=graph, brief=brief)
        except SceneTimingAllocationError as exc:
            raise WorkUnitContractError(str(exc)) from exc
        if stage_plan.scene_timing_allocation != expected_timing:
            raise WorkUnitContractError(
                "Scene Beats timing allocation does not match the frozen graph and brief"
            )
        if (
            stage_plan.dialogue_timing_profile is None
            or stage_plan.dialogue_capacity_plan is None
        ):
            raise WorkUnitContractError(
                "Scene Beats compilation requires frozen dialogue capacity inputs"
            )
        try:
            expected_capacity = plan_dialogue_capacity(
                scene_timing_allocation=expected_timing,
                dialogue_timing_profile=stage_plan.dialogue_timing_profile,
                policy_version=stage_plan.dialogue_capacity_plan.policy_version,
                authoring_language=stage_plan.dialogue_capacity_plan.authoring_language,
            )
        except DialogueCapacityPlanningError as exc:
            raise WorkUnitContractError(str(exc)) from exc
        if stage_plan.dialogue_capacity_plan != expected_capacity:
            raise WorkUnitContractError(
                "Scene Beats dialogue capacity does not match the frozen timing inputs"
            )
    snapshot_json = canonical_json(_json_value(canonical_snapshot))
    # Repository-backed plans use CanonicalSnapshot.snapshot_hash as their
    # immutable identity fingerprint.  The serialized byte count remains a
    # separate guard against passing a different snapshot representation.  Pure
    # callers without the domain object retain the content-hash contract used
    # by create_generation_plan(canonical_snapshot=...).
    snapshot_identity = (
        canonical_snapshot.snapshot_hash
        if isinstance(canonical_snapshot, CanonicalSnapshot)
        else sha256_text(snapshot_json)
    )
    if snapshot_identity != generation_plan.canonical_snapshot_hash:
        raise WorkUnitContractError("canonical_snapshot does not match the generation plan")
    if len(snapshot_json.encode("utf-8")) != generation_plan.canonical_snapshot_bytes:
        raise WorkUnitContractError("canonical_snapshot byte size does not match the generation plan")
    if sha256_text(instructions) != generation_plan.instructions_hash:
        raise WorkUnitContractError("instructions do not match the generation plan")
    if len(instructions.encode("utf-8")) != generation_plan.instructions_bytes:
        raise WorkUnitContractError("instructions byte size does not match the generation plan")

    try:
        scoped_context = work_unit_context(
            work_unit,
            dependencies=dependencies,
            scene_timing_allocation=stage_plan.scene_timing_allocation,
            dialogue_timing_profile=stage_plan.dialogue_timing_profile,
            dialogue_capacity_plan=stage_plan.dialogue_capacity_plan,
        )
    except PlanningError as exc:
        raise WorkUnitContractError(str(exc)) from exc
    if content_hash(scoped_context) != work_unit.unit_dependency_hash:
        raise WorkUnitContractError("work-unit context does not match its frozen hash")

    storyboard_timing_guidance = (
        _storyboard_timing_guidance(scoped_context, brief=brief)
        if work_unit.stage == StageName.STORYBOARD
        else None
    )

    adapter = _validator_for_unit(
        work_unit=work_unit,
        stage_plan=stage_plan,
        brief=brief,
        dependencies=dependencies,
        scoped_context=scoped_context,
        story_graph_topology=story_graph_topology,
        storyboard_timing_guidance=storyboard_timing_guidance,
    )
    schema = adapter.json_schema()
    prompt_id, variables = _prompt_variables(
        work_unit=work_unit,
        canonical_snapshot=_json_value(canonical_snapshot),
        scoped_context=scoped_context,
        stage_constraints=dict(stage_constraints or {}),
        schema=schema,
        story_graph_topology=story_graph_topology,
    )
    active_renderer = renderer or PromptRenderer()
    rendered = active_renderer.render(prompt_id, variables)
    join_state_requirements = (
        _continuity_requirements(scoped_context)
        if work_unit.stage == StageName.SCENE_BEATS
        else None
    )
    compiled_edge_entry_requirements = (
        edge_entry_state_requirements(scoped_context)
        if work_unit.stage == StageName.SCENE_BEATS
        else None
    )
    if work_unit.stage == StageName.SCENE_BEATS:
        if (
            stage_plan.join_state_value_contract_version is None
            or stage_plan.join_state_value_contract_hash is None
            or join_state_requirements is None
            or stage_plan.edge_entry_state_contract_version is None
            or stage_plan.edge_entry_state_contract_hash is None
            or compiled_edge_entry_requirements is None
        ):
            raise WorkUnitContractError(
                "current Scene Beats StagePlan has no frozen join state value contract"
            )
        if (
            join_state_requirements["contractVersion"]
            != stage_plan.join_state_value_contract_version
            or join_state_requirements["contractHash"]
            != stage_plan.join_state_value_contract_hash
        ):
            raise WorkUnitContractError(
                "Scene Beats context does not match the StagePlan join state value contract"
            )
        if (
            compiled_edge_entry_requirements["contractVersion"]
            != stage_plan.edge_entry_state_contract_version
            or compiled_edge_entry_requirements["contractHash"]
            != stage_plan.edge_entry_state_contract_hash
        ):
            raise WorkUnitContractError(
                "Scene Beats context does not match the StagePlan typed edge-entry contract"
            )
    contract = WorkUnitPromptContract(
        contract_version=WORK_UNIT_PROMPT_CONTRACT_VERSION,
        correction_policy_version=CORRECTION_POLICY_VERSION,
        correction_directive_registry_version=CORRECTION_DIRECTIVE_REGISTRY_VERSION,
        correction_evidence_projection_version=CORRECTION_EVIDENCE_PROJECTION_VERSION,
        correction_issue_selection_version=CORRECTION_ISSUE_SELECTION_VERSION,
        correction_response_schema_version=CORRECTION_RESPONSE_SCHEMA_VERSION,
        correction_ordinal=None,
        correction_strategy=None,
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=work_unit.unit_id,
        stage=work_unit.stage,
        selector_kind=work_unit.selector.kind,
        selector_id=work_unit.selector.stable_id,
        prompt_id=prompt_id,
        prompt_version=rendered.trace.prompt_version,
        prompt_spec_hash=rendered.trace.spec_hash,
        schema_id=adapter.schema_id,
        schema_hash=sha256_text(canonical_json(schema)),
        variables_hash=rendered.trace.input_hash,
        rendered_hash=rendered.trace.rendered_hash,
        work_unit_input_hash=work_unit.input_hash,
        dependency_hash=work_unit.dependency_hash,
        unit_dependency_hash=work_unit.unit_dependency_hash,
        fragment_id_binding_version=FRAGMENT_ID_BINDING_VERSION,
        dialogue_timing_profile_version=(
            adapter.dialogue_timing_profile.version
            if isinstance(adapter, WorkUnitFragmentValidationAdapter)
            and adapter.dialogue_timing_profile is not None
            else None
        ),
        dialogue_timing_profile_hash=(
            dialogue_timing_profile_hash(adapter.dialogue_timing_profile)
            if isinstance(adapter, WorkUnitFragmentValidationAdapter)
            and adapter.dialogue_timing_profile is not None
            else None
        ),
        scene_timing_allocation_version=(
            stage_plan.scene_timing_allocation.allocation_version
            if stage_plan.scene_timing_allocation is not None
            else None
        ),
        scene_timing_allocation_hash=(
            stage_plan.scene_timing_allocation.allocation_hash
            if stage_plan.scene_timing_allocation is not None
            else None
        ),
        node_duration_budget_units=(
            stage_plan.scene_timing_allocation.node_duration_budget(
                work_unit.selector.stable_id
            )
            if stage_plan.scene_timing_allocation is not None
            else None
        ),
        dialogue_capacity_policy_version=(
            stage_plan.dialogue_capacity_plan.policy_version
            if stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        dialogue_capacity_plan_hash=(
            stage_plan.dialogue_capacity_plan.capacity_plan_hash
            if stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        dialogue_capacity_guidance=(
            stage_plan.dialogue_capacity_plan.guidance_for(
                work_unit.selector.stable_id
            )
            if stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        join_state_value_contract_version=(
            str(join_state_requirements["contractVersion"])
            if join_state_requirements is not None
            else None
        ),
        join_state_value_contract_hash=(
            str(join_state_requirements["contractHash"])
            if join_state_requirements is not None
            else None
        ),
        edge_entry_state_contract_version=(
            str(compiled_edge_entry_requirements["contractVersion"])
            if compiled_edge_entry_requirements is not None
            else None
        ),
        edge_entry_state_contract_hash=(
            str(compiled_edge_entry_requirements["contractHash"])
            if compiled_edge_entry_requirements is not None
            else None
        ),
        storyboard_timing_guidance=storyboard_timing_guidance,
        audio_event_id_binding_version=(
            AUDIO_EVENT_ID_BINDING_VERSION
            if work_unit.stage == StageName.STORYBOARD
            else None
        ),
        storyboard_primary_coverage_binding_version=(
            STORYBOARD_PRIMARY_COVERAGE_BINDING_VERSION
            if work_unit.stage == StageName.STORYBOARD
            else None
        ),
    )
    return CompiledWorkUnitRequest(
        rendered=rendered,
        validator=adapter,
        contract=contract,
        response_schema=schema,
    )


def _storyboard_timing_guidance(
    scoped_context: Mapping[str, Any],
    *,
    brief: ProjectBrief,
) -> StoryboardTimingGuidance:
    """Freeze all text-free timing identities before schema or provider work."""

    scene = scoped_context.get("dramatic_scene")
    beats = scoped_context.get("beats")
    cues = scoped_context.get("dialogue_cues")
    if not isinstance(scene, Mapping) or not isinstance(beats, list) or not isinstance(cues, list):
        raise WorkUnitContractError("Storyboard context has no valid timing scope")
    scene_id = scene.get("id")
    scene_budget = scene.get("durationBudgetUnits")
    if (
        not isinstance(scene_id, str)
        or not scene_id
        or not isinstance(scene_budget, int)
        or isinstance(scene_budget, bool)
        or scene_budget < 1
    ):
        raise WorkUnitContractError("Storyboard context has no valid frozen scene duration budget")
    try:
        return build_storyboard_timing_guidance(
            scene_id=scene_id,
            scene_duration_budget_units=scene_budget,
            min_shots=brief.shots_per_scene_min,
            configured_max_shots=brief.shots_per_scene_max,
            beats=beats,
            cues=cues,
        )
    except StoryboardTimingInfeasibleError as exc:
        raise WorkUnitContractError(
            "sealed Storyboard timing cannot fit the frozen dramatic-scene budget",
            code=exc.code,
        ) from exc
    except (KeyError, ValueError) as exc:
        raise WorkUnitContractError("Storyboard context has invalid frozen timing identities") from exc


def _assert_unit_membership(
    generation_plan: GenerationPlan,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
) -> None:
    if generation_plan.plan_hash != stage_plan.generation_plan_hash:
        raise WorkUnitContractError("StagePlan does not belong to the GenerationPlan")
    if work_unit not in stage_plan.work_units:
        raise WorkUnitContractError("work unit does not belong to the StagePlan")
    if work_unit.stage != stage_plan.stage:
        raise WorkUnitContractError("work unit stage does not match the StagePlan")
    if work_unit.dependency_hash != stage_plan.dependency_hash:
        raise WorkUnitContractError("work unit dependency hash does not match the StagePlan")
    try:
        assert_work_unit_input_contract(generation_plan, work_unit)
    except PlanningError as exc:
        raise WorkUnitContractError(str(exc)) from exc


def _validator_for_unit(
    *,
    work_unit: GenerationWorkUnit,
    stage_plan: StagePlan,
    brief: ProjectBrief,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    scoped_context: Mapping[str, Any],
    story_graph_topology: StoryGraphTopology | None,
    storyboard_timing_guidance: StoryboardTimingGuidance | None,
) -> ValidationAdapter[Any]:
    if work_unit.stage == StageName.STORY_BIBLE:
        return CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=brief)
    bible = dependencies.get(StageName.STORY_BIBLE)
    if not isinstance(bible, StoryBibleV2):
        raise WorkUnitContractError(f"{work_unit.stage.value} requires a sealed StoryBible")
    if work_unit.stage == StageName.STORY_GRAPH:
        if story_graph_topology is not None:
            return StoryGraphContentFillValidationAdapter(
                topology=story_graph_topology, brief=brief, bible=bible
            )
        return CanonicalStageValidationAdapter(StageName.STORY_GRAPH, brief=brief, bible=bible)
    return WorkUnitFragmentValidationAdapter(
        stage_plan=stage_plan,
        work_unit=work_unit,
        brief=brief,
        bible=bible,
        scoped_context=scoped_context,
        dialogue_timing_profile=(
            stage_plan.dialogue_timing_profile
            if work_unit.stage == StageName.SCENE_BEATS
            else None
        ),
        dialogue_capacity_guidance=(
            stage_plan.dialogue_capacity_plan.guidance_for(
                work_unit.selector.stable_id
            )
            if work_unit.stage == StageName.SCENE_BEATS
            and stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        storyboard_timing_guidance=storyboard_timing_guidance,
    )


def _prompt_variables(
    *,
    work_unit: GenerationWorkUnit,
    canonical_snapshot: Any,
    scoped_context: Mapping[str, Any],
    stage_constraints: Mapping[str, Any],
    schema: Mapping[str, Any],
    story_graph_topology: StoryGraphTopology | None,
) -> tuple[str, dict[str, Any]]:
    if work_unit.stage == StageName.STORY_BIBLE:
        # The full snapshot remains the identity checked above, but the model
        # needs only the public creative input.  Stage heads, project IDs,
        # hashes, and capture timestamps are execution provenance, not prompt
        # material.
        project_input = canonical_snapshot.get("brief", canonical_snapshot)
        return "story_bible", {
            "project_input": project_input,
            "creative_constraints": stage_constraints,
            "json_schema": schema,
        }
    if work_unit.stage == StageName.STORY_GRAPH:
        variables = {
            "story_bible": scoped_context["story_bible"],
            "graph_constraints": stage_constraints,
            "json_schema": schema,
        }
        if story_graph_topology is not None:
            variables["story_graph_topology"] = story_graph_content_fill_manifest(
                story_graph_topology
            )
            return "story_graph_content_fill", variables
        return "story_graph", variables
    if work_unit.stage == StageName.SCENE_BEATS:
        return "scene_beats_fragment", {
            "story_bible": scoped_context["story_bible"],
            "story_node": scoped_context["story_node"],
            "incident_edges": scoped_context["incident_edges"],
            "join_contracts": scoped_context["join_contracts"],
            "continuity_requirements": _continuity_requirements(scoped_context),
            "edge_entry_state_requirements": edge_entry_state_requirements(scoped_context),
            "beat_constraints": stage_constraints,
            "node_timing_allocation": scoped_context["scene_timing_allocation"],
            "dialogue_capacity_guidance": scoped_context[
                "dialogue_capacity_guidance"
            ],
            "json_schema": schema,
        }
    return "storyboard_fragment", {
        "story_bible": scoped_context["story_bible"],
        "story_node": scoped_context["story_node"],
        "dramatic_scene": scoped_context["dramatic_scene"],
        "beats": scoped_context["beats"],
        "dialogue_cues": scoped_context["dialogue_cues"],
        "storyboard_constraints": stage_constraints,
        "json_schema": schema,
    }


def _bind_fragment(
    output: FragmentOutput,
    *,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
    dialogue_timing_profile: DialogueTimingProfile | None,
    scene_timing_allocation: SceneTimingAllocation | None,
) -> StageFragment:
    if isinstance(output, SceneBeatsFragmentOutput):
        if dialogue_timing_profile is None:
            raise WorkUnitContractError(
                "Scene Beats binding requires a frozen dialogue timing profile"
            )
        if scene_timing_allocation is None:
            raise WorkUnitContractError(
                "Scene Beats binding requires a frozen scene timing allocation"
            )
        scene_ids = {
            scene.local_scene_id: canonical_fragment_id(
                "scene",
                work_unit.selector.stable_id,
                str(scene.order),
            )
            for scene in output.scenes
        }
        beat_ids = {
            beat.local_beat_id: canonical_fragment_id(
                "beat",
                scene_ids[beat.scene_local_id],
                str(beat.order),
            )
            for beat in output.beats
        }
        bound_beats = tuple(
            BeatV2(
                id=beat_ids[beat.local_beat_id],
                scene_id=scene_ids[beat.scene_local_id],
                order=beat.order,
                description=beat.description,
                purpose=beat.purpose,
                visible_event=beat.visible_event,
                immediate_result=beat.immediate_result,
                dramatic_change=beat.dramatic_change,
                entry_state=beat.entry_state,
                exit_state=beat.exit_state,
                continuity_anchors=beat.continuity_anchors,
                continuity_delta=beat.continuity_delta,
            )
            for beat in output.beats
        )
        scene_local_id_by_beat = {
            beat.local_beat_id: beat.scene_local_id for beat in output.beats
        }
        scene_cue_duration_units: dict[str, int] = {}
        bound_cues: list[DialogueCue] = []
        for cue in output.dialogue_cues:
            duration_units = dialogue_timing_profile.estimate_text_duration_units(
                text=cue.text,
                language=cue.language,
                delivery=cue.delivery,
            )
            if duration_units is None:
                raise WorkUnitContractError(
                    "dialogue timing profile has no exact or wildcard rule"
                )
            scene_local_id = scene_local_id_by_beat[cue.beat_local_id]
            scene_cue_duration_units[scene_local_id] = (
                scene_cue_duration_units.get(scene_local_id, 0) + duration_units
            )
            bound_cues.append(
                DialogueCue(
                    id=canonical_fragment_id(
                        "dialogue-cue",
                        beat_ids[cue.beat_local_id],
                        str(cue.order),
                    ),
                    beat_id=beat_ids[cue.beat_local_id],
                    order=cue.order,
                    speaker_id=cue.speaker_id,
                    voice_over=cue.voice_over,
                    text=cue.text,
                    language=cue.language,
                    delivery=cue.delivery,
                    performance_notes=cue.performance_notes,
                    estimated_duration_units=duration_units,
                )
            )
        node_duration_budget_units = scene_timing_allocation.node_duration_budget(
            work_unit.selector.stable_id
        )
        scene_budgets = _allocate_scene_duration_budgets(
            output=output,
            scene_cue_duration_units=scene_cue_duration_units,
            node_duration_budget_units=node_duration_budget_units,
        )
        bound_scenes = tuple(
            DramaticSceneV2(
                id=scene_ids[scene.local_scene_id],
                story_node_id=work_unit.selector.stable_id,
                order=scene.order,
                title=scene.title,
                objective=scene.objective,
                location_id=scene.location_id,
                character_ids=scene.character_ids,
                beat_ids=[
                    beat_ids[beat.local_beat_id]
                    for beat in sorted(
                        (
                            item
                            for item in output.beats
                            if item.scene_local_id == scene.local_scene_id
                        ),
                        key=lambda item: item.order,
                    )
                ],
                duration_budget_units=scene_budgets[scene.local_scene_id],
                entry_state=scene.entry_state,
                exit_state=scene.exit_state,
            )
            for scene in output.scenes
        )
        return SceneBeatsFragment(
            stage_plan_hash=stage_plan.stage_plan_hash,
            work_unit_id=work_unit.unit_id,
            story_node_id=work_unit.selector.stable_id,
            scenes=bound_scenes,
            beats=bound_beats,
            dialogue_cues=tuple(bound_cues),
        )
    shot_ids = {
        shot.local_shot_id: canonical_fragment_id(
            "shot",
            work_unit.selector.stable_id,
            str(shot.order),
        )
        for shot in output.shots
    }
    return StoryboardFragment(
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=work_unit.unit_id,
        scene_id=work_unit.selector.stable_id,
        shots=tuple(
            ShotV2(
                id=shot_ids[shot.local_shot_id],
                scene_id=work_unit.selector.stable_id,
                order=shot.order,
                title=shot.title,
                shot_size=shot.shot_size,
                duration_units=shot.duration_units,
                camera_angle=shot.camera_angle,
                camera_movement=shot.camera_movement,
                composition=shot.composition,
                visual_intent=shot.visual_intent,
                motion_intent=shot.motion_intent,
                action=shot.action,
                transition=shot.transition,
                cue_ids=shot.cue_ids,
                audio_plan=AudioPlan(
                    events=[
                        AudioEvent(
                            id=canonical_audio_event_id(
                                shot_ids[shot.local_shot_id],
                                event_index,
                            ),
                            kind=event.kind,
                            description=event.description,
                            start_offset_units=event.start_offset_units,
                            duration_units=event.duration_units,
                        )
                        for event_index, event in enumerate(
                            shot.audio_plan.events,
                            start=1,
                        )
                    ]
                ),
                character_ids=shot.character_ids,
                location_id=shot.location_id,
                prop_ids=shot.prop_ids,
                required_entity_states=shot.required_entity_states,
                entry_state=shot.entry_state,
                exit_state=shot.exit_state,
            )
            for shot in output.shots
        ),
        shot_beat_links=tuple(
            [
                ShotBeatLinkV2(
                    shot_id=shot_ids[local_shot_id],
                    beat_id=beat_id,
                    role=V2CoverageRole.PRIMARY,
                    coverage_weight=1.0,
                )
                for beat_id, local_shot_id in sorted(
                    output.primary_shot_local_id_by_beat.items()
                )
            ]
            + [
                ShotBeatLinkV2(
                    shot_id=shot_ids[link.shot_local_id],
                    beat_id=link.beat_id,
                    role=V2CoverageRole.SUPPORTING,
                    coverage_weight=link.coverage_weight,
                )
                for link in output.supporting_beat_links
            ]
        ),
    )


def _allocate_scene_duration_budgets(
    *,
    output: SceneBeatsFragmentOutput,
    scene_cue_duration_units: Mapping[str, int],
    node_duration_budget_units: int,
) -> dict[str, int]:
    """Partition one frozen node cap without delegating arithmetic to a model.

    Each scene first receives the greater of one millisecond or its trusted
    dialogue minimum.  Remaining time follows the model's relative
    ``durationWeight`` using integer largest-remainder apportionment with a
    stable authored-order tie break.  Semantic validation proves feasibility
    before this trusted binder runs.
    """

    ordered = sorted(output.scenes, key=lambda scene: scene.order)
    minimums = {
        scene.local_scene_id: max(
            1, scene_cue_duration_units.get(scene.local_scene_id, 0)
        )
        for scene in ordered
    }
    remaining = node_duration_budget_units - sum(minimums.values())
    if remaining < 0:
        raise WorkUnitContractError(
            "dialogue minimums exceed the frozen Story Graph node budget"
        )
    weight_total = sum(scene.duration_weight for scene in ordered)
    allocations = dict(minimums)
    ranked_remainders: list[tuple[int, int, str]] = []
    distributed = 0
    for scene in ordered:
        numerator = remaining * scene.duration_weight
        share, remainder = divmod(numerator, weight_total)
        allocations[scene.local_scene_id] += share
        distributed += share
        ranked_remainders.append((-remainder, scene.order, scene.local_scene_id))
    for _negative_remainder, _order, scene_id in sorted(ranked_remainders)[
        : remaining - distributed
    ]:
        allocations[scene_id] += 1
    if sum(allocations.values()) != node_duration_budget_units:
        raise WorkUnitContractError("scene duration allocation did not conserve node budget")
    return allocations


def canonical_fragment_id(kind: str, *parts: str) -> str:
    """Bind model-local correlation IDs into the canonical UUID namespace.

    Sharded model calls cannot coordinate globally unique identifiers.  The
    trusted binder therefore derives canonical IDs solely from an immutable
    parent selector and an already-validated local order.  Model IDs remain in
    raw response evidence, while candidates and canonical stages contain only
    these reproducible IDs.
    """

    name = ":".join((FRAGMENT_ID_BINDING_VERSION, kind, *parts))
    return str(uuid5(NAMESPACE_URL, f"https://plotloom.local/{name}"))


def canonical_audio_event_id(shot_id: str, event_index: int) -> str:
    """Return the audio-event ID in its own versioned provenance namespace.

    Audio events have a separate binding contract from generic fragment IDs.
    Keeping the version in the UUID name—not merely in the prompt contract—
    ensures a future audio-only migration cannot silently claim a different
    provenance for unchanged identifiers.
    """

    if event_index < 1:
        raise ValueError("audio event index must be one-based and positive")
    name = ":".join((AUDIO_EVENT_ID_BINDING_VERSION, "audio-event", shot_id, str(event_index)))
    return str(uuid5(NAMESPACE_URL, f"https://plotloom.local/{name}"))


def _fragment_semantic_issues(
    output: FragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
    dialogue_timing_profile: DialogueTimingProfile | None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
) -> tuple[ValidationIssue, ...]:
    if isinstance(output, SceneBeatsFragmentOutput):
        if dialogue_timing_profile is None:
            raise WorkUnitContractError(
                "Scene Beats validation requires a frozen dialogue timing profile"
            )
        if dialogue_capacity_guidance is None:
            raise WorkUnitContractError(
                "Scene Beats validation requires frozen dialogue capacity guidance"
            )
        return _scene_beats_semantic_issues(
            output,
            work_unit=work_unit,
            bible=bible,
            scoped_context=scoped_context,
            dialogue_timing_profile=dialogue_timing_profile,
            dialogue_capacity_guidance=dialogue_capacity_guidance,
        )
    return _storyboard_semantic_issues(output, work_unit=work_unit, brief=brief, bible=bible, scoped_context=scoped_context)


def story_graph_join_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
) -> tuple[SemanticRepairFact, ...]:
    """Return only topology-bound, correction-safe Story Graph join facts.

    The response schema fixes content IDs but intentionally omits edge
    endpoints.  A correction therefore cannot reconstruct which edges enter a
    join unless this function projects that immutable topology into typed
    evidence.  It never selects creative state values except when every other
    convergent incoming edge already proves one exact finite value.
    """

    # Kept for direct historical tests/readers.  The execution path below
    # supplies topology and produces the richer current fact.  Without one we
    # retain only the original safe array replacement, never infer endpoints.
    try:
        fill = StoryGraphContentFill.model_validate(value, by_alias=True)
    except ValidationError:
        return ()
    joins_by_id = {join.id: join for join in fill.join_contracts}
    facts: list[SemanticRepairFact] = []
    for issue in issues:
        path = issue.path
        if (
            issue.code != "semantic.join_allowed_differences_must_be_required"
            or len(path) != 3
            or path[0] != "joinContracts"
            or not isinstance(path[1], str)
            or path[2] != "allowedDifferences"
        ):
            continue
        join = joins_by_id.get(path[1])
        if join is None:
            continue
        key_lists = (join.required_state_keys, join.allowed_differences)
        if any(
            any(not key.strip() for key in keys) or len(keys) != len(set(keys))
            for keys in key_lists
        ):
            continue
        missing = tuple(key for key in join.allowed_differences if key not in set(join.required_state_keys))
        if missing:
            facts.append(
                JoinAllowedDifferencesRepairFact(
                    code=issue.code,
                    path=path,
                    join_contract_id=join.id,
                    missing_required_state_keys=missing,
                    expected_required_state_keys=tuple((*join.required_state_keys, *missing)),
                    expected_allowed_differences=tuple(join.allowed_differences),
                )
            )
    return tuple(facts)


def _story_graph_edge_state_effect_json_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    topology: StoryGraphTopology | None,
) -> tuple[EdgeStateEffectJsonRepairFact, ...]:
    """Bind a malformed state effect to exactly one immutable topology edge.

    The validator rejects non-finite JSON on every Story Graph edge.  Earlier
    repair routing only handled join-adjacent edges, leaving ordinary choices
    quarantined despite a safe, local repair.  This compiler owns the missing
    graph-wide contract: it authorizes replacement of the one rejected value,
    never a replacement topology or a guessed state value.
    """

    relevant = tuple(
        issue for issue in issues if issue.code == "semantic.state_effect_not_json"
    )
    if not relevant or topology is None:
        return ()
    try:
        fill = StoryGraphContentFill.model_validate(value, by_alias=True)
    except ValidationError:
        return ()
    fill_edges = {edge.id: edge for edge in fill.edges}
    topology_edges = {edge.id: edge for edge in topology.edges}
    facts: list[EdgeStateEffectJsonRepairFact] = []
    for issue in relevant:
        path = issue.path
        if (
            len(path) != 4
            or path[0] != "edges"
            or not isinstance(path[1], str)
            or path[2] != "stateEffects"
            or not isinstance(path[3], str)
        ):
            continue
        edge_id, state_key = path[1], path[3]
        fill_edge = fill_edges.get(edge_id)
        topology_edge = topology_edges.get(edge_id)
        if (
            fill_edge is None
            or topology_edge is None
            or state_key not in fill_edge.state_effects
        ):
            continue
        try:
            finite_canonical_json(fill_edge.state_effects[state_key])
        except (TypeError, ValueError):
            facts.append(
                EdgeStateEffectJsonRepairFact(
                    code=issue.code,
                    path=path,
                    edge_id=edge_id,
                    source_node_id=topology_edge.source_node_id,
                    target_node_id=topology_edge.target_node_id,
                    state_key=state_key,
                )
            )
    return tuple(facts)


def _story_graph_join_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    topology: StoryGraphTopology | None,
) -> tuple[SemanticRepairFact, ...]:
    relevant_codes = {
        "semantic.join_allowed_differences_must_be_required",
        "semantic.join_state_effect_missing",
        "semantic.join_state_effect_conflict",
        "semantic.join_allowed_difference_without_reconciliation",
    }
    relevant_issues = tuple(issue for issue in issues if issue.code in relevant_codes)
    if not relevant_issues or topology is None:
        return ()
    try:
        fill = StoryGraphContentFill.model_validate(value, by_alias=True)
    except ValidationError:
        return ()
    joins_by_id = {join.id: join for join in fill.join_contracts}
    edge_fill = {edge.id: edge for edge in fill.edges}
    topology_joins = {join.id: join for join in topology.joins}
    topology_edges = {edge.id: edge for edge in topology.edges}

    def incoming_edges(join_id: str) -> tuple[JoinIncomingEdgeRepairTarget, ...] | None:
        join = topology_joins.get(join_id)
        if join is None:
            return None
        targets = [
            JoinIncomingEdgeRepairTarget(
                edge_id=edge.id,
                source_node_id=edge.source_node_id,
            )
            for edge in topology_edges.values()
            if edge.target_node_id == join.join_node_id
            and edge.source_node_id in set(join.incoming_node_ids)
        ]
        if len(targets) != len(join.incoming_node_ids):
            return None
        return tuple(sorted(targets, key=lambda edge: (edge.edge_id, edge.source_node_id)))

    incoming_by_join = {
        join_id: targets
        for join_id in topology_joins
        if (targets := incoming_edges(join_id)) is not None
    }
    mutable_keys_by_join: dict[str, set[str]] = {
        join_id: set() for join_id in incoming_by_join
    }
    for issue in issues:
        path = issue.path
        if (
            issue.code == "semantic.join_allowed_differences_must_be_required"
            and len(path) == 3
            and path[0] == "joinContracts"
            and isinstance(path[1], str)
            and path[2] == "allowedDifferences"
        ):
            join = joins_by_id.get(path[1])
            if join is not None:
                required = set(join.required_state_keys)
                mutable_keys_by_join.setdefault(join.id, set()).update(
                    key for key in join.allowed_differences if key not in required
                )
            continue
        if (
            issue.code == "semantic.join_state_effect_conflict"
            and len(path) == 4
            and path[0] == "joinContracts"
            and isinstance(path[1], str)
            and path[2] == "requiredStateKeys"
            and isinstance(path[3], str)
        ):
            mutable_keys_by_join.setdefault(path[1], set()).add(path[3])
            continue
        if (
            issue.code
            in {
                "semantic.join_state_effect_missing",
                "semantic.state_effect_not_json",
            }
            and len(path) == 4
            and path[0] == "edges"
            and isinstance(path[1], str)
            and path[2] == "stateEffects"
            and isinstance(path[3], str)
        ):
            edge = topology_edges.get(path[1])
            if edge is None:
                continue
            for join_id, targets in incoming_by_join.items():
                if edge.id in {target.edge_id for target in targets}:
                    mutable_keys_by_join.setdefault(join_id, set()).add(path[3])
                    break

    def preserved_state_effects(
        join: StoryGraphJoinContractContent,
        targets: tuple[JoinIncomingEdgeRepairTarget, ...],
    ) -> tuple[JoinPreservedStateEffect, ...]:
        """Freeze only sibling keys already valid in the rejected response.

        The rejected final is source authority for values that already satisfy
        the complete join rule. It is never authority for a key that needs a
        correction in this packet, so concurrent repairable keys stay mutable.
        """

        preserved: list[JoinPreservedStateEffect] = []
        mutable_keys = mutable_keys_by_join.get(join.id, set())
        for state_key in join.required_state_keys:
            if state_key in mutable_keys:
                continue
            incoming_effects: list[JoinPreservedIncomingStateEffect] = []
            serialized_values: list[str] = []
            for target in targets:
                fill_edge = edge_fill.get(target.edge_id)
                if fill_edge is None or state_key not in fill_edge.state_effects:
                    incoming_effects = []
                    break
                try:
                    serialized_values.append(
                        finite_canonical_json(fill_edge.state_effects[state_key])
                    )
                except (TypeError, ValueError):
                    incoming_effects = []
                    break
                incoming_effects.append(
                    JoinPreservedIncomingStateEffect(
                        edge_id=target.edge_id,
                        expected_value=deepcopy(fill_edge.state_effects[state_key]),
                    )
                )
            if not incoming_effects:
                continue
            if state_key not in join.allowed_differences and len(set(serialized_values)) != 1:
                continue
            preserved.append(
                JoinPreservedStateEffect(
                    state_key=state_key,
                    incoming_effects=tuple(incoming_effects),
                )
            )
        return tuple(preserved)

    facts: list[SemanticRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if issue.code == "semantic.join_allowed_differences_must_be_required":
            if (
                len(path) != 3
                or path[0] != "joinContracts"
                or not isinstance(path[1], str)
                or path[2] != "allowedDifferences"
            ):
                continue
            join = joins_by_id.get(path[1])
            targets = incoming_edges(path[1])
            if join is None or targets is None:
                continue
            key_lists = (join.required_state_keys, join.allowed_differences)
            if any(
                any(not key.strip() for key in keys)
                or len(keys) != len(set(keys))
                for keys in key_lists
            ):
                continue
            required = set(join.required_state_keys)
            missing = tuple(key for key in join.allowed_differences if key not in required)
            if not missing:
                continue
            facts.append(
                JoinAllowedDifferencesRepairFact(
                    code=issue.code,
                    path=path,
                    join_contract_id=join.id,
                    missing_required_state_keys=missing,
                    expected_required_state_keys=tuple((*join.required_state_keys, *missing)),
                    expected_allowed_differences=tuple(join.allowed_differences),
                    new_required_key_incoming_edges=tuple(
                        JoinNewRequiredKeyIncomingEdges(
                            state_key=state_key,
                            incoming_edges=targets,
                        )
                        for state_key in missing
                    ),
                )
            )
            continue
        if issue.code == "semantic.join_allowed_difference_without_reconciliation":
            if (
                len(path) != 3
                or path[0] != "joinContracts"
                or not isinstance(path[1], str)
                or path[2] != "reconciliation"
            ):
                continue
            join = joins_by_id.get(path[1])
            if join is None or not join.allowed_differences:
                continue
            facts.append(
                JoinReconciliationRepairFact(
                    code=issue.code,
                    path=path,
                    join_contract_id=join.id,
                    allowed_difference_keys=tuple(join.allowed_differences),
                )
            )
            continue

        # The compiler emits missing at an edge path and a conflict
        # at the join key list.  Resolve the contract/key only from the frozen
        # topology plus schema-valid fill, never from a guessed response edge.
        join_id: str | None = None
        state_key: str | None = None
        target_edge_id: str | None = None
        if issue.code == "semantic.join_state_effect_conflict":
            if (
                len(path) == 4
                and path[0] == "joinContracts"
                and isinstance(path[1], str)
                and path[2] == "requiredStateKeys"
                and isinstance(path[3], str)
            ):
                join_id = path[1]
                join = joins_by_id.get(join_id)
                if join is not None:
                    # The compiler reports one conflict per key.  Recover it
                    # deterministically by checking the first non-equal
                    # non-variant required key in declared key order.
                    targets = incoming_edges(join_id)
                    if targets is not None and path[3] in join.required_state_keys:
                        state_key = path[3]
        elif (
            len(path) == 4
            and path[0] == "edges"
            and isinstance(path[1], str)
            and path[2] == "stateEffects"
            and isinstance(path[3], str)
        ):
            target_edge_id = path[1]
            state_key = path[3]
            edge = topology_edges.get(target_edge_id)
            if edge is not None:
                for candidate in topology_joins.values():
                    if edge.target_node_id == candidate.join_node_id and edge.source_node_id in candidate.incoming_node_ids:
                        join_id = candidate.id
                        break
        if join_id is None or state_key is None:
            continue
        join = joins_by_id.get(join_id)
        targets = incoming_edges(join_id)
        topology_join = topology_joins.get(join_id)
        if join is None or targets is None or topology_join is None or state_key not in join.required_state_keys:
            continue
        mode: Literal["convergent", "variant"] = (
            "variant" if state_key in join.allowed_differences else "convergent"
        )
        expected_value: Any | None = None
        has_expected_value = False
        if issue.code == "semantic.join_state_effect_missing" and mode == "convergent":
            peer_values: list[str] = []
            peer_value: Any | None = None
            for target in targets:
                if target.edge_id == target_edge_id:
                    continue
                fill_edge = edge_fill.get(target.edge_id)
                if fill_edge is None or state_key not in fill_edge.state_effects:
                    peer_values = []
                    break
                try:
                    serialized = finite_canonical_json(fill_edge.state_effects[state_key])
                except (TypeError, ValueError):
                    peer_values = []
                    break
                peer_values.append(serialized)
                peer_value = deepcopy(fill_edge.state_effects[state_key])
            if peer_values and len(set(peer_values)) == 1:
                expected_value = peer_value
                has_expected_value = True
        action: Literal["set_missing", "make_all_equal"]
        if issue.code == "semantic.join_state_effect_missing":
            action = "set_missing"
        elif issue.code == "semantic.join_state_effect_conflict":
            action = "make_all_equal"
        fact_input: dict[str, Any] = {
            "code": issue.code,
            "path": path,
            "join_contract_id": join_id,
            "join_node_id": topology_join.join_node_id,
            "state_key": state_key,
            "mode": mode,
            "incoming_edges": targets,
            "repair_action": action,
            "has_expected_value": has_expected_value,
            "preserved_state_effects": preserved_state_effects(join, targets),
        }
        if has_expected_value:
            fact_input["expected_value"] = expected_value
        facts.append(JoinStateEffectRepairFact(**fact_input))
    return tuple(facts)


def storyboard_required_entity_state_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    bible: StoryBibleV2,
) -> tuple[RequiredEntityStateRepairFact, ...]:
    """Project exact frozen Story Bible state choices into correction facts.

    Facts are emitted only when the whole model response is schema-valid and
    the persisted semantic issue points to the same parsed requirement.  This
    keeps malformed indexes, unknown entities, and empty author vocabularies
    fail-closed instead of turning them into guessed repair authority.
    """

    relevant_issues = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.invalid_required_entity_state"
    )
    if not relevant_issues:
        return ()
    try:
        output = StoryboardFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()
    entities_by_type = {
        EntityType.CHARACTER: {item.id: item for item in bible.characters},
        EntityType.LOCATION: {item.id: item for item in bible.locations},
        EntityType.PROP: {item.id: item for item in bible.props},
    }
    facts: list[RequiredEntityStateRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 5
            or path[0] != "shots"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "requiredEntityStates"
            or not isinstance(path[3], int)
            or isinstance(path[3], bool)
            or path[3] < 0
            or path[4] != "state"
        ):
            continue
        shot_index = path[1]
        state_index = path[3]
        if shot_index >= len(output.shots):
            continue
        requirements = output.shots[shot_index].required_entity_states
        if state_index >= len(requirements):
            continue
        requirement = requirements[state_index]
        entity = entities_by_type[requirement.entity_type].get(
            requirement.entity_id
        )
        if entity is None:
            continue
        allowed_states = tuple(entity.allowed_states)
        if not allowed_states or requirement.state in allowed_states:
            continue
        facts.append(
            RequiredEntityStateRepairFact(
                code=issue.code,
                path=path,
                entity_type=requirement.entity_type,
                entity_id=requirement.entity_id,
                allowed_states=allowed_states,
            )
        )
    return tuple(facts)


def continuity_entity_state_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2,
) -> tuple[ContinuityEntityStateRepairFact, ...]:
    """Rebind known invalid continuity states to frozen Bible vocabulary."""

    relevant = tuple(
        issue for issue in issues
        if issue.code == "semantic.invalid_continuity_entity_state"
    )
    if not relevant or stage not in {StageName.SCENE_BEATS, StageName.STORYBOARD}:
        return ()
    try:
        output: SceneBeatsFragmentOutput | StoryboardFragmentOutput
        output = (
            SceneBeatsFragmentOutput.model_validate(value, by_alias=True, by_name=False)
            if stage == StageName.SCENE_BEATS
            else StoryboardFragmentOutput.model_validate(value, by_alias=True, by_name=False)
        )
    except ValidationError:
        return ()
    entities_by_type = {
        EntityType.CHARACTER: {item.id: item for item in bible.characters},
        EntityType.LOCATION: {item.id: item for item in bible.locations},
        EntityType.PROP: {item.id: item for item in bible.props},
    }
    collections: dict[str, tuple[str, str, list[Any]]]
    if isinstance(output, SceneBeatsFragmentOutput):
        collections = {
            "scenes": ("scene", "local_scene_id", list(output.scenes)),
            "beats": ("beat", "local_beat_id", list(output.beats)),
        }
    else:
        collections = {"shots": ("shot", "local_shot_id", list(output.shots))}
    facts: list[ContinuityEntityStateRepairFact] = []
    for issue in relevant:
        path = issue.path
        if (
            len(path) != 6
            or path[0] not in collections
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] not in {"entryState", "exitState"}
            or path[3] != "entityStates"
            or not isinstance(path[4], int)
            or isinstance(path[4], bool)
            or path[4] < 0
            or path[5] != "state"
        ):
            continue
        kind, local_id_field, items = collections[path[0]]
        item_index, state_index = path[1], path[4]
        if item_index >= len(items):
            continue
        item = items[item_index]
        continuity = item.entry_state if path[2] == "entryState" else item.exit_state
        if state_index >= len(continuity.entity_states):
            continue
        assignment = continuity.entity_states[state_index]
        entity = entities_by_type[assignment.entity_type].get(assignment.entity_id)
        if entity is None or not entity.allowed_states or assignment.state in entity.allowed_states:
            continue
        facts.append(
            ContinuityEntityStateRepairFact(
                code=issue.code,
                path=path,
                target=ContinuityStateEndpoint(
                    kind=kind,
                    id=getattr(item, local_id_field),
                    id_scope="response_local",
                    state="entry" if path[2] == "entryState" else "exit",
                ),
                entity_state_index=state_index,
                entity_type=assignment.entity_type,
                entity_id=assignment.entity_id,
                allowed_states=tuple(entity.allowed_states),
            )
        )
    return tuple(facts)


def storyboard_audio_timing_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
) -> tuple[AudioTimingRepairFact, ...]:
    """Turn one schema-valid audio overflow into an exact safe action.

    The portable response schema can constrain each field but cannot express
    ``startOffsetUnits + durationUnits <= shot.durationUnits``.  This router
    derives a correction only when the persisted semantic issue still points
    at the same parsed event.  A correction therefore gets one authoritative
    replacement duration, or an unambiguous removal when an event starts at
    or past the shot end; all malformed or stale evidence fails closed.
    """

    relevant_issues = tuple(
        issue for issue in issues if issue.code == "semantic.audio_timing"
    )
    if not relevant_issues:
        return ()
    try:
        output = StoryboardFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()

    facts_by_target: dict[tuple[int, int], AudioTimingRepairFact] = {}
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 6
            or path[0] != "shots"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "audioPlan"
            or path[3] != "events"
            or not isinstance(path[4], int)
            or isinstance(path[4], bool)
            or path[4] < 0
            or path[5] != "durationUnits"
        ):
            continue
        shot_index = path[1]
        event_index = path[4]
        if shot_index >= len(output.shots):
            continue
        shot = output.shots[shot_index]
        if event_index >= len(shot.audio_plan.events):
            continue
        event = shot.audio_plan.events[event_index]
        if event.start_offset_units + event.duration_units <= shot.duration_units:
            continue
        remaining_duration_units = shot.duration_units - event.start_offset_units
        if remaining_duration_units >= 1:
            repair_action: Literal["replace_duration", "remove_event"] = (
                "replace_duration"
            )
            replacement_duration_units: int | None = remaining_duration_units
        else:
            repair_action = "remove_event"
            replacement_duration_units = None
        fact = AudioTimingRepairFact(
            code=issue.code,
            path=path,
            shot_local_id=shot.local_shot_id,
            event_index=event_index,
            start_offset_units=event.start_offset_units,
            duration_units=event.duration_units,
            shot_duration_units=shot.duration_units,
            repair_action=repair_action,
            replacement_duration_units=replacement_duration_units,
        )
        target = (shot_index, event_index)
        # A correction must be an executable sequence, not an unordered bag
        # of suggestions.  Two facts for one original array element would
        # make a later removal/replacement order ambiguous, so fail closed.
        if target in facts_by_target:
            return ()
        facts_by_target[target] = fact
    return tuple(
        fact
        for _target, fact in sorted(
            facts_by_target.items(),
            key=lambda item: (item[0][0], -item[0][1]),
        )
    )


def scene_beats_join_entry_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    requirements: Mapping[str, Any],
) -> tuple[JoinEntryStateValueRepairFact, ...]:
    """Bind a rejected join fact to the exact frozen edge-transition value."""

    relevant = tuple(
        issue
        for issue in issues
        if issue.code
        in {
            "semantic.join_entry_state_value_missing",
            "semantic.join_entry_state_value_mismatch",
            "semantic.join_entry_state_value_not_json",
        }
    )
    if not relevant:
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()
    contract_version = requirements.get("contractVersion")
    contract_hash = requirements.get("contractHash")
    expected_facts = requirements.get("requiredEntryFacts")
    if (
        not isinstance(contract_version, str)
        or not contract_version
        or not isinstance(contract_hash, str)
        or len(contract_hash) != 64
        or not isinstance(expected_facts, Mapping)
    ):
        return ()
    facts: list[JoinEntryStateValueRepairFact] = []
    for issue in relevant:
        path = issue.path
        if (
            len(path) != 5
            or path[0] != "scenes"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[1] >= len(output.scenes)
            or path[2] != "entryState"
            or path[3] != "facts"
            or not isinstance(path[4], str)
            or path[4] not in expected_facts
        ):
            continue
        state_key = path[4]
        current = output.scenes[path[1]].entry_state.facts
        if issue.code.endswith("missing") and state_key in current:
            continue
        if issue.code.endswith(("mismatch", "not_json")) and state_key in current:
            try:
                if finite_json_values_equal(
                    current[state_key], expected_facts[state_key]
                ):
                    continue
            except CanonicalJsonValueError:
                # A non-finite value remains a validation failure; do not
                # manufacture a repair fact from an invalid authority.
                continue
        facts.append(
            JoinEntryStateValueRepairFact(
                code=issue.code,
                path=path,
                contract_version=contract_version,
                contract_hash=contract_hash,
                state_key=state_key,
                expected_value=deepcopy(expected_facts[state_key]),
            )
        )
    return tuple(facts)


def scene_beats_dialogue_capacity_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    guidance: DialogueCapacityNodeGuidance,
) -> tuple[DialogueCapacityRepairFact, ...]:
    """Derive exact cue caps from schema-valid output and frozen guidance.

    A malformed response, an issue for another field, a language outside the
    frozen ProjectBrief, or a rule that cannot be proved from the sealed plan
    receives no fact.  That keeps corrections from gaining authority through
    guessed indexes or current process configuration.
    """

    if guidance.authoring_language is None or guidance.schema_max_text_codepoints is None:
        return ()
    relevant_issues = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.dialogue_cue_capacity_exceeded"
    )
    if not relevant_issues:
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()

    def rule_for(
        language: str,
        delivery: DialogueDeliveryPace,
    ) -> DialogueCapacityRuleGuidance | None:
        exact = next(
            (
                rule
                for rule in guidance.rule_guidance
                if rule.language == language and rule.delivery == delivery
            ),
            None,
        )
        if exact is not None:
            return exact
        return next(
            (
                rule
                for rule in guidance.rule_guidance
                if rule.language == "*" and rule.delivery == delivery
            ),
            None,
        )

    compatible_limits: list[DialogueCapacityDeliveryLimit] = []
    for delivery in DialogueDeliveryPace:
        rule = rule_for(guidance.authoring_language, delivery)
        if rule is None:
            return ()
        compatible_limits.append(
            DialogueCapacityDeliveryLimit(
                delivery=delivery,
                max_text_codepoints=min(
                    rule.max_text_codepoints,
                    guidance.schema_max_text_codepoints,
                ),
            )
        )
    limits = tuple(compatible_limits)
    facts: list[DialogueCapacityRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 3
            or path[0] != "dialogueCues"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "text"
            or path[1] >= len(output.dialogue_cues)
        ):
            continue
        cue = output.dialogue_cues[path[1]]
        if cue.language != guidance.authoring_language:
            continue
        limit = next(item for item in limits if item.delivery == cue.delivery)
        if len(cue.text.strip()) <= limit.max_text_codepoints:
            # The issue was caused by a different invariant; do not invent a
            # text-shortening authority for it.
            continue
        facts.append(
            DialogueCapacityRepairFact(
                code=issue.code,
                path=path,
                authoring_language=guidance.authoring_language,
                language=cue.language,
                delivery=cue.delivery,
                current_text_codepoints=len(cue.text.strip()),
                max_text_codepoints=limit.max_text_codepoints,
                compatible_delivery_limits=limits,
            )
        )
    return tuple(facts)


_CUE_ORDER_COLLECTION_MUTATION_CODES = frozenset(
    {
        # These repairs can remove or rename a cue/beat.  A complete
        # membership-preserving overlay would conflict with that authority, so
        # cue order must wait for the structurally safe rejection that follows.
        "semantic.dialogue_cue_count_exceeded",
        "semantic.dialogue_exceeds_node_budget",
        "semantic.duplicate_beat_id",
        "semantic.duplicate_cue_id",
        "semantic.cross_unit_beat",
        "semantic.cross_unit_cue",
        "semantic.scene_capacity_exceeded",
    }
)


def scene_beats_cue_order_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
) -> tuple[CueOrderRepairFact, ...]:
    """Derive a complete, source-bound cue renumbering when identity is safe.

    Cue order is validated across a collection, rather than at one index.  A
    correction therefore receives the complete response-local membership map,
    not a guessed target cue.  If another stable issue can delete, rename, or
    reassign a cue, no fact is emitted: an exact membership repair would be
    contradictory and must not be fabricated.
    """

    relevant = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.cue_order" and issue.path == ("dialogueCues",)
    )
    if not relevant or any(
        issue.code in _CUE_ORDER_COLLECTION_MUTATION_CODES for issue in issues
    ):
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()

    beat_ids = [beat.local_beat_id for beat in output.beats]
    cue_ids = [cue.local_cue_id for cue in output.dialogue_cues]
    known_beat_ids = set(beat_ids)
    if (
        len(beat_ids) != len(set(beat_ids))
        or len(cue_ids) != len(set(cue_ids))
        or any(not beat_id.strip() for beat_id in beat_ids)
        or any(not cue_id.strip() for cue_id in cue_ids)
        or any(cue.beat_local_id not in known_beat_ids for cue in output.dialogue_cues)
    ):
        return ()

    cues_by_beat: dict[str, list[tuple[int, DialogueCueContent]]] = {}
    for source_index, cue in enumerate(output.dialogue_cues):
        cues_by_beat.setdefault(cue.beat_local_id, []).append((source_index, cue))

    assignments: list[CueOrderRepairAssignment] = []
    source_is_invalid = False
    for beat_id in beat_ids:
        # This is the validator's ordering with the response index made
        # explicit as a deterministic duplicate-order tie breaker.
        ordered = sorted(
            cues_by_beat.get(beat_id, ()),
            key=lambda item: (item[1].order, item[0]),
        )
        if [cue.order for _index, cue in ordered] != list(
            range(1, len(ordered) + 1)
        ):
            source_is_invalid = True
        assignments.extend(
            CueOrderRepairAssignment(
                local_cue_id=cue.local_cue_id,
                beat_local_id=beat_id,
                expected_order=expected_order,
            )
            for expected_order, (_index, cue) in enumerate(ordered, start=1)
        )
    if not source_is_invalid:
        # Do not turn an issue from another validator layer into authority for
        # an otherwise valid source collection.
        return ()
    canonical_assignments = tuple(
        sorted(assignments, key=lambda item: item.local_cue_id)
    )
    return tuple(
        CueOrderRepairFact(
            code=issue.code,
            path=issue.path,
            assignments=canonical_assignments,
        )
        for issue in relevant
    )


def scene_beats_dialogue_node_budget_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    node_id: str,
    node_duration_budget_units: int | None,
    dialogue_timing_profile: DialogueTimingProfile | None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
) -> tuple[DialogueNodeBudgetRepairFact, ...]:
    """Create a deterministic delete-and-renumber plan for a global overage.

    It is intentionally conservative: if the rejected fragment is not
    unambiguous under exactly the same frozen inputs used by semantic
    validation, no fact is emitted and no repair authority is fabricated.
    """

    relevant = tuple(
        issue for issue in issues if issue.code == "semantic.dialogue_exceeds_node_budget"
    )
    if (
        not relevant
        or node_duration_budget_units is None
        or dialogue_timing_profile is None
        or dialogue_capacity_guidance is None
    ):
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(value, by_alias=True, by_name=False)
    except ValidationError:
        return ()
    scene_ids = {scene.local_scene_id for scene in output.scenes}
    beat_ids = {beat.local_beat_id for beat in output.beats}
    cue_ids = [cue.local_cue_id for cue in output.dialogue_cues]
    if (
        len(scene_ids) != len(output.scenes)
        or len(beat_ids) != len(output.beats)
        or len(cue_ids) != len(set(cue_ids))
        or any(beat.scene_local_id not in scene_ids for beat in output.beats)
        or any(cue.beat_local_id not in beat_ids for cue in output.dialogue_cues)
        or dialogue_capacity_guidance.authoring_language is None
    ):
        return ()
    beat_scene = {beat.local_beat_id: beat.scene_local_id for beat in output.beats}
    timed: list[tuple[int, int, DialogueCueContent]] = []
    for index, cue in enumerate(output.dialogue_cues):
        if cue.language != dialogue_capacity_guidance.authoring_language:
            return ()
        duration = dialogue_timing_profile.estimate_text_duration_units(
            text=cue.text,
            language=cue.language,
            delivery=cue.delivery,
        )
        if duration is None:
            return ()
        timed.append((duration, index, cue))
    def node_minimum(excluded: set[str]) -> int:
        by_scene = {scene.local_scene_id: 0 for scene in output.scenes}
        for duration, _index, cue in timed:
            if cue.local_cue_id not in excluded:
                by_scene[beat_scene[cue.beat_local_id]] += duration
        # This exactly matches _scene_beats_semantic_issues: every scene
        # consumes a one-unit floor even when all of its cues are removed.
        return sum(max(1, duration) for duration in by_scene.values())

    current_total = node_minimum(set())
    if current_total <= node_duration_budget_units:
        return ()
    remaining = current_total
    removed: set[str] = set()
    # Recompute the exact scene-floor total after every candidate deletion.
    # A last cue in a scene may free no time because that scene's mandatory
    # one-unit floor remains; sorting raw cue durations would produce a plan
    # that still fails the validator.
    candidates = {cue.local_cue_id: (duration, index, cue) for duration, index, cue in timed}
    while remaining > node_duration_budget_units and candidates:
        ranked: list[tuple[int, int, str, int, DialogueCueContent]] = []
        for cue_id, (duration, index, cue) in candidates.items():
            next_total = node_minimum({*removed, cue_id})
            ranked.append((-(remaining - next_total), -index, cue_id, next_total, cue))
        _negative_reduction, _negative_index, selected_id, next_total, _cue = min(ranked)
        if next_total >= remaining:
            return ()
        removed.add(selected_id)
        candidates.pop(selected_id)
        remaining = next_total
    if remaining > node_duration_budget_units or not removed:
        return ()
    retained: list[DialogueNodeBudgetRemainingCue] = []
    next_order_by_beat: dict[str, int] = {}
    for _duration, _index, cue in timed:
        if cue.local_cue_id in removed:
            continue
        next_order = next_order_by_beat.get(cue.beat_local_id, 0) + 1
        next_order_by_beat[cue.beat_local_id] = next_order
        retained.append(
            DialogueNodeBudgetRemainingCue(
                local_cue_id=cue.local_cue_id,
                beat_local_id=cue.beat_local_id,
                expected_order=next_order,
            )
        )
    return tuple(
        DialogueNodeBudgetRepairFact(
            code=issue.code,
            path=issue.path,
            node_id=node_id,
            node_duration_budget_units=node_duration_budget_units,
            current_minimum_duration_units=current_total,
            remove_local_cue_ids=tuple(
                cue.local_cue_id
                for _duration, _index, cue in timed
                if cue.local_cue_id in removed
            ),
            remaining_cues=tuple(retained),
            remaining_minimum_duration_units=remaining,
        )
        for issue in relevant
        if issue.path == ("dialogueCues",)
    )


def storyboard_timing_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    guidance: StoryboardTimingGuidance | None,
) -> tuple[StoryboardTimingRepairPlanFact, ...]:
    """Build issue-bound references to one complete executable timing plan.

    This intentionally declines to help when response identity/coverage is
    unsafe.  Coverage has its own repair contract; a later correction can
    create this plan only after that contract made its identity complete.
    """

    if guidance is None:
        return ()
    relevant = tuple(
        issue
        for issue in issues
        if issue.code
        in {
            "semantic.shot_duration_budget_exceeded",
            "semantic.cue_duration_exceeds_shot",
        }
    )
    if not relevant:
        return ()
    if not isinstance(value, Mapping):
        return ()
    plan = build_storyboard_timing_repair_plan(value, guidance=guidance)
    if plan is None:
        return ()
    return tuple(
        StoryboardTimingRepairPlanFact(
            code=issue.code,
            path=issue.path,
            plan=plan,
            guidance_hash=storyboard_timing_guidance_hash(guidance),
            plan_hash=plan.plan_hash,
        )
        for issue in relevant
    )


def continuity_sequence_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2 | None,
    scoped_context: Mapping[str, Any] | None = None,
) -> tuple[ContinuitySequenceRepairFact, ...]:
    """Compile exact left-to-right continuity repairs for one fragment response.

    This compiler deliberately accepts only schema-valid fragments and a
    valid Story Bible.  It never repairs a one-sided declaration, notes, or a
    malformed state; those cases lack an exact, safe ownership authority.
    """

    if bible is None:
        return ()
    if stage == StageName.SCENE_BEATS:
        relevant = tuple(
            issue
            for issue in issues
            if issue.code == "semantic.continuity_beat_sequence_mismatch"
        )
        if not relevant:
            return ()
        try:
            output = SceneBeatsFragmentOutput.model_validate(value, by_alias=True, by_name=False)
        except ValidationError:
            return ()
        scene_ids = [scene.local_scene_id for scene in output.scenes]
        beat_ids = [beat.local_beat_id for beat in output.beats]
        if len(scene_ids) != len(set(scene_ids)) or len(beat_ids) != len(set(beat_ids)):
            return ()
        facts: list[ContinuitySequenceRepairFact] = []
        for issue in relevant:
            path = issue.path
            if (
                len(path) != 2
                or path[0] != "scenes"
                or not isinstance(path[1], int)
                or isinstance(path[1], bool)
                or path[1] < 0
                or path[1] >= len(output.scenes)
            ):
                continue
            scene = output.scenes[path[1]]
            ordered = sorted(
                (beat for beat in output.beats if beat.scene_local_id == scene.local_scene_id),
                key=lambda beat: beat.order,
            )
            if (
                not ordered
                or any(beat.scene_local_id not in set(scene_ids) for beat in output.beats)
                or [beat.order for beat in ordered] != list(range(1, len(ordered) + 1))
            ):
                continue
            differences = continuity_sequence_repair_boundaries(
                scene.entry_state,
                ordered,
                scene.exit_state,
                bible=bible,
            )
            if not differences:
                continue
            boundaries: list[ContinuityBoundaryRepair] = []
            for difference in differences:
                source, target = _scene_beats_continuity_boundary_endpoints(
                    scene,
                    ordered,
                    difference.boundary_index,
                )
                assignments = tuple(
                    _continuity_assignment_from_candidate(candidate)
                    for candidate in difference.assignments
                )
                boundaries.append(
                    ContinuityBoundaryRepair(
                        source=source,
                        target=target,
                        assignments=assignments,
                    )
                )
            facts.append(
                ContinuitySequenceRepairFact(
                    code=issue.code,
                    path=path,
                    sequence_kind="beat",
                    owner=ContinuityStateEndpoint(
                        kind="scene",
                        id=scene.local_scene_id,
                        id_scope="response_local",
                        state="entry",
                    ),
                    ordered_item_ids=tuple(beat.local_beat_id for beat in ordered),
                    boundaries=tuple(boundaries),
                )
            )
        return tuple(facts)

    if stage != StageName.STORYBOARD:
        return ()
    relevant = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.continuity_shot_sequence_mismatch"
        and issue.path == ("shots",)
    )
    if not relevant or scoped_context is None:
        return ()
    try:
        output = StoryboardFragmentOutput.model_validate(value, by_alias=True, by_name=False)
        scene = scoped_context.get("dramatic_scene")
        if not isinstance(scene, Mapping):
            return ()
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            return ()
        scene_entry = continuity_state_from_context(scene, "entryState")
        scene_exit = continuity_state_from_context(scene, "exitState")
    except (ValidationError, FragmentSemanticContextError):
        return ()
    shot_ids = [shot.local_shot_id for shot in output.shots]
    ordered = sorted(output.shots, key=lambda shot: shot.order)
    if (
        len(shot_ids) != len(set(shot_ids))
        or not ordered
        or [shot.order for shot in ordered] != list(range(1, len(ordered) + 1))
    ):
        return ()
    differences = continuity_sequence_repair_boundaries(
        scene_entry,
        ordered,
        scene_exit,
        bible=bible,
        final_boundary_source="sequence_exit",
    )
    if not differences:
        return ()
    boundaries = []
    for difference in differences:
        source, target = _storyboard_continuity_boundary_endpoints(
            scene_id,
            ordered,
            difference.boundary_index,
        )
        boundaries.append(
            ContinuityBoundaryRepair(
                source=source,
                target=target,
                assignments=tuple(
                    _continuity_assignment_from_candidate(candidate)
                    for candidate in difference.assignments
                ),
            )
        )
    return tuple(
        ContinuitySequenceRepairFact(
            code=issue.code,
            path=issue.path,
            sequence_kind="shot",
            owner=ContinuityStateEndpoint(
                kind="scene",
                id=scene_id,
                id_scope="canonical_context",
                state="entry",
            ),
            ordered_item_ids=tuple(shot.local_shot_id for shot in ordered),
            boundaries=tuple(boundaries),
        )
        for issue in relevant
    )


def _continuity_assignment_from_candidate(candidate: Any) -> ContinuityRepairAssignment:
    if candidate.kind == "fact":
        assert candidate.fact_key is not None
        return ContinuityFactAssignment(
            kind="fact",
            key=candidate.fact_key,
            expected_value=candidate.expected_value,
        )
    if candidate.kind == "entity_state":
        assert candidate.entity_type is not None and candidate.entity_id is not None
        return ContinuityEntityStateAssignment(
            kind="entity_state",
            entity_type=candidate.entity_type,
            entity_id=candidate.entity_id,
            expected_state=candidate.expected_value,
        )
    assert candidate.scalar_field is not None
    return ContinuityScalarAssignment(
        kind="scalar",
        field={
            "screen_direction": "screenDirection",
            "lighting": "lighting",
            "sound": "sound",
        }[candidate.scalar_field],
        expected_value=candidate.expected_value,
    )


def _scene_beats_continuity_boundary_endpoints(
    scene: DramaticSceneContent,
    ordered: list[BeatContent],
    boundary_index: int,
) -> tuple[ContinuityStateEndpoint, ContinuityStateEndpoint]:
    scene_entry = ContinuityStateEndpoint(
        kind="scene", id=scene.local_scene_id, id_scope="response_local", state="entry"
    )
    scene_exit = ContinuityStateEndpoint(
        kind="scene", id=scene.local_scene_id, id_scope="response_local", state="exit"
    )
    if boundary_index == 0:
        return scene_entry, ContinuityStateEndpoint(
            kind="beat", id=ordered[0].local_beat_id, id_scope="response_local", state="entry"
        )
    if boundary_index == len(ordered):
        return ContinuityStateEndpoint(
            kind="beat", id=ordered[-1].local_beat_id, id_scope="response_local", state="exit"
        ), scene_exit
    return ContinuityStateEndpoint(
        kind="beat", id=ordered[boundary_index - 1].local_beat_id, id_scope="response_local", state="exit"
    ), ContinuityStateEndpoint(
        kind="beat", id=ordered[boundary_index].local_beat_id, id_scope="response_local", state="entry"
    )


def _storyboard_continuity_boundary_endpoints(
    scene_id: str,
    ordered: list[ShotContent],
    boundary_index: int,
) -> tuple[ContinuityStateEndpoint, ContinuityStateEndpoint]:
    scene_entry = ContinuityStateEndpoint(
        kind="scene", id=scene_id, id_scope="canonical_context", state="entry"
    )
    scene_exit = ContinuityStateEndpoint(
        kind="scene", id=scene_id, id_scope="canonical_context", state="exit"
    )
    if boundary_index == 0:
        return scene_entry, ContinuityStateEndpoint(
            kind="shot", id=ordered[0].local_shot_id, id_scope="response_local", state="entry"
        )
    if boundary_index == len(ordered):
        return scene_exit, ContinuityStateEndpoint(
            kind="shot", id=ordered[-1].local_shot_id, id_scope="response_local", state="exit"
        )
    return ContinuityStateEndpoint(
        kind="shot", id=ordered[boundary_index - 1].local_shot_id, id_scope="response_local", state="exit"
    ), ContinuityStateEndpoint(
        kind="shot", id=ordered[boundary_index].local_shot_id, id_scope="response_local", state="entry"
    )


def semantic_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2 | None = None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
    node_duration_budget_units: int | None = None,
    join_state_value_requirements: Mapping[str, Any] | None = None,
    storyboard_timing_guidance: StoryboardTimingGuidance | None = None,
    story_graph_topology: StoryGraphTopology | None = None,
    scoped_context: Mapping[str, Any] | None = None,
) -> tuple[SemanticRepairFact, ...]:
    """Route stable issues to versioned, stage-owned deterministic facts."""

    if stage == StageName.STORY_GRAPH:
        return (
            *_story_graph_edge_state_effect_json_repair_facts(
                value,
                issues,
                topology=story_graph_topology,
            ),
            *_story_graph_join_repair_facts(
                value,
                issues,
                topology=story_graph_topology,
            ),
        )
    if stage == StageName.STORYBOARD:
        continuity_entity_state_facts = (
            continuity_entity_state_repair_facts(value, issues, stage=stage, bible=bible)
            if bible is not None
            else ()
        )
        continuity_facts = continuity_sequence_repair_facts(
            value,
            issues,
            stage=stage,
            bible=bible,
            scoped_context=scoped_context,
        )
        required_entity_state_facts = (
            storyboard_required_entity_state_repair_facts(
                value,
                issues,
                bible=bible,
            )
            if bible is not None
            else ()
        )
        required_entity_presence_facts = (
            storyboard_required_entity_presence_repair_facts(value, issues)
        )
        timing_facts = storyboard_timing_repair_facts(
            value,
            issues,
            guidance=storyboard_timing_guidance,
        )
        audio_facts = (
            ()
            if timing_facts
            else storyboard_audio_timing_repair_facts(value, issues)
        )
        return (
            *continuity_entity_state_facts,
            *continuity_facts,
            *required_entity_state_facts,
            *required_entity_presence_facts,
            *timing_facts,
            *audio_facts,
        )
    if stage == StageName.SCENE_BEATS:
        entity_state_facts = (
            continuity_entity_state_repair_facts(value, issues, stage=stage, bible=bible)
            if bible is not None
            else ()
        )
        continuity_facts = continuity_sequence_repair_facts(
            value,
            issues,
            stage=stage,
            bible=bible,
            scoped_context=scoped_context,
        )
        capacity_facts = (
            scene_beats_dialogue_capacity_repair_facts(
                value,
                issues,
                guidance=dialogue_capacity_guidance,
            )
            if dialogue_capacity_guidance is not None
            else ()
        )
        join_facts = (
            scene_beats_join_entry_repair_facts(
                value,
                issues,
                requirements=join_state_value_requirements,
            )
            if join_state_value_requirements is not None
            else ()
        )
        edge_entry_facts = (
            edge_entry_entity_state_repair_facts(
                value,
                issues,
                requirements=edge_entry_state_requirements(scoped_context),
            )
            if scoped_context is not None
            else ()
        )
        node_budget_facts = scene_beats_dialogue_node_budget_repair_facts(
            value,
            issues,
            node_id=(
                dialogue_capacity_guidance.node_id
                if dialogue_capacity_guidance is not None
                else ""
            ),
            node_duration_budget_units=node_duration_budget_units,
            dialogue_timing_profile=dialogue_timing_profile,
            dialogue_capacity_guidance=dialogue_capacity_guidance,
        )
        cue_order_facts = scene_beats_cue_order_repair_facts(value, issues)
        return (
            *entity_state_facts,
            *continuity_facts,
            *capacity_facts,
            *join_facts,
            *edge_entry_facts,
            *node_budget_facts,
            *cue_order_facts,
        )
    return ()


def parse_semantic_repair_fact(value: Any) -> SemanticRepairFact:
    """Revalidate persisted repair evidence without adding current defaults."""

    if isinstance(value, Mapping):
        if value.get("code") == "semantic.cue_duration_underestimated":
            # Read-only evidence from the retired duration-estimate repair
            # contract.  It remains inspectable but is deliberately outside
            # ``CurrentSemanticRepairFact`` and therefore cannot authorize a
            # newly compiled correction.
            return DialogueTimingRepairFact.model_validate(value)
        if "plan" in value and value.get("code") in {
            "semantic.shot_duration_budget_exceeded",
            "semantic.cue_duration_exceeds_shot",
        } and "guidanceHash" not in value:
            return LegacyStoryboardTimingRepairPlanFact.model_validate(value)
        if "plan" not in value and value.get("code") == "semantic.shot_duration_budget_exceeded":
            return ShotDurationBudgetRepairFact.model_validate(value)
        if "plan" not in value and value.get("code") == "semantic.cue_duration_exceeds_shot":
            return CueDurationFitRepairFact.model_validate(value)
    return _SEMANTIC_REPAIR_FACT_ADAPTER.validate_python(value)


def serialize_semantic_repair_fact(fact: SemanticRepairFact) -> dict[str, Any]:
    """Serialize current facts without injecting absent historical fields.

    ``exclude_none`` preserves old evidence shape, except that an explicitly
    authorized JSON null is semantically distinct from no `expectedValue`
    authority.  Keep that one null when `hasExpectedValue` says it is real.
    """

    payload = fact.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(fact, JoinStateEffectRepairFact) and fact.has_expected_value:
        payload["expectedValue"] = fact.expected_value
    if isinstance(fact, JoinStateEffectRepairFact):
        # A preserved sibling may deliberately be JSON null.  Unlike the
        # repair target, every preserved assignment carries exact authority,
        # so restore nulls stripped by ``exclude_none`` at every nested edge.
        for serialized_effect, effect in zip(
            payload.get("preservedStateEffects", []),
            fact.preserved_state_effects,
            strict=True,
        ):
            for serialized_incoming, incoming in zip(
                serialized_effect["incomingEffects"],
                effect.incoming_effects,
                strict=True,
            ):
                serialized_incoming["expectedValue"] = incoming.expected_value
    if isinstance(fact, ContinuitySequenceRepairFact):
        # ``exclude_none`` is correct for optional evidence fields, but a
        # continuity fact assignment may deliberately copy JSON null.  Keep
        # that value so persisted facts remain executable and round-trip.
        for serialized_boundary, boundary in zip(
            payload["boundaries"], fact.boundaries, strict=True
        ):
            for serialized_assignment, assignment in zip(
                serialized_boundary["assignments"], boundary.assignments, strict=True
            ):
                if isinstance(assignment, ContinuityFactAssignment):
                    serialized_assignment["expectedValue"] = assignment.expected_value
    return payload


def assert_semantic_repair_fact_matches_issue(
    fact: SemanticRepairFact,
    issues: tuple[ValidationIssue, ...],
) -> None:
    """Bind persisted repair authority to one exact stable rejection.

    A syntactically valid fact is not sufficient: it must name the same code
    and data path as an issue in the immutable validation artifact which
    authorizes this correction attempt.
    """

    if not any(issue.code == fact.code and issue.path == fact.path for issue in issues):
        raise ValueError(
            "deterministic repair fact has no matching stable validation issue"
        )


def assert_continuity_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
    *,
    stage: StageName,
    bible: StoryBibleV2 | None,
    scoped_context: Mapping[str, Any] | None = None,
) -> None:
    """Bind executable continuity authority back to the rejected response.

    Internal endpoint adjacency is necessary but insufficient: a persisted
    fact could otherwise name a different owner or reorder response-local
    items while remaining self-consistent.  Recompiling the one exact fact
    from the source value and frozen context proves that its owner, IDs,
    sequence order, boundaries, and assignments all came from the response
    that was actually rejected.
    """

    if not isinstance(fact, ContinuitySequenceRepairFact):
        return
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = continuity_sequence_repair_facts(
        source_value,
        (source_issue,),
        stage=stage,
        bible=bible,
        scoped_context=scoped_context,
    )
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError(
            "continuity repair fact does not match the rejected response and frozen context"
        )


def assert_continuity_entity_state_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
    *,
    stage: StageName,
    bible: StoryBibleV2 | None,
) -> None:
    """Prove a vocabulary fact still belongs to this rejected response."""

    if not isinstance(fact, ContinuityEntityStateRepairFact):
        return
    if bible is None:
        raise ValueError("continuity entity-state repair requires a frozen story bible")
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = continuity_entity_state_repair_facts(
        source_value, (source_issue,), stage=stage, bible=bible
    )
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError(
            "continuity entity-state repair fact does not match the rejected response and frozen story bible"
        )


def assert_cue_order_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
) -> None:
    """Bind executable cue renumbering authority to its rejected response."""

    if not isinstance(fact, CueOrderRepairFact):
        return
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = scene_beats_cue_order_repair_facts(source_value, (source_issue,))
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError(
            "cue-order repair fact does not match the rejected response"
        )


def assert_join_state_effect_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
    *,
    issues: tuple[ValidationIssue, ...],
    topology: StoryGraphTopology | None,
) -> None:
    """Rebuild join preservation authority from the rejected source response.

    A persisted fact can be syntactically valid while carrying values from a
    different rejected response. Recompiling against the immutable topology
    and complete stable issue set proves both the repaired key and every
    preserved sibling assignment were actually valid source facts.
    """

    if not isinstance(fact, JoinStateEffectRepairFact):
        return
    expected = _story_graph_join_repair_facts(
        source_value,
        issues,
        topology=topology,
    )
    matches = [
        item
        for item in expected
        if isinstance(item, JoinStateEffectRepairFact)
        and item.code == fact.code
        and item.path == fact.path
    ]
    if len(matches) != 1 or matches[0] != fact:
        raise ValueError(
            "join state-effect repair fact does not match the rejected response and frozen topology"
        )


def _scene_beats_semantic_issues(
    output: SceneBeatsFragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
    dialogue_timing_profile: DialogueTimingProfile,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    target = work_unit.selector.stable_id
    target_node = scoped_context.get("story_node", {})
    if target_node.get("id") != target:
        issues.append(_issue("context.selector", "storyNodeId", "trusted context does not match unit selector"))
    if dialogue_capacity_guidance.node_id != target:
        raise WorkUnitContractError(
            "dialogue capacity guidance does not match the work-unit selector"
        )
    if len(output.scenes) > dialogue_capacity_guidance.max_scenes:
        issues.append(
            _issue(
                "semantic.scene_capacity_exceeded",
                "scenes",
                "scene count exceeds the frozen dialogue capacity envelope",
            )
        )
    if len(output.dialogue_cues) > dialogue_capacity_guidance.max_dialogue_cues:
        issues.append(
            _issue(
                "semantic.dialogue_cue_count_exceeded",
                "dialogueCues",
                "dialogue cue count exceeds the frozen capacity envelope",
            )
        )
    scene_ids = [scene.local_scene_id for scene in output.scenes]
    if len(scene_ids) != len(set(scene_ids)):
        issues.append(_issue("semantic.duplicate_scene_id", "scenes", "fragment contains duplicate scene IDs"))
    scene_orders = sorted(scene.order for scene in output.scenes)
    if scene_orders != list(range(1, len(scene_orders) + 1)):
        issues.append(_issue("semantic.scene_order", "scenes", "scene order must be contiguous from 1"))
    beat_ids = [beat.local_beat_id for beat in output.beats]
    if len(beat_ids) != len(set(beat_ids)):
        issues.append(_issue("semantic.duplicate_beat_id", "beats", "fragment contains duplicate beat IDs"))
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    edge_entry_requirements = edge_entry_state_requirements(scoped_context)
    issues.extend(first_scene_entry_issues(
        [scene.model_dump(mode="json", by_alias=True) for scene in output.scenes],
        edge_entry_requirements,
    ))
    beats_by_scene: dict[str, list[BeatContent]] = {}
    for beat in output.beats:
        beats_by_scene.setdefault(beat.scene_local_id, []).append(beat)
        if beat.scene_local_id not in scene_ids:
            issues.append(_issue("semantic.cross_unit_beat", "beats", "beat belongs to a scene outside this fragment"))
    cues_by_beat: dict[str, list[DialogueCueContent]] = {}
    cue_ids = [cue.local_cue_id for cue in output.dialogue_cues]
    if len(cue_ids) != len(set(cue_ids)):
        issues.append(_issue("semantic.duplicate_cue_id", "dialogueCues", "fragment contains duplicate cue IDs"))
    for cue_index, cue in enumerate(output.dialogue_cues):
        cues_by_beat.setdefault(cue.beat_local_id, []).append(cue)
        if cue.beat_local_id not in beat_ids:
            issues.append(_issue("semantic.cross_unit_cue", ("dialogueCues", cue_index, "beatLocalId"), "cue belongs to a beat outside this fragment"))
        if cue.speaker_id is not None and cue.speaker_id not in known_characters:
            issues.append(_issue("semantic.unknown_cue_speaker", ("dialogueCues", cue_index, "speakerId"), "cue speaker is not in the Story Bible"))
    for beat_index, beat in enumerate(output.beats):
        issues.extend(
            continuity_state_issues(
                beat.entry_state,
                bible=bible,
                path=("beats", beat_index, "entryState"),
            )
        )
        issues.extend(
            continuity_state_issues(
                beat.exit_state,
                bible=bible,
                path=("beats", beat_index, "exitState"),
            )
        )
        for delta_key, delta_value in beat.continuity_delta.items():
            try:
                finite_canonical_json(delta_value)
            except CanonicalJsonValueError:
                issues.append(
                    _issue(
                        "semantic.continuity_delta_not_json",
                        ("beats", beat_index, "continuityDelta", delta_key),
                        "continuity delta values must be finite canonical JSON",
                    )
                )
    cue_order_invalid = False
    for index, scene in enumerate(output.scenes):
        if scene.location_id is not None and scene.location_id not in known_locations:
            issues.append(_issue("semantic.unknown_location", ("scenes", index, "locationId"), "scene references an unknown location"))
        unknown_characters = set(scene.character_ids) - known_characters
        if unknown_characters:
            issues.append(_issue("semantic.unknown_characters", ("scenes", index, "characterIds"), "scene references unknown characters"))
        if len(scene.character_ids) != len(set(scene.character_ids)):
            issues.append(
                _issue(
                    "semantic.duplicate_character_ref",
                    ("scenes", index, "characterIds"),
                    "scene references the same character more than once",
                )
            )
        issues.extend(
            continuity_state_issues(
                scene.entry_state,
                bible=bible,
                path=("scenes", index, "entryState"),
            )
        )
        issues.extend(
            continuity_state_issues(
                scene.exit_state,
                bible=bible,
                path=("scenes", index, "exitState"),
            )
        )
        ordered = sorted(beats_by_scene.get(scene.local_scene_id, []), key=lambda beat: beat.order)
        if not ordered:
            issues.append(_issue("semantic.scene_without_beats", ("scenes", index), "each scene must contain at least one beat"))
        if [beat.order for beat in ordered] != list(range(1, len(ordered) + 1)):
            issues.append(_issue("semantic.beat_order", ("scenes", index), "beat order must be contiguous from 1"))
        for beat in ordered:
            beat_cues = sorted(cues_by_beat.get(beat.local_beat_id, []), key=lambda cue: cue.order)
            if any(cue.speaker_id is not None and cue.speaker_id not in scene.character_ids for cue in beat_cues):
                issues.append(_issue("semantic.cue_speaker_not_in_scene", "dialogueCues", "cue speaker must appear in its dramatic scene"))
            if [cue.order for cue in beat_cues] != list(range(1, len(beat_cues) + 1)):
                cue_order_invalid = True
        if ordered and not continuity_sequence_is_compatible(
            scene.entry_state,
            ordered,
            scene.exit_state,
        ):
            issues.append(
                _issue(
                    "semantic.continuity_beat_sequence_mismatch",
                    ("scenes", index),
                    "scene entry, ordered beat states, and scene exit must be compatible",
                )
            )
    if cue_order_invalid:
        issues.append(
            _issue(
                "semantic.cue_order",
                "dialogueCues",
                "cue order must be contiguous within its beat",
            )
        )
    timing_allocation = scoped_context.get("scene_timing_allocation")
    if not isinstance(timing_allocation, Mapping) or not isinstance(
        timing_allocation.get("durationBudgetUnits"), int
    ):
        raise WorkUnitContractError(
            "Scene Beats context has no valid frozen node timing allocation"
        )
    structure_is_unambiguous = (
        len(scene_ids) == len(set(scene_ids))
        and len(beat_ids) == len(set(beat_ids))
        and all(beat.scene_local_id in set(scene_ids) for beat in output.beats)
        and all(cue.beat_local_id in set(beat_ids) for cue in output.dialogue_cues)
    )
    if structure_is_unambiguous:
        scene_by_beat = {
            beat.local_beat_id: beat.scene_local_id for beat in output.beats
        }
        cue_minimum_by_scene = {scene_id: 0 for scene_id in scene_ids}
        for cue_index, cue in enumerate(output.dialogue_cues):
            if (
                dialogue_capacity_guidance.authoring_language is not None
                and cue.language != dialogue_capacity_guidance.authoring_language
            ):
                issues.append(
                    _issue(
                        "semantic.dialogue_language_not_authoring_language",
                        ("dialogueCues", cue_index, "language"),
                        "cue language differs from the frozen ProjectBrief language",
                    )
                )
                # The model-authored language is already outside the frozen
                # contract. Do not query the timing profile with that
                # untrusted value: a valid authoring-language-only profile is
                # not required to have a wildcard for arbitrary languages.
                # Returning the semantic issue keeps this failure eligible for
                # the normal bounded correction path.
                continue
            minimum = dialogue_timing_profile.estimate_text_duration_units(
                text=cue.text,
                language=cue.language,
                delivery=cue.delivery,
            )
            if minimum is None:
                raise WorkUnitContractError(
                    "dialogue timing profile has no exact or wildcard rule"
                )
            schema_maximum = dialogue_capacity_guidance.schema_max_text_codepoints
            exceeds_portable_text_cap = (
                schema_maximum is not None
                and len(cue.text.strip()) > schema_maximum
            )
            if (
                minimum > dialogue_capacity_guidance.per_cue_duration_budget_units
                or exceeds_portable_text_cap
            ):
                issues.append(
                    _issue(
                        "semantic.dialogue_cue_capacity_exceeded",
                        ("dialogueCues", cue_index, "text"),
                        "trusted cue duration exceeds its frozen per-cue capacity",
                    )
                )
            scene_id = scene_by_beat[cue.beat_local_id]
            cue_minimum_by_scene[scene_id] += minimum
        node_budget = timing_allocation["durationBudgetUnits"]
        required_node_budget = sum(
            max(1, minimum) for minimum in cue_minimum_by_scene.values()
        )
        if required_node_budget > node_budget:
            issues.append(
                _issue(
                    "semantic.dialogue_exceeds_node_budget",
                    "dialogueCues",
                    "trusted dialogue minimums exceed the frozen Story Graph node budget",
                )
            )
    join_requirements = _continuity_requirements(scoped_context)
    required_entry_facts = join_requirements["requiredEntryFacts"]
    for scene_index, scene in enumerate(output.scenes):
        for state_key, expected_value in required_entry_facts.items():
            path = (
                "scenes",
                scene_index,
                "entryState",
                "facts",
                state_key,
            )
            if state_key not in scene.entry_state.facts:
                issues.append(
                    _issue(
                        "semantic.join_entry_state_value_missing",
                        path,
                        "join entry is missing a fact from the frozen edge-transition contract",
                    )
                )
            else:
                try:
                    matches = finite_json_values_equal(
                        scene.entry_state.facts[state_key],
                        expected_value,
                    )
                except CanonicalJsonValueError:
                    issues.append(
                        _issue(
                            "semantic.join_entry_state_value_not_json",
                            path,
                            "join entry facts must be finite canonical JSON values",
                        )
                    )
                else:
                    if not matches:
                        issues.append(
                            _issue(
                                "semantic.join_entry_state_value_mismatch",
                                path,
                                "join entry fact differs from the frozen edge-transition contract",
                            )
                        )
    return tuple(issues)


def _storyboard_semantic_issues(
    output: StoryboardFragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    target = work_unit.selector.stable_id
    scene = scoped_context.get("dramatic_scene", {})
    if scene.get("id") != target:
        issues.append(_issue("context.selector", "sceneId", "trusted context does not match unit selector"))
    scene_duration_budget = scene.get("durationBudgetUnits")
    if not isinstance(scene_duration_budget, int) or isinstance(
        scene_duration_budget, bool
    ) or scene_duration_budget < 1:
        raise WorkUnitContractError(
            "Storyboard context has no valid dramatic-scene duration budget"
        )
    beat_ids = {beat["id"] for beat in scoped_context.get("beats", [])}
    shot_ids = [shot.local_shot_id for shot in output.shots]
    if len(shot_ids) != len(set(shot_ids)):
        issues.append(_issue("semantic.duplicate_shot_id", "shots", "fragment contains duplicate shot IDs"))
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    known_props = {item.id for item in bible.props}
    entities_by_type = allowed_entity_states(bible)
    cues_by_id = {
        str(cue["id"]): cue
        for cue in scoped_context.get("dialogue_cues", [])
        if isinstance(cue, Mapping) and cue.get("id")
    }
    scheduled_cues: dict[str, str] = {}
    for index, shot in enumerate(output.shots):
        if shot.location_id is not None and shot.location_id not in known_locations:
            issues.append(_issue("semantic.unknown_location", ("shots", index, "locationId"), "shot references an unknown location"))
        if set(shot.character_ids) - known_characters:
            issues.append(_issue("semantic.unknown_characters", ("shots", index, "characterIds"), "shot references unknown characters"))
        if len(shot.character_ids) != len(set(shot.character_ids)):
            issues.append(
                _issue(
                    "semantic.duplicate_character_ref",
                    ("shots", index, "characterIds"),
                    "shot references the same character more than once",
                )
            )
        if set(shot.prop_ids) - known_props:
            issues.append(_issue("semantic.unknown_props", ("shots", index, "propIds"), "shot references unknown props"))
        if len(shot.prop_ids) != len(set(shot.prop_ids)):
            issues.append(
                _issue(
                    "semantic.duplicate_prop_ref",
                    ("shots", index, "propIds"),
                    "shot references the same prop more than once",
                )
            )
        issues.extend(
            continuity_state_issues(
                shot.entry_state,
                bible=bible,
                path=("shots", index, "entryState"),
            )
        )
        issues.extend(
            continuity_state_issues(
                shot.exit_state,
                bible=bible,
                path=("shots", index, "exitState"),
            )
        )
        for cue_id in shot.cue_ids:
            if cue_id not in cues_by_id:
                issues.append(_issue("semantic.unknown_cue_ref", ("shots", index, "cueIds"), "shot references an unknown cue"))
            elif cue_id in scheduled_cues:
                issues.append(_issue("semantic.duplicate_cue_ref", ("shots", index, "cueIds"), "a cue may be scheduled only once per scene"))
            else:
                scheduled_cues[cue_id] = shot.local_shot_id
        required_entities: set[tuple[EntityType, str]] = set()
        for state_index, required in enumerate(shot.required_entity_states):
            key = (required.entity_type, required.entity_id)
            if key in required_entities:
                issues.append(_issue("semantic.duplicate_required_entity_state", ("shots", index, "requiredEntityStates", state_index), "entity state is duplicated within one shot"))
            required_entities.add(key)
            allowed = entities_by_type[required.entity_type].get(required.entity_id)
            if allowed is None:
                issues.append(_issue("semantic.unknown_required_entity", ("shots", index, "requiredEntityStates", state_index, "entityId"), "required entity is absent from the Story Bible or has the wrong type"))
            elif required.state not in allowed:
                issues.append(_issue("semantic.invalid_required_entity_state", ("shots", index, "requiredEntityStates", state_index, "state"), "required entity state is not allowed by the Story Bible"))
            if not required_entity_is_in_shot(required, shot):
                issues.append(
                    _issue(
                        "semantic.required_entity_not_in_shot",
                        (
                            "shots",
                            index,
                            "requiredEntityStates",
                            state_index,
                            "entityId",
                        ),
                        "required entity state must belong to an entity present in the shot",
                    )
                )
        for event_index, event in enumerate(shot.audio_plan.events):
            if event.start_offset_units + event.duration_units > shot.duration_units:
                issues.append(
                    _issue(
                        "semantic.audio_timing",
                        (
                            "shots",
                            index,
                            "audioPlan",
                            "events",
                            event_index,
                            "durationUnits",
                        ),
                        "audio event must fit within the shot duration",
                    )
                )
    ordered = sorted(output.shots, key=lambda shot: shot.order)
    if [shot.order for shot in ordered] != list(range(1, len(ordered) + 1)):
        issues.append(_issue("semantic.shot_order", "shots", "shot order must be contiguous from 1"))
    if not brief.shots_per_scene_min <= len(output.shots) <= brief.shots_per_scene_max:
        issues.append(_issue("semantic.shot_count", "shots", "shot count falls outside the project scene budget"))
    total_duration = sum(shot.duration_units for shot in output.shots)
    if total_duration > scene_duration_budget:
        issues.append(
            _issue(
                "semantic.shot_duration_budget_exceeded",
                "shots",
                "ordered shot durations exceed the frozen dramatic-scene duration budget",
            )
        )
    try:
        scene_entry_state = continuity_state_from_context(scene, "entryState")
        scene_exit_state = continuity_state_from_context(scene, "exitState")
    except FragmentSemanticContextError as exc:
        raise WorkUnitContractError(str(exc)) from exc
    if ordered and not continuity_sequence_is_compatible(
        scene_entry_state,
        ordered,
        scene_exit_state,
    ):
        issues.append(
            _issue(
                "semantic.continuity_shot_sequence_mismatch",
                "shots",
                "scene entry, ordered shot states, and scene exit must be compatible",
            )
        )
    linked_shots: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    primary_map = output.primary_shot_local_id_by_beat
    if set(primary_map) != beat_ids:
        issues.append(_issue("semantic.primary_coverage", "primaryShotLocalIdByBeat", "PRIMARY coverage must contain exactly the selected beat IDs"))
    for beat_id, shot_local_id in primary_map.items():
        pair = (shot_local_id, beat_id)
        if pair in pairs:
            issues.append(_issue("semantic.duplicate_link", "primaryShotLocalIdByBeat", "duplicate shot-to-beat link"))
        pairs.add(pair)
        if shot_local_id not in shot_ids:
            issues.append(_issue("semantic.unknown_link_shot", ("primaryShotLocalIdByBeat", beat_id), "PRIMARY link references a shot outside this fragment"))
        else:
            linked_shots.add(shot_local_id)
        if beat_id not in beat_ids:
            issues.append(_issue("semantic.cross_unit_beat", ("primaryShotLocalIdByBeat", beat_id), "PRIMARY link references a beat outside this fragment"))
    for index, link in enumerate(output.supporting_beat_links):
        pair = (link.shot_local_id, link.beat_id)
        if pair in pairs:
            issues.append(_issue("semantic.duplicate_link", ("supportingBeatLinks", index), "duplicate shot-to-beat link"))
        pairs.add(pair)
        if link.shot_local_id not in shot_ids:
            issues.append(_issue("semantic.unknown_link_shot", ("supportingBeatLinks", index), "supporting link references a shot outside this fragment"))
        else:
            linked_shots.add(link.shot_local_id)
        if link.beat_id not in beat_ids:
            issues.append(_issue("semantic.cross_unit_beat", ("supportingBeatLinks", index), "supporting link references a beat outside this fragment"))
    if set(shot_ids) - linked_shots:
        issues.append(_issue("semantic.unlinked_shots", "primaryShotLocalIdByBeat", "each shot must cover a selected beat"))
    for cue_id, cue in cues_by_id.items():
        scheduled_shot = scheduled_cues.get(cue_id)
        if scheduled_shot is None:
            issues.append(_issue("semantic.unscheduled_cue_ref", "shots", f"cue {cue_id} is not scheduled by a shot"))
            continue
        cue_beat_id = str(cue.get("beatId") or "")
        covered_beats = {
            beat_id
            for beat_id, shot_id in primary_map.items()
            if shot_id == scheduled_shot
        } | {
            link.beat_id
            for link in output.supporting_beat_links
            if link.shot_local_id == scheduled_shot
        }
        if cue_beat_id not in covered_beats:
            issues.append(_issue("semantic.cue_not_covered_by_shot", "shots", f"cue {cue_id} must be scheduled by a shot covering its beat"))
    for index, shot in enumerate(output.shots):
        known_cues = [cues_by_id[cue_id] for cue_id in shot.cue_ids if cue_id in cues_by_id]
        try:
            cue_order_keys = [
                cue_canonical_order_key(cue, scoped_context=scoped_context)
                for cue in known_cues
            ]
            total_cue_duration = sum(
                cue_duration_units(cue) for cue in known_cues
            )
        except FragmentSemanticContextError as exc:
            raise WorkUnitContractError(str(exc)) from exc
        if cue_order_keys != sorted(cue_order_keys):
            issues.append(
                _issue(
                    "semantic.cue_canonical_order",
                    ("shots", index, "cueIds"),
                    "cue IDs must retain canonical beat and cue order within a shot",
                )
            )
        if total_cue_duration > shot.duration_units:
            issues.append(
                _issue(
                    "semantic.cue_duration_exceeds_shot",
                    ("shots", index, "cueIds"),
                    "scheduled dialogue durations must fit within the shot duration",
                )
            )
    return tuple(issues)


def _issue(code: str, path: str | tuple[str | int, ...], message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=(path,) if isinstance(path, str) else path, message=message)


def _json_value(value: BaseModel | Mapping[str, Any]) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    return value


def _canonicalize_model_local_ids(value: Any, *, stage: StageName) -> Any:
    """Keep model-facing local IDs intact for the specialized content models."""

    del stage
    return deepcopy(value)


def _bind_fragment_foreign_keys(
    schema: dict[str, Any],
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
    storyboard_timing_guidance: StoryboardTimingGuidance | None,
) -> None:
    """Expose trusted selector/foreign-key constraints in the model schema.

    These constraints reduce avoidable model transcription errors, but do not
    replace semantic validation. Generated scene, beat, and shot handles are
    local to one response; the trusted binder derives canonical IDs only after
    this validation succeeds.
    """

    definitions = schema["$defs"]
    character_ids = sorted(item.id for item in bible.characters)
    location_ids = sorted(item.id for item in bible.locations)
    prop_ids = sorted(item.id for item in bible.props)

    if work_unit.stage == StageName.SCENE_BEATS:
        if dialogue_capacity_guidance is None:
            raise WorkUnitContractError(
                "Scene Beats schema binding requires frozen dialogue capacity guidance"
            )
        schema["properties"]["scenes"]["maxItems"] = (
            dialogue_capacity_guidance.max_scenes
        )
        schema["properties"]["dialogueCues"]["maxItems"] = (
            0
            if dialogue_capacity_guidance.schema_max_text_codepoints == 0
            else dialogue_capacity_guidance.max_dialogue_cues
        )
        scene_properties = definitions["DramaticSceneContent"]["properties"]
        _set_nullable_string_enum(scene_properties["locationId"], location_ids)
        _set_array_string_enum(scene_properties["characterIds"], character_ids)
        cue_properties = definitions["DialogueCueContent"]["properties"]
        _set_nullable_string_enum(cue_properties["speakerId"], character_ids)
        if dialogue_capacity_guidance.authoring_language is not None:
            _set_string_const(
                cue_properties["language"],
                dialogue_capacity_guidance.authoring_language,
            )
            assert dialogue_capacity_guidance.schema_max_text_codepoints is not None
            cue_properties["text"]["maxLength"] = (
                dialogue_capacity_guidance.schema_max_text_codepoints
            )
        continuity = _continuity_requirements(scoped_context)
        _require_state_fact_values(
            scene_properties["entryState"],
            continuity["requiredEntryFacts"],
        )
        require_first_scene_entity_state_values(
            definitions["DramaticSceneContent"],
            edge_entry_state_requirements(scoped_context)["requiredEntityStates"],
        )
        return

    if work_unit.stage != StageName.STORYBOARD:
        raise WorkUnitContractError("foreign-key binding only supports sharded stages")
    if dialogue_capacity_guidance is not None:
        raise WorkUnitContractError(
            "dialogue capacity guidance only belongs to Scene Beats"
        )
    if storyboard_timing_guidance is None:
        raise WorkUnitContractError(
            "Storyboard schema binding requires frozen timing guidance"
        )
    schema["properties"]["shots"].update(
        {
            "minItems": storyboard_timing_guidance.min_shots,
            "maxItems": storyboard_timing_guidance.max_shots,
        }
    )
    shot_properties = definitions["ShotContent"]["properties"]
    _set_nullable_string_enum(shot_properties["locationId"], location_ids)
    _set_array_string_enum(shot_properties["characterIds"], character_ids)
    _set_array_string_enum(shot_properties["propIds"], prop_ids)
    cue_ids = sorted(
        str(item["id"])
        for item in scoped_context.get("dialogue_cues", [])
        if isinstance(item, Mapping) and item.get("id")
    )
    _set_array_string_enum(shot_properties["cueIds"], cue_ids)
    beat_ids = sorted(
        str(item["id"])
        for item in scoped_context.get("beats", [])
        if isinstance(item, Mapping) and item.get("id")
    )
    _set_string_enum(
        definitions["SupportingBeatLinkContent"]["properties"]["beatId"], beat_ids
    )
    primary_coverage = schema["properties"]["primaryShotLocalIdByBeat"]
    primary_coverage.clear()
    primary_coverage.update(
        {
            "type": "object",
            "properties": {
                beat_id: {"type": "string", "minLength": 1}
                for beat_id in beat_ids
            },
            "required": beat_ids,
            "additionalProperties": False,
            "minProperties": len(beat_ids),
            "maxProperties": len(beat_ids),
        }
    )
    # Native strict JSON-Schema providers require every declared root property.
    # Supporting coverage is semantically optional, but its wire representation
    # is always an array; models return [] when no supporting link is needed.


def _set_string_const(schema_node: dict[str, Any], value: str) -> None:
    schema_node.clear()
    schema_node.update({"type": "string", "const": value})


def _set_string_enum(schema_node: dict[str, Any], values: list[str]) -> None:
    schema_node.clear()
    schema_node.update({"type": "string", "enum": values})


def _set_nullable_string_enum(
    schema_node: dict[str, Any], values: list[str]
) -> None:
    description = schema_node.get("description")
    schema_node.clear()
    if values:
        schema_node.update(
            {
                "anyOf": [
                    {"type": "string", "enum": values},
                    {"type": "null"},
                ]
            }
        )
    else:
        schema_node.update({"type": "null"})
    if isinstance(description, str) and description:
        schema_node["description"] = description


def _set_array_string_enum(
    schema_node: dict[str, Any], values: list[str]
) -> None:
    schema_node["items"] = {"type": "string", "enum": values}
    if not values:
        schema_node["maxItems"] = 0


def _continuity_requirements(
    scoped_context: Mapping[str, Any],
) -> dict[str, Any]:
    value = scoped_context.get("join_state_value_requirements")
    if not isinstance(value, Mapping):
        raise WorkUnitContractError(
            "Scene Beats context has no frozen join state value requirements"
        )
    version = value.get("contractVersion")
    contract_hash = value.get("contractHash")
    keys = value.get("requiredEntryFactKeys")
    facts = value.get("requiredEntryFacts")
    transitions = value.get("outgoingJoinTransitions")
    if (
        not isinstance(version, str)
        or not version
        or not isinstance(contract_hash, str)
        or len(contract_hash) != 64
        or not isinstance(keys, list)
        or any(not isinstance(key, str) or not key for key in keys)
        or len(keys) != len(set(keys))
        or not isinstance(facts, Mapping)
        or set(keys) != set(facts)
        or not isinstance(transitions, list)
    ):
        raise WorkUnitContractError(
            "Scene Beats join state value requirements are malformed"
        )
    return deepcopy(dict(value))


def _require_state_fact_values(
    schema_node: dict[str, Any],
    facts: Mapping[str, Any],
) -> None:
    if not facts:
        return
    keys = sorted(facts)
    referenced_state = deepcopy(schema_node)
    schema_node.clear()
    schema_node.update(
        {
            "allOf": [referenced_state],
            "type": "object",
            "required": ["facts"],
            "properties": {
                "facts": {
                    "type": "object",
                    "required": keys,
                    "properties": {
                        key: {"const": deepcopy(facts[key])}
                        for key in keys
                    },
                }
            },
        }
    )


def _resolve_schema(schema_node: Any, root: Mapping[str, Any]) -> Any:
    if not isinstance(schema_node, Mapping):
        return schema_node
    reference = schema_node.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return schema_node
    resolved: Any = root
    for segment in reference[2:].split("/"):
        if not isinstance(resolved, Mapping):
            return schema_node
        resolved = resolved.get(segment.replace("~1", "/").replace("~0", "~"))
    return resolved


def _schema_matches_value(schema_node: Any, value: Any, root: Mapping[str, Any]) -> bool:
    resolved = _resolve_schema(schema_node, root)
    if not isinstance(resolved, Mapping):
        return True
    kind = resolved.get("type")
    return {
        "null": value is None,
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }.get(str(kind), True)


def _presence_issues(value: Any, schema: Mapping[str, Any]) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    def visit(current: Any, schema_node: Any, path: tuple[str | int, ...]) -> None:
        resolved = _resolve_schema(schema_node, schema)
        if not isinstance(resolved, Mapping):
            return
        all_of = resolved.get("allOf")
        if isinstance(all_of, list):
            for item in all_of:
                visit(current, item, path)
        variants = resolved.get("anyOf") or resolved.get("oneOf")
        if isinstance(variants, list):
            selected = next((item for item in variants if _schema_matches_value(item, current, schema)), None)
            if selected is not None:
                visit(current, selected, path)
            return
        properties = resolved.get("properties")
        required = resolved.get("required")
        if isinstance(required, list) and isinstance(current, Mapping):
            for name in required:
                if (
                    isinstance(name, str)
                    and name not in current
                    and not (isinstance(properties, Mapping) and name in properties)
                ):
                    issues.append(
                        ValidationIssue(
                            code="schema.missing",
                            message="Field required for generated fragment output",
                            path=(*path, name),
                        )
                    )
        if isinstance(properties, Mapping) and isinstance(current, Mapping):
            for name, child in properties.items():
                if name not in current:
                    if isinstance(required, list) and name in required:
                        issues.append(ValidationIssue(code="schema.missing", message="Field required for generated fragment output", path=(*path, str(name))))
                else:
                    visit(current[name], child, (*path, str(name)))
            return
        items = resolved.get("items")
        if items is not None and isinstance(current, list):
            for index, item in enumerate(current):
                visit(item, items, (*path, index))

    visit(value, schema, ())
    return tuple(issues)
