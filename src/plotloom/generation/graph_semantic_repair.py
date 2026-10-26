"""Derive graph/join repairs and revalidate complete preserved source assignments."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import (
    ValidationError,
)

from ..json_value_contract import (
    finite_canonical_json,
)
from .contracts import ValidationIssue
from .graph_repair_contracts import (
    EdgeStateEffectJsonRepairFact,
    JoinAllowedDifferencesRepairFact,
    JoinIncomingEdgeRepairTarget,
    JoinNewRequiredKeyIncomingEdges,
    JoinPreservedIncomingStateEffect,
    JoinPreservedStateEffect,
    JoinReconciliationRepairFact,
    JoinStateEffectRepairFact,
)
from .repair_facts import SemanticRepairFact
from plotloom.generation.story_graph_content_contracts import StoryGraphContentFill, StoryGraphJoinContentFill
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology


def _story_graph_edge_state_effect_json_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    topology: StoryGraphTopology | None,
) -> tuple[EdgeStateEffectJsonRepairFact, ...]:
    """Bind a malformed state effect to exactly one immutable topology edge.

    The validator rejects non-finite JSON on every Story Graph edge.  Earlier
    repair routing only handled join-adjacent edges, leaving ordinary choices
    quarantined despite a safe, local repair.  This compiler owns the missing
    graph-wide contract: it authorizes replacement of the one rejected value,
    never a replacement topology or a guessed state value.
    """

    relevant = tuple(
        issue for issue in issues if issue.code == "semantic.state_effect_not_json"
    )
    if not relevant or topology is None:
        return ()
    try:
        fill = StoryGraphContentFill.model_validate(value, by_alias=True)
    except ValidationError:
        return ()
    fill_edges = {edge.id: edge for edge in fill.edges}
    topology_edges = {edge.id: edge for edge in topology.edges}
    facts: list[EdgeStateEffectJsonRepairFact] = []
    for issue in relevant:
        path = issue.path
        if (
            len(path) != 4
            or path[0] != "edges"
            or not isinstance(path[1], str)
            or path[2] != "stateEffects"
            or not isinstance(path[3], str)
        ):
            continue
        edge_id, state_key = path[1], path[3]
        fill_edge = fill_edges.get(edge_id)
        topology_edge = topology_edges.get(edge_id)
        if (
            fill_edge is None
            or topology_edge is None
            or state_key not in fill_edge.state_effects
        ):
            continue
        try:
            finite_canonical_json(fill_edge.state_effects[state_key])
        except (TypeError, ValueError):
            facts.append(
                EdgeStateEffectJsonRepairFact(
                    code=issue.code,
                    path=path,
                    edge_id=edge_id,
                    source_node_id=topology_edge.source_node_id,
                    target_node_id=topology_edge.target_node_id,
                    state_key=state_key,
                )
            )
    return tuple(facts)


def _story_graph_join_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    topology: StoryGraphTopology | None,
) -> tuple[SemanticRepairFact, ...]:
    relevant_codes = {
        "semantic.join_allowed_differences_must_be_required",
        "semantic.join_state_effect_missing",
        "semantic.join_state_effect_conflict",
        "semantic.join_allowed_difference_without_reconciliation",
    }
    relevant_issues = tuple(issue for issue in issues if issue.code in relevant_codes)
    if not relevant_issues or topology is None:
        return ()
    try:
        fill = StoryGraphContentFill.model_validate(value, by_alias=True)
    except ValidationError:
        return ()
    joins_by_id = {join.id: join for join in fill.join_contracts}
    edge_fill = {edge.id: edge for edge in fill.edges}
    topology_joins = {join.id: join for join in topology.joins}
    topology_edges = {edge.id: edge for edge in topology.edges}

    def incoming_edges(join_id: str) -> tuple[JoinIncomingEdgeRepairTarget, ...] | None:
        join = topology_joins.get(join_id)
        if join is None:
            return None
        targets = [
            JoinIncomingEdgeRepairTarget(
                edge_id=edge.id,
                source_node_id=edge.source_node_id,
            )
            for edge in topology_edges.values()
            if edge.target_node_id == join.join_node_id
            and edge.source_node_id in set(join.incoming_node_ids)
        ]
        if len(targets) != len(join.incoming_node_ids):
            return None
        return tuple(
            sorted(targets, key=lambda edge: (edge.edge_id, edge.source_node_id))
        )

    incoming_by_join = {
        join_id: targets
        for join_id in topology_joins
        if (targets := incoming_edges(join_id)) is not None
    }
    mutable_keys_by_join: dict[str, set[str]] = {
        join_id: set() for join_id in incoming_by_join
    }
    for issue in issues:
        path = issue.path
        if (
            issue.code == "semantic.join_allowed_differences_must_be_required"
            and len(path) == 3
            and path[0] == "joinContracts"
            and isinstance(path[1], str)
            and path[2] == "allowedDifferences"
        ):
            join = joins_by_id.get(path[1])
            if join is not None:
                required = set(join.required_state_keys)
                mutable_keys_by_join.setdefault(join.id, set()).update(
                    key for key in join.allowed_differences if key not in required
                )
            continue
        if (
            issue.code == "semantic.join_state_effect_conflict"
            and len(path) == 4
            and path[0] == "joinContracts"
            and isinstance(path[1], str)
            and path[2] == "requiredStateKeys"
            and isinstance(path[3], str)
        ):
            mutable_keys_by_join.setdefault(path[1], set()).add(path[3])
            continue
        if (
            issue.code
            in {
                "semantic.join_state_effect_missing",
                "semantic.state_effect_not_json",
            }
            and len(path) == 4
            and path[0] == "edges"
            and isinstance(path[1], str)
            and path[2] == "stateEffects"
            and isinstance(path[3], str)
        ):
            edge = topology_edges.get(path[1])
            if edge is None:
                continue
            for join_id, targets in incoming_by_join.items():
                if edge.id in {target.edge_id for target in targets}:
                    mutable_keys_by_join.setdefault(join_id, set()).add(path[3])
                    break

    def preserved_state_effects(
        join: StoryGraphJoinContentFill,
        targets: tuple[JoinIncomingEdgeRepairTarget, ...],
    ) -> tuple[JoinPreservedStateEffect, ...]:
        """Freeze only sibling keys already valid in the rejected response.

        The rejected final is source authority for values that already satisfy
        the complete join rule. It is never authority for a key that needs a
        correction in this packet, so concurrent repairable keys stay mutable.
        """

        preserved: list[JoinPreservedStateEffect] = []
        mutable_keys = mutable_keys_by_join.get(join.id, set())
        for state_key in join.required_state_keys:
            if state_key in mutable_keys:
                continue
            incoming_effects: list[JoinPreservedIncomingStateEffect] = []
            serialized_values: list[str] = []
            for target in targets:
                fill_edge = edge_fill.get(target.edge_id)
                if fill_edge is None or state_key not in fill_edge.state_effects:
                    incoming_effects = []
                    break
                try:
                    serialized_values.append(
                        finite_canonical_json(fill_edge.state_effects[state_key])
                    )
                except (TypeError, ValueError):
                    incoming_effects = []
                    break
                incoming_effects.append(
                    JoinPreservedIncomingStateEffect(
                        edge_id=target.edge_id,
                        expected_value=deepcopy(fill_edge.state_effects[state_key]),
                    )
                )
            if not incoming_effects:
                continue
            if (
                state_key not in join.allowed_differences
                and len(set(serialized_values)) != 1
            ):
                continue
            preserved.append(
                JoinPreservedStateEffect(
                    state_key=state_key,
                    incoming_effects=tuple(incoming_effects),
                )
            )
        return tuple(preserved)

    facts: list[SemanticRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if issue.code == "semantic.join_allowed_differences_must_be_required":
            if (
                len(path) != 3
                or path[0] != "joinContracts"
                or not isinstance(path[1], str)
                or path[2] != "allowedDifferences"
            ):
                continue
            join = joins_by_id.get(path[1])
            targets = incoming_edges(path[1])
            if join is None or targets is None:
                continue
            key_lists = (join.required_state_keys, join.allowed_differences)
            if any(
                any(not key.strip() for key in keys) or len(keys) != len(set(keys))
                for keys in key_lists
            ):
                continue
            required = set(join.required_state_keys)
            missing = tuple(
                key for key in join.allowed_differences if key not in required
            )
            if not missing:
                continue
            facts.append(
                JoinAllowedDifferencesRepairFact(
                    code=issue.code,
                    path=path,
                    join_contract_id=join.id,
                    missing_required_state_keys=missing,
                    expected_required_state_keys=tuple(
                        (*join.required_state_keys, *missing)
                    ),
                    expected_allowed_differences=tuple(join.allowed_differences),
                    new_required_key_incoming_edges=tuple(
                        JoinNewRequiredKeyIncomingEdges(
                            state_key=state_key,
                            incoming_edges=targets,
                        )
                        for state_key in missing
                    ),
                )
            )
            continue
        if issue.code == "semantic.join_allowed_difference_without_reconciliation":
            if (
                len(path) != 3
                or path[0] != "joinContracts"
                or not isinstance(path[1], str)
                or path[2] != "reconciliation"
            ):
                continue
            join = joins_by_id.get(path[1])
            if join is None or not join.allowed_differences:
                continue
            facts.append(
                JoinReconciliationRepairFact(
                    code=issue.code,
                    path=path,
                    join_contract_id=join.id,
                    allowed_difference_keys=tuple(join.allowed_differences),
                )
            )
            continue

        # The compiler emits missing at an edge path and a conflict
        # at the join key list.  Resolve the contract/key only from the frozen
        # topology plus schema-valid fill, never from a guessed response edge.
        join_id: str | None = None
        state_key: str | None = None
        target_edge_id: str | None = None
        if issue.code == "semantic.join_state_effect_conflict":
            if (
                len(path) == 4
                and path[0] == "joinContracts"
                and isinstance(path[1], str)
                and path[2] == "requiredStateKeys"
                and isinstance(path[3], str)
            ):
                join_id = path[1]
                join = joins_by_id.get(join_id)
                if join is not None:
                    # The compiler reports one conflict per key.  Recover it
                    # deterministically by checking the first non-equal
                    # non-variant required key in declared key order.
                    targets = incoming_edges(join_id)
                    if targets is not None and path[3] in join.required_state_keys:
                        state_key = path[3]
        elif (
            len(path) == 4
            and path[0] == "edges"
            and isinstance(path[1], str)
            and path[2] == "stateEffects"
            and isinstance(path[3], str)
        ):
            target_edge_id = path[1]
            state_key = path[3]
            edge = topology_edges.get(target_edge_id)
            if edge is not None:
                for candidate in topology_joins.values():
                    if (
                        edge.target_node_id == candidate.join_node_id
                        and edge.source_node_id in candidate.incoming_node_ids
                    ):
                        join_id = candidate.id
                        break
        if join_id is None or state_key is None:
            continue
        join = joins_by_id.get(join_id)
        targets = incoming_edges(join_id)
        topology_join = topology_joins.get(join_id)
        if (
            join is None
            or targets is None
            or topology_join is None
            or state_key not in join.required_state_keys
        ):
            continue
        mode: Literal["convergent", "variant"] = (
            "variant" if state_key in join.allowed_differences else "convergent"
        )
        expected_value: Any | None = None
        has_expected_value = False
        if issue.code == "semantic.join_state_effect_missing" and mode == "convergent":
            peer_values: list[str] = []
            peer_value: Any | None = None
            for target in targets:
                if target.edge_id == target_edge_id:
                    continue
                fill_edge = edge_fill.get(target.edge_id)
                if fill_edge is None or state_key not in fill_edge.state_effects:
                    peer_values = []
                    break
                try:
                    serialized = finite_canonical_json(
                        fill_edge.state_effects[state_key]
                    )
                except (TypeError, ValueError):
                    peer_values = []
                    break
                peer_values.append(serialized)
                peer_value = deepcopy(fill_edge.state_effects[state_key])
            if peer_values and len(set(peer_values)) == 1:
                expected_value = peer_value
                has_expected_value = True
        action: Literal["set_missing", "make_all_equal"]
        if issue.code == "semantic.join_state_effect_missing":
            action = "set_missing"
        elif issue.code == "semantic.join_state_effect_conflict":
            action = "make_all_equal"
        fact_input: dict[str, Any] = {
            "code": issue.code,
            "path": path,
            "join_contract_id": join_id,
            "join_node_id": topology_join.join_node_id,
            "state_key": state_key,
            "mode": mode,
            "incoming_edges": targets,
            "repair_action": action,
            "has_expected_value": has_expected_value,
            "preserved_state_effects": preserved_state_effects(join, targets),
        }
        if has_expected_value:
            fact_input["expected_value"] = expected_value
        facts.append(JoinStateEffectRepairFact(**fact_input))
    return tuple(facts)


def assert_join_state_effect_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
    *,
    issues: tuple[ValidationIssue, ...],
    topology: StoryGraphTopology | None,
) -> None:
    """Rebuild join preservation authority from the rejected source response.

    A persisted fact can be syntactically valid while carrying values from a
    different rejected response. Recompiling against the immutable topology
    and complete stable issue set proves both the repaired key and every
    preserved sibling assignment were actually valid source facts.
    """

    if not isinstance(fact, JoinStateEffectRepairFact):
        return
    expected = _story_graph_join_repair_facts(
        source_value,
        issues,
        topology=topology,
    )
    matches = [
        item
        for item in expected
        if isinstance(item, JoinStateEffectRepairFact)
        and item.code == fact.code
        and item.path == fact.path
    ]
    if len(matches) != 1 or matches[0] != fact:
        raise ValueError(
            "join state-effect repair fact does not match the rejected response and frozen topology"
        )
