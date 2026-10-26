"""Exact JSON Schema shape operations shared by correction families."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ..json_value_contract import finite_canonical_json
from .correction_schema_contracts import CorrectionResponseSchemaError


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
    if finite_canonical_json(constraints[key]) != finite_canonical_json(expected_value):
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
            raise CorrectionResponseSchemaError(f"{label} conflict with the base enum")
    if "const" in property_schema and (
        len(values) != 1 or property_schema["const"] != values[0]
    ):
        raise CorrectionResponseSchemaError(f"{label} conflict with the base const")
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
