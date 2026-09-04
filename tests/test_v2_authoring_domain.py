from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.domain import (
    AudioEvent,
    AudioKind,
    AudioPlan,
    BeatV2,
    CharacterV2,
    ContinuityStateV2,
    DialogueCue,
    DialogueDeliveryPace,
    DialogueTimingProfile,
    DialogueTimingRule,
    DramaticSceneV2,
    EntityType,
    LocationV2,
    ProjectBrief,
    PropV2,
    RequiredEntityState,
    SceneBeatPlanV1,
    SceneBeatPlanV2,
    StoryEdgeV2,
    JoinContractV2,
    ShotBeatLinkV2,
    ShotV2,
    StoryBibleV1,
    StoryBibleV2,
    StoryboardV2,
    StoryGraphV2,
    StoryNodeV2,
    StageName,
    TimelineContractError,
    V2CoverageRole,
    V2ShotSize,
    derive_node_timecodes,
    derive_path_timecode,
    derive_scene_timecodes,
    stage_payload_model,
)
from plotloom.validation import DomainValidationError, StoryboardGateEvaluator, validate_stage_payload


def _state(*entity_states: RequiredEntityState) -> ContinuityStateV2:
    return ContinuityStateV2(
        facts={}, entity_states=list(entity_states), screen_direction=None, lighting=None, sound=None, notes=[]
    )


def _authoring_fixture() -> tuple[StoryBibleV2, SceneBeatPlanV2, StoryboardV2, DialogueTimingProfile]:
    character_state = RequiredEntityState(entity_type=EntityType.CHARACTER, entity_id="mira", state="calm")
    bible = StoryBibleV2(
        logline="Mira decides.", premise="A small choice changes the voyage.", genre="drama", tone="quiet",
        audience="adult", narrative_promise="a consequence", visual_language="natural", themes=[], world_rules=[],
        known_facts=[], open_questions=[], source_notes=[],
        characters=[CharacterV2(id="mira", name="Mira", description="pilot", role="lead", goal="get home", traits=["decisive"], visual_anchors=["red coat"], sound_anchors=["boots"], voice_anchors=["low voice"], allowed_states=["calm"], continuity_rules=["coat stays red"])],
        locations=[LocationV2(id="bridge", name="Bridge", description="ship bridge", visual_anchors=["glass"], sound_anchors=["hum"], allowed_states=["powered"], continuity_rules=["night"])],
        props=[PropV2(id="key", name="Key", description="brass key", visual_anchors=["brass"], sound_anchors=["click"], allowed_states=["held"], continuity_rules=["unbroken"])],
    )
    scene = DramaticSceneV2(
        id="scene-1", story_node_id="node-1", order=1, title="Decision", objective="choose", location_id="bridge",
        character_ids=["mira"], beat_ids=["beat-1"], duration_budget_units=330,
        entry_state=_state(character_state), exit_state=_state(character_state),
    )
    beat = BeatV2(
        id="beat-1", scene_id="scene-1", order=1, description="Mira speaks", purpose="choose", visible_event="Mira turns",
        immediate_result="she commits", dramatic_change="choice made", entry_state=_state(character_state), exit_state=_state(character_state), continuity_anchors=[], continuity_delta={},
    )
    cue = DialogueCue(id="cue-1", beat_id="beat-1", order=1, speaker_id="mira", voice_over=None, text="走", language="zh-CN", delivery="natural", performance_notes="calmly", estimated_duration_units=330)
    plan = SceneBeatPlanV2(scenes=[scene], beats=[beat], dialogue_cues=[cue])
    shot = ShotV2(
        id="shot-1", scene_id="scene-1", order=1, title="Mira", shot_size=V2ShotSize.MEDIUM, duration_units=330,
        camera_angle="eye", camera_movement="still", composition="single", visual_intent="choice", motion_intent="hold", action="Mira turns", transition="cut",
        cue_ids=["cue-1"], audio_plan=AudioPlan(events=[AudioEvent(id="hum", kind=AudioKind.AMBIENCE, description="engine hum", start_offset_units=0, duration_units=330)]),
        character_ids=["mira"], location_id="bridge", prop_ids=[], required_entity_states=[character_state], entry_state=_state(character_state), exit_state=_state(character_state),
    )
    board = StoryboardV2(shots=[shot], shot_beat_links=[ShotBeatLinkV2(shot_id="shot-1", beat_id="beat-1", role=V2CoverageRole.PRIMARY, coverage_weight=1)])
    profile = DialogueTimingProfile(version="dialogue.zh-CN.natural.v1", rules=[DialogueTimingRule(language="zh-CN", delivery="natural", units_per_character=330)])
    return bible, plan, board, profile


def test_schema_dispatch_keeps_v1_read_and_v2_authoring_separate() -> None:
    assert stage_payload_model("story_bible", schema_version=1) is StoryBibleV1
    assert stage_payload_model("scene_beats", schema_version=1) is SceneBeatPlanV1
    assert stage_payload_model("story_bible", schema_version=2) is StoryBibleV2
    assert stage_payload_model("scene_beats", schema_version=2) is SceneBeatPlanV2

    # V2 does not fabricate anchors, allowed states, or dialogue ownership from
    # a minimal legacy bible.  Conversely V1 rejects V2-only authoring fields.
    with pytest.raises(ValidationError):
        StoryBibleV2.model_validate({"logline": "old", "premise": "old"})
    with pytest.raises(ValidationError):
        StoryBibleV1.model_validate(
            {"logline": "new", "premise": "new", "characters": [{"id": "m", "name": "M", "visualAnchors": []}]}
        )


def test_dialogue_cue_requires_exactly_one_speaker_or_voice_over() -> None:
    common = dict(id="cue", beat_id="beat", order=1, text="line", language="en", delivery="natural", performance_notes="", estimated_duration_units=1)
    with pytest.raises(ValidationError):
        DialogueCue(**common, speaker_id=None, voice_over=None)
    with pytest.raises(ValidationError):
        DialogueCue(**common, speaker_id="mira", voice_over="narrator")


def test_v2_gate_and_integer_timeline_are_deterministic() -> None:
    bible, plan, board, profile = _authoring_fixture()
    brief = ProjectBrief(title="x", synopsis="y", ending_count=1, desired_join_count=0, decision_points_per_path=0, node_budget=2, shots_per_scene_min=1, shots_per_scene_max=1)
    evaluation = StoryboardGateEvaluator().evaluate(board, plan, bible, brief, timing_profile=profile)
    assert evaluation.passed is True
    assert {result.evaluated_input_hash for result in evaluation.results} == {evaluation.evaluated_input_hash}
    assert evaluation.results[0].model_copy(update={"status": "skipped"}).passed is False

    scenes = derive_scene_timecodes(plan, board)
    nodes = derive_node_timecodes(plan, board)
    graph = StoryGraphV2(
        start_node_id="node-1",
        nodes=[StoryNodeV2(id="node-1", title="Decision", summary="choose", kind="ending")],
        edges=[],
        join_contracts=[],
    )
    path = derive_path_timecode(plan, board, ["node-1"], graph=graph)
    assert scenes[0].timecode.start_units == 0 and scenes[0].timecode.duration_units == 330
    assert nodes[0].timecode.duration_units == 330
    assert path.scenes[0].timecode.start_units == 0 and path.duration_units == 330

    incomplete_graph = graph.model_copy(
        update={"nodes": [graph.nodes[0].model_copy(update={"kind": "start"})]}
    )
    with pytest.raises(TimelineContractError) as incomplete_path:
        derive_path_timecode(plan, board, ["node-1"], graph=incomplete_graph)
    assert incomplete_path.value.code == "timeline.path_not_ending"

    bad_order = board.model_copy(
        update={"shots": [board.shots[0].model_copy(update={"order": 2})]}
    )
    with pytest.raises(TimelineContractError) as invalid_order:
        derive_scene_timecodes(plan, bad_order)
    assert invalid_order.value.code == "timeline.shot_order"

    with pytest.raises(TimelineContractError) as repeated_path:
        derive_path_timecode(plan, board, ["node-1", "node-1"], graph=graph)
    assert repeated_path.value.code == "timeline.repeated_path_node"


def test_required_dialogue_timing_skip_and_audio_overrun_fail_the_gate() -> None:
    bible, plan, board, profile = _authoring_fixture()
    skipped = StoryboardGateEvaluator().evaluate(board, plan, bible)
    assert skipped.passed is False
    assert any(result.status.value == "skipped" and result.required for result in skipped.results)

    invalid_audio = board.model_copy(
        update={"shots": [board.shots[0].model_copy(update={"audio_plan": AudioPlan(events=[AudioEvent(id="too-long", kind=AudioKind.SCORE, description="score", start_offset_units=329, duration_units=2)])})]}
    )
    failed = StoryboardGateEvaluator().evaluate(invalid_audio, plan, bible, timing_profile=profile)
    assert failed.passed is False
    assert any(result.gate_id == "audio.timing.shot-1" and result.status.value == "fail" for result in failed.results)


def test_default_timing_profile_supports_non_chinese_dialogue_explicitly() -> None:
    bible, plan, board, _ = _authoring_fixture()
    english_cue = plan.dialogue_cues[0].model_copy(
        update={
            "text": "Go",
            "language": "en",
            "delivery": DialogueDeliveryPace.NATURAL,
            "estimated_duration_units": 120,
        }
    )
    english_plan = plan.model_copy(update={"dialogue_cues": [english_cue]})
    brief = ProjectBrief(
        title="x",
        synopsis="y",
        ending_count=1,
        desired_join_count=0,
        decision_points_per_path=0,
        node_budget=2,
        shots_per_scene_min=1,
        shots_per_scene_max=1,
    )
    receipt = validate_stage_payload(
        StageName.STORYBOARD,
        board,
        schema_version=2,
        brief=brief,
        bible=bible,
        scene_beats=english_plan,
    )
    assert receipt is not None and receipt.passed

    understated = english_plan.model_copy(
        update={
            "dialogue_cues": [
                english_cue.model_copy(update={"estimated_duration_units": 119})
            ]
        }
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.SCENE_BEATS,
            understated,
            schema_version=2,
            brief=brief,
            bible=bible,
            graph=StoryGraphV2(
                start_node_id="node-1",
                nodes=[
                    StoryNodeV2(
                        id="node-1", title="Decision", summary="choose", kind="start"
                    )
                ],
                edges=[],
                join_contracts=[],
            ),
        )
    assert any(
        issue["code"] == "dialogue_duration_underestimated"
        for issue in captured.value.issues
    )


def test_v2_storyboard_validation_returns_gate_receipt_and_projects_stable_gate_issues() -> None:
    bible, plan, board, _ = _authoring_fixture()
    brief = ProjectBrief(title="x", synopsis="y", ending_count=1, desired_join_count=0, decision_points_per_path=0, node_budget=2, shots_per_scene_min=1, shots_per_scene_max=1)
    receipt = validate_stage_payload(
        StageName.STORYBOARD,
        board,
        schema_version=2,
        brief=brief,
        bible=bible,
        scene_beats=plan,
    )
    assert receipt is not None and receipt.passed
    assert receipt.gate_set_version == "storyboard.v2"

    invalid_speaker = plan.model_copy(
        update={"dialogue_cues": [plan.dialogue_cues[0].model_copy(update={"speaker_id": "missing"})]}
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.STORYBOARD,
            board,
            schema_version=2,
            brief=brief,
            bible=bible,
            scene_beats=invalid_speaker,
        )
    assert any(issue["code"] == "gate.dialogue_cue.speaker.cue-1" for issue in captured.value.issues)

    invalid_board = board.model_copy(
        update={
            "shots": [
                board.shots[0].model_copy(
                    update={
                        "required_entity_states": [
                            RequiredEntityState(
                                entity_type=EntityType.CHARACTER,
                                entity_id="mira",
                                state="unknown-state",
                            )
                        ]
                    }
                )
            ],
            "shot_beat_links": [],
        }
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.STORYBOARD,
            invalid_board,
            schema_version=2,
            brief=brief,
            bible=bible,
            scene_beats=plan,
        )
    codes = {issue["code"] for issue in captured.value.issues}
    assert "gate.entity.required_state.available.shot-1" in codes
    assert "gate.coverage.primary.beat-1" in codes


def test_global_gate_defensively_rejects_duplicate_entity_audio_and_cue_schedules() -> None:
    bible, plan, board, profile = _authoring_fixture()
    shot = board.shots[0]
    duplicated_state = RequiredEntityState(
        entity_type=EntityType.CHARACTER, entity_id="mira", state="calm"
    )
    bypassed_model_validation = shot.model_copy(
        update={
            "character_ids": ["mira", "mira"],
            "required_entity_states": [duplicated_state, duplicated_state],
            "audio_plan": shot.audio_plan.model_copy(
                update={"events": [shot.audio_plan.events[0], shot.audio_plan.events[0]]}
            ),
        }
    )
    duplicate_board = board.model_copy(update={"shots": [bypassed_model_validation]})
    duplicate_codes = {
        result.gate_id
        for result in StoryboardGateEvaluator().evaluate(
            duplicate_board, plan, bible, timing_profile=profile
        ).results
        if not result.passed
    }
    assert {
        "entity.reference_unique.shot-1",
        "entity.required_state.unique.shot-1",
        "audio.event_id.unique.shot-1",
    } <= duplicate_codes

    twice_scheduled = shot.model_copy(
        update={"id": "shot-2", "order": 2, "cue_ids": ["cue-1"]}
    )
    duplicate_schedule_board = board.model_copy(
        update={"shots": [shot, twice_scheduled]}
    )
    schedule_codes = {
        result.gate_id
        for result in StoryboardGateEvaluator().evaluate(
            duplicate_schedule_board, plan, bible, timing_profile=profile
        ).results
        if not result.passed
    }
    assert "dialogue_cue.schedule_cardinality.cue-1" in schedule_codes
    assert "dialogue_cue.beat_coverage.cue-1" in schedule_codes


def test_schema_rejects_ambiguous_entity_state_and_duplicate_shot_references() -> None:
    _, _, board, _ = _authoring_fixture()
    shot = board.shots[0].model_dump(mode="python")
    shot["character_ids"] = ["mira", "mira"]
    with pytest.raises(ValidationError, match="characterIds must not contain duplicates"):
        ShotV2.model_validate(shot)

    with pytest.raises(ValidationError, match="audio event ids must be unique"):
        AudioPlan.model_validate(
            {
                "events": [
                    {
                        "id": "hum",
                        "kind": "ambience",
                        "description": "engine hum",
                        "startOffsetUnits": 0,
                        "durationUnits": 1,
                    },
                    {
                        "id": "hum",
                        "kind": "ambience",
                        "description": "second engine hum",
                        "startOffsetUnits": 1,
                        "durationUnits": 1,
                    },
                ]
            }
        )

    ambiguous_state = {
        "facts": {},
        "entity_states": [
            {"entity_type": "character", "entity_id": "mira", "state": "calm"},
            {"entity_type": "character", "entity_id": "mira", "state": "calm"},
        ],
        "screen_direction": None,
        "lighting": None,
        "sound": None,
        "notes": [],
    }
    with pytest.raises(ValidationError, match="continuity entityStates"):
        ContinuityStateV2.model_validate(ambiguous_state)


def test_v2_scene_beats_rejects_unordered_scenes_and_unallowed_continuity_states() -> None:
    bible, plan, board, _ = _authoring_fixture()
    brief = ProjectBrief(
        title="x",
        synopsis="y",
        ending_count=1,
        desired_join_count=0,
        decision_points_per_path=0,
        node_budget=2,
        shots_per_scene_min=1,
        shots_per_scene_max=1,
    )
    graph = StoryGraphV2(
        start_node_id="node-1",
        nodes=[StoryNodeV2(id="node-1", title="Decision", summary="choose", kind="start")],
        edges=[],
        join_contracts=[],
    )
    unordered_plan = plan.model_copy(
        update={"scenes": [plan.scenes[0].model_copy(update={"order": 2})]}
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.SCENE_BEATS,
            unordered_plan,
            schema_version=2,
            brief=brief,
            bible=bible,
            graph=graph,
        )
    assert any(issue["code"] == "non_contiguous_scene_order" for issue in captured.value.issues)

    invalid_state = RequiredEntityState(
        entity_type=EntityType.CHARACTER, entity_id="mira", state="furious"
    )
    invalid_plan = plan.model_copy(
        update={
            "beats": [plan.beats[0].model_copy(update={"entry_state": _state(invalid_state)})]
        }
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.SCENE_BEATS,
            invalid_plan,
            schema_version=2,
            brief=brief,
            bible=bible,
            graph=graph,
        )
    issue = next(issue for issue in captured.value.issues if issue["code"] == "invalid_continuity_entity_state")
    assert issue["path"] == "beats.beat-1.entryState.entityStates.0.state"

    invalid_board = board.model_copy(
        update={
            "shots": [
                board.shots[0].model_copy(update={"exit_state": _state(invalid_state)})
            ]
        }
    )
    failed = StoryboardGateEvaluator().evaluate(invalid_board, plan, bible)
    assert any(
        result.gate_id == "continuity.entity_state.available.shot.shot-1"
        and not result.passed
        for result in failed.results
    )


def test_beat_continuity_sequence_is_required_at_scene_beats_and_storyboard() -> None:
    bible, plan, board, profile = _authoring_fixture()
    brief = ProjectBrief(
        title="x",
        synopsis="y",
        ending_count=1,
        desired_join_count=0,
        decision_points_per_path=0,
        node_budget=2,
        shots_per_scene_min=1,
        shots_per_scene_max=1,
    )
    graph = StoryGraphV2(
        start_node_id="node-1",
        nodes=[StoryNodeV2(id="node-1", title="Decision", summary="choose", kind="start")],
        edges=[],
        join_contracts=[],
    )
    passing = StoryboardGateEvaluator().evaluate(
        board, plan, bible, brief, timing_profile=profile
    )
    assert next(
        result for result in passing.results
        if result.gate_id == "continuity.beat_sequence.scene-1"
    ).passed

    bible_with_alert = bible.model_copy(
        update={
            "characters": [
                bible.characters[0].model_copy(update={"allowed_states": ["calm", "alert"]})
            ]
        }
    )
    alert = RequiredEntityState(
        entity_type=EntityType.CHARACTER, entity_id="mira", state="alert"
    )
    discontinuous_plan = plan.model_copy(
        update={
            "beats": [
                plan.beats[0].model_copy(update={"entry_state": _state(alert)})
            ]
        }
    )
    failed = StoryboardGateEvaluator().evaluate(
        board, discontinuous_plan, bible_with_alert, brief, timing_profile=profile
    )
    assert not next(
        result for result in failed.results
        if result.gate_id == "continuity.beat_sequence.scene-1"
    ).passed

    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.SCENE_BEATS,
            discontinuous_plan,
            schema_version=2,
            brief=brief,
            bible=bible_with_alert,
            graph=graph,
        )
    issue = next(
        issue
        for issue in captured.value.issues
        if issue["code"] == "continuity_beat_sequence_mismatch"
    )
    assert issue["path"] == "scenes.scene-1"


def test_v2_ids_and_dialogue_scalars_are_trimmed_or_rejected() -> None:
    cue = DialogueCue(
        id=" cue-1 ",
        beat_id=" beat-1 ",
        order=1,
        speaker_id=" mira ",
        voice_over=None,
        text="  Go.  ",
        language=" en ",
        delivery="natural",
        performance_notes="",
        estimated_duration_units=1,
    )
    assert (cue.id, cue.beat_id, cue.speaker_id, cue.text, cue.language) == (
        "cue-1", "beat-1", "mira", "Go.", "en"
    )
    with pytest.raises(ValidationError):
        DialogueCue(
            id="cue.with.dot",
            beat_id="beat-1",
            order=1,
            speaker_id="mira",
            voice_over=None,
            text="Go.",
            language="en",
            delivery="natural",
            performance_notes="",
            estimated_duration_units=1,
        )
    with pytest.raises(ValidationError):
        DialogueCue(
            id="cue-1",
            beat_id="beat-1",
            order=1,
            speaker_id=None,
            voice_over="   ",
            text="   ",
            language="en",
            delivery="natural",
            performance_notes="",
            estimated_duration_units=1,
        )


def test_v2_graph_rejects_duplicate_directed_connections() -> None:
    graph = StoryGraphV2(
        start_node_id="start",
        nodes=[
            StoryNodeV2(id="start", title="Start", summary="begin", kind="start"),
            StoryNodeV2(id="decision", title="Decision", summary="choose", kind="decision"),
            StoryNodeV2(id="end", title="End", summary="finish", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(id="e-start", source_node_id="start", target_node_id="decision", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="e-choice-a", source_node_id="decision", target_node_id="end", kind="choice", choice_text="go", state_effects={}),
            StoryEdgeV2(id="e-choice-b", source_node_id="decision", target_node_id="end", kind="choice", choice_text="also go", state_effects={}),
        ],
        join_contracts=[],
    )
    brief = ProjectBrief(
        title="x", synopsis="y", ending_count=1, desired_join_count=0,
        decision_points_per_path=1, node_budget=3, shots_per_scene_min=1,
        shots_per_scene_max=1,
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(StageName.STORY_GRAPH, graph, schema_version=2, brief=brief)
    duplicate = next(issue for issue in captured.value.issues if issue["code"] == "duplicate_edge_connection")
    assert duplicate["path"] == "edges.2"


def test_v2_join_contract_and_edge_choice_fields_are_unambiguous() -> None:
    valid = dict(
        id="join-contract", join_node_id="join", incoming_node_ids=["left", "right"],
        required_state_keys=["channel"], allowed_differences=[], reconciliation="", notes="",
    )
    with pytest.raises(ValidationError, match="incomingNodeIds must not contain duplicates"):
        JoinContractV2(**(valid | {"incoming_node_ids": ["left", "left"]}))
    with pytest.raises(ValidationError, match="requiredStateKeys must not contain duplicates"):
        JoinContractV2(**(valid | {"required_state_keys": ["channel", "channel"]}))
    with pytest.raises(ValidationError, match="allowedDifferences must not contain duplicates"):
        JoinContractV2(**(valid | {"allowed_differences": ["channel", "channel"]}))
    with pytest.raises(ValidationError, match="allowedDifferences must be contained"):
        JoinContractV2(**(valid | {"allowed_differences": ["route"]}))
    normalized = JoinContractV2(**(valid | {"required_state_keys": [" channel "]}))
    assert normalized.required_state_keys == ["channel"]

    with pytest.raises(ValidationError, match="at least 1 item"):
        StoryEdgeV2(
            id="choice", source_node_id="a", target_node_id="b", kind="choice",
            choice_text="  ", state_effects={},
        )
    with pytest.raises(ValidationError, match="continuation edges must not define choice_text"):
        StoryEdgeV2(
            id="continuation", source_node_id="a", target_node_id="b", kind="continuation",
            choice_text="continue", state_effects={},
        )


def test_v2_join_required_state_equality_allows_only_reconciled_exceptions() -> None:
    bible, plan, _, _ = _authoring_fixture()
    def state(channel: str) -> ContinuityStateV2:
        return ContinuityStateV2(
            facts={"channel": channel}, entity_states=[], screen_direction=None,
            lighting=None, sound=None, notes=[],
        )

    left = plan.scenes[0].model_copy(
        update={"id": "scene-left", "story_node_id": "left", "beat_ids": ["beat-left"], "entry_state": state("open"), "exit_state": state("open")}
    )
    right = plan.scenes[0].model_copy(
        update={"id": "scene-right", "story_node_id": "right", "beat_ids": ["beat-right"], "entry_state": state("closed"), "exit_state": state("closed")}
    )
    joined = plan.scenes[0].model_copy(
        update={"id": "scene-join", "story_node_id": "join", "beat_ids": ["beat-join"], "entry_state": state("open"), "exit_state": state("open")}
    )
    joined_plan = plan.model_copy(
        update={
            "scenes": [left, right, joined],
            "beats": [
                plan.beats[0].model_copy(update={"id": "beat-left", "scene_id": "scene-left", "entry_state": state("open"), "exit_state": state("open")}),
                plan.beats[0].model_copy(update={"id": "beat-right", "scene_id": "scene-right", "entry_state": state("closed"), "exit_state": state("closed")}),
                plan.beats[0].model_copy(update={"id": "beat-join", "scene_id": "scene-join", "entry_state": state("open"), "exit_state": state("open")}),
            ],
            "dialogue_cues": [],
        }
    )
    def graph(allowed_differences: list[str], reconciliation: str) -> StoryGraphV2:
        return StoryGraphV2(
            start_node_id="left",
            nodes=[
                StoryNodeV2(id="left", title="Left", summary="left", kind="start"),
                StoryNodeV2(id="right", title="Right", summary="right", kind="scene"),
                StoryNodeV2(id="join", title="Join", summary="join", kind="ending"),
            ],
            edges=[
                StoryEdgeV2(id="left-join", source_node_id="left", target_node_id="join", kind="choice", choice_text="join", state_effects={}),
                StoryEdgeV2(id="left-right", source_node_id="left", target_node_id="right", kind="choice", choice_text="right", state_effects={}),
                StoryEdgeV2(id="right-join", source_node_id="right", target_node_id="join", kind="continuation", choice_text=None, state_effects={}),
            ],
            join_contracts=[JoinContractV2(
                id="join-contract", join_node_id="join", incoming_node_ids=["left", "right"],
                required_state_keys=["channel"], allowed_differences=allowed_differences,
                reconciliation=reconciliation, notes="",
            )],
        )

    brief = ProjectBrief(title="x", synopsis="y", ending_count=1, desired_join_count=0, decision_points_per_path=0, node_budget=3, shots_per_scene_min=1, shots_per_scene_max=1)
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(StageName.SCENE_BEATS, joined_plan, schema_version=2, brief=brief, bible=bible, graph=graph([], ""))
    mismatch = next(issue for issue in captured.value.issues if issue["code"] == "join_required_state_mismatch")
    assert mismatch["path"] == "joinContracts.join-contract.requiredStateKeys"

    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(StageName.SCENE_BEATS, joined_plan, schema_version=2, brief=brief, bible=bible, graph=graph(["channel"], ""))
    assert any(issue["code"] == "join_allowed_difference_without_reconciliation" for issue in captured.value.issues)

    assert validate_stage_payload(
        StageName.SCENE_BEATS, joined_plan, schema_version=2, brief=brief,
        bible=bible, graph=graph(["channel"], "the join resolves this channel state"),
    ) is None

    over_budget_plan = joined_plan.model_copy(
        update={
            "scenes": [
                joined_plan.scenes[0].model_copy(update={"duration_budget_units": 60_001}),
                *joined_plan.scenes[1:],
            ]
        }
    )
    with pytest.raises(DomainValidationError) as captured:
        validate_stage_payload(
            StageName.SCENE_BEATS,
            over_budget_plan,
            schema_version=2,
            brief=brief,
            bible=bible,
            graph=graph(["channel"], "the join resolves this channel state"),
        )
    assert any(
        issue["code"] == "scene_node_budget_exceeded"
        for issue in captured.value.issues
    )


def test_coverage_gate_ids_use_shot_and_beat_identity() -> None:
    bible, plan, board, profile = _authoring_fixture()
    gate_ids = {
        result.gate_id
        for result in StoryboardGateEvaluator().evaluate(board, plan, bible, timing_profile=profile).results
    }
    assert "coverage.link.unique.shot-1.beat-1" in gate_ids
    assert "coverage.link.reference.shot-1.beat-1" in gate_ids
    assert "coverage.link.scene.shot-1.beat-1" in gate_ids

    second_beat = plan.beats[0].model_copy(update={"id": "beat-2", "order": 2})
    two_beat_plan = plan.model_copy(
        update={
            "scenes": [plan.scenes[0].model_copy(update={"beat_ids": ["beat-1", "beat-2"]})],
            "beats": [plan.beats[0], second_beat],
        }
    )
    second_shot = board.shots[0].model_copy(update={"id": "shot-2", "order": 2, "cue_ids": []})
    second_link = ShotBeatLinkV2(
        shot_id="shot-2", beat_id="beat-2", role=V2CoverageRole.PRIMARY, coverage_weight=1,
    )
    two_link_board = board.model_copy(
        update={"shots": [board.shots[0], second_shot], "shot_beat_links": [board.shot_beat_links[0], second_link]}
    )
    reordered_board = two_link_board.model_copy(
        update={"shot_beat_links": [second_link, board.shot_beat_links[0]]}
    )
    def coverage_ids(value: StoryboardV2) -> set[str]:
        return {
            result.gate_id
            for result in StoryboardGateEvaluator().evaluate(value, two_beat_plan, bible, timing_profile=profile).results
            if result.gate_id.startswith("coverage.link.")
        }
    assert coverage_ids(two_link_board) == coverage_ids(reordered_board)

    duplicate_link_board = board.model_copy(
        update={"shot_beat_links": [board.shot_beat_links[0], board.shot_beat_links[0]]}
    )
    duplicate_ids = coverage_ids(duplicate_link_board)
    assert "coverage.link.unique.duplicate-1" in duplicate_ids

    invalid_link = board.shot_beat_links[0].model_copy(update={"shot_id": "missing-shot"})
    invalid_link_board = board.model_copy(update={"shot_beat_links": [invalid_link]})
    invalid_ids = coverage_ids(invalid_link_board)
    assert "coverage.link.reference.invalid-0" in invalid_ids


def test_beat_continuity_gate_evaluates_each_scene_with_its_own_beats() -> None:
    bible, plan, board, profile = _authoring_fixture()
    bible = bible.model_copy(
        update={
            "characters": [
                bible.characters[0].model_copy(
                    update={"allowed_states": ["calm", "alert"]}
                )
            ]
        }
    )
    alert = RequiredEntityState(
        entity_type=EntityType.CHARACTER, entity_id="mira", state="alert"
    )
    second_scene = plan.scenes[0].model_copy(
        update={
            "id": "scene-2",
            "story_node_id": "node-2",
            "title": "Aftermath",
            "beat_ids": ["beat-2"],
            "entry_state": _state(alert),
            "exit_state": _state(alert),
        }
    )
    second_beat = plan.beats[0].model_copy(
        update={
            "id": "beat-2",
            "scene_id": "scene-2",
            "entry_state": _state(alert),
            "exit_state": _state(alert),
        }
    )
    second_cue = plan.dialogue_cues[0].model_copy(
        update={"id": "cue-2", "beat_id": "beat-2", "text": "看"}
    )
    second_shot = board.shots[0].model_copy(
        update={
            "id": "shot-2",
            "scene_id": "scene-2",
            "title": "Mira sees it",
            "cue_ids": ["cue-2"],
            "required_entity_states": [alert],
            "entry_state": _state(alert),
            "exit_state": _state(alert),
        }
    )
    two_scene_plan = plan.model_copy(
        update={
            "scenes": [plan.scenes[0], second_scene],
            "beats": [plan.beats[0], second_beat],
            "dialogue_cues": [plan.dialogue_cues[0], second_cue],
        }
    )
    two_scene_board = board.model_copy(
        update={
            "shots": [board.shots[0], second_shot],
            "shot_beat_links": [
                board.shot_beat_links[0],
                ShotBeatLinkV2(
                    shot_id="shot-2",
                    beat_id="beat-2",
                    role=V2CoverageRole.PRIMARY,
                    coverage_weight=1,
                ),
            ],
        }
    )

    evaluation = StoryboardGateEvaluator().evaluate(
        two_scene_board,
        two_scene_plan,
        bible,
        timing_profile=profile,
    )
    beat_sequence_results = {
        result.gate_id: result.passed
        for result in evaluation.results
        if result.gate_id.startswith("continuity.beat_sequence.")
    }
    assert beat_sequence_results == {
        "continuity.beat_sequence.scene-1": True,
        "continuity.beat_sequence.scene-2": True,
    }
