from __future__ import annotations

import hashlib
import json
from time import perf_counter

import pytest
from pydantic import ValidationError

from plotloom.domain import ProjectBrief, StageName, StoryBibleV2, StoryEdgeKind, StoryNodeKind
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.story_graph_topology import (
    StoryGraphContentBindingError,
    StoryGraphTopologyError,
    bind_story_graph_content_fill,
    plan_story_graph_topology,
)
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import compile_work_unit_request
from plotloom.validation import validate_story_graph


def _brief(**updates: int) -> ProjectBrief:
    values = {
        "ending_count": 3,
        "decision_points_per_path": 2,
        "desired_join_count": 1,
        "node_budget": 9,
        "max_out_degree": 3,
    }
    values.update(updates)
    return ProjectBrief(title="冻结骨架", synopsis="主角在失控列车上寻找出口。", **values)


def _complete_fill(topology) -> dict:
    return {
        "nodes": [
            {"id": item.id, "title": f"节点 {index}", "summary": f"推进剧情 {index}"}
            for index, item in enumerate(topology.nodes, start=1)
        ],
        "edges": [
            {
                "id": item.id,
                "choiceText": "继续前进" if item.kind == StoryEdgeKind.CHOICE else None,
                "stateEffects": {"route": item.id} if item.kind == StoryEdgeKind.CHOICE else {},
            }
            for item in topology.edges
        ],
        "joinContracts": [
            {
                "id": item.id,
                "requiredStateKeys": ["route"],
                "allowedDifferences": ["route"],
                "reconciliation": "所有路线都抵达同一个危机。",
                "notes": "保留分支后果。",
            }
            for item in topology.joins
        ],
    }


def test_planner_is_deterministic_minimal_and_domain_valid() -> None:
    brief = _brief()
    first = plan_story_graph_topology(project_id="project-a", brief=brief)
    second = plan_story_graph_topology(project_id="project-a", brief=brief)

    assert first == second
    assert len(first.nodes) == 9
    assert len(first.joins) == brief.desired_join_count
    assert first.nodes[0].kind == StoryNodeKind.START
    node_by_id = {node.id: node for node in first.nodes}
    assert len([node for node in first.nodes if node.kind == StoryNodeKind.ENDING]) == brief.ending_count
    assert all(node_by_id[join.join_node_id].kind == StoryNodeKind.JOIN for join in first.joins)

    graph = bind_story_graph_content_fill(first, _complete_fill(first), brief=brief)
    validate_story_graph(graph, brief)
    assert graph.start_node_id == first.start_node_id
    assert {edge.id for edge in graph.edges} == {edge.id for edge in first.edges}


def test_planner_reports_stable_pre_provider_errors() -> None:
    with pytest.raises(StoryGraphTopologyError) as limited:
        plan_story_graph_topology(project_id="project-a", brief=_brief(node_budget=8))
    assert limited.value.code == "topology.node_budget_too_small"

    with pytest.raises(StoryGraphTopologyError) as impossible:
        plan_story_graph_topology(
            project_id="project-a",
            brief=_brief(ending_count=1, decision_points_per_path=1, desired_join_count=0, node_budget=5),
        )
    assert impossible.value.code == "topology.infeasible"


def test_planner_handles_large_bounded_brief_without_enumerating_graphs() -> None:
    brief = _brief(
        node_budget=128,
        ending_count=8,
        decision_points_per_path=6,
        desired_join_count=4,
        max_out_degree=4,
    )

    started = perf_counter()
    topology = plan_story_graph_topology(project_id="large-project", brief=brief)
    elapsed = perf_counter() - started

    assert len(topology.nodes) <= brief.node_budget
    assert len(topology.joins) == brief.desired_join_count
    # This guard is intentionally generous. The bounded state planner normally
    # completes this case in well under a second; the former edge-matrix
    # enumeration did not complete at all in the same interval.
    assert elapsed < 3.0


def test_binder_rejects_missing_unknown_and_topology_changes() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    fill = _complete_fill(topology)
    fill["nodes"].pop()

    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, fill, brief=brief)
    codes = {issue["code"] for issue in captured.value.issues}
    assert "binding.missing_id" in codes

    altered = _complete_fill(topology)
    altered["edges"][0]["sourceNodeId"] = "attempted-topology-change"
    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, altered, brief=brief)
    codes = {issue["code"] for issue in captured.value.issues}
    # Extra endpoint data is forbidden by the content-only Pydantic contract.
    assert any(code.startswith("schema.") for code in codes)

    duplicate = _complete_fill(topology)
    duplicate["nodes"].append(dict(duplicate["nodes"][0]))
    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, duplicate, brief=brief)
    assert "binding.duplicate_id" in {issue["code"] for issue in captured.value.issues}

    unknown = _complete_fill(topology)
    unknown["nodes"][0]["id"] = "unknown-node"
    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, unknown, brief=brief)
    assert {"binding.unknown_id", "binding.missing_id"} <= {
        issue["code"] for issue in captured.value.issues
    }

    invalid_choice = _complete_fill(topology)
    next(edge for edge in invalid_choice["edges"] if edge["choiceText"] is not None)["choiceText"] = None
    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, invalid_choice, brief=brief)
    assert any(issue["code"].startswith("semantic.") for issue in captured.value.issues)


def test_v2_edge_and_join_contract_violations_are_reportable_binding_issues() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    invalid = _complete_fill(topology)
    continuation_id = next(
        item.id for item in topology.edges if item.kind == StoryEdgeKind.CONTINUATION
    )
    continuation = next(
        edge for edge in invalid["edges"] if edge["id"] == continuation_id
    )
    continuation["choiceText"] = "不应出现的选择文案"
    invalid["joinContracts"][0]["requiredStateKeys"] = ["route", "route"]
    invalid["joinContracts"][0]["allowedDifferences"] = ["other"]

    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, invalid, brief=brief)

    issues = {issue["code"]: issue["path"] for issue in captured.value.issues}
    assert issues["semantic.continuation_choice_text_must_be_null"].startswith("edges.")
    assert issues["semantic.join_state_keys_must_be_unique"].startswith("joinContracts.")
    assert issues["semantic.join_allowed_differences_must_be_required"].startswith("joinContracts.")


def test_v2_choice_and_join_text_must_be_non_blank() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    invalid = _complete_fill(topology)
    choice_id = next(
        item.id for item in topology.edges if item.kind == StoryEdgeKind.CHOICE
    )
    next(edge for edge in invalid["edges"] if edge["id"] == choice_id)[
        "choiceText"
    ] = "   "
    invalid["joinContracts"][0]["requiredStateKeys"] = ["   "]

    with pytest.raises(StoryGraphContentBindingError) as captured:
        bind_story_graph_content_fill(topology, invalid, brief=brief)

    assert {issue["code"] for issue in captured.value.issues} >= {
        "semantic.choice_edge_choice_text_required",
        "semantic.join_state_key_must_be_non_blank",
    }


def test_different_project_id_changes_stable_ids_but_not_shape() -> None:
    brief = _brief()
    left = plan_story_graph_topology(project_id="project-a", brief=brief)
    right = plan_story_graph_topology(project_id="project-b", brief=brief)

    assert [node.kind for node in left.nodes] == [node.kind for node in right.nodes]
    assert left.topology_hash != right.topology_hash
    assert left.start_node_id != right.start_node_id


def test_topology_hash_covers_immutable_join_kinds() -> None:
    topology = plan_story_graph_topology(project_id="project-a", brief=_brief())
    tampered = topology.model_dump(mode="json", by_alias=True)
    join_id = topology.joins[0].join_node_id
    next(node for node in tampered["nodes"] if node["id"] == join_id)["kind"] = "scene"

    with pytest.raises(ValidationError, match="topologyHash"):
        type(topology).model_validate(tampered, by_alias=True)

    unsigned = {key: value for key, value in tampered.items() if key != "topologyHash"}
    tampered["topologyHash"] = hashlib.sha256(
        json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with pytest.raises(ValidationError, match="join node must have kind 'join'"):
        type(topology).model_validate(tampered, by_alias=True)


def test_work_unit_compiler_exposes_content_only_graph_schema() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    snapshot = {"brief": brief.model_dump(mode="json", by_alias=True)}
    plan = create_generation_plan(
        run_id="topology-unit",
        requested_stages=[StageName.STORY_GRAPH],
        provider_profile_hash="profile",
        canonical_snapshot=snapshot,
    )
    bible = StoryBibleV2(
        logline="列车失控。", premise="每条路线都要付出代价。", genre="", tone="", audience="",
        narrative_promise="", visual_language="", themes=[], world_rules=[], known_facts=[],
        open_questions=[], source_notes=[], characters=[], locations=[], props=[],
    )
    stage_plan = plan_stage(plan, stage=StageName.STORY_GRAPH, dependencies={StageName.STORY_BIBLE: bible})
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=stage_plan.work_units[0],
        dependencies={StageName.STORY_BIBLE: bible},
        brief=brief,
        canonical_snapshot=snapshot,
        story_graph_topology=topology,
    )

    assert compiled.contract.schema_id == "story_graph_content_fill.v2"
    assert compiled.response_schema["properties"]["nodes"]["minItems"] == len(
        topology.nodes
    )
    assert compiled.response_schema["properties"]["nodes"]["maxItems"] == len(
        topology.nodes
    )
    assert compiled.response_schema["properties"]["nodes"]["items"]["properties"][
        "id"
    ]["enum"] == [item.id for item in topology.nodes]
    assert compiled.response_schema["properties"]["edges"]["items"]["properties"][
        "id"
    ]["enum"] == [item.id for item in topology.edges]
    assert compiled.response_schema["properties"]["joinContracts"]["items"][
        "properties"
    ]["id"]["enum"] == [item.id for item in topology.joins]
    prompt = compiled.rendered.messages[1].content
    assert topology.topology_hash in prompt
    assert topology.planner_version in prompt
    assert "projectId" not in prompt
    assert "structuralParameters" not in prompt
    assert all(item.id in prompt for item in (*topology.nodes, *topology.edges, *topology.joins))
    assert "sourceNodeId" not in compiled.rendered.messages[1].content.split("【目标 JSON Schema】", 1)[1]
    edge_schema = compiled.response_schema["properties"]["edges"]["items"]
    conditions = edge_schema["allOf"]
    continuation_id = next(
        item.id for item in topology.edges if item.kind == StoryEdgeKind.CONTINUATION
    )
    choice_id = next(item.id for item in topology.edges if item.kind == StoryEdgeKind.CHOICE)
    by_id = {
        condition["if"]["properties"]["id"]["const"]: condition["then"]["properties"]["choiceText"]
        for condition in conditions
    }
    assert by_id[continuation_id] == {"const": None}
    assert by_id[choice_id] == {"type": "string", "minLength": 1}
    accepted = compiled.validator.validate(
        _complete_fill(topology), context=SemanticValidationContext(stage="story_graph")
    )
    assert accepted.accepted is True
    assert accepted.value.start_node_id == topology.start_node_id

    invalid = _complete_fill(topology)
    next(edge for edge in invalid["edges"] if edge["id"] == continuation_id)["choiceText"] = "错误选择"
    rejected = compiled.validator.validate(
        invalid, context=SemanticValidationContext(stage="story_graph")
    )
    assert rejected.accepted is False
    assert [issue.code for issue in rejected.issues] == [
        "semantic.continuation_choice_text_must_be_null"
    ]
