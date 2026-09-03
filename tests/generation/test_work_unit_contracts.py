from __future__ import annotations

import pytest

from plotloom.domain import (
    Beat,
    CoverageRole,
    DramaticScene,
    ProjectBrief,
    SceneBeatPlan,
    Shot,
    ShotBeatLink,
    ShotSize,
    StageName,
    StoryBible,
    StoryEdge,
    StoryGraph,
    StoryNode,
    StoryNodeKind,
)
from plotloom.generation.fragments import SceneBeatsFragment, StoryboardFragment
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    SceneBeatsFragmentOutput,
    StoryboardFragmentOutput,
    WorkUnitContractError,
    compile_work_unit_request,
)


def _brief() -> ProjectBrief:
    return ProjectBrief(
        title="分片测试",
        synopsis="领航员在空间站寻找身份。",
        ending_count=1,
        decision_points_per_path=0,
        desired_join_count=0,
        node_budget=3,
        shots_per_scene_min=1,
        shots_per_scene_max=2,
    )


def _bible() -> StoryBible:
    return StoryBible(logline="领航员寻找身份。", premise="记忆决定生存。")


def _graph() -> StoryGraph:
    return StoryGraph(
        start_node_id="node-a",
        nodes=[
            StoryNode(id="node-a", title="苏醒", summary="她在控制室醒来。", kind=StoryNodeKind.START),
            StoryNode(id="node-b", title="秘密节点", summary="PRIVATE_OTHER_NODE", kind=StoryNodeKind.ENDING),
        ],
        edges=[StoryEdge(id="edge-a-b", source_node_id="node-a", target_node_id="node-b")],
    )


def _scene_beats(graph: StoryGraph) -> SceneBeatPlan:
    scenes: list[DramaticScene] = []
    beats: list[Beat] = []
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
            )
        )
        beats.append(
            Beat(
                id=beat_id,
                scene_id=scene_id,
                order=1,
                description=node.summary,
                purpose="推进叙事",
            )
        )
    return SceneBeatPlan(scenes=scenes, beats=beats)


def _plan_and_inputs():
    brief = _brief()
    snapshot = {"brief": brief.model_dump(mode="json", by_alias=True)}
    plan = create_generation_plan(
        run_id="work-unit-test",
        requested_stages=list(StageName),
        provider_profile_hash="profile-hash",
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    bible = _bible()
    graph = _graph()
    scene_beats = _scene_beats(graph)
    return brief, snapshot, plan, bible, graph, scene_beats


def _compile_scene_beats():
    brief, snapshot, plan, bible, graph, _ = _plan_and_inputs()
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
    )
    unit = stage_plan.work_units[0]
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
        stage_constraints={"maxBeats": 2},
    )
    return compiled, stage_plan, unit, bible, graph


def _scene_output(node_id: str = "node-a") -> dict:
    scene = DramaticScene(
        id="scene-node-a",
        story_node_id=node_id,
        title="苏醒",
        objective="确认身份",
        beat_ids=["beat-node-a"],
    )
    beat = Beat(
        id="beat-node-a",
        scene_id="scene-node-a",
        order=1,
        description="她睁开眼睛。",
        purpose="建立危机",
    )
    return SceneBeatsFragmentOutput(
        story_node_id=node_id,
        scenes=[scene],
        beats=[beat],
    ).model_dump(mode="json", by_alias=True)


def test_scene_work_unit_prompt_only_contains_the_selected_node_and_public_schema() -> None:
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    brief, snapshot, plan, _, _, _ = _plan_and_inputs()
    second_stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
    )
    second = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=second_stage_plan,
        work_unit=second_stage_plan.work_units[0],
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
        stage_constraints={"maxBeats": 2},
    )
    message = compiled.rendered.messages[1].content

    assert "node-a" in message
    assert "PRIVATE_OTHER_NODE" not in message
    # The node ID may appear in an incident edge; the other node's title and
    # summary must not be copied into the unit's creative context.
    assert "stagePlanHash" not in compiled.response_schema["properties"]
    assert "workUnitId" not in compiled.response_schema["properties"]
    assert "unitDependencyHash" not in compiled.response_schema["properties"]
    assert compiled.contract.work_unit_id == unit.unit_id
    assert compiled.contract.stage_plan_hash == stage_plan.stage_plan_hash
    assert compiled.contract.prompt_id == "scene_beats_fragment"
    assert compiled.contract.schema_hash
    assert compiled.contract.variables_hash == second.contract.variables_hash
    assert compiled.contract.rendered_hash == second.contract.rendered_hash


def test_scene_fragment_rejects_wrong_selector_and_binds_metadata_only_after_validation() -> None:
    compiled, stage_plan, unit, _, _ = _compile_scene_beats()
    wrong_selector = compiled.validator.validate(
        _scene_output("node-b"),
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert wrong_selector.accepted is False
    assert "selector.story_node" in {issue.code for issue in wrong_selector.issues}

    accepted = compiled.validator.validate(
        _scene_output(),
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert accepted.accepted is True
    assert isinstance(accepted.value, SceneBeatsFragment)
    assert accepted.value.stage_plan_hash == stage_plan.stage_plan_hash
    assert accepted.value.work_unit_id == unit.unit_id


def test_storyboard_fragment_rejects_other_scene_or_beat_reference() -> None:
    brief, snapshot, plan, bible, graph, scene_beats = _plan_and_inputs()
    stage_plan = plan_stage(
        plan,
        stage=StageName.STORYBOARD,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
            StageName.SCENE_BEATS: scene_beats,
        },
    )
    unit = stage_plan.work_units[0]
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
            StageName.SCENE_BEATS: scene_beats,
        },
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    shot = Shot(
        id="shot-a",
        scene_id="scene-node-a",
        order=1,
        title="苏醒",
        shot_size=ShotSize.CLOSE_UP,
        duration_seconds=2,
    )
    output = StoryboardFragmentOutput(
        scene_id="scene-node-a",
        shots=[shot],
        shot_beat_links=[
            ShotBeatLink(
                shot_id="shot-a",
                beat_id="beat-node-b",
                role=CoverageRole.PRIMARY,
            )
        ],
    ).model_dump(mode="json", by_alias=True)
    rejected = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert rejected.accepted is False
    assert "semantic.cross_unit_beat" in {issue.code for issue in rejected.issues}

    output["shotBeatLinks"][0]["beatId"] = "beat-node-a"
    accepted = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert accepted.accepted is True
    assert isinstance(accepted.value, StoryboardFragment)


def test_compiler_rejects_non_frozen_snapshot_or_context() -> None:
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    plan = _plan_and_inputs()[2]
    with pytest.raises(WorkUnitContractError, match="canonical_snapshot"):
        compile_work_unit_request(
            generation_plan=plan,
            stage_plan=stage_plan,
            work_unit=unit,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
            brief=_brief(),
            canonical_snapshot={"different": True},
            instructions="preserve the project brief",
        )
