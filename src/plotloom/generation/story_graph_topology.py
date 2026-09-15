"""Deterministic, model-independent Story Graph topology planning.

The language model supplies prose for a graph, never its control-flow.  This
module owns the latter: it searches a small layered DAG space, assigns stable
IDs, and binds a content-only response back to the trusted skeleton.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
import hashlib
import json
from itertools import count
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import ConfigDict, Field, ValidationError, model_validator

from ..canonical_schema import StoryGraphV2
from ..domain import (
    CamelModel,
    JoinContract,
    ProjectBrief,
    RequiredEntityState,
    StoryBibleV2,
    StoryEdge,
    StoryEdgeKind,
    StoryGraph,
    StoryNode,
    StoryNodeKind,
    to_camel,
)
from ..validation import DomainValidationError, validate_story_graph
from ..join_state_values import (
    JoinStateValueContractError,
    compile_join_state_value_contract,
)
from .json_schema import explicit_presence_json_schema, inline_local_json_references


STORY_GRAPH_TOPOLOGY_VERSION = "story_graph_topology.v1"
STORY_GRAPH_CONTENT_FILL_SCHEMA_ID = "story_graph_content_fill.v4"
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


class StoryGraphContentBindingError(ValueError):
    """A content fill attempted to omit, duplicate, or alter trusted IDs."""

    def __init__(self, issues: list[dict[str, str]]) -> None:
        self.issues = issues
        super().__init__("; ".join(issue["message"] for issue in issues))


class _FrozenCamelModel(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class StoryGraphTopologyNode(_FrozenCamelModel):
    id: str = Field(min_length=1)
    kind: StoryNodeKind


class StoryGraphTopologyEdge(_FrozenCamelModel):
    id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    kind: StoryEdgeKind


class StoryGraphTopologyJoin(_FrozenCamelModel):
    id: str = Field(min_length=1)
    join_node_id: str = Field(min_length=1)
    incoming_node_ids: tuple[str, ...] = Field(min_length=2)


class StoryGraphTopology(_FrozenCamelModel):
    """The frozen structural portion of a newly requested Story Graph."""

    planner_version: str = STORY_GRAPH_TOPOLOGY_VERSION
    project_id: str = Field(min_length=1)
    structural_parameters: dict[str, int]
    start_node_id: str = Field(min_length=1)
    nodes: tuple[StoryGraphTopologyNode, ...]
    edges: tuple[StoryGraphTopologyEdge, ...]
    joins: tuple[StoryGraphTopologyJoin, ...]
    topology_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_topology_hash(self) -> "StoryGraphTopology":
        unsigned = self.model_dump(mode="json", by_alias=True, exclude={"topology_hash"})
        expected = hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
        if self.topology_hash != expected:
            raise ValueError("topologyHash does not match the immutable topology")
        _validate_topology_semantics(self)
        return self


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


def plan_story_graph_topology(
    *,
    project_id: str,
    brief: ProjectBrief,
    max_downstream_work_units: int = DEFAULT_MAX_DOWNSTREAM_WORK_UNITS,
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

    shape = _find_minimum_shape(brief, limit)
    if shape is None:
        raise StoryGraphTopologyError(
            "topology.node_budget_too_small" if limit == brief.node_budget else budget_code,
            "no Story Graph topology satisfies the requested endings, joins, decisions, and node budget",
        )
    return _materialize_topology(project_id, brief, shape)


@dataclass(frozen=True)
class _Shape:
    # Layer tuples are (kind, width); ENDING is always the final layer.
    layers: tuple[tuple[StoryNodeKind, int], ...]
    transitions: tuple[tuple[tuple[int, ...], ...], ...]


@dataclass(frozen=True)
class _PlannerState:
    decisions: int
    joins: int
    kind: StoryNodeKind
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

    start = _PlannerState(0, 0, StoryNodeKind.START, 1)
    best_cost: dict[_PlannerState, int] = {start: 1}
    predecessor: dict[_PlannerState, _PlannerStep] = {}
    serial = count()
    queue: list[tuple[int, int, int, str, int, int, _PlannerState]] = []
    heappush(queue, (1, 0, 0, StoryNodeKind.START.value, 1, next(serial), start))

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
                max_out=brief.max_out_degree,
                join_targets=0,
            )
        ):
            return _reconstruct_shape(state, predecessor, brief)

        # Reserve the exact ending layer before considering another interior
        # layer. This is both a node-budget proof and the finite search bound.
        max_target_width = limit - cost - brief.ending_count
        if max_target_width < 1:
            continue
        next_kinds: list[StoryNodeKind] = []
        if state.decisions < brief.decision_points_per_path:
            next_kinds.append(StoryNodeKind.DECISION)
        next_kinds.append(StoryNodeKind.SCENE)

        for next_kind in next_kinds:
            next_decisions = state.decisions + int(
                next_kind == StoryNodeKind.DECISION
            )
            max_joins_added = (
                brief.desired_join_count - state.joins
                if next_kind == StoryNodeKind.SCENE
                else 0
            )
            for target_width in range(1, max_target_width + 1):
                for joins_added in range(
                    0, min(max_joins_added, target_width) + 1
                ):
                    if not _transition_is_possible(
                        state.width,
                        target_width,
                        min_out=_minimum_out_degree(state.kind),
                        max_out=brief.max_out_degree,
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


def _minimum_out_degree(kind: StoryNodeKind) -> int:
    return 2 if kind == StoryNodeKind.DECISION else 1


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
            max_out=brief.max_out_degree,
            join_targets=join_count,
        )
        if transition is None:  # defensive: DP and constructor share one contract
            raise RuntimeError("planner selected a transition that cannot be materialized")
        transitions.append(transition)

    ending_transition = _construct_transition(
        terminal.width,
        brief.ending_count,
        min_out=_minimum_out_degree(terminal.kind),
        max_out=brief.max_out_degree,
        join_targets=0,
    )
    if ending_transition is None:
        raise RuntimeError("planner selected an ending transition that cannot be materialized")
    layers.append((StoryNodeKind.ENDING, brief.ending_count))
    transitions.append(ending_transition)
    return _Shape(layers=tuple(layers), transitions=tuple(transitions))


def _join_target_indices(
    transition: tuple[tuple[int, ...], ...], target_count: int
) -> frozenset[int]:
    """Return targets with two or more distinct incoming source nodes."""

    return frozenset(
        target for target in range(target_count) if sum(target in row for row in transition) >= 2
    )


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
    row_column_edges: list[list[_FlowEdge]] = [
        [] for _ in range(source_count)
    ]

    def add_edge(source: int, target: int, capacity: int) -> _FlowEdge:
        forward = _FlowEdge(target, len(graph[target]), capacity, capacity)
        reverse = _FlowEdge(source, len(graph[source]), 0, 0)
        graph[source].append(forward)
        graph[target].append(reverse)
        return forward

    def add_bounded_edge(
        source: int, target: int, lower: int, upper: int
    ) -> _FlowEdge:
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


def _materialize_topology(project_id: str, brief: ProjectBrief, shape: _Shape) -> StoryGraphTopology:
    parameters = {
        "nodeBudget": brief.node_budget,
        "maxOutDegree": brief.max_out_degree,
        "endingCount": brief.ending_count,
        "decisionPointsPerPath": brief.decision_points_per_path,
        "desiredJoinCount": brief.desired_join_count,
    }
    seed = _canonical_json(
        {"version": STORY_GRAPH_TOPOLOGY_VERSION, "projectId": project_id, "parameters": parameters}
    )
    namespace = uuid5(NAMESPACE_URL, seed)
    join_targets_by_layer = {
        layer_index + 1: _join_target_indices(rows, shape.layers[layer_index + 1][1])
        for layer_index, rows in enumerate(shape.transitions)
        if shape.layers[layer_index + 1][0] == StoryNodeKind.SCENE
    }
    layers: list[list[StoryGraphTopologyNode]] = []
    sequence = 0
    for layer_index, (kind, width) in enumerate(shape.layers):
        layer: list[StoryGraphTopologyNode] = []
        for node_index in range(width):
            sequence += 1
            layer.append(
                StoryGraphTopologyNode(
                    id=f"node-{uuid5(namespace, f'node:{sequence}')}",
                    kind=(
                        StoryNodeKind.JOIN
                        if node_index in join_targets_by_layer.get(layer_index, frozenset())
                        else kind
                    ),
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
                        kind=StoryEdgeKind.CHOICE if source.kind == StoryNodeKind.DECISION else StoryEdgeKind.CONTINUATION,
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
        "nodes": [node.model_dump(mode="json", by_alias=True) for layer in layers for node in layer],
        "edges": [edge.model_dump(mode="json", by_alias=True) for edge in edges],
        "joins": [join.model_dump(mode="json", by_alias=True) for join in joins],
    }
    return StoryGraphTopology(
        **unsigned,
        topology_hash=hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest(),
    )


def bind_story_graph_content_fill(
    topology: StoryGraphTopology,
    content: StoryGraphContentFill | dict[str, Any],
    *,
    brief: ProjectBrief,
    bible: StoryBibleV2 | None = None,
) -> StoryGraph:
    """Bind model prose to immutable topology and rerun the full domain validator."""

    try:
        fill = content if isinstance(content, StoryGraphContentFill) else StoryGraphContentFill.model_validate(content, by_alias=True)
    except ValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {"code": f"schema.{error['type']}", "path": _path(error.get("loc") or ()), "message": error["msg"]}
                for error in exc.errors(include_url=False, include_context=False)
            ]
        ) from exc
    _assert_exact_ids("nodes", [item.id for item in fill.nodes], [item.id for item in topology.nodes])
    _assert_exact_ids("edges", [item.id for item in fill.edges], [item.id for item in topology.edges])
    _assert_exact_ids("joinContracts", [item.id for item in fill.join_contracts], [item.id for item in topology.joins])
    _assert_v2_content_contract(topology, fill)
    try:
        graph = _bound_story_graph_from_content_fill(topology, fill)
        validate_story_graph(graph, brief, bible=bible)
    except ValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {
                    "code": f"semantic.{error['type']}",
                    "path": _path(error.get("loc") or ()),
                    "message": error["msg"],
                }
                for error in exc.errors(include_url=False, include_context=False)
            ]
        ) from exc
    except DomainValidationError as exc:
        raise StoryGraphContentBindingError(
            [{"code": f"semantic.{issue['code']}", "path": issue["path"], "message": issue["message"]} for issue in exc.issues]
        ) from exc
    # The durable generation path installs V2 only.  Keep this projection at
    # the binding boundary so a value that the historical V1 shape permits
    # cannot escape as a worker exception.  The adapter converts this typed
    # binding failure into a correction-eligible ValidationReport.
    try:
        v2_graph = StoryGraphV2.model_validate(
            graph.model_dump(mode="json", by_alias=True)
        )
        validate_story_graph(v2_graph, brief, strict_v2=True, bible=bible)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {
                    "code": "semantic.v2_projection_invalid",
                    "path": _path(error.get("loc") or ()),
                    "message": error["msg"],
                }
                for error in exc.errors(include_url=False, include_context=False)
            ]
        ) from exc
    except DomainValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {
                    "code": f"semantic.{issue['code']}",
                    "path": issue["path"],
                    "message": issue["message"],
                }
                for issue in exc.issues
            ]
        ) from exc
    return graph


def story_graph_content_fill_join_diagnostic_issues(
    topology: StoryGraphTopology,
    content: StoryGraphContentFill,
) -> list[dict[str, str]]:
    """Expose independent join defects hidden by an allowed-key subset error.

    A response with an allowed-only key cannot construct the canonical V2 join
    contract, so normal binding correctly stops before the join-value compiler.
    For correction evidence only, this helper creates an in-memory diagnostic
    view whose required keys are the ordered union of required and allowed
    keys.  It never accepts, persists, or rewrites the model response.  The
    shared join-state compiler remains the authority for missing values,
    conflicts, finite JSON, and reconciliation semantics.
    """

    _assert_exact_ids("nodes", [item.id for item in content.nodes], [item.id for item in topology.nodes])
    _assert_exact_ids("edges", [item.id for item in content.edges], [item.id for item in topology.edges])
    _assert_exact_ids("joinContracts", [item.id for item in content.join_contracts], [item.id for item in topology.joins])

    try:
        diagnostic_graph = _bound_story_graph_from_content_fill(
            topology,
            content,
            include_allowed_in_required=True,
        )
        # Keep native values (not ``mode='json'``) so NaN/Infinity remain
        # visible to finite_canonical_json instead of being silently coerced.
        diagnostic_v2 = StoryGraphV2.model_validate(
            diagnostic_graph.model_dump(by_alias=True)
        )
        compile_join_state_value_contract(diagnostic_v2)
    except JoinStateValueContractError as exc:
        diagnostic_issues = list(exc.issues)
    except ValidationError:
        # Blank/duplicate keys and other malformed join arrays do not grant
        # extra repair authority.  Normal binding reports those defects.
        return []
    else:
        return []

    promoted_by_join = {
        join.id: set(join.allowed_differences) - set(join.required_state_keys)
        for join in content.join_contracts
    }
    joins_by_incoming_edge = {
        edge.id: join.id
        for join in topology.joins
        for edge in topology.edges
        if edge.target_node_id == join.join_node_id
        and edge.source_node_id in set(join.incoming_node_ids)
    }
    retained: list[dict[str, str]] = []
    for issue in diagnostic_issues:
        if issue.code == "join_state_effect_missing":
            parts = issue.path.split(".")
            if len(parts) == 4 and parts[0] == "edges":
                join_id = joins_by_incoming_edge.get(parts[1])
                if join_id is not None and parts[3] in promoted_by_join[join_id]:
                    # The subset repair fact already authorizes writing every
                    # promoted allowed key to each immutable incoming edge.
                    continue
        retained.append(
            {
                "code": f"semantic.{issue.code}",
                "path": issue.path,
                "message": issue.message,
            }
        )
    return retained


def _bound_story_graph_from_content_fill(
    topology: StoryGraphTopology,
    fill: StoryGraphContentFill,
    *,
    include_allowed_in_required: bool = False,
) -> StoryGraph:
    """Bind frozen topology to content, optionally normalizing join diagnostics."""

    node_fill = {item.id: item for item in fill.nodes}
    edge_fill = {item.id: item for item in fill.edges}
    join_fill = {item.id: item for item in fill.join_contracts}
    return StoryGraph(
        start_node_id=topology.start_node_id,
        nodes=[
            StoryNode(
                id=item.id,
                kind=item.kind,
                title=node_fill[item.id].title,
                summary=node_fill[item.id].summary,
            )
            for item in topology.nodes
        ],
        edges=[
            StoryEdge(
                id=item.id,
                source_node_id=item.source_node_id,
                target_node_id=item.target_node_id,
                kind=item.kind,
                choice_text=edge_fill[item.id].choice_text,
                state_effects=edge_fill[item.id].state_effects,
                entity_state_effects=edge_fill[item.id].entity_state_effects,
            )
            for item in topology.edges
        ],
        join_contracts=[
            JoinContract(
                id=item.id,
                join_node_id=item.join_node_id,
                incoming_node_ids=list(item.incoming_node_ids),
                required_state_keys=(
                    list(dict.fromkeys(
                        (*join_fill[item.id].required_state_keys, *join_fill[item.id].allowed_differences)
                    ))
                    if include_allowed_in_required
                    else join_fill[item.id].required_state_keys
                ),
                allowed_differences=join_fill[item.id].allowed_differences,
                reconciliation=join_fill[item.id].reconciliation,
                notes=join_fill[item.id].notes,
            )
            for item in topology.joins
        ],
    )


def _validate_topology_semantics(topology: StoryGraphTopology) -> None:
    """Apply the full graph validator to a content-free trusted skeleton."""

    if topology.planner_version != STORY_GRAPH_TOPOLOGY_VERSION:
        raise ValueError(f"unsupported plannerVersion: {topology.planner_version}")
    if set(topology.structural_parameters) != _STRUCTURAL_PARAMETER_KEYS:
        raise ValueError("structuralParameters must contain the canonical graph constraints")

    nodes_by_id = {node.id: node for node in topology.nodes}
    incoming: dict[str, set[str]] = {node.id: set() for node in topology.nodes}
    for edge in topology.edges:
        if edge.source_node_id in nodes_by_id and edge.target_node_id in nodes_by_id:
            incoming[edge.target_node_id].add(edge.source_node_id)
    actual_join_node_ids = {node_id for node_id, sources in incoming.items() if len(sources) >= 2}
    declared_join_node_ids = {join.join_node_id for join in topology.joins}
    for node_id in actual_join_node_ids:
        if nodes_by_id[node_id].kind != StoryNodeKind.JOIN:
            raise ValueError("join node must have kind 'join'")
    if {node.id for node in topology.nodes if node.kind == StoryNodeKind.JOIN} != actual_join_node_ids:
        raise ValueError("JOIN node kind must correspond exactly to a graph merge")
    if declared_join_node_ids != actual_join_node_ids:
        raise ValueError("joins must correspond exactly to graph merge nodes")

    try:
        brief = ProjectBrief.model_validate(
            {"title": "Topology", "synopsis": "Structural validation.", **topology.structural_parameters},
            by_alias=True,
        )
        validate_story_graph(
            StoryGraph(
                start_node_id=topology.start_node_id,
                nodes=[
                    StoryNode(id=node.id, kind=node.kind, title="Topology", summary="Structural node.")
                    for node in topology.nodes
                ],
                edges=[
                    StoryEdge(
                        id=edge.id,
                        source_node_id=edge.source_node_id,
                        target_node_id=edge.target_node_id,
                        kind=edge.kind,
                        choice_text="Continue" if edge.kind == StoryEdgeKind.CHOICE else None,
                    )
                    for edge in topology.edges
                ],
                join_contracts=[
                    JoinContract(
                        id=join.id,
                        join_node_id=join.join_node_id,
                        incoming_node_ids=list(join.incoming_node_ids),
                    )
                    for join in topology.joins
                ],
            ),
            brief,
        )
    except (DomainValidationError, ValidationError) as exc:
        raise ValueError(f"invalid deterministic Story Graph topology: {exc}") from exc


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
            {"id": item.id, "kind": item.kind.value} for item in topology.nodes
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
    for edge in topology.edges:
        if edge.kind == StoryEdgeKind.CONTINUATION:
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
                    "properties": {"choiceText": choice_text_schema},
                    "required": ["choiceText"],
                },
            }
        )
    edge_schema["allOf"] = contracts


def _assert_v2_content_contract(
    topology: StoryGraphTopology, fill: StoryGraphContentFill
) -> None:
    """Reject all model-controlled values that V2 would reject after binding.

    The original binder builds a V1 graph to preserve historical read types.
    V1 permits several values that current V2 authoring forbids.  Classifying
    those values here turns ordinary model mistakes into stable, repairable
    validation issues instead of letting a later V2 projection crash a worker.
    """

    edge_by_id = {edge.id: edge for edge in topology.edges}
    issues: list[dict[str, str]] = []
    for edge in fill.edges:
        topology_edge = edge_by_id[edge.id]
        path = f"edges.{edge.id}.choiceText"
        if topology_edge.kind == StoryEdgeKind.CONTINUATION and edge.choice_text is not None:
            issues.append(
                {
                    "code": "semantic.continuation_choice_text_must_be_null",
                    "path": path,
                    "message": "continuation edges must set choiceText to null",
                }
            )
        elif topology_edge.kind == StoryEdgeKind.CHOICE and (
            edge.choice_text is None or not edge.choice_text.strip()
        ):
            issues.append(
                {
                    "code": "semantic.choice_edge_choice_text_required",
                    "path": path,
                    "message": "choice edges require a non-blank choiceText",
                }
            )

    for join in fill.join_contracts:
        required_keys = join.required_state_keys
        allowed_differences = join.allowed_differences
        for field_name, values in (
            ("requiredStateKeys", required_keys),
            ("allowedDifferences", allowed_differences),
        ):
            path = f"joinContracts.{join.id}.{field_name}"
            if any(not value.strip() for value in values):
                issues.append(
                    {
                        "code": "semantic.join_state_key_must_be_non_blank",
                        "path": path,
                        "message": f"{field_name} entries must be non-blank",
                    }
                )
            if len(values) != len(set(values)):
                issues.append(
                    {
                        "code": "semantic.join_state_keys_must_be_unique",
                        "path": path,
                        "message": f"{field_name} entries must be unique",
                    }
                )
        if not set(allowed_differences) <= set(required_keys):
            issues.append(
                {
                    "code": "semantic.join_allowed_differences_must_be_required",
                    "path": f"joinContracts.{join.id}.allowedDifferences",
                    "message": "allowedDifferences must be contained in requiredStateKeys",
                }
            )
    if issues:
        raise StoryGraphContentBindingError(issues)


def _assert_exact_ids(label: str, actual: list[str], expected: list[str]) -> None:
    duplicate = sorted({item for item in actual if actual.count(item) > 1})
    unknown = sorted(set(actual) - set(expected))
    missing = sorted(set(expected) - set(actual))
    issues: list[dict[str, str]] = []
    if duplicate:
        issues.append({"code": "binding.duplicate_id", "path": label, "message": f"duplicate {label} IDs: {', '.join(duplicate)}"})
    if unknown:
        issues.append({"code": "binding.unknown_id", "path": label, "message": f"unknown {label} IDs: {', '.join(unknown)}"})
    if missing:
        issues.append({"code": "binding.missing_id", "path": label, "message": f"missing {label} IDs: {', '.join(missing)}"})
    if issues:
        raise StoryGraphContentBindingError(issues)


def _path(parts: Any) -> str:
    return ".".join(str(part) for part in parts)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
