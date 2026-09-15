from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest
from pydantic import ValidationError

from plotloom.domain import (
    BeatV2,
    CharacterV2,
    ContinuityStateV2,
    DialogueCue,
    DialogueDeliveryPace,
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
from plotloom.generation.prompts import PromptRenderer
from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.correction_directives import (
    compile_correction_instruction_plan,
)
from plotloom.generation.correction_postconditions import validate_correction_postconditions
from plotloom.generation.correction_schema import compile_correction_response_schema
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.fragment_semantics import (
    continuity_state_issues,
    continuity_states_are_compatible,
)
from plotloom.generation.work_units import (
    AUDIO_EVENT_ID_BINDING_VERSION,
    WorkUnitContractError,
    WorkUnitPromptContract,
    CueOrderRepairAssignment,
    CueOrderRepairFact,
    ContinuityEntityStateRepairFact,
    assert_continuity_entity_state_repair_fact_matches_source,
    assert_cue_order_repair_fact_matches_source,
    canonical_audio_event_id,
    canonical_fragment_id,
    continuity_entity_state_repair_facts,
    compile_work_unit_request,
    scene_beats_cue_order_repair_facts,
    scene_beats_dialogue_node_budget_repair_facts,
    semantic_repair_facts,
    storyboard_timing_repair_facts,
    parse_semantic_repair_fact,
    serialize_semantic_repair_fact,
)
from plotloom.generation.storyboard_timing_repair import (
    StoryboardTimingInfeasibleError,
    StoryboardTimingRepairPlanFact,
    build_storyboard_timing_guidance,
)
from plotloom.json_value_contract import finite_canonical_json
from plotloom.validation import (
    _continuity_state_issues,
    _continuity_states_are_compatible,
)
from plotloom.generation.work_units import (
    BeatContent,
    DramaticSceneContent,
    SceneBeatsFragmentOutput,
    ShotContent,
    StoryboardFragmentOutput,
    StoryboardTimingGuidance,
    StoryboardCueTimingGuidance,
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


def _character_state(state: str) -> ContinuityStateV2:
    return ContinuityStateV2(
        facts={},
        entity_states=[{"entityType": "character", "entityId": "hero", "state": state}],
        screen_direction=None,
        lighting=None,
        sound=None,
        notes=[],
    )


def _bible() -> StoryBibleV2:
    return StoryBibleV2(logline="领航员寻找身份。", premise="记忆决定生存。", genre="", tone="", audience="", narrative_promise="", visual_language="", themes=[], world_rules=[], known_facts=[], open_questions=[], source_notes=[], characters=[], locations=[], props=[])


def _bible_with_hero() -> StoryBibleV2:
    return _bible().model_copy(
        update={
            "characters": [
                CharacterV2(
                    id="hero",
                    name="领航员",
                    description="失忆的领航员。",
                    visual_anchors=[],
                    sound_anchors=[],
                    allowed_states=["alert", "calm"],
                    continuity_rules=[],
                    role="protagonist",
                    goal="找回身份",
                    traits=[],
                    voice_anchors=[],
                )
            ]
        }
    )


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


def _cue_order_output(*, second_order: int = 2) -> dict:
    """A valid fragment shape whose second per-beat order is deliberately wrong."""

    output = _scene_output()
    output["beats"].append(
        {
            **deepcopy(output["beats"][0]),
            "localBeatId": "beat-node-b",
            "order": 2,
            "description": "她听见远处警报。",
        }
    )
    output["dialogueCues"] = [
        {
            "localCueId": "cue-a",
            "beatLocalId": "beat-node-a",
            "order": 1,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "第一句",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
        {
            "localCueId": "cue-b",
            "beatLocalId": "beat-node-b",
            "order": second_order,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "第二句",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
    ]
    return output


def _storyboard_output(*, beat_ids: list[str], local_shot_id: str = "shot-a") -> dict:
    return StoryboardFragmentOutput(
        shots=[ShotContent(local_shot_id=local_shot_id, order=1, title="苏醒", shot_size="close_up", duration_units=2, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=[], audio_plan={"events": []}, character_ids=[], location_id=None, prop_ids=[], required_entity_states=[], entry_state=_state(), exit_state=_state())],
        primary_shot_local_id_by_beat={beat_id: local_shot_id for beat_id in beat_ids}, supporting_beat_links=[],
    ).model_dump(mode="json", by_alias=True)


def test_dialogue_node_budget_fact_uses_validator_scene_floors() -> None:
    """Deleting a scene's final cue retains its one-unit timing floor."""

    compiled, stage_plan, unit, _bible, _graph = _compile_scene_beats()
    output = _scene_output()
    output["dialogueCues"] = [
        {
            "localCueId": "cue-a",
            "beatLocalId": "beat-node-a",
            "order": 1,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "甲",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
        {
            "localCueId": "cue-b",
            "beatLocalId": "beat-node-a",
            "order": 2,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "乙",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
    ]
    facts = scene_beats_dialogue_node_budget_repair_facts(
        output,
        (
            ValidationIssue(
                code="semantic.dialogue_exceeds_node_budget",
                message="fixture",
                path=("dialogueCues",),
            ),
        ),
        node_id=unit.selector.stable_id,
        node_duration_budget_units=1,
        dialogue_timing_profile=stage_plan.dialogue_timing_profile,
        dialogue_capacity_guidance=compiled.contract.dialogue_capacity_guidance,
    )
    assert len(facts) == 1
    fact = facts[0]
    assert fact.remove_local_cue_ids == ("cue-a", "cue-b")
    # The scene remains, so the validator's `max(1, scene cue total)` floor
    # survives even when every cue is removed.
    assert fact.remaining_minimum_duration_units == 1
    assert fact.remaining_cues == ()


def test_cue_order_fact_renumbers_independently_per_beat_and_round_trips() -> None:
    output = _cue_order_output()
    issue = ValidationIssue(
        code="semantic.cue_order",
        message="fixture",
        path=("dialogueCues",),
    )

    facts = scene_beats_cue_order_repair_facts(output, (issue,))

    assert facts == (
        CueOrderRepairFact(
            code="semantic.cue_order",
            path=("dialogueCues",),
            assignments=(
                CueOrderRepairAssignment(
                    local_cue_id="cue-a",
                    beat_local_id="beat-node-a",
                    expected_order=1,
                ),
                CueOrderRepairAssignment(
                    local_cue_id="cue-b",
                    beat_local_id="beat-node-b",
                    expected_order=1,
                ),
            ),
        ),
    )
    fact = facts[0]
    assert parse_semantic_repair_fact(serialize_semantic_repair_fact(fact)) == fact
    assert_cue_order_repair_fact_matches_source(fact, output)
    routed = semantic_repair_facts(output, (issue,), stage=StageName.SCENE_BEATS)
    assert routed == facts

    tampered = deepcopy(output)
    tampered["dialogueCues"][1]["beatLocalId"] = "beat-node-a"
    with pytest.raises(ValueError, match="does not match the rejected response"):
        assert_cue_order_repair_fact_matches_source(fact, tampered)


def test_scene_beats_reports_one_aggregate_cue_order_issue() -> None:
    compiled, _stage_plan, _unit, _bible, _graph = _compile_scene_beats()
    output = _cue_order_output()
    output["dialogueCues"][0]["order"] = 2

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    cue_order_issues = [
        issue
        for issue in report.issues
        if issue.code == "semantic.cue_order"
    ]
    assert [(issue.code, issue.path) for issue in cue_order_issues] == [
        ("semantic.cue_order", ("dialogueCues",))
    ]


def test_cue_order_fact_uses_source_index_to_break_duplicate_order_ties() -> None:
    output = _scene_output()
    output["dialogueCues"] = [
        {
            "localCueId": "cue-first",
            "beatLocalId": "beat-node-a",
            "order": 3,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "第一句",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
        {
            "localCueId": "cue-second",
            "beatLocalId": "beat-node-a",
            "order": 3,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "第二句",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
    ]
    issue = ValidationIssue(
        code="semantic.cue_order", message="fixture", path=("dialogueCues",)
    )

    (fact,) = scene_beats_cue_order_repair_facts(output, (issue,))

    assert [(item.local_cue_id, item.expected_order) for item in fact.assignments] == [
        ("cue-first", 1),
        ("cue-second", 2),
    ]


@pytest.mark.parametrize(
    ("mutate", "extra_issue"),
    [
        (
            lambda output: output["dialogueCues"][1].update({"localCueId": "cue-a"}),
            ValidationIssue(
                code="semantic.duplicate_cue_id",
                message="fixture",
                path=("dialogueCues",),
            ),
        ),
        (
            lambda output: output["beats"][1].update({"localBeatId": "beat-node-a"}),
            ValidationIssue(
                code="semantic.duplicate_beat_id",
                message="fixture",
                path=("beats",),
            ),
        ),
        (
            lambda output: None,
            ValidationIssue(
                code="semantic.dialogue_cue_count_exceeded",
                message="fixture",
                path=("dialogueCues",),
            ),
        ),
        (
            lambda output: None,
            ValidationIssue(
                code="semantic.cross_unit_beat",
                message="fixture",
                path=("beats",),
            ),
        ),
        (
            lambda output: None,
            ValidationIssue(
                code="semantic.scene_capacity_exceeded",
                message="fixture",
                path=("scenes",),
            ),
        ),
    ],
)
def test_cue_order_fact_declines_unsafe_identity_or_cardinality_source(
    mutate,
    extra_issue: ValidationIssue,
) -> None:
    output = _cue_order_output()
    mutate(output)
    cue_order_issue = ValidationIssue(
        code="semantic.cue_order", message="fixture", path=("dialogueCues",)
    )

    assert scene_beats_cue_order_repair_facts(
        output, (cue_order_issue, extra_issue)
    ) == ()


def test_cue_order_fact_invariants_fail_closed() -> None:
    assignment = CueOrderRepairAssignment(
        local_cue_id="cue-a", beat_local_id="beat-a", expected_order=1
    )
    with pytest.raises(ValidationError, match="complete dialogueCues"):
        CueOrderRepairFact(
            code="semantic.cue_order",
            path=("dialogueCues", 0, "order"),
            assignments=(assignment,),
        )
    with pytest.raises(ValidationError, match="local cue IDs must be unique"):
        CueOrderRepairFact(
            code="semantic.cue_order",
            path=("dialogueCues",),
            assignments=(assignment, assignment),
        )
    with pytest.raises(ValidationError, match="contiguous within each beat"):
        CueOrderRepairFact(
            code="semantic.cue_order",
            path=("dialogueCues",),
            assignments=(
                assignment,
                CueOrderRepairAssignment(
                    local_cue_id="cue-b", beat_local_id="beat-a", expected_order=3
                ),
            ),
        )
    with pytest.raises(ValidationError, match="canonical local cue ID order"):
        CueOrderRepairFact(
            code="semantic.cue_order",
            path=("dialogueCues",),
            assignments=(
                CueOrderRepairAssignment(
                    local_cue_id="cue-b", beat_local_id="beat-b", expected_order=1
                ),
                assignment,
            ),
        )


def test_storyboard_timing_facts_are_text_free_and_path_bound() -> None:
    guidance = StoryboardTimingGuidance(
        scene_id="scene-a",
        scene_duration_budget_units=5,
        min_shots=1,
        max_shots=2,
        configured_max_shots=2,
        beats=(
            {"beatId": "beat-a", "order": 1},
        ),
        cues=(
            StoryboardCueTimingGuidance(
                cue_id="cue-a", beat_id="beat-a", beat_order=1, cue_order=1,
                estimated_duration_units=3,
            ),
            StoryboardCueTimingGuidance(
                cue_id="cue-b", beat_id="beat-a", beat_order=1, cue_order=2,
                estimated_duration_units=2,
            ),
        ),
    )
    output = _storyboard_output(beat_ids=["beat-a"])
    output["shots"][0]["durationUnits"] = 4
    output["shots"][0]["cueIds"] = ["cue-a", "cue-b"]
    facts = storyboard_timing_repair_facts(
        output,
        (
            ValidationIssue(
                code="semantic.cue_duration_exceeds_shot",
                message="fixture",
                path=("shots", 0, "cueIds"),
            ),
        ),
        guidance=guidance,
    )
    assert len(facts) == 1
    fact = facts[0]
    assert fact.plan_hash == fact.plan.plan_hash
    assert fact.plan.target_shots[0].target_cue_ids == ("cue-a", "cue-b")
    assert fact.plan.target_shots[0].target_duration_units == 5
    assert "text" not in fact.model_dump(mode="json", by_alias=True)


def test_storyboard_timing_plan_is_shared_by_issues_and_suppresses_audio_facts() -> None:
    guidance = build_storyboard_timing_guidance(
        scene_id="scene-a",
        scene_duration_budget_units=5,
        min_shots=2,
        configured_max_shots=2,
        beats=[{"id": "beat-a", "order": 1}],
        cues=[
            {"id": "cue-a", "beatId": "beat-a", "order": 1, "estimatedDurationUnits": 3},
            {"id": "cue-b", "beatId": "beat-a", "order": 2, "estimatedDurationUnits": 2},
        ],
    )
    output = _storyboard_output(beat_ids=["beat-a"])
    second = deepcopy(output["shots"][0])
    second.update({"localShotId": "shot-b", "order": 2, "durationUnits": 2})
    output["shots"] = [output["shots"][0], second]
    output["shots"][0].update(
        {
            "durationUnits": 4,
            "cueIds": ["cue-a", "cue-b"],
            "audioPlan": {
                "events": [
                    {"kind": "ambience", "description": "x", "startOffsetUnits": 4, "durationUnits": 2}
                ]
            },
        }
    )
    output["primaryShotLocalIdByBeat"] = {"beat-a": "shot-a"}
    output["supportingBeatLinks"] = [
        {"shotLocalId": "shot-b", "beatId": "beat-a", "coverageWeight": 1.0}
    ]
    issues = (
        ValidationIssue(code="semantic.shot_duration_budget_exceeded", message="fixture", path=("shots",)),
        ValidationIssue(code="semantic.cue_duration_exceeds_shot", message="fixture", path=("shots", 0, "cueIds")),
        ValidationIssue(code="semantic.audio_timing", message="fixture", path=("shots", 0, "audioPlan", "events", 0, "durationUnits")),
    )
    facts = semantic_repair_facts(
        output, issues, stage=StageName.STORYBOARD, storyboard_timing_guidance=guidance
    )
    assert len(facts) == 2
    assert all(isinstance(fact, StoryboardTimingRepairPlanFact) for fact in facts)
    assert len({fact.plan_hash for fact in facts}) == 1
    plan = facts[0].plan
    assert [(shot.local_shot_id, shot.target_duration_units, shot.target_cue_ids) for shot in plan.target_shots] == [
        ("shot-a", 3, ("cue-a",)),
        ("shot-b", 2, ("cue-b",)),
    ]
    assert plan.target_shots[0].remove_audio_event_indexes == (0,)


def test_storyboard_timing_plan_rejects_rehashed_invalid_coverage() -> None:
    guidance = build_storyboard_timing_guidance(
        scene_id="scene-a", scene_duration_budget_units=3, min_shots=1,
        configured_max_shots=1, beats=[{"id": "beat-a", "order": 1}],
        cues=[{"id": "cue-a", "beatId": "beat-a", "order": 1, "estimatedDurationUnits": 3}],
    )
    output = _storyboard_output(beat_ids=["beat-a"])
    output["shots"][0].update({"durationUnits": 1, "cueIds": ["cue-a"]})
    fact = storyboard_timing_repair_facts(
        output,
        (ValidationIssue(code="semantic.cue_duration_exceeds_shot", message="fixture", path=("shots", 0, "cueIds")),),
        guidance=guidance,
    )[0]
    payload = fact.model_dump(mode="json", by_alias=True)
    payload["plan"]["targetPrimaryLinks"][0]["shotLocalId"] = "not-a-shot"
    unsigned = {key: value for key, value in payload["plan"].items() if key != "planHash"}
    payload["plan"]["planHash"] = hashlib.sha256(
        finite_canonical_json(unsigned).encode("utf-8")
    ).hexdigest()
    payload["planHash"] = payload["plan"]["planHash"]
    with pytest.raises(ValidationError, match="primary map references"):
        StoryboardTimingRepairPlanFact.model_validate(payload)


@pytest.mark.parametrize(
    ("budget", "min_shots", "cues"),
    [
        (1, 2, []),
        (1, 2, [{"id": "cue-a", "beatId": "beat-a", "order": 1, "estimatedDurationUnits": 1}]),
    ],
)
def test_storyboard_timing_infeasible_before_provider_for_empty_or_minimum_cues(
    budget: int, min_shots: int, cues: list[dict],
) -> None:
    with pytest.raises(StoryboardTimingInfeasibleError) as exc:
        build_storyboard_timing_guidance(
            scene_id="scene-a", scene_duration_budget_units=budget,
            min_shots=min_shots, configured_max_shots=2,
            beats=[{"id": "beat-a", "order": 1}], cues=cues,
        )
    assert exc.value.code == "contract.storyboard_timing_infeasible"


def test_join_exact_json_null_survives_repair_fact_rendering() -> None:
    fact = parse_semantic_repair_fact(
        {
            "code": "semantic.join_state_effect_missing",
            "path": ["edges", "edge-a", "stateEffects", "route"],
            "joinContractId": "join-a",
            "joinNodeId": "node-a",
            "stateKey": "route",
            "mode": "convergent",
            "incomingEdges": [
                {"edgeId": "edge-a", "sourceNodeId": "left"},
                {"edgeId": "edge-b", "sourceNodeId": "right"},
            ],
            "repairAction": "set_missing",
            "hasExpectedValue": True,
            "expectedValue": None,
            "preservedStateEffects": [
                {
                    "stateKey": "variant",
                    "incomingEffects": [
                        {"edgeId": "edge-a", "expectedValue": None},
                        {"edgeId": "edge-b", "expectedValue": {"branch": 2}},
                    ],
                }
            ],
        }
    )
    serialized = serialize_semantic_repair_fact(fact)
    assert serialized["hasExpectedValue"] is True
    assert "expectedValue" in serialized and serialized["expectedValue"] is None
    assert serialized["preservedStateEffects"][0]["incomingEffects"][0] == {
        "edgeId": "edge-a",
        "expectedValue": None,
    }
    issue = ValidationIssue(code=fact.code, message="stable", path=fact.path)
    instruction_plan = compile_correction_instruction_plan([issue], [fact])
    rendered = PromptRenderer().render(
        "work_unit_correction",
        {
            "original_contract": {},
            "response_schema": {},
            "previous_final_content": "{}",
            "validation_issues": [
                {"code": fact.code, "path": list(fact.path)}
            ],
            "repair_evidence_projection": instruction_plan.prompt_evidence,
            "correction_directives": [
                directive.model_dump(mode="json")
                for directive in instruction_plan.directives
            ],
            "correction_ordinal": 1,
            "correction_strategy": "repair_previous_final",
        },
    )
    assert '"hasExpectedValue":true' in rendered.messages[1].content
    assert '"expectedValue":null' in rendered.messages[1].content
    projected = instruction_plan.prompt_evidence["facts"][0]
    assert projected["preservedStateEffects"][0]["incomingEffects"][0] == {
        "edgeId": "edge-a",
        "expectedValue": None,
    }


@pytest.mark.parametrize("expected_value", [None, "unauthorized"])
def test_join_repair_fact_rejects_explicit_expected_value_without_authority(
    expected_value: object,
) -> None:
    payload = {
        "code": "semantic.join_state_effect_missing",
        "path": ["edges", "edge-a", "stateEffects", "route"],
        "joinContractId": "join-a",
        "joinNodeId": "node-a",
        "stateKey": "route",
        "mode": "convergent",
        "incomingEdges": [
            {"edgeId": "edge-a", "sourceNodeId": "left"},
            {"edgeId": "edge-b", "sourceNodeId": "right"},
        ],
        "repairAction": "set_missing",
        "hasExpectedValue": False,
        "expectedValue": expected_value,
    }
    with pytest.raises(ValidationError, match="expectedValue requires"):
        parse_semantic_repair_fact(payload)


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
    assert compiled.rendered.output.schema_id == "scene_beats.fragment.v12"
    assert "allowedStates" in message
    assert "scene.entryState →" in message
    scene_properties = compiled.response_schema["properties"]["scenes"]["items"][
        "properties"
    ]
    assert "storyNodeId" not in compiled.response_schema["properties"]
    assert "storyNodeId" not in scene_properties
    assert "beatLocalIds" not in scene_properties
    assert "beatIds" not in scene_properties
    assert "localSceneId" in scene_properties
    cue_schema = compiled.response_schema["properties"]["dialogueCues"]["items"]
    assert cue_schema["properties"]["order"]["description"] == (
        "One-based contiguous dialogue order within this cue's beatLocalId."
    )
    assert "exactly one of speakerId and voiceOver" in cue_schema["properties"][
        "speakerId"
    ]["description"]
    assert "exactly one of speakerId and voiceOver" in cue_schema["properties"][
        "voiceOver"
    ]["description"]
    assert "oneOf" not in cue_schema
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


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (_state().model_copy(update={"facts": {"x": 1}}), _state().model_copy(update={"facts": {"x": 1.0}}), False),
        (_state().model_copy(update={"facts": {"x": "same"}}), _state().model_copy(update={"facts": {"x": "same"}}), True),
    ],
)
def test_fragment_and_canonical_continuity_use_identical_finite_json_identity(
    left: ContinuityStateV2,
    right: ContinuityStateV2,
    expected: bool,
) -> None:
    """Fragment checks must use the same value identity as canonical gates."""

    assert continuity_states_are_compatible(left, right) is expected
    assert _continuity_states_are_compatible(left, right) is expected


def test_nonfinite_continuity_facts_are_rejected_locally_and_canonically() -> None:
    state = _state().model_copy(update={"facts": {"x": float("nan")}})
    local = continuity_state_issues(state, bible=_bible(), path=("scenes", 0, "entryState"))
    canonical = _continuity_state_issues("scenes.scene-a.entryState", state, _bible())

    assert [(issue.code, issue.path) for issue in local] == [
        ("semantic.continuity_fact_not_json", ("scenes", 0, "entryState", "facts", "x"))
    ]
    assert [(issue["code"], issue["path"]) for issue in canonical] == [
        ("continuity_fact_not_json", "scenes.scene-a.entryState.facts.x")
    ]


@pytest.mark.parametrize(
    "invalid_value",
    [
        ("tuple values are not JSON arrays",),
        {1: "object keys must stay strings"},
        object(),
    ],
)
def test_non_native_continuity_facts_are_rejected_locally_and_canonically(
    invalid_value: object,
) -> None:
    """The fragment and canonical boundaries reject the same non-JSON value."""

    state = _state().model_copy(update={"facts": {"x": invalid_value}})
    local = continuity_state_issues(
        state,
        bible=_bible(),
        path=("scenes", 0, "entryState"),
    )
    canonical = _continuity_state_issues(
        "scenes.scene-a.entryState",
        state,
        _bible(),
    )

    assert [(issue.code, issue.path) for issue in local] == [
        ("semantic.continuity_fact_not_json", ("scenes", 0, "entryState", "facts", "x"))
    ]
    assert [(issue["code"], issue["path"]) for issue in canonical] == [
        ("continuity_fact_not_json", "scenes.scene-a.entryState.facts.x")
    ]


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

    with pytest.raises(ValidationError, match="compiler hashes"):
        WorkUnitPromptContract.model_validate(
            {
                **primary,
                "correction_ordinal": 1,
                "correction_strategy": "repair_previous_final",
            }
        )

    with pytest.raises(ValidationError, match="current correction policy"):
        WorkUnitPromptContract.model_validate(
            {**primary, "correction_policy_version": "bounded_correction.future"}
        )

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        WorkUnitPromptContract.model_validate(
            {
                **primary,
                "correction_ordinal": 1,
                "correction_strategy": "repair_previous_final",
                "correction_directive_set_hash": "g" * 64,
                "correction_evidence_projection_hash": "0" * 64,
                "correction_issue_selection_hash": "0" * 64,
                "correction_response_schema_hash": "0" * 64,
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
            StoryEdgeV2(id="edge-a-b", source_node_id="node-a", target_node_id="node-b", kind="choice", choice_text="直接汇流", state_effects={"船钟归属": "由摆渡人保管"}),
            StoryEdgeV2(id="edge-a-c", source_node_id="node-a", target_node_id="node-c", kind="choice", choice_text="先走乙线", state_effects={}),
            StoryEdgeV2(id="edge-c-b", source_node_id="node-c", target_node_id="node-b", kind="continuation", choice_text=None, state_effects={"船钟归属": "由摆渡人保管"}),
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
    assert entry_schema["properties"]["facts"]["properties"]["船钟归属"] == {
        "const": "由摆渡人保管"
    }
    assert '"requiredEntryFactKeys":["船钟归属"]' in compiled.rendered.messages[1].content

    output = _scene_output()
    missing = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert missing.accepted is False
    assert "schema.missing" in {issue.code for issue in missing.issues}

    output["scenes"][0]["entryState"]["facts"] = {"船钟归属": "错误值"}
    mismatched = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert mismatched.accepted is False
    assert {issue.code for issue in mismatched.issues} == {
        "semantic.join_entry_state_value_mismatch"
    }

    output["scenes"][0]["entryState"]["facts"] = {"船钟归属": "由摆渡人保管"}
    accepted = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert accepted.accepted is True


def test_scene_fragment_rejects_nonfinite_join_fact_and_continuity_delta() -> None:
    compiled, _, _, _, _ = _compile_scene_beats()
    output = _scene_output()
    output["scenes"][0]["entryState"]["facts"] = {"bad": float("nan")}
    output["beats"][0]["continuityDelta"] = {"bad": float("nan")}

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert {issue.code for issue in report.issues} == {
        "semantic.continuity_fact_not_json",
        "semantic.continuity_delta_not_json",
    }


def test_scene_beats_compilation_requires_the_exact_stage_plan_join_marker() -> None:
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    brief, snapshot, plan, _, _, _ = _plan_and_inputs()
    assert stage_plan.join_state_value_contract_version == "join_required_state_values.v1"
    assert stage_plan.join_state_value_contract_hash == (
        compiled.contract.join_state_value_contract_hash
    )

    tampered = stage_plan.model_copy(
        update={"join_state_value_contract_hash": "0" * 64}
    )
    with pytest.raises(WorkUnitContractError, match="does not match"):
        compile_work_unit_request(
            generation_plan=plan,
            stage_plan=tampered,
            work_unit=unit,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
            brief=brief,
            canonical_snapshot=snapshot,
            instructions="preserve the project brief",
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
    assert "beat.order、再按该 beat 内 cue.order" in compiled.rendered.messages[1].content
    assert "实体必须实际出现在同一 shot" in compiled.rendered.messages[1].content
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


def test_storyboard_audio_event_ids_are_deterministic_and_contracts_preserve_history() -> None:
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

    historical = compiled.contract.snapshot_dump()
    historical["contract_version"] = "m1.12j"
    historical["correction_policy_version"] = "bounded_correction.v14"
    historical.pop("audio_event_id_binding_version")
    historical.pop("correction_directive_registry_version")
    historical.pop("correction_evidence_projection_version")
    historical.pop("correction_issue_selection_version")
    historical.pop("correction_response_schema_version")
    parsed = WorkUnitPromptContract.model_validate(historical)
    assert parsed.snapshot_dump() == historical


def test_v15_timing_plan_fact_remains_readable_without_guidance_injection() -> None:
    """Terminal v15 evidence stays inspectable but cannot become v16 authority."""

    historical = {
        "code": "semantic.cue_duration_exceeds_shot",
        "path": ["shots", 0, "cueIds"],
        "plan": {"version": "storyboard_timing_repair_plan.v1", "planHash": "old-plan"},
        "planHash": "old-plan",
    }

    parsed = parse_semantic_repair_fact(historical)

    assert serialize_semantic_repair_fact(parsed) == historical


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
                ShotContent(local_shot_id="shot-a", order=1, title="苏醒", shot_size="close_up", duration_units=1, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=[], audio_plan={"events": []}, character_ids=[], location_id=None, prop_ids=[], required_entity_states=[], entry_state=_state(), exit_state=_state()),
            ShotContent(local_shot_id="shot-b", order=2, title="反应", shot_size="medium", duration_units=1, camera_angle="", camera_movement="", composition="", visual_intent="", motion_intent="", action="", transition="", cue_ids=[], audio_plan={"events": []}, character_ids=[], location_id=None, prop_ids=[], required_entity_states=[], entry_state=_state(), exit_state=_state()),
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


def test_scene_fragment_rejects_invalid_continuity_vocabulary_and_sequence_before_binding() -> None:
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
    invalid_vocabulary["scenes"][0]["entryState"] = _character_state("missing").model_dump(
        mode="json", by_alias=True
    )
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


def test_continuity_state_correction_rebinds_exact_response_entry_to_bible_vocabulary() -> None:
    brief, snapshot, plan, _, graph, _ = _plan_and_inputs()
    bible = _bible_with_hero()
    stage_plan = plan_stage(
        plan, stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph}, brief=brief,
    )
    unit = stage_plan.work_units[0]
    compiled = compile_work_unit_request(
        generation_plan=plan, stage_plan=stage_plan, work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief, canonical_snapshot=snapshot, instructions="preserve the project brief",
    )
    rejected_value = _scene_output()
    rejected_value["scenes"][0]["entryState"] = _character_state("missing").model_dump(
        mode="json", by_alias=True
    )
    report = compiled.validator.validate(
        rejected_value, context=SemanticValidationContext(stage="scene_beats")
    )
    facts = semantic_repair_facts(
        rejected_value, report.issues, stage=StageName.SCENE_BEATS, bible=bible,
        scoped_context=compiled.validator.scoped_context,
        dialogue_capacity_guidance=compiled.contract.dialogue_capacity_guidance,
        dialogue_timing_profile=stage_plan.dialogue_timing_profile,
        node_duration_budget_units=compiled.contract.node_duration_budget_units,
        join_state_value_requirements=compiled.validator.scoped_context["join_state_value_requirements"],
    )
    fact = next(item for item in facts if isinstance(item, ContinuityEntityStateRepairFact))
    assert fact.path == ("scenes", 0, "entryState", "entityStates", 0, "state")
    assert fact.entity_id == "hero"
    assert fact.allowed_states == ("alert", "calm")
    assert_continuity_entity_state_repair_fact_matches_source(
        fact, rejected_value, stage=StageName.SCENE_BEATS, bible=bible
    )
    directive_plan = compile_correction_instruction_plan(report.issues, facts)
    assert "continuity_values" in [directive.id for directive in directive_plan.directives]
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
