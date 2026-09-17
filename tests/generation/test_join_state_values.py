from __future__ import annotations

import math

import pytest

from plotloom.canonical_schema import (
    JoinContractV2,
    StoryBibleV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.domain import ProjectBrief, StageName
from plotloom.generation.planning import (
    PlanningError,
    create_generation_plan,
    plan_stage,
    work_unit_context,
)
from plotloom.join_state_values import (
    JOIN_STATE_VALUE_CONTRACT_VERSION,
    JOIN_VARIANT_VALUE_VERSION,
    JoinStateValueContract,
    JoinStateValueContractError,
    compile_join_state_value_contract,
)
from plotloom.edge_entry_states import (
    EdgeEntryStateContractError,
    compile_edge_entry_state_contract,
)
from plotloom.canonical_schema import EntityType, RequiredEntityState
from plotloom.validation import DomainValidationError, validate_story_graph


def _graph(
    *,
    left_effects: dict | None = None,
    right_effects: dict | None = None,
    allowed_differences: list[str] | None = None,
    reconciliation: str = "汇流后保留两条路线的来源。",
) -> StoryGraphV2:
    return StoryGraphV2(
        start_node_id="start",
        nodes=[
            StoryNodeV2(id="start", title="开始", summary="开始", kind="start"),
            StoryNodeV2(id="decision", title="选择", summary="选择", kind="decision"),
            StoryNodeV2(id="left", title="左路", summary="左路", kind="scene"),
            StoryNodeV2(id="right", title="右路", summary="右路", kind="scene"),
            StoryNodeV2(id="join", title="汇流", summary="汇流", kind="join"),
            StoryNodeV2(id="ending", title="结局", summary="结局", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(id="start-decision", source_node_id="start", target_node_id="decision", kind="continuation", choice_text=None, state_effects={}),
            StoryEdgeV2(id="choose-left", source_node_id="decision", target_node_id="left", kind="choice", choice_text="左", state_effects={"choice": "left"}),
            StoryEdgeV2(id="choose-right", source_node_id="decision", target_node_id="right", kind="choice", choice_text="右", state_effects={"choice": "right"}),
            StoryEdgeV2(
                id="left-join",
                source_node_id="left",
                target_node_id="join",
                kind="continuation",
                choice_text=None,
                state_effects=left_effects or {"shared": "ready", "route": "left"},
            ),
            StoryEdgeV2(
                id="right-join",
                source_node_id="right",
                target_node_id="join",
                kind="continuation",
                choice_text=None,
                state_effects=right_effects or {"shared": "ready", "route": "right"},
            ),
            StoryEdgeV2(id="join-ending", source_node_id="join", target_node_id="ending", kind="continuation", choice_text=None, state_effects={}),
        ],
        join_contracts=[
            JoinContractV2(
                id="join-contract",
                join_node_id="join",
                incoming_node_ids=["left", "right"],
                required_state_keys=["route", "shared"],
                allowed_differences=allowed_differences or ["route"],
                reconciliation=reconciliation,
                notes="保留来源。",
            )
        ],
    )


def _issue_codes(error: JoinStateValueContractError) -> set[str]:
    return {issue.code for issue in error.issues}


def _brief() -> ProjectBrief:
    return ProjectBrief(
        title="汇流合同测试",
        synopsis="一次选择在保留路线来源后重新汇流。",
        target_playthrough_seconds=24,
        decision_points_per_path=1,
        ending_count=1,
        node_budget=6,
        max_out_degree=2,
        desired_join_count=1,
        shots_per_scene_min=1,
        shots_per_scene_max=2,
    )


def _bible() -> StoryBibleV2:
    return StoryBibleV2(
        logline="两条路线在终点前汇流。",
        premise="不同经历可以被保留，而共享事实必须一致。",
        genre="",
        tone="",
        audience="",
        narrative_promise="",
        visual_language="",
        themes=[],
        world_rules=[],
        known_facts=[],
        open_questions=[],
        source_notes=[],
        characters=[],
        locations=[],
        props=[],
    )


def _generation_plan(brief: ProjectBrief):
    return create_generation_plan(
        run_id="join-state-planning-test",
        requested_stages=[StageName.SCENE_BEATS],
        provider_profile_hash="profile-public-hash",
        canonical_snapshot={
            "projectId": "join-state-project",
            "brief": brief.model_dump(mode="json", by_alias=True),
        },
    )


def test_contract_is_deterministic_and_preserves_allowed_variants() -> None:
    first = compile_join_state_value_contract(_graph())
    second = compile_join_state_value_contract(_graph())

    assert first == second
    assert first.version == JOIN_STATE_VALUE_CONTRACT_VERSION
    assert [entry.state_key for entry in first.entries] == ["route", "shared"]
    by_key = {entry.state_key: entry for entry in first.entries}
    assert by_key["shared"].mode == "convergent"
    assert by_key["shared"].expected_join_entry_value == "ready"
    assert by_key["route"].mode == "variant_map"
    variant = by_key["route"].expected_join_entry_value
    assert variant["$plotloom"] == JOIN_VARIANT_VALUE_VERSION
    assert [item["edgeId"] for item in variant["byIncomingEdge"]] == [
        "left-join",
        "right-join",
    ]
    assert JoinStateValueContract.model_validate(
        first.model_dump(mode="json", by_alias=True),
        by_alias=True,
    ) == first


def test_node_requirements_apply_only_to_post_edge_join_entry() -> None:
    contract = compile_join_state_value_contract(_graph())

    join = contract.requirements_for_node("join")
    assert join["requiredEntryFactKeys"] == ["route", "shared"]
    assert join["requiredEntryFacts"]["shared"] == "ready"
    assert join["outgoingJoinTransitions"] == []
    assert contract.requirements_for_node("start")["requiredEntryFacts"] == {}
    assert contract.requirements_for_node("decision")["requiredEntryFacts"] == {}
    assert contract.requirements_for_node("left")["requiredEntryFacts"] == {}


def test_typed_direct_edge_requirements_preserve_omission_and_fail_closed_at_multiple_inputs() -> None:
    graph = _graph()
    graph.edges[1].entity_state_effects = [
        RequiredEntityState(entity_type=EntityType.CHARACTER, entity_id="mira", state="calm")
    ]
    contract = compile_edge_entry_state_contract(graph)
    assert contract.requirements_for_node("left")["requiredEntityStates"] == [
        {
            "entityType": "character",
            "entityId": "mira",
            "state": "calm",
            "incomingEdgeIds": ["choose-left"],
        }
    ]
    assert contract.requirements_for_node("right")["requiredEntityStates"] == []

    graph.edges[3].entity_state_effects = [
        RequiredEntityState(entity_type=EntityType.CHARACTER, entity_id="mira", state="calm")
    ]
    graph.edges[4].entity_state_effects = [
        RequiredEntityState(entity_type=EntityType.CHARACTER, entity_id="mira", state="calm")
    ]
    convergent = compile_edge_entry_state_contract(graph)
    assert convergent.requirements_for_node("join")["requiredEntityStates"][0]["state"] == "calm"

    graph.edges[4].entity_state_effects = [
        RequiredEntityState(entity_type=EntityType.CHARACTER, entity_id="mira", state="alert")
    ]
    with pytest.raises(EdgeEntryStateContractError) as conflict:
        compile_edge_entry_state_contract(graph)
    assert {issue.code for issue in conflict.value.issues} == {"edge_entry_entity_state_conflict"}


def test_contract_rejects_missing_and_conflicting_incoming_assignments() -> None:
    with pytest.raises(JoinStateValueContractError) as missing:
        compile_join_state_value_contract(
            _graph(right_effects={"route": "right"})
        )
    assert "join_state_effect_missing" in _issue_codes(missing.value)

    with pytest.raises(JoinStateValueContractError) as conflict:
        compile_join_state_value_contract(
            _graph(right_effects={"shared": "different", "route": "right"})
        )
    assert "join_state_effect_conflict" in _issue_codes(conflict.value)
    conflict_issue = next(
        issue for issue in conflict.value.issues if issue.code == "join_state_effect_conflict"
    )
    assert conflict_issue.path.endswith(".requiredStateKeys.shared")


def test_graph_admission_rejects_path_dependent_typed_entry_state_before_scene_beats() -> None:
    """Graph sealing cannot defer an unrepresentable direct-input join to planning."""

    graph = _graph()
    graph.edges[3].entity_state_effects = [
        RequiredEntityState(entity_type=EntityType.CHARACTER, entity_id="mira", state="calm")
    ]
    with pytest.raises(DomainValidationError) as rejected:
        validate_story_graph(graph, _brief(), strict_v2=True)

    issue = next(item for item in rejected.value.issues if item["code"] == "edge_entry_entity_state_incomplete")
    assert issue["path"] == "nodes.join.entityStateEffects.character.mira"
    assert "left-join" in issue["message"]
    assert "right-join" in issue["message"]
    assert "saving or resubmitting" in issue["message"]


def test_graph_admission_examples_match_typed_direct_incoming_prompt_rule() -> None:
    """Omission and equal assignments pass; partial and conflicting ones fail."""

    validate_story_graph(_graph(), _brief(), strict_v2=True)

    equal = _graph()
    for edge in equal.edges[3:5]:
        edge.entity_state_effects = [
            RequiredEntityState(
                entity_type=EntityType.CHARACTER,
                entity_id="mira",
                state="calm",
            )
        ]
    validate_story_graph(equal, _brief(), strict_v2=True)

    incomplete = _graph()
    incomplete.edges[3].entity_state_effects = [
        RequiredEntityState(
            entity_type=EntityType.CHARACTER,
            entity_id="mira",
            state="calm",
        )
    ]
    with pytest.raises(DomainValidationError) as partial_rejection:
        validate_story_graph(incomplete, _brief(), strict_v2=True)
    assert {issue["code"] for issue in partial_rejection.value.issues} >= {
        "edge_entry_entity_state_incomplete"
    }

    conflicting = _graph()
    conflicting.edges[3].entity_state_effects = [
        RequiredEntityState(
            entity_type=EntityType.CHARACTER,
            entity_id="mira",
            state="calm",
        )
    ]
    conflicting.edges[4].entity_state_effects = [
        RequiredEntityState(
            entity_type=EntityType.CHARACTER,
            entity_id="mira",
            state="alert",
        )
    ]
    with pytest.raises(DomainValidationError) as conflict_rejection:
        validate_story_graph(conflicting, _brief(), strict_v2=True)
    assert {issue["code"] for issue in conflict_rejection.value.issues} >= {
        "edge_entry_entity_state_conflict"
    }


def test_contract_rejects_unreconciled_variants_and_non_finite_json() -> None:
    with pytest.raises(JoinStateValueContractError) as unreconciled:
        compile_join_state_value_contract(_graph(reconciliation=""))
    assert "join_allowed_difference_without_reconciliation" in _issue_codes(
        unreconciled.value
    )

    graph = _graph()
    graph.edges[0].state_effects["bad"] = math.nan
    with pytest.raises(JoinStateValueContractError) as non_json:
        compile_join_state_value_contract(graph)
    assert "state_effect_not_json" in _issue_codes(non_json.value)


def test_contract_reports_independent_join_issues_alongside_non_finite_values() -> None:
    """One rejected graph exposes all join repairs unaffected by a NaN value."""

    graph = _graph(
        left_effects={"shared": "left", "invalid": math.nan, "route": "left"},
        right_effects={"shared": "right", "invalid": "ready", "route": "right"},
        reconciliation="",
    )
    graph.join_contracts[0].required_state_keys = ["route", "shared", "missing", "invalid"]

    with pytest.raises(JoinStateValueContractError) as rejected:
        compile_join_state_value_contract(graph)

    codes = _issue_codes(rejected.value)
    assert {
        "state_effect_not_json",
        "join_state_effect_conflict",
        "join_state_effect_missing",
        "join_allowed_difference_without_reconciliation",
    } <= codes


def test_required_nonfinite_edge_effect_has_one_stable_issue() -> None:
    """A malformed required value authorizes one, not duplicate, correction fact."""

    graph = _graph(left_effects={"shared": math.nan, "route": "left"})
    with pytest.raises(JoinStateValueContractError) as captured:
        compile_join_state_value_contract(graph)

    matching = [
        issue
        for issue in captured.value.issues
        if issue.code == "state_effect_not_json"
        and issue.path == "edges.left-join.stateEffects.shared"
    ]
    assert len(matching) == 1


def test_contract_hash_rejects_rewritten_evidence() -> None:
    contract = compile_join_state_value_contract(_graph())
    payload = contract.model_dump(mode="json", by_alias=True)
    payload["entries"][0]["expectedJoinEntryValue"] = "tampered"

    with pytest.raises(ValueError, match="contractHash"):
        JoinStateValueContract.model_validate(payload, by_alias=True)


def test_scene_beats_plan_freezes_exact_join_requirements_in_unit_hash() -> None:
    brief = _brief()
    bible = _bible()
    graph = _graph()
    stage_plan = plan_stage(
        _generation_plan(brief),
        stage=StageName.SCENE_BEATS,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
        },
        brief=brief,
    )
    join_unit = next(
        unit for unit in stage_plan.work_units if unit.selector.stable_id == "join"
    )
    context = work_unit_context(
        join_unit,
        dependencies={
            StageName.STORY_BIBLE: bible,
            StageName.STORY_GRAPH: graph,
        },
        scene_timing_allocation=stage_plan.scene_timing_allocation,
    )
    expected = compile_join_state_value_contract(graph)

    assert context["join_state_value_requirements"] == (
        expected.requirements_for_node("join")
    )
    assert context["join_state_value_requirements"]["contractHash"] == (
        expected.contract_hash
    )
    assert join_unit.input_hash


def test_scene_beats_planning_rejects_unresolvable_join_before_provider_work() -> None:
    brief = _brief()
    graph = _graph(right_effects={"route": "right"})

    with pytest.raises(PlanningError) as captured:
        plan_stage(
            _generation_plan(brief),
            stage=StageName.SCENE_BEATS,
            dependencies={
                StageName.STORY_BIBLE: _bible(),
                StageName.STORY_GRAPH: graph,
            },
            brief=brief,
        )

    assert captured.value.code == "planning.join_state_value_contract_unresolvable"
    assert captured.value.stage == StageName.SCENE_BEATS
