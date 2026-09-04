from __future__ import annotations

import pytest

from plotloom.domain import ProjectBrief, StoryEdgeV2, StoryGraphV2, StoryNodeV2
from plotloom.generation.scene_timing_allocation import (
    SceneTimingAllocationError,
    plan_scene_timing_allocation,
)


def _brief(*, seconds: int = 1) -> ProjectBrief:
    return ProjectBrief(
        title="时长分配",
        synopsis="在分歧后重新汇合。",
        target_playthrough_seconds=seconds,
    )


def _layered_graph() -> StoryGraphV2:
    return StoryGraphV2(
        start_node_id="start",
        nodes=[
            StoryNodeV2(id="start", title="开始", summary="抵达", kind="start"),
            StoryNodeV2(id="decision", title="选择", summary="选择路线", kind="decision"),
            StoryNodeV2(id="left", title="左路", summary="绕行", kind="scene"),
            StoryNodeV2(id="right", title="右路", summary="直行", kind="scene"),
            StoryNodeV2(id="join", title="汇流", summary="会合", kind="join"),
            StoryNodeV2(id="ending", title="结局", summary="离开", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(id="e1", source_node_id="start", target_node_id="decision", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="e2", source_node_id="decision", target_node_id="left", kind="choice", choice_text="左", state_effects={}),
            StoryEdgeV2(id="e3", source_node_id="decision", target_node_id="right", kind="choice", choice_text="右", state_effects={}),
            StoryEdgeV2(id="e4", source_node_id="left", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="e5", source_node_id="right", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="e6", source_node_id="join", target_node_id="ending", kind="continuation", choice_text=None, state_effects={}),
        ],
        join_contracts=[],
    )


def test_layered_allocation_is_deterministic_shared_and_exact_for_all_paths() -> None:
    graph = _layered_graph()
    first = plan_scene_timing_allocation(graph=graph, brief=_brief(seconds=1))
    reordered = StoryGraphV2(
        start_node_id=graph.start_node_id,
        nodes=list(reversed(graph.nodes)),
        edges=list(reversed(graph.edges)),
        join_contracts=[],
    )
    second = plan_scene_timing_allocation(graph=reordered, brief=_brief(seconds=1))

    assert first == second
    assert first.target_duration_units == 1_000
    assert first.exact_for_all_complete_paths is True
    assert [layer.duration_budget_units for layer in first.layers] == [200, 200, 200, 200, 200]
    assert first.node_duration_budget("left") == first.node_duration_budget("right") == 200
    left_path = ("start", "decision", "left", "join", "ending")
    right_path = ("start", "decision", "right", "join", "ending")
    assert sum(first.node_duration_budget(node_id) for node_id in left_path) == 1_000
    assert sum(first.node_duration_budget(node_id) for node_id in right_path) == 1_000


def test_non_layered_dag_can_be_shorter_but_never_exceeds_target() -> None:
    graph = _layered_graph().model_copy(
        update={
            "edges": [
                StoryEdgeV2(id="e1", source_node_id="start", target_node_id="decision", kind="continuation", choice_text=None, state_effects={}),
                StoryEdgeV2(id="e2", source_node_id="decision", target_node_id="left", kind="choice", choice_text="左", state_effects={}),
                StoryEdgeV2(id="e3", source_node_id="decision", target_node_id="right", kind="choice", choice_text="右", state_effects={}),
                StoryEdgeV2(id="e4", source_node_id="left", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
                StoryEdgeV2(id="e5", source_node_id="right", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
                StoryEdgeV2(id="e6", source_node_id="join", target_node_id="ending", kind="continuation", choice_text=None, state_effects={}),
                StoryEdgeV2(id="shortcut", source_node_id="start", target_node_id="ending", kind="continuation", choice_text=None, state_effects={}),
            ]
        }
    )
    allocation = plan_scene_timing_allocation(graph=graph, brief=_brief(seconds=1))

    assert allocation.exact_for_all_complete_paths is False
    assert sum(allocation.node_duration_budget(node_id) for node_id in ("start", "ending")) < 1_000
    assert sum(
        allocation.node_duration_budget(node_id)
        for node_id in ("start", "decision", "left", "join", "ending")
    ) == 1_000


def test_allocation_identity_ignores_story_prose_but_tracks_structure() -> None:
    graph = _layered_graph()
    renamed = graph.model_copy(
        update={
            "nodes": [
                node.model_copy(update={"title": f"改名 {node.id}", "summary": "同一结构"})
                for node in graph.nodes
            ]
        }
    )

    assert plan_scene_timing_allocation(graph=graph, brief=_brief()) == plan_scene_timing_allocation(
        graph=renamed, brief=_brief()
    )


def test_cycle_has_a_stable_infeasible_error_code() -> None:
    graph = StoryGraphV2(
        start_node_id="start",
        nodes=[
            StoryNodeV2(id="start", title="开始", summary="开始", kind="start"),
            StoryNodeV2(id="loop", title="循环", summary="循环", kind="scene"),
            StoryNodeV2(id="ending", title="结局", summary="结束", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(id="e1", source_node_id="start", target_node_id="loop", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="e2", source_node_id="loop", target_node_id="start", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="e3", source_node_id="loop", target_node_id="ending", kind="continuation", choice_text=None, state_effects={}),
        ],
        join_contracts=[],
    )
    with pytest.raises(SceneTimingAllocationError) as failure:
        plan_scene_timing_allocation(graph=graph, brief=_brief())

    assert failure.value.code == "timing.graph_cycle"


def test_target_smaller_than_graph_depth_has_a_stable_infeasible_error_code() -> None:
    nodes = [StoryNodeV2(id=f"n{index}", title="n", summary="n", kind="scene") for index in range(1_001)]
    nodes[0] = StoryNodeV2(id="n0", title="n", summary="n", kind="start")
    nodes[-1] = StoryNodeV2(id="n1000", title="n", summary="n", kind="ending")
    graph = StoryGraphV2(
        start_node_id="n0",
        nodes=nodes,
        edges=[
            StoryEdgeV2(
                id=f"e{index}",
                source_node_id=f"n{index}",
                target_node_id=f"n{index + 1}",
                kind="continuation",
                choice_text=None,
                state_effects={},
            )
            for index in range(1_000)
        ],
        join_contracts=[],
    )
    with pytest.raises(SceneTimingAllocationError) as failure:
        plan_scene_timing_allocation(graph=graph, brief=_brief(seconds=1))

    assert failure.value.code == "timing.target_too_small"
