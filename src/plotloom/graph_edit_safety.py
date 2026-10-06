"""Incomplete draft states are allowed; edits cannot add structural violations."""
from collections import Counter

from .domain import ProjectBrief
from .exceptions import InvalidTransitionError
from .graph_authoring_drafts import GraphAuthoringDraft


def structural_violations(draft: GraphAuthoringDraft, brief: ProjectBrief) -> Counter[str]:
    topology = draft.mapping.topology
    nodes = {node.id: node.kind.value for node in topology.nodes}
    issues: Counter[str] = Counter()
    for category, values in (("node", [node.id for node in topology.nodes]),
                             ("edge", [edge.id for edge in topology.edges]),
                             ("section", [section.section_id for section in draft.mapping.sections])):
        for identity, count in Counter(values).items():
            if count > 1:
                issues[f"duplicate_{category}:{identity}"] = count - 1
    if len(nodes) > brief.node_budget:
        issues["node_capacity"] = len(nodes) - brief.node_budget
    if topology.start_node_id is not None and nodes.get(topology.start_node_id) != "start":
        issues["invalid_start"] += 1
    if sum(kind == "start" for kind in nodes.values()) > 1:
        issues["multiple_starts"] += 1
    outgoing: dict[str, list] = {identity: [] for identity in nodes}
    incoming: dict[str, set[str]] = {identity: set() for identity in nodes}
    adjacency: dict[str, list[str]] = {identity: [] for identity in nodes}
    for edge in topology.edges:
        for endpoint in (edge.source_node_id, edge.target_node_id):
            if endpoint is not None and endpoint not in nodes:
                issues[f"unknown_endpoint:{edge.id}"] += 1
        if edge.source_node_id not in nodes:
            continue
        outgoing[edge.source_node_id].append(edge)
        if edge.target_node_id in nodes:
            adjacency[edge.source_node_id].append(edge.target_node_id)
            incoming[edge.target_node_id].add(edge.source_node_id)
        if edge.source_node_id == edge.target_node_id:
            issues[f"self_link:{edge.id}"] += 1
        required_kind = "choice" if nodes[edge.source_node_id] == "decision" else "continuation"
        if edge.kind.value != required_kind:
            issues[f"edge_kind:{edge.id}"] += 1
        if edge.target_node_id == topology.start_node_id:
            issues[f"start_input:{edge.id}"] += 1
    for identity, edges in outgoing.items():
        kind = nodes[identity]
        limit = min(6, brief.max_out_degree) if kind == "decision" else 0 if kind == "ending" else 1
        if len(edges) > limit:
            issues[f"out_degree:{identity}"] = len(edges) - limit
    join_targets = {join.join_node_id for join in topology.joins}
    for identity, sources in incoming.items():
        if len(sources) > 1 and identity not in join_targets:
            issues[f"unreviewed_merge:{identity}"] = len(sources) - 1
    # Cycle membership is stable by edge identity, so reconnecting cannot hide a
    # new cycle behind an unrelated pre-existing draft error.
    def reaches(origin: str, target: str) -> bool:
        pending, visited = [origin], set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current not in visited:
                visited.add(current)
                pending.extend(adjacency.get(current, []))
        return False
    for edge in topology.edges:
        if edge.source_node_id in nodes and edge.target_node_id in nodes and reaches(edge.target_node_id, edge.source_node_id):
            issues[f"cycle:{edge.id}"] += 1
    return issues


def assert_edit_safe(before: GraphAuthoringDraft, after: GraphAuthoringDraft, brief: ProjectBrief) -> None:
    old, new = structural_violations(before, brief), structural_violations(after, brief)
    introduced = sorted(key for key, count in new.items() if count > old[key])
    if introduced:
        raise InvalidTransitionError("结构修改不能新增或加重错误：" + "；".join(introduced))
