from __future__ import annotations

import hashlib
import json
from time import perf_counter

import pytest
from pydantic import ValidationError

from plotloom.domain import ProjectBrief, StageName, StoryBibleV2, StoryEdgeKind, StoryNodeKind
from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.story_graph_topology import (
    StoryGraphContentBindingError,
    StoryGraphTopologyError,
    bind_story_graph_content_fill,
    plan_story_graph_topology,
)
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    DialogueTimingRepairFact,
    EdgeStateEffectJsonRepairFact,
    JoinAllowedDifferencesRepairFact,
    JoinStateEffectRepairFact,
    RequiredEntityStateRepairFact,
    StoryGraphContentFillValidationAdapter,
    assert_join_state_effect_repair_fact_matches_source,
    assert_semantic_repair_fact_matches_issue,
    compile_work_unit_request,
    parse_semantic_repair_fact,
    semantic_repair_facts,
    story_graph_join_repair_facts,
)
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
    join_pairs = {
        (source_id, join.join_node_id)
        for join in topology.joins
        for source_id in join.incoming_node_ids
    }
    return {
        "nodes": [
            {"id": item.id, "title": f"节点 {index}", "summary": f"推进剧情 {index}"}
            for index, item in enumerate(topology.nodes, start=1)
        ],
        "edges": [
            {
                "id": item.id,
                "choiceText": "继续前进" if item.kind == StoryEdgeKind.CHOICE else None,
                "stateEffects": (
                    {"route": item.id}
                    if item.kind == StoryEdgeKind.CHOICE
                    or (item.source_node_id, item.target_node_id) in join_pairs
                    else {}
                ),
                "entityStateEffects": [],
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


def test_current_join_missing_fact_is_bound_to_frozen_direct_edges() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    fill = _complete_fill(topology)
    join = topology.joins[0]
    target_edges = sorted(
        (
            edge
            for edge in topology.edges
            if edge.target_node_id == join.join_node_id
        ),
        key=lambda edge: (edge.id, edge.source_node_id),
    )
    next(edge for edge in fill["edges"] if edge["id"] == target_edges[0].id)["stateEffects"] = {}
    report = StoryGraphContentFillValidationAdapter(
        topology=topology,
        brief=brief,
    ).validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert report.accepted is False
    issues = report.issues
    facts = semantic_repair_facts(
        fill,
        issues,
        stage=StageName.STORY_GRAPH,
        story_graph_topology=topology,
    )
    missing = next(fact for fact in facts if fact.code == "semantic.join_state_effect_missing")
    assert missing.path == ("edges", target_edges[0].id, "stateEffects", "route")
    assert [edge.edge_id for edge in missing.incoming_edges] == [
        edge.id for edge in target_edges
    ]
    assert missing.mode == "variant"
    assert missing.has_expected_value is False


def test_join_repair_fact_preserves_only_valid_sibling_assignments_and_rebinds_source() -> None:
    """A convergent repair cannot delete a valid variant sibling from its source."""

    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    fill = _complete_fill(topology)
    join = topology.joins[0]
    incoming = sorted(
        (
            edge
            for edge in topology.edges
            if edge.target_node_id == join.join_node_id
            and edge.source_node_id in join.incoming_node_ids
        ),
        key=lambda edge: (edge.id, edge.source_node_id),
    )
    fill["joinContracts"][0]["requiredStateKeys"] = ["route", "variant"]
    fill["joinContracts"][0]["allowedDifferences"] = ["variant"]
    edges = {edge["id"]: edge for edge in fill["edges"]}
    for position, edge in enumerate(incoming, start=1):
        edges[edge.id]["stateEffects"] = {
            "route": f"conflict-{position}",
            "variant": None if position == 1 else {"branch": position},
        }

    report = StoryGraphContentFillValidationAdapter(
        topology=topology, brief=brief
    ).validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert [issue.code for issue in report.issues] == [
        "semantic.join_state_effect_conflict"
    ]
    facts = semantic_repair_facts(
        fill,
        report.issues,
        stage=StageName.STORY_GRAPH,
        story_graph_topology=topology,
    )
    assert len(facts) == 1
    fact = facts[0]
    assert isinstance(fact, JoinStateEffectRepairFact)
    assert fact.state_key == "route"
    assert [effect.model_dump(mode="json", by_alias=True) for effect in fact.preserved_state_effects] == [
        {
            "stateKey": "variant",
            "incomingEffects": [
                {"edgeId": incoming[0].id, "expectedValue": None},
                {"edgeId": incoming[1].id, "expectedValue": {"branch": 2}},
            ],
        },
    ]
    assert_join_state_effect_repair_fact_matches_source(
        fact, fill, issues=report.issues, topology=topology
    )

    tampered = json.loads(json.dumps(fill))
    tampered_edges = {edge["id"]: edge for edge in tampered["edges"]}
    tampered_edges[incoming[1].id]["stateEffects"]["variant"] = {"branch": "foreign"}
    with pytest.raises(ValueError, match="does not match the rejected response"):
        assert_join_state_effect_repair_fact_matches_source(
            fact, tampered, issues=report.issues, topology=topology
        )


def test_join_repair_facts_do_not_preserve_multiple_keys_that_need_repair() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    fill = _complete_fill(topology)
    join = topology.joins[0]
    fill["joinContracts"][0]["requiredStateKeys"] = ["route", "variant"]
    fill["joinContracts"][0]["allowedDifferences"] = ["variant"]
    for edge in fill["edges"]:
        if any(edge["id"] == candidate.id for candidate in topology.edges if candidate.target_node_id == join.join_node_id):
            edge["stateEffects"] = {}

    report = StoryGraphContentFillValidationAdapter(
        topology=topology, brief=brief
    ).validate(fill, context=SemanticValidationContext(stage="story_graph"))
    facts = semantic_repair_facts(
        fill,
        report.issues,
        stage=StageName.STORY_GRAPH,
        story_graph_topology=topology,
    )
    join_facts = [fact for fact in facts if isinstance(fact, JoinStateEffectRepairFact)]
    assert {fact.state_key for fact in join_facts} == {"route", "variant"}
    assert all(fact.preserved_state_effects == () for fact in join_facts)


def test_subset_join_diagnostics_include_existing_conflicts_but_not_promoted_missing_keys() -> None:
    """An allowed-only key must not hide an independent convergent conflict."""

    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    fill = _complete_fill(topology)
    join = topology.joins[0]
    incoming = sorted(
        (
            edge
            for edge in topology.edges
            if edge.target_node_id == join.join_node_id
            and edge.source_node_id in join.incoming_node_ids
        ),
        key=lambda edge: (edge.id, edge.source_node_id),
    )
    fill["joinContracts"][0]["requiredStateKeys"] = ["route"]
    fill["joinContracts"][0]["allowedDifferences"] = ["variant"]
    for position, edge in enumerate(incoming, start=1):
        next(item for item in fill["edges"] if item["id"] == edge.id)["stateEffects"] = {
            "route": f"conflict-{position}",
        }

    report = StoryGraphContentFillValidationAdapter(
        topology=topology,
        brief=brief,
    ).validate(fill, context=SemanticValidationContext(stage="story_graph"))

    assert report.accepted is False
    assert [issue.code for issue in report.issues] == [
        "semantic.join_allowed_differences_must_be_required",
        "semantic.join_state_effect_conflict",
    ]
    facts = semantic_repair_facts(
        fill,
        report.issues,
        stage=StageName.STORY_GRAPH,
        story_graph_topology=topology,
    )
    assert [fact.code for fact in facts] == [
        "semantic.join_allowed_differences_must_be_required",
        "semantic.join_state_effect_conflict",
    ]
    conflict = facts[1]
    assert conflict.path == (
        "joinContracts", join.id, "requiredStateKeys", "route"
    )
    assert conflict.has_expected_value is False


def test_non_join_nonfinite_state_effect_gets_a_topology_bound_repair_fact() -> None:
    """Finite JSON is graph-wide, so ordinary choices must be repairable too."""

    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    fill = _complete_fill(topology)
    join_targets = {
        edge.id
        for join in topology.joins
        for edge in topology.edges
        if edge.target_node_id == join.join_node_id
    }
    target = next(edge for edge in topology.edges if edge.id not in join_targets)
    fill_edge = next(edge for edge in fill["edges"] if edge["id"] == target.id)
    fill_edge["stateEffects"] = {"ordinary": float("nan")}

    report = StoryGraphContentFillValidationAdapter(
        topology=topology,
        brief=brief,
    ).validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert any(issue.code == "semantic.state_effect_not_json" for issue in report.issues)

    facts = semantic_repair_facts(
        fill,
        report.issues,
        stage=StageName.STORY_GRAPH,
        story_graph_topology=topology,
    )
    fact = next(fact for fact in facts if fact.code == "semantic.state_effect_not_json")
    assert isinstance(fact, EdgeStateEffectJsonRepairFact)
    assert fact.path == ("edges", target.id, "stateEffects", "ordinary")
    assert (fact.edge_id, fact.source_node_id, fact.target_node_id) == (
        target.id,
        target.source_node_id,
        target.target_node_id,
    )
    assert fact.repair_action == "replace_with_finite_json"


def test_typed_graph_entity_state_effects_require_exact_frozen_bible_membership() -> None:
    brief = _brief()
    topology = plan_story_graph_topology(project_id="project-a", brief=brief)
    bible = StoryBibleV2(
        logline="站台等待。", premise="选择改变站台状态。", genre="", tone="", audience="",
        narrative_promise="", visual_language="", themes=[], world_rules=[], known_facts=[],
        open_questions=[], source_notes=[], characters=[], props=[],
        locations=[{
            "id": "loc_station", "name": "站台", "description": "空站台。",
            "visualAnchors": [], "soundAnchors": [],
            "allowedStates": ["空无一人", "林澈在场", "站务员在场（未定）"],
            "continuityRules": [],
        }],
    )
    fill = _complete_fill(topology)
    edge = fill["edges"][0]
    edge["entityStateEffects"] = [{
        "entityType": "location", "entityId": "loc_station", "state": "站务员在场",
    }]
    adapter = StoryGraphContentFillValidationAdapter(
        topology=topology, brief=brief, bible=bible
    )
    rejected = adapter.validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert ("semantic.invalid_entity_state_effect", ("edges", edge["id"], "entityStateEffects", "0", "state")) in {
        (issue.code, tuple(str(part) for part in issue.path)) for issue in rejected.issues
    }

    edge["entityStateEffects"][0]["state"] = "站务员在场（未定）"
    accepted = adapter.validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert accepted.accepted is True

    edge["entityStateEffects"][0]["entityId"] = "missing_station"
    unknown = adapter.validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert any(issue.code == "semantic.unknown_entity_state_effect_entity" for issue in unknown.issues)
    edge["entityStateEffects"][0]["entityId"] = "loc_station"
    edge["entityStateEffects"][0]["entityType"] = "character"
    wrong_type = adapter.validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert any(issue.code == "semantic.unknown_entity_state_effect_entity" for issue in wrong_type.issues)
    edge["entityStateEffects"] = []
    edge["stateEffects"] = {"loc_station_state": "free-form story fact"}
    assert adapter.validate(fill, context=SemanticValidationContext(stage="story_graph")).accepted is True

    edge["entityStateEffects"] = [
        {"entityType": "location", "entityId": "loc_station", "state": "空无一人"},
        {"entityType": "location", "entityId": "loc_station", "state": "林澈在场"},
    ]
    duplicate = adapter.validate(fill, context=SemanticValidationContext(stage="story_graph"))
    assert any(issue.code == "semantic.value_error" or issue.code == "semantic.duplicate_entity_state_effect" for issue in duplicate.issues)


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

    assert compiled.contract.schema_id == "story_graph_content_fill.v4"
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

    invalid_join = _complete_fill(topology)
    invalid_join["joinContracts"][0]["requiredStateKeys"] = ["route"]
    invalid_join["joinContracts"][0]["allowedDifferences"] = ["other"]
    join_report = compiled.validator.validate(
        invalid_join,
        context=SemanticValidationContext(stage="story_graph"),
    )
    facts = story_graph_join_repair_facts(invalid_join, join_report.issues)
    assert join_report.accepted is False
    assert len(facts) == 1
    assert facts[0].model_dump(mode="json", by_alias=True) == {
        "code": "semantic.join_allowed_differences_must_be_required",
        "path": [
            "joinContracts",
            topology.joins[0].id,
            "allowedDifferences",
        ],
        "joinContractId": topology.joins[0].id,
        "missingRequiredStateKeys": ["other"],
        "expectedRequiredStateKeys": ["route", "other"],
        "expectedAllowedDifferences": ["other"],
    }

    for unsafe_allowed in (["   "], ["other", "other"]):
        unsafe = _complete_fill(topology)
        unsafe["joinContracts"][0]["requiredStateKeys"] = ["route"]
        unsafe["joinContracts"][0]["allowedDifferences"] = unsafe_allowed
        unsafe_report = compiled.validator.validate(
            unsafe,
            context=SemanticValidationContext(stage="story_graph"),
        )
        assert unsafe_report.accepted is False
        assert story_graph_join_repair_facts(unsafe, unsafe_report.issues) == ()

    assert story_graph_join_repair_facts(
        {"joinContracts": []}, join_report.issues
    ) == ()
    assert story_graph_join_repair_facts(
        invalid_join,
        (
            ValidationIssue(
                code="semantic.some_other_issue",
                message="ignored",
                path=("joinContracts", topology.joins[0].id),
            ),
        ),
    ) == ()


def test_semantic_repair_fact_union_revalidates_current_and_legacy_evidence() -> None:
    join = parse_semantic_repair_fact(
        {
            "code": "semantic.join_allowed_differences_must_be_required",
            "path": ["joinContracts", "join-1", "allowedDifferences"],
            "joinContractId": "join-1",
            "missingRequiredStateKeys": ["route"],
        }
    )
    assert isinstance(join, JoinAllowedDifferencesRepairFact)
    assert_semantic_repair_fact_matches_issue(
        join,
        (
            ValidationIssue(
                code="semantic.join_allowed_differences_must_be_required",
                message="safe message is not correction authority",
                path=("joinContracts", "join-1", "allowedDifferences"),
            ),
        ),
    )

    timing = parse_semantic_repair_fact(
        {
            "code": "semantic.cue_duration_underestimated",
            "path": ["dialogueCues", 0, "estimatedDurationUnits"],
            "timingProfileVersion": "dialogue.default.v1",
            "matchedRuleLanguage": "zh-CN",
            "delivery": "natural",
            "textCharacterCount": 2,
            "unitsPerCharacter": 330,
            "minimumDurationUnits": 660,
            "currentEstimatedDurationUnits": 1,
            "sceneDurationBudgetUnits": 600,
            "sceneCueEstimatedTotalUnits": 1,
            "sceneCueMinimumTotalUnits": 660,
            "minimumFitsSceneBudget": False,
        }
    )
    assert isinstance(timing, DialogueTimingRepairFact)

    entity_state = parse_semantic_repair_fact(
        {
            "code": "semantic.invalid_required_entity_state",
            "path": ["shots", 0, "requiredEntityStates", 1, "state"],
            "entityType": "character",
            "entityId": "speaker",
            "allowedStates": ["awake", "injured"],
        }
    )
    assert isinstance(entity_state, RequiredEntityStateRepairFact)

    with pytest.raises(ValidationError):
        parse_semantic_repair_fact(
            {
                "code": "semantic.join_allowed_differences_must_be_required",
                "path": ["joinContracts", "join-1", "allowedDifferences"],
                "joinContractId": "join-1",
                "missingRequiredStateKeys": ["route", "route"],
            }
        )
    with pytest.raises(ValidationError, match="path must identify"):
        parse_semantic_repair_fact(
            {
                "code": "semantic.join_allowed_differences_must_be_required",
                "path": ["bogus", 0],
                "joinContractId": "join-1",
                "missingRequiredStateKeys": ["route"],
            }
        )
    with pytest.raises(ValidationError, match="path must identify"):
        parse_semantic_repair_fact(
            {
                "code": "semantic.invalid_required_entity_state",
                "path": ["shots", 0, "requiredEntityStates", 1, "entityId"],
                "entityType": "character",
                "entityId": "speaker",
                "allowedStates": ["awake"],
            }
        )
    with pytest.raises(ValidationError, match="allowedStates must be unique"):
        parse_semantic_repair_fact(
            {
                "code": "semantic.invalid_required_entity_state",
                "path": ["shots", 0, "requiredEntityStates", 1, "state"],
                "entityType": "character",
                "entityId": "speaker",
                "allowedStates": ["awake", "awake"],
            }
        )
    with pytest.raises(ValueError, match="no matching stable validation issue"):
        assert_semantic_repair_fact_matches_issue(
            join,
            (
                ValidationIssue(
                    code="semantic.join_allowed_differences_must_be_required",
                    message="different join",
                    path=("joinContracts", "join-2", "allowedDifferences"),
                ),
            ),
        )
    with pytest.raises(ValidationError):
        parse_semantic_repair_fact({"code": "semantic.unknown"})
