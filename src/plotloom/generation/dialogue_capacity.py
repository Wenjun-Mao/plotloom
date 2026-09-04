"""Pure, hash-bound dialogue capacity planning for Scene Beats.

The timing allocator owns the total duration of a Story Graph node.  This
module turns that immutable total plus the sealed dialogue timing profile into
a small authoring envelope.  It intentionally does not inspect model output
or alter dialogue text: later prompt/schema and validation layers consume the
same frozen facts.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import ConfigDict, Field, model_validator

from ..canonical_schema import DialogueDeliveryPace, DialogueTimingProfile
from ..domain import CamelModel, to_camel
from .scene_timing_allocation import SceneTimingAllocation


DIALOGUE_CAPACITY_POLICY_V1 = "dialogue_capacity.v1"
DIALOGUE_CAPACITY_POLICY_V2 = "dialogue_capacity.v2"
# New plans use v2.  v1 remains executable because sealed StagePlans name their
# own policy; do not reinterpret a persisted v1 envelope using these defaults.
DIALOGUE_CAPACITY_POLICY_VERSION = DIALOGUE_CAPACITY_POLICY_V2


class _CapacityPolicy:
    def __init__(self, *, max_scenes: int, max_dialogue_cues: int) -> None:
        self.max_scenes = max_scenes
        self.max_dialogue_cues = max_dialogue_cues


_POLICIES = {
    DIALOGUE_CAPACITY_POLICY_V1: _CapacityPolicy(max_scenes=2, max_dialogue_cues=4),
    DIALOGUE_CAPACITY_POLICY_V2: _CapacityPolicy(max_scenes=2, max_dialogue_cues=2),
}
# Public aliases describe the new-plan default only.  Historical v1 replay
# always selects its named policy above.
MAX_SCENES_PER_NODE = _POLICIES[DIALOGUE_CAPACITY_POLICY_VERSION].max_scenes
MAX_DIALOGUE_CUES_PER_NODE = _POLICIES[DIALOGUE_CAPACITY_POLICY_VERSION].max_dialogue_cues


class DialogueCapacityPlanningError(ValueError):
    """A frozen node cap cannot support the current capacity policy."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class _FrozenCamelModel(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class DialogueCapacityRuleGuidance(_FrozenCamelModel):
    """One profile rule projected into one node's authoring envelope."""

    language: str = Field(min_length=1)
    delivery: DialogueDeliveryPace
    units_per_character: int = Field(ge=1)
    max_text_codepoints: int = Field(ge=0)


class DialogueCapacityNodeGuidance(_FrozenCamelModel):
    """The bounded dialogue envelope for one immutable Story Graph node."""

    node_id: str = Field(min_length=1)
    duration_budget_units: int = Field(ge=1)
    max_scenes: int = Field(ge=1)
    max_dialogue_cues: int = Field(ge=1)
    per_cue_duration_budget_units: int = Field(ge=1)
    rule_guidance: tuple[DialogueCapacityRuleGuidance, ...] = Field(min_length=1)
    # These two fields were intentionally absent from v1's serialized shape.
    # They are optional only for exact historical hash compatibility.
    authoring_language: str | None = Field(default=None, min_length=1)
    schema_max_text_codepoints: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _rules_are_unique(self) -> "DialogueCapacityNodeGuidance":
        keys = [(rule.language, rule.delivery) for rule in self.rule_guidance]
        if len(keys) != len(set(keys)):
            raise ValueError("dialogue capacity rules must be unique by language and delivery")
        if (self.authoring_language is None) != (self.schema_max_text_codepoints is None):
            raise ValueError("authoring language and schema text cap must be set together")
        return self


class DialogueCapacityPlan(_FrozenCamelModel):
    """Versioned capacity guidance derived only from frozen timing inputs."""

    policy_version: str = Field(default=DIALOGUE_CAPACITY_POLICY_VERSION, min_length=1)
    scene_timing_allocation_version: str = Field(min_length=1)
    scene_timing_allocation_hash: str = Field(min_length=64, max_length=64)
    dialogue_timing_profile_version: str = Field(min_length=1)
    dialogue_timing_profile_hash: str = Field(min_length=64, max_length=64)
    max_scenes_per_node: int = Field(default=MAX_SCENES_PER_NODE, ge=1)
    max_dialogue_cues_per_node: int = Field(default=MAX_DIALOGUE_CUES_PER_NODE, ge=1)
    # v1 has no plan-level authoring language.  v2 freezes it both at the plan
    # boundary and inside each node guidance used by the provider schema.
    authoring_language: str | None = Field(default=None, min_length=1)
    node_guidance: tuple[DialogueCapacityNodeGuidance, ...] = Field(min_length=1)
    capacity_plan_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def _validate_shape_and_hash(self) -> "DialogueCapacityPlan":
        node_ids = [guidance.node_id for guidance in self.node_guidance]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("dialogue capacity guidance must name each node once")
        if any(
            guidance.max_scenes != self.max_scenes_per_node
            or guidance.max_dialogue_cues != self.max_dialogue_cues_per_node
            for guidance in self.node_guidance
        ):
            raise ValueError("node guidance must use the plan capacity policy")
        if self.policy_version == DIALOGUE_CAPACITY_POLICY_V2:
            if self.authoring_language is None or any(
                guidance.authoring_language != self.authoring_language
                or guidance.schema_max_text_codepoints is None
                for guidance in self.node_guidance
            ):
                raise ValueError("dialogue_capacity.v2 requires one frozen authoring language")
        elif self.policy_version == DIALOGUE_CAPACITY_POLICY_V1:
            if self.authoring_language is not None or any(
                guidance.authoring_language is not None
                or guidance.schema_max_text_codepoints is not None
                for guidance in self.node_guidance
            ):
                raise ValueError("dialogue_capacity.v1 may not contain v2 authoring fields")
        else:
            raise ValueError("unsupported dialogue capacity policy")
        unsigned = self.model_dump(mode="json", by_alias=True, exclude={"capacity_plan_hash"})
        # v1 was sealed before authoringLanguage/schemaMaxTextCodepoints
        # existed.  Preserve its byte-for-byte hash input rather than treating
        # a missing value as a current default.
        if self.policy_version == DIALOGUE_CAPACITY_POLICY_V1:
            unsigned.pop("authoringLanguage", None)
            for guidance in unsigned["nodeGuidance"]:
                guidance.pop("authoringLanguage", None)
                guidance.pop("schemaMaxTextCodepoints", None)
        if self.capacity_plan_hash != _sha256(unsigned):
            raise ValueError("capacityPlanHash does not match the immutable capacity plan")
        return self

    def guidance_for(self, node_id: str) -> DialogueCapacityNodeGuidance:
        for guidance in self.node_guidance:
            if guidance.node_id == node_id:
                return guidance
        raise KeyError(node_id)


def dialogue_timing_profile_hash(profile: DialogueTimingProfile) -> str:
    """Return the durable identity of the exact profile used for capacity."""

    return _sha256(profile.model_dump(mode="json", by_alias=True))


def plan_dialogue_capacity(
    *,
    scene_timing_allocation: SceneTimingAllocation,
    dialogue_timing_profile: DialogueTimingProfile,
    authoring_language: str | None = None,
    policy_version: str = DIALOGUE_CAPACITY_POLICY_VERSION,
) -> DialogueCapacityPlan:
    """Build a conservative, per-node envelope without model arithmetic.

    Reserve one unit for each policy-bounded scene, then split the remaining
    node budget into equal cue slots.  Any node unable to fund all slots fails
    before a provider call rather than silently emitting an unusable envelope.
    A rule whose one-character minimum is greater than a slot remains present
    with ``maxTextCodepoints=0``; later model-facing layers can exclude that
    choice while the plan still faithfully describes the frozen profile.
    """

    try:
        policy = _POLICIES[policy_version]
    except KeyError as exc:
        raise DialogueCapacityPlanningError(
            "dialogue_capacity.policy_unknown",
            f"unsupported dialogue capacity policy: {policy_version}",
        ) from exc
    if policy_version == DIALOGUE_CAPACITY_POLICY_V2 and not authoring_language:
        raise DialogueCapacityPlanningError(
            "dialogue_capacity.authoring_language_required",
            "dialogue_capacity.v2 requires the frozen ProjectBrief language",
        )
    if policy_version == DIALOGUE_CAPACITY_POLICY_V1 and authoring_language is not None:
        raise DialogueCapacityPlanningError(
            "dialogue_capacity.v1_authoring_language_forbidden",
            "dialogue_capacity.v1 must retain its original serialized shape",
        )
    if policy_version == DIALOGUE_CAPACITY_POLICY_V2:
        assert authoring_language is not None
        missing_deliveries = tuple(
            delivery.value
            for delivery in DialogueDeliveryPace
            if dialogue_timing_profile.rule_for(
                language=authoring_language,
                delivery=delivery,
            )
            is None
        )
        if missing_deliveries:
            raise DialogueCapacityPlanningError(
                "dialogue_capacity.timing_profile_incomplete",
                "dialogue_capacity.v2 requires an exact or wildcard timing rule "
                "for every delivery in the frozen authoring language",
            )
    required_minimum = policy.max_scenes + policy.max_dialogue_cues
    node_guidance: list[DialogueCapacityNodeGuidance] = []
    for allocation in scene_timing_allocation.node_allocations:
        budget = allocation.duration_budget_units
        if budget < required_minimum:
            raise DialogueCapacityPlanningError(
                "dialogue_capacity.node_budget_too_small",
                "node "
                f"{allocation.node_id} has {budget} duration units, but dialogue capacity "
                f"policy {policy_version} requires at least "
                f"{required_minimum} for {policy.max_scenes} scene floors and "
                f"{policy.max_dialogue_cues} cue slots",
            )
        per_cue_budget = (budget - policy.max_scenes) // policy.max_dialogue_cues
        rule_guidance = tuple(
            DialogueCapacityRuleGuidance(
                language=rule.language,
                delivery=rule.delivery,
                units_per_character=rule.units_per_character,
                max_text_codepoints=per_cue_budget // rule.units_per_character,
            )
            for rule in dialogue_timing_profile.rules
        )
        schema_max_text_codepoints: int | None = None
        if policy_version == DIALOGUE_CAPACITY_POLICY_V2:
            assert authoring_language is not None
            safe_caps = []
            for delivery in DialogueDeliveryPace:
                rule = dialogue_timing_profile.rule_for(
                    language=authoring_language,
                    delivery=delivery,
                )
                # Completeness is a plan-level precondition above. Keep the
                # assertion adjacent to this projection so future enum changes
                # cannot silently turn a missing rule into provider work.
                assert rule is not None
                safe_caps.append(per_cue_budget // rule.units_per_character)
            # A portable schema has one text.maxLength rather than
            # provider-specific conditionals.  The minimum is safe for every
            # permitted delivery; zero makes dialogue impossible for this node.
            schema_max_text_codepoints = min(safe_caps, default=0)
        node_guidance.append(
            DialogueCapacityNodeGuidance(
                node_id=allocation.node_id,
                duration_budget_units=budget,
                max_scenes=policy.max_scenes,
                max_dialogue_cues=policy.max_dialogue_cues,
                per_cue_duration_budget_units=per_cue_budget,
                rule_guidance=rule_guidance,
                authoring_language=authoring_language,
                schema_max_text_codepoints=schema_max_text_codepoints,
            )
        )
    node_payloads = [item.model_dump(mode="json", by_alias=True) for item in node_guidance]
    if policy_version == DIALOGUE_CAPACITY_POLICY_V1:
        for guidance in node_payloads:
            guidance.pop("authoringLanguage", None)
            guidance.pop("schemaMaxTextCodepoints", None)
    unsigned = {
        "policyVersion": policy_version,
        "sceneTimingAllocationVersion": scene_timing_allocation.allocation_version,
        "sceneTimingAllocationHash": scene_timing_allocation.allocation_hash,
        "dialogueTimingProfileVersion": dialogue_timing_profile.version,
        "dialogueTimingProfileHash": dialogue_timing_profile_hash(dialogue_timing_profile),
        "maxScenesPerNode": policy.max_scenes,
        "maxDialogueCuesPerNode": policy.max_dialogue_cues,
        **({"authoringLanguage": authoring_language} if authoring_language is not None else {}),
        "nodeGuidance": node_payloads,
    }
    return DialogueCapacityPlan(**unsigned, capacity_plan_hash=_sha256(unsigned))


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
