from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.domain import (
    AudioPlan,
    BeatV2,
    ContinuityStateV2,
    DramaticSceneV2,
    JoinContractV2,
    ProjectBrief,
    SceneBeatPlanV2,
    StageName,
    StoryBibleV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.generation.fragments import SceneBeatsFragment, StoryboardFragment
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    WorkUnitContractError,
    WorkUnitPromptContract,
    compile_work_unit_request,
)
from plotloom.generation.work_units import (
    BeatContent,
    DramaticSceneContent,
    SceneBeatsFragmentOutput,
    ShotContent,
    StoryboardFragmentOutput,
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


def _state() -> ContinuityStateV2:
    return ContinuityStateV2(facts={}, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[])


def _bible() -> StoryBibleV2:
    return StoryBibleV2(logline="领航员寻找身份。", premise="记忆决定生存。", genre="", tone="", audience="", narrative_promise="", visual_language="", themes=[], world_rules=[], known_facts=[], open_questions=[], source_notes=[], characters=[], locations=[], props=[])


def _graph() -> StoryGraphV2:
    return StoryGraphV2(
        start_node_id="node-a",
        nodes=[
            StoryNodeV2(id="node-a", title="苏醒", summary="她在控制室醒来。", kind="start"),
            StoryNodeV2(id="node-b", title="秘密节点", summary="PRIVATE_OTHER_NODE", kind="ending"),
        ],
        edges=[StoryEdgeV2(id="edge-a-b", source_node_id="node-a", target_node_id="node-b", kind="continuation", choice_text=None, state_effects={})],
        join_contracts=[],
    )


def _scene_beats(graph: StoryGraphV2) -> SceneBeatPlanV2:
    scenes: list[DramaticSceneV2] = []
    beats: list[BeatV2] = []
    for node in graph.nodes:
        scene_id = f"scene-{node.id}"
        beat_id = f"beat-{node.id}"
        scenes.append(
            DramaticSceneV2(
                id=scene_id,
                story_node_id=node.id,
                title=node.title,
                objective=node.summary,
                order=1, beat_ids=[beat_id], duration_budget_units=2, entry_state=_state(), exit_state=_state(), location_id=None, character_ids=[],
            )
        )
        beats.append(
            BeatV2(
                id=beat_id,
                scene_id=scene_id,
                order=1,
                description=node.summary,
                purpose="推进叙事", visible_event="", immediate_result="", dramatic_change="", entry_state=_state(), exit_state=_state(), continuity_anchors=[], continuity_delta={},
            )
        )
    return SceneBeatPlanV2(scenes=scenes, beats=beats, dialogue_cues=[])


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
        brief=brief,
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


def _scene_output() -> dict:
    return SceneBeatsFragmentOutput(
        scenes=[DramaticSceneContent(local_scene_id="scene-node-a", order=1, title="苏醒", objective="确认身份", location_id=None, character_ids=[], duration_weight=1, entry_state=_state(), exit_state=_state())],
        beats=[BeatContent(local_beat_id="beat-node-a", scene_local_id="scene-node-a", order=1, description="她睁开眼睛。", purpose="建立危机", visible_event="", immediate_result="", dramatic_change="", entry_state=_state(), exit_state=_state(), continuity_anchors=[], continuity_delta={})], dialogue_cues=[],
    ).model_dump(mode="json", by_alias=True)


def _storyboard_output(*, beat_ids: list[str], local_shot_id: str = "shot-a") -> dict:
    return StoryboardFragmentOutput(
        shots=[ShotContent(local_shot_id=local_shot_id, order=1, title="苏醒", shot_size="close_up", duration_units=2, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=[], audio_plan=AudioPlan(events=[]), character_ids=[], location_id=None, prop_ids=[], required_entity_states=[], entry_state=_state(), exit_state=_state())],
        primary_shot_local_id_by_beat={beat_id: local_shot_id for beat_id in beat_ids}, supporting_beat_links=[],
    ).model_dump(mode="json", by_alias=True)


def test_scene_work_unit_prompt_only_contains_the_selected_node_and_public_schema() -> None:
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    brief, snapshot, plan, _, _, _ = _plan_and_inputs()
    second_stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
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
    assert compiled.rendered.output.schema_id == "scene_beats.fragment.v9"
    scene_properties = compiled.response_schema["properties"]["scenes"]["items"][
        "properties"
    ]
    assert "storyNodeId" not in compiled.response_schema["properties"]
    assert "storyNodeId" not in scene_properties
    assert "beatLocalIds" not in scene_properties
    assert "beatIds" not in scene_properties
    assert "localSceneId" in scene_properties
    assert "$defs" not in compiled.response_schema
    assert '"$ref"' not in str(compiled.response_schema)
    assert scene_properties["exitState"]["required"] == [
        "facts",
        "entityStates",
        "screenDirection",
        "lighting",
        "sound",
        "notes",
    ]
    assert compiled.contract.schema_hash
    assert compiled.contract.variables_hash == second.contract.variables_hash
    assert compiled.contract.rendered_hash == second.contract.rendered_hash


def test_prompt_contract_requires_complete_correction_schedule() -> None:
    compiled, _, _, _, _ = _compile_scene_beats()
    primary = compiled.contract.model_dump(mode="json")

    with pytest.raises(ValidationError, match="must be set together"):
        WorkUnitPromptContract.model_validate(
            {**primary, "correction_ordinal": 1}
        )

    with pytest.raises(ValidationError, match="must be set together"):
        WorkUnitPromptContract.model_validate(
            {**primary, "correction_strategy": "repair_previous_final"}
        )

    with pytest.raises(ValidationError, match="does not match"):
        WorkUnitPromptContract.model_validate(
            {
                **primary,
                "correction_ordinal": 1,
                "correction_strategy": "reconstruct_from_schema",
            }
        )


def test_scene_fragment_rejects_legacy_parent_ids_and_binds_metadata_only_after_validation() -> None:
    compiled, stage_plan, unit, _, _ = _compile_scene_beats()
    legacy_parent = _scene_output()
    legacy_parent["storyNodeId"] = "node-b"
    rejected = compiled.validator.validate(
        legacy_parent,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert rejected.accepted is False
    assert "schema.extra_forbidden" in {issue.code for issue in rejected.issues}

    nested_legacy_parent = _scene_output()
    nested_legacy_parent["scenes"][0]["storyNodeId"] = "node-b"
    nested_rejected = compiled.validator.validate(
        nested_legacy_parent,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert nested_rejected.accepted is False
    assert "schema.extra_forbidden" in {issue.code for issue in nested_rejected.issues}

    legacy_beat_list = _scene_output()
    legacy_beat_list["scenes"][0]["beatLocalIds"] = ["beat-node-a"]
    legacy_beat_list_rejected = compiled.validator.validate(
        legacy_beat_list,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert legacy_beat_list_rejected.accepted is False
    assert "schema.extra_forbidden" in {
        issue.code for issue in legacy_beat_list_rejected.issues
    }

    accepted = compiled.validator.validate(
        _scene_output(),
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert accepted.accepted is True
    assert isinstance(accepted.value, SceneBeatsFragment)
    assert accepted.value.stage_plan_hash == stage_plan.stage_plan_hash
    assert accepted.value.work_unit_id == unit.unit_id
    assert accepted.value.scenes[0].id != "scene-node-a"
    assert accepted.value.beats[0].id != "beat-node-a"
    assert accepted.value.scenes[0].beat_ids == [accepted.value.beats[0].id]
    assert accepted.value.beats[0].scene_id == accepted.value.scenes[0].id

    repeated = compiled.validator.validate(
        _scene_output(),
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert repeated.accepted is True
    assert repeated.value.scenes[0].id == accepted.value.scenes[0].id
    assert repeated.value.beats[0].id == accepted.value.beats[0].id


def test_scene_fragment_requires_at_least_one_beat_per_scene() -> None:
    compiled, _, _, _, _ = _compile_scene_beats()
    output = _scene_output()
    output["scenes"].append(
        {
            **output["scenes"][0],
            "localSceneId": "scene-empty",
            "title": "空场",
            "objective": "不能没有节拍",
        }
    )

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert "semantic.scene_without_beats" in {issue.code for issue in report.issues}


def test_scene_fragment_binding_namespaces_identical_model_ids_by_story_node() -> None:
    _, _, plan, bible, graph, _ = _plan_and_inputs()
    brief, snapshot, _, _, _, _ = _plan_and_inputs()
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    bound_ids: list[str] = []
    for unit in stage_plan.work_units:
        compiled = compile_work_unit_request(
            generation_plan=plan,
            stage_plan=stage_plan,
            work_unit=unit,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
            brief=brief,
            canonical_snapshot=snapshot,
            instructions="preserve the project brief",
        )
        report = compiled.validator.validate(
            _scene_output(),
            context=SemanticValidationContext(stage="scene_beats"),
        )
        assert report.accepted is True
        bound_ids.append(report.value.scenes[0].id)

    assert len(set(bound_ids)) == 2


def test_join_continuity_keys_are_explicit_in_schema_prompt_and_validation() -> None:
    brief, snapshot, plan, bible, _, _ = _plan_and_inputs()
    graph = StoryGraphV2(
        start_node_id="node-a",
        nodes=[
            StoryNodeV2(id="node-a", title="甲", summary="甲线", kind="start"),
            StoryNodeV2(id="node-c", title="乙", summary="乙线", kind="scene"),
            StoryNodeV2(id="node-b", title="汇流", summary="会合", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(id="edge-a-b", source_node_id="node-a", target_node_id="node-b", kind="choice", choice_text="直接汇流", state_effects={}),
            StoryEdgeV2(id="edge-a-c", source_node_id="node-a", target_node_id="node-c", kind="choice", choice_text="先走乙线", state_effects={}),
            StoryEdgeV2(id="edge-c-b", source_node_id="node-c", target_node_id="node-b", kind="continuation", choice_text=None, state_effects={}),
        ],
        join_contracts=[
            JoinContractV2(
                id="join-a-c-b",
                join_node_id="node-b",
                incoming_node_ids=["node-a", "node-c"],
                required_state_keys=["船钟归属"], allowed_differences=[], reconciliation="", notes="",
            )
        ],
    )
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    unit = next(item for item in stage_plan.work_units if item.selector.stable_id == "node-b")
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    entry_schema = compiled.response_schema["properties"]["scenes"]["items"][
        "properties"
    ]["entryState"]
    assert entry_schema["properties"]["facts"]["required"] == ["船钟归属"]
    assert '"requiredEntryFactKeys":["船钟归属"]' in compiled.rendered.messages[1].content

    output = _scene_output()
    missing = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert missing.accepted is False
    assert "schema.missing" in {issue.code for issue in missing.issues}

    output["scenes"][0]["entryState"]["facts"] = {"船钟归属": "由摆渡人保管"}
    accepted = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert accepted.accepted is True


def test_storyboard_fragment_uses_closed_primary_coverage_and_injects_scene() -> None:
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
    assert compiled.rendered.output.schema_id == "storyboard.fragment.v4"
    assert "sceneId" not in compiled.response_schema["properties"]
    assert "sceneId" not in compiled.response_schema["properties"]["shots"]["items"][
        "properties"
    ]
    assert compiled.response_schema["properties"]["supportingBeatLinks"]["items"][
        "properties"
    ]["beatId"]["enum"] == ["beat-node-a"]
    primary_schema = compiled.response_schema["properties"]["primaryShotLocalIdByBeat"]
    assert primary_schema["required"] == ["beat-node-a"]
    assert primary_schema["additionalProperties"] is False
    assert compiled.response_schema["required"] == [
        "shots",
        "primaryShotLocalIdByBeat",
        "supportingBeatLinks",
    ]
    assert compiled.response_schema["properties"]["shots"]["minItems"] == 1
    assert compiled.response_schema["properties"]["shots"]["maxItems"] == 2
    assert "shotsPerSceneMin/shotsPerSceneMax" in compiled.rendered.messages[1].content
    output = _storyboard_output(beat_ids=["beat-node-a", "beat-node-b"])
    rejected = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert rejected.accepted is False
    assert "semantic.primary_coverage" in {issue.code for issue in rejected.issues}

    output["primaryShotLocalIdByBeat"] = {"beat-node-a": "shot-a"}
    accepted = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert accepted.accepted is True
    assert isinstance(accepted.value, StoryboardFragment)
    assert accepted.value.shots[0].id != "shot-a"
    assert accepted.value.shot_beat_links[0].shot_id == accepted.value.shots[0].id
    assert accepted.value.shots[0].scene_id == "scene-node-a"

    legacy_shot_parent = _storyboard_output(beat_ids=["beat-node-a"])
    legacy_shot_parent["shots"][0]["sceneId"] = "scene-node-a"
    legacy_shot_rejected = compiled.validator.validate(
        legacy_shot_parent,
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert legacy_shot_rejected.accepted is False
    assert "schema.extra_forbidden" in {issue.code for issue in legacy_shot_rejected.issues}


def test_storyboard_fragment_binding_namespaces_identical_local_shot_ids_by_scene() -> None:
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
    bound_ids: list[str] = []
    dependencies = {
        StageName.STORY_BIBLE: bible,
        StageName.STORY_GRAPH: graph,
        StageName.SCENE_BEATS: scene_beats,
    }
    for unit in stage_plan.work_units:
        compiled = compile_work_unit_request(
            generation_plan=plan,
            stage_plan=stage_plan,
            work_unit=unit,
            dependencies=dependencies,
            brief=brief,
            canonical_snapshot=snapshot,
            instructions="preserve the project brief",
        )
        scene = next(item for item in scene_beats.scenes if item.id == unit.selector.stable_id)
        beat_id = scene.beat_ids[0]
        output = _storyboard_output(beat_ids=[beat_id], local_shot_id="local-shot-1")
        report = compiled.validator.validate(
            output,
            context=SemanticValidationContext(stage="storyboard"),
        )
        assert report.accepted is True
        bound_ids.append(report.value.shots[0].id)
        assert report.value.shot_beat_links[0].shot_id == report.value.shots[0].id

    assert len(set(bound_ids)) == len(bound_ids) == 2


def test_storyboard_primary_map_closes_three_beats_with_one_shot_and_supporting_is_secondary() -> None:
    brief, snapshot, plan, bible, graph, scene_beats = _plan_and_inputs()
    first_scene = scene_beats.scenes[0].model_copy(
        update={"beat_ids": ["beat-node-a", "beat-node-a-2", "beat-node-a-3"]}
    )
    expanded_beats = SceneBeatPlanV2(
        scenes=[first_scene, *scene_beats.scenes[1:]],
        beats=[
            scene_beats.beats[0],
                BeatV2(id="beat-node-a-2", scene_id=first_scene.id, order=2, description="警报加速。", purpose="升级风险", visible_event="", immediate_result="", dramatic_change="", entry_state=_state(), exit_state=_state(), continuity_anchors=[], continuity_delta={}),
                BeatV2(id="beat-node-a-3", scene_id=first_scene.id, order=3, description="她做出决定。", purpose="完成转折", visible_event="", immediate_result="", dramatic_change="", entry_state=_state(), exit_state=_state(), continuity_anchors=[], continuity_delta={}),
            *scene_beats.beats[1:],
        ], dialogue_cues=[],
    )
    stage_plan = plan_stage(
        plan,
        stage=StageName.STORYBOARD,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph, StageName.SCENE_BEATS: expanded_beats},
    )
    unit = stage_plan.work_units[0]
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph, StageName.SCENE_BEATS: expanded_beats},
        brief=brief.model_copy(update={"shots_per_scene_min": 1, "shots_per_scene_max": 1}),
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    beat_ids = first_scene.beat_ids
    one_shot = _storyboard_output(beat_ids=beat_ids)
    accepted = compiled.validator.validate(one_shot, context=SemanticValidationContext(stage="storyboard"))
    assert accepted.accepted is True
    assert len(accepted.value.shots) == 1
    assert [link.beat_id for link in accepted.value.shot_beat_links if link.role == "primary"] == sorted(beat_ids)
    assert {link.shot_id for link in accepted.value.shot_beat_links if link.role == "primary"} == {accepted.value.shots[0].id}

    missing = _storyboard_output(beat_ids=beat_ids[:-1])
    missing_report = compiled.validator.validate(missing, context=SemanticValidationContext(stage="storyboard"))
    assert missing_report.accepted is False
    assert "schema.missing" in {issue.code for issue in missing_report.issues}

    unknown_local = _storyboard_output(beat_ids=beat_ids)
    unknown_local["primaryShotLocalIdByBeat"][beat_ids[0]] = "unknown-shot"
    unknown_report = compiled.validator.validate(unknown_local, context=SemanticValidationContext(stage="storyboard"))
    assert unknown_report.accepted is False
    assert "semantic.unknown_link_shot" in {issue.code for issue in unknown_report.issues}

    two_shots = StoryboardFragmentOutput(
        shots=[
            ShotContent(local_shot_id="shot-a", order=1, title="苏醒", shot_size="close_up", duration_units=2, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=[], audio_plan=AudioPlan(events=[]), character_ids=[], location_id=None, prop_ids=[], required_entity_states=[], entry_state=_state(), exit_state=_state()),
            ShotContent(local_shot_id="shot-b", order=2, title="反应", shot_size="medium", duration_units=2, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=[], audio_plan=AudioPlan(events=[]), character_ids=[], location_id=None, prop_ids=[], required_entity_states=[], entry_state=_state(), exit_state=_state()),
        ],
        primary_shot_local_id_by_beat={beat_id: "shot-a" for beat_id in beat_ids},
        supporting_beat_links=[{"shotLocalId": "shot-b", "beatId": beat_ids[-1], "coverageWeight": 1.0}],
    ).model_dump(mode="json", by_alias=True)
    two_shot_compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph, StageName.SCENE_BEATS: expanded_beats},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    supporting_report = two_shot_compiled.validator.validate(two_shots, context=SemanticValidationContext(stage="storyboard"))
    assert supporting_report.accepted is True
    links = supporting_report.value.shot_beat_links
    assert sum(link.role == "primary" for link in links) == 3
    assert sum(link.role == "supporting" for link in links) == 1


def test_compiler_rejects_non_frozen_snapshot_or_context() -> None:
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    brief, snapshot, plan, _, _, _ = _plan_and_inputs()
    with pytest.raises(WorkUnitContractError, match="timing allocation"):
        compile_work_unit_request(
            generation_plan=plan,
            stage_plan=stage_plan,
            work_unit=unit,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
            brief=brief.model_copy(update={"target_playthrough_seconds": 181}),
            canonical_snapshot=snapshot,
            instructions="preserve the project brief",
        )
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
