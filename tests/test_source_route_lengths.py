"""The approved story's short ending does not require an invented extra choice."""
import pytest

from plotloom.brief_contracts import ProjectBrief
from plotloom.canonical_schema import StoryGraphV2
from plotloom.source_outline_contracts import validate_section_map_graph
from plotloom.validation import DomainValidationError, validate_story_graph


def last_projection_graph():
    roles = [("n00", "start"), ("c01", "decision"), ("n10", "scene"), ("c02", "decision"),
        ("e01", "ending"), ("e02", "ending"), ("e03", "ending")]
    routes = [("edge_opening_choice", "n00", "c01", None),
        ("edge_submit_alone", "c01", "e01", "现在写明真相并封存"),
        ("edge_hear_explanation", "c01", "n10", "先听阿岚解释"),
        ("edge_explanation_choice", "n10", "c02", None),
        ("edge_submit_together", "c02", "e02", "让她签字，一起交接"),
        ("edge_destroy_evidence", "c02", "e03", "销毁卡，保留旧记录")]
    return StoryGraphV2(startNodeId="n00", joinContracts=[],
        nodes=[{"id": identifier, "title": identifier, "summary": identifier, "kind": kind,
            "footageMode": "route_only" if kind == "decision" else "footage"} for identifier, kind in roles],
        edges=[{"id": identifier, "sourceNodeId": source, "targetNodeId": target,
            "kind": "choice" if label else "continuation", "choiceText": label,
            "stateEffects": {}, "entityStateEffects": []} for identifier, source, target, label in routes])


def test_source_owner_admits_exact_seven_roles_six_edges_with_one_two_two_choices():
    graph = last_projection_graph()
    brief = ProjectBrief(title="放映室最后一夜", synopsis="原始故事", decisionPointsPerPath=2,
        endingCount=3, desiredJoinCount=0, nodeBudget=7, maxOutDegree=2)
    before = graph.model_dump(mode="json", by_alias=True)
    validate_section_map_graph(graph, brief)
    assert graph.model_dump(mode="json", by_alias=True) == before
    with pytest.raises(DomainValidationError, match="decision points"):
        validate_story_graph(graph, brief)  # Generic generation remains exact.
    with pytest.raises(DomainValidationError, match="at most 1"):
        validate_section_map_graph(graph, brief.model_copy(update={"decision_points_per_path": 1}))
    with pytest.raises(DomainValidationError, match="nodeBudget"):
        validate_section_map_graph(graph, brief.model_copy(update={"node_budget": 6}))
