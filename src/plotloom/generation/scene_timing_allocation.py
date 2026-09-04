"""Pure, deterministic duration-cap planning for Scene Beats.

The Scene Beats model may choose how a story node is split into dramatic
scenes, but it must not choose the total amount of time available to that
node.  This module owns that allocation independently of providers,
persistence, prompts, and execution.  Integration will freeze the result in a
StagePlan before any Scene Beats work unit is rendered.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque

from pydantic import ConfigDict, Field, model_validator

from ..canonical_schema import StoryGraphV2, StoryNodeV2, V2StoryNodeKind
from ..domain import CamelModel, ProjectBrief, to_camel


SCENE_TIMING_ALLOCATION_VERSION = "scene_timing_allocation.v1"
_MILLISECONDS_PER_SECOND = 1_000


class SceneTimingAllocationError(ValueError):
    """A graph cannot receive a trustworthy path-duration allocation."""

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


class SceneTimingLayerAllocation(_FrozenCamelModel):
    """One topological depth and its shared cap for every node in that depth."""

    depth: int = Field(ge=0)
    duration_budget_units: int = Field(ge=1)
    node_ids: tuple[str, ...] = Field(min_length=1)


class SceneTimingNodeAllocation(_FrozenCamelModel):
    """The total cap which one node's dramatic scenes must partition exactly."""

    node_id: str = Field(min_length=1)
    depth: int = Field(ge=0)
    duration_budget_units: int = Field(ge=1)


class SceneTimingAllocation(_FrozenCamelModel):
    """Versioned, hash-bound timing ownership for one sealed Story Graph."""

    allocation_version: str = SCENE_TIMING_ALLOCATION_VERSION
    graph_topology_hash: str = Field(min_length=64, max_length=64)
    target_playthrough_seconds: int = Field(ge=1)
    target_duration_units: int = Field(ge=1)
    layers: tuple[SceneTimingLayerAllocation, ...] = Field(min_length=1)
    node_allocations: tuple[SceneTimingNodeAllocation, ...] = Field(min_length=1)
    exact_for_all_complete_paths: bool
    allocation_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def _validate_hash_and_shape(self) -> "SceneTimingAllocation":
        if self.target_duration_units != self.target_playthrough_seconds * _MILLISECONDS_PER_SECOND:
            raise ValueError("targetDurationUnits must be targetPlaythroughSeconds in milliseconds")
        if [layer.depth for layer in self.layers] != list(range(len(self.layers))):
            raise ValueError("layers must cover contiguous depths from zero")
        layer_nodes = [node_id for layer in self.layers for node_id in layer.node_ids]
        if len(layer_nodes) != len(set(layer_nodes)):
            raise ValueError("a node may appear in only one timing layer")
        node_ids = [item.node_id for item in self.node_allocations]
        if len(node_ids) != len(set(node_ids)) or set(node_ids) != set(layer_nodes):
            raise ValueError("node allocations must exactly cover timing-layer nodes")
        layer_by_depth = {layer.depth: layer for layer in self.layers}
        for node in self.node_allocations:
            layer = layer_by_depth[node.depth]
            if node.node_id not in layer.node_ids or node.duration_budget_units != layer.duration_budget_units:
                raise ValueError("node allocation must match its shared layer budget")
        unsigned = self.model_dump(mode="json", by_alias=True, exclude={"allocation_hash"})
        expected = _sha256(unsigned)
        if self.allocation_hash != expected:
            raise ValueError("allocationHash does not match the immutable allocation")
        return self

    def node_duration_budget(self, node_id: str) -> int:
        """Return a node's frozen cap, refusing unknown nodes explicitly."""

        for item in self.node_allocations:
            if item.node_id == node_id:
                return item.duration_budget_units
        raise KeyError(node_id)


def plan_scene_timing_allocation(
    *,
    graph: StoryGraphV2,
    brief: ProjectBrief,
) -> SceneTimingAllocation:
    """Allocate a Brief's playthrough cap across topological graph depths.

    Every node in the same depth gets the same duration cap.  An edge always
    advances to a higher depth, so any complete DAG path visits at most one
    node per depth and cannot exceed the Brief target.  The generated layered
    topology uses every depth on every complete path; there the cap is exact.
    """

    node_by_id = _validate_and_index_graph(graph)
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming_count: dict[str, int] = {node_id: 0 for node_id in node_by_id}
    for edge in graph.edges:
        outgoing[edge.source_node_id].append(edge.target_node_id)
        incoming_count[edge.target_node_id] += 1

    reachable = _reachable(graph.start_node_id, outgoing)
    missing = sorted(set(node_by_id) - reachable)
    if missing:
        raise SceneTimingAllocationError(
            "timing.graph_unreachable_node",
            "Story Graph contains nodes unreachable from startNodeId: " + ", ".join(missing),
        )
    endings = {
        node_id
        for node_id, node in node_by_id.items()
        if node.kind == V2StoryNodeKind.ENDING
    }
    if not endings:
        raise SceneTimingAllocationError(
            "timing.graph_missing_ending", "Story Graph requires at least one ending node"
        )
    if any(outgoing.get(node_id) for node_id in endings):
        raise SceneTimingAllocationError(
            "timing.graph_ending_has_outgoing_edge", "ending nodes must not have outgoing edges"
        )
    dead_ends = sorted(
        node_id
        for node_id in reachable
        if node_id not in endings and not outgoing.get(node_id)
    )
    if dead_ends:
        raise SceneTimingAllocationError(
            "timing.graph_dead_end",
            "non-ending nodes must lead to an ending: " + ", ".join(dead_ends),
        )
    if not all(_can_reach_ending(node_id, outgoing, endings) for node_id in reachable):
        raise SceneTimingAllocationError(
            "timing.graph_path_without_ending",
            "every reachable Story Graph node must lead to an ending",
        )

    depths = _topological_depths(node_by_id, outgoing, incoming_count)
    max_depth = max(depths.values())
    depth_count = max_depth + 1
    target_units = brief.target_playthrough_seconds * _MILLISECONDS_PER_SECOND
    if target_units < depth_count:
        raise SceneTimingAllocationError(
            "timing.target_too_small",
            "targetPlaythroughSeconds does not provide one millisecond for each graph depth",
        )
    base, remainder = divmod(target_units, depth_count)
    layers: list[SceneTimingLayerAllocation] = []
    allocations: list[SceneTimingNodeAllocation] = []
    for depth in range(depth_count):
        # Giving the earliest depths the remainder is deterministic and keeps
        # every sibling branch perfectly comparable.
        duration = base + int(depth < remainder)
        node_ids = tuple(sorted(node_id for node_id, value in depths.items() if value == depth))
        layers.append(
            SceneTimingLayerAllocation(
                depth=depth,
                duration_budget_units=duration,
                node_ids=node_ids,
            )
        )
        allocations.extend(
            SceneTimingNodeAllocation(
                node_id=node_id,
                depth=depth,
                duration_budget_units=duration,
            )
            for node_id in node_ids
        )
    allocation_inputs = {
        "allocationVersion": SCENE_TIMING_ALLOCATION_VERSION,
        "graphTopologyHash": _graph_topology_hash(graph),
        "targetPlaythroughSeconds": brief.target_playthrough_seconds,
        "targetDurationUnits": target_units,
        "layers": [item.model_dump(mode="json", by_alias=True) for item in layers],
        "nodeAllocations": [item.model_dump(mode="json", by_alias=True) for item in allocations],
        "exactForAllCompletePaths": _is_exact_for_all_complete_paths(
            graph, depths, max_depth, endings
        ),
    }
    return SceneTimingAllocation(
        **allocation_inputs,
        allocation_hash=_sha256(allocation_inputs),
    )


def _validate_and_index_graph(graph: StoryGraphV2) -> dict[str, StoryNodeV2]:
    node_by_id = {node.id: node for node in graph.nodes}
    if len(node_by_id) != len(graph.nodes):
        raise SceneTimingAllocationError(
            "timing.graph_duplicate_node_id", "Story Graph node IDs must be unique"
        )
    if graph.start_node_id not in node_by_id:
        raise SceneTimingAllocationError(
            "timing.graph_unknown_start", "startNodeId must name a Story Graph node"
        )
    if node_by_id[graph.start_node_id].kind != V2StoryNodeKind.START:
        raise SceneTimingAllocationError(
            "timing.graph_start_kind", "startNodeId must name the START node"
        )
    edge_ids = [edge.id for edge in graph.edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise SceneTimingAllocationError(
            "timing.graph_duplicate_edge_id", "Story Graph edge IDs must be unique"
        )
    for edge in graph.edges:
        if edge.source_node_id not in node_by_id or edge.target_node_id not in node_by_id:
            raise SceneTimingAllocationError(
                "timing.graph_unknown_edge_node", "Story Graph edges must reference known nodes"
            )
    return node_by_id


def _reachable(start_node_id: str, outgoing: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    queue = deque([start_node_id])
    while queue:
        node_id = queue.popleft()
        if node_id in seen:
            continue
        seen.add(node_id)
        queue.extend(outgoing.get(node_id, ()))
    return seen


def _can_reach_ending(node_id: str, outgoing: dict[str, list[str]], endings: set[str]) -> bool:
    return bool(_reachable(node_id, outgoing) & endings)


def _topological_depths(
    node_by_id: dict[str, StoryNodeV2],
    outgoing: dict[str, list[str]],
    incoming_count: dict[str, int],
) -> dict[str, int]:
    ready = deque(sorted(node_id for node_id, count in incoming_count.items() if count == 0))
    depths = {node_id: 0 for node_id in ready}
    visited = 0
    while ready:
        node_id = ready.popleft()
        visited += 1
        for target in sorted(outgoing.get(node_id, ())):
            depths[target] = max(depths.get(target, 0), depths[node_id] + 1)
            incoming_count[target] -= 1
            if incoming_count[target] == 0:
                ready.append(target)
    if visited != len(node_by_id):
        raise SceneTimingAllocationError(
            "timing.graph_cycle", "Story Graph must be acyclic before timing is allocated"
        )
    return depths


def _is_exact_for_all_complete_paths(
    graph: StoryGraphV2,
    depths: dict[str, int],
    max_depth: int,
    endings: set[str],
) -> bool:
    """Whether all complete paths consume every allocated depth exactly once."""

    return (
        all(depths[ending] == max_depth for ending in endings)
        and all(depths[edge.target_node_id] == depths[edge.source_node_id] + 1 for edge in graph.edges)
    )


def _graph_topology_hash(graph: StoryGraphV2) -> str:
    """Hash only timing-relevant structure, not model-authored prose fields."""

    return _sha256(
        {
            "startNodeId": graph.start_node_id,
            "nodes": sorted(
                ({"id": node.id, "kind": node.kind.value} for node in graph.nodes),
                key=lambda item: item["id"],
            ),
            "edges": sorted(
                (
                    {
                        "id": edge.id,
                        "sourceNodeId": edge.source_node_id,
                        "targetNodeId": edge.target_node_id,
                        "kind": edge.kind.value,
                    }
                    for edge in graph.edges
                ),
                key=lambda item: item["id"],
            ),
        }
    )


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
