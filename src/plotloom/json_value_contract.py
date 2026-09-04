"""Finite canonical JSON primitives shared by V2 semantic boundaries.

``Any``-typed story facts still need a durable equality rule.  Python equality
is not a JSON identity rule (notably ``1 == 1.0``), and permissive JSON
serialization can hide non-finite values.  Generation fragments and canonical
installation use these helpers so a locally accepted fact cannot change
meaning at aggregation time.
"""

from __future__ import annotations

import json
import math
from typing import Any


class CanonicalJsonValueError(ValueError):
    """A value cannot participate in the finite JSON authoring contract."""


def finite_canonical_json(value: Any) -> str:
    """Serialize one finite JSON value with the contract's stable identity."""

    _assert_native_finite_json(value, ancestors=set())
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise CanonicalJsonValueError(
            "value must be finite JSON and cannot contain opaque Python values"
        ) from exc


def _assert_native_finite_json(value: Any, *, ancestors: set[int]) -> None:
    """Reject Python values that JSON encoding would silently coerce.

    ``json.dumps`` accepts tuples and non-string mapping keys, converting them
    into arrays or strings.  That conversion makes the authoring boundary
    non-injective: two distinct Python values acquire the same canonical JSON
    identity.  Facts crossing this boundary are therefore restricted to the
    JSON-native recursive value set before serialisation.
    """

    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return
    if value_type is float:
        if math.isfinite(value):
            return
        raise CanonicalJsonValueError("floating-point values must be finite")
    if value_type is list:
        _assert_acyclic_container(value, ancestors=ancestors)
        try:
            for item in value:
                _assert_native_finite_json(item, ancestors=ancestors)
        finally:
            ancestors.remove(id(value))
        return
    if value_type is dict:
        _assert_acyclic_container(value, ancestors=ancestors)
        try:
            for key, item in value.items():
                if type(key) is not str:
                    raise CanonicalJsonValueError("object keys must be strings")
                _assert_native_finite_json(item, ancestors=ancestors)
        finally:
            ancestors.remove(id(value))
        return
    raise CanonicalJsonValueError(
        "value must use only native JSON null, booleans, numbers, strings, arrays, and objects"
    )


def _assert_acyclic_container(value: list[Any] | dict[str, Any], *, ancestors: set[int]) -> None:
    identity = id(value)
    if identity in ancestors:
        raise CanonicalJsonValueError("JSON values cannot contain recursive containers")
    ancestors.add(identity)


def finite_json_values_equal(left: Any, right: Any) -> bool:
    """Compare two values by finite canonical JSON identity.

    ``1`` and ``1.0`` are deliberately distinct because their canonical JSON
    representations differ.  Callers that need an error report should first
    validate individual values with :func:`finite_canonical_json` and may use
    a ``CanonicalJsonValueError`` here as a non-compatible boundary.
    """

    return finite_canonical_json(left) == finite_canonical_json(right)
