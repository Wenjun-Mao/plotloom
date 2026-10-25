"""Derive join-entry repair authority from frozen incoming-transition values."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from pydantic import (
    ValidationError,
)

from ..json_value_contract import (
    CanonicalJsonValueError,
    finite_json_values_equal,
)
from .contracts import ValidationIssue
from .graph_repair_contracts import (
    JoinEntryStateValueRepairFact,
)
from .scene_response_contracts import (
    SceneBeatsFragmentOutput,
)


def scene_beats_join_entry_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    requirements: Mapping[str, Any],
) -> tuple[JoinEntryStateValueRepairFact, ...]:
    """Bind a rejected join fact to the exact frozen edge-transition value."""

    relevant = tuple(
        issue
        for issue in issues
        if issue.code
        in {
            "semantic.join_entry_state_value_missing",
            "semantic.join_entry_state_value_mismatch",
            "semantic.join_entry_state_value_not_json",
        }
    )
    if not relevant:
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()
    contract_version = requirements.get("contractVersion")
    contract_hash = requirements.get("contractHash")
    expected_facts = requirements.get("requiredEntryFacts")
    if (
        not isinstance(contract_version, str)
        or not contract_version
        or not isinstance(contract_hash, str)
        or len(contract_hash) != 64
        or not isinstance(expected_facts, Mapping)
    ):
        return ()
    facts: list[JoinEntryStateValueRepairFact] = []
    for issue in relevant:
        path = issue.path
        if (
            len(path) != 5
            or path[0] != "scenes"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[1] >= len(output.scenes)
            or path[2] != "entryState"
            or path[3] != "facts"
            or not isinstance(path[4], str)
            or path[4] not in expected_facts
        ):
            continue
        state_key = path[4]
        current = output.scenes[path[1]].entry_state.facts
        if issue.code.endswith("missing") and state_key in current:
            continue
        if issue.code.endswith(("mismatch", "not_json")) and state_key in current:
            try:
                if finite_json_values_equal(
                    current[state_key], expected_facts[state_key]
                ):
                    continue
            except CanonicalJsonValueError:
                # A non-finite value remains a validation failure; do not
                # manufacture a repair fact from an invalid authority.
                continue
        facts.append(
            JoinEntryStateValueRepairFact(
                code=issue.code,
                path=path,
                contract_version=contract_version,
                contract_hash=contract_hash,
                state_key=state_key,
                expected_value=deepcopy(expected_facts[state_key]),
            )
        )
    return tuple(facts)
