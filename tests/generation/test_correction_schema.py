from __future__ import annotations

from copy import deepcopy

import pytest

from plotloom.generation.continuity_repair_contracts import (
    ContinuityBoundaryRepair,
    ContinuityEntityStateAssignment,
    ContinuityFactAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
    ContinuityStateEndpoint,
)
from plotloom.generation.correction_contract import CORRECTION_RESPONSE_SCHEMA_VERSION
from plotloom.generation.correction_schema import compile_correction_response_schema
from plotloom.generation.correction_schema_contracts import (
    CorrectionResponseSchemaError,
)
from plotloom.generation.dialogue_repair_contracts import (
    CueOrderRepairAssignment,
    CueOrderRepairFact,
)
from plotloom.generation.graph_repair_contracts import (
    JoinAllowedDifferencesRepairFact,
    JoinPreservedIncomingStateEffect,
    JoinPreservedStateEffect,
    JoinStateEffectRepairFact,
)
from tests.generation.correction_schema_fixtures import (
    _base_schema,
    _branch_by_id,
    _continuity_base_schema,
    _cue_order_base_schema,
    _cue_order_fact,
    _join_array_fact,
    _join_state_fact,
    _preserved_variant,
    _timing_plan_base_schema,
    _timing_plan_fact,
    _timing_plan_response,
)


def test_join_array_projection_is_exact_deterministic_and_non_mutating() -> None:
    base = _base_schema()
    original = deepcopy(base)

    first = compile_correction_response_schema(base, [_join_array_fact()])
    second = compile_correction_response_schema(base, [_join_array_fact()])

    assert CORRECTION_RESPONSE_SCHEMA_VERSION == "correction_response_schema.v6"
    assert base == original
    assert first.schema == second.schema
    assert first.schema_hash == second.schema_hash
    assert first.applied_fact_codes == (
        "semantic.join_allowed_differences_must_be_required",
    )
    join_branch = _branch_by_id(first.schema, "joinContracts", "join-a")
    properties = join_branch["then"]["properties"]
    assert properties["requiredStateKeys"] == {"const": ["route", "variant"]}
    assert properties["allowedDifferences"] == {"const": ["variant"]}
    for edge_id in ("edge-a", "edge-b"):
        edge_branch = _branch_by_id(first.schema, "edges", edge_id)
        state_effects = edge_branch["then"]["properties"]["stateEffects"]
        assert state_effects["required"] == ["variant"]
        assert state_effects["properties"]["variant"] == {}


def test_exact_join_state_value_strengthens_presence_constraint() -> None:
    projected = compile_correction_response_schema(
        _base_schema(),
        [_join_array_fact(), _join_state_fact(expected_value=None, has_expected=True)],
    )

    for edge_id in ("edge-a", "edge-b"):
        edge_branch = _branch_by_id(projected.schema, "edges", edge_id)
        state_effects = edge_branch["then"]["properties"]["stateEffects"]
        assert state_effects["required"] == ["route", "variant"]
        assert state_effects["properties"]["route"] == {"const": None}
        assert state_effects["properties"]["variant"] == {}


def test_join_state_preservation_projects_source_bound_null_and_per_edge_values() -> (
    None
):
    values = _join_state_fact().model_dump(mode="python")
    values.pop("expected_value", None)
    values["preserved_state_effects"] = _preserved_variant()
    fact = JoinStateEffectRepairFact(**values)

    projected = compile_correction_response_schema(_base_schema(), [fact])
    edge_a = _branch_by_id(projected.schema, "edges", "edge-a")
    edge_b = _branch_by_id(projected.schema, "edges", "edge-b")
    state_a = edge_a["then"]["properties"]["stateEffects"]
    state_b = edge_b["then"]["properties"]["stateEffects"]
    assert state_a["required"] == ["route", "variant"]
    assert state_b["required"] == ["route", "variant"]
    assert state_a["properties"]["variant"] == {"const": None}
    assert state_b["properties"]["variant"] == {"const": {"branch": 2}}


def test_join_state_preservation_rejects_unknown_or_repaired_edge_constraints() -> None:
    values = _join_state_fact().model_dump(mode="python")
    values.pop("expected_value", None)
    values["preserved_state_effects"] = (
        JoinPreservedStateEffect(
            state_key="route",
            incoming_effects=(
                JoinPreservedIncomingStateEffect(edge_id="edge-b", expected_value="x"),
                JoinPreservedIncomingStateEffect(edge_id="edge-a", expected_value="x"),
            ),
        ),
    )
    with pytest.raises(ValueError, match="repaired state key"):
        JoinStateEffectRepairFact(**values)

    values["preserved_state_effects"] = (
        JoinPreservedStateEffect(
            state_key="variant",
            incoming_effects=(
                JoinPreservedIncomingStateEffect(edge_id="edge-b", expected_value="x"),
                JoinPreservedIncomingStateEffect(
                    edge_id="unknown-edge", expected_value="x"
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="exact ordered incoming edge set"):
        JoinStateEffectRepairFact(**values)


def test_fact_order_does_not_change_projected_schema() -> None:
    facts = [
        _join_array_fact(),
        _join_state_fact(expected_value={"ok": True}, has_expected=True),
    ]

    forward = compile_correction_response_schema(_base_schema(), facts)
    reverse = compile_correction_response_schema(_base_schema(), list(reversed(facts)))

    assert forward.schema == reverse.schema
    assert forward.schema_hash == reverse.schema_hash


def test_incomplete_current_join_array_fact_is_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="expectedRequiredStateKeys"):
        JoinAllowedDifferencesRepairFact(
            code="semantic.join_allowed_differences_must_be_required",
            path=("joinContracts", "join-a", "allowedDifferences"),
            join_contract_id="join-a",
            missing_required_state_keys=("variant",),
        )


def test_conflicting_exact_state_values_fail_closed() -> None:
    first = _join_state_fact(expected_value="left", has_expected=True)
    second = _join_state_fact(expected_value="right", has_expected=True)

    with pytest.raises(
        CorrectionResponseSchemaError,
        match="conflicting state-effect repair facts",
    ):
        compile_correction_response_schema(_base_schema(), [first, second])


def test_continuity_overlay_requires_exact_fact_entity_and_scalar_targets() -> None:
    fact = ContinuitySequenceRepairFact(
        code="semantic.continuity_beat_sequence_mismatch",
        path=("scenes", 0),
        sequence_kind="beat",
        owner=ContinuityStateEndpoint(
            kind="scene",
            id="scene-local",
            id_scope="response_local",
            state="entry",
        ),
        ordered_item_ids=("beat-local",),
        boundaries=(
            ContinuityBoundaryRepair(
                source=ContinuityStateEndpoint(
                    kind="scene",
                    id="scene-local",
                    id_scope="response_local",
                    state="entry",
                ),
                target=ContinuityStateEndpoint(
                    kind="beat",
                    id="beat-local",
                    id_scope="response_local",
                    state="entry",
                ),
                assignments=(
                    ContinuityFactAssignment(
                        kind="fact", key="route", expected_value=None
                    ),
                    ContinuityEntityStateAssignment(
                        kind="entity_state",
                        entity_type="character",
                        entity_id="hero",
                        expected_state="alert",
                    ),
                    ContinuityScalarAssignment(
                        kind="scalar",
                        field="sound",
                        expected_value="quiet",
                    ),
                ),
            ),
        ),
    )

    projected = compile_correction_response_schema(_continuity_base_schema(), [fact])

    assert projected.version == CORRECTION_RESPONSE_SCHEMA_VERSION
    branch = next(
        item
        for item in projected.schema["properties"]["beats"]["allOf"]
        if item["contains"]["properties"]["localBeatId"]["const"] == "beat-local"
    )
    assert branch["minContains"] == branch["maxContains"] == 1
    entry = branch["contains"]["properties"]["entryState"]
    assert entry["properties"]["facts"] == {
        "properties": {"route": {"const": None}},
        "required": ["route"],
    }
    assert entry["properties"]["sound"] == {"const": "quiet"}
    entity_constraint = entry["properties"]["entityStates"]["allOf"][0]
    assert entity_constraint == {
        "contains": {
            "type": "object",
            "properties": {
                "entityType": {"const": "character"},
                "entityId": {"const": "hero"},
                "state": {"const": "alert"},
            },
            "required": ["entityType", "entityId", "state"],
        },
        "minContains": 1,
        "maxContains": 1,
    }


def test_cue_order_overlay_freezes_collection_cardinality_without_advanced_keywords() -> (
    None
):
    base = _cue_order_base_schema()
    original = deepcopy(base)

    projected = compile_correction_response_schema(base, [_cue_order_fact()])

    assert base == original
    assert projected.applied_fact_codes == ("semantic.cue_order",)
    collection = projected.schema["properties"]["dialogueCues"]
    assert collection["minItems"] == collection["maxItems"] == 2
    assert collection["items"] == original["properties"]["dialogueCues"]["items"]
    assert "contains" not in str(collection)
    assert "minContains" not in str(collection)
    assert "maxContains" not in str(collection)


def test_cue_order_overlay_rejects_conflicting_or_impossible_authority() -> None:
    first = _cue_order_fact()
    second = CueOrderRepairFact(
        code="semantic.cue_order",
        path=("dialogueCues",),
        assignments=(
            CueOrderRepairAssignment(
                local_cue_id="cue-a",
                beat_local_id="beat-b",
                expected_order=1,
            ),
            CueOrderRepairAssignment(
                local_cue_id="cue-b",
                beat_local_id="beat-a",
                expected_order=1,
            ),
        ),
    )

    with pytest.raises(CorrectionResponseSchemaError, match="conflicting cue-order"):
        compile_correction_response_schema(
            _cue_order_base_schema(),
            [first, second],
        )

    with pytest.raises(CorrectionResponseSchemaError, match="base maxItems"):
        compile_correction_response_schema(
            _cue_order_base_schema(max_items=1),
            [first],
        )


def test_storyboard_timing_plan_overlay_is_exact_deterministic_and_non_mutating() -> (
    None
):
    base = _timing_plan_base_schema()
    original = deepcopy(base)
    cue_fact = _timing_plan_fact()
    total_fact = _timing_plan_fact(
        code="semantic.shot_duration_budget_exceeded",
        path=("shots",),
    )

    first = compile_correction_response_schema(base, [cue_fact, total_fact])
    second = compile_correction_response_schema(base, [total_fact, cue_fact])

    assert base == original
    assert first.schema == second.schema
    assert first.schema_hash == second.schema_hash
    assert first.applied_fact_codes == (
        "semantic.cue_duration_exceeds_shot",
        "semantic.shot_duration_budget_exceeded",
    )

    shots = first.schema["properties"]["shots"]
    assert shots["minItems"] == shots["maxItems"] == 2
    item_schema = shots["items"]
    assert item_schema["properties"]["localShotId"]["enum"] == ["shot-a", "shot-b"]
    branches = item_schema["allOf"]
    by_shot = {
        branch["if"]["properties"]["localShotId"]["const"]: branch["then"]
        for branch in branches
    }
    assert by_shot == {
        "shot-a": {
            "properties": {
                "order": {"const": 1},
                "durationUnits": {"const": 3},
                "cueIds": {"const": ["cue-a"]},
            },
            "required": ["cueIds", "durationUnits", "order"],
        },
        "shot-b": {
            "properties": {
                "order": {"const": 2},
                "durationUnits": {"const": 2},
                "cueIds": {"const": ["cue-b"]},
            },
            "required": ["cueIds", "durationUnits", "order"],
        },
    }
    root = first.schema["properties"]
    assert root["primaryShotLocalIdByBeat"]["const"] == {
        "beat-a": "shot-a",
        "beat-b": "shot-b",
    }
    assert root["supportingBeatLinks"]["const"] == [
        {
            "shotLocalId": "shot-a",
            "beatId": "beat-b",
            "coverageWeight": 0.5,
        }
    ]


def test_storyboard_timing_plan_overlay_rejects_conflicting_plan_or_base_cardinality() -> (
    None
):
    first = _timing_plan_fact()
    alternate_response = _timing_plan_response()
    alternate_response["primaryShotLocalIdByBeat"] = {
        "beat-a": "shot-b",
        "beat-b": "shot-a",
    }
    alternate_response["supportingBeatLinks"] = [
        {"shotLocalId": "shot-a", "beatId": "beat-a", "coverageWeight": 1.0},
        {"shotLocalId": "shot-b", "beatId": "beat-b", "coverageWeight": 1.0},
    ]
    conflicting = _timing_plan_fact(
        code="semantic.shot_duration_budget_exceeded",
        path=("shots",),
        response=alternate_response,
    )

    with pytest.raises(CorrectionResponseSchemaError):
        compile_correction_response_schema(
            _timing_plan_base_schema(),
            [first, conflicting],
        )

    with pytest.raises(CorrectionResponseSchemaError):
        compile_correction_response_schema(
            _timing_plan_base_schema(min_items=3),
            [first],
        )
    with pytest.raises(CorrectionResponseSchemaError):
        compile_correction_response_schema(
            _timing_plan_base_schema(max_items=1),
            [first],
        )

    incompatible_ids = _timing_plan_base_schema()
    incompatible_ids["properties"]["shots"]["items"]["properties"][  # type: ignore[index]
        "localShotId"
    ]["enum"] = ["other-shot"]
    with pytest.raises(CorrectionResponseSchemaError, match="base enum"):
        compile_correction_response_schema(incompatible_ids, [first])


def test_mixed_graph_and_cue_projection_preserves_nulls_hashes_and_base() -> None:
    base = _base_schema()
    base["properties"].update(_cue_order_base_schema()["properties"])
    before = deepcopy(base)
    facts = [
        _join_array_fact(),
        _join_state_fact(expected_value=None, has_expected=True),
        _cue_order_fact(),
    ]
    forward = compile_correction_response_schema(base, facts)
    reverse = compile_correction_response_schema(base, list(reversed(facts)))
    assert forward.schema == reverse.schema
    assert forward.schema_hash == reverse.schema_hash
    assert forward.applied_fact_codes == tuple(sorted(fact.code for fact in facts))
    effects = _branch_by_id(forward.schema, "edges", "edge-a")["then"]["properties"][
        "stateEffects"
    ]
    assert effects["properties"]["route"] == {"const": None}
    assert forward.schema["properties"]["dialogueCues"]["minItems"] == 2
    assert base == before


@pytest.mark.parametrize("cue_conflict_first", [False, True])
def test_mixed_family_conflicts_keep_original_fact_traversal_precedence(
    cue_conflict_first: bool,
) -> None:
    graph_first = _join_state_fact(expected_value="left", has_expected=True)
    graph_second = _join_state_fact(expected_value="right", has_expected=True)
    cue_first = _cue_order_fact()
    cue_second = cue_first.model_copy(
        update={"assignments": tuple(reversed(cue_first.assignments))}
    )
    facts = (
        [graph_first, cue_first, cue_second, graph_second]
        if cue_conflict_first
        else [cue_first, graph_first, graph_second, cue_second]
    )
    message = (
        "conflicting cue-order repair facts target dialogueCues"
        if cue_conflict_first
        else "conflicting state-effect repair facts"
    )
    with pytest.raises(CorrectionResponseSchemaError, match=message):
        compile_correction_response_schema({}, facts)
