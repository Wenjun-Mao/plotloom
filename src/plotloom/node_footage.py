"""Current creation policy and scene-owned state admission for routing controls."""
from typing import Literal

from .canonical_schema import StoryGraphV2, V2StoryNodeKind


def creation_footage_mode(kind: V2StoryNodeKind | str) -> Literal["footage", "route_only"]:
    """Creation policy, never a missing-field default at a receiving boundary."""
    return "route_only" if kind in {"decision", "join"} else "footage"


def route_only_state_issues(graph: StoryGraphV2) -> list[dict[str, str]]:
    route_only = {node.id for node in graph.nodes if node.footage_mode == "route_only"}
    issues = []
    for edge in graph.edges:
        if edge.target_node_id in route_only and edge.entity_state_effects:
            issues.append({
                "code": "route_only_entity_entry_required",
                "path": f"nodes.{edge.target_node_id}.footageMode",
                "message": f"节点 {edge.target_node_id} 的入边 {edge.id} 要求实际场景入口状态；请明确为此节点包含画面。边效果与草稿仍保留。",
            })
    for contract in graph.join_contracts:
        if contract.join_node_id in route_only and contract.required_state_keys:
            issues.append({
                "code": "route_only_join_scene_required",
                "path": f"nodes.{contract.join_node_id}.footageMode",
                "message": f"汇合 {contract.join_node_id} 要求实际场景入口事实；请明确为此节点包含画面。汇合契约与草稿仍保留。",
            })
    return issues
