"""Bind one successful worker report to its coordinator-assigned native cases."""

from __future__ import annotations

import json
from collections.abc import Sequence

from scripts.testing.python_suite_schedule import native_case_fingerprint

RUN_MARKER = "PYTHON_SUITE_TIMING_RUN "
COMPLETION_SCHEMA_VERSION = 1


class CompletionError(ValueError):
    """A worker did not prove completion of its exact assigned case IDs."""


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CompletionError(f"duplicate completion field: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise CompletionError(f"nonfinite completion value: {value}")


def validate_worker_completion(stdout: str, expected_cases: Sequence[str]) -> str:
    """Return the verified fingerprint, refusing count-only or ambiguous proof."""
    if not expected_cases or len(expected_cases) != len(set(expected_cases)):
        raise CompletionError("assigned native cases must be nonempty and unique")
    markers = [line[len(RUN_MARKER):] for line in stdout.splitlines() if line.startswith(RUN_MARKER)]
    if len(markers) != 1:
        raise CompletionError("expected exactly one worker completion marker")
    try:
        value = json.loads(markers[0], object_pairs_hook=_unique_fields, parse_constant=_reject_constant)
    except json.JSONDecodeError as error:
        raise CompletionError("malformed worker completion marker") from error
    fields = {"schema_version", "complete", "exitstatus", "files", "case_count", "native_case_ids_sha256"}
    if not isinstance(value, dict) or set(value) != fields:
        raise CompletionError("worker completion fields do not match the current contract")
    expected_numbers = {
        "schema_version": COMPLETION_SCHEMA_VERSION,
        "exitstatus": 0,
        "files": len({case.split("::", 1)[0] for case in expected_cases}),
        "case_count": len(expected_cases),
    }
    if value["complete"] is not True or any(
        type(value[key]) is not int or value[key] != expected
        for key, expected in expected_numbers.items()
    ):
        raise CompletionError("worker did not complete the assigned native case/file counts")
    fingerprint = native_case_fingerprint(expected_cases)
    if value["native_case_ids_sha256"] != fingerprint:
        raise CompletionError("worker native case IDs differ from the coordinator assignment")
    return fingerprint
