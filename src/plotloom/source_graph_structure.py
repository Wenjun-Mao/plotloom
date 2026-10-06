"""Author-owned source structure; planner receipts remain immutable seed evidence."""
from pydantic import Field

from .canonical_schema import (
    RequiredEntityState, StableId, V2StoryEdgeKind, V2StoryNodeKind,
)
from .domain_base import CamelModel
from .generation.story_graph_topology import StoryGraphTopology


class SourceStructureNode(CamelModel):
    id: StableId
    kind: V2StoryNodeKind


class SourceStructureEdge(CamelModel):
    id: StableId
    source_node_id: StableId
    target_node_id: StableId
    kind: V2StoryEdgeKind
    state_effects: dict
    entity_state_effects: list[RequiredEntityState]


class SourceStructureJoin(CamelModel):
    id: StableId
    join_node_id: StableId
    incoming_node_ids: list[StableId] = Field(min_length=2)
    required_state_keys: list[str]
    allowed_differences: list[str]
    notes: str


class SourceStructure(CamelModel):
    start_node_id: StableId
    nodes: list[SourceStructureNode] = Field(min_length=1, max_length=128)
    edges: list[SourceStructureEdge]
    joins: list[SourceStructureJoin]


def structure_from_seed(seed: StoryGraphTopology) -> SourceStructure:
    """Compile a current planner seed, not an old-shape admission adapter."""
    return SourceStructure(
        start_node_id=seed.start_node_id,
        nodes=[SourceStructureNode(id=node.id, kind=node.kind.value) for node in seed.nodes],
        edges=[SourceStructureEdge(id=edge.id, source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id, kind=edge.kind.value,
            state_effects={}, entity_state_effects=[]) for edge in seed.edges],
        joins=[SourceStructureJoin(id=join.id, join_node_id=join.join_node_id,
            incoming_node_ids=list(join.incoming_node_ids), required_state_keys=[],
            allowed_differences=[], notes="Source structure narrative reconciliation.") for join in seed.joins],
    )
