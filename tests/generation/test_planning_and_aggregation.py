from __future__ import annotations

import pytest

from plotloom.domain import (
    Beat,
    ContinuityState,
    CoverageRole,
    DramaticScene,
    JoinContract,
    Shot,
    ShotBeatLink,
    ShotSize,
    StageName,
    StoryBible,
    StoryEdge,
    StoryEdgeKind,
    StoryGraph,
    StoryNode,
    StoryNodeKind,
    Storyboard,
)
from plotloom.generation.aggregation import (
    AggregateValidationError,
    aggregate_stage_fragments,
)
from plotloom.generation.fragments import (
    SceneBeatsFragment,
    StoryBibleFragment,
    StoryboardFragment,
    StoryGraphFragment,
)
from plotloom.generation.planning import (
    PlanningError,
    StageBudget,
    WorkUnitSelectorKind,
    create_generation_plan,
    plan_stage,
)

def _run_plan(
    *,
    stage_budgets: dict[StageName, StageBudget] | None = None,
    canonical_snapshot: dict | None = None,
    instructions: str = "keep the supplied story premise intact",
    context_window_tokens: int = 32_768,
    provider_output_token_ceiling: int | None = None,
):
    return create_generation_plan(
        run_id="run-planning-test",
        requested_stages=list(StageName),
        provider_profile_hash="profile-public-hash",
        canonical_snapshot=canonical_snapshot
        or {
            "projectId": "project-planning-test",
            "brief": _brief().model_dump(mode="json", by_alias=True),
        },
        instructions=instructions,
        stage_budgets=stage_budgets,
        context_window_tokens=context_window_tokens,
        provider_output_token_ceiling=provider_output_token_ceiling,
    )


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
        StoryEdge(id="e2", source_node_id="decision-1", target_node_id="route-a", kind=StoryEdgeKind.CHOICE, choice_text="去控制室"),
        StoryEdge(id="e3", source_node_id="decision-1", target_node_id="route-b", kind=StoryEdgeKind.CHOICE, choice_text="去记忆舱"),
        StoryEdge(id="e4", source_node_id="route-a", target_node_id="join"),
        StoryEdge(id="e5", source_node_id="route-b", target_node_id="join"),
        StoryEdge(id="e6", source_node_id="join", target_node_id="decision-2"),
        StoryEdge(id="e7", source_node_id="decision-2", target_node_id="ending-1", kind=StoryEdgeKind.CHOICE, choice_text="唤醒"),
        StoryEdge(id="e8", source_node_id="decision-2", target_node_id="ending-2", kind=StoryEdgeKind.CHOICE, choice_text="关闭"),
        StoryEdge(id="e9", source_node_id="decision-2", target_node_id="ending-3", kind=StoryEdgeKind.CHOICE, choice_text="融合"),
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


def make_scene_beats(graph: StoryGraph) -> "SceneBeatPlan":
    from plotloom.domain import SceneBeatPlan

    scenes = []
    beats = []
    for node in graph.nodes:
        scene_id = f"scene-{node.id}"
        beat_id = f"beat-{node.id}"
        scenes.append(
            DramaticScene(
                id=scene_id,
                story_node_id=node.id,
                title=node.title,
                objective=node.summary,
                beat_ids=[beat_id],
                entry_state=ContinuityState(facts={"identity": "confirmed"} if node.id == "join" else {}),
                exit_state=ContinuityState(facts={"identity": "confirmed"} if node.id in {"route-a", "route-b"} else {}),
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


def make_storyboard(plan) -> Storyboard:
    shots = []
    links = []
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


def _stage_plans():
    bible = make_story_bible()
    graph = make_story_graph()
    scene_beats = make_scene_beats(graph)
    plan = _run_plan()
    bible_stage = plan_stage(plan, stage=StageName.STORY_BIBLE, dependencies={})
    graph_stage = plan_stage(
        plan,
        stage=StageName.STORY_GRAPH,
        dependencies={StageName.STORY_BIBLE: bible},
    )
    beats_stage = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
    )
    storyboard_stage = plan_stage(
        plan,
        stage=StageName.STORYBOARD,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
            StageName.SCENE_BEATS: scene_beats,
        },
    )
    return bible, graph, scene_beats, bible_stage, graph_stage, beats_stage, storyboard_stage


def _scene_fragments(stage_plan, scene_beats):
    by_node = {
        scene.story_node_id: [scene]
        for scene in scene_beats.scenes
    }
    fragments = []
    for unit in stage_plan.work_units:
        scenes = by_node[unit.selector.stable_id]
        scene_ids = {scene.id for scene in scenes}
        fragments.append(
            SceneBeatsFragment(
                stage_plan_hash=stage_plan.stage_plan_hash,
                work_unit_id=unit.unit_id,
                story_node_id=unit.selector.stable_id,
                scenes=scenes,
                beats=[beat for beat in scene_beats.beats if beat.scene_id in scene_ids],
            )
        )
    return fragments


def _storyboard_fragments(stage_plan, storyboard):
    fragments = []
    for unit in stage_plan.work_units:
        shots = [shot for shot in storyboard.shots if shot.scene_id == unit.selector.stable_id]
        shot_ids = {shot.id for shot in shots}
        fragments.append(
            StoryboardFragment(
                stage_plan_hash=stage_plan.stage_plan_hash,
                work_unit_id=unit.unit_id,
                scene_id=unit.selector.stable_id,
                shots=shots,
                shot_beat_links=[
                    link for link in storyboard.shot_beat_links if link.shot_id in shot_ids
                ],
            )
        )
    return fragments


def test_run_plan_does_not_invent_future_selectors_and_stage_plans_are_deterministic():
    plan = _run_plan()

    with pytest.raises(PlanningError, match="sealed/canonical dependencies"):
        plan_stage(plan, stage=StageName.STORYBOARD, dependencies={})

    bible = make_story_bible()
    graph = make_story_graph()
    first = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
    )
    second = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
    )

    assert first == second
    assert [unit.selector.stable_id for unit in first.work_units] == [
        node.id for node in graph.nodes
    ]
    assert all(unit.selector.kind == WorkUnitSelectorKind.STORY_NODE for unit in first.work_units)

    changed_story = _run_plan(canonical_snapshot={"brief": {"title": "另一个故事"}})
    changed_instructions = _run_plan(instructions="preserve a different constraint")
    assert plan.plan_hash != changed_story.plan_hash
    assert plan.plan_hash != changed_instructions.plan_hash
    assert plan.run_request_hash != changed_instructions.run_request_hash
    changed_stage = plan_stage(
        changed_instructions,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
    )
    assert first.dependency_hash != changed_stage.dependency_hash
    assert first.work_units[0].input_hash != changed_stage.work_units[0].input_hash

    with pytest.raises(PlanningError, match="canonical_snapshot_hash does not match"):
        create_generation_plan(
            run_id="forged-snapshot-plan",
            requested_stages=[StageName.STORY_BIBLE],
            provider_profile_hash="profile-public-hash",
            canonical_snapshot={"brief": {"title": "原始故事"}},
            canonical_snapshot_hash="not-the-snapshot-hash",
        )


def test_planner_refuses_unbounded_unit_or_input_budget():
    bible = make_story_bible()
    graph = make_story_graph()
    too_few_units = _run_plan(
        stage_budgets={StageName.SCENE_BEATS: StageBudget(max_units=1)}
    )
    with pytest.raises(PlanningError, match="max_units"):
        plan_stage(
            too_few_units,
            stage=StageName.SCENE_BEATS,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        )

    too_small_input = _run_plan(
        stage_budgets={StageName.SCENE_BEATS: StageBudget(max_input_bytes=1)}
    )
    with pytest.raises(PlanningError, match="max_input_bytes"):
        plan_stage(
            too_small_input,
            stage=StageName.SCENE_BEATS,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        )

    over_context = _run_plan(context_window_tokens=10)
    with pytest.raises(PlanningError, match="context window"):
        plan_stage(
            over_context,
            stage=StageName.SCENE_BEATS,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        )


def test_generation_plan_freezes_effective_provider_output_ceiling():
    capped = _run_plan(provider_output_token_ceiling=1_024)
    custom = _run_plan(
        stage_budgets={StageName.STORY_BIBLE: StageBudget(max_output_tokens=512)},
        provider_output_token_ceiling=1_024,
    )
    uncapped = _run_plan()

    assert {budget.max_output_tokens for budget in capped.stage_budgets.values()} == {1_024}
    assert custom.stage_budgets[StageName.STORY_BIBLE].max_output_tokens == 512
    assert capped.plan_hash != uncapped.plan_hash

    with pytest.raises(PlanningError, match="provider_output_token_ceiling"):
        _run_plan(provider_output_token_ceiling=0)


def test_scene_beat_aggregation_requires_exact_ordered_unit_manifest():
    bible, graph, scene_beats, _, _, beats_stage, _ = _stage_plans()
    fragments = _scene_fragments(beats_stage, scene_beats)

    aggregate = aggregate_stage_fragments(
        beats_stage,
        fragments,
        brief=_brief(),
        bible=bible,
        graph=graph,
    )
    assert aggregate == scene_beats

    with pytest.raises(AggregateValidationError, match="missing units"):
        aggregate_stage_fragments(
            beats_stage,
            fragments[:-1],
            brief=_brief(),
            bible=bible,
            graph=graph,
        )
    with pytest.raises(AggregateValidationError, match="sequence order"):
        aggregate_stage_fragments(
            beats_stage,
            list(reversed(fragments)),
            brief=_brief(),
            bible=bible,
            graph=graph,
        )


def test_storyboard_aggregation_rejects_cross_unit_references_and_multiple_primary_links():
    bible, graph, scene_beats, _, _, _, storyboard_stage = _stage_plans()
    storyboard = make_storyboard(scene_beats)
    fragments = _storyboard_fragments(storyboard_stage, storyboard)

    bad_cross_unit = fragments[0].model_copy(
        update={
            "shot_beat_links": (
                fragments[0].shot_beat_links[0].model_copy(
                    update={"beat_id": scene_beats.scenes[1].beat_ids[0]}
                ),
                *fragments[0].shot_beat_links[1:],
            )
        }
    )
    with pytest.raises(AggregateValidationError, match="another dramatic-scene unit"):
        aggregate_stage_fragments(
            storyboard_stage,
            [bad_cross_unit, *fragments[1:]],
            brief=_brief(),
            bible=bible,
            graph=graph,
            scene_beats=scene_beats,
        )

    duplicate_primary = fragments[0].model_copy(
        update={
            "shot_beat_links": (
                *fragments[0].shot_beat_links[:1],
                fragments[0].shot_beat_links[1].model_copy(
                    update={"role": CoverageRole.PRIMARY}
                ),
            )
        }
    )
    with pytest.raises(AggregateValidationError, match="more than one PRIMARY"):
        aggregate_stage_fragments(
            storyboard_stage,
            [duplicate_primary, *fragments[1:]],
            brief=_brief(),
            bible=bible,
            graph=graph,
            scene_beats=scene_beats,
        )


def test_storyboard_aggregation_allows_multiple_supporting_links_per_beat():
    bible, graph, scene_beats, _, _, _, storyboard_stage = _stage_plans()
    storyboard = make_storyboard(scene_beats)
    fragments = _storyboard_fragments(storyboard_stage, storyboard)
    first = fragments[0]
    additional_shot = first.shots[-1].model_copy(update={"id": "extra-supporting-shot", "order": 3})
    additional_link = ShotBeatLink(
        shot_id=additional_shot.id,
        beat_id=scene_beats.scenes[0].beat_ids[0],
        role=CoverageRole.SUPPORTING,
    )
    fragments[0] = first.model_copy(
        update={
            "shots": (*first.shots, additional_shot),
            "shot_beat_links": (*first.shot_beat_links, additional_link),
        }
    )

    aggregate = aggregate_stage_fragments(
        storyboard_stage,
        fragments,
        brief=_brief(shots_per_scene_max=3),
        bible=bible,
        graph=graph,
        scene_beats=scene_beats,
    )
    assert len(aggregate.shot_beat_links) == len(storyboard.shot_beat_links) + 1


def _brief(*, shots_per_scene_max: int = 2):
    from plotloom.domain import ProjectBrief

    return ProjectBrief(
        title="星海回声",
        synopsis="失忆领航员醒来后必须决定是否唤醒飞船人工智能。",
        shots_per_scene_max=shots_per_scene_max,
    )
