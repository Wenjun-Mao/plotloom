from __future__ import annotations

from copy import deepcopy

from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.correction_postconditions import (
    validate_correction_postconditions,
)
from plotloom.generation.work_units import (
    ContinuityBoundaryRepair,
    ContinuityEntityStateAssignment,
    ContinuityFactAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
    ContinuityStateEndpoint,
    CueOrderRepairAssignment,
    CueOrderRepairFact,
    JoinAllowedDifferencesRepairFact,
    JoinIncomingEdgeRepairTarget,
    JoinNewRequiredKeyIncomingEdges,
    JoinStateEffectRepairFact,
    ShotDurationBudgetRepairFact,
)


def _incoming() -> tuple[JoinIncomingEdgeRepairTarget, ...]:
    return (
        JoinIncomingEdgeRepairTarget(edge_id="edge-a", source_node_id="node-a"),
        JoinIncomingEdgeRepairTarget(edge_id="edge-b", source_node_id="node-b"),
    )


def _cue_fact() -> CueOrderRepairFact:
    return CueOrderRepairFact(
        code="semantic.cue_order",
        path=("dialogueCues",),
        assignments=(
            CueOrderRepairAssignment(
                local_cue_id="cue-a", beat_local_id="beat-a", expected_order=1
            ),
            CueOrderRepairAssignment(
                local_cue_id="cue-b", beat_local_id="beat-b", expected_order=1
            ),
        ),
    )


def _response() -> dict[str, object]:
    return {
        "joinContracts": [
            {
                "id": "join-a",
                "requiredStateKeys": ["route", "variant"],
                "allowedDifferences": ["variant"],
            }
        ],
        "edges": [
            {
                "id": "edge-a",
                "stateEffects": {"route": {"next": 1}, "variant": "left"},
            },
            {
                "id": "edge-b",
                "stateEffects": {"route": {"next": 1}, "variant": "right"},
            },
        ],
        "scenes": [
            {
                "localSceneId": "scene-a",
                "entryState": {"facts": {}, "entityStates": []},
                "exitState": {"facts": {}, "entityStates": []},
            }
        ],
        "beats": [
            {
                "localBeatId": "beat-a",
                "entryState": {
                    "facts": {"route": {"next": 1}},
                    "entityStates": [
                        {"entityType": "character", "entityId": "hero", "state": "alert"}
                    ],
                    "sound": "quiet",
                },
                "exitState": {"facts": {}, "entityStates": []},
            }
        ],
        "shots": [],
        "dialogueCues": [
            {"localCueId": "cue-a", "beatLocalId": "beat-a", "order": 1},
            {"localCueId": "cue-b", "beatLocalId": "beat-b", "order": 1},
        ],
    }


def _join_arrays_fact() -> JoinAllowedDifferencesRepairFact:
    return JoinAllowedDifferencesRepairFact(
        code="semantic.join_allowed_differences_must_be_required",
        path=("joinContracts", "join-a", "allowedDifferences"),
        join_contract_id="join-a",
        missing_required_state_keys=("variant",),
        expected_required_state_keys=("route", "variant"),
        expected_allowed_differences=("variant",),
        new_required_key_incoming_edges=(
            JoinNewRequiredKeyIncomingEdges(
                state_key="variant", incoming_edges=_incoming()
            ),
        ),
    )


def _join_state_fact() -> JoinStateEffectRepairFact:
    return JoinStateEffectRepairFact(
        code="semantic.join_state_effect_missing",
        path=("edges", "edge-a", "stateEffects", "route"),
        join_contract_id="join-a",
        join_node_id="node-join",
        state_key="route",
        mode="convergent",
        incoming_edges=_incoming(),
        repair_action="set_missing",
        has_expected_value=True,
        expected_value={"next": 1},
    )


def _continuity_fact() -> ContinuitySequenceRepairFact:
    return ContinuitySequenceRepairFact(
        code="semantic.continuity_beat_sequence_mismatch",
        path=("scenes", 0),
        sequence_kind="beat",
        owner=ContinuityStateEndpoint(
            kind="scene", id="scene-a", id_scope="response_local", state="entry"
        ),
        ordered_item_ids=("beat-a",),
        boundaries=(
            ContinuityBoundaryRepair(
                source=ContinuityStateEndpoint(
                    kind="scene", id="scene-a", id_scope="response_local", state="entry"
                ),
                target=ContinuityStateEndpoint(
                    kind="beat", id="beat-a", id_scope="response_local", state="entry"
                ),
                assignments=(
                    ContinuityFactAssignment(kind="fact", key="route", expected_value={"next": 1}),
                    ContinuityEntityStateAssignment(
                        kind="entity_state",
                        entity_type="character",
                        entity_id="hero",
                        expected_state="alert",
                    ),
                    ContinuityScalarAssignment(
                        kind="scalar", field="sound", expected_value="quiet"
                    ),
                ),
            ),
        ),
    )


def _mismatch(path: tuple[str | int, ...]) -> tuple[ValidationIssue, ...]:
    return (
        ValidationIssue(
            code="contract.correction_output_constraint_mismatch",
            path=path,
            message="Correction output does not satisfy an exact repair constraint.",
        ),
    )


def test_cue_postcondition_accepts_complete_exact_assignment() -> None:
    assert validate_correction_postconditions(_response(), [_cue_fact()]) == ()


def test_cue_postcondition_rejects_deleted_moved_or_renamed_cue() -> None:
    for mutation in (
        lambda response: response["dialogueCues"].pop(),
        lambda response: response["dialogueCues"].__setitem__(0, {"localCueId": "cue-a", "beatLocalId": "beat-b", "order": 1}),
        lambda response: response["dialogueCues"].__setitem__(0, {"localCueId": "cue-renamed", "beatLocalId": "beat-a", "order": 1}),
    ):
        response = deepcopy(_response())
        mutation(response)  # type: ignore[arg-type]
        assert validate_correction_postconditions(response, [_cue_fact()]) == _mismatch(("dialogueCues",))


def test_join_postconditions_require_complete_arrays_state_presence_and_exact_value() -> None:
    facts = [_join_arrays_fact(), _join_state_fact()]
    assert validate_correction_postconditions(_response(), facts) == ()

    response = deepcopy(_response())
    response["edges"][1]["stateEffects"].pop("variant")  # type: ignore[index]
    assert validate_correction_postconditions(response, facts) == _mismatch(_join_arrays_fact().path)

    response = deepcopy(_response())
    response["edges"][1]["stateEffects"]["route"] = {"next": 1.0}  # type: ignore[index]
    assert validate_correction_postconditions(response, facts) == _mismatch(_join_state_fact().path)


def test_continuity_postcondition_requires_all_exact_response_local_assignments() -> None:
    fact = _continuity_fact()
    assert validate_correction_postconditions(_response(), [fact]) == ()

    response = deepcopy(_response())
    response["beats"][0]["entryState"]["entityStates"] = []  # type: ignore[index]
    assert validate_correction_postconditions(response, [fact]) == _mismatch(fact.path)


def test_unsupported_fact_is_ignored_without_schema_or_provider_dependency() -> None:
    unsupported = ShotDurationBudgetRepairFact(
        code="semantic.shot_duration_budget_exceeded",
        path=("shots",),
        scene_id="scene-a",
        scene_duration_budget_units=10,
        current_total_duration_units=12,
        required_reduction_units=2,
    )

    assert validate_correction_postconditions(object(), [unsupported]) == ()


def test_supported_fact_fails_closed_for_malformed_response_collections() -> None:
    assert validate_correction_postconditions(
        {"dialogueCues": [{"localCueId": "cue-a"}]},
        [_cue_fact()],
    ) == _mismatch(("dialogueCues",))
