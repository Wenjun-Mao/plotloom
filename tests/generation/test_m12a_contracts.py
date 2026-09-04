from __future__ import annotations

import pytest

import plotloom.generation.planning as generation_planning
from plotloom.domain import (
    BeatV2,
    CharacterV2,
    ContinuityStateV2,
    DialogueCue,
    DialogueDeliveryPace,
    DialogueTimingProfile,
    DialogueTimingRule,
    DramaticSceneV2,
    ProjectBrief,
    PropV2,
    SceneBeatPlanV2,
    StageName,
    StoryBibleV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    BeatContent,
    DialogueCueContent,
    DialogueCapacityRepairFact,
    DramaticSceneContent,
    RequiredEntityStateRepairFact,
    SceneBeatsFragmentOutput,
    ShotContent,
    StoryboardFragmentOutput,
    compile_work_unit_request,
    scene_beats_dialogue_capacity_repair_facts,
    storyboard_required_entity_state_repair_facts,
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
    graph = StoryGraphV2(
        start_node_id="node",
        nodes=[
            StoryNodeV2(id="node", title="节点", summary="概要", kind="start"),
            StoryNodeV2(id="ending", title="结局", summary="完成", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(
                id="node-ending",
                source_node_id="node",
                target_node_id="ending",
                kind="continuation",
                choice_text=None,
                state_effects={},
            )
        ],
        join_contracts=[],
    )
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
    stage_plan = plan_stage(plan, stage=stage, dependencies=dependencies, brief=brief)
    return compile_work_unit_request(generation_plan=plan, stage_plan=stage_plan, work_unit=stage_plan.work_units[0], dependencies=dependencies, brief=brief, canonical_snapshot=snapshot)


def _authoring_only_timing_profile() -> DialogueTimingProfile:
    return DialogueTimingProfile(
        version="dialogue.zh-cn-only.v1",
        rules=[
            DialogueTimingRule(
                language="zh-CN",
                delivery=delivery,
                units_per_character=330,
            )
            for delivery in DialogueDeliveryPace
        ],
    )


def _scene_output(*, speaker_id: str = "speaker") -> dict:
    state = _state()
    return SceneBeatsFragmentOutput(
        scenes=[DramaticSceneContent(local_scene_id="s", order=1, title="场", objective="目标", location_id=None, character_ids=["speaker"], duration_weight=1, entry_state=state, exit_state=state)],
        beats=[BeatContent(local_beat_id="b", scene_local_id="s", order=1, description="动作", purpose="推进", visible_event="", immediate_result="", dramatic_change="", entry_state=state, exit_state=state, continuity_anchors=[], continuity_delta={})],
        dialogue_cues=[DialogueCueContent(local_cue_id="q", beat_local_id="b", order=1, speaker_id=speaker_id, voice_over=None, text="继续", language="zh-CN", delivery="natural", performance_notes="平静")],
    ).model_dump(mode="json", by_alias=True)


def _board_output(*, cue_ids: list[str] | None = None, audio_duration: int = 660, state: str = "awake") -> dict:
    continuity = _state()
    return StoryboardFragmentOutput(
        shots=[ShotContent(local_shot_id="shot", order=1, title="镜头", shot_size="medium", duration_units=660, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=cue_ids or ["cue"], audio_plan={"events": [{"id": "amb", "kind": "ambience", "description": "低鸣", "startOffsetUnits": 0, "durationUnits": audio_duration}]}, character_ids=["speaker"], location_id=None, prop_ids=[], required_entity_states=[{"entityType": "character", "entityId": "speaker", "state": state}], entry_state=continuity, exit_state=continuity)],
        primary_shot_local_id_by_beat={"beat": "shot"}, supporting_beat_links=[],
    ).model_dump(mode="json", by_alias=True)


def test_m12a_scene_prompt_schema_and_binder_create_authoritative_cues() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    assert compiled.rendered.output.schema_id == "scene_beats.fragment.v9"
    assert compiled.contract.contract_version == "m1.12h"
    assert "dialogueCues" in compiled.response_schema["properties"]
    assert '"dialogue"' not in str(compiled.response_schema)
    cue_schema = compiled.response_schema["properties"]["dialogueCues"]["items"]
    scene_schema = compiled.response_schema["properties"]["scenes"]["items"]
    assert "estimatedDurationUnits" not in cue_schema["properties"]
    assert "estimatedDurationUnits" not in cue_schema["required"]
    assert "durationBudgetUnits" not in scene_schema["properties"]
    assert "durationWeight" in scene_schema["required"]
    assert compiled.contract.dialogue_timing_profile_version == "dialogue.default.v1"
    assert compiled.contract.dialogue_timing_profile_hash
    assert compiled.contract.scene_timing_allocation_version == "scene_timing_allocation.v1"
    assert compiled.contract.scene_timing_allocation_hash
    assert compiled.contract.node_duration_budget_units == 90_000
    assert compiled.contract.dialogue_capacity_policy_version == "dialogue_capacity.v2"
    assert compiled.contract.dialogue_capacity_plan_hash
    assert compiled.contract.dialogue_capacity_guidance is not None
    assert compiled.contract.dialogue_capacity_guidance.max_scenes == 2
    assert compiled.contract.dialogue_capacity_guidance.max_dialogue_cues == 2
    assert compiled.contract.dialogue_capacity_guidance.authoring_language == "zh-CN"
    assert compiled.contract.dialogue_capacity_guidance.schema_max_text_codepoints == 107
    assert compiled.response_schema["properties"]["scenes"]["maxItems"] == 2
    assert compiled.response_schema["properties"]["dialogueCues"]["maxItems"] == 2
    assert cue_schema["properties"]["language"] == {"type": "string", "const": "zh-CN"}
    assert cue_schema["properties"]["text"]["maxLength"] == 107
    assert "本节点冻结对白容量" in compiled.rendered.messages[1].content
    report = compiled.validator.validate(_scene_output(), context=SemanticValidationContext(stage="scene_beats"))
    assert report.accepted
    assert report.value.dialogue_cues[0].beat_id == report.value.beats[0].id
    assert report.value.dialogue_cues[0].estimated_duration_units == 660


def test_m12a_wrong_cue_language_is_semantic_feedback_without_wildcard_timing_rule(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        generation_planning,
        "default_dialogue_timing_profile",
        _authoring_only_timing_profile,
    )
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0]["language"] = "fr-FR"

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert [(issue.code, issue.path) for issue in report.issues] == [
        (
            "semantic.dialogue_language_not_authoring_language",
            ("dialogueCues", 0, "language"),
        )
    ]
    guidance = compiled.contract.dialogue_capacity_guidance
    assert guidance is not None
    assert scene_beats_dialogue_capacity_repair_facts(
        output,
        report.issues,
        guidance=guidance,
    ) == ()


def test_m12a_scene_capacity_fact_is_exact_and_fail_closed() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0]["text"] = "长" * 108
    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    guidance = compiled.contract.dialogue_capacity_guidance
    assert guidance is not None
    facts = scene_beats_dialogue_capacity_repair_facts(
        output,
        report.issues,
        guidance=guidance,
    )
    assert len(facts) == 1
    fact = facts[0]
    assert isinstance(fact, DialogueCapacityRepairFact)
    assert fact.path == ("dialogueCues", 0, "text")
    assert fact.current_text_codepoints == 108
    assert fact.max_text_codepoints == 107
    assert {item.delivery.value for item in fact.compatible_delivery_limits} == {
        "measured", "natural", "brisk"
    }

    malformed = _scene_output()
    malformed["dialogueCues"][0].pop("text")
    assert scene_beats_dialogue_capacity_repair_facts(
        malformed,
        report.issues,
        guidance=guidance,
    ) == ()


def test_m12a_schema_disables_cues_for_zero_portable_capacity() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    guidance = compiled.contract.dialogue_capacity_guidance
    assert guidance is not None
    compiled.validator.dialogue_capacity_guidance = guidance.model_copy(
        update={"schema_max_text_codepoints": 0}
    )

    schema = compiled.validator.json_schema()

    assert schema["properties"]["dialogueCues"]["maxItems"] == 0


def test_m12a_scene_fragment_rejects_blank_voice_over() -> None:
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


def test_m12a_scene_fragment_rejects_model_authored_timing() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0]["estimatedDurationUnits"] = 1

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert any(
        issue.code == "schema.extra_forbidden"
        and issue.path == ("dialogueCues", 0, "estimatedDurationUnits")
        for issue in report.issues
    )


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


def test_m12a_binder_derives_dialogue_and_frozen_node_budget() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    understated = _scene_output()
    understated["scenes"][0]["durationWeight"] = 1
    report = compiled.validator.validate(
        understated,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is True
    assert report.value.dialogue_cues[0].estimated_duration_units == 660
    assert report.value.scenes[0].duration_budget_units == 90_000


def test_m12a_binder_partitions_node_budget_by_scene_weight_and_dialogue_floor() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["scenes"][0]["durationWeight"] = 1
    output["scenes"].append(
        {
            **output["scenes"][0],
            "localSceneId": "s2",
            "order": 2,
            "title": "第二场",
            "durationWeight": 3,
        }
    )
    output["beats"].append(
        {
            **output["beats"][0],
            "localBeatId": "b2",
            "sceneLocalId": "s2",
        }
    )

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is True
    budgets = [scene.duration_budget_units for scene in report.value.scenes]
    assert sum(budgets) == 90_000
    assert budgets[0] >= 660
    assert budgets[1] > budgets[0]


def test_m12a_rejects_dialogue_that_cannot_fit_frozen_node_budget() -> None:
    compiled = _compiled(StageName.SCENE_BEATS)
    output = _scene_output()
    output["dialogueCues"][0]["text"] = "长" * 300

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert "semantic.dialogue_cue_capacity_exceeded" in {
        issue.code for issue in report.issues
    }


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


def test_m12a_invalid_entity_state_projects_only_frozen_allowed_choices() -> None:
    _, bible, _, _, _ = _inputs()
    board = _compiled(StageName.STORYBOARD)
    output = _board_output(state="asleep")
    report = board.validator.validate(
        output,
        context=SemanticValidationContext(stage="storyboard"),
    )

    facts = storyboard_required_entity_state_repair_facts(
        output,
        report.issues,
        bible=bible,
    )

    assert facts == (
        RequiredEntityStateRepairFact(
            code="semantic.invalid_required_entity_state",
            path=("shots", 0, "requiredEntityStates", 0, "state"),
            entity_type="character",
            entity_id="speaker",
            allowed_states=("awake",),
        ),
    )
    assert set(facts[0].model_dump(mode="json", by_alias=True)) == {
        "code",
        "path",
        "entityType",
        "entityId",
        "allowedStates",
    }
    assert "asleep" not in str(facts[0].model_dump(mode="json", by_alias=True))


@pytest.mark.parametrize(
    "issue_path",
    (
        ("shots", 1, "requiredEntityStates", 0, "state"),
        ("shots", 0, "requiredEntityStates", 1, "state"),
        ("shots", 0, "requiredEntityStates", 0, "entityId"),
        ("shots", -1, "requiredEntityStates", 0, "state"),
    ),
)
def test_m12a_entity_state_repair_fact_rejects_unbound_issue_paths(
    issue_path: tuple[str | int, ...],
) -> None:
    from plotloom.generation.contracts import ValidationIssue

    _, bible, _, _, _ = _inputs()
    assert storyboard_required_entity_state_repair_facts(
        _board_output(state="asleep"),
        (
            ValidationIssue(
                code="semantic.invalid_required_entity_state",
                message="untrusted prose",
                path=issue_path,
            ),
        ),
        bible=bible,
    ) == ()


def test_m12a_entity_state_repair_fact_fails_closed_without_state_vocabulary() -> None:
    from plotloom.generation.contracts import ValidationIssue

    _, bible, _, _, _ = _inputs()
    empty_vocabulary = bible.model_copy(
        update={
            "characters": [
                bible.characters[0].model_copy(update={"allowed_states": []})
            ]
        }
    )
    issue = ValidationIssue(
        code="semantic.invalid_required_entity_state",
        message="untrusted prose",
        path=("shots", 0, "requiredEntityStates", 0, "state"),
    )
    assert storyboard_required_entity_state_repair_facts(
        _board_output(state="asleep"),
        (issue,),
        bible=empty_vocabulary,
    ) == ()

    schema_invalid = _board_output(state="asleep")
    del schema_invalid["shots"][0]["requiredEntityStates"][0]["entityId"]
    assert storyboard_required_entity_state_repair_facts(
        schema_invalid,
        (issue,),
        bible=bible,
    ) == ()


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
