"""Frozen Story Graph topology contracts, hashes and structural semantics."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import ConfigDict, Field, ValidationError, model_validator

from ..canonical_schema import (
    JoinContractV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
    V2StoryEdgeKind,
    V2StoryNodeKind,
)
from plotloom.domain_base import CamelModel, to_camel
from plotloom.brief_contracts import ProjectBrief
from ..validation import DomainValidationError, validate_story_graph

STORY_GRAPH_TOPOLOGY_VERSION = "story_graph_topology.v3"

DEFAULT_MAX_DOWNSTREAM_WORK_UNITS = 128

_STRUCTURAL_PARAMETER_KEYS = frozenset(
    {
        "nodeBudget",
        "maxOutDegree",
        "endingCount",
        "decisionPointsPerPath",
        "desiredJoinCount",
    }
)


class StoryGraphTopologyError(ValueError):
    """A brief has no representable topology under the frozen constraints."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class _FrozenCamelModel(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class StoryGraphTopologyNode(_FrozenCamelModel):
    id: str = Field(min_length=1)
    kind: V2StoryNodeKind
    footage_mode: Literal["footage", "route_only"]


class StoryGraphTopologyEdge(_FrozenCamelModel):
    id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    kind: V2StoryEdgeKind


class StoryGraphTopologyJoin(_FrozenCamelModel):
    id: str = Field(min_length=1)
    join_node_id: str = Field(min_length=1)
    incoming_node_ids: tuple[str, ...] = Field(min_length=2)


class StoryGraphTopology(_FrozenCamelModel):
    """The frozen structural portion of a newly requested Story Graph."""

    planner_version: Literal["story_graph_topology.v3"]
    project_id: str = Field(min_length=1)
    structural_parameters: dict[str, int]
    start_node_id: str = Field(min_length=1)
    nodes: tuple[StoryGraphTopologyNode, ...]
    edges: tuple[StoryGraphTopologyEdge, ...]
    joins: tuple[StoryGraphTopologyJoin, ...]
    topology_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_topology_hash(self) -> "StoryGraphTopology":
        unsigned = self.model_dump(
            mode="json", by_alias=True, exclude={"topology_hash"}
        )
        expected = hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
        if self.topology_hash != expected:
            raise ValueError("topologyHash does not match the immutable topology")
        _validate_topology_semantics(self)
        return self


def _validate_topology_semantics(topology: StoryGraphTopology) -> None:
    """Apply the full graph validator to a content-free trusted skeleton."""

    if topology.planner_version != STORY_GRAPH_TOPOLOGY_VERSION:
        raise ValueError(f"unsupported plannerVersion: {topology.planner_version}")
    if set(topology.structural_parameters) != _STRUCTURAL_PARAMETER_KEYS:
        raise ValueError(
            "structuralParameters must contain the canonical graph constraints"
        )

    nodes_by_id = {node.id: node for node in topology.nodes}
    for node in topology.nodes:
        outgoing = [edge for edge in topology.edges if edge.source_node_id == node.id]
        if node.kind != V2StoryNodeKind.DECISION and len(outgoing) > 1:
            raise ValueError("non-decision topology nodes cannot fork continuations")
        expected_kind = (
            V2StoryEdgeKind.CHOICE
            if node.kind == V2StoryNodeKind.DECISION
            else V2StoryEdgeKind.CONTINUATION
        )
        if any(edge.kind != expected_kind for edge in outgoing):
            raise ValueError("topology edge kind must match its explicit decision role")
    incoming: dict[str, set[str]] = {node.id: set() for node in topology.nodes}
    for edge in topology.edges:
        if edge.source_node_id in nodes_by_id and edge.target_node_id in nodes_by_id:
            incoming[edge.target_node_id].add(edge.source_node_id)
    actual_join_node_ids = {
        node_id for node_id, sources in incoming.items() if len(sources) >= 2
    }
    declared_join_node_ids = {join.join_node_id for join in topology.joins}
    for node_id in actual_join_node_ids:
        if nodes_by_id[node_id].kind != V2StoryNodeKind.JOIN:
            raise ValueError("join node must have kind 'join'")
    if {
        node.id for node in topology.nodes if node.kind == V2StoryNodeKind.JOIN
    } != actual_join_node_ids:
        raise ValueError("JOIN node kind must correspond exactly to a graph merge")
    if declared_join_node_ids != actual_join_node_ids:
        raise ValueError("joins must correspond exactly to graph merge nodes")

    try:
        brief = ProjectBrief.model_validate(
            {
                "title": "Topology",
                "synopsis": "Structural validation.",
                **topology.structural_parameters,
            },
            by_alias=True,
        )
        validate_story_graph(
            StoryGraphV2(
                start_node_id=topology.start_node_id,
                nodes=[
                    StoryNodeV2(
                        id=node.id,
                        kind=node.kind,
                        title="Topology",
                        summary="Structural node.",
                        footage_mode=node.footage_mode,
                    )
                    for node in topology.nodes
                ],
                edges=[
                    StoryEdgeV2(
                        id=edge.id,
                        source_node_id=edge.source_node_id,
                        target_node_id=edge.target_node_id,
                        kind=edge.kind,
                        choice_text="Continue"
                        if edge.kind == V2StoryEdgeKind.CHOICE
                        else None,
                        state_effects={},
                        entity_state_effects=[],
                    )
                    for edge in topology.edges
                ],
                join_contracts=[
                    JoinContractV2(
                        id=join.id,
                        join_node_id=join.join_node_id,
                        incoming_node_ids=list(join.incoming_node_ids),
                        required_state_keys=[],
                        allowed_differences=[],
                        reconciliation="",
                        notes="",
                    )
                    for join in topology.joins
                ],
            ),
            brief,
        )
    except (DomainValidationError, ValidationError) as exc:
        raise ValueError(f"invalid deterministic Story Graph topology: {exc}") from exc


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
