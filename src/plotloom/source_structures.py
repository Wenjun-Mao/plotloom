"""Trusted topology admission, compilation and complete Source playback routes."""
from typing import Any
from .canonical_schema import StoryGraphV2, StoryNodeV2, StoryEdgeV2, JoinContractV2
from .domain import ProjectBrief
from .generation.story_graph_topology import plan_story_graph_topology, StoryGraphTopologyError
from .exceptions import InvalidTransitionError

MAX_SOURCE_OPTIONS = 6


def planned_structure(project_id: str, brief: ProjectBrief):
    try:
        return plan_story_graph_topology(project_id=project_id, brief=brief, max_options_per_choice=MAX_SOURCE_OPTIONS)
    except StoryGraphTopologyError as error:
        explanation = ("剧情节点上限不足以容纳开场、每次完整播放的选择、汇合与结局；请增加节点上限，或减少选择、结局与汇合数量。" if error.code == "topology.node_budget_too_small" else "这些结构设置无法组成完整故事。选择点至少需要两个选项；分支通往同一结局需要汇合。请调整选择次数、结局数、最多选项数或汇合次数。")
        raise InvalidTransitionError(explanation + " 当前每次选择最多支持 6 个选项；输入设置仍保留。") from error


def compile_structure(mapping: Any) -> StoryGraphV2:
    topology = mapping.topology
    sections = {section.section_id: section for section in mapping.sections}
    choices = {choice.section_id: choice for choice in mapping.choices}
    options = {option.outcome_id: option for choice in mapping.choices for option in choice.outcomes}
    return StoryGraphV2(
        start_node_id=topology.start_node_id,
        nodes=[StoryNodeV2(id=node.id, kind=node.kind.value, title=sections[node.id].title, summary=sections[node.id].summary) for node in topology.nodes],
        edges=[StoryEdgeV2(id=edge.id, source_node_id=edge.source_node_id, target_node_id=edge.target_node_id,
            kind=edge.kind.value, choice_text=options[edge.id].label if edge.id in options else None,
            state_effects={"sourceMapChoiceId": edge.source_node_id, "sourceMapOutcomeId": edge.id, "sourceMapConsequence": options[edge.id].consequence} if edge.id in options else {}, entity_state_effects=[]) for edge in topology.edges],
        join_contracts=[JoinContractV2(id=join.id, join_node_id=join.join_node_id, incoming_node_ids=list(join.incoming_node_ids), required_state_keys=[], allowed_differences=[], reconciliation=mapping.join_reconciliations[join.id], notes="Source structure narrative reconciliation; no invented entity-state effects.") for join in topology.joins],
    )


def complete_routes(graph: StoryGraphV2) -> list[list[str]]:
    nodes = {node.id: node for node in graph.nodes}
    outgoing = {node: [edge.target_node_id for edge in graph.edges if edge.source_node_id == node] for node in nodes}
    result = []
    stack = [(graph.start_node_id, [])]
    while stack:
        current, path = stack.pop()
        if current in path:
            raise InvalidTransitionError("剧情结构包含循环，无法形成完整播放路线。")
        path = [*path, current]
        if nodes[current].kind.value == "ending":
            result.append(path)
        else:
            stack.extend((target, path) for target in reversed(outgoing[current]))
    return result


def structure_choices(mapping: Any) -> list[dict[str, Any]]:
    if mapping.topology is None:
        return [mapping.choice.model_dump(mode="json", by_alias=True)]
    return [choice.model_dump(mode="json", by_alias=True) for choice in mapping.choices]
