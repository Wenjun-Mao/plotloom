"""Validate and project the frozen join-entry requirements for one work unit."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .work_unit_contracts import (
    WorkUnitContractError,
)


def _continuity_requirements(
    scoped_context: Mapping[str, Any],
) -> dict[str, Any]:
    value = scoped_context.get("join_state_value_requirements")
    if not isinstance(value, Mapping):
        raise WorkUnitContractError(
            "Scene Beats context has no frozen join state value requirements"
        )
    version = value.get("contractVersion")
    contract_hash = value.get("contractHash")
    keys = value.get("requiredEntryFactKeys")
    facts = value.get("requiredEntryFacts")
    transitions = value.get("outgoingJoinTransitions")
    if (
        not isinstance(version, str)
        or not version
        or not isinstance(contract_hash, str)
        or len(contract_hash) != 64
        or not isinstance(keys, list)
        or any(not isinstance(key, str) or not key for key in keys)
        or len(keys) != len(set(keys))
        or not isinstance(facts, Mapping)
        or set(keys) != set(facts)
        or not isinstance(transitions, list)
    ):
        raise WorkUnitContractError(
            "Scene Beats join state value requirements are malformed"
        )
    return deepcopy(dict(value))
