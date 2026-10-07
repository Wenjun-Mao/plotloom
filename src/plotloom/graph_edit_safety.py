"""Incomplete draft states are allowed; edits cannot add structural violations."""
from collections import Counter

from .domain import ProjectBrief
from .graph_authoring_drafts import GraphAuthoringDraft
from .graph_safety_diagnostics import GraphEditSafetyError, GraphSafetyDiagnostic


def structural_diagnostics(draft: GraphAuthoringDraft, brief: ProjectBrief) -> dict[str, GraphSafetyDiagnostic]:
    topology = draft.mapping.topology
    nodes = {node.id: node.kind.value for node in topology.nodes}
    issues: dict[str, GraphSafetyDiagnostic] = {}
    def record(code: str, suffix: str = "", severity: int = 1, **facts) -> None:
        identity = f"{code}:{suffix}" if suffix else code
        previous = issues.get(identity)
        issues[identity] = GraphSafetyDiagnostic(code, identity, severity + (previous.severity if previous else 0), facts)
    for category, values in (("node", [node.id for node in topology.nodes]),
                             ("edge", [edge.id for edge in topology.edges]),
                             ("section", [section.section_id for section in draft.mapping.sections])):
        for identity, count in Counter(values).items():
            if count > 1:
                record(f"duplicate_{category}", identity, count - 1, entityId=identity, actual=count, limit=1)
    if len(nodes) > brief.node_budget:
        record("node_capacity", severity=len(nodes) - brief.node_budget, actual=len(nodes), limit=brief.node_budget)
    if topology.start_node_id is not None and nodes.get(topology.start_node_id) != "start":
        record("invalid_start", nodeId=topology.start_node_id, actualKind=nodes.get(topology.start_node_id), requiredKind="start")
    if sum(kind == "start" for kind in nodes.values()) > 1:
        record("multiple_starts", actual=sum(kind == "start" for kind in nodes.values()), limit=1)
    outgoing: dict[str, list] = {identity: [] for identity in nodes}
    incoming: dict[str, set[str]] = {identity: set() for identity in nodes}
    adjacency: dict[str, list[str]] = {identity: [] for identity in nodes}
    for edge in topology.edges:
        for endpoint in (edge.source_node_id, edge.target_node_id):
            if endpoint is not None and endpoint not in nodes:
                record("unknown_endpoint", edge.id, edgeId=edge.id, sourceNodeId=edge.source_node_id, targetNodeId=edge.target_node_id)
        if edge.source_node_id not in nodes:
            continue
        outgoing[edge.source_node_id].append(edge)
        if edge.target_node_id in nodes:
            adjacency[edge.source_node_id].append(edge.target_node_id)
            incoming[edge.target_node_id].add(edge.source_node_id)
        if edge.source_node_id == edge.target_node_id:
            record("self_link", edge.id, edgeId=edge.id, nodeId=edge.source_node_id)
        required_kind = "choice" if nodes[edge.source_node_id] == "decision" else "continuation"
        if edge.kind.value != required_kind:
            record("edge_kind", edge.id, edgeId=edge.id, nodeId=edge.source_node_id, nodeKind=nodes[edge.source_node_id], actualKind=edge.kind.value, requiredKind=required_kind)
        if edge.target_node_id == topology.start_node_id:
            record("start_input", edge.id, edgeId=edge.id, nodeId=topology.start_node_id)
    for identity, edges in outgoing.items():
        kind = nodes[identity]
        limit = min(6, brief.max_out_degree) if kind == "decision" else 0 if kind == "ending" else 1
        if len(edges) > limit:
            record("out_degree", identity, len(edges) - limit, nodeId=identity, nodeKind=kind, actual=len(edges), limit=limit)
    join_targets = {join.join_node_id for join in topology.joins}
    for identity, sources in incoming.items():
        if len(sources) > 1 and identity not in join_targets:
            record("unreviewed_merge", identity, len(sources) - 1, nodeId=identity, actual=len(sources), limit=1, sourceNodeIds=sorted(sources))
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
            record("cycle", edge.id, edgeId=edge.id, sourceNodeId=edge.source_node_id, targetNodeId=edge.target_node_id)
    return issues


def structural_violations(draft: GraphAuthoringDraft, brief: ProjectBrief) -> Counter[str]:
    return Counter({identity: item.severity for identity, item in structural_diagnostics(draft, brief).items()})


def assert_edit_safe(before: GraphAuthoringDraft, after: GraphAuthoringDraft, brief: ProjectBrief) -> None:
    old, new = structural_violations(before, brief), structural_diagnostics(after, brief)
    introduced = sorted(key for key, item in new.items() if item.severity > old[key])
    if introduced:
        raise GraphEditSafetyError([new[key].public(old[key]) for key in introduced])
