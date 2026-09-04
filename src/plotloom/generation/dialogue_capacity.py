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


DIALOGUE_CAPACITY_POLICY_VERSION = "dialogue_capacity.v1"
MAX_SCENES_PER_NODE = 2
MAX_DIALOGUE_CUES_PER_NODE = 4


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

    @model_validator(mode="after")
    def _rules_are_unique(self) -> "DialogueCapacityNodeGuidance":
        keys = [(rule.language, rule.delivery) for rule in self.rule_guidance]
        if len(keys) != len(set(keys)):
            raise ValueError("dialogue capacity rules must be unique by language and delivery")
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
        unsigned = self.model_dump(mode="json", by_alias=True, exclude={"capacity_plan_hash"})
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
) -> DialogueCapacityPlan:
    """Build a conservative, per-node envelope without model arithmetic.

    Reserve one unit for each policy-bounded scene, then split the remaining
    node budget into equal cue slots.  Any node unable to fund all slots fails
    before a provider call rather than silently emitting an unusable envelope.
    A rule whose one-character minimum is greater than a slot remains present
    with ``maxTextCodepoints=0``; later model-facing layers can exclude that
    choice while the plan still faithfully describes the frozen profile.
    """

    required_minimum = MAX_SCENES_PER_NODE + MAX_DIALOGUE_CUES_PER_NODE
    node_guidance: list[DialogueCapacityNodeGuidance] = []
    for allocation in scene_timing_allocation.node_allocations:
        budget = allocation.duration_budget_units
        if budget < required_minimum:
            raise DialogueCapacityPlanningError(
                "dialogue_capacity.node_budget_too_small",
                "node "
                f"{allocation.node_id} has {budget} duration units, but dialogue capacity "
                f"policy {DIALOGUE_CAPACITY_POLICY_VERSION} requires at least "
                f"{required_minimum} for {MAX_SCENES_PER_NODE} scene floors and "
                f"{MAX_DIALOGUE_CUES_PER_NODE} cue slots",
            )
        per_cue_budget = (budget - MAX_SCENES_PER_NODE) // MAX_DIALOGUE_CUES_PER_NODE
        node_guidance.append(
            DialogueCapacityNodeGuidance(
                node_id=allocation.node_id,
                duration_budget_units=budget,
                max_scenes=MAX_SCENES_PER_NODE,
                max_dialogue_cues=MAX_DIALOGUE_CUES_PER_NODE,
                per_cue_duration_budget_units=per_cue_budget,
                rule_guidance=tuple(
                    DialogueCapacityRuleGuidance(
                        language=rule.language,
                        delivery=rule.delivery,
                        units_per_character=rule.units_per_character,
                        max_text_codepoints=per_cue_budget // rule.units_per_character,
                    )
                    for rule in dialogue_timing_profile.rules
                ),
            )
        )
    unsigned = {
        "policyVersion": DIALOGUE_CAPACITY_POLICY_VERSION,
        "sceneTimingAllocationVersion": scene_timing_allocation.allocation_version,
        "sceneTimingAllocationHash": scene_timing_allocation.allocation_hash,
        "dialogueTimingProfileVersion": dialogue_timing_profile.version,
        "dialogueTimingProfileHash": dialogue_timing_profile_hash(dialogue_timing_profile),
        "maxScenesPerNode": MAX_SCENES_PER_NODE,
        "maxDialogueCuesPerNode": MAX_DIALOGUE_CUES_PER_NODE,
        "nodeGuidance": [item.model_dump(mode="json", by_alias=True) for item in node_guidance],
    }
    return DialogueCapacityPlan(**unsigned, capacity_plan_hash=_sha256(unsigned))


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
