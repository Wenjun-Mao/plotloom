"""Frozen generation planning contracts and exact hash validation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain import (
    STAGE_ORDER,
    DialogueTimingProfile,
    StageName,
)
from .dialogue_capacity import (
    DialogueCapacityPlan,
    DialogueCapacityPlanningError,
    plan_dialogue_capacity,
)
from .prompts import canonical_json, sha256_text
from .scene_timing_allocation import (
    SceneTimingAllocation,
)

PLANNING_POLICY_VERSION = "m1.5-p0.7"


class PlanningError(ValueError):
    """The requested scope cannot be turned into a bounded deterministic plan."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "planning.invalid",
        stage: StageName | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage


class PlanningModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkUnitSelectorKind(str, Enum):
    WHOLE_STAGE = "whole_stage"
    STORY_NODE = "story_node"
    DRAMATIC_SCENE = "dramatic_scene"


class WorkUnitSelector(PlanningModel):
    kind: WorkUnitSelectorKind
    stable_id: str = Field(min_length=1)


class StageBudget(PlanningModel):
    """Bounds frozen in the run plan, then copied into each work unit."""

    max_units: int = Field(default=64, ge=1)
    max_input_bytes: int = Field(default=1_000_000, ge=1)
    max_output_tokens: int = Field(default=8_192, ge=1)
    max_aggregate_items: int = Field(default=10_000, ge=1)


DEFAULT_STAGE_BUDGETS: dict[StageName, StageBudget] = {
    StageName.STORY_BIBLE: StageBudget(max_units=1, max_output_tokens=8_192),
    StageName.STORY_GRAPH: StageBudget(max_units=1, max_output_tokens=8_192),
    StageName.SCENE_BEATS: StageBudget(max_units=128, max_output_tokens=4_096),
    StageName.STORYBOARD: StageBudget(max_units=256, max_output_tokens=4_096),
}


class GenerationPlan(PlanningModel):
    """Run-level contract created at enqueue time.

    ``canonical_input_hashes`` contains only inputs that were already canonical
    at enqueue.  It intentionally does not contain future Story Graph nodes or
    dramatic scenes; their selectors are first frozen by ``plan_stage``.
    """

    run_id: str = Field(min_length=1)
    requested_stages: tuple[StageName, ...]
    planning_policy_version: Literal["m1.5-p0.7"]
    planning_policy_hash: str
    provider_profile_hash: str = Field(min_length=1)
    story_graph_topology_hash: str | None
    canonical_snapshot_hash: str = Field(min_length=1)
    canonical_snapshot_bytes: int = Field(ge=0)
    instructions_hash: str = Field(min_length=1)
    instructions_bytes: int = Field(ge=0)
    run_request_hash: str = Field(min_length=1)
    canonical_input_hashes: dict[StageName, str]
    stage_budgets: dict[StageName, StageBudget]
    context_window_tokens: int = Field(ge=1)
    prompt_overhead_bytes: int = Field(ge=0)
    max_concurrency: int = Field(default=1, ge=1, le=32)
    plan_hash: str

    @model_validator(mode="after")
    def validate_requested_range(self) -> "GenerationPlan":
        stages = list(self.requested_stages)
        if not stages:
            raise ValueError("generation plans require at least one requested stage")
        if len(stages) != len(set(stages)):
            raise ValueError("requested stages must not contain duplicates")
        first = STAGE_ORDER.index(stages[0])
        if stages != list(STAGE_ORDER[first : first + len(stages)]):
            raise ValueError("requested stages must form a contiguous canonical range")
        if set(self.stage_budgets) != set(stages):
            raise ValueError(
                "stage budgets must exist for exactly the requested stages"
            )
        if self.planning_policy_hash != sha256_text(self.planning_policy_version):
            raise ValueError("planning policy hash does not match its version")
        expected_request_hash = sha256_text(
            canonical_json(
                {
                    "canonical_snapshot_hash": self.canonical_snapshot_hash,
                    "instructions_hash": self.instructions_hash,
                }
            )
        )
        if self.run_request_hash != expected_request_hash:
            raise ValueError("run request hash does not match its frozen inputs")
        expected_hash = _generation_plan_hash(self)
        if self.plan_hash != expected_hash:
            raise ValueError("generation plan hash does not match its public fields")
        return self


class GenerationWorkUnit(PlanningModel):
    """Immutable specification for one future provider attempt unit."""

    unit_id: str = Field(min_length=1)
    stage: StageName
    selector: WorkUnitSelector
    sequence: int = Field(ge=1)
    generation_plan_hash: str = Field(min_length=1)
    dependency_hash: str = Field(min_length=1)
    unit_dependency_hash: str = Field(min_length=1)
    input_hash: str = Field(min_length=1)
    budget: StageBudget
    estimated_input_tokens: int = Field(ge=0)
    context_window_tokens: int = Field(ge=1)
    dialogue_timing_profile: DialogueTimingProfile | None
    dialogue_capacity_plan: DialogueCapacityPlan | None

    @model_validator(mode="after")
    def validate_dialogue_capacity_pair(self) -> "GenerationWorkUnit":
        has_profile = self.dialogue_timing_profile is not None
        has_capacity = self.dialogue_capacity_plan is not None
        if has_profile != has_capacity:
            raise ValueError(
                "dialogue timing profile and dialogue capacity plan must be set together"
            )
        if self.stage == StageName.SCENE_BEATS and not has_profile:
            raise ValueError("Scene Beats requires frozen dialogue capacity inputs")
        if self.stage != StageName.SCENE_BEATS and has_profile:
            raise ValueError("dialogue capacity only belongs to Scene Beats")
        return self


class StagePlan(PlanningModel):
    """Stage-local contract made only after its upstream inputs are available."""

    run_id: str = Field(min_length=1)
    stage: StageName
    generation_plan_hash: str = Field(min_length=1)
    dependency_hash: str = Field(min_length=1)
    scene_timing_allocation: SceneTimingAllocation | None
    dialogue_timing_profile: DialogueTimingProfile | None
    dialogue_capacity_plan: DialogueCapacityPlan | None

    # Storyboard has no dialogue-capacity planning of its own, but canonical
    # validation must still replay the policy that was frozen when this
    # downstream run was planned.  Keeping it stage-local makes a
    # Storyboard-only run reproducible without falsely claiming that a READY
    # Scene Beats revision was generated by this run.
    storyboard_dialogue_timing_profile: DialogueTimingProfile | None
    join_state_value_contract_version: str | None
    join_state_value_contract_hash: str | None
    edge_entry_state_contract_version: str | None
    edge_entry_state_contract_hash: str | None

    work_units: tuple[GenerationWorkUnit, ...]
    stage_plan_hash: str

    @model_validator(mode="after")
    def validate_units_and_hash(self) -> "StagePlan":
        if not self.work_units:
            raise ValueError("stage plans require at least one work unit")
        expected_sequences = list(range(1, len(self.work_units) + 1))
        if [unit.sequence for unit in self.work_units] != expected_sequences:
            raise ValueError(
                "stage-plan work units must be in contiguous sequence order"
            )
        if any(unit.stage != self.stage for unit in self.work_units):
            raise ValueError("stage-plan units must belong to the stage")
        if any(
            unit.generation_plan_hash != self.generation_plan_hash
            for unit in self.work_units
        ):
            raise ValueError("stage-plan units must reference the generation plan")
        if any(
            unit.dependency_hash != self.dependency_hash for unit in self.work_units
        ):
            raise ValueError("stage-plan units must share the dependency fingerprint")
        if len({unit.unit_id for unit in self.work_units}) != len(self.work_units):
            raise ValueError("stage-plan work-unit IDs must be unique")
        selectors = [
            (unit.selector.kind, unit.selector.stable_id) for unit in self.work_units
        ]
        if len(set(selectors)) != len(selectors):
            raise ValueError("stage-plan work-unit selectors must be unique")
        if self.stage == StageName.SCENE_BEATS and any(
            value is None
            for value in (
                self.scene_timing_allocation,
                self.dialogue_timing_profile,
                self.dialogue_capacity_plan,
                self.join_state_value_contract_version,
                self.join_state_value_contract_hash,
                self.edge_entry_state_contract_version,
                self.edge_entry_state_contract_hash,
            )
        ):
            raise ValueError(
                "Scene Beats requires its complete frozen timing and state contracts"
            )
        if (
            self.stage == StageName.STORYBOARD
            and self.storyboard_dialogue_timing_profile is None
        ):
            raise ValueError("Storyboard requires a frozen dialogue timing profile")
        has_dialogue_capacity_profile = self.dialogue_timing_profile is not None
        has_dialogue_capacity_plan = self.dialogue_capacity_plan is not None
        if has_dialogue_capacity_profile != has_dialogue_capacity_plan:
            raise ValueError(
                "dialogue timing profile and dialogue capacity plan must be set together"
            )
        if self.stage != StageName.SCENE_BEATS and has_dialogue_capacity_profile:
            raise ValueError("dialogue capacity only belongs to Scene Beats")
        if (
            self.stage != StageName.STORYBOARD
            and self.storyboard_dialogue_timing_profile is not None
        ):
            raise ValueError(
                "Storyboard dialogue timing provenance only belongs to Storyboard"
            )
        has_join_version = self.join_state_value_contract_version is not None
        has_join_hash = self.join_state_value_contract_hash is not None
        if has_join_version != has_join_hash:
            raise ValueError(
                "join state value contract version and hash must be set together"
            )
        if self.stage != StageName.SCENE_BEATS and has_join_version:
            raise ValueError("join state value contract only belongs to Scene Beats")
        if has_join_hash and len(self.join_state_value_contract_hash or "") != 64:
            raise ValueError(
                "join state value contract hash must be a SHA-256 hex digest"
            )
        has_edge_entry_version = self.edge_entry_state_contract_version is not None
        has_edge_entry_hash = self.edge_entry_state_contract_hash is not None
        if has_edge_entry_version != has_edge_entry_hash:
            raise ValueError(
                "edge entry state contract version and hash must be set together"
            )
        if self.stage != StageName.SCENE_BEATS and has_edge_entry_version:
            raise ValueError("edge entry state contract only belongs to Scene Beats")
        if has_edge_entry_hash and len(self.edge_entry_state_contract_hash or "") != 64:
            raise ValueError(
                "edge entry state contract hash must be a SHA-256 hex digest"
            )
        if has_dialogue_capacity_profile:
            if self.scene_timing_allocation is None:
                raise ValueError("dialogue capacity requires a scene timing allocation")
            assert self.dialogue_timing_profile is not None
            assert self.dialogue_capacity_plan is not None
            try:
                expected_capacity = plan_dialogue_capacity(
                    scene_timing_allocation=self.scene_timing_allocation,
                    dialogue_timing_profile=self.dialogue_timing_profile,
                    authoring_language=self.dialogue_capacity_plan.authoring_language,
                )
            except DialogueCapacityPlanningError as exc:
                raise ValueError(str(exc)) from exc
            if self.dialogue_capacity_plan != expected_capacity:
                raise ValueError(
                    "dialogue capacity plan does not match the frozen timing inputs"
                )
            if any(
                unit.dialogue_timing_profile != self.dialogue_timing_profile
                or unit.dialogue_capacity_plan != self.dialogue_capacity_plan
                for unit in self.work_units
            ):
                raise ValueError(
                    "Scene Beats work units must carry the StagePlan dialogue capacity inputs"
                )
        expected_hash = _stage_plan_hash(self)
        if self.stage_plan_hash != expected_hash:
            raise ValueError("stage plan hash does not match its public fields")
        return self


def content_hash(value: BaseModel | Mapping[str, Any] | Any) -> str:
    """Hash JSON-shaped canonical inputs without depending on Python object identity."""

    return sha256_text(canonical_json(_json_value(value)))


def assert_work_unit_input_contract(
    generation_plan: GenerationPlan,
    work_unit: GenerationWorkUnit,
) -> None:
    """Reject a persisted unit whose input hash no longer matches its plan.

    ``StagePlan`` verifies its aggregate hash, while this function exposes the
    unit-level derivation needed by the prompt compiler before it records a
    provider-facing trace.
    """

    expected_payload = {
        "generation_plan_hash": generation_plan.plan_hash,
        "stage": work_unit.stage.value,
        "selector": work_unit.selector.model_dump(mode="json"),
        "sequence": work_unit.sequence,
        "dependency_hash": work_unit.dependency_hash,
        "unit_dependency_hash": work_unit.unit_dependency_hash,
        "budget": work_unit.budget.model_dump(mode="json"),
        "estimated_input_tokens": work_unit.estimated_input_tokens,
        "context_window_tokens": work_unit.context_window_tokens,
    }
    if (
        work_unit.dialogue_timing_profile is not None
        and work_unit.dialogue_capacity_plan is not None
    ):
        expected_payload["dialogue_timing_profile"] = (
            work_unit.dialogue_timing_profile.model_dump(mode="json", by_alias=False)
        )
        expected_payload["dialogue_capacity_plan"] = (
            work_unit.dialogue_capacity_plan.model_dump(mode="json", by_alias=False)
        )
    expected_hash = sha256_text(canonical_json(expected_payload))
    if work_unit.input_hash != expected_hash:
        raise PlanningError(
            f"work-unit input hash does not match its frozen public fields: {work_unit.unit_id}"
        )
    expected_id = (
        f"unit-{work_unit.stage.value}-{work_unit.sequence:04d}-{expected_hash[:16]}"
    )
    if work_unit.unit_id != expected_id:
        raise PlanningError("work-unit ID does not match its frozen input hash")


def _json_value(value: BaseModel | Mapping[str, Any] | Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    return value


def _generation_plan_hash(plan: GenerationPlan) -> str:
    unsigned = plan.model_dump(
        mode="json",
        by_alias=False,
        exclude={"plan_hash"},
    )
    return sha256_text(canonical_json(unsigned))


def _stage_plan_hash(plan: StagePlan) -> str:
    unsigned = plan.model_dump(
        mode="json",
        by_alias=False,
        exclude={"stage_plan_hash"},
        exclude_none=True,
    )
    return sha256_text(canonical_json(unsigned))
