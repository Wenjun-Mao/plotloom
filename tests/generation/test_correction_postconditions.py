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
from plotloom.generation.storyboard_timing_repair import (
    StoryboardTimingRepairPlanFact,
    build_storyboard_timing_guidance,
    build_storyboard_timing_repair_plan,
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


def _timing_plan_response() -> dict[str, object]:
    """A fully specified response which the timing plan can safely replace."""

    return {
        "shots": [
            {
                "localShotId": "shot-a",
                "order": 1,
                "durationUnits": 3,
                "cueIds": ["cue-a"],
                "audioPlan": {"events": []},
            },
            {
                "localShotId": "shot-b",
                "order": 2,
                "durationUnits": 2,
                "cueIds": ["cue-b"],
                "audioPlan": {"events": []},
            },
        ],
        "primaryShotLocalIdByBeat": {"beat-a": "shot-a", "beat-b": "shot-b"},
        "supportingBeatLinks": [
            {"shotLocalId": "shot-a", "beatId": "beat-b", "coverageWeight": 0.5}
        ],
    }


def _timing_plan_fact() -> StoryboardTimingRepairPlanFact:
    guidance = build_storyboard_timing_guidance(
        scene_id="scene-a",
        scene_duration_budget_units=5,
        min_shots=2,
        configured_max_shots=2,
        beats=[{"id": "beat-a", "order": 1}, {"id": "beat-b", "order": 2}],
        cues=[
            {
                "id": "cue-a",
                "beatId": "beat-a",
                "order": 1,
                "estimatedDurationUnits": 3,
            },
            {
                "id": "cue-b",
                "beatId": "beat-b",
                "order": 1,
                "estimatedDurationUnits": 2,
            },
        ],
    )
    plan = build_storyboard_timing_repair_plan(
        _timing_plan_response(), guidance=guidance
    )
    assert plan is not None
    return StoryboardTimingRepairPlanFact(
        code="semantic.cue_duration_exceeds_shot",
        path=("shots", 0, "cueIds"),
        plan=plan,
        guidance_hash=plan.guidance_hash,
        plan_hash=plan.plan_hash,
    )


def _ordered_cue_timing_plan_fact() -> StoryboardTimingRepairPlanFact:
    guidance = build_storyboard_timing_guidance(
        scene_id="scene-ordered-cues",
        scene_duration_budget_units=5,
        min_shots=1,
        configured_max_shots=1,
        beats=[{"id": "beat-a", "order": 1}],
        cues=[
            {
                "id": "cue-a",
                "beatId": "beat-a",
                "order": 1,
                "estimatedDurationUnits": 2,
            },
            {
                "id": "cue-b",
                "beatId": "beat-a",
                "order": 2,
                "estimatedDurationUnits": 3,
            },
        ],
    )
    response = {
        "shots": [
            {
                "localShotId": "shot-a",
                "order": 1,
                "durationUnits": 5,
                "cueIds": ["cue-a", "cue-b"],
                "audioPlan": {"events": []},
            }
        ],
        "primaryShotLocalIdByBeat": {"beat-a": "shot-a"},
        "supportingBeatLinks": [],
    }
    plan = build_storyboard_timing_repair_plan(response, guidance=guidance)
    assert plan is not None
    return StoryboardTimingRepairPlanFact(
        code="semantic.cue_duration_exceeds_shot",
        path=("shots", 0, "cueIds"),
        plan=plan,
        guidance_hash=plan.guidance_hash,
        plan_hash=plan.plan_hash,
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


def test_storyboard_timing_plan_postcondition_requires_exact_replacement_shape() -> None:
    """A timing correction cannot alter plan-owned shots or coverage links."""

    fact = _timing_plan_fact()
    assert validate_correction_postconditions(_timing_plan_response(), [fact]) == ()

    mutations = (
        lambda response: response["shots"].pop(),
        lambda response: response["shots"].__setitem__(
            1,
            {
                **response["shots"][1],
                "localShotId": "shot-renamed",
            },
        ),
        lambda response: response["shots"][1].__setitem__("localShotId", "shot-a"),
        lambda response: response["shots"][0].__setitem__("order", 2),
        lambda response: response["shots"][0].__setitem__("durationUnits", 4),
        lambda response: response["shots"][0].__setitem__("cueIds", ["cue-b"]),
        lambda response: response["primaryShotLocalIdByBeat"].__setitem__(
            "beat-a", "shot-b"
        ),
        lambda response: response.__setitem__(
            "supportingBeatLinks",
            [
                {
                    "shotLocalId": "shot-a",
                    "beatId": "beat-b",
                    "coverageWeight": 1.0,
                }
            ],
        ),
        lambda response: response.__setitem__("supportingBeatLinks", []),
        lambda response: response.__setitem__(
            "supportingBeatLinks",
            response["supportingBeatLinks"] * 2,
        ),
    )
    for mutate in mutations:
        response = deepcopy(_timing_plan_response())
        mutate(response)
        assert validate_correction_postconditions(response, [fact]) == _mismatch(
            fact.path
        )


def test_storyboard_timing_plan_postcondition_preserves_cue_order() -> None:
    fact = _ordered_cue_timing_plan_fact()
    response = {
        "shots": [
            {
                "localShotId": "shot-a",
                "order": 1,
                "durationUnits": 5,
                "cueIds": ["cue-b", "cue-a"],
                "audioPlan": {"events": []},
            }
        ],
        "primaryShotLocalIdByBeat": {"beat-a": "shot-a"},
        "supportingBeatLinks": [],
    }

    assert validate_correction_postconditions(response, [fact]) == _mismatch(
        fact.path
    )


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
