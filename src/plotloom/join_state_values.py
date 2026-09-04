"""Compile exact join-entry facts from sealed Story Graph edge transitions.

``StoryEdge.stateEffects`` describes state after traversing an edge, while a
story-node ``exitState`` is shared by every outgoing choice.  A branch-specific
edge effect therefore cannot be imposed on the source node's single exit
state.  This module gives join entries their own versioned authority: every
incoming edge assigns every required key, and trusted code compiles those
assignments into the one exact value a join scene must expose.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from .canonical_schema import StoryGraphV2
from .domain import CamelModel
from .json_value_contract import finite_canonical_json


JOIN_STATE_VALUE_CONTRACT_VERSION = "join_required_state_values.v1"
JOIN_VARIANT_VALUE_VERSION = "join_variant.v1"


class _FrozenCamelModel(CamelModel):
    model_config = ConfigDict(
        alias_generator=CamelModel.model_config.get("alias_generator"),
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class JoinIncomingStateValue(_FrozenCamelModel):
    edge_id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    value: Any


class JoinRequiredStateValue(_FrozenCamelModel):
    join_contract_id: str = Field(min_length=1)
    join_node_id: str = Field(min_length=1)
    state_key: str = Field(min_length=1)
    mode: Literal["convergent", "variant_map"]
    incoming: tuple[JoinIncomingStateValue, ...] = Field(min_length=2)
    expected_join_entry_value: Any


class JoinStateValueContract(_FrozenCamelModel):
    """Hash-bound values used by every Scene Beats shard and final validator."""

    version: str = JOIN_STATE_VALUE_CONTRACT_VERSION
    graph_content_hash: str = Field(min_length=64, max_length=64)
    entries: tuple[JoinRequiredStateValue, ...]
    contract_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_contract_hash(self) -> "JoinStateValueContract":
        unsigned = self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"contract_hash"},
        )
        if self.contract_hash != _sha256(unsigned):
            raise ValueError("contractHash does not match the join state value contract")
        return self

    def requirements_for_node(self, node_id: str) -> dict[str, Any]:
        """Return the bounded, prompt-safe requirements for one story node.

        New V2 generation intentionally has no ``requiredExitFacts``.  An
        incoming edge applies its branch-specific effect only after the source
        node's shared exit state.  Requiring that value on the source scene
        would make a decision node satisfy mutually exclusive choices at once.
        """

        matching = [entry for entry in self.entries if entry.join_node_id == node_id]
        facts: dict[str, Any] = {}
        for entry in matching:
            if entry.state_key in facts:
                raise ValueError(
                    f"join node {node_id} has more than one authority for {entry.state_key}"
                )
            facts[entry.state_key] = deepcopy(entry.expected_join_entry_value)
        return {
            "contractVersion": self.version,
            "contractHash": self.contract_hash,
            "requiredEntryFactKeys": sorted(facts),
            "requiredEntryFacts": {
                key: facts[key]
                for key in sorted(facts)
            },
            "outgoingJoinTransitions": [],
        }


class JoinStateValueIssue(_FrozenCamelModel):
    code: str = Field(min_length=1)
    path: str = Field(min_length=1)
    message: str = Field(min_length=1)


class JoinStateValueContractError(ValueError):
    def __init__(self, issues: list[JoinStateValueIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in issues))


def compile_join_state_value_contract(
    graph: StoryGraphV2,
) -> JoinStateValueContract:
    """Compile a deterministic join-entry value contract or fail closed.

    Required values come only from direct incoming edge transitions.  We do
    not infer an initial state, propagate arbitrary path state, or reinterpret
    a node exit as a post-edge state.  Those would require additional first-
    class authoring domains rather than heuristics in a generation adapter.
    """

    graph_json = graph.model_dump(mode="json", by_alias=True)
    issues: list[JoinStateValueIssue] = []
    for edge in graph.edges:
        for state_key, value in edge.state_effects.items():
            try:
                finite_canonical_json(value)
            except (TypeError, ValueError):
                issues.append(
                    JoinStateValueIssue(
                        code="state_effect_not_json",
                        path=f"edges.{edge.id}.stateEffects.{state_key}",
                        message="story edge state effects must be finite canonical JSON values",
                    )
                )
    if issues:
        raise JoinStateValueContractError(issues)
    graph_hash = _sha256(graph_json)
    edges_by_pair: dict[tuple[str, str], list[Any]] = {}
    for edge in graph.edges:
        edges_by_pair.setdefault(
            (edge.source_node_id, edge.target_node_id),
            [],
        ).append(edge)

    entries: list[JoinRequiredStateValue] = []
    for contract in sorted(graph.join_contracts, key=lambda item: item.id):
        allowed = set(contract.allowed_differences)
        if allowed and not contract.reconciliation.strip():
            issues.append(
                JoinStateValueIssue(
                    code="join_allowed_difference_without_reconciliation",
                    path=f"joinContracts.{contract.id}.reconciliation",
                    message="allowedDifferences require an explicit reconciliation",
                )
            )
        for state_key in sorted(contract.required_state_keys):
            incoming: list[JoinIncomingStateValue] = []
            serialized_values: list[str] = []
            key_is_complete = True
            for source_node_id in sorted(contract.incoming_node_ids):
                edges = edges_by_pair.get(
                    (source_node_id, contract.join_node_id),
                    [],
                )
                if len(edges) != 1:
                    issues.append(
                        JoinStateValueIssue(
                            code="join_incoming_edge_ambiguous",
                            path=f"joinContracts.{contract.id}.incomingNodeIds",
                            message=(
                                "each declared incoming node must have exactly one "
                                "direct edge into its join"
                            ),
                        )
                    )
                    key_is_complete = False
                    continue
                edge = edges[0]
                if state_key not in edge.state_effects:
                    issues.append(
                        JoinStateValueIssue(
                            code="join_state_effect_missing",
                            path=f"edges.{edge.id}.stateEffects.{state_key}",
                            message=(
                                f"incoming edge {edge.id} must assign required "
                                f"join state key {state_key!r}"
                            ),
                        )
                    )
                    key_is_complete = False
                    continue
                # Every edge effect was checked above before contract
                # compilation begins.  Rechecking the same required value
                # here would turn one rejected edge/key into duplicate stable
                # issues (and consequently duplicate correction facts).
                serialized = finite_canonical_json(edge.state_effects[state_key])
                # Reparse the finite canonical representation so nested
                # mappings cannot retain mutable aliases from the graph.
                value = json.loads(serialized)
                incoming.append(
                    JoinIncomingStateValue(
                        edge_id=edge.id,
                        source_node_id=source_node_id,
                        value=value,
                    )
                )
                serialized_values.append(serialized)
            if not key_is_complete:
                continue

            incoming.sort(key=lambda item: (item.edge_id, item.source_node_id))
            if state_key not in allowed:
                if len(set(serialized_values)) != 1:
                    issues.append(
                        JoinStateValueIssue(
                            code="join_state_effect_conflict",
                            # A conflict is per required state key.  Keeping
                            # that identity in the stable issue path lets one
                            # typed correction repair every independent key
                            # in the same bounded response.
                            path=(
                                f"joinContracts.{contract.id}.requiredStateKeys."
                                f"{state_key}"
                            ),
                            message=(
                                f"non-variant join state {state_key!r} must have "
                                "one equal value on every incoming edge"
                            ),
                        )
                    )
                    continue
                mode: Literal["convergent", "variant_map"] = "convergent"
                expected: Any = deepcopy(incoming[0].value)
            else:
                mode = "variant_map"
                expected = {
                    "$plotloom": JOIN_VARIANT_VALUE_VERSION,
                    "joinContractId": contract.id,
                    "stateKey": state_key,
                    "byIncomingEdge": [
                        item.model_dump(mode="json", by_alias=True)
                        for item in incoming
                    ],
                }
            entries.append(
                JoinRequiredStateValue(
                    join_contract_id=contract.id,
                    join_node_id=contract.join_node_id,
                    state_key=state_key,
                    mode=mode,
                    incoming=tuple(incoming),
                    expected_join_entry_value=expected,
                )
            )

    if issues:
        raise JoinStateValueContractError(issues)
    entries.sort(key=lambda item: (item.join_contract_id, item.state_key))
    unsigned = {
        "version": JOIN_STATE_VALUE_CONTRACT_VERSION,
        "graphContentHash": graph_hash,
        "entries": [
            entry.model_dump(mode="json", by_alias=True)
            for entry in entries
        ],
    }
    return JoinStateValueContract(
        version=JOIN_STATE_VALUE_CONTRACT_VERSION,
        graph_content_hash=graph_hash,
        entries=tuple(entries),
        contract_hash=_sha256(unsigned),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(finite_canonical_json(value).encode("utf-8")).hexdigest()
