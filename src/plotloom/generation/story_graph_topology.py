"""Bounded topology search, tie-breaking and deterministic materialization."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from uuid import NAMESPACE_URL, uuid5

from ..canonical_schema import (
    V2StoryEdgeKind,
    V2StoryNodeKind,
)
from plotloom.brief_contracts import ProjectBrief
from ..node_footage import creation_footage_mode
from .story_graph_topology_contracts import (
    DEFAULT_MAX_DOWNSTREAM_WORK_UNITS,
    STORY_GRAPH_TOPOLOGY_VERSION,
    StoryGraphTopology,
    StoryGraphTopologyEdge,
    StoryGraphTopologyError,
    StoryGraphTopologyJoin,
    StoryGraphTopologyNode,
    _canonical_json,
)
from .story_graph_topology_flow import _construct_transition, _transition_is_possible


def plan_story_graph_topology(
    *,
    project_id: str,
    brief: ProjectBrief,
    max_downstream_work_units: int = DEFAULT_MAX_DOWNSTREAM_WORK_UNITS,
    max_options_per_choice: int | None = None,
) -> StoryGraphTopology:
    """Find the smallest deterministic DAG satisfying the graph part of a brief.

    The search has no model/provider dependency.  It enumerates layered DAG
    shapes by node count and returns the first valid shape, giving an explicit
    minimum under this canonical, forward-only graph grammar.  A layer is a
    group of equal-progress nodes; each decision layer spans every active path,
    preserving the exact number of decisions on every start-to-ending path.
    """

    if not project_id:
        raise StoryGraphTopologyError("topology.infeasible", "project_id is required")
    limit = min(brief.node_budget, max_downstream_work_units)
    if limit < brief.node_budget and brief.node_budget > max_downstream_work_units:
        # The result still uses the real node budget as an upper bound.  This
        # stable code distinguishes an otherwise valid brief from an executor
        # capacity restriction before any provider request is sent.
        budget_code = "topology.node_budget_too_small"
    else:
        budget_code = "topology.infeasible"
    if brief.max_out_degree < 2 and brief.decision_points_per_path:
        raise StoryGraphTopologyError(
            "topology.infeasible", "decision points require maxOutDegree of at least 2"
        )
    if (
        brief.decision_points_per_path
        and brief.ending_count == 1
        and brief.desired_join_count == 0
    ):
        # A decision has at least two distinct successors; reaching one ending
        # therefore requires a merge, which is forbidden by this brief.
        raise StoryGraphTopologyError(
            "topology.infeasible",
            "a branching path to one ending requires at least one join",
        )
    # START, ENDING, DECISION, and JOIN are mutually exclusive node kinds, so
    # these requested counts are an unconditional lower bound for every DAG.
    if limit < (
        1
        + brief.ending_count
        + brief.decision_points_per_path
        + brief.desired_join_count
    ):
        raise StoryGraphTopologyError(
            "topology.node_budget_too_small",
            "nodeBudget cannot contain the start, endings, decisions, and joins",
        )

    # Receiving capacity narrows the search, never the frozen author parameters.
    search_brief = (
        brief
        if max_options_per_choice is None
        else brief.model_copy(
            update={"max_out_degree": min(brief.max_out_degree, max_options_per_choice)}
        )
    )
    shape = _find_minimum_shape(search_brief, limit)
    if shape is None:
        raise StoryGraphTopologyError(
            "topology.node_budget_too_small"
            if limit == brief.node_budget
            else budget_code,
            "no Story Graph topology satisfies the requested endings, joins, decisions, and node budget",
        )
    return _materialize_topology(project_id, brief, shape)


@dataclass(frozen=True)
class _Shape:
    # Layer tuples are (kind, width); ENDING is always the final layer.
    layers: tuple[tuple[V2StoryNodeKind, int], ...]
    transitions: tuple[tuple[tuple[int, ...], ...], ...]


@dataclass(frozen=True)
class _PlannerState:
    decisions: int
    joins: int
    kind: V2StoryNodeKind
    width: int


@dataclass(frozen=True)
class _PlannerStep:
    previous: _PlannerState
    joins_added: int


def _find_minimum_shape(brief: ProjectBrief, limit: int) -> _Shape | None:
    """Use bounded dynamic programming to find the minimum layered DAG.

    A state records only facts that can affect a future transition: decision
    depth, joins already consumed, current layer kind, and current width. The
    cheapest path to the same state dominates every more expensive path, so
    the search is finite and does not enumerate graphs or edge matrices.
    """

    start = _PlannerState(0, 0, V2StoryNodeKind.START, 1)
    best_cost: dict[_PlannerState, int] = {start: 1}
    predecessor: dict[_PlannerState, _PlannerStep] = {}
    serial = count()
    queue: list[tuple[int, int, int, str, int, int, _PlannerState]] = []
    heappush(queue, (1, 0, 0, V2StoryNodeKind.START.value, 1, next(serial), start))

    while queue:
        cost, _d, _j, _kind, _width, _serial, state = heappop(queue)
        if best_cost.get(state) != cost:
            continue

        if (
            state.decisions == brief.decision_points_per_path
            and state.joins == brief.desired_join_count
            and cost + brief.ending_count <= limit
            and _transition_is_possible(
                state.width,
                brief.ending_count,
                min_out=_minimum_out_degree(state.kind),
                max_out=_maximum_out_degree(state.kind, brief),
                join_targets=0,
            )
        ):
            return _reconstruct_shape(state, predecessor, brief)

        # Reserve the exact ending layer before considering another interior
        # layer. This is both a node-budget proof and the finite search bound.
        max_target_width = limit - cost - brief.ending_count
        if max_target_width < 1:
            continue
        next_kinds: list[V2StoryNodeKind] = []
        if state.decisions < brief.decision_points_per_path:
            next_kinds.append(V2StoryNodeKind.DECISION)
        next_kinds.append(V2StoryNodeKind.SCENE)

        for next_kind in next_kinds:
            next_decisions = state.decisions + int(
                next_kind == V2StoryNodeKind.DECISION
            )
            max_joins_added = (
                brief.desired_join_count - state.joins
                if next_kind == V2StoryNodeKind.SCENE
                else 0
            )
            for target_width in range(1, max_target_width + 1):
                for joins_added in range(0, min(max_joins_added, target_width) + 1):
                    if not _transition_is_possible(
                        state.width,
                        target_width,
                        min_out=_minimum_out_degree(state.kind),
                        max_out=_maximum_out_degree(state.kind, brief),
                        join_targets=joins_added,
                    ):
                        continue
                    next_state = _PlannerState(
                        next_decisions,
                        state.joins + joins_added,
                        next_kind,
                        target_width,
                    )
                    next_cost = cost + target_width
                    if next_cost >= best_cost.get(next_state, limit + 1):
                        continue
                    best_cost[next_state] = next_cost
                    predecessor[next_state] = _PlannerStep(
                        previous=state,
                        joins_added=joins_added,
                    )
                    heappush(
                        queue,
                        (
                            next_cost,
                            next_state.decisions,
                            next_state.joins,
                            next_state.kind.value,
                            next_state.width,
                            next(serial),
                            next_state,
                        ),
                    )
    return None


def _maximum_out_degree(kind: V2StoryNodeKind, brief: ProjectBrief) -> int:
    return brief.max_out_degree if kind == V2StoryNodeKind.DECISION else 1


def _minimum_out_degree(kind: V2StoryNodeKind) -> int:
    return 2 if kind == V2StoryNodeKind.DECISION else 1


def _reconstruct_shape(
    terminal: _PlannerState,
    predecessor: dict[_PlannerState, _PlannerStep],
    brief: ProjectBrief,
) -> _Shape:
    states = [terminal]
    joins_added: list[int] = []
    cursor = terminal
    while cursor in predecessor:
        step = predecessor[cursor]
        joins_added.append(step.joins_added)
        cursor = step.previous
        states.append(cursor)
    states.reverse()
    joins_added.reverse()

    layers = [(state.kind, state.width) for state in states]
    transitions: list[tuple[tuple[int, ...], ...]] = []
    for source, target, join_count in zip(
        states[:-1], states[1:], joins_added, strict=True
    ):
        transition = _construct_transition(
            source.width,
            target.width,
            min_out=_minimum_out_degree(source.kind),
            max_out=_maximum_out_degree(source.kind, brief),
            join_targets=join_count,
        )
        if transition is None:  # defensive: DP and constructor share one contract
            raise RuntimeError(
                "planner selected a transition that cannot be materialized"
            )
        transitions.append(transition)

    ending_transition = _construct_transition(
        terminal.width,
        brief.ending_count,
        min_out=_minimum_out_degree(terminal.kind),
        max_out=_maximum_out_degree(terminal.kind, brief),
        join_targets=0,
    )
    if ending_transition is None:
        raise RuntimeError(
            "planner selected an ending transition that cannot be materialized"
        )
    layers.append((V2StoryNodeKind.ENDING, brief.ending_count))
    transitions.append(ending_transition)
    return _Shape(layers=tuple(layers), transitions=tuple(transitions))


def _join_target_indices(
    transition: tuple[tuple[int, ...], ...], target_count: int
) -> frozenset[int]:
    """Return targets with two or more distinct incoming source nodes."""

    return frozenset(
        target
        for target in range(target_count)
        if sum(target in row for row in transition) >= 2
    )


def _materialize_topology(
    project_id: str, brief: ProjectBrief, shape: _Shape
) -> StoryGraphTopology:
    parameters = {
        "nodeBudget": brief.node_budget,
        "maxOutDegree": brief.max_out_degree,
        "endingCount": brief.ending_count,
        "decisionPointsPerPath": brief.decision_points_per_path,
        "desiredJoinCount": brief.desired_join_count,
    }
    seed = _canonical_json(
        {
            "version": STORY_GRAPH_TOPOLOGY_VERSION,
            "projectId": project_id,
            "parameters": parameters,
        }
    )
    namespace = uuid5(NAMESPACE_URL, seed)
    join_targets_by_layer = {
        layer_index + 1: _join_target_indices(rows, shape.layers[layer_index + 1][1])
        for layer_index, rows in enumerate(shape.transitions)
        if shape.layers[layer_index + 1][0] == V2StoryNodeKind.SCENE
    }
    layers: list[list[StoryGraphTopologyNode]] = []
    sequence = 0
    for layer_index, (kind, width) in enumerate(shape.layers):
        layer: list[StoryGraphTopologyNode] = []
        for node_index in range(width):
            sequence += 1
            node_kind = (
                V2StoryNodeKind.JOIN
                if node_index in join_targets_by_layer.get(layer_index, frozenset())
                else kind
            )
            layer.append(
                StoryGraphTopologyNode(
                    id=f"node-{uuid5(namespace, f'node:{sequence}')}",
                    kind=node_kind,
                    footage_mode=creation_footage_mode(node_kind.value),
                )
            )
        layers.append(layer)
    edges: list[StoryGraphTopologyEdge] = []
    edge_sequence = 0
    incoming: dict[str, list[str]] = {}
    for layer_index, rows in enumerate(shape.transitions):
        for source_index, targets in enumerate(rows):
            source = layers[layer_index][source_index]
            for target_index in targets:
                target = layers[layer_index + 1][target_index]
                edge_sequence += 1
                edges.append(
                    StoryGraphTopologyEdge(
                        id=f"edge-{uuid5(namespace, f'edge:{edge_sequence}')}",
                        source_node_id=source.id,
                        target_node_id=target.id,
                        kind=V2StoryEdgeKind.CHOICE
                        if source.kind == V2StoryNodeKind.DECISION
                        else V2StoryEdgeKind.CONTINUATION,
                    )
                )
                incoming.setdefault(target.id, []).append(source.id)
    joins: list[StoryGraphTopologyJoin] = []
    for node in (node for layer in layers for node in layer):
        sources = tuple(incoming.get(node.id, ()))
        if len(sources) >= 2:
            joins.append(
                StoryGraphTopologyJoin(
                    id=f"join-{uuid5(namespace, f'join:{node.id}')}",
                    join_node_id=node.id,
                    incoming_node_ids=sources,
                )
            )
    unsigned = {
        "plannerVersion": STORY_GRAPH_TOPOLOGY_VERSION,
        "projectId": project_id,
        "structuralParameters": parameters,
        "startNodeId": layers[0][0].id,
        "nodes": [
            node.model_dump(mode="json", by_alias=True)
            for layer in layers
            for node in layer
        ],
        "edges": [edge.model_dump(mode="json", by_alias=True) for edge in edges],
        "joins": [join.model_dump(mode="json", by_alias=True) for join in joins],
    }
    return StoryGraphTopology(
        **unsigned,
        topology_hash=hashlib.sha256(
            _canonical_json(unsigned).encode("utf-8")
        ).hexdigest(),
    )
