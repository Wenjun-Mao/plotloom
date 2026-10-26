"""Current typed correction schema fixture builders shared by family tests."""

from __future__ import annotations

from copy import deepcopy

from plotloom.generation.dialogue_repair_contracts import (
    CueOrderRepairAssignment,
    CueOrderRepairFact,
)
from plotloom.generation.graph_repair_contracts import (
    JoinAllowedDifferencesRepairFact,
    JoinIncomingEdgeRepairTarget,
    JoinNewRequiredKeyIncomingEdges,
    JoinPreservedIncomingStateEffect,
    JoinPreservedStateEffect,
    JoinStateEffectRepairFact,
)
from plotloom.generation.storyboard_timing_repair import (
    StoryboardTimingRepairPlanFact,
    build_storyboard_timing_guidance,
    build_storyboard_timing_repair_plan,
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


def _cue_order_base_schema(*, max_items: int = 8) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "dialogueCues": {
                "type": "array",
                "minItems": 0,
                "maxItems": max_items,
                "items": {
                    "type": "object",
                    "properties": {
                        "localCueId": {"type": "string"},
                        "beatLocalId": {"type": "string"},
                        "order": {"type": "integer", "minimum": 1},
                        "text": {"type": "string"},
                    },
                    "required": ["localCueId", "beatLocalId", "order", "text"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["dialogueCues"],
    }


def _cue_order_fact() -> CueOrderRepairFact:
    return CueOrderRepairFact(
        code="semantic.cue_order",
        path=("dialogueCues",),
        assignments=(
            CueOrderRepairAssignment(
                local_cue_id="cue-a",
                beat_local_id="beat-a",
                expected_order=1,
            ),
            CueOrderRepairAssignment(
                local_cue_id="cue-b",
                beat_local_id="beat-b",
                expected_order=1,
            ),
        ),
    )


def _timing_plan_base_schema(
    *, min_items: int = 0, max_items: int = 4
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "minItems": min_items,
                "maxItems": max_items,
                "items": {
                    "type": "object",
                    "properties": {
                        "localShotId": {"type": "string"},
                        "order": {"type": "integer", "minimum": 1},
                        "durationUnits": {"type": "integer", "minimum": 1},
                        "cueIds": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["localShotId", "order", "durationUnits", "cueIds"],
                },
            },
            "primaryShotLocalIdByBeat": {"type": "object"},
            "supportingBeatLinks": {"type": "array", "items": {"type": "object"}},
        },
        "required": [
            "shots",
            "primaryShotLocalIdByBeat",
            "supportingBeatLinks",
        ],
    }


def _timing_plan_response() -> dict[str, object]:
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


def _timing_plan_fact(
    *,
    code: str = "semantic.cue_duration_exceeds_shot",
    path: tuple[str | int, ...] = ("shots", 0, "cueIds"),
    response: dict[str, object] | None = None,
) -> StoryboardTimingRepairPlanFact:
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
        response or _timing_plan_response(), guidance=guidance
    )
    assert plan is not None
    return StoryboardTimingRepairPlanFact(
        code=code,
        path=path,
        plan=plan,
        guidance_hash=plan.guidance_hash,
        plan_hash=plan.plan_hash,
    )


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


def _preserved_variant() -> tuple[JoinPreservedStateEffect, ...]:
    return (
        JoinPreservedStateEffect(
            state_key="variant",
            incoming_effects=(
                JoinPreservedIncomingStateEffect(
                    edge_id="edge-b", expected_value={"branch": 2}
                ),
                JoinPreservedIncomingStateEffect(edge_id="edge-a", expected_value=None),
            ),
        ),
    )


def _branch_by_id(schema: dict[str, object], collection: str, identity: str):
    items = schema["properties"][collection]["items"]  # type: ignore[index]
    return next(
        branch
        for branch in items["allOf"]  # type: ignore[index]
        if branch["if"]["properties"]["id"].get("const") == identity
    )
