"""Exact selector-scoped canonical context and frozen input verification."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel

from plotloom.canonical_schema import DialogueTimingProfile, SceneBeatPlanV2, StoryGraphV2
from plotloom.stage_contracts import StageName
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
)
from .planning_contracts import (
    GenerationWorkUnit,
    PlanningError,
    WorkUnitSelector,
    _json_value,
    content_hash,
)
from .scene_timing_allocation import (
    SceneTimingAllocation,
)


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
        node = next(
            (node for node in graph.nodes if node.id == selector.stable_id), None
        )
        if node is None:
            raise PlanningError(
                f"unknown Story Graph node selector {selector.stable_id}"
            )
        try:
            join_state_values = compile_join_state_value_contract(graph)
        except JoinStateValueContractError as error:
            raise PlanningError(
                "sealed Story Graph cannot produce an exact join-state value contract",
                code="planning.join_state_value_contract_unresolvable",
                stage=stage,
            ) from error
        try:
            edge_entry_states = compile_edge_entry_state_contract(graph)
        except EdgeEntryStateContractError as error:
            raise PlanningError(
                "sealed Story Graph cannot produce an exact typed edge-entry contract",
                code="planning.edge_entry_state_contract_unresolvable",
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
            "edge_entry_state_requirements": (
                edge_entry_states.requirements_for_node(selector.stable_id)
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
    scene = next(
        (scene for scene in scene_beats.scenes if scene.id == selector.stable_id), None
    )
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
            _json_value(beat) for beat in scene_beats.beats if beat.scene_id == scene.id
        ],
        "dialogue_cues": [
            _json_value(cue)
            for cue in scene_beats.dialogue_cues
            if cue.beat_id in set(scene.beat_ids)
        ],
    }
