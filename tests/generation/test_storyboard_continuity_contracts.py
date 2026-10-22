"""test storyboard continuity contracts behavior contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest

from plotloom.domain import (
    ContinuityStateV2,
    DialogueCue,
    DialogueDeliveryPace,
    SceneBeatPlanV2,
    StageName,
)
from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.correction_directives import (
    compile_correction_instruction_plan,
)
from plotloom.generation.correction_postconditions import (
    validate_correction_postconditions,
)
from plotloom.generation.correction_schema import compile_correction_response_schema
from plotloom.generation.planning import plan_stage
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    ContinuityEntityStateRepairFact,
    ShotContent,
    StoryboardFragmentOutput,
    WorkUnitContractError,
    assert_continuity_entity_state_repair_fact_matches_source,
    compile_work_unit_request,
    continuity_entity_state_repair_facts,
    semantic_repair_facts,
)
from tests.generation.work_unit_contract_fixtures import (
    _bible_with_hero,
    _brief,
    _character_state,
    _compile_scene_beats,
    _plan_and_inputs,
    _scene_output,
    _storyboard_output,
)


def test_scene_fragment_rejects_invalid_continuity_vocabulary_and_sequence_before_binding() -> (
    None
):
    brief, snapshot, plan, _, graph, _ = _plan_and_inputs()
    bible = _bible_with_hero()
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
    )
    invalid_vocabulary = _scene_output()
    invalid_vocabulary["scenes"][0]["entryState"] = _character_state(
        "missing"
    ).model_dump(mode="json", by_alias=True)
    invalid_vocabulary["beats"][0]["exitState"] = ContinuityStateV2(
        facts={},
        entity_states=[
            {"entityType": "character", "entityId": "unknown", "state": "alert"}
        ],
        screen_direction=None,
        lighting=None,
        sound=None,
        notes=[],
    ).model_dump(mode="json", by_alias=True)
    report = compiled.validator.validate(
        invalid_vocabulary,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert report.accepted is False
    issues = {(issue.code, issue.path) for issue in report.issues}
    assert (
        "semantic.invalid_continuity_entity_state",
        ("scenes", 0, "entryState", "entityStates", 0, "state"),
    ) in issues
    assert (
        "semantic.unknown_continuity_entity",
        ("beats", 0, "exitState", "entityStates", 0, "entityId"),
    ) in issues

    sequence_mismatch = _scene_output()
    sequence_mismatch["scenes"][0]["entryState"] = _character_state("alert").model_dump(
        mode="json", by_alias=True
    )
    sequence_mismatch["scenes"][0]["exitState"] = _character_state("alert").model_dump(
        mode="json", by_alias=True
    )
    sequence_mismatch["beats"][0]["entryState"] = _character_state("calm").model_dump(
        mode="json", by_alias=True
    )
    sequence_mismatch["beats"][0]["exitState"] = _character_state("alert").model_dump(
        mode="json", by_alias=True
    )
    sequence_report = compiled.validator.validate(
        sequence_mismatch,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert sequence_report.accepted is False
    assert (
        "semantic.continuity_beat_sequence_mismatch",
        ("scenes", 0),
    ) in {(issue.code, issue.path) for issue in sequence_report.issues}


def test_continuity_state_correction_rebinds_exact_response_entry_to_bible_vocabulary() -> (
    None
):
    brief, snapshot, plan, _, graph, _ = _plan_and_inputs()
    bible = _bible_with_hero()
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
    )
    rejected_value = _scene_output()
    rejected_value["scenes"][0]["entryState"] = _character_state("missing").model_dump(
        mode="json", by_alias=True
    )
    report = compiled.validator.validate(
        rejected_value, context=SemanticValidationContext(stage="scene_beats")
    )
    facts = semantic_repair_facts(
        rejected_value,
        report.issues,
        stage=StageName.SCENE_BEATS,
        bible=bible,
        scoped_context=compiled.validator.scoped_context,
        dialogue_capacity_guidance=compiled.contract.dialogue_capacity_guidance,
        dialogue_timing_profile=stage_plan.dialogue_timing_profile,
        node_duration_budget_units=compiled.contract.node_duration_budget_units,
        join_state_value_requirements=compiled.validator.scoped_context[
            "join_state_value_requirements"
        ],
    )
    fact = next(
        item for item in facts if isinstance(item, ContinuityEntityStateRepairFact)
    )
    assert fact.path == ("scenes", 0, "entryState", "entityStates", 0, "state")
    assert fact.entity_id == "hero"
    assert fact.allowed_states == ("alert", "calm")
    assert_continuity_entity_state_repair_fact_matches_source(
        fact, rejected_value, stage=StageName.SCENE_BEATS, bible=bible
    )
    directive_plan = compile_correction_instruction_plan(report.issues, facts)
    assert "continuity_values" in [
        directive.id for directive in directive_plan.directives
    ]
    overlay = compile_correction_response_schema(compiled.response_schema, [fact])
    assert fact.code in overlay.applied_fact_codes

    repaired = deepcopy(rejected_value)
    repaired["scenes"][0]["entryState"]["entityStates"][0]["state"] = "alert"
    assert validate_correction_postconditions(repaired, [fact]) == ()
    repaired["scenes"][0]["entryState"]["entityStates"][0]["entityId"] = "other"
    assert validate_correction_postconditions(repaired, [fact])


def test_storyboard_continuity_state_repair_keeps_the_typed_fact() -> None:
    bible = _bible_with_hero()
    value = _storyboard_output(beat_ids=["beat-node-a"])
    value["shots"][0]["exitState"] = _character_state("missing").model_dump(
        mode="json", by_alias=True
    )
    issue = ValidationIssue(
        code="semantic.invalid_continuity_entity_state",
        message="fixture",
        path=("shots", 0, "exitState", "entityStates", 0, "state"),
    )
    facts = continuity_entity_state_repair_facts(
        value, (issue,), stage=StageName.STORYBOARD, bible=bible
    )
    assert len(facts) == 1
    fact = facts[0]
    assert fact.target.kind == "shot"
    assert fact.target.id == "shot-a"
    assert_continuity_entity_state_repair_fact_matches_source(
        fact, value, stage=StageName.STORYBOARD, bible=bible
    )


def test_storyboard_fragment_rejects_canonical_gate_semantics_before_binding() -> None:
    brief, snapshot, plan, _, graph, scene_beats = _plan_and_inputs()
    bible = _bible_with_hero()
    scene = scene_beats.scenes[0].model_copy(
        update={
            "duration_budget_units": 5,
            "entry_state": _character_state("alert"),
            "exit_state": _character_state("alert"),
        }
    )
    beat = scene_beats.beats[0].model_copy(
        update={
            "entry_state": _character_state("alert"),
            "exit_state": _character_state("alert"),
        }
    )
    cues = [
        DialogueCue(
            id="cue-first",
            beat_id=beat.id,
            order=1,
            speaker_id="hero",
            voice_over=None,
            text="第一句。",
            language="zh-CN",
            delivery=DialogueDeliveryPace.NATURAL,
            performance_notes="压低声音。",
            estimated_duration_units=2,
        ),
        DialogueCue(
            id="cue-second",
            beat_id=beat.id,
            order=2,
            speaker_id="hero",
            voice_over=None,
            text="第二句。",
            language="zh-CN",
            delivery=DialogueDeliveryPace.NATURAL,
            performance_notes="看向警报。",
            estimated_duration_units=2,
        ),
    ]
    enriched_scene_beats = SceneBeatPlanV2(
        scenes=[scene, *scene_beats.scenes[1:]],
        beats=[beat, *scene_beats.beats[1:]],
        dialogue_cues=cues,
    )
    stage_plan = plan_stage(
        plan,
        stage=StageName.STORYBOARD,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
            StageName.SCENE_BEATS: enriched_scene_beats,
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
            StageName.SCENE_BEATS: enriched_scene_beats,
        },
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    output = StoryboardFragmentOutput(
        shots=[
            ShotContent(
                local_shot_id="first",
                order=1,
                title="苏醒",
                shot_size="close_up",
                duration_units=2,
                camera_angle="",
                camera_movement="",
                composition="",
                visual_intent="",
                motion_intent="",
                action="",
                transition="",
                cue_ids=["cue-second", "cue-first"],
                audio_plan={"events": []},
                character_ids=["hero"],
                location_id=None,
                prop_ids=[],
                required_entity_states=[
                    {"entityType": "character", "entityId": "hero", "state": "alert"}
                ],
                entry_state=_character_state("calm"),
                exit_state=_character_state("alert"),
            ),
            ShotContent(
                local_shot_id="second",
                order=2,
                title="警报",
                shot_size="medium",
                duration_units=4,
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
                required_entity_states=[
                    {"entityType": "character", "entityId": "hero", "state": "alert"}
                ],
                entry_state=_character_state("alert"),
                exit_state=_character_state("alert"),
            ),
        ],
        primary_shot_local_id_by_beat={beat.id: "first"},
        supporting_beat_links=[
            {"shotLocalId": "second", "beatId": beat.id, "coverageWeight": 1.0}
        ],
    ).model_dump(mode="json", by_alias=True)
    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert report.accepted is False
    issues = {(issue.code, issue.path) for issue in report.issues}
    assert ("semantic.shot_duration_budget_exceeded", ("shots",)) in issues
    assert (
        "semantic.required_entity_not_in_shot",
        ("shots", 1, "requiredEntityStates", 0, "entityId"),
    ) in issues
    assert (
        "semantic.continuity_shot_sequence_mismatch",
        ("shots",),
    ) in issues
    assert ("semantic.cue_canonical_order", ("shots", 0, "cueIds")) in issues
    assert ("semantic.cue_duration_exceeds_shot", ("shots", 0, "cueIds")) in issues


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
