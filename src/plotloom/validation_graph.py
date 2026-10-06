from __future__ import annotations

from collections import defaultdict, deque
from pydantic import ValidationError
from .canonical_schema import EntityType, StoryBibleV2, StoryGraphV2, V2StoryEdgeKind, V2StoryNodeKind
from .domain import ProjectBrief
from .join_state_values import JoinStateValueContractError, compile_join_state_value_contract
from .edge_entry_states import EdgeEntryStateContractError, compile_edge_entry_state_contract
from .validation_state import _allowed_entity_states
from .validation_issues import DomainValidationError, ValidationIssue, _duplicates, _issue

def validate_story_graph(
    graph: StoryGraphV2,
    brief: ProjectBrief,
    *,
    bible: StoryBibleV2 | None = None,
) -> None:
    issues: list[ValidationIssue] = []
    from .node_footage import route_only_state_issues
    issues.extend(ValidationIssue(**issue) for issue in route_only_state_issues(graph))
    nodes_by_id = {node.id: node for node in graph.nodes}

    for node_id in sorted(_duplicates(node.id for node in graph.nodes)):
        issues.append(_issue("duplicate_node_id", "nodes", f"duplicate story node id: {node_id}"))
    for edge_id in sorted(_duplicates(edge.id for edge in graph.edges)):
        issues.append(_issue("duplicate_edge_id", "edges", f"duplicate story edge id: {edge_id}"))
    if bible is not None:
        allowed_states = _allowed_entity_states(bible)
        for edge in graph.edges:
            seen_entity_effects: set[tuple[EntityType, str]] = set()
            for index, effect in enumerate(edge.entity_state_effects):
                effect_path = f"edges.{edge.id}.entityStateEffects.{index}"
                key = (effect.entity_type, effect.entity_id)
                if key in seen_entity_effects:
                    issues.append(_issue(
                        "duplicate_entity_state_effect",
                        effect_path,
                        "an edge may assign an entity state at most once",
                    ))
                    continue
                seen_entity_effects.add(key)
                known_states = allowed_states[effect.entity_type].get(effect.entity_id)
                if known_states is None:
                    issues.append(_issue(
                        "unknown_entity_state_effect_entity",
                        f"{effect_path}.entityId",
                        "entity state effect references an entity absent from the story bible or has the wrong type",
                    ))
                elif effect.state not in known_states:
                    issues.append(_issue(
                        "invalid_entity_state_effect",
                        f"{effect_path}.state",
                        "entity state effect is not allowed by the story bible",
                    ))
    for contract_id in sorted(_duplicates(contract.id for contract in graph.join_contracts)):
        issues.append(
            _issue("duplicate_join_contract_id", "joinContracts", f"duplicate join contract id: {contract_id}")
        )

    if graph.start_node_id not in nodes_by_id:
        issues.append(_issue("missing_start_node", "startNodeId", "startNodeId does not reference a node"))
    else:
        start_nodes = [node.id for node in graph.nodes if node.kind == V2StoryNodeKind.START]
        if start_nodes != [graph.start_node_id]:
            issues.append(
                _issue(
                    "invalid_start_nodes",
                    "nodes",
                    "the graph must have exactly one start node and it must match startNodeId",
                )
            )

    adjacency: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, set[str]] = defaultdict(set)
    seen_connections: set[tuple[str, str]] = set()
    for index, edge in enumerate(graph.edges):
        path = f"edges.{index}"
        if edge.source_node_id not in nodes_by_id:
            issues.append(_issue("unknown_edge_source", path, f"unknown source node: {edge.source_node_id}"))
            continue
        if edge.target_node_id not in nodes_by_id:
            issues.append(_issue("unknown_edge_target", path, f"unknown target node: {edge.target_node_id}"))
            continue
        if edge.source_node_id == edge.target_node_id:
            issues.append(_issue("self_loop", path, "story graph self-loops are not allowed"))
        connection = (edge.source_node_id, edge.target_node_id)
        if connection in seen_connections:
            issues.append(
                _issue(
                    "duplicate_edge_connection",
                    path,
                    "story graph may not contain duplicate directed connections",
                )
            )
            # Duplicate edge rows must never manufacture an additional branch
            # or consume an extra out-degree slot.
            continue
        seen_connections.add(connection)
        adjacency[edge.source_node_id].append(edge.target_node_id)
        incoming[edge.target_node_id].add(edge.source_node_id)

    if len(graph.nodes) > brief.node_budget:
        issues.append(
            _issue(
                "node_budget_exceeded",
                "nodes",
                f"graph has {len(graph.nodes)} nodes but nodeBudget is {brief.node_budget}",
            )
        )

    for node_id, targets in adjacency.items():
        if len(targets) > 1 and any(edge.source_node_id == node_id and edge.kind != V2StoryEdgeKind.CHOICE for edge in graph.edges):
            issues.append(_issue("implicit_continuation_branch", f"nodes.{node_id}", "every runtime branch must use explicit choice edges"))
        if len(targets) > brief.max_out_degree:
            issues.append(
                _issue(
                    "max_out_degree_exceeded",
                    f"nodes.{node_id}",
                    f"out-degree {len(targets)} exceeds maxOutDegree {brief.max_out_degree}",
                )
            )

    for node in graph.nodes:
        degree = len(adjacency[node.id])
        if node.kind == V2StoryNodeKind.ENDING and degree:
            issues.append(_issue("ending_has_outgoing_edge", f"nodes.{node.id}", "ending nodes must be terminal"))
        if node.kind != V2StoryNodeKind.ENDING and degree == 0:
            issues.append(_issue("dead_end", f"nodes.{node.id}", "non-ending nodes must have an outgoing edge"))
        if node.kind == V2StoryNodeKind.DECISION and degree < 2:
            issues.append(
                _issue("decision_without_branches", f"nodes.{node.id}", "decision nodes require at least two branches")
            )

    endings = [node for node in graph.nodes if node.kind == V2StoryNodeKind.ENDING]
    if len(endings) != brief.ending_count:
        issues.append(
            _issue(
                "ending_count_mismatch",
                "nodes",
                f"graph has {len(endings)} endings but endingCount is {brief.ending_count}",
            )
        )

    # Kahn's algorithm verifies the DAG contract independently of reachability.
    indegree = {node_id: 0 for node_id in nodes_by_id}
    for source_id, targets in adjacency.items():
        if source_id not in nodes_by_id:
            continue
        for target_id in targets:
            if target_id in indegree:
                indegree[target_id] += 1
    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited_count = 0
    while queue:
        node_id = queue.popleft()
        visited_count += 1
        for target_id in adjacency[node_id]:
            if target_id not in indegree:
                continue
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                queue.append(target_id)
    graph_is_dag = visited_count == len(nodes_by_id)
    if not graph_is_dag:
        issues.append(_issue("cycle", "edges", "story graph must be acyclic"))

    reachable: set[str] = set()
    if graph.start_node_id in nodes_by_id:
        frontier = [graph.start_node_id]
        while frontier:
            node_id = frontier.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            frontier.extend(adjacency[node_id])
    unreachable = set(nodes_by_id) - reachable
    if unreachable:
        issues.append(
            _issue(
                "unreachable_nodes",
                "nodes",
                f"nodes are unreachable from startNodeId: {', '.join(sorted(unreachable))}",
            )
        )

    join_node_ids = {node_id for node_id, sources in incoming.items() if len(sources) >= 2}
    if len(join_node_ids) != brief.desired_join_count:
        issues.append(
            _issue(
                "join_count_mismatch",
                "joinContracts",
                f"graph has {len(join_node_ids)} joins but desiredJoinCount is {brief.desired_join_count}",
            )
        )
    contracts_by_node: dict[str, list] = defaultdict(list)
    for contract in graph.join_contracts:
        contracts_by_node[contract.join_node_id].append(contract)
        if contract.join_node_id not in nodes_by_id:
            issues.append(
                _issue(
                    "unknown_join_node",
                    f"joinContracts.{contract.id}",
                    f"unknown join node: {contract.join_node_id}",
                )
            )
            continue
        actual_sources = incoming[contract.join_node_id]
        declared_sources = set(contract.incoming_node_ids)
        if len(actual_sources) < 2:
            issues.append(
                _issue(
                    "not_a_join",
                    f"joinContracts.{contract.id}",
                    "join contract target must have at least two incoming story edges",
                )
            )
        if declared_sources != actual_sources:
            issues.append(
                _issue(
                    "join_sources_mismatch",
                    f"joinContracts.{contract.id}.incomingNodeIds",
                    "incomingNodeIds must exactly match the graph's incoming sources",
                )
            )
    for join_node_id in join_node_ids:
        if len(contracts_by_node[join_node_id]) != 1:
            issues.append(
                _issue(
                    "join_contract_cardinality",
                    "joinContracts",
                    f"join node {join_node_id} requires exactly one join contract",
                )
            )

    # Path counting is only meaningful after the topology is known to be a DAG.
    if graph_is_dag and graph.start_node_id in nodes_by_id:
        path_stack: list[tuple[str, int, tuple[str, ...]]] = [(graph.start_node_id, 0, ())]
        while path_stack:
            node_id, decision_count, path = path_stack.pop()
            node = nodes_by_id[node_id]
            next_count = decision_count + int(any(edge.source_node_id == node_id and edge.kind == V2StoryEdgeKind.CHOICE for edge in graph.edges))
            next_path = (*path, node_id)
            if node.kind == V2StoryNodeKind.ENDING:
                if next_count != brief.decision_points_per_path:
                    issues.append(
                        _issue(
                            "decision_points_per_path_mismatch",
                            "edges",
                            f"path {' -> '.join(next_path)} has {next_count} decision points; expected "
                            f"{brief.decision_points_per_path}",
                        )
                    )
                continue
            for target_id in adjacency[node_id]:
                path_stack.append((target_id, next_count, next_path))

    if not issues:
        try:
            compile_join_state_value_contract(graph)
            # A graph with path-dependent typed entry state has no truthful
            # single Scene Beats entry.  Admit this at the Graph boundary,
            # not only when a later stage happens to compile the contract.
            compile_edge_entry_state_contract(graph)
        except ValidationError as error:
            issues.extend(
                _issue(
                    "join_state_contract_schema_invalid",
                    ".".join(str(part) for part in item.get("loc") or ()),
                    item["msg"],
                )
                for item in error.errors(
                    include_url=False,
                    include_context=False,
                )
            )
        except JoinStateValueContractError as error:
            issues.extend(
                _issue(issue.code, issue.path, issue.message)
                for issue in error.issues
            )
        except EdgeEntryStateContractError as error:
            issues.extend(
                _issue(issue.code, issue.path, issue.message)
                for issue in error.issues
            )

    if issues:
        raise DomainValidationError(issues)
