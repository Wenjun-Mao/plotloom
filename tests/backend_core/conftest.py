from __future__ import annotations

import pytest

from plotloom.domain import (
    AudioPlan,
    BeatV2,
    ContinuityStateV2,
    DialogueCue,
    DramaticSceneV2,
    JoinContractV2,
    ProjectBrief,
    SceneBeatPlanV2,
    ShotBeatLinkV2,
    ShotV2,
    StoryBibleV2,
    StoryboardV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.canonical_schema import V2CoverageRole, V2ShotSize
from plotloom.persistence import SQLiteRepository


@pytest.fixture
def repository() -> SQLiteRepository:
    repo = SQLiteRepository("sqlite://")
    yield repo
    repo.close()


@pytest.fixture
def brief() -> ProjectBrief:
    return ProjectBrief(title="星海回声", synopsis="失忆领航员醒来后必须决定是否唤醒飞船人工智能。")


def make_story_bible() -> StoryBibleV2:
    return StoryBibleV2(
        logline="领航员在真相与生存之间选择。", premise="记忆可能是被设计的导航工具。",
        genre="", tone="", audience="", narrative_promise="", visual_language="",
        themes=[], world_rules=[], known_facts=[], open_questions=[], source_notes=[],
        characters=[], locations=[], props=[],
    )


def make_story_graph() -> StoryGraphV2:
    nodes = [
        StoryNodeV2(id="start", title="苏醒", summary="林默苏醒。", kind="start"),
        StoryNodeV2(id="decision-1", title="第一次选择", summary="选择调查路线。", kind="decision"),
        StoryNodeV2(id="route-a", title="控制室", summary="检查控制室。", kind="scene"),
        StoryNodeV2(id="route-b", title="记忆舱", summary="检查记忆舱。", kind="scene"),
        StoryNodeV2(id="join", title="汇合", summary="线索汇合。", kind="join"),
        StoryNodeV2(id="decision-2", title="最终选择", summary="决定人工智能命运。", kind="decision"),
        StoryNodeV2(id="ending-1", title="唤醒", summary="人工智能苏醒。", kind="ending"),
        StoryNodeV2(id="ending-2", title="关闭", summary="人工智能关闭。", kind="ending"),
        StoryNodeV2(id="ending-3", title="融合", summary="人与人工智能融合。", kind="ending"),
    ]
    edges = [
        StoryEdgeV2(id="e1", source_node_id="start", target_node_id="decision-1", kind="continuation", choice_text=None, state_effects={}),
        StoryEdgeV2(
            id="e2",
            source_node_id="decision-1",
            target_node_id="route-a",
            kind="choice",
            choice_text="去控制室",
            state_effects={},
        ),
        StoryEdgeV2(
            id="e3",
            source_node_id="decision-1",
            target_node_id="route-b",
            kind="choice",
            choice_text="去记忆舱",
            state_effects={},
        ),
        StoryEdgeV2(id="e4", source_node_id="route-a", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
        StoryEdgeV2(id="e5", source_node_id="route-b", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
        StoryEdgeV2(id="e6", source_node_id="join", target_node_id="decision-2", kind="continuation", choice_text=None, state_effects={}),
        StoryEdgeV2(
            id="e7",
            source_node_id="decision-2",
            target_node_id="ending-1",
            kind="choice",
            choice_text="唤醒",
            state_effects={},
        ),
        StoryEdgeV2(
            id="e8",
            source_node_id="decision-2",
            target_node_id="ending-2",
            kind="choice",
            choice_text="关闭",
            state_effects={},
        ),
        StoryEdgeV2(
            id="e9",
            source_node_id="decision-2",
            target_node_id="ending-3",
            kind="choice",
            choice_text="融合",
            state_effects={},
        ),
    ]
    return StoryGraphV2(
        start_node_id="start",
        nodes=nodes,
        edges=edges,
        join_contracts=[
            JoinContractV2(
                id="join-contract",
                join_node_id="join",
                incoming_node_ids=["route-a", "route-b"],
                required_state_keys=["identity"],
                allowed_differences=[],
                reconciliation="两条路线都确认主角身份。",
                notes="",
            )
        ],
    )


def make_scene_beats(graph: StoryGraphV2 | None = None) -> SceneBeatPlanV2:
    graph = graph or make_story_graph()
    scenes: list[DramaticSceneV2] = []
    beats: list[BeatV2] = []
    for node in graph.nodes:
        scene_id = f"scene-{node.id}"
        beat_id = f"beat-{node.id}"
        entry_facts = {"identity": "confirmed"} if node.id == "join" else {}
        exit_facts = {"identity": "confirmed"} if node.id in {"route-a", "route-b"} else {}
        scenes.append(
            DramaticSceneV2(
                id=scene_id,
                story_node_id=node.id,
                order=1,
                title=node.title,
                objective=node.summary,
                location_id=None,
                character_ids=[],
                beat_ids=[beat_id],
                duration_budget_units=8,
                entry_state=ContinuityStateV2(facts=entry_facts, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]),
                exit_state=ContinuityStateV2(facts=exit_facts, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]),
            )
        )
        beats.append(
            BeatV2(
                id=beat_id,
                scene_id=scene_id,
                order=1,
                description=node.summary,
                purpose="推进叙事",
                visible_event=node.summary, immediate_result="状态发生改变", dramatic_change="",
                entry_state=ContinuityStateV2(facts={}, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]),
                exit_state=ContinuityStateV2(facts={}, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]),
                continuity_anchors=[], continuity_delta={},
            )
        )
    return SceneBeatPlanV2(scenes=scenes, beats=beats, dialogue_cues=[])


def make_storyboard(plan: SceneBeatPlanV2 | None = None) -> StoryboardV2:
    plan = plan or make_scene_beats()
    shots: list[ShotV2] = []
    links: list[ShotBeatLinkV2] = []
    for scene in plan.scenes:
        beat_id = scene.beat_ids[0]
        for order in (1, 2):
            shot_id = f"shot-{scene.id}-{order}"
            shots.append(
                ShotV2(
                    id=shot_id,
                    scene_id=scene.id,
                    order=order,
                    title=f"{scene.title}-{order}",
                    shot_size=V2ShotSize.MEDIUM,
                    duration_units=4,
                    camera_angle="", camera_movement="", composition="",
                    visual_intent="清楚呈现人物与空间关系",
                    motion_intent="稳定推进",
                    action=scene.objective,
                    transition="硬切",
                    cue_ids=[], audio_plan=AudioPlan(events=[]),
                    character_ids=[], location_id=None, prop_ids=[], required_entity_states=[],
                    entry_state=ContinuityStateV2(facts={}, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]),
                    exit_state=ContinuityStateV2(facts={}, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]),
                )
            )
            links.append(
                ShotBeatLinkV2(
                    shot_id=shot_id,
                    beat_id=beat_id,
                    role=V2CoverageRole.PRIMARY if order == 1 else V2CoverageRole.SUPPORTING,
                    coverage_weight=1.0,
                )
            )
    return StoryboardV2(shots=shots, shot_beat_links=links)


def all_stage_payloads() -> tuple[StoryBibleV2, StoryGraphV2, SceneBeatPlanV2, StoryboardV2]:
    bible = make_story_bible()
    graph = make_story_graph()
    plan = make_scene_beats(graph)
    storyboard = make_storyboard(plan)
    return bible, graph, plan, storyboard
