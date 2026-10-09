"""Authored timing is bounded by routes, not a generator's depth allocation."""
from __future__ import annotations

from graphlib import CycleError, TopologicalSorter
from hashlib import sha256
import json
import math
from collections.abc import Mapping, Sequence

from .canonical_schema import StoryGraphV2

AUTHORED_ROUTE_TIMING_VERSION = "authored_route_timing.v1"


def route_budget_hash(*, target_seconds: int, section_bindings: list[dict],
                      routes: list[list[str]], route_only_ids: list[str]) -> str:
    payload = {
        "version": AUTHORED_ROUTE_TIMING_VERSION,
        "targetPlaythroughSeconds": target_seconds,
        "sectionBindings": section_bindings,
        "completeRouteSectionIds": routes,
        "routeOnlySectionIds": route_only_ids,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode()).hexdigest()


def validate_route_seconds(*, durations: Mapping[str, float], routes: Sequence[Sequence[str]],
                           route_only_ids: Sequence[str], maximum: int, label: str) -> None:
    """Check the exact frozen routes, without summing alternative endings."""
    route_only = set(route_only_ids)
    expected = {node for route in routes for node in route} - route_only
    if set(durations) != expected:
        raise ValueError(f"{label} timing must cover every footage section exactly")
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value <= 0 for value in durations.values()):
        raise ValueError(f"{label} timing must contain finite positive durations")
    for route in routes:
        if sum(durations.get(node, 0) for node in route) > maximum + 0.0001:
            raise ValueError(f"a complete {label} route exceeds the author playthrough maximum")


def longest_authored_route_units(graph: StoryGraphV2, durations: Mapping[str, int]) -> int:
    """Linear DAG accounting avoids enumerating exponentially many paths."""
    nodes = {node.id: node for node in graph.nodes}
    if len(nodes) != len(graph.nodes) or graph.start_node_id not in nodes:
        raise ValueError("authored timing requires unique nodes and a known start")
    if set(durations) - set(nodes):
        raise ValueError("authored timing references an unknown node")
    parents: dict[str, set[str]] = {node: set() for node in nodes}
    children: dict[str, set[str]] = {node: set() for node in nodes}
    for edge in graph.edges:
        if edge.source_node_id not in nodes or edge.target_node_id not in nodes:
            raise ValueError("authored timing has an unknown edge endpoint")
        parents[edge.target_node_id].add(edge.source_node_id)
        children[edge.source_node_id].add(edge.target_node_id)
    try:
        order = list(TopologicalSorter(parents).static_order())
    except CycleError as error:
        raise ValueError("authored timing requires an acyclic graph") from error
    longest: dict[str, int] = {}
    for node_id in order:
        node = nodes[node_id]
        duration = durations.get(node_id, 0)
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise ValueError("authored timing requires nonnegative integer milliseconds")
        if node.footage_mode == "route_only" and duration:
            raise ValueError("route-only nodes cannot contain authored duration")
        if node_id == graph.start_node_id:
            if parents[node_id]:
                raise ValueError("start node cannot have incoming edges")
            longest[node_id] = duration
        elif not parents[node_id] or any(parent not in longest for parent in parents[node_id]):
            raise ValueError("authored timing requires every node reachable from start")
        else:
            longest[node_id] = max(longest[parent] for parent in parents[node_id]) + duration
        if (node.kind.value == "ending") != (not children[node_id]):
            raise ValueError("every complete authored route must terminate at an ending")
    endings = [longest[node.id] for node in graph.nodes if node.kind.value == "ending"]
    if not endings:
        raise ValueError("authored timing requires an ending")
    return max(endings)
