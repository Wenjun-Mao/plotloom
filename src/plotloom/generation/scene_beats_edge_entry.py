"""Typed direct-edge entry-state helpers owned by Scene Beats.

The graph compiler owns which state is required.  This module owns carrying
that frozen requirement through Scene Beats response validation and exact
correction authority.  It deliberately does not infer path state or mutate a
later beat.
"""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import Field, model_validator

from ..canonical_schema import EntityType, NonBlankText
from ..domain import CamelModel
from .contracts import ValidationIssue


class EdgeEntryEntityStateRepairFact(CamelModel):
    """Exact typed edge state owed by the first target scene in one response."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.edge_entry_entity_state_missing",
        "semantic.edge_entry_entity_state_mismatch",
    ]
    path: tuple[str | int, ...]
    contract_version: str = Field(min_length=1)
    contract_hash: str = Field(min_length=64, max_length=64)
    scene_local_id: NonBlankText
    entity_type: EntityType
    entity_id: NonBlankText
    expected_state: NonBlankText

    @model_validator(mode="after")
    def validate_exact_entry_path(self) -> "EdgeEntryEntityStateRepairFact":
        if (
            len(self.path) != 6
            or self.path[0] != "scenes"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2:4] != ("entryState", "entityStates")
            or self.path[4] != self.entity_type.value
            or self.path[5] != self.entity_id
        ):
            raise ValueError("path must identify one first-scene typed entry state")
        return self


def edge_entry_state_requirements(scoped_context: Mapping[str, Any]) -> dict[str, Any]:
    """Return a validated, detached frozen entry-state projection."""

    value = (
        scoped_context
        if "contractVersion" in scoped_context
        else scoped_context.get("edge_entry_state_requirements")
    )
    if not isinstance(value, Mapping):
        raise ValueError("Scene Beats context has no frozen typed edge-entry requirements")
    version = value.get("contractVersion")
    contract_hash = value.get("contractHash")
    requirements = value.get("requiredEntityStates")
    if (
        not isinstance(version, str)
        or not version
        or not isinstance(contract_hash, str)
        or len(contract_hash) != 64
        or not isinstance(requirements, list)
    ):
        raise ValueError("Scene Beats typed edge-entry requirements are malformed")
    seen: set[tuple[str, str]] = set()
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            raise ValueError("Scene Beats typed edge-entry requirement is malformed")
        entity_type = requirement.get("entityType")
        entity_id = requirement.get("entityId")
        state = requirement.get("state")
        edge_ids = requirement.get("incomingEdgeIds")
        key = (entity_type, entity_id)
        if (
            not isinstance(entity_type, str)
            or not isinstance(entity_id, str)
            or not entity_id
            or not isinstance(state, str)
            or not state
            or not isinstance(edge_ids, list)
            or not edge_ids
            or any(not isinstance(edge_id, str) or not edge_id for edge_id in edge_ids)
            or key in seen
        ):
            raise ValueError("Scene Beats typed edge-entry requirement is malformed")
        seen.add(key)
    return deepcopy(dict(value))


def first_scene_entry_issues(
    scenes: Sequence[Mapping[str, Any]], requirements: Mapping[str, Any]
) -> tuple[ValidationIssue, ...]:
    """Validate frozen edge effects against first-scene entry state only."""

    issues: list[ValidationIssue] = []
    for index, scene in enumerate(scenes):
        if scene.get("order") != 1:
            continue
        entry_state = scene.get("entryState")
        entity_states = entry_state.get("entityStates") if isinstance(entry_state, Mapping) else None
        states = {
            (item.get("entityType"), item.get("entityId")): item.get("state")
            for item in entity_states
            if isinstance(item, Mapping)
        } if isinstance(entity_states, list) else {}
        for requirement in requirements["requiredEntityStates"]:
            entity_type = requirement["entityType"]
            entity_id = requirement["entityId"]
            path = ("scenes", index, "entryState", "entityStates", entity_type, entity_id)
            actual = states.get((entity_type, entity_id))
            if actual is None:
                issues.append(ValidationIssue(
                    code="semantic.edge_entry_entity_state_missing",
                    path=path,
                    message="first scene entry is missing a typed state from its direct incoming edge",
                ))
            elif actual != requirement["state"]:
                issues.append(ValidationIssue(
                    code="semantic.edge_entry_entity_state_mismatch",
                    path=path,
                    message="first scene entry differs from a typed state on its direct incoming edge",
                ))
    return tuple(issues)


def require_first_scene_entity_state_values(
    scene_schema: dict[str, Any], requirements: Sequence[Mapping[str, Any]]
) -> None:
    """Project frozen first-entry requirements into a portable schema hint."""

    if not requirements:
        return
    entry_constraints = [
        {
            "contains": {
                "type": "object",
                "required": ["entityType", "entityId", "state"],
                "properties": {
                    "entityType": {"const": requirement["entityType"]},
                    "entityId": {"const": requirement["entityId"]},
                    "state": {"const": requirement["state"]},
                },
            },
            "minContains": 1,
            "maxContains": 1,
        }
        for requirement in requirements
    ]
    scene_schema.setdefault("allOf", []).append({
        "if": {"properties": {"order": {"const": 1}}, "required": ["order"]},
        "then": {"properties": {"entryState": {"properties": {"entityStates": {"allOf": entry_constraints}}}}},
    })


def edge_entry_entity_state_repair_facts(
    value: Any, issues: tuple[ValidationIssue, ...], *, requirements: Mapping[str, Any]
) -> tuple[EdgeEntryEntityStateRepairFact, ...]:
    """Recompute exact repair authority from rejected response and frozen requirements."""

    relevant = tuple(issue for issue in issues if issue.code in {
        "semantic.edge_entry_entity_state_missing", "semantic.edge_entry_entity_state_mismatch"
    })
    if not relevant or not isinstance(value, Mapping):
        return ()
    scenes = value.get("scenes")
    if not isinstance(scenes, list):
        return ()
    try:
        projection = edge_entry_state_requirements(requirements)
    except ValueError:
        return ()
    # A persisted issue is evidence, not authority. Recompute the actual
    # first-entry failure from the frozen rejected payload before deriving a
    # correction fact, so a self-consistent forged fact/issue cannot repair a
    # response that already satisfies the required state.
    actual_issue_keys = {
        (issue.code, issue.path)
        for issue in first_scene_entry_issues(scenes, projection)
    }
    expected_by_key = {
        (item["entityType"], item["entityId"]): item["state"]
        for item in projection["requiredEntityStates"]
    }
    facts: list[EdgeEntryEntityStateRepairFact] = []
    for issue in relevant:
        if (issue.code, issue.path) not in actual_issue_keys:
            continue
        path = issue.path
        if (
            len(path) != 6 or path[0] != "scenes" or not isinstance(path[1], int)
            or isinstance(path[1], bool) or path[1] < 0 or path[1] >= len(scenes)
            or path[2:4] != ("entryState", "entityStates")
            or not isinstance(path[4], str) or not isinstance(path[5], str)
        ):
            continue
        scene = scenes[path[1]]
        expected_state = expected_by_key.get((path[4], path[5]))
        if not isinstance(scene, Mapping) or scene.get("order") != 1 or not isinstance(expected_state, str) or not expected_state:
            continue
        scene_local_id = scene.get("localSceneId")
        if not isinstance(scene_local_id, str) or not scene_local_id:
            continue
        try:
            facts.append(EdgeEntryEntityStateRepairFact(
                code=issue.code, path=path, contract_version=projection["contractVersion"],
                contract_hash=projection["contractHash"], scene_local_id=scene_local_id,
                entity_type=EntityType(path[4]), entity_id=path[5], expected_state=expected_state,
            ))
        except ValueError:
            continue
    return tuple(facts)


def assert_edge_entry_entity_state_repair_fact_matches_source(
    fact: Any, source_value: Any, *, requirements: Mapping[str, Any]
) -> None:
    """Reject persisted entry-state authority that cannot be re-derived exactly."""

    if not isinstance(fact, EdgeEntryEntityStateRepairFact):
        return
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = edge_entry_entity_state_repair_facts(source_value, (source_issue,), requirements=requirements)
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError("typed edge-entry repair fact does not match the rejected response and frozen requirements")


def edge_entry_entity_state_satisfied(response: Any, fact: EdgeEntryEntityStateRepairFact) -> bool:
    """Check the exact first-entry correction without trusting model output IDs."""

    if not isinstance(response, Mapping):
        return False
    scenes = response.get("scenes")
    if not isinstance(scenes, list):
        return False
    matching = [scene for scene in scenes if isinstance(scene, Mapping) and scene.get("localSceneId") == fact.scene_local_id]
    if len(matching) != 1 or matching[0].get("order") != 1:
        return False
    entry_state = matching[0].get("entryState")
    entity_states = entry_state.get("entityStates") if isinstance(entry_state, Mapping) else None
    matches = [item for item in entity_states if isinstance(item, Mapping) and item.get("entityType") == fact.entity_type.value and item.get("entityId") == fact.entity_id] if isinstance(entity_states, list) else []
    return len(matches) == 1 and matches[0].get("state") == fact.expected_state
