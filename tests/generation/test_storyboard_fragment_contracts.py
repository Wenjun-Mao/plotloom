"""test storyboard fragment contracts behavior contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.domain import BeatV2, SceneBeatPlanV2, StageName
from plotloom.generation.fragments import StoryboardFragment
from plotloom.generation.planning import plan_stage
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    AUDIO_EVENT_ID_BINDING_VERSION,
    ShotContent,
    StoryboardFragmentOutput,
    WorkUnitPromptContract,
    canonical_audio_event_id,
    compile_work_unit_request,
)
from tests.generation.work_unit_contract_fixtures import (
    _plan_and_inputs,
    _state,
    _storyboard_output,
)


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
    assert compiled.rendered.output.schema_id == "storyboard.fragment.v6"
    assert compiled.contract.audio_event_id_binding_version == (
        AUDIO_EVENT_ID_BINDING_VERSION
    )
    assert "所有 shots 的 durationUnits 总和" in compiled.rendered.messages[1].content
    assert (
        "beat.order、再按该 beat 内 cue.order" in compiled.rendered.messages[1].content
    )
    assert "实体必须实际出现在同一 shot" in compiled.rendered.messages[1].content
    assert "sceneId" not in compiled.response_schema["properties"]
    assert (
        "sceneId"
        not in compiled.response_schema["properties"]["shots"]["items"]["properties"]
    )
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
    assert "schema.extra_forbidden" in {
        issue.code for issue in legacy_shot_rejected.issues
    }


def test_storyboard_audio_event_ids_are_deterministic_and_contracts_reject_retired_history() -> (
    None
):
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
    output = _storyboard_output(beat_ids=["beat-node-a"])
    output["shots"][0]["audioPlan"] = {
        "events": [
            {
                "kind": "ambience",
                "description": "低沉的舱内嗡鸣",
                "startOffsetUnits": 0,
                "durationUnits": 1,
            }
        ]
    }
    first = compiled.validator.validate(
        output, context=SemanticValidationContext(stage="storyboard")
    )
    second = compiled.validator.validate(
        output, context=SemanticValidationContext(stage="storyboard")
    )
    assert first.accepted and second.accepted
    shot = first.value.shots[0]
    assert shot.audio_plan.events[0].id == canonical_audio_event_id(shot.id, 1)
    assert second.value.shots[0].audio_plan.events[0].id == shot.audio_plan.events[0].id

    retired = compiled.contract.snapshot_dump()
    retired["contract_version"] = "m1.12j"
    with pytest.raises(ValidationError, match="unsupported work-unit prompt"):
        WorkUnitPromptContract.model_validate(retired)


def test_storyboard_fragment_binding_namespaces_identical_local_shot_ids_by_scene() -> (
    None
):
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
        scene = next(
            item for item in scene_beats.scenes if item.id == unit.selector.stable_id
        )
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


def test_storyboard_primary_map_closes_three_beats_with_one_shot_and_supporting_is_secondary() -> (
    None
):
    brief, snapshot, plan, bible, graph, scene_beats = _plan_and_inputs()
    first_scene = scene_beats.scenes[0].model_copy(
        update={"beat_ids": ["beat-node-a", "beat-node-a-2", "beat-node-a-3"]}
    )
    expanded_beats = SceneBeatPlanV2(
        scenes=[first_scene, *scene_beats.scenes[1:]],
        beats=[
            scene_beats.beats[0],
            BeatV2(
                id="beat-node-a-2",
                scene_id=first_scene.id,
                order=2,
                description="警报加速。",
                purpose="升级风险",
                visible_event="",
                immediate_result="",
                dramatic_change="",
                entry_state=_state(),
                exit_state=_state(),
                continuity_anchors=[],
                continuity_delta={},
            ),
            BeatV2(
                id="beat-node-a-3",
                scene_id=first_scene.id,
                order=3,
                description="她做出决定。",
                purpose="完成转折",
                visible_event="",
                immediate_result="",
                dramatic_change="",
                entry_state=_state(),
                exit_state=_state(),
                continuity_anchors=[],
                continuity_delta={},
            ),
            *scene_beats.beats[1:],
        ],
        dialogue_cues=[],
    )
    stage_plan = plan_stage(
        plan,
        stage=StageName.STORYBOARD,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
            StageName.SCENE_BEATS: expanded_beats,
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
            StageName.SCENE_BEATS: expanded_beats,
        },
        brief=brief.model_copy(
            update={"shots_per_scene_min": 1, "shots_per_scene_max": 1}
        ),
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    beat_ids = first_scene.beat_ids
    one_shot = _storyboard_output(beat_ids=beat_ids)
    accepted = compiled.validator.validate(
        one_shot, context=SemanticValidationContext(stage="storyboard")
    )
    assert accepted.accepted is True
    assert len(accepted.value.shots) == 1
    assert [
        link.beat_id
        for link in accepted.value.shot_beat_links
        if link.role == "primary"
    ] == sorted(beat_ids)
    assert {
        link.shot_id
        for link in accepted.value.shot_beat_links
        if link.role == "primary"
    } == {accepted.value.shots[0].id}

    missing = _storyboard_output(beat_ids=beat_ids[:-1])
    missing_report = compiled.validator.validate(
        missing, context=SemanticValidationContext(stage="storyboard")
    )
    assert missing_report.accepted is False
    assert "schema.missing" in {issue.code for issue in missing_report.issues}

    unknown_local = _storyboard_output(beat_ids=beat_ids)
    unknown_local["primaryShotLocalIdByBeat"][beat_ids[0]] = "unknown-shot"
    unknown_report = compiled.validator.validate(
        unknown_local, context=SemanticValidationContext(stage="storyboard")
    )
    assert unknown_report.accepted is False
    assert "semantic.unknown_link_shot" in {
        issue.code for issue in unknown_report.issues
    }

    two_shots = StoryboardFragmentOutput(
        shots=[
            ShotContent(
                local_shot_id="shot-a",
                order=1,
                title="苏醒",
                shot_size="close_up",
                duration_units=1,
                camera_angle="",
                camera_movement="",
                composition="",
                visual_intent="",
                motion_intent="",
                action="",
                transition="",
                cue_ids=[],
                audio_plan={"events": []},
                character_ids=[],
                location_id=None,
                prop_ids=[],
                required_entity_states=[],
                entry_state=_state(),
                exit_state=_state(),
            ),
            ShotContent(
                local_shot_id="shot-b",
                order=2,
                title="反应",
                shot_size="medium",
                duration_units=1,
                camera_angle="",
                camera_movement="",
                composition="",
                visual_intent="",
                motion_intent="",
                action="",
                transition="",
                cue_ids=[],
                audio_plan={"events": []},
                character_ids=[],
                location_id=None,
                prop_ids=[],
                required_entity_states=[],
                entry_state=_state(),
                exit_state=_state(),
            ),
        ],
        primary_shot_local_id_by_beat={beat_id: "shot-a" for beat_id in beat_ids},
        supporting_beat_links=[
            {"shotLocalId": "shot-b", "beatId": beat_ids[-1], "coverageWeight": 1.0}
        ],
    ).model_dump(mode="json", by_alias=True)
    two_shot_compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
            StageName.SCENE_BEATS: expanded_beats,
        },
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    supporting_report = two_shot_compiled.validator.validate(
        two_shots, context=SemanticValidationContext(stage="storyboard")
    )
    assert supporting_report.accepted is True
    links = supporting_report.value.shot_beat_links
    assert sum(link.role == "primary" for link in links) == 3
    assert sum(link.role == "supporting" for link in links) == 1
