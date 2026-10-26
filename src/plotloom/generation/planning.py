"""Stage-local unit planning after upstream canonical inputs exist."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel

from ..domain import (
    DialogueTimingProfile,
    ProjectBrief,
    SceneBeatPlanV2,
    StageName,
    StoryGraphV2,
    default_dialogue_timing_profile,
)
from ..edge_entry_states import (
    EdgeEntryStateContractError,
    compile_edge_entry_state_contract,
)
from ..join_state_values import (
    JoinStateValueContractError,
    compile_join_state_value_contract,
)
from .dialogue_capacity import (
    DialogueCapacityPlan,
    DialogueCapacityPlanningError,
    plan_dialogue_capacity,
)
from .planning_context import _required_dependencies, _unit_dependency_payload
from .planning_contracts import (
    GenerationPlan,
    GenerationWorkUnit,
    PlanningError,
    StageBudget,
    StagePlan,
    WorkUnitSelector,
    WorkUnitSelectorKind,
    _json_value,
)
from .prompts import canonical_json, sha256_text
from .scene_timing_allocation import (
    SceneTimingAllocation,
    SceneTimingAllocationError,
    plan_scene_timing_allocation,
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
    missing = [
        dependency.value for dependency in required if dependency not in dependencies
    ]
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
        dependency: dependencies[dependency] for dependency in required
    }
    scene_timing_allocation: SceneTimingAllocation | None = None
    dialogue_timing_profile: DialogueTimingProfile | None = None
    dialogue_capacity_plan: DialogueCapacityPlan | None = None
    join_state_value_contract_version: str | None = None
    join_state_value_contract_hash: str | None = None
    edge_entry_state_contract_version: str | None = None
    edge_entry_state_contract_hash: str | None = None
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
        try:
            edge_entry_states = compile_edge_entry_state_contract(graph)
        except EdgeEntryStateContractError as exc:
            raise PlanningError(
                "sealed Story Graph cannot produce an exact typed edge-entry contract",
                code="planning.edge_entry_state_contract_unresolvable",
                stage=stage,
            ) from exc
        edge_entry_state_contract_version = edge_entry_states.version
        edge_entry_state_contract_hash = edge_entry_states.contract_hash
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
        dependency_payload["dialogue_timing_profile"] = (
            dialogue_timing_profile.model_dump(mode="json", by_alias=True)
        )
        dependency_payload["dialogue_capacity_plan"] = (
            dialogue_capacity_plan.model_dump(mode="json", by_alias=True)
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
    if (
        edge_entry_state_contract_version is not None
        and edge_entry_state_contract_hash is not None
    ):
        dependency_payload["edge_entry_state_contract"] = {
            "version": edge_entry_state_contract_version,
            "hash": edge_entry_state_contract_hash,
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
    if (
        edge_entry_state_contract_version is not None
        and edge_entry_state_contract_hash is not None
    ):
        unsigned["edge_entry_state_contract_version"] = (
            edge_entry_state_contract_version
        )
        unsigned["edge_entry_state_contract_hash"] = edge_entry_state_contract_hash
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
        edge_entry_state_contract_version=edge_entry_state_contract_version,
        edge_entry_state_contract_hash=edge_entry_state_contract_hash,
        work_units=work_units,
        stage_plan_hash=sha256_text(canonical_json(unsigned)),
    )


def _selectors_for_stage(
    stage: StageName,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
) -> tuple[WorkUnitSelector, ...]:
    if stage in {StageName.STORY_BIBLE, StageName.STORY_GRAPH}:
        return (
            WorkUnitSelector(
                kind=WorkUnitSelectorKind.WHOLE_STAGE, stable_id=stage.value
            ),
        )
    if stage == StageName.SCENE_BEATS:
        graph = dependencies[StageName.STORY_GRAPH]
        if not isinstance(graph, StoryGraphV2):
            raise PlanningError("scene_beats planning requires a parsed StoryGraph")
        return tuple(
            WorkUnitSelector(kind=WorkUnitSelectorKind.STORY_NODE, stable_id=node.id)
            for node in graph.nodes
            if node.footage_mode == "footage"
        )
    scene_beats = dependencies[StageName.SCENE_BEATS]
    graph = dependencies[StageName.STORY_GRAPH]
    if not isinstance(scene_beats, SceneBeatPlanV2) or not isinstance(
        graph, StoryGraphV2
    ):
        raise PlanningError(
            "storyboard planning requires parsed StoryGraph and SceneBeatPlan"
        )
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
            key=lambda item: (
                node_position[item[1].story_node_id],
                item[1].order,
                item[0],
            ),
        )
    ]
    if not ordered_scenes:
        raise PlanningError("storyboard planning requires at least one dramatic scene")
    return tuple(
        WorkUnitSelector(kind=WorkUnitSelectorKind.DRAMATIC_SCENE, stable_id=scene.id)
        for scene in ordered_scenes
    )


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
