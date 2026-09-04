from __future__ import annotations

import copy
import json

import pytest

from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.correction_directives import (
    CORRECTION_DIRECTIVE_REGISTRY_VERSION,
    CorrectionDirectivePlanError,
    SUPPORTED_CORRECTION_ISSUE_CODES,
    compile_correction_instruction_plan,
)
from plotloom.generation.work_units import parse_semantic_repair_fact


def _issue(code: str, path: tuple[str | int, ...]) -> ValidationIssue:
    return ValidationIssue(code=code, message="stable fixture", path=path)


def _join_allowed_fact():
    return parse_semantic_repair_fact(
        {
            "code": "semantic.join_allowed_differences_must_be_required",
            "path": ["joinContracts", "join-a", "allowedDifferences"],
            "joinContractId": "join-a",
            "missingRequiredStateKeys": ["route"],
            "expectedRequiredStateKeys": ["shared", "route"],
            "expectedAllowedDifferences": ["route"],
            "newRequiredKeyIncomingEdges": [
                {
                    "stateKey": "route",
                    "incomingEdges": [
                        {"edgeId": "edge-a", "sourceNodeId": "left"},
                        {"edgeId": "edge-b", "sourceNodeId": "right"},
                    ],
                }
            ],
        }
    )


def _join_effect_fact(
    edge_id: str,
    *,
    has_expected_value: bool = False,
):
    payload = {
        "code": "semantic.join_state_effect_missing",
        "path": ["edges", edge_id, "stateEffects", "shared"],
        "joinContractId": "join-a",
        "joinNodeId": "join-node",
        "stateKey": "shared",
        "mode": "convergent",
        "incomingEdges": [
            {"edgeId": "edge-a", "sourceNodeId": "left"},
            {"edgeId": "edge-b", "sourceNodeId": "right"},
        ],
        "repairAction": "set_missing",
        "hasExpectedValue": has_expected_value,
    }
    if has_expected_value:
        payload["expectedValue"] = {"stable": True}
    return parse_semantic_repair_fact(payload)


def test_single_typed_fact_selects_only_its_static_directive() -> None:
    fact = _join_allowed_fact()
    issue = _issue(fact.code, fact.path)

    plan = compile_correction_instruction_plan([issue], [fact])

    assert plan.registry_version == CORRECTION_DIRECTIVE_REGISTRY_VERSION
    assert [directive.id for directive in plan.directives] == [
        "join_allowed_differences"
    ]
    assert "JoinAllowedDifferencesRepairFact" in plan.directives[0].text
    assert plan.prompt_evidence["facts"] == [
        fact.model_dump(mode="json", by_alias=True, exclude_none=True)
    ]
    assert plan.prompt_evidence["joinStateEffectGroups"] == []


def test_directive_order_and_hashes_are_stable_not_issue_ordered() -> None:
    allowed = _join_allowed_fact()
    effect = _join_effect_fact("edge-a")
    issues = [_issue(effect.code, effect.path), _issue(allowed.code, allowed.path)]

    first = compile_correction_instruction_plan(issues, [effect, allowed])
    second = compile_correction_instruction_plan(
        copy.deepcopy(issues), copy.deepcopy([effect, allowed])
    )

    assert [directive.id for directive in first.directives] == [
        "join_allowed_differences",
        "join_state_effect",
    ]
    assert first.directive_set_hash == second.directive_set_hash
    assert first.evidence_projection_hash == second.evidence_projection_hash
    assert first.prompt_evidence == second.prompt_evidence


def test_operationally_identical_join_effect_facts_are_losslessly_grouped() -> None:
    left = _join_effect_fact("edge-a")
    right = _join_effect_fact("edge-b")
    issues = [_issue(left.code, left.path), _issue(right.code, right.path)]
    original_payloads = [
        fact.model_dump(mode="json", by_alias=True, exclude_none=True)
        for fact in (left, right)
    ]

    plan = compile_correction_instruction_plan(issues, [left, right])

    assert plan.prompt_evidence["facts"] == []
    assert plan.prompt_evidence["joinStateEffectGroups"] == [
        {
            "code": "semantic.join_state_effect_missing",
            "joinContractId": "join-a",
            "joinNodeId": "join-node",
            "stateKey": "shared",
            "mode": "convergent",
            "incomingEdges": [
                {"edgeId": "edge-a", "sourceNodeId": "left"},
                {"edgeId": "edge-b", "sourceNodeId": "right"},
            ],
            "repairAction": "set_missing",
            "hasExpectedValue": False,
            "sourceFactIndexes": [0, 1],
            "issuePaths": [
                ["edges", "edge-a", "stateEffects", "shared"],
                ["edges", "edge-b", "stateEffects", "shared"],
            ],
        }
    ]
    assert [
        fact.model_dump(mode="json", by_alias=True, exclude_none=True)
        for fact in (left, right)
    ] == original_payloads


def test_join_effect_facts_with_different_authority_are_not_grouped() -> None:
    without_value = _join_effect_fact("edge-a")
    with_value = _join_effect_fact("edge-b", has_expected_value=True)
    issues = [
        _issue(without_value.code, without_value.path),
        _issue(with_value.code, with_value.path),
    ]

    plan = compile_correction_instruction_plan(issues, [without_value, with_value])

    assert plan.prompt_evidence["joinStateEffectGroups"] == []
    assert plan.prompt_evidence["facts"] == [
        without_value.model_dump(mode="json", by_alias=True, exclude_none=True),
        {
            **with_value.model_dump(mode="json", by_alias=True, exclude_none=True),
            "expectedValue": {"stable": True},
        },
    ]


def test_required_typed_fact_and_unknown_semantic_code_fail_closed() -> None:
    missing_fact_issue = _issue(
        "semantic.join_allowed_differences_must_be_required",
        ("joinContracts", "join-a", "allowedDifferences"),
    )
    with pytest.raises(CorrectionDirectivePlanError, match="requires a matching"):
        compile_correction_instruction_plan([missing_fact_issue], [])

    unknown = _issue("semantic.future_unmodeled_contract", ("graph",))
    with pytest.raises(CorrectionDirectivePlanError, match="unsupported correction issue"):
        compile_correction_instruction_plan([unknown], [])

    sequence_without_blocker = _issue(
        "semantic.continuity_beat_sequence_mismatch",
        ("scenes", 0),
    )
    with pytest.raises(CorrectionDirectivePlanError, match="requires a matching"):
        compile_correction_instruction_plan([sequence_without_blocker], [])


@pytest.mark.parametrize(
    ("blocker_code", "blocker_path", "sequence_code", "sequence_path"),
    [
        (
            "semantic.invalid_continuity_entity_state",
            ("beats", 0, "entryState", "entityStates", 0, "state"),
            "semantic.continuity_beat_sequence_mismatch",
            ("scenes", 0),
        ),
        (
            "semantic.unknown_continuity_entity",
            ("shots", 0, "entryState", "entityStates", 0, "entityId"),
            "semantic.continuity_shot_sequence_mismatch",
            ("shots",),
        ),
        (
            "semantic.continuity_fact_not_json",
            ("shots", 0, "entryState", "facts", "position"),
            "semantic.continuity_shot_sequence_mismatch",
            ("shots",),
        ),
    ],
)
def test_derived_continuity_issue_is_deferred_until_exact_fact_is_safe(
    blocker_code: str,
    blocker_path: tuple[str | int, ...],
    sequence_code: str,
    sequence_path: tuple[str | int, ...],
) -> None:
    blocker = _issue(blocker_code, blocker_path)
    sequence = _issue(sequence_code, sequence_path)

    plan = compile_correction_instruction_plan([blocker, sequence], [])

    assert plan.executable_issue_indexes == (0,)
    assert plan.deferred_issue_indexes == (1,)
    assert plan.executable_fact_indexes == ()
    assert [directive.id for directive in plan.directives] == [
        "continuity_values"
    ]
    selection = plan.prompt_evidence["issueSelection"]
    assert set(selection) == {"version", "executableIssues", "factBindings"}
    assert selection["executableIssues"] == [
        {"code": blocker_code, "path": list(blocker_path)}
    ]
    assert selection["factBindings"] == []
    prompt_evidence_json = json.dumps(
        plan.prompt_evidence,
        ensure_ascii=False,
        sort_keys=True,
    )
    assert sequence_code not in prompt_evidence_json
    assert json.dumps(list(sequence_path), ensure_ascii=False) not in prompt_evidence_json
    assert "deferredIssues" not in prompt_evidence_json
    assert "allIssues" not in prompt_evidence_json
    assert plan.audit_issue_selection["deferredIssues"] == [
        {
            "code": sequence_code,
            "path": list(sequence_path),
            "reasonCode": "authority.sequence_fact_blocked_by_invalid_state",
            "blockingIssues": [
                {"code": blocker_code, "path": list(blocker_path)}
            ],
        }
    ]

    same_authority = compile_correction_instruction_plan(
        [
            blocker.model_copy(update={"message": "different diagnostic prose"}),
            sequence.model_copy(update={"message": "also different"}),
        ],
        [],
    )
    assert same_authority.issue_selection_hash == plan.issue_selection_hash
    assert same_authority.evidence_projection_hash == plan.evidence_projection_hash

    different_deferred_path = compile_correction_instruction_plan(
        [blocker, sequence.model_copy(update={"path": ("scenes", 1)})],
        [],
    )
    assert different_deferred_path.issue_selection_hash != plan.issue_selection_hash
    assert different_deferred_path.prompt_evidence == plan.prompt_evidence
    assert (
        different_deferred_path.evidence_projection_hash
        == plan.evidence_projection_hash
    )


def test_continuity_delta_error_cannot_defer_missing_sequence_authority() -> None:
    delta = _issue(
        "semantic.continuity_delta_not_json",
        ("beats", 0, "continuityDelta", "position"),
    )
    sequence = _issue(
        "semantic.continuity_beat_sequence_mismatch",
        ("scenes", 0),
    )

    with pytest.raises(CorrectionDirectivePlanError, match="requires a matching"):
        compile_correction_instruction_plan([delta, sequence], [])


def test_prompt_fact_bindings_use_executable_local_issue_indexes() -> None:
    sequence = _issue(
        "semantic.continuity_beat_sequence_mismatch",
        ("scenes", 0),
    )
    blocker = _issue(
        "semantic.invalid_continuity_entity_state",
        ("beats", 0, "entryState", "entityStates", 0, "state"),
    )
    fact = _join_allowed_fact()
    fact_issue = _issue(fact.code, fact.path)

    plan = compile_correction_instruction_plan(
        [sequence, blocker, fact_issue],
        [fact],
    )

    assert plan.executable_issue_indexes == (1, 2)
    assert plan.deferred_issue_indexes == (0,)
    selection = plan.prompt_evidence["issueSelection"]
    assert selection["factBindings"] == [
        {
            "factIndex": 0,
            "issueIndex": 1,
            "code": fact.code,
            "path": list(fact.path),
            "model": "JoinAllowedDifferencesRepairFact",
        }
    ]
    assert all(
        binding["issueIndex"] < len(selection["executableIssues"])
        for binding in selection["factBindings"]
    )


def test_known_schema_and_extraction_codes_need_no_semantic_fact() -> None:
    plan = compile_correction_instruction_plan(
        [
            _issue("response.extraction", ()),
            _issue("schema.missing", ("title",)),
            _issue("schema.extra_forbidden", ("unexpected",)),
            _issue("schema.greater_than_equal", ("shots", 0, "order")),
        ],
        [],
    )

    assert plan.directives == ()
    assert plan.prompt_evidence["facts"] == []


def test_current_model_correctable_semantic_families_are_registered() -> None:
    assert {
        "binding.missing_id",
        "semantic.continuation_choice_text_must_be_null",
        "semantic.choice_edge_choice_text_required",
        "semantic.unknown_cue_speaker",
        "semantic.dialogue_language_not_authoring_language",
        "semantic.continuity_beat_sequence_mismatch",
        "semantic.continuity_shot_sequence_mismatch",
        "semantic.duplicate_shot_id",
        "semantic.shot_count",
        "semantic.primary_coverage",
    } <= SUPPORTED_CORRECTION_ISSUE_CODES
    # This generic defensive wrapper carries no executable field-level
    # authority and must remain fail-closed until it is replaced by a precise
    # stable issue code.
    assert "semantic.v2_projection_invalid" not in SUPPORTED_CORRECTION_ISSUE_CODES


def test_retired_dialogue_timing_fact_is_read_only_not_current_authority() -> None:
    fact = parse_semantic_repair_fact(
        {
            "code": "semantic.cue_duration_underestimated",
            "path": ["dialogueCues", 0, "estimatedDurationUnits"],
            "timingProfileVersion": "dialogue.default.v1",
            "matchedRuleLanguage": "zh-CN",
            "delivery": "natural",
            "textCharacterCount": 2,
            "unitsPerCharacter": 330,
            "minimumDurationUnits": 660,
            "currentEstimatedDurationUnits": 1,
        }
    )
    issue = _issue(fact.code, fact.path)

    assert fact.code not in SUPPORTED_CORRECTION_ISSUE_CODES
    with pytest.raises(CorrectionDirectivePlanError, match="not supported"):
        compile_correction_instruction_plan([issue], [fact])
