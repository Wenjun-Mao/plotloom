"""Degree-bounded bipartite transition feasibility and deterministic circulation."""

from __future__ import annotations

from dataclasses import dataclass


def _transition_is_possible(
    source_count: int,
    target_count: int,
    *,
    min_out: int,
    max_out: int,
    join_targets: int,
) -> bool:
    """Constant-time feasibility for a complete bipartite layer transition."""

    if source_count < 1 or target_count < 1:
        return False
    maximum_out = min(max_out, target_count)
    if min_out > maximum_out or not 0 <= join_targets <= target_count:
        return False
    if join_targets and source_count < 2:
        return False
    # Every target has one incoming edge; each declared join needs at least a
    # second. Non-joins are capped at exactly one, while joins may receive one
    # edge from every distinct source.
    target_lower = target_count + join_targets
    target_upper = target_count + join_targets * (source_count - 1)
    source_lower = source_count * min_out
    source_upper = source_count * maximum_out
    return max(source_lower, target_lower) <= min(source_upper, target_upper)


@dataclass
class _FlowEdge:
    target: int
    reverse: int
    capacity: int
    original_capacity: int


def _construct_transition(
    source_count: int,
    target_count: int,
    *,
    min_out: int,
    max_out: int,
    join_targets: int,
) -> tuple[tuple[int, ...], ...] | None:
    """Build one deterministic simple bipartite graph with degree bounds.

    Lower-bound circulation is used only for the transitions chosen by the DP;
    it never enumerates candidate edge matrices. The first ``join_targets``
    columns are selected because columns are structurally symmetric.
    """

    if not _transition_is_possible(
        source_count,
        target_count,
        min_out=min_out,
        max_out=max_out,
        join_targets=join_targets,
    ):
        return None

    network_source = 0
    row_offset = 1
    column_offset = row_offset + source_count
    network_sink = column_offset + target_count
    super_source = network_sink + 1
    super_sink = super_source + 1
    graph: list[list[_FlowEdge]] = [[] for _ in range(super_sink + 1)]
    demands = [0] * (super_sink + 1)
    row_column_edges: list[list[_FlowEdge]] = [[] for _ in range(source_count)]

    def add_edge(source: int, target: int, capacity: int) -> _FlowEdge:
        forward = _FlowEdge(target, len(graph[target]), capacity, capacity)
        reverse = _FlowEdge(source, len(graph[source]), 0, 0)
        graph[source].append(forward)
        graph[target].append(reverse)
        return forward

    def add_bounded_edge(source: int, target: int, lower: int, upper: int) -> _FlowEdge:
        demands[source] -= lower
        demands[target] += lower
        return add_edge(source, target, upper - lower)

    maximum_out = min(max_out, target_count)
    for row in range(source_count):
        add_bounded_edge(
            network_source,
            row_offset + row,
            min_out,
            maximum_out,
        )
        for column in range(target_count):
            edge = add_bounded_edge(
                row_offset + row,
                column_offset + column,
                0,
                1,
            )
            row_column_edges[row].append(edge)
    for column in range(target_count):
        lower = 2 if column < join_targets else 1
        upper = source_count if column < join_targets else 1
        add_bounded_edge(
            column_offset + column,
            network_sink,
            lower,
            upper,
        )
    add_edge(network_sink, network_source, source_count * target_count)

    required_flow = 0
    for node in range(network_sink + 1):
        if demands[node] > 0:
            add_edge(super_source, node, demands[node])
            required_flow += demands[node]
        elif demands[node] < 0:
            add_edge(node, super_sink, -demands[node])
    if _maximum_flow(graph, super_source, super_sink) != required_flow:
        return None

    return tuple(
        tuple(
            column
            for column, edge in enumerate(edges)
            if edge.original_capacity - edge.capacity == 1
        )
        for edges in row_column_edges
    )


def _maximum_flow(graph: list[list[_FlowEdge]], source: int, sink: int) -> int:
    """Small deterministic Dinic implementation for planner-local circulation."""

    total = 0
    while True:
        level = [-1] * len(graph)
        level[source] = 0
        queue = [source]
        for node in queue:
            for edge in graph[node]:
                if edge.capacity > 0 and level[edge.target] < 0:
                    level[edge.target] = level[node] + 1
                    queue.append(edge.target)
        if level[sink] < 0:
            return total
        cursor = [0] * len(graph)

        def send(node: int, available: int) -> int:
            if node == sink:
                return available
            while cursor[node] < len(graph[node]):
                edge = graph[node][cursor[node]]
                if edge.capacity > 0 and level[edge.target] == level[node] + 1:
                    pushed = send(edge.target, min(available, edge.capacity))
                    if pushed:
                        edge.capacity -= pushed
                        reverse = graph[edge.target][edge.reverse]
                        reverse.capacity += pushed
                        return pushed
                cursor[node] += 1
            return 0

        while True:
            pushed = send(source, 1 << 60)
            if not pushed:
                break
            total += pushed
