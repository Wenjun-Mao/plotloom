from __future__ import annotations

import pytest

from plotloom.generation.json_schema import (
    JsonSchemaReferenceError,
    explicit_presence_json_schema,
    inline_local_json_references,
)


def test_local_references_are_inlined_without_mutating_the_source() -> None:
    source = {
        "$defs": {
            "State": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            }
        },
        "type": "object",
        "properties": {"state": {"$ref": "#/$defs/State"}},
        "required": ["state"],
        "additionalProperties": False,
    }

    expanded = inline_local_json_references(source)

    assert "$defs" not in expanded
    assert expanded["properties"]["state"] == source["$defs"]["State"]
    assert source["properties"]["state"] == {"$ref": "#/$defs/State"}


def test_recursive_or_ambiguous_local_references_fail_closed() -> None:
    with pytest.raises(JsonSchemaReferenceError, match="recursive"):
        inline_local_json_references(
            {
                "$defs": {"Loop": {"$ref": "#/$defs/Loop"}},
                "$ref": "#/$defs/Loop",
            }
        )

    with pytest.raises(JsonSchemaReferenceError, match="sibling"):
        inline_local_json_references(
            {
                "$defs": {"Text": {"type": "string"}},
                "type": "object",
                "properties": {
                    "value": {
                        "$ref": "#/$defs/Text",
                        "minLength": 1,
                    }
                },
            }
        )


def test_explicit_presence_requires_properties_without_default_annotations() -> None:
    source = {
        "type": "object",
        "properties": {
            "facts": {"type": "object", "default": {}},
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
        },
    }

    strict = explicit_presence_json_schema(source)

    assert strict["required"] == ["facts", "note"]
    assert "default" not in strict["properties"]["facts"]
    assert "default" not in strict["properties"]["note"]
    assert source["properties"]["facts"]["default"] == {}
