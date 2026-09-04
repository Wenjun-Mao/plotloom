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
    RequiredEntityState,
    SceneBeatPlanV2,
    ShotV2,
    ShotBeatLinkV2,
    StageName,
    StoryBibleV2,
    StoryGraphV2,
)
from ..canonical_schema import NonBlankText, V2CoverageRole, V2ShotSize
from .contracts import RenderedPrompt, ValidationIssue, ValidationReport
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
    DialogueCapacityPlanningError,
    dialogue_timing_profile_hash,
    plan_dialogue_capacity,
)
from .fragments import SceneBeatsFragment, StageFragment, StoryboardFragment
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
from .story_graph_topology import (
    STORY_GRAPH_CONTENT_FILL_SCHEMA_ID,
    StoryGraphContentBindingError,
    StoryGraphContentFill,
    StoryGraphTopology,
    bind_story_graph_content_fill,
    story_graph_content_fill_manifest,
    story_graph_content_fill_schema,
)
from .validation import CanonicalStageValidationAdapter, SemanticValidationContext, ValidationAdapter


WORK_UNIT_PROMPT_CONTRACT_VERSION = "m1.12h"
CORRECTION_POLICY_VERSION = "bounded_correction.v9"
FRAGMENT_ID_BINDING_VERSION = "fragment_ids.v1"
STORYBOARD_PRIMARY_COVERAGE_BINDING_VERSION = "storyboard_primary_coverage.v1"
SCENE_BEATS_FRAGMENT_SCHEMA_ID = "scene_beats.fragment.v9"
STORYBOARD_FRAGMENT_SCHEMA_ID = "storyboard.fragment.v4"


class WorkUnitContractError(ValueError):
    """A planned unit cannot be rendered or bound at the trusted boundary."""


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
    order: int = Field(ge=1)
    speaker_id: str | None
    voice_over: NonBlankText | None
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


SemanticRepairFact: TypeAlias = Annotated[
    DialogueTimingRepairFact
    | DialogueCapacityRepairFact
    | JoinAllowedDifferencesRepairFact
    | RequiredEntityStateRepairFact,
    Field(discriminator="code"),
]
_SEMANTIC_REPAIR_FACT_ADAPTER = TypeAdapter(SemanticRepairFact)


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
    audio_plan: AudioPlan
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


FragmentOutput: TypeAlias = SceneBeatsFragmentOutput | StoryboardFragmentOutput


class StoryGraphContentFillValidationAdapter(ValidationAdapter[StoryGraphV2]):
    """Validate model prose against a frozen topology before canonicalizing it."""

    schema_id = STORY_GRAPH_CONTENT_FILL_SCHEMA_ID

    def __init__(self, *, topology: StoryGraphTopology, brief: ProjectBrief) -> None:
        self.topology = topology
        self.brief = brief

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
            graph = bind_story_graph_content_fill(self.topology, fill, brief=self.brief)
        except StoryGraphContentBindingError as exc:
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code=issue["code"],
                        message=issue["message"],
                        path=tuple(part for part in issue["path"].split(".") if part),
                    )
                    for issue in exc.issues
                ),
            )
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
        return self
    unit_dependency_hash: str = Field(min_length=1)
    fragment_id_binding_version: str = FRAGMENT_ID_BINDING_VERSION
    storyboard_primary_coverage_binding_version: str | None = None


@dataclass(frozen=True)
class CompiledWorkUnitRequest:
    """Pure hand-off object consumed later by Pipeline/Provider adapters."""

    rendered: RenderedPrompt
    validator: ValidationAdapter[Any]
    contract: WorkUnitPromptContract
    response_schema: dict[str, Any]


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

    adapter = _validator_for_unit(
        work_unit=work_unit,
        stage_plan=stage_plan,
        brief=brief,
        dependencies=dependencies,
        scoped_context=scoped_context,
        story_graph_topology=story_graph_topology,
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
    contract = WorkUnitPromptContract(
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
) -> ValidationAdapter[Any]:
    if work_unit.stage == StageName.STORY_BIBLE:
        return CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=brief)
    bible = dependencies.get(StageName.STORY_BIBLE)
    if not isinstance(bible, StoryBibleV2):
        raise WorkUnitContractError(f"{work_unit.stage.value} requires a sealed StoryBible")
    if work_unit.stage == StageName.STORY_GRAPH:
        if story_graph_topology is not None:
            return StoryGraphContentFillValidationAdapter(topology=story_graph_topology, brief=brief)
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
                audio_plan=shot.audio_plan,
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
) -> tuple[JoinAllowedDifferencesRepairFact, ...]:
    """Derive missing tracked keys for the one safe join-subset repair.

    Blank and duplicate keys remain ordinary semantic failures: guessing how
    to rewrite those arrays could erase author intent.  For the subset issue,
    appending the model-authored allowed keys is both deterministic and
    semantics-preserving.  Trusted code supplies that fact but never installs
    a repaired candidate directly.
    """

    relevant_issues = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.join_allowed_differences_must_be_required"
    )
    if not relevant_issues:
        return ()
    try:
        fill = StoryGraphContentFill.model_validate(value, by_alias=True)
    except ValidationError:
        return ()
    joins_by_id = {join.id: join for join in fill.join_contracts}
    facts: list[JoinAllowedDifferencesRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 3
            or path[0] != "joinContracts"
            or not isinstance(path[1], str)
            or path[2] != "allowedDifferences"
        ):
            continue
        join = joins_by_id.get(path[1])
        if join is None:
            continue
        # A deterministic append is safe only after the two source arrays pass
        # their own hygiene invariants.  Blank or duplicate keys need a normal
        # model correction; turning them into trusted facts would either fail
        # fact validation or prescribe another invalid array.
        key_lists = (join.required_state_keys, join.allowed_differences)
        if any(
            any(not key.strip() for key in keys)
            or len(keys) != len(set(keys))
            for keys in key_lists
        ):
            continue
        required = set(join.required_state_keys)
        missing = tuple(
            key for key in join.allowed_differences if key not in required
        )
        if not missing:
            continue
        facts.append(
            JoinAllowedDifferencesRepairFact(
                code=issue.code,
                path=path,
                join_contract_id=join.id,
                missing_required_state_keys=missing,
                expected_required_state_keys=tuple(
                    (*join.required_state_keys, *missing)
                ),
                expected_allowed_differences=tuple(join.allowed_differences),
            )
        )
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


def semantic_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2 | None = None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None = None,
) -> tuple[SemanticRepairFact, ...]:
    """Route stable issues to versioned, stage-owned deterministic facts."""

    if stage == StageName.STORY_GRAPH:
        return story_graph_join_repair_facts(value, issues)
    if stage == StageName.STORYBOARD and bible is not None:
        return storyboard_required_entity_state_repair_facts(
            value,
            issues,
            bible=bible,
        )
    if stage == StageName.SCENE_BEATS and dialogue_capacity_guidance is not None:
        return scene_beats_dialogue_capacity_repair_facts(
            value,
            issues,
            guidance=dialogue_capacity_guidance,
        )
    return ()


def parse_semantic_repair_fact(value: Any) -> SemanticRepairFact:
    """Revalidate persisted repair evidence without adding current defaults."""

    return _SEMANTIC_REPAIR_FACT_ADAPTER.validate_python(value)


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
                issues.append(_issue("semantic.cue_order", "dialogueCues", "cue order must be contiguous within its beat"))
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
    for contract in scoped_context.get("join_contracts", []):
        required_keys = set(contract.get("requiredStateKeys", []))
        if target == contract.get("joinNodeId"):
            if any(not required_keys <= set(scene.entry_state.facts) for scene in output.scenes):
                issues.append(_issue("semantic.join_entry_state", "scenes", "join fragment is missing required entry-state facts"))
        if target in set(contract.get("incomingNodeIds", [])):
            if any(not required_keys <= set(scene.exit_state.facts) for scene in output.scenes):
                issues.append(_issue("semantic.join_exit_state", "scenes", "incoming fragment is missing required exit-state facts"))
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
    beat_ids = {beat["id"] for beat in scoped_context.get("beats", [])}
    shot_ids = [shot.local_shot_id for shot in output.shots]
    if len(shot_ids) != len(set(shot_ids)):
        issues.append(_issue("semantic.duplicate_shot_id", "shots", "fragment contains duplicate shot IDs"))
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    known_props = {item.id for item in bible.props}
    entities_by_type = {
        EntityType.CHARACTER: {item.id: set(item.allowed_states) for item in bible.characters},
        EntityType.LOCATION: {item.id: set(item.allowed_states) for item in bible.locations},
        EntityType.PROP: {item.id: set(item.allowed_states) for item in bible.props},
    }
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
        for event_index, event in enumerate(shot.audio_plan.events):
            if event.start_offset_units + event.duration_units > shot.duration_units:
                issues.append(_issue("semantic.audio_timing", ("shots", index, "audioPlan", "events", event_index), "audio event must fit within the shot duration"))
    ordered = sorted(output.shots, key=lambda shot: shot.order)
    if [shot.order for shot in ordered] != list(range(1, len(ordered) + 1)):
        issues.append(_issue("semantic.shot_order", "shots", "shot order must be contiguous from 1"))
    if not brief.shots_per_scene_min <= len(output.shots) <= brief.shots_per_scene_max:
        issues.append(_issue("semantic.shot_count", "shots", "shot count falls outside the project scene budget"))
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
        _require_state_fact_keys(
            scene_properties["entryState"],
            continuity["requiredEntryFactKeys"],
        )
        _require_state_fact_keys(
            scene_properties["exitState"],
            continuity["requiredExitFactKeys"],
        )
        return

    if work_unit.stage != StageName.STORYBOARD:
        raise WorkUnitContractError("foreign-key binding only supports sharded stages")
    if dialogue_capacity_guidance is not None:
        raise WorkUnitContractError(
            "dialogue capacity guidance only belongs to Scene Beats"
        )
    schema["properties"]["shots"].update(
        {
            "minItems": brief.shots_per_scene_min,
            "maxItems": brief.shots_per_scene_max,
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


def _set_array_string_enum(
    schema_node: dict[str, Any], values: list[str]
) -> None:
    schema_node["items"] = {"type": "string", "enum": values}
    if not values:
        schema_node["maxItems"] = 0


def _continuity_requirements(
    scoped_context: Mapping[str, Any],
) -> dict[str, list[str]]:
    target = str(scoped_context.get("story_node", {}).get("id") or "")
    entry_keys: set[str] = set()
    exit_keys: set[str] = set()
    for contract in scoped_context.get("join_contracts", []):
        if not isinstance(contract, Mapping):
            continue
        keys = {
            str(key)
            for key in contract.get("requiredStateKeys", [])
            if isinstance(key, str) and key
        }
        if contract.get("joinNodeId") == target:
            entry_keys.update(keys)
        if target in set(contract.get("incomingNodeIds", [])):
            exit_keys.update(keys)
    return {
        "requiredEntryFactKeys": sorted(entry_keys),
        "requiredExitFactKeys": sorted(exit_keys),
    }


def _require_state_fact_keys(schema_node: dict[str, Any], keys: list[str]) -> None:
    if not keys:
        return
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
