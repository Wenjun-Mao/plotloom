"""Deterministic, domain-aware planning for bounded generation work.

This module deliberately has no repository, provider, or orchestration imports.
It defines the immutable planning boundary used *before* those layers allocate
durable records.  In particular, a run plan cannot fabricate selectors for a
stage whose upstream canonical objects do not exist yet.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain import (
    DialogueTimingProfile,
    ProjectBrief,
    STAGE_ORDER,
    SceneBeatPlanV2,
    StageName,
    StoryGraphV2,
    default_dialogue_timing_profile,
)
from ..join_state_values import JoinStateValueContractError, compile_join_state_value_contract
from .dialogue_capacity import (
    DialogueCapacityPlan,
    DialogueCapacityPlanningError,
    plan_dialogue_capacity,
)
from .prompts import canonical_json, sha256_text
from .scene_timing_allocation import (
    SceneTimingAllocation,
    SceneTimingAllocationError,
    plan_scene_timing_allocation,
)


# ``p0.5`` adds an explicit Storyboard timing-profile provenance boundary.
# A Storyboard-only run may validly consume a READY Scene Beats revision that
# was produced by another run (or authored directly).  The canonical revision
# does not carry generator-only policy metadata, so its downstream StagePlan
# owns an independently frozen profile rather than looking for a same-run
# Scene Beats plan at seal/install time.
PLANNING_POLICY_VERSION = "m1.5-p0.5"


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
    planning_policy_version: str = Field(default=PLANNING_POLICY_VERSION, min_length=1)
    planning_policy_hash: str
    provider_profile_hash: str = Field(min_length=1)
    story_graph_topology_hash: str | None = None
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
            raise ValueError("stage budgets must exist for exactly the requested stages")
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
    # Optional only for historical work-unit records. New Scene Beats units
    # carry their exact capacity inputs, avoiding any process-global fallback
    # when their bounded context is reconstructed.
    dialogue_timing_profile: DialogueTimingProfile | None = None
    dialogue_capacity_plan: DialogueCapacityPlan | None = None

    @model_validator(mode="after")
    def validate_dialogue_capacity_pair(self) -> "GenerationWorkUnit":
        has_profile = self.dialogue_timing_profile is not None
        has_capacity = self.dialogue_capacity_plan is not None
        if has_profile != has_capacity:
            raise ValueError(
                "dialogue timing profile and dialogue capacity plan must be set together"
            )
        if self.stage != StageName.SCENE_BEATS and has_profile:
            raise ValueError("dialogue capacity only belongs to Scene Beats")
        return self

class StagePlan(PlanningModel):
    """Stage-local contract made only after its upstream inputs are available."""

    run_id: str = Field(min_length=1)
    stage: StageName
    generation_plan_hash: str = Field(min_length=1)
    dependency_hash: str = Field(min_length=1)
    scene_timing_allocation: SceneTimingAllocation | None = None
    # Both fields are optional only so terminal historical StagePlans retain
    # their original serialized shape and hash.  Newly planned Scene Beats
    # stages always set them together below.
    dialogue_timing_profile: DialogueTimingProfile | None = None
    dialogue_capacity_plan: DialogueCapacityPlan | None = None
    # Storyboard has no dialogue-capacity planning of its own, but canonical
    # validation must still replay the policy that was frozen when this
    # downstream run was planned.  Keeping it stage-local makes a
    # Storyboard-only run reproducible without falsely claiming that a READY
    # Scene Beats revision was generated by this run.
    storyboard_dialogue_timing_profile: DialogueTimingProfile | None = None
    # Optional only for immutable historical plans.  New Scene Beats plans
    # freeze the exact join-entry value contract which their unit contexts
    # consume, so startup recovery never rebuilds them under new semantics.
    join_state_value_contract_version: str | None = None
    join_state_value_contract_hash: str | None = None
    work_units: tuple[GenerationWorkUnit, ...]
    stage_plan_hash: str

    @model_validator(mode="after")
    def validate_units_and_hash(self) -> "StagePlan":
        if not self.work_units:
            raise ValueError("stage plans require at least one work unit")
        expected_sequences = list(range(1, len(self.work_units) + 1))
        if [unit.sequence for unit in self.work_units] != expected_sequences:
            raise ValueError("stage-plan work units must be in contiguous sequence order")
        if any(unit.stage != self.stage for unit in self.work_units):
            raise ValueError("stage-plan units must belong to the stage")
        if any(unit.generation_plan_hash != self.generation_plan_hash for unit in self.work_units):
            raise ValueError("stage-plan units must reference the generation plan")
        if any(unit.dependency_hash != self.dependency_hash for unit in self.work_units):
            raise ValueError("stage-plan units must share the dependency fingerprint")
        if len({unit.unit_id for unit in self.work_units}) != len(self.work_units):
            raise ValueError("stage-plan work-unit IDs must be unique")
        selectors = [
            (unit.selector.kind, unit.selector.stable_id)
            for unit in self.work_units
        ]
        if len(set(selectors)) != len(selectors):
            raise ValueError("stage-plan work-unit selectors must be unique")
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
            raise ValueError("Storyboard dialogue timing provenance only belongs to Storyboard")
        has_join_version = self.join_state_value_contract_version is not None
        has_join_hash = self.join_state_value_contract_hash is not None
        if has_join_version != has_join_hash:
            raise ValueError(
                "join state value contract version and hash must be set together"
            )
        if self.stage != StageName.SCENE_BEATS and has_join_version:
            raise ValueError("join state value contract only belongs to Scene Beats")
        if has_join_hash and len(self.join_state_value_contract_hash or "") != 64:
            raise ValueError("join state value contract hash must be a SHA-256 hex digest")
        if has_dialogue_capacity_profile:
            if self.scene_timing_allocation is None:
                raise ValueError("dialogue capacity requires a scene timing allocation")
            assert self.dialogue_timing_profile is not None
            assert self.dialogue_capacity_plan is not None
            try:
                expected_capacity = plan_dialogue_capacity(
                    scene_timing_allocation=self.scene_timing_allocation,
                    dialogue_timing_profile=self.dialogue_timing_profile,
                    policy_version=self.dialogue_capacity_plan.policy_version,
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


def create_generation_plan(
    *,
    run_id: str,
    requested_stages: tuple[StageName, ...] | list[StageName],
    provider_profile_hash: str,
    story_graph_topology_hash: str | None = None,
    canonical_snapshot: BaseModel | Mapping[str, Any] | None = None,
    canonical_snapshot_hash: str | None = None,
    canonical_snapshot_bytes: int | None = None,
    instructions: str | None = None,
    canonical_inputs: Mapping[StageName, BaseModel | Mapping[str, Any]] | None = None,
    stage_budgets: Mapping[StageName, StageBudget] | None = None,
    provider_output_token_ceiling: int | None = None,
    max_concurrency: int = 1,
    context_window_tokens: int = 32_768,
    prompt_overhead_bytes: int = 16_384,
    planning_policy_version: str = PLANNING_POLICY_VERSION,
) -> GenerationPlan:
    """Freeze enqueue-time bounds without creating future entity selectors."""

    requested = tuple(requested_stages)
    _validate_requested_range(requested)
    if provider_output_token_ceiling is not None and (
        isinstance(provider_output_token_ceiling, bool)
        or provider_output_token_ceiling < 1
    ):
        raise PlanningError("provider_output_token_ceiling must be at least 1")
    snapshot_json: str | None = None
    if canonical_snapshot is not None:
        snapshot_json = canonical_json(_json_value(canonical_snapshot))
        computed_snapshot_hash = sha256_text(snapshot_json)
        computed_snapshot_bytes = len(snapshot_json.encode("utf-8"))
        if (
            canonical_snapshot_hash is not None
            and canonical_snapshot_hash != computed_snapshot_hash
        ):
            raise PlanningError("canonical_snapshot_hash does not match canonical_snapshot")
        if (
            canonical_snapshot_bytes is not None
            and canonical_snapshot_bytes != computed_snapshot_bytes
        ):
            raise PlanningError("canonical_snapshot_bytes does not match canonical_snapshot")
    if canonical_snapshot_hash is None:
        if snapshot_json is None:
            raise PlanningError(
                "canonical_snapshot or canonical_snapshot_hash is required when enqueueing"
            )
        canonical_snapshot_hash = sha256_text(snapshot_json)
    if canonical_snapshot_bytes is None:
        if snapshot_json is None:
            raise PlanningError(
                "canonical_snapshot_bytes is required when only a snapshot hash is supplied"
            )
        canonical_snapshot_bytes = len(snapshot_json.encode("utf-8"))
    if canonical_snapshot_bytes < 0:
        raise PlanningError("canonical_snapshot_bytes cannot be negative")
    instructions_json = instructions or ""
    instructions_hash = sha256_text(instructions_json)
    instructions_bytes = len(instructions_json.encode("utf-8"))
    run_request_hash = sha256_text(
        canonical_json(
            {
                "canonical_snapshot_hash": canonical_snapshot_hash,
                "instructions_hash": instructions_hash,
            }
        )
    )
    existing = canonical_inputs or {}
    allowed_inputs = set(STAGE_ORDER[: STAGE_ORDER.index(requested[0])])
    unexpected = set(existing) - allowed_inputs
    if unexpected:
        names = ", ".join(stage.value for stage in sorted(unexpected, key=STAGE_ORDER.index))
        raise PlanningError(
            "run-level plans may freeze only canonical inputs that precede the "
            f"requested range; got {names}"
        )
    supplied_budgets = stage_budgets or {}
    unknown_budgets = set(supplied_budgets) - set(requested)
    if unknown_budgets:
        names = ", ".join(stage.value for stage in sorted(unknown_budgets, key=STAGE_ORDER.index))
        raise PlanningError(f"budgets were supplied for unrequested stages: {names}")
    budgets: dict[StageName, StageBudget] = {}
    for stage in requested:
        requested_budget = supplied_budgets.get(stage, DEFAULT_STAGE_BUDGETS[stage])
        if provider_output_token_ceiling is not None:
            requested_budget = requested_budget.model_copy(
                update={
                    "max_output_tokens": min(
                        requested_budget.max_output_tokens,
                        provider_output_token_ceiling,
                    )
                }
            )
        budgets[stage] = requested_budget
        if requested_budget.max_output_tokens >= context_window_tokens:
            raise PlanningError(
                f"{stage.value} max_output_tokens must leave room for provider input",
                code="planning.output_budget_exceeds_context",
                stage=stage,
            )
    input_hashes = {
        stage: content_hash(value)
        for stage, value in sorted(existing.items(), key=lambda item: STAGE_ORDER.index(item[0]))
    }
    policy_hash = sha256_text(planning_policy_version)
    unsigned = {
        "run_id": run_id,
        "requested_stages": [stage.value for stage in requested],
        "planning_policy_version": planning_policy_version,
        "planning_policy_hash": policy_hash,
        "provider_profile_hash": provider_profile_hash,
        "canonical_snapshot_hash": canonical_snapshot_hash,
        "canonical_snapshot_bytes": canonical_snapshot_bytes,
        "instructions_hash": instructions_hash,
        "instructions_bytes": instructions_bytes,
        "run_request_hash": run_request_hash,
        "canonical_input_hashes": {stage.value: value for stage, value in input_hashes.items()},
        "stage_budgets": {
            stage.value: budget.model_dump(mode="json") for stage, budget in budgets.items()
        },
        "max_concurrency": max_concurrency,
        "context_window_tokens": context_window_tokens,
        "prompt_overhead_bytes": prompt_overhead_bytes,
    }
    if story_graph_topology_hash is not None:
        unsigned["story_graph_topology_hash"] = story_graph_topology_hash
    return GenerationPlan(
        run_id=run_id,
        requested_stages=requested,
        planning_policy_version=planning_policy_version,
        planning_policy_hash=policy_hash,
        provider_profile_hash=provider_profile_hash,
        story_graph_topology_hash=story_graph_topology_hash,
        canonical_snapshot_hash=canonical_snapshot_hash,
        canonical_snapshot_bytes=canonical_snapshot_bytes,
        instructions_hash=instructions_hash,
        instructions_bytes=instructions_bytes,
        run_request_hash=run_request_hash,
        canonical_input_hashes=input_hashes,
        stage_budgets=budgets,
        max_concurrency=max_concurrency,
        context_window_tokens=context_window_tokens,
        prompt_overhead_bytes=prompt_overhead_bytes,
        plan_hash=sha256_text(canonical_json(unsigned)),
    )


def plan_stage(
    generation_plan: GenerationPlan,
    *,
    stage: StageName,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    brief: ProjectBrief | None = None,
    scene_beats_dialogue_timing_profile: DialogueTimingProfile | None = None,
    storyboard_dialogue_timing_profile: DialogueTimingProfile | None = None,
) -> StagePlan:
    """Create a stage plan once all selectors for that stage are canonical.

    The resolver makes the dependency fingerprint from exactly the input objects
    the stage prompt needs.  It refuses to derive Scene Beats selectors without
    a Story Graph and Storyboard selectors without a Scene Beat Plan.
    """

    if stage not in generation_plan.requested_stages:
        raise PlanningError(
            f"stage {stage.value} is not requested by this generation plan",
            code="planning.stage_not_requested",
            stage=stage,
        )
    required = _required_dependencies(stage)
    missing = [dependency.value for dependency in required if dependency not in dependencies]
    if missing:
        raise PlanningError(
            f"cannot plan {stage.value} before sealed/canonical dependencies exist: "
            f"{', '.join(missing)}",
            code="planning.dependencies_unavailable",
            stage=stage,
        )
    if (
        stage == StageName.SCENE_BEATS
        and storyboard_dialogue_timing_profile is not None
    ) or (
        stage == StageName.STORYBOARD
        and scene_beats_dialogue_timing_profile is not None
    ):
        raise PlanningError(
            "dialogue timing provenance was supplied to the wrong owning stage",
            code="planning.dialogue_timing_provenance_invalid",
            stage=stage,
        )
    dependency_values = {
        dependency: dependencies[dependency]
        for dependency in required
    }
    scene_timing_allocation: SceneTimingAllocation | None = None
    dialogue_timing_profile: DialogueTimingProfile | None = None
    dialogue_capacity_plan: DialogueCapacityPlan | None = None
    join_state_value_contract_version: str | None = None
    join_state_value_contract_hash: str | None = None
    if stage == StageName.SCENE_BEATS:
        graph = dependency_values.get(StageName.STORY_GRAPH)
        if not isinstance(graph, StoryGraphV2):
            raise PlanningError(
                "scene_beats timing allocation requires a parsed StoryGraph",
                code="planning.scene_timing_graph_unavailable",
                stage=stage,
            )
        if brief is None:
            raise PlanningError(
                "scene_beats timing allocation requires the frozen ProjectBrief",
                code="planning.scene_timing_brief_unavailable",
                stage=stage,
            )
        try:
            scene_timing_allocation = plan_scene_timing_allocation(
                graph=graph,
                brief=brief,
            )
        except SceneTimingAllocationError as exc:
            raise PlanningError(str(exc), code=exc.code, stage=stage) from exc
        try:
            join_state_values = compile_join_state_value_contract(graph)
        except JoinStateValueContractError as exc:
            raise PlanningError(
                "sealed Story Graph cannot produce an exact join-state value contract",
                code="planning.join_state_value_contract_unresolvable",
                stage=stage,
            ) from exc
        join_state_value_contract_version = join_state_values.version
        join_state_value_contract_hash = join_state_values.contract_hash
        dialogue_timing_profile = (
            scene_beats_dialogue_timing_profile
            if scene_beats_dialogue_timing_profile is not None
            else default_dialogue_timing_profile()
        )
        try:
            dialogue_capacity_plan = plan_dialogue_capacity(
                scene_timing_allocation=scene_timing_allocation,
                dialogue_timing_profile=dialogue_timing_profile,
                authoring_language=brief.language,
            )
        except DialogueCapacityPlanningError as exc:
            raise PlanningError(str(exc), code=exc.code, stage=stage) from exc
    elif stage == StageName.STORYBOARD:
        # The current canonical Scene Beats payload contains cue estimates but
        # intentionally no generator-policy provenance.  Freeze the explicit
        # profile in the Storyboard StagePlan now; never recover it later from
        # a mutable process default or a possibly unrelated historical run.
        storyboard_dialogue_timing_profile = (
            storyboard_dialogue_timing_profile
            if storyboard_dialogue_timing_profile is not None
            else default_dialogue_timing_profile()
        )
    elif (
        scene_beats_dialogue_timing_profile is not None
        or storyboard_dialogue_timing_profile is not None
    ):
        raise PlanningError(
            "dialogue timing provenance may only be supplied to its owning stage",
            code="planning.dialogue_timing_provenance_invalid",
            stage=stage,
        )
    dependency_payload = {
        # A StagePlan must retain the run request boundary even when this stage
        # has no upstream canonical object (notably Story Bible).
        "run_request_hash": generation_plan.run_request_hash,
        "enqueue_canonical_input_hashes": {
            dependency.value: value
            for dependency, value in generation_plan.canonical_input_hashes.items()
        },
        "dependencies": {
            dependency.value: _json_value(value)
            for dependency, value in dependency_values.items()
        },
    }
    if scene_timing_allocation is not None:
        dependency_payload["scene_timing_allocation"] = (
            scene_timing_allocation.model_dump(mode="json", by_alias=True)
        )
    if dialogue_timing_profile is not None and dialogue_capacity_plan is not None:
        dependency_payload["dialogue_timing_profile"] = dialogue_timing_profile.model_dump(
            mode="json", by_alias=True
        )
        dependency_payload["dialogue_capacity_plan"] = dialogue_capacity_plan.model_dump(
            mode="json", by_alias=True
        )
    if storyboard_dialogue_timing_profile is not None:
        dependency_payload["storyboard_dialogue_timing_profile"] = (
            storyboard_dialogue_timing_profile.model_dump(mode="json", by_alias=True)
        )
    if (
        join_state_value_contract_version is not None
        and join_state_value_contract_hash is not None
    ):
        dependency_payload["join_state_value_contract"] = {
            "version": join_state_value_contract_version,
            "hash": join_state_value_contract_hash,
        }
    dependency_json = canonical_json(dependency_payload)
    dependency_hash = sha256_text(dependency_json)
    selectors = _selectors_for_stage(stage, dependency_values)
    budget = generation_plan.stage_budgets[stage]
    if len(selectors) > budget.max_units:
        raise PlanningError(
            f"{stage.value} requires {len(selectors)} work units, exceeding its "
            f"max_units budget of {budget.max_units}",
            code="planning.max_units_exceeded",
            stage=stage,
        )
    if len(selectors) > budget.max_aggregate_items:
        raise PlanningError(
            f"{stage.value} requires {len(selectors)} aggregate selectors, exceeding "
            f"its max_aggregate_items budget of {budget.max_aggregate_items}",
            code="planning.max_aggregate_items_exceeded",
            stage=stage,
        )

    work_units = tuple(
        _work_unit(
            generation_plan=generation_plan,
            stage=stage,
            selector=selector,
            sequence=index,
            dependency_hash=dependency_hash,
            budget=budget,
            dialogue_timing_profile=dialogue_timing_profile,
            dialogue_capacity_plan=dialogue_capacity_plan,
            unit_dependency_payload=_unit_dependency_payload(
                stage,
                selector,
                dependency_values,
                scene_timing_allocation=scene_timing_allocation,
                dialogue_timing_profile=dialogue_timing_profile,
                dialogue_capacity_plan=dialogue_capacity_plan,
            ),
        )
        for index, selector in enumerate(selectors, start=1)
    )
    unsigned = {
        "run_id": generation_plan.run_id,
        "stage": stage.value,
        "generation_plan_hash": generation_plan.plan_hash,
        "dependency_hash": dependency_hash,
        "work_units": [
            unit.model_dump(mode="json", exclude_none=True) for unit in work_units
        ],
    }
    if scene_timing_allocation is not None:
        unsigned["scene_timing_allocation"] = scene_timing_allocation.model_dump(
            mode="json", by_alias=False
        )
    if dialogue_timing_profile is not None and dialogue_capacity_plan is not None:
        unsigned["dialogue_timing_profile"] = dialogue_timing_profile.model_dump(
            mode="json", by_alias=False
        )
        unsigned["dialogue_capacity_plan"] = dialogue_capacity_plan.model_dump(
            mode="json", by_alias=False
        )
    if storyboard_dialogue_timing_profile is not None:
        unsigned["storyboard_dialogue_timing_profile"] = (
            storyboard_dialogue_timing_profile.model_dump(mode="json", by_alias=False)
        )
    if (
        join_state_value_contract_version is not None
        and join_state_value_contract_hash is not None
    ):
        unsigned["join_state_value_contract_version"] = (
            join_state_value_contract_version
        )
        unsigned["join_state_value_contract_hash"] = join_state_value_contract_hash
    return StagePlan(
        run_id=generation_plan.run_id,
        stage=stage,
        generation_plan_hash=generation_plan.plan_hash,
        dependency_hash=dependency_hash,
        scene_timing_allocation=scene_timing_allocation,
        dialogue_timing_profile=dialogue_timing_profile,
        dialogue_capacity_plan=dialogue_capacity_plan,
        storyboard_dialogue_timing_profile=storyboard_dialogue_timing_profile,
        join_state_value_contract_version=join_state_value_contract_version,
        join_state_value_contract_hash=join_state_value_contract_hash,
        work_units=work_units,
        stage_plan_hash=sha256_text(canonical_json(unsigned)),
    )


def content_hash(value: BaseModel | Mapping[str, Any] | Any) -> str:
    """Hash JSON-shaped canonical inputs without depending on Python object identity."""

    return sha256_text(canonical_json(_json_value(value)))


def work_unit_context(
    work_unit: GenerationWorkUnit,
    *,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    scene_timing_allocation: SceneTimingAllocation | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
    dialogue_capacity_plan: DialogueCapacityPlan | None = None,
) -> dict[str, Any]:
    """Reconstruct and verify the canonical context frozen for one unit.

    Planning deliberately stores hashes rather than duplicating potentially
    large canonical values in every work-unit record.  The prompt compiler is
    the only consumer that needs the values again.  Recomputing the exact
    selector-scoped payload here and checking its hash prevents a caller from
    accidentally rendering a work unit with a newer full graph or scene plan.
    """

    required = _required_dependencies(work_unit.stage)
    missing = [stage.value for stage in required if stage not in dependencies]
    if missing:
        raise PlanningError(
            f"cannot render {work_unit.unit_id} without dependencies: {', '.join(missing)}"
        )
    scoped_dependencies = {stage: dependencies[stage] for stage in required}
    if dialogue_timing_profile is None:
        dialogue_timing_profile = work_unit.dialogue_timing_profile
    elif (
        work_unit.dialogue_timing_profile is not None
        and dialogue_timing_profile != work_unit.dialogue_timing_profile
    ):
        raise PlanningError(
            "supplied dialogue timing profile does not match the frozen work unit",
            code="planning.dialogue_capacity_mismatch",
            stage=work_unit.stage,
        )
    if dialogue_capacity_plan is None:
        dialogue_capacity_plan = work_unit.dialogue_capacity_plan
    elif (
        work_unit.dialogue_capacity_plan is not None
        and dialogue_capacity_plan != work_unit.dialogue_capacity_plan
    ):
        raise PlanningError(
            "supplied dialogue capacity plan does not match the frozen work unit",
            code="planning.dialogue_capacity_mismatch",
            stage=work_unit.stage,
        )
    context = _unit_dependency_payload(
        work_unit.stage,
        work_unit.selector,
        scoped_dependencies,
        scene_timing_allocation=scene_timing_allocation,
        dialogue_timing_profile=dialogue_timing_profile,
        dialogue_capacity_plan=dialogue_capacity_plan,
    )
    actual_hash = content_hash(context)
    if actual_hash != work_unit.unit_dependency_hash:
        raise PlanningError(
            f"canonical context for {work_unit.unit_id} no longer matches its frozen "
            "unit_dependency_hash"
        )
    return context


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
        expected_payload["dialogue_timing_profile"] = work_unit.dialogue_timing_profile.model_dump(
            mode="json", by_alias=False
        )
        expected_payload["dialogue_capacity_plan"] = work_unit.dialogue_capacity_plan.model_dump(
            mode="json", by_alias=False
        )
    expected_hash = sha256_text(canonical_json(expected_payload))
    if work_unit.input_hash != expected_hash:
        raise PlanningError(
            f"work-unit input hash does not match its frozen public fields: {work_unit.unit_id}"
        )
    expected_id = f"unit-{work_unit.stage.value}-{work_unit.sequence:04d}-{expected_hash[:16]}"
    if work_unit.unit_id != expected_id:
        raise PlanningError("work-unit ID does not match its frozen input hash")


def _json_value(value: BaseModel | Mapping[str, Any] | Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    return value


def _validate_requested_range(requested: tuple[StageName, ...]) -> None:
    if not requested:
        raise PlanningError("generation plans require at least one requested stage")
    if len(requested) != len(set(requested)):
        raise PlanningError("requested stages must not contain duplicates")
    first = STAGE_ORDER.index(requested[0])
    expected = STAGE_ORDER[first : first + len(requested)]
    if requested != expected:
        raise PlanningError("requested stages must form a contiguous canonical range")


def _required_dependencies(stage: StageName) -> tuple[StageName, ...]:
    return {
        StageName.STORY_BIBLE: (),
        StageName.STORY_GRAPH: (StageName.STORY_BIBLE,),
        StageName.SCENE_BEATS: (StageName.STORY_BIBLE, StageName.STORY_GRAPH),
        StageName.STORYBOARD: (
            StageName.STORY_BIBLE,
            StageName.STORY_GRAPH,
            StageName.SCENE_BEATS,
        ),
    }[stage]


def _selectors_for_stage(
    stage: StageName,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
) -> tuple[WorkUnitSelector, ...]:
    if stage in {StageName.STORY_BIBLE, StageName.STORY_GRAPH}:
        return (WorkUnitSelector(kind=WorkUnitSelectorKind.WHOLE_STAGE, stable_id=stage.value),)
    if stage == StageName.SCENE_BEATS:
        graph = dependencies[StageName.STORY_GRAPH]
        if not isinstance(graph, StoryGraphV2):
            raise PlanningError("scene_beats planning requires a parsed StoryGraph")
        return tuple(
            WorkUnitSelector(kind=WorkUnitSelectorKind.STORY_NODE, stable_id=node.id)
            for node in graph.nodes
        )
    scene_beats = dependencies[StageName.SCENE_BEATS]
    graph = dependencies[StageName.STORY_GRAPH]
    if not isinstance(scene_beats, SceneBeatPlanV2) or not isinstance(graph, StoryGraphV2):
        raise PlanningError("storyboard planning requires parsed StoryGraph and SceneBeatPlan")
    node_position = {node.id: position for position, node in enumerate(graph.nodes)}
    unknown_nodes = sorted(
        {scene.story_node_id for scene in scene_beats.scenes} - set(node_position)
    )
    if unknown_nodes:
        raise PlanningError(
            "storyboard planning found scenes that do not belong to the sealed Story Graph: "
            + ", ".join(unknown_nodes)
        )
    # Preserve the authored/sealed order of sibling scenes. Canonical UUIDv5
    # identifiers are opaque identity, not sortable sequence metadata.
    ordered_scenes = [
        scene
        for _, scene in sorted(
            enumerate(scene_beats.scenes),
            key=lambda item: (node_position[item[1].story_node_id], item[1].order, item[0]),
        )
    ]
    if not ordered_scenes:
        raise PlanningError("storyboard planning requires at least one dramatic scene")
    return tuple(
        WorkUnitSelector(kind=WorkUnitSelectorKind.DRAMATIC_SCENE, stable_id=scene.id)
        for scene in ordered_scenes
    )


def _unit_dependency_payload(
    stage: StageName,
    selector: WorkUnitSelector,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    *,
    scene_timing_allocation: SceneTimingAllocation | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
    dialogue_capacity_plan: DialogueCapacityPlan | None = None,
) -> dict[str, Any]:
    """Return the bounded canonical context selected for one provider unit.

    The current whole-stage prompt templates are deliberately not changed by
    this pure domain slice.  Their later work-unit renderer must consume this
    exact scope instead of serializing a full downstream aggregate for every
    shard; otherwise shard planning would only create the appearance of a
    context bound.
    """

    if stage == StageName.STORY_BIBLE:
        return {}
    bible = dependencies[StageName.STORY_BIBLE]
    if stage == StageName.STORY_GRAPH:
        return {"story_bible": _json_value(bible)}
    graph = dependencies[StageName.STORY_GRAPH]
    if not isinstance(graph, StoryGraphV2):
        raise PlanningError(f"{stage.value} requires a parsed StoryGraph")
    if stage == StageName.SCENE_BEATS:
        if scene_timing_allocation is None:
            raise PlanningError(
                "scene_beats work units require a frozen timing allocation",
                code="planning.scene_timing_allocation_unavailable",
                stage=stage,
            )
        if (dialogue_timing_profile is None) != (dialogue_capacity_plan is None):
            raise PlanningError(
                "scene_beats work units require dialogue profile and capacity together",
                code="planning.dialogue_capacity_unavailable",
                stage=stage,
            )
        node = next((node for node in graph.nodes if node.id == selector.stable_id), None)
        if node is None:
            raise PlanningError(f"unknown Story Graph node selector {selector.stable_id}")
        try:
            join_state_values = compile_join_state_value_contract(graph)
        except JoinStateValueContractError as error:
            raise PlanningError(
                "sealed Story Graph cannot produce an exact join-state value contract",
                code="planning.join_state_value_contract_unresolvable",
                stage=stage,
            ) from error
        context = {
            "story_bible": _json_value(bible),
            "story_node": _json_value(node),
            "incident_edges": [
                _json_value(edge)
                for edge in graph.edges
                if selector.stable_id in {edge.source_node_id, edge.target_node_id}
            ],
            "join_contracts": [
                _json_value(contract)
                for contract in graph.join_contracts
                if contract.join_node_id == selector.stable_id
                or selector.stable_id in contract.incoming_node_ids
            ],
            "join_state_value_requirements": (
                join_state_values.requirements_for_node(selector.stable_id)
            ),
            "scene_timing_allocation": {
                "allocationVersion": scene_timing_allocation.allocation_version,
                "allocationHash": scene_timing_allocation.allocation_hash,
                "nodeId": selector.stable_id,
                "durationBudgetUnits": scene_timing_allocation.node_duration_budget(
                    selector.stable_id
                ),
            },
        }
        if dialogue_timing_profile is not None and dialogue_capacity_plan is not None:
            guidance = dialogue_capacity_plan.guidance_for(selector.stable_id)
            context["dialogue_timing_profile"] = dialogue_timing_profile.model_dump(
                mode="json", by_alias=True
            )
            context["dialogue_capacity_guidance"] = {
                "policyVersion": dialogue_capacity_plan.policy_version,
                "capacityPlanHash": dialogue_capacity_plan.capacity_plan_hash,
                "dialogueTimingProfileVersion": dialogue_capacity_plan.dialogue_timing_profile_version,
                "dialogueTimingProfileHash": dialogue_capacity_plan.dialogue_timing_profile_hash,
                "nodeGuidance": guidance.model_dump(mode="json", by_alias=True),
            }
        return context
    scene_beats = dependencies[StageName.SCENE_BEATS]
    if not isinstance(scene_beats, SceneBeatPlanV2):
        raise PlanningError("storyboard requires a parsed SceneBeatPlan")
    scene = next((scene for scene in scene_beats.scenes if scene.id == selector.stable_id), None)
    if scene is None:
        raise PlanningError(f"unknown dramatic-scene selector {selector.stable_id}")
    node = next((node for node in graph.nodes if node.id == scene.story_node_id), None)
    if node is None:
        raise PlanningError(f"scene {scene.id} references unknown Story Graph node")
    return {
        "story_bible": _json_value(bible),
        "story_node": _json_value(node),
        "dramatic_scene": _json_value(scene),
        "beats": [
            _json_value(beat)
            for beat in scene_beats.beats
            if beat.scene_id == scene.id
        ],
        "dialogue_cues": [
            _json_value(cue)
            for cue in scene_beats.dialogue_cues
            if cue.beat_id in set(scene.beat_ids)
        ],
    }


def _work_unit(
    *,
    generation_plan: GenerationPlan,
    stage: StageName,
    selector: WorkUnitSelector,
    sequence: int,
    dependency_hash: str,
    budget: StageBudget,
    unit_dependency_payload: Mapping[str, Any],
    dialogue_timing_profile: DialogueTimingProfile | None = None,
    dialogue_capacity_plan: DialogueCapacityPlan | None = None,
) -> GenerationWorkUnit:
    unit_dependency_json = canonical_json(unit_dependency_payload)
    unit_dependency_hash = sha256_text(unit_dependency_json)
    # This portable estimate is a bounded byte upper bound for memory and trace
    # purposes, not a tokenizer result. Tokenization is provider/model-specific,
    # so comparing it to a token context window would create deterministic false
    # rejections for CJK prompts. The provider owns the exact context check; the
    # planner only rejects the exact impossibility where output alone consumes
    # the entire declared window (in ``create_generation_plan`` above).
    estimated_input_tokens = (
        generation_plan.instructions_bytes
        + len(unit_dependency_json.encode("utf-8"))
        + generation_plan.prompt_overhead_bytes
    )
    if estimated_input_tokens > budget.max_input_bytes:
        raise PlanningError(
            f"{stage.value} unit {selector.stable_id} conservative input estimate "
            f"is {estimated_input_tokens} bytes, exceeding its max_input_bytes budget "
            f"of {budget.max_input_bytes}",
            code="planning.max_input_bytes_exceeded",
            stage=stage,
        )
    input_payload = {
        "generation_plan_hash": generation_plan.plan_hash,
        "stage": stage.value,
        "selector": selector.model_dump(mode="json"),
        "sequence": sequence,
        "dependency_hash": dependency_hash,
        "unit_dependency_hash": unit_dependency_hash,
        "budget": budget.model_dump(mode="json"),
        "estimated_input_tokens": estimated_input_tokens,
        "context_window_tokens": generation_plan.context_window_tokens,
    }
    if dialogue_timing_profile is not None and dialogue_capacity_plan is not None:
        input_payload["dialogue_timing_profile"] = dialogue_timing_profile.model_dump(
            mode="json", by_alias=False
        )
        input_payload["dialogue_capacity_plan"] = dialogue_capacity_plan.model_dump(
            mode="json", by_alias=False
        )
    input_hash = sha256_text(canonical_json(input_payload))
    unit_id = f"unit-{stage.value}-{sequence:04d}-{input_hash[:16]}"
    return GenerationWorkUnit(
        unit_id=unit_id,
        stage=stage,
        selector=selector,
        sequence=sequence,
        generation_plan_hash=generation_plan.plan_hash,
        dependency_hash=dependency_hash,
        unit_dependency_hash=unit_dependency_hash,
        input_hash=input_hash,
        budget=budget,
        estimated_input_tokens=estimated_input_tokens,
        context_window_tokens=generation_plan.context_window_tokens,
        dialogue_timing_profile=dialogue_timing_profile,
        dialogue_capacity_plan=dialogue_capacity_plan,
    )


def _generation_plan_hash(plan: GenerationPlan) -> str:
    unsigned = plan.model_dump(
        mode="json",
        by_alias=False,
        exclude={"plan_hash"},
    )
    # Historical M1 plans predate deterministic topologies.  Excluding the
    # absent field retains their byte-for-byte hash contract while every M1.5
    # graph-generating plan includes the non-null topology hash.
    if unsigned.get("story_graph_topology_hash") is None:
        unsigned.pop("story_graph_topology_hash", None)
    return sha256_text(canonical_json(unsigned))


def _stage_plan_hash(plan: StagePlan) -> str:
    unsigned = plan.model_dump(
        mode="json",
        by_alias=False,
        exclude={"stage_plan_hash"},
        exclude_none=True,
    )
    return sha256_text(canonical_json(unsigned))
