"""Pure current-draft transactions; stable IDs and authored effects stay in place."""
from hashlib import sha256

from .domain import ProjectBrief
from .exceptions import InvalidTransitionError
from .graph_authoring_drafts import DetachedEndpoint, GraphAuthoringDraft
from .graph_commands import (
    AddGraphNode, DeleteGraphNode, GraphCommand, GraphCommandImpact,
    InsertGraphNode, ReassignGraphStart, RetargetGraphEdge, ReuseGraphNode, ReplaceGraphInput,
    ChangeGraphNodeKind, AddGraphEdge, RemoveGraphEdge, AddGraphJoin, RemoveGraphJoin,
)
from .graph_edit_safety import assert_edit_safe
from .node_footage import creation_footage_mode


def _identity(seed: str, purpose: str) -> str:
    return "graph-" + sha256(f"{seed}:{purpose}".encode()).hexdigest()[:24]


def _node(draft, identity):
    result = next((node for node in draft.mapping.topology.nodes if node.id == identity), None)
    if result is None:
        raise InvalidTransitionError(f"节点已不存在：{identity}")
    return result


def _edge(draft, identity):
    result = next((edge for edge in draft.mapping.topology.edges if edge.id == identity), None)
    if result is None:
        raise InvalidTransitionError(f"连接已不存在：{identity}")
    return result


def _retain(draft, edge, endpoint):
    identity = getattr(edge, f"{endpoint}_node_id")
    if identity is None:
        return
    node = _node(draft, identity)
    section = next(item for item in draft.mapping.sections if item.section_id == identity)
    draft.detached_endpoints.setdefault(edge.id, {})[endpoint] = DetachedEndpoint(
        node_id=identity, title=section.title, kind=node.kind.value,
    )


def _append_edge(draft, identity, source, target, kind):
    from .graph_authoring_drafts import DraftSourceEdge
    if any(edge.id == identity for edge in draft.mapping.topology.edges):
        raise InvalidTransitionError(f"连接身份已存在：{identity}")
    draft.mapping.topology.edges.append(DraftSourceEdge(id=identity,
        source_node_id=source, target_node_id=target, kind=kind,
        state_effects={}, entity_state_effects=[]))


def _append_node(draft, command):
    from .graph_authoring_drafts import DraftStorySection, DraftSectionChoice, DraftSourceJoin
    from .source_graph_structure import SourceStructureNode
    if any(node.id == command.node_id for node in draft.mapping.topology.nodes):
        raise InvalidTransitionError("节点身份已存在；请重新准备预览。")
    draft.mapping.topology.nodes.append(SourceStructureNode(id=command.node_id, kind=command.kind))
    draft.mapping.sections.append(DraftStorySection(section_id=command.node_id,
        title="", summary="", ending=command.kind == "ending",
        footage_mode=creation_footage_mode(command.kind)))
    draft.row_hints[command.node_id] = command.row_hint
    draft.selected_node_id = command.node_id
    if command.kind == "decision":
        draft.mapping.choices.append(DraftSectionChoice(choice_id=command.node_id,
            section_id=command.node_id, prompt="", outcomes=[]))
    if command.kind == "join":
        identity = _identity(command.node_id, "join")
        draft.mapping.topology.joins.append(DraftSourceJoin(id=identity,
            join_node_id=command.node_id, incoming_node_ids=[], required_state_keys=[],
            allowed_differences=[], notes=""))
        draft.mapping.join_reconciliations[identity] = ""


def _sync_relationships(draft):
    from .graph_authoring_drafts import DraftBranchOutcome
    edges = draft.mapping.topology.edges
    prior_options = {option.outcome_id: option.model_copy(deep=True)
        for choice in draft.mapping.choices for option in choice.outcomes}
    owners = {option.outcome_id: choice.section_id
        for choice in draft.mapping.choices for option in choice.outcomes}
    for choice in draft.mapping.choices:
        choice.outcomes = []
        for edge in edges:
            owner = edge.source_node_id if edge.source_node_id is not None else owners.get(edge.id)
            if edge.kind.value != "choice" or owner != choice.section_id:
                continue
            option = prior_options.get(edge.id) or DraftBranchOutcome(outcome_id=edge.id,
                label="", consequence="", ending_section_id=edge.target_node_id)
            option.ending_section_id = edge.target_node_id
            choice.outcomes.append(option)
    for join in draft.mapping.topology.joins:
        join.incoming_node_ids = list(dict.fromkeys(edge.source_node_id for edge in edges
            if edge.target_node_id == join.join_node_id and edge.source_node_id is not None))
    decisions = {node.id for node in draft.mapping.topology.nodes if node.kind.value == "decision"}
    # Detached options retain one primary prose owner even after their decision
    # is deleted. Only explicit reassignment/removal can empty that owner.
    draft.mapping.choices = [choice for choice in draft.mapping.choices
        if choice.section_id in decisions or choice.outcomes]


def _retarget(draft, command):
    edge = _edge(draft, command.edge_id)
    if getattr(edge, f"{command.endpoint}_node_id") == command.node_id:
        raise InvalidTransitionError("连接未变化；请选择不同端点或取消。")
    if command.node_id is not None:
        node = _node(draft, command.node_id)
        if command.endpoint == "source":
            expected = "decision" if edge.kind.value == "choice" else "continuation"
            if (node.kind.value == "decision") != (expected == "decision"):
                raise InvalidTransitionError("选项连接必须来自选择点；普通连接不能创建隐式分支。")
        elif edge.entity_state_effects:
            section = next(item for item in draft.mapping.sections if item.section_id == node.id)
            if section.footage_mode == "route_only":
                raise InvalidTransitionError("此连接有场景入口状态效果；请先明确启用目标节点画面。")
    if command.node_id is None:
        _retain(draft, edge, command.endpoint)
    else:
        draft.detached_endpoints.get(edge.id, {}).pop(command.endpoint, None)
    setattr(edge, f"{command.endpoint}_node_id", command.node_id)


def _delete(draft, command):
    node = _node(draft, command.node_id)
    if node.id == draft.mapping.topology.start_node_id:
        raise InvalidTransitionError("当前开场受到保护；请先明确重新指定开场。")
    edges = draft.mapping.topology.edges
    incoming = [edge for edge in edges if edge.target_node_id == node.id]
    outgoing = [edge for edge in edges if edge.source_node_id == node.id]
    if command.method == "safe_bypass":
        connected = [edge for edge in outgoing if edge.target_node_id is not None]
        if node.kind.value not in {"scene", "join"} or not incoming or len(outgoing) != 1 or len(connected) != 1:
            raise InvalidTransitionError("安全绕过需要剧情/汇合节点、有输入且恰有一条已连接后续。")
        continuation = connected[0]
        if continuation.state_effects or continuation.entity_state_effects or any(key.startswith(f"edge:{continuation.id}:") for key in draft.field_buffers):
            raise InvalidTransitionError("后续连接有独立效果，不能合并或丢弃；可选择仅删除并保留待连接内容。")
        target = _node(draft, continuation.target_node_id)
        target_join = next((join for join in draft.mapping.topology.joins if join.join_node_id == target.id), None)
        if len(incoming) > 1 and target_join is None:
            raise InvalidTransitionError("多输入汇合不能安全绕过到单入口节点。")
        for edge in incoming:
            _retarget(draft, RetargetGraphEdge(operation="retarget", edge_id=edge.id,
                endpoint="target", node_id=target.id))
        edges.remove(continuation)
        draft.detached_endpoints.pop(continuation.id, None)
    else:
        for edge in incoming:
            _retain(draft, edge, "target")
            edge.target_node_id = None
        for edge in outgoing:
            _retain(draft, edge, "source")
            edge.source_node_id = None
    draft.mapping.topology.nodes.remove(node)
    draft.mapping.sections = [item for item in draft.mapping.sections if item.section_id != node.id]
    removed_joins = [join for join in draft.mapping.topology.joins if join.join_node_id == node.id]
    for join in removed_joins:
        draft.mapping.topology.joins.remove(join)
        draft.mapping.join_reconciliations.pop(join.id, None)
        draft.field_buffers = {key: value for key, value in draft.field_buffers.items() if not key.startswith(f"join:{join.id}:")}
    draft.row_hints.pop(node.id, None)
    draft.selected_node_id = incoming[0].source_node_id if incoming else draft.mapping.topology.start_node_id


def execute_graph_command(before: GraphAuthoringDraft, command: GraphCommand, brief: ProjectBrief) -> tuple[GraphAuthoringDraft, GraphCommandImpact]:
    draft = before.model_copy(deep=True)
    messages = ["保留所有未选中节点、下游场景、镜头与媒体；本次操作不会生成或批准内容。"]
    if isinstance(command, (AddGraphNode, ReuseGraphNode)):
        if command.source_node_id is not None and _node(draft, command.source_node_id).kind.value != "decision":
            raise InvalidTransitionError("并行新增只可推断明确的选择父节点；普通节点不能隐式分叉。")
        if isinstance(command, ReuseGraphNode):
            node = _node(draft, command.node_id)
            if node.id == draft.mapping.topology.start_node_id or any(edge.target_node_id == node.id and edge.source_node_id is not None for edge in draft.mapping.topology.edges):
                raise InvalidTransitionError("仅可复用没有现有输入的未接入节点；开场受到保护。")
            if command.target_node_id is not None and any(edge.source_node_id == node.id for edge in draft.mapping.topology.edges):
                raise InvalidTransitionError("已有后续保持原样；请取消默认后续，再明确逐条改接。")
            draft.row_hints[node.id] = command.row_hint
            draft.selected_node_id = node.id
            kind = node.kind.value
        else:
            _append_node(draft, command)
            kind = command.kind
        if command.source_node_id is not None:
            _append_edge(draft, command.incoming_edge_id, command.source_node_id, command.node_id, "choice")
        if command.target_node_id is not None:
            if kind == "ending":
                raise InvalidTransitionError("结局没有后续连接。")
            _node(draft, command.target_node_id)
            _append_edge(draft, command.outgoing_edge_id, command.node_id, command.target_node_id,
                "choice" if kind == "decision" else "continuation")
    elif isinstance(command, InsertGraphNode):
        original = _edge(draft, command.edge_id) if command.edge_id else None
        old_target = original.target_node_id if original else None
        _append_node(draft, command)
        if original:
            if original.entity_state_effects and creation_footage_mode(command.kind) == "route_only":
                raise InvalidTransitionError("原连接有场景入口状态效果；插入节点需明确启用画面后再连接。")
            original.target_node_id = command.node_id
            messages.append("原连接的身份、选项与效果留在输入；原目标保留，不删除其正文或下游内容。")
            if command.kind in {"scene", "join"}:
                _append_edge(draft, command.continuation_edge_id, command.node_id, old_target, "continuation")
            elif command.kind == "decision":
                messages.append("新增选择的后续待明确填写；没有猜测原目标属于哪个选项。")
    elif isinstance(command, RetargetGraphEdge):
        _retarget(draft, command)
    elif isinstance(command, ReplaceGraphInput):
        _node(draft, command.node_id)
        chosen = _edge(draft, command.chosen_edge_id)
        if chosen.source_node_id is None:
            raise InvalidTransitionError("请先明确所选输出的起点。")
        if command.prior_edge_id == chosen.id:
            raise InvalidTransitionError("原样选择不会改变入口；请选择另一个精确输出或取消。")
        if command.prior_edge_id is not None:
            prior = _edge(draft, command.prior_edge_id)
            if prior.target_node_id != command.node_id:
                raise InvalidTransitionError("待修改入口已变化，请重新准备预览。")
            _retarget(draft, RetargetGraphEdge(operation="retarget", edge_id=prior.id, endpoint="target", node_id=None))
        _retarget(draft, RetargetGraphEdge(operation="retarget", edge_id=chosen.id, endpoint="target", node_id=command.node_id))
        messages.append("原入口保持待连接；所选输出的旧目标保留，两个端点变化一次确认。")
    elif isinstance(command, DeleteGraphNode):
        _delete(draft, command)
    elif isinstance(command, ReassignGraphStart):
        target = _node(draft, command.node_id)
        if target.kind.value not in {"start", "scene"}:
            raise InvalidTransitionError("只能将普通剧情节点明确指定为开场。")
        previous = _node(draft, draft.mapping.topology.start_node_id) if draft.mapping.topology.start_node_id else None
        if previous:
            previous.kind = "scene"
        target.kind = "start"
        draft.mapping.topology.start_node_id = target.id
    elif isinstance(command, ChangeGraphNodeKind):
        node = _node(draft, command.node_id)
        if node.id == draft.mapping.topology.start_node_id:
            raise InvalidTransitionError("当前开场的类型受到保护。")
        if command.footage_mode == "route_only" and command.kind not in {"decision", "join"}:
            raise InvalidTransitionError("普通剧情与结局必须包含画面。")
        node.kind = command.kind
        section = next(section for section in draft.mapping.sections if section.section_id == node.id)
        section.footage_mode, section.ending = command.footage_mode, command.kind == "ending"
        if command.kind == "decision" and not any(choice.section_id == node.id for choice in draft.mapping.choices):
            from .graph_authoring_drafts import DraftSectionChoice
            draft.mapping.choices.append(DraftSectionChoice(choice_id=node.id, section_id=node.id, prompt="", outcomes=[]))
    elif isinstance(command, AddGraphEdge):
        source = _node(draft, command.source_node_id)
        if command.target_node_id is not None:
            _node(draft, command.target_node_id)
        _append_edge(draft, command.edge_id, source.id, command.target_node_id,
            "choice" if source.kind.value == "decision" else "continuation")
    elif isinstance(command, RemoveGraphEdge):
        draft.mapping.topology.edges.remove(_edge(draft, command.edge_id))
        draft.detached_endpoints.pop(command.edge_id, None)
        draft.field_buffers = {key: value for key, value in draft.field_buffers.items() if not key.startswith(f"edge:{command.edge_id}:")}
    elif isinstance(command, AddGraphJoin):
        from .graph_authoring_drafts import DraftSourceJoin
        _node(draft, command.node_id)
        if any(join.id == command.join_id or join.join_node_id == command.node_id for join in draft.mapping.topology.joins):
            raise InvalidTransitionError("此汇合身份或节点合同已存在。")
        draft.mapping.topology.joins.append(DraftSourceJoin(id=command.join_id,
            join_node_id=command.node_id, incoming_node_ids=[], required_state_keys=[], allowed_differences=[], notes=""))
        draft.mapping.join_reconciliations[command.join_id] = ""
    elif isinstance(command, RemoveGraphJoin):
        join = next((join for join in draft.mapping.topology.joins if join.id == command.join_id), None)
        if join is None:
            raise InvalidTransitionError("汇合合同已不存在。")
        draft.mapping.topology.joins.remove(join)
        draft.mapping.join_reconciliations.pop(join.id, None)
        draft.field_buffers = {key: value for key, value in draft.field_buffers.items() if not key.startswith(f"join:{join.id}:")}
    if isinstance(command, (AddGraphNode, InsertGraphNode)) and command.kind == "decision" and command.create_pending_choices:
        seed = command.outgoing_edge_id if isinstance(command, AddGraphNode) else command.continuation_edge_id
        existing = sum(edge.source_node_id == command.node_id for edge in draft.mapping.topology.edges)
        for index in range(existing, 2):
            _append_edge(draft, _identity(seed, str(index)), command.node_id, None, "choice")
    _sync_relationships(draft)
    draft.mapping.topology_origin = "author"
    assert_edit_safe(before, draft, brief)
    old_nodes = {node.id for node in before.mapping.topology.nodes}
    new_nodes = {node.id for node in draft.mapping.topology.nodes}
    old_edges = {edge.id: edge for edge in before.mapping.topology.edges}
    new_edges = {edge.id: edge for edge in draft.mapping.topology.edges}
    old_joins = {join.id: join for join in before.mapping.topology.joins}
    new_joins = {join.id: join for join in draft.mapping.topology.joins}
    affected = sorted(identity for identity in old_joins.keys() | new_joins.keys() if old_joins.get(identity) != new_joins.get(identity))
    if affected:
        messages.append("汇合输入身份已变化；保留原有事实、允许差异和衔接文字，需重新审阅。")
    return draft, GraphCommandImpact(added_node_ids=sorted(new_nodes - old_nodes), removed_node_ids=sorted(old_nodes - new_nodes),
        added_edge_ids=sorted(new_edges.keys() - old_edges.keys()), removed_edge_ids=sorted(old_edges.keys() - new_edges.keys()),
        changed_edge_ids=sorted(identity for identity in old_edges.keys() & new_edges.keys() if old_edges[identity] != new_edges[identity]),
        affected_join_ids=affected, retained_node_ids=sorted(old_nodes & new_nodes),
        pending_edge_ids=[edge.id for edge in draft.mapping.topology.edges if edge.source_node_id is None or edge.target_node_id is None], messages=messages)
