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
    STAGE_ORDER,
    SceneBeatPlan,
    StageName,
    StoryGraph,
)
from .prompts import canonical_json, sha256_text


PLANNING_POLICY_VERSION = "m1-p0.1"


class PlanningError(ValueError):
    """The requested scope cannot be turned into a bounded deterministic plan."""


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

    @model_validator(mode="after")
    def validate_context_budget(self) -> "GenerationWorkUnit":
        if self.estimated_input_tokens + self.budget.max_output_tokens > self.context_window_tokens:
            raise ValueError("work-unit input and output budget exceeds its context window")
        return self


class StagePlan(PlanningModel):
    """Stage-local contract made only after its upstream inputs are available."""

    run_id: str = Field(min_length=1)
    stage: StageName
    generation_plan_hash: str = Field(min_length=1)
    dependency_hash: str = Field(min_length=1)
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
        expected_hash = _stage_plan_hash(self)
        if self.stage_plan_hash != expected_hash:
            raise ValueError("stage plan hash does not match its public fields")
        return self


def create_generation_plan(
    *,
    run_id: str,
    requested_stages: tuple[StageName, ...] | list[StageName],
    provider_profile_hash: str,
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
    return GenerationPlan(
        run_id=run_id,
        requested_stages=requested,
        planning_policy_version=planning_policy_version,
        planning_policy_hash=policy_hash,
        provider_profile_hash=provider_profile_hash,
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
) -> StagePlan:
    """Create a stage plan once all selectors for that stage are canonical.

    The resolver makes the dependency fingerprint from exactly the input objects
    the stage prompt needs.  It refuses to derive Scene Beats selectors without
    a Story Graph and Storyboard selectors without a Scene Beat Plan.
    """

    if stage not in generation_plan.requested_stages:
        raise PlanningError(f"stage {stage.value} is not requested by this generation plan")
    required = _required_dependencies(stage)
    missing = [dependency.value for dependency in required if dependency not in dependencies]
    if missing:
        raise PlanningError(
            f"cannot plan {stage.value} before sealed/canonical dependencies exist: "
            f"{', '.join(missing)}"
        )
    dependency_values = {
        dependency: dependencies[dependency]
        for dependency in required
    }
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
    dependency_json = canonical_json(dependency_payload)
    dependency_hash = sha256_text(dependency_json)
    selectors = _selectors_for_stage(stage, dependency_values)
    budget = generation_plan.stage_budgets[stage]
    if len(selectors) > budget.max_units:
        raise PlanningError(
            f"{stage.value} requires {len(selectors)} work units, exceeding its "
            f"max_units budget of {budget.max_units}"
        )
    if len(selectors) > budget.max_aggregate_items:
        raise PlanningError(
            f"{stage.value} requires {len(selectors)} aggregate selectors, exceeding "
            f"its max_aggregate_items budget of {budget.max_aggregate_items}"
        )

    work_units = tuple(
        _work_unit(
            generation_plan=generation_plan,
            stage=stage,
            selector=selector,
            sequence=index,
            dependency_hash=dependency_hash,
            budget=budget,
            unit_dependency_payload=_unit_dependency_payload(
                stage,
                selector,
                dependency_values,
            ),
        )
        for index, selector in enumerate(selectors, start=1)
    )
    unsigned = {
        "run_id": generation_plan.run_id,
        "stage": stage.value,
        "generation_plan_hash": generation_plan.plan_hash,
        "dependency_hash": dependency_hash,
        "work_units": [unit.model_dump(mode="json") for unit in work_units],
    }
    return StagePlan(
        run_id=generation_plan.run_id,
        stage=stage,
        generation_plan_hash=generation_plan.plan_hash,
        dependency_hash=dependency_hash,
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
    context = _unit_dependency_payload(
        work_unit.stage,
        work_unit.selector,
        {stage: dependencies[stage] for stage in required},
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
        if not isinstance(graph, StoryGraph):
            raise PlanningError("scene_beats planning requires a parsed StoryGraph")
        return tuple(
            WorkUnitSelector(kind=WorkUnitSelectorKind.STORY_NODE, stable_id=node.id)
            for node in graph.nodes
        )
    scene_beats = dependencies[StageName.SCENE_BEATS]
    graph = dependencies[StageName.STORY_GRAPH]
    if not isinstance(scene_beats, SceneBeatPlan) or not isinstance(graph, StoryGraph):
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
    ordered_scenes = sorted(
        scene_beats.scenes,
        key=lambda scene: (node_position[scene.story_node_id], scene.id),
    )
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
    if not isinstance(graph, StoryGraph):
        raise PlanningError(f"{stage.value} requires a parsed StoryGraph")
    if stage == StageName.SCENE_BEATS:
        node = next((node for node in graph.nodes if node.id == selector.stable_id), None)
        if node is None:
            raise PlanningError(f"unknown Story Graph node selector {selector.stable_id}")
        return {
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
        }
    scene_beats = dependencies[StageName.SCENE_BEATS]
    if not isinstance(scene_beats, SceneBeatPlan):
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
) -> GenerationWorkUnit:
    unit_dependency_json = canonical_json(unit_dependency_payload)
    unit_dependency_hash = sha256_text(unit_dependency_json)
    # UTF-8 byte length is an intentionally conservative token upper bound for
    # this provider-agnostic planner: a tokenizer cannot consume more byte
    # pieces than the serialized input contains.  The separately frozen prompt
    # overhead reserves template/schema text that is not represented here.
    estimated_input_tokens = (
        generation_plan.canonical_snapshot_bytes
        + generation_plan.instructions_bytes
        + len(unit_dependency_json.encode("utf-8"))
        + generation_plan.prompt_overhead_bytes
    )
    if estimated_input_tokens > budget.max_input_bytes:
        raise PlanningError(
            f"{stage.value} unit {selector.stable_id} conservative input estimate "
            f"is {estimated_input_tokens} bytes, exceeding its max_input_bytes budget "
            f"of {budget.max_input_bytes}"
        )
    if estimated_input_tokens + budget.max_output_tokens > generation_plan.context_window_tokens:
        raise PlanningError(
            f"{stage.value} unit {selector.stable_id} conservative input estimate "
            f"({estimated_input_tokens}) plus max_output_tokens ({budget.max_output_tokens}) "
            f"exceeds provider context window ({generation_plan.context_window_tokens})"
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
    )


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
    )
    return sha256_text(canonical_json(unsigned))
