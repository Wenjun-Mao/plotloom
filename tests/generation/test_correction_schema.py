from __future__ import annotations

from copy import deepcopy

import pytest

from plotloom.generation.correction_schema import (
    CORRECTION_RESPONSE_SCHEMA_VERSION,
    CorrectionResponseSchemaError,
    compile_correction_response_schema,
)
from plotloom.generation.work_units import (
    ContinuityBoundaryRepair,
    ContinuityEntityStateAssignment,
    ContinuityFactAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
    ContinuityStateEndpoint,
    JoinAllowedDifferencesRepairFact,
    JoinIncomingEdgeRepairTarget,
    JoinNewRequiredKeyIncomingEdges,
    JoinStateEffectRepairFact,
)


def _base_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "joinContracts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "stateEffects": {"type": "object"},
                    },
                    "required": ["id", "stateEffects"],
                },
            },
        },
        "required": ["joinContracts", "edges"],
    }


def _continuity_base_schema() -> dict[str, object]:
    state_schema = {
        "type": "object",
        "properties": {
            "facts": {"type": "object"},
            "entityStates": {"type": "array", "items": {"type": "object"}},
            "screenDirection": {"type": ["string", "null"]},
            "lighting": {"type": ["string", "null"]},
            "sound": {"type": ["string", "null"]},
        },
    }
    return {
        "type": "object",
        "properties": {
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "localSceneId": {"type": "string"},
                        "entryState": deepcopy(state_schema),
                        "exitState": deepcopy(state_schema),
                    },
                },
            },
            "beats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "localBeatId": {"type": "string"},
                        "entryState": deepcopy(state_schema),
                        "exitState": deepcopy(state_schema),
                    },
                },
            },
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "localShotId": {"type": "string"},
                        "entryState": deepcopy(state_schema),
                        "exitState": deepcopy(state_schema),
                    },
                },
            },
        },
    }


def _incoming() -> tuple[JoinIncomingEdgeRepairTarget, ...]:
    return (
        JoinIncomingEdgeRepairTarget(edge_id="edge-b", source_node_id="node-b"),
        JoinIncomingEdgeRepairTarget(edge_id="edge-a", source_node_id="node-a"),
    )


def _join_array_fact() -> JoinAllowedDifferencesRepairFact:
    return JoinAllowedDifferencesRepairFact(
        code="semantic.join_allowed_differences_must_be_required",
        path=("joinContracts", "join-a", "allowedDifferences"),
        join_contract_id="join-a",
        missing_required_state_keys=("variant",),
        expected_required_state_keys=("route", "variant"),
        expected_allowed_differences=("variant",),
        new_required_key_incoming_edges=(
            JoinNewRequiredKeyIncomingEdges(
                state_key="variant",
                incoming_edges=_incoming(),
            ),
        ),
    )


def _join_state_fact(*, expected_value: object = None, has_expected: bool = False):
    values = {
        "code": "semantic.join_state_effect_missing",
        "path": ("edges", "edge-a", "stateEffects", "route"),
        "join_contract_id": "join-a",
        "join_node_id": "node-join",
        "state_key": "route",
        "mode": "convergent",
        "incoming_edges": _incoming(),
        "repair_action": "set_missing",
        "has_expected_value": has_expected,
    }
    if has_expected:
        values["expected_value"] = expected_value
    return JoinStateEffectRepairFact(**values)


def _branch_by_id(schema: dict[str, object], collection: str, identity: str):
    items = schema["properties"][collection]["items"]  # type: ignore[index]
    return next(
        branch
        for branch in items["allOf"]  # type: ignore[index]
        if branch["if"]["properties"]["id"].get("const") == identity
    )


def test_join_array_projection_is_exact_deterministic_and_non_mutating() -> None:
    base = _base_schema()
    original = deepcopy(base)

    first = compile_correction_response_schema(base, [_join_array_fact()])
    second = compile_correction_response_schema(base, [_join_array_fact()])

    assert CORRECTION_RESPONSE_SCHEMA_VERSION == "correction_response_schema.v1"
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


def test_fact_order_does_not_change_projected_schema() -> None:
    facts = [_join_array_fact(), _join_state_fact(expected_value={"ok": True}, has_expected=True)]

    forward = compile_correction_response_schema(_base_schema(), facts)
    reverse = compile_correction_response_schema(_base_schema(), list(reversed(facts)))

    assert forward.schema == reverse.schema
    assert forward.schema_hash == reverse.schema_hash


def test_legacy_incomplete_join_array_fact_fails_closed() -> None:
    legacy = JoinAllowedDifferencesRepairFact(
        code="semantic.join_allowed_differences_must_be_required",
        path=("joinContracts", "join-a", "allowedDifferences"),
        join_contract_id="join-a",
        missing_required_state_keys=("variant",),
    )

    with pytest.raises(
        CorrectionResponseSchemaError,
        match="no complete replacement arrays",
    ):
        compile_correction_response_schema(_base_schema(), [legacy])


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
