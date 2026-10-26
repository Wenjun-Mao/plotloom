"""Model-facing content-fill DTO, schema and frozen topology manifest."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from ..canonical_schema import (
    RequiredEntityState,
    V2StoryEdgeKind,
)
from ..domain import CamelModel
from .json_schema import explicit_presence_json_schema, inline_local_json_references
from .story_graph_topology_contracts import StoryGraphTopology

STORY_GRAPH_CONTENT_FILL_SCHEMA_ID = "story_graph_content_fill.v5"


class StoryGraphNodeContentFill(CamelModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class StoryGraphEdgeContentFill(CamelModel):
    id: str = Field(min_length=1)
    choice_text: str | None
    state_effects: dict[str, Any]
    entity_state_effects: list[RequiredEntityState]


class StoryGraphJoinContentFill(CamelModel):
    id: str = Field(min_length=1)
    required_state_keys: list[str]
    allowed_differences: list[str]
    reconciliation: str
    notes: str


class StoryGraphContentFill(CamelModel):
    """The sole model-facing representation of a planned Story Graph."""

    nodes: list[StoryGraphNodeContentFill]
    edges: list[StoryGraphEdgeContentFill]
    join_contracts: list[StoryGraphJoinContentFill]


def story_graph_content_fill_schema(
    topology: StoryGraphTopology | None = None,
) -> dict[str, Any]:
    """Expose a presence-strict, optionally topology-bound response schema.

    The Pydantic model describes the reusable content-only shape.  A real
    generation work unit additionally binds the array cardinalities and the
    exact immutable UUID sets.  This puts the same contract in front of both
    native-JSON-schema providers and prompt-only providers; the binder remains
    the final authority and still rejects duplicates, omissions, or inventions.
    """

    schema = explicit_presence_json_schema(
        StoryGraphContentFill.model_json_schema(by_alias=True)
    )
    if topology is not None:
        _bind_content_fill_ids(
            schema,
            property_name="nodes",
            definition_name="StoryGraphNodeContentFill",
            identifiers=[item.id for item in topology.nodes],
        )
        _bind_content_fill_ids(
            schema,
            property_name="edges",
            definition_name="StoryGraphEdgeContentFill",
            identifiers=[item.id for item in topology.edges],
        )
        _bind_content_fill_ids(
            schema,
            property_name="joinContracts",
            definition_name="StoryGraphJoinContentFill",
            identifiers=[item.id for item in topology.joins],
        )
        _bind_edge_content_contract(schema, topology)
        route_only_ids = {
            node.id for node in topology.nodes if node.footage_mode == "route_only"
        }
        joins = schema["$defs"]["StoryGraphJoinContentFill"]
        joins["allOf"] = [
            {
                "if": {"properties": {"id": {"const": join.id}}, "required": ["id"]},
                "then": {
                    "properties": {
                        key: {"type": "array", "maxItems": 0}
                        for key in ("requiredStateKeys", "allowedDifferences")
                    }
                },
            }
            for join in topology.joins
            if join.join_node_id in route_only_ids
        ]
    return inline_local_json_references(schema)


def story_graph_content_fill_manifest(topology: StoryGraphTopology) -> dict[str, Any]:
    """Return only topology facts that a content-fill model must preserve.

    Project identity and structural search inputs remain in durable provenance,
    not in the creative prompt.  The planner version and topology hash bind this
    compact manifest back to the full frozen topology.
    """

    return {
        "plannerVersion": topology.planner_version,
        "topologyHash": topology.topology_hash,
        "startNodeId": topology.start_node_id,
        "nodes": [
            {"id": item.id, "kind": item.kind.value, "footageMode": item.footage_mode}
            for item in topology.nodes
        ],
        "edges": [
            {
                "id": item.id,
                "sourceNodeId": item.source_node_id,
                "targetNodeId": item.target_node_id,
                "kind": item.kind.value,
            }
            for item in topology.edges
        ],
        "joinContracts": [
            {
                "id": item.id,
                "joinNodeId": item.join_node_id,
                "incomingNodeIds": list(item.incoming_node_ids),
            }
            for item in topology.joins
        ],
    }


def _bind_content_fill_ids(
    schema: dict[str, Any],
    *,
    property_name: str,
    definition_name: str,
    identifiers: list[str],
) -> None:
    collection = schema["properties"][property_name]
    collection["minItems"] = len(identifiers)
    collection["maxItems"] = len(identifiers)
    identifier_schema = schema["$defs"][definition_name]["properties"]["id"]
    identifier_schema.clear()
    identifier_schema.update(
        {
            "title": "Immutable topology ID",
            "type": "string",
            "enum": identifiers,
        }
    )


def _bind_edge_content_contract(
    schema: dict[str, Any], topology: StoryGraphTopology
) -> None:
    """Make immutable edge kinds executable in the model-facing schema.

    ``choiceText`` is structurally present for every edge.  Its permitted value
    is nevertheless determined by the trusted edge kind, not by model prose.
    The binder below repeats this check because JSON Schema support varies among
    compatible providers.
    """

    edge_schema = schema["$defs"]["StoryGraphEdgeContentFill"]
    contracts: list[dict[str, Any]] = []
    route_only_ids = {
        node.id for node in topology.nodes if node.footage_mode == "route_only"
    }
    for edge in topology.edges:
        if edge.kind == V2StoryEdgeKind.CONTINUATION:
            choice_text_schema: dict[str, Any] = {"const": None}
        else:
            choice_text_schema = {"type": "string", "minLength": 1}
        contracts.append(
            {
                "if": {
                    "properties": {"id": {"const": edge.id}},
                    "required": ["id"],
                },
                "then": {
                    "properties": {
                        "choiceText": choice_text_schema,
                        **(
                            {"entityStateEffects": {"type": "array", "maxItems": 0}}
                            if edge.target_node_id in route_only_ids
                            else {}
                        ),
                    },
                    "required": ["choiceText"],
                },
            }
        )
    edge_schema["allOf"] = contracts
