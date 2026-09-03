"""Deterministic JSON Schema normalization for provider-facing contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


class JsonSchemaReferenceError(ValueError):
    """A local reference cannot be expanded without changing its meaning."""


_REFERENCE_ANNOTATION_KEYS = frozenset(
    {
        "default",
        "deprecated",
        "description",
        "examples",
        "readOnly",
        "title",
        "writeOnly",
    }
)


def explicit_presence_json_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Require every declared property and remove conflicting default hints.

    Domain defaults remain useful for hand-authored data. Generated data uses a
    stricter trust boundary: omission must be observable instead of silently
    turning into a default. JSON Schema's ``default`` is only an annotation,
    but compatible constrained decoders do not all honor that distinction when
    it appears beside ``required``.
    """

    result = deepcopy(dict(schema))

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            properties = value.get("properties")
            if isinstance(properties, dict):
                value["required"] = list(properties)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(result)
    return result


def inline_local_json_references(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return an equivalent schema with pure ``#/...`` references expanded.

    Some OpenAI-compatible constrained decoders accept JSON Schema requests but
    incompletely enforce ``required`` inside nested ``$defs`` references. The
    local validator stays strict, so the provider-facing representation is
    normalized instead of weakening validation. Ambiguous sibling constraints
    and recursive references fail before a provider call.
    """

    root = deepcopy(dict(schema))

    def resolve(reference: str) -> Any:
        if not reference.startswith("#/"):
            raise JsonSchemaReferenceError(
                f"only local JSON Schema references can be expanded: {reference}"
            )
        current: Any = root
        for raw_segment in reference[2:].split("/"):
            segment = raw_segment.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, Mapping) or segment not in current:
                raise JsonSchemaReferenceError(
                    f"unresolved local JSON Schema reference: {reference}"
                )
            current = current[segment]
        return current

    def expand(value: Any, stack: tuple[str, ...]) -> Any:
        if isinstance(value, list):
            return [expand(item, stack) for item in value]
        if not isinstance(value, Mapping):
            return deepcopy(value)
        reference = value.get("$ref")
        if reference is not None:
            if not isinstance(reference, str):
                raise JsonSchemaReferenceError("JSON Schema $ref must be a string")
            siblings = {
                key: item
                for key, item in value.items()
                if key not in {"$ref", "$defs"}
            }
            unsupported_siblings = set(siblings) - _REFERENCE_ANNOTATION_KEYS
            if unsupported_siblings:
                raise JsonSchemaReferenceError(
                    "local JSON Schema reference has sibling constraints: "
                    f"{reference} ({', '.join(sorted(unsupported_siblings))})"
                )
            if reference in stack:
                chain = " -> ".join((*stack, reference))
                raise JsonSchemaReferenceError(
                    f"recursive local JSON Schema reference is unsupported: {chain}"
                )
            expanded_reference = expand(resolve(reference), (*stack, reference))
            if siblings:
                if not isinstance(expanded_reference, dict):
                    raise JsonSchemaReferenceError(
                        f"annotated JSON Schema reference is not an object: {reference}"
                    )
                expanded_reference.update(deepcopy(siblings))
            return expanded_reference
        return {
            key: expand(item, stack)
            for key, item in value.items()
            if key != "$defs"
        }

    expanded = expand(root, ())
    if not isinstance(expanded, dict):
        raise JsonSchemaReferenceError("expanded JSON Schema root must be an object")
    return expanded
