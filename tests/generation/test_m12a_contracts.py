from __future__ import annotations

import pytest

from plotloom.domain import (
    BeatV2,
    CharacterV2,
    ContinuityStateV2,
    DialogueCue,
    DramaticSceneV2,
    ProjectBrief,
    PropV2,
    SceneBeatPlanV2,
    StageName,
    StoryBibleV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    BeatContent,
    DialogueCueContent,
    DramaticSceneContent,
    SceneBeatsFragmentOutput,
    ShotContent,
    StoryboardFragmentOutput,
    compile_work_unit_request,
    dialogue_timing_repair_facts,
)


def _state() -> ContinuityStateV2:
    return ContinuityStateV2(
        facts={}, entity_states=[], screen_direction=None, lighting=None, sound=None, notes=[]
    )


def _inputs() -> tuple[ProjectBrief, StoryBibleV2, StoryGraphV2, SceneBeatPlanV2, dict]:
    brief = ProjectBrief(
        title="V2", synopsis="cue contract", ending_count=1, decision_points_per_path=0,
        desired_join_count=0, node_budget=1, shots_per_scene_min=1, shots_per_scene_max=2,
    )
    bible = StoryBibleV2(
        logline="l", premise="p", genre="", tone="", audience="", narrative_promise="",
        visual_language="", themes=[], world_rules=[], known_facts=[], open_questions=[], source_notes=[],
        characters=[CharacterV2(id="speaker", name="说话者", description="", visual_anchors=[], sound_anchors=[], allowed_states=["awake"], continuity_rules=[], role=None, goal="", traits=[], voice_anchors=[])],
        locations=[],
        props=[PropV2(id="prop", name="道具", description="", visual_anchors=[], sound_anchors=[], allowed_states=["intact"], continuity_rules=[])],
    )
    graph = StoryGraphV2(start_node_id="node", nodes=[StoryNodeV2(id="node", title="节点", summary="概要", kind="start")], edges=[], join_contracts=[])
    state = _state()
    scene = DramaticSceneV2(id="scene", story_node_id="node", order=1, title="场", objective="目标", location_id=None, character_ids=["speaker"], beat_ids=["beat"], duration_budget_units=660, entry_state=state, exit_state=state)
    beat = BeatV2(id="beat", scene_id="scene", order=1, description="动作", purpose="推进", visible_event="", immediate_result="", dramatic_change="", entry_state=state, exit_state=state, continuity_anchors=[], continuity_delta={})
    cue = DialogueCue(id="cue", beat_id="beat", order=1, speaker_id="speaker", voice_over=None, text="继续", language="zh-CN", delivery="natural", performance_notes="平静", estimated_duration_units=660)
    return brief, bible, graph, SceneBeatPlanV2(scenes=[scene], beats=[beat], dialogue_cues=[cue]), {"brief": brief.model_dump(mode="json", by_alias=True)}


def _compiled(stage: StageName):
    brief, bible, graph, scene_beats, snapshot = _inputs()
    plan = create_generation_plan(run_id="m12a", requested_stages=list(StageName), provider_profile_hash="p", canonical_snapshot=snapshot)
    dependencies = {StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph}
    if stage == StageName.STORYBOARD:
        dependencies[StageName.SCENE_BEATS] = scene_beats
    stage_plan = plan_stage(plan, stage=stage, dependencies=dependencies)
    return compile_work_unit_request(generation_plan=plan, stage_plan=stage_plan, work_unit=stage_plan.work_units[0], dependencies=dependencies, brief=brief, canonical_snapshot=snapshot)


def _scene_output(*, speaker_id: str = "speaker") -> dict:
    state = _state()
    return SceneBeatsFragmentOutput(
        scenes=[DramaticSceneContent(local_scene_id="s", order=1, title="场", objective="目标", location_id=None, character_ids=["speaker"], duration_budget_units=660, entry_state=state, exit_state=state)],
        beats=[BeatContent(local_beat_id="b", scene_local_id="s", order=1, description="动作", purpose="推进", visible_event="", immediate_result="", dramatic_change="", entry_state=state, exit_state=state, continuity_anchors=[], continuity_delta={})],
        dialogue_cues=[DialogueCueContent(local_cue_id="q", beat_local_id="b", order=1, speaker_id=speaker_id, voice_over=None, text="继续", language="zh-CN", delivery="natural", performance_notes="平静", estimated_duration_units=660)],
    ).model_dump(mode="json", by_alias=True)


def _board_output(*, cue_ids: list[str] | None = None, audio_duration: int = 660, state: str = "awake") -> dict:
    continuity = _state()
    return StoryboardFragmentOutput(
        shots=[ShotContent(local_shot_id="shot", order=1, title="镜头", shot_size="medium", duration_units=660, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=cue_ids or ["cue"], audio_plan={"events": [{"id": "amb", "kind": "ambience", "description": "低鸣", "startOffsetUnits": 0, "durationUnits": audio_duration}]}, character_ids=["speaker"], location_id=None, prop_ids=[], required_entity_states=[{"entityType": "character", "entityId": "speaker", "state": state}], entry_state=continuity, exit_state=continuity)],
        primary_shot_local_id_by_beat={"beat": "shot"}, supporting_beat_links=[],
    ).model_dump(mode="json", by_alias=True)


def test_m12a_scene_prompt_schema_and_binder_create_authoritative_cues() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    assert compiled.rendered.output.schema_id == "scene_beats.fragment.v5"
    assert compiled.contract.contract_version == "m1.12b"
    assert "dialogueCues" in compiled.response_schema["properties"]
    assert '"dialogue"' not in str(compiled.response_schema)
    assert '"version":"dialogue.default.v1"' in compiled.rendered.messages[1].content
    assert '"unitsPerCharacter":330' in compiled.rendered.messages[1].content
    report = compiled.validator.validate(_scene_output(), context=SemanticValidationContext(stage="scene_beats"))
    assert report.accepted and report.value.dialogue_cues[0].beat_id == report.value.beats[0].id


def test_m12a_scene_fragment_rejects_blank_voice_over_and_underestimated_timing() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    blank_voice_over = _scene_output()
    blank_voice_over["dialogueCues"][0].update(
        {"speakerId": None, "voiceOver": "   "}
    )
    blank_report = compiled.validator.validate(
        blank_voice_over,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert blank_report.accepted is False
    assert any(issue.path[-1] == "voiceOver" for issue in blank_report.issues)

    understated = _scene_output()
    understated["dialogueCues"][0]["estimatedDurationUnits"] = 659
    timing_report = compiled.validator.validate(
        understated,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert timing_report.accepted is False
    timing_issue = next(
        issue
        for issue in timing_report.issues
        if issue.code == "semantic.cue_duration_underestimated"
    )
    assert timing_issue.path == ("dialogueCues", 0, "estimatedDurationUnits")


@pytest.mark.parametrize("field", ("text", "language"))
def test_m12a_scene_fragment_rejects_whitespace_only_dialogue_fields(field: str) -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0][field] = "   "

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert any(
        issue.code == "schema.too_short"
        and issue.path == ("dialogueCues", 0, field)
        for issue in report.issues
    )


def test_m12a_local_cue_handle_does_not_require_a_canonical_stable_id() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    # Response-local handles are correlation keys only.  The trusted binder
    # derives the canonical cue UUID from the bound beat and cue order.
    output["dialogueCues"][0]["localCueId"] = "not a stable id"

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is True
    assert report.value.dialogue_cues[0].id != "not a stable id"


def test_m12a_dialogue_timing_repair_facts_are_derived_and_expose_budget_conflict() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    understated = _scene_output()
    understated["dialogueCues"][0]["estimatedDurationUnits"] = 500
    understated["scenes"][0]["durationBudgetUnits"] = 600
    report = compiled.validator.validate(
        understated,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    facts = dialogue_timing_repair_facts(understated, report.issues)

    assert report.accepted is False
    assert len(facts) == 1
    assert facts[0].model_dump(mode="json", by_alias=True) == {
        "code": "semantic.cue_duration_underestimated",
        "path": ["dialogueCues", 0, "estimatedDurationUnits"],
        "timingProfileVersion": "dialogue.default.v1",
        "matchedRuleLanguage": "zh-CN",
        "delivery": "natural",
        "textCharacterCount": 2,
        "unitsPerCharacter": 330,
        "minimumDurationUnits": 660,
        "currentEstimatedDurationUnits": 500,
        "sceneDurationBudgetUnits": 600,
        "sceneCueEstimatedTotalUnits": 500,
        "sceneCueMinimumTotalUnits": 660,
        "minimumFitsSceneBudget": False,
    }
    serialized = facts[0].model_dump(mode="json", by_alias=True)
    assert "text" not in serialized
    assert "message" not in serialized


def test_m12a_dialogue_timing_repair_facts_require_a_parseable_cue() -> None:
    facts = dialogue_timing_repair_facts(
        {"dialogueCues": []},
        (),
    )
    assert facts == ()


def test_m12a_timing_fact_keeps_cue_minimum_when_scene_is_unresolved() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0]["beatLocalId"] = "unknown-beat"
    output["dialogueCues"][0]["estimatedDurationUnits"] = 1
    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert {issue.code for issue in report.issues} >= {
        "semantic.cross_unit_cue",
        "semantic.cue_duration_underestimated",
    }
    facts = dialogue_timing_repair_facts(output, report.issues)
    assert len(facts) == 1
    assert facts[0].minimum_duration_units == 660
    assert facts[0].scene_duration_budget_units is None
    assert facts[0].scene_cue_estimated_total_units is None
    assert facts[0].scene_cue_minimum_total_units is None
    assert facts[0].minimum_fits_scene_budget is None


def test_m12a_timing_fact_omits_scene_claims_for_duplicate_local_ids() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0]["estimatedDurationUnits"] = 1
    output["beats"].append({**output["beats"][0]})
    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert {issue.code for issue in report.issues} >= {
        "semantic.duplicate_beat_id",
        "semantic.cue_duration_underestimated",
    }
    facts = dialogue_timing_repair_facts(output, report.issues)
    assert len(facts) == 1
    assert facts[0].minimum_duration_units == 660
    assert facts[0].scene_duration_budget_units is None
    assert facts[0].minimum_fits_scene_budget is None


def test_m12a_rejects_illegal_speaker_and_cue_schedule_references() -> None:
    scene = _compiled(StageName.SCENE_BEATS)
    bad_speaker = scene.validator.validate(_scene_output(speaker_id="invented"), context=SemanticValidationContext(stage="scene_beats"))
    assert "semantic.unknown_cue_speaker" in {issue.code for issue in bad_speaker.issues}

    board = _compiled(StageName.STORYBOARD)
    unknown = board.validator.validate(_board_output(cue_ids=["invented"]), context=SemanticValidationContext(stage="storyboard"))
    assert "semantic.unknown_cue_ref" in {issue.code for issue in unknown.issues}
    duplicate = board.validator.validate(_board_output(cue_ids=["cue", "cue"]), context=SemanticValidationContext(stage="storyboard"))
    assert "semantic.duplicate_cue_ref" in {issue.code for issue in duplicate.issues}


def test_m12a_rejects_duplicate_canonical_entity_references_before_binding() -> None:
    scene = _compiled(StageName.SCENE_BEATS)
    duplicate_scene_character = _scene_output()
    duplicate_scene_character["scenes"][0]["characterIds"] = ["speaker", "speaker"]
    scene_report = scene.validator.validate(
        duplicate_scene_character,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert scene_report.accepted is False
    assert any(
        issue.code == "semantic.duplicate_character_ref"
        and issue.path == ("scenes", 0, "characterIds")
        for issue in scene_report.issues
    )

    board = _compiled(StageName.STORYBOARD)
    for field, expected_code in (
        ("characterIds", "semantic.duplicate_character_ref"),
        ("propIds", "semantic.duplicate_prop_ref"),
    ):
        output = _board_output()
        output["shots"][0][field] = ["speaker", "speaker"] if field == "characterIds" else ["prop", "prop"]
        report = board.validator.validate(
            output,
            context=SemanticValidationContext(stage="storyboard"),
        )
        assert report.accepted is False
        assert any(
            issue.code == expected_code
            and issue.path == ("shots", 0, field)
            for issue in report.issues
        )


def test_m12a_rejects_audio_timing_and_unavailable_entity_state() -> None:
    board = _compiled(StageName.STORYBOARD)
    timing = board.validator.validate(_board_output(audio_duration=661), context=SemanticValidationContext(stage="storyboard"))
    assert "semantic.audio_timing" in {issue.code for issue in timing.issues}
    entity = board.validator.validate(_board_output(state="asleep"), context=SemanticValidationContext(stage="storyboard"))
    assert "semantic.invalid_required_entity_state" in {issue.code for issue in entity.issues}


def test_m12a_storyboard_fragment_rejects_legacy_raw_dialogue_and_audio() -> None:
    board = _compiled(StageName.STORYBOARD)
    for legacy_field in ("dialogue", "audio"):
        output = _board_output()
        output["shots"][0][legacy_field] = "legacy free text"
        report = board.validator.validate(
            output,
            context=SemanticValidationContext(stage="storyboard"),
        )
        assert report.accepted is False
        assert "schema.extra_forbidden" in {issue.code for issue in report.issues}
