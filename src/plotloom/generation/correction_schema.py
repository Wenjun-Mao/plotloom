"""Typed, deterministic JSON-Schema hints for bounded corrections.

The base work-unit schema remains the canonical response shape.  A correction
can additionally carry exact authority derived from the rejected attempt (for
example, the complete arrays for one join contract). This module projects the
portable parts of that authority into a fresh schema. Application-side
postconditions remain the acceptance boundary because provider schema dialects
and enforcement vary. This module never reads validator prose or model text and
never mutates the base schema.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..json_value_contract import finite_canonical_json
from .correction_contract import CORRECTION_RESPONSE_SCHEMA_VERSION
from .prompts import canonical_json, sha256_text
from .work_units import (
    ContinuityEntityStateAssignment,
    ContinuityEntityStateRepairFact,
    ContinuityFactAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
    CueOrderRepairFact,
    JoinAllowedDifferencesRepairFact,
    JoinStateEffectRepairFact,
    SemanticRepairFact,
    StoryboardTimingRepairPlanFact,
)


class CorrectionResponseSchemaError(ValueError):
    """Typed repair authority cannot be represented without ambiguity."""


@dataclass(frozen=True)
class CorrectionResponseSchema:
    """One immutable overlay result bound into correction provenance."""

    version: str
    schema: dict[str, Any]
    schema_hash: str
    applied_fact_codes: tuple[str, ...]


def compile_correction_response_schema(
    base_schema: Mapping[str, Any],
    facts: Sequence[SemanticRepairFact],
) -> CorrectionResponseSchema:
    """Return a deep-copied schema narrowed by typed repair authority.

    Unsupported fact types deliberately leave the schema unchanged. They may
    still be executable through their versioned prompt directive and the
    canonical validator. Exact facts are independently checked after response
    validation, so this schema is a constrained-decoding aid rather than the
    trust boundary. A supported fact with incomplete or contradictory authority
    fails closed instead of silently falling back to prose.
    """

    schema = deepcopy(dict(base_schema))
    join_arrays: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    edge_state_requirements: dict[str, dict[str, Any]] = {}
    continuity_requirements: dict[
        tuple[str, str, str, str],
        dict[str, Any],
    ] = {}
    continuity_entity_state_requirements: dict[
        tuple[str, str, str, str, int], ContinuityEntityStateRepairFact
    ] = {}
    cue_order_fact: CueOrderRepairFact | None = None
    timing_plan_fact: StoryboardTimingRepairPlanFact | None = None
    applied_codes: set[str] = set()

    for fact in facts:
        if isinstance(fact, JoinAllowedDifferencesRepairFact):
            required = fact.expected_required_state_keys
            allowed = fact.expected_allowed_differences
            if required is None or allowed is None:
                raise CorrectionResponseSchemaError(
                    "current join-array repair fact has no complete replacement arrays"
                )
            replacement = (tuple(required), tuple(allowed))
            previous = join_arrays.setdefault(fact.join_contract_id, replacement)
            if previous != replacement:
                raise CorrectionResponseSchemaError(
                    "conflicting join-array repair facts target the same join contract"
                )
            if fact.new_required_key_incoming_edges is not None:
                for key_scope in fact.new_required_key_incoming_edges:
                    for edge in key_scope.incoming_edges:
                        _merge_edge_state_constraint(
                            edge_state_requirements,
                            edge_id=edge.edge_id,
                            state_key=key_scope.state_key,
                            expected_value=_NO_EXPECTED_VALUE,
                        )
            applied_codes.add(fact.code)
            continue

        if isinstance(fact, JoinStateEffectRepairFact):
            expected_value = (
                deepcopy(fact.expected_value)
                if fact.has_expected_value
                else _NO_EXPECTED_VALUE
            )
            if fact.has_expected_value:
                # Re-run the finite JSON boundary here so a future legacy
                # parser cannot smuggle a non-portable const into a provider
                # schema even if its Pydantic shape remains readable.
                finite_canonical_json(expected_value)
            for edge in fact.incoming_edges:
                _merge_edge_state_constraint(
                    edge_state_requirements,
                    edge_id=edge.edge_id,
                    state_key=fact.state_key,
                    expected_value=expected_value,
                )
            for preserved_effect in fact.preserved_state_effects:
                for incoming_effect in preserved_effect.incoming_effects:
                    _merge_edge_state_constraint(
                        edge_state_requirements,
                        edge_id=incoming_effect.edge_id,
                        state_key=preserved_effect.state_key,
                        expected_value=deepcopy(incoming_effect.expected_value),
                    )
            applied_codes.add(fact.code)
            continue

        if isinstance(fact, ContinuitySequenceRepairFact):
            for boundary in fact.boundaries:
                target = boundary.target
                if target.id_scope != "response_local":
                    raise CorrectionResponseSchemaError(
                        "continuity correction target is outside the model response"
                    )
                collection, identity_field = _continuity_collection(target.kind)
                state_field = (
                    "entryState" if target.state == "entry" else "exitState"
                )
                target_key = (collection, identity_field, target.id, state_field)
                target_constraints = continuity_requirements.setdefault(
                    target_key,
                    {"facts": {}, "entities": {}, "scalars": {}},
                )
                for assignment in boundary.assignments:
                    if isinstance(assignment, ContinuityFactAssignment):
                        finite_canonical_json(assignment.expected_value)
                        _merge_exact_constraint(
                            target_constraints["facts"],
                            assignment.key,
                            deepcopy(assignment.expected_value),
                            label="continuity fact",
                        )
                    elif isinstance(assignment, ContinuityEntityStateAssignment):
                        entity_key = (
                            assignment.entity_type.value,
                            assignment.entity_id,
                        )
                        _merge_exact_constraint(
                            target_constraints["entities"],
                            entity_key,
                            assignment.expected_state,
                            label="continuity entity state",
                        )
                    elif isinstance(assignment, ContinuityScalarAssignment):
                        _merge_exact_constraint(
                            target_constraints["scalars"],
                            assignment.field,
                            assignment.expected_value,
                            label="continuity scalar",
                        )
                    else:  # Defensive against a future union member.
                        raise CorrectionResponseSchemaError(
                            "unsupported continuity assignment type"
                        )
            applied_codes.add(fact.code)
            continue

        if isinstance(fact, ContinuityEntityStateRepairFact):
            target = fact.target
            if target.id_scope != "response_local":
                raise CorrectionResponseSchemaError(
                    "continuity entity-state correction target is outside the model response"
                )
            collection, identity_field = _continuity_collection(target.kind)
            state_field = "entryState" if target.state == "entry" else "exitState"
            key = (collection, identity_field, target.id, state_field, fact.entity_state_index)
            previous = continuity_entity_state_requirements.setdefault(key, fact)
            if previous != fact:
                raise CorrectionResponseSchemaError(
                    "conflicting continuity entity-state repair facts target the same response path"
                )
            applied_codes.add(fact.code)
            continue

        if isinstance(fact, CueOrderRepairFact):
            if cue_order_fact is not None and cue_order_fact != fact:
                raise CorrectionResponseSchemaError(
                    "conflicting cue-order repair facts target dialogueCues"
                )
            cue_order_fact = fact
            applied_codes.add(fact.code)
            continue

        if isinstance(fact, StoryboardTimingRepairPlanFact):
            if (
                timing_plan_fact is not None
                and timing_plan_fact.plan != fact.plan
            ):
                raise CorrectionResponseSchemaError(
                    "conflicting Storyboard timing repair facts carry different plans"
                )
            timing_plan_fact = fact
            applied_codes.add(fact.code)

    if join_arrays:
        item_schema = _collection_item_schema(schema, "joinContracts")
        branches = item_schema.setdefault("allOf", [])
        if not isinstance(branches, list):
            raise CorrectionResponseSchemaError(
                "joinContracts item schema has a non-list allOf"
            )
        for join_id in sorted(join_arrays):
            required, allowed = join_arrays[join_id]
            branches.append(
                _selected_item_branch(
                    "id",
                    join_id,
                    {
                        "requiredStateKeys": {"const": list(required)},
                        "allowedDifferences": {"const": list(allowed)},
                    },
                )
            )

    if edge_state_requirements:
        item_schema = _collection_item_schema(schema, "edges")
        branches = item_schema.setdefault("allOf", [])
        if not isinstance(branches, list):
            raise CorrectionResponseSchemaError("edges item schema has a non-list allOf")
        for edge_id in sorted(edge_state_requirements):
            constraints = edge_state_requirements[edge_id]
            state_properties: dict[str, Any] = {}
            for state_key in sorted(constraints):
                expected = constraints[state_key]
                state_properties[state_key] = (
                    {} if expected is _NO_EXPECTED_VALUE else {"const": expected}
                )
            branches.append(
                _selected_item_branch(
                    "id",
                    edge_id,
                    {
                        "stateEffects": {
                            "properties": state_properties,
                            "required": sorted(state_properties),
                        }
                    },
                )
            )

    for collection, identity_field, identity, state_field in sorted(
        continuity_requirements
    ):
        requirements = continuity_requirements[
            (collection, identity_field, identity, state_field)
        ]
        state_properties: dict[str, Any] = {}
        state_required: list[str] = []
        if requirements["facts"]:
            state_properties["facts"] = {
                "properties": {
                    key: {"const": requirements["facts"][key]}
                    for key in sorted(requirements["facts"])
                },
                "required": sorted(requirements["facts"]),
            }
            state_required.append("facts")
        if requirements["entities"]:
            entity_presence_constraints = []
            for entity_type, entity_id in sorted(requirements["entities"]):
                entity_presence_constraints.append(
                    {
                        "contains": {
                            "type": "object",
                            "properties": {
                                "entityType": {"const": entity_type},
                                "entityId": {"const": entity_id},
                                "state": {
                                    "const": requirements["entities"][
                                        (entity_type, entity_id)
                                    ]
                                },
                            },
                            "required": ["entityType", "entityId", "state"],
                        },
                        "minContains": 1,
                        "maxContains": 1,
                    }
                )
            state_properties["entityStates"] = {
                "allOf": entity_presence_constraints,
            }
            state_required.append("entityStates")
        for field in sorted(requirements["scalars"]):
            state_properties[field] = {
                "const": requirements["scalars"][field]
            }
            state_required.append(field)
        collection_schema = _collection_schema(schema, collection)
        branches = collection_schema.setdefault("allOf", [])
        if not isinstance(branches, list):
            raise CorrectionResponseSchemaError(
                f"{collection} schema has a non-list allOf"
            )
        branches.append(
            {
                "contains": {
                    "type": "object",
                    "properties": {
                        identity_field: {"const": identity},
                        state_field: {
                            "properties": state_properties,
                            "required": sorted(state_required),
                        },
                    },
                    "required": [identity_field, state_field],
                },
                "minContains": 1,
                "maxContains": 1,
            }
        )

    for key, fact in sorted(continuity_entity_state_requirements.items()):
        collection, identity_field, identity, state_field, entity_state_index = key
        collection_schema = _collection_schema(schema, collection)
        branches = collection_schema.setdefault("allOf", [])
        if not isinstance(branches, list):
            raise CorrectionResponseSchemaError(
                f"{collection} schema has a non-list allOf"
            )
        constrained_assignment = {
            "type": "object",
            "properties": {
                "entityType": {"const": fact.entity_type.value},
                "entityId": {"const": fact.entity_id},
                "state": {"enum": list(fact.allowed_states)},
            },
            "required": ["entityType", "entityId", "state"],
        }
        branches.append(
            {
                "contains": {
                    "type": "object",
                    "properties": {
                        identity_field: {"const": identity},
                        state_field: {
                            "properties": {
                                "entityStates": {
                                    "allOf": [
                                        {
                                            "prefixItems": [
                                                *({} for _ in range(entity_state_index)),
                                                constrained_assignment,
                                            ],
                                            "minItems": entity_state_index + 1,
                                        }
                                    ]
                                }
                            },
                            "required": ["entityStates"],
                        },
                    },
                    "required": [identity_field, state_field],
                },
                "minContains": 1,
                "maxContains": 1,
            }
        )

    if cue_order_fact is not None:
        collection_schema = _collection_schema(schema, "dialogueCues")
        assignment_count = len(cue_order_fact.assignments)
        existing_min = collection_schema.get("minItems")
        existing_max = collection_schema.get("maxItems")
        if isinstance(existing_min, int) and existing_min > assignment_count:
            raise CorrectionResponseSchemaError(
                "cue-order repair count conflicts with base minItems"
            )
        if isinstance(existing_max, int) and existing_max < assignment_count:
            raise CorrectionResponseSchemaError(
                "cue-order repair count conflicts with base maxItems"
            )
        collection_schema["minItems"] = assignment_count
        collection_schema["maxItems"] = assignment_count

    if timing_plan_fact is not None:
        plan = timing_plan_fact.plan
        collection_schema = _collection_schema(schema, "shots")
        target_count = len(plan.target_shots)
        _replace_collection_cardinality(
            collection_schema,
            target_count,
            label="Storyboard timing target shot",
        )
        item_schema = _collection_item_schema(schema, "shots")
        item_properties = _schema_properties(
            item_schema,
            label="shots item schema",
        )
        identity_schema = item_properties.get("localShotId")
        if not isinstance(identity_schema, dict):
            raise CorrectionResponseSchemaError(
                "base response schema has no localShotId field contract"
            )
        target_ids = sorted(shot.local_shot_id for shot in plan.target_shots)
        _set_string_enum(
            identity_schema,
            target_ids,
            label="Storyboard timing target shot IDs",
        )
        branches = item_schema.setdefault("allOf", [])
        if not isinstance(branches, list):
            raise CorrectionResponseSchemaError(
                "shots item schema has a non-list allOf"
            )
        for shot in sorted(plan.target_shots, key=lambda item: item.local_shot_id):
            branches.append(
                _selected_item_branch(
                    "localShotId",
                    shot.local_shot_id,
                    {
                        "order": {"const": shot.target_order},
                        "durationUnits": {"const": shot.target_duration_units},
                        "cueIds": {"const": list(shot.target_cue_ids)},
                    },
                )
            )

        root_properties = _schema_properties(schema, label="response schema")
        _set_property_const(
            root_properties,
            "primaryShotLocalIdByBeat",
            {
                link.beat_id: link.shot_local_id
                for link in plan.target_primary_links
            },
        )
        _set_property_const(
            root_properties,
            "supportingBeatLinks",
            [
                {
                    "shotLocalId": link.shot_local_id,
                    "beatId": link.beat_id,
                    "coverageWeight": link.coverage_weight,
                }
                for link in plan.target_supporting_links
            ],
        )

    return CorrectionResponseSchema(
        version=CORRECTION_RESPONSE_SCHEMA_VERSION,
        schema=schema,
        schema_hash=sha256_text(canonical_json(schema)),
        applied_fact_codes=tuple(sorted(applied_codes)),
    )


class _NoExpectedValue:
    pass


_NO_EXPECTED_VALUE = _NoExpectedValue()


def _merge_edge_state_constraint(
    constraints: dict[str, dict[str, Any]],
    *,
    edge_id: str,
    state_key: str,
    expected_value: Any,
) -> None:
    by_key = constraints.setdefault(edge_id, {})
    if state_key not in by_key:
        by_key[state_key] = expected_value
        return
    previous = by_key[state_key]
    if previous is _NO_EXPECTED_VALUE:
        by_key[state_key] = expected_value
        return
    if expected_value is _NO_EXPECTED_VALUE:
        return
    if finite_canonical_json(previous) != finite_canonical_json(expected_value):
        raise CorrectionResponseSchemaError(
            "conflicting state-effect repair facts target the same edge key"
        )


def _merge_exact_constraint(
    constraints: dict[Any, Any],
    key: Any,
    expected_value: Any,
    *,
    label: str,
) -> None:
    if key not in constraints:
        constraints[key] = expected_value
        return
    if finite_canonical_json(constraints[key]) != finite_canonical_json(
        expected_value
    ):
        raise CorrectionResponseSchemaError(
            f"conflicting {label} repair facts target the same field"
        )


def _continuity_collection(kind: str) -> tuple[str, str]:
    try:
        return {
            "scene": ("scenes", "localSceneId"),
            "beat": ("beats", "localBeatId"),
            "shot": ("shots", "localShotId"),
        }[kind]
    except KeyError as error:
        raise CorrectionResponseSchemaError(
            f"unsupported continuity endpoint kind: {kind}"
        ) from error


def _collection_item_schema(schema: dict[str, Any], collection: str) -> dict[str, Any]:
    collection_schema = _collection_schema(schema, collection)
    try:
        item_schema = collection_schema["items"]
    except (KeyError, TypeError) as error:
        raise CorrectionResponseSchemaError(
            f"base response schema has no {collection} item contract"
        ) from error
    if not isinstance(item_schema, dict):
        raise CorrectionResponseSchemaError(
            f"base response schema has an invalid {collection} item contract"
        )
    return item_schema


def _collection_schema(schema: dict[str, Any], collection: str) -> dict[str, Any]:
    try:
        collection_schema = schema["properties"][collection]
    except (KeyError, TypeError) as error:
        raise CorrectionResponseSchemaError(
            f"base response schema has no {collection} collection contract"
        ) from error
    if not isinstance(collection_schema, dict):
        raise CorrectionResponseSchemaError(
            f"base response schema has an invalid {collection} collection contract"
        )
    return collection_schema


def _schema_properties(
    schema: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise CorrectionResponseSchemaError(f"{label} has no properties contract")
    return properties


def _replace_collection_cardinality(
    collection_schema: dict[str, Any],
    count: int,
    *,
    label: str,
) -> None:
    existing_min = collection_schema.get("minItems")
    existing_max = collection_schema.get("maxItems")
    if isinstance(existing_min, int) and existing_min > count:
        raise CorrectionResponseSchemaError(
            f"{label} count conflicts with base minItems"
        )
    if isinstance(existing_max, int) and existing_max < count:
        raise CorrectionResponseSchemaError(
            f"{label} count conflicts with base maxItems"
        )
    collection_schema["minItems"] = count
    collection_schema["maxItems"] = count


def _set_property_const(
    properties: dict[str, Any],
    name: str,
    value: Any,
) -> None:
    property_schema = properties.get(name)
    if not isinstance(property_schema, dict):
        raise CorrectionResponseSchemaError(
            f"base response schema has no {name} field contract"
        )
    if "const" in property_schema and finite_canonical_json(
        property_schema["const"]
    ) != finite_canonical_json(value):
        raise CorrectionResponseSchemaError(
            f"base response schema has a conflicting {name} const"
        )
    property_schema["const"] = deepcopy(value)


def _set_string_enum(
    property_schema: dict[str, Any],
    values: list[str],
    *,
    label: str,
) -> None:
    existing_enum = property_schema.get("enum")
    if existing_enum is not None:
        if not isinstance(existing_enum, list) or any(
            value not in existing_enum for value in values
        ):
            raise CorrectionResponseSchemaError(
                f"{label} conflict with the base enum"
            )
    if "const" in property_schema and (
        len(values) != 1 or property_schema["const"] != values[0]
    ):
        raise CorrectionResponseSchemaError(
            f"{label} conflict with the base const"
        )
    property_schema["enum"] = list(values)


def _selected_item_branch(
    identity_field: str,
    identity: str,
    constrained_properties: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "if": {
            "properties": {identity_field: {"const": identity}},
            "required": [identity_field],
        },
        "then": {
            "properties": deepcopy(dict(constrained_properties)),
            "required": sorted(constrained_properties),
        },
    }
