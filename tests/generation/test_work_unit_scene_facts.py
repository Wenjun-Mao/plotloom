"""test work unit scene facts behavior contracts."""

from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest
from pydantic import ValidationError

from plotloom.domain import StageName
from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.storyboard_timing_repair import (
    StoryboardTimingInfeasibleError,
    StoryboardTimingRepairPlanFact,
    build_storyboard_timing_guidance,
)
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    CueOrderRepairAssignment,
    CueOrderRepairFact,
    StoryboardCueTimingGuidance,
    StoryboardTimingGuidance,
    assert_cue_order_repair_fact_matches_source,
    parse_semantic_repair_fact,
    scene_beats_cue_order_repair_facts,
    scene_beats_dialogue_node_budget_repair_facts,
    semantic_repair_facts,
    serialize_semantic_repair_fact,
    storyboard_timing_repair_facts,
)
from plotloom.json_value_contract import finite_canonical_json
from tests.generation.work_unit_contract_fixtures import (
    _compile_scene_beats,
    _cue_order_output,
    _scene_output,
    _storyboard_output,
)


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
        issue for issue in report.issues if issue.code == "semantic.cue_order"
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

    assert (
        scene_beats_cue_order_repair_facts(output, (cue_order_issue, extra_issue)) == ()
    )


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
        beats=({"beatId": "beat-a", "order": 1},),
        cues=(
            StoryboardCueTimingGuidance(
                cue_id="cue-a",
                beat_id="beat-a",
                beat_order=1,
                cue_order=1,
                estimated_duration_units=3,
            ),
            StoryboardCueTimingGuidance(
                cue_id="cue-b",
                beat_id="beat-a",
                beat_order=1,
                cue_order=2,
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


def test_storyboard_timing_plan_is_shared_by_issues_and_suppresses_audio_facts() -> (
    None
):
    guidance = build_storyboard_timing_guidance(
        scene_id="scene-a",
        scene_duration_budget_units=5,
        min_shots=2,
        configured_max_shots=2,
        beats=[{"id": "beat-a", "order": 1}],
        cues=[
            {
                "id": "cue-a",
                "beatId": "beat-a",
                "order": 1,
                "estimatedDurationUnits": 3,
            },
            {
                "id": "cue-b",
                "beatId": "beat-a",
                "order": 2,
                "estimatedDurationUnits": 2,
            },
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
                    {
                        "kind": "ambience",
                        "description": "x",
                        "startOffsetUnits": 4,
                        "durationUnits": 2,
                    }
                ]
            },
        }
    )
    output["primaryShotLocalIdByBeat"] = {"beat-a": "shot-a"}
    output["supportingBeatLinks"] = [
        {"shotLocalId": "shot-b", "beatId": "beat-a", "coverageWeight": 1.0}
    ]
    issues = (
        ValidationIssue(
            code="semantic.shot_duration_budget_exceeded",
            message="fixture",
            path=("shots",),
        ),
        ValidationIssue(
            code="semantic.cue_duration_exceeds_shot",
            message="fixture",
            path=("shots", 0, "cueIds"),
        ),
        ValidationIssue(
            code="semantic.audio_timing",
            message="fixture",
            path=("shots", 0, "audioPlan", "events", 0, "durationUnits"),
        ),
    )
    facts = semantic_repair_facts(
        output, issues, stage=StageName.STORYBOARD, storyboard_timing_guidance=guidance
    )
    assert len(facts) == 2
    assert all(isinstance(fact, StoryboardTimingRepairPlanFact) for fact in facts)
    assert len({fact.plan_hash for fact in facts}) == 1
    plan = facts[0].plan
    assert [
        (shot.local_shot_id, shot.target_duration_units, shot.target_cue_ids)
        for shot in plan.target_shots
    ] == [
        ("shot-a", 3, ("cue-a",)),
        ("shot-b", 2, ("cue-b",)),
    ]
    assert plan.target_shots[0].remove_audio_event_indexes == (0,)


def test_storyboard_timing_plan_rejects_rehashed_invalid_coverage() -> None:
    guidance = build_storyboard_timing_guidance(
        scene_id="scene-a",
        scene_duration_budget_units=3,
        min_shots=1,
        configured_max_shots=1,
        beats=[{"id": "beat-a", "order": 1}],
        cues=[
            {"id": "cue-a", "beatId": "beat-a", "order": 1, "estimatedDurationUnits": 3}
        ],
    )
    output = _storyboard_output(beat_ids=["beat-a"])
    output["shots"][0].update({"durationUnits": 1, "cueIds": ["cue-a"]})
    fact = storyboard_timing_repair_facts(
        output,
        (
            ValidationIssue(
                code="semantic.cue_duration_exceeds_shot",
                message="fixture",
                path=("shots", 0, "cueIds"),
            ),
        ),
        guidance=guidance,
    )[0]
    payload = fact.model_dump(mode="json", by_alias=True)
    payload["plan"]["targetPrimaryLinks"][0]["shotLocalId"] = "not-a-shot"
    unsigned = {
        key: value for key, value in payload["plan"].items() if key != "planHash"
    }
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
        (
            1,
            2,
            [
                {
                    "id": "cue-a",
                    "beatId": "beat-a",
                    "order": 1,
                    "estimatedDurationUnits": 1,
                }
            ],
        ),
    ],
)
def test_storyboard_timing_infeasible_before_provider_for_empty_or_minimum_cues(
    budget: int,
    min_shots: int,
    cues: list[dict],
) -> None:
    with pytest.raises(StoryboardTimingInfeasibleError) as exc:
        build_storyboard_timing_guidance(
            scene_id="scene-a",
            scene_duration_budget_units=budget,
            min_shots=min_shots,
            configured_max_shots=2,
            beats=[{"id": "beat-a", "order": 1}],
            cues=cues,
        )
    assert exc.value.code == "contract.storyboard_timing_infeasible"
