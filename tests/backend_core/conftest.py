from __future__ import annotations

import pytest

from plotloom.domain import (
    Beat,
    ContinuityState,
    CoverageRole,
    DramaticScene,
    JoinContract,
    ProjectBrief,
    SceneBeatPlan,
    Shot,
    ShotBeatLink,
    ShotSize,
    StoryBible,
    Storyboard,
    StoryEdge,
    StoryEdgeKind,
    StoryGraph,
    StoryNode,
    StoryNodeKind,
)
from plotloom.persistence import SQLiteRepository


@pytest.fixture
def repository() -> SQLiteRepository:
    repo = SQLiteRepository("sqlite://")
    yield repo
    repo.close()


@pytest.fixture
def brief() -> ProjectBrief:
    return ProjectBrief(title="星海回声", synopsis="失忆领航员醒来后必须决定是否唤醒飞船人工智能。")


def make_story_bible() -> StoryBible:
    return StoryBible(logline="领航员在真相与生存之间选择。", premise="记忆可能是被设计的导航工具。")


def make_story_graph() -> StoryGraph:
    nodes = [
        StoryNode(id="start", title="苏醒", summary="林默苏醒。", kind=StoryNodeKind.START),
        StoryNode(id="decision-1", title="第一次选择", summary="选择调查路线。", kind=StoryNodeKind.DECISION),
        StoryNode(id="route-a", title="控制室", summary="检查控制室。", kind=StoryNodeKind.SCENE),
        StoryNode(id="route-b", title="记忆舱", summary="检查记忆舱。", kind=StoryNodeKind.SCENE),
        StoryNode(id="join", title="汇合", summary="线索汇合。", kind=StoryNodeKind.JOIN),
        StoryNode(id="decision-2", title="最终选择", summary="决定人工智能命运。", kind=StoryNodeKind.DECISION),
        StoryNode(id="ending-1", title="唤醒", summary="人工智能苏醒。", kind=StoryNodeKind.ENDING),
        StoryNode(id="ending-2", title="关闭", summary="人工智能关闭。", kind=StoryNodeKind.ENDING),
        StoryNode(id="ending-3", title="融合", summary="人与人工智能融合。", kind=StoryNodeKind.ENDING),
    ]
    edges = [
        StoryEdge(id="e1", source_node_id="start", target_node_id="decision-1"),
        StoryEdge(
            id="e2",
            source_node_id="decision-1",
            target_node_id="route-a",
            kind=StoryEdgeKind.CHOICE,
            choice_text="去控制室",
        ),
        StoryEdge(
            id="e3",
            source_node_id="decision-1",
            target_node_id="route-b",
            kind=StoryEdgeKind.CHOICE,
            choice_text="去记忆舱",
        ),
        StoryEdge(id="e4", source_node_id="route-a", target_node_id="join"),
        StoryEdge(id="e5", source_node_id="route-b", target_node_id="join"),
        StoryEdge(id="e6", source_node_id="join", target_node_id="decision-2"),
        StoryEdge(
            id="e7",
            source_node_id="decision-2",
            target_node_id="ending-1",
            kind=StoryEdgeKind.CHOICE,
            choice_text="唤醒",
        ),
        StoryEdge(
            id="e8",
            source_node_id="decision-2",
            target_node_id="ending-2",
            kind=StoryEdgeKind.CHOICE,
            choice_text="关闭",
        ),
        StoryEdge(
            id="e9",
            source_node_id="decision-2",
            target_node_id="ending-3",
            kind=StoryEdgeKind.CHOICE,
            choice_text="融合",
        ),
    ]
    return StoryGraph(
        start_node_id="start",
        nodes=nodes,
        edges=edges,
        join_contracts=[
            JoinContract(
                id="join-contract",
                join_node_id="join",
                incoming_node_ids=["route-a", "route-b"],
                required_state_keys=["identity"],
                allowed_differences=["route"],
                reconciliation="两条路线都确认主角身份。",
            )
        ],
    )


def make_scene_beats(graph: StoryGraph | None = None) -> SceneBeatPlan:
    graph = graph or make_story_graph()
    scenes: list[DramaticScene] = []
    beats: list[Beat] = []
    for node in graph.nodes:
        scene_id = f"scene-{node.id}"
        beat_id = f"beat-{node.id}"
        entry_facts = {"identity": "confirmed"} if node.id == "join" else {}
        exit_facts = {"identity": "confirmed"} if node.id in {"route-a", "route-b"} else {}
        scenes.append(
            DramaticScene(
                id=scene_id,
                story_node_id=node.id,
                title=node.title,
                objective=node.summary,
                beat_ids=[beat_id],
                entry_state=ContinuityState(facts=entry_facts),
                exit_state=ContinuityState(facts=exit_facts),
            )
        )
        beats.append(
            Beat(
                id=beat_id,
                scene_id=scene_id,
                order=1,
                description=node.summary,
                purpose="推进叙事",
                visible_event=node.summary,
                immediate_result="状态发生改变",
            )
        )
    return SceneBeatPlan(scenes=scenes, beats=beats)


def make_storyboard(plan: SceneBeatPlan | None = None) -> Storyboard:
    plan = plan or make_scene_beats()
    shots: list[Shot] = []
    links: list[ShotBeatLink] = []
    for scene in plan.scenes:
        beat_id = scene.beat_ids[0]
        for order in (1, 2):
            shot_id = f"shot-{scene.id}-{order}"
            shots.append(
                Shot(
                    id=shot_id,
                    scene_id=scene.id,
                    order=order,
                    title=f"{scene.title}-{order}",
                    shot_size=ShotSize.MEDIUM,
                    duration_seconds=4,
                    visual_intent="清楚呈现人物与空间关系",
                    motion_intent="稳定推进",
                    action=scene.objective,
                    audio="环境底噪",
                    transition="硬切",
                )
            )
            links.append(
                ShotBeatLink(
                    shot_id=shot_id,
                    beat_id=beat_id,
                    role=CoverageRole.PRIMARY if order == 1 else CoverageRole.SUPPORTING,
                )
            )
    return Storyboard(shots=shots, shot_beat_links=links)


def all_stage_payloads() -> tuple[StoryBible, StoryGraph, SceneBeatPlan, Storyboard]:
    bible = make_story_bible()
    graph = make_story_graph()
    plan = make_scene_beats(graph)
    storyboard = make_storyboard(plan)
    return bible, graph, plan, storyboard
