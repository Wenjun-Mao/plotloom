"""G0 current author graph, incomplete draft and explicit footage boundaries."""

import pytest
from tests.graph_draft_fixtures import graph_map_save_request, graph_draft_revision

from pydantic import ValidationError

from plotloom.canonical_schema import StoryBibleV2, StoryGraphV2
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from plotloom.graph_authoring_drafts import GraphAuthoringDraft
from plotloom.generation.scene_timing_allocation import plan_scene_timing_allocation
from plotloom.source_outline_contracts import (
    OutlineAcceptRequest, SectionMap, SectionMapGraphInstallRequest,
    SectionMapSaveRequest, compile_section_map_graph, validate_section_map_graph,
)
from plotloom.source_structures import complete_routes, planned_structure
from plotloom.validation import DomainValidationError
from tests.backend_core.conftest import make_story_bible
from tests.test_project_storage_source_outline import _storage, _material, _request, _deliver


@pytest.fixture
def source_project(tmp_path):
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={
        "node_budget": 12, "decision_points_per_path": 1, "ending_count": 1,
        "max_out_degree": 3, "desired_join_count": 1,
    }))
    try:
        material = _material()
        store.save_source_material(expected_source_revision=0, material=material)
        request = _request(store.manifest.project_id, material, brief=store.project().brief)
        store.prepare_outline_candidate(request)
        store.admit_outline_delivery(_deliver(store, request))
        store.accept_outline_candidate(OutlineAcceptRequest(
            job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0,
        ))
        yield store
    finally:
        store.close()


def authored_map(store):
    node_kinds = [("opening", "start"), ("choose", "decision"),
        ("branch-123", "scene"), ("branch-222", "scene"), ("branch-333", "scene"),
        ("inserted-step", "scene"), ("merge", "join"), ("ending", "ending")]
    connections = [("opening-choice", "opening", "choose", "continuation"),
        ("option-123", "choose", "branch-123", "choice"),
        ("option-222", "choose", "branch-222", "choice"),
        ("option-333", "choose", "branch-333", "choice"),
        ("branch-input", "branch-123", "inserted-step", "continuation"),
        ("new-continuation", "inserted-step", "merge", "continuation"),
        ("second-input", "branch-222", "merge", "continuation"),
        ("third-input", "branch-333", "merge", "continuation"),
        ("merge-ending", "merge", "ending", "continuation")]
    return SectionMap.model_validate({
        "seedTopology": planned_structure(store.manifest.project_id, store.project().brief),
        "topologyOrigin": "author",
        "topology": {"startNodeId": "opening", "nodes": [{"id": key, "kind": kind} for key, kind in node_kinds],
            "edges": [{"id": key, "sourceNodeId": source, "targetNodeId": target, "kind": kind,
                "stateEffects": {"retainedFact": "original traversal"} if key == "branch-input" else {},
                "entityStateEffects": []} for key, source, target, kind in connections],
            "joins": [{"id": "join-contract", "joinNodeId": "merge", "incomingNodeIds": ["inserted-step", "branch-222", "branch-333"], "requiredStateKeys": [], "allowedDifferences": [], "notes": "Authored reconciliation."}]},
        "sections": [{"sectionId": key, "title": key, "summary": f"Reviewed story at {key}.",
            "ending": kind == "ending", "footageMode": "route_only" if kind in {"decision", "join"} else "footage"} for key, kind in node_kinds],
        "choices": [{"choiceId": "choose", "sectionId": "choose", "prompt": "Which action?",
            "outcomes": [{"outcomeId": f"option-{number}", "label": str(number), "consequence": f"Action {number}.", "endingSectionId": f"branch-{number}"} for number in [123, 222, 333]]}],
        "joinReconciliations": {"join-contract": "The three actions reconnect at the shared ending."},
    })


def save(store, mapping):
    state = store.source_outline_state()
    return store.save_section_map(graph_map_save_request(store,
        expected_source_revision=state.source.revision,
        expected_outline_revision=state.accepted_outline.revision,
        expected_outline_content_hash=state.accepted_outline.content_hash,
        expected_section_map_revision=state.accepted_section_map.revision if state.accepted_section_map else 0,
        mapping=mapping,
    ))


def install_request(state, draft_revision):
    return SectionMapGraphInstallRequest(
        expected_source_revision=state.source.revision, expected_source_content_hash=state.source.content_hash,
        expected_outline_revision=state.accepted_outline.revision, expected_outline_content_hash=state.accepted_outline.content_hash,
        expected_section_map_revision=state.accepted_section_map.revision,
        expected_section_map_content_hash=state.accepted_section_map.content_hash,
        expected_graph_revision=state.graph_admission.graph_revision if state.graph_admission else 0,
        expected_graph_draft_revision=draft_revision,
    )


def test_author_topology_round_trip_preserves_seed_ids_effects_and_full_routes(source_project):
    store = source_project
    mapping = authored_map(store)
    graph = compile_section_map_graph(mapping)
    validate_section_map_graph(graph, store.project().brief)
    saved = save(store, mapping)
    installed = store.install_section_map_graph(install_request(saved, graph_draft_revision(store)))
    assert installed.graph_admission.status == "current"
    assert store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORY_GRAPH) == graph
    assert installed.accepted_section_map.mapping.seed_topology == mapping.seed_topology
    assert installed.accepted_section_map.mapping.topology_origin == "author"
    assert next(edge for edge in graph.edges if edge.id == "branch-input").state_effects == {"retainedFact": "original traversal"}
    assert len(complete_routes(graph)) == 3
    assert all("choose" in route and "merge" in route for route in complete_routes(graph))
    allocation = plan_scene_timing_allocation(graph=graph, brief=store.project().brief)
    assert allocation.node_duration_budget("choose") == allocation.node_duration_budget("merge") == 0
    assert all(sum(allocation.node_duration_budget(node) for node in route) <= store.project().brief.target_playthrough_seconds * 1000 for route in complete_routes(graph))
    assert all(item.duration_budget_units > 0 for item in allocation.node_allocations if item.footage_mode == "footage")


def test_unfinished_current_draft_round_trips_but_cannot_be_admitted(source_project):
    store = source_project
    data = authored_map(store).model_dump(mode="json", by_alias=True)
    data["sections"][0]["summary"] = ""
    data["topology"]["edges"][1]["targetNodeId"] = None
    data["choices"][0]["outcomes"][0]["endingSectionId"] = None
    draft = GraphAuthoringDraft(binding_hash=store.graph_workbench_state().binding_hash, detached_endpoints={}, field_buffers={}, mapping=data, row_hints={"branch-123": 2}, selected_node_id="branch-123")
    saved = store.save_authoring_draft(editor_scope="story_graph", entity_id="root",
        base_canonical_revision=0, expected_draft_revision=0, payload=draft.model_dump(mode="json", by_alias=True))
    assert store.authoring_drafts()[0].payload == saved.payload
    with pytest.raises(ValidationError):
        draft.admitted_mapping()
    assert store.authoring.get_stage_head(store.manifest.project_id, StageName.STORY_GRAPH).revision == 0


def test_admission_consumes_only_exact_current_graph_draft_and_cas(source_project):
    store = source_project
    mapping = authored_map(store)
    draft = GraphAuthoringDraft(binding_hash=store.graph_workbench_state().binding_hash, detached_endpoints={}, field_buffers={}, mapping=mapping.model_dump(mode="json", by_alias=True), row_hints={}, selected_node_id="branch-333")
    receipt = store.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=0,
        expected_draft_revision=0, payload=draft.model_dump(mode="json", by_alias=True))
    saved = save(store, mapping)
    with pytest.raises(RevisionConflictError):
        store.install_section_map_graph(install_request(saved, receipt.draft_revision))
    current_revision = graph_draft_revision(store)
    assert current_revision > receipt.draft_revision
    store.install_section_map_graph(install_request(saved, current_revision))
    assert store.authoring_drafts() == []
    with pytest.raises(RevisionConflictError):
        store.install_section_map_graph(install_request(saved, receipt.draft_revision))


def test_required_mode_missing_fields_and_false_planner_provenance_are_rejected(source_project):
    data = authored_map(source_project).model_dump(mode="json", by_alias=True)
    data["topologyOrigin"] = "planner"
    with pytest.raises(ValidationError, match="author provenance"):
        SectionMap.model_validate(data)
    graph = compile_section_map_graph(authored_map(source_project)).model_dump(mode="json", by_alias=True)
    graph["nodes"][0].pop("footageMode")
    with pytest.raises(ValidationError, match="footageMode"):
        StoryGraphV2.model_validate(graph)


def test_footage_edit_requires_author_provenance_and_retains_frozen_seed(source_project):
    from plotloom.branch_suggestions import BranchSuggestion, bind_branches
    from tests.test_creator_branch_suggestions import proposal

    store = source_project
    seed = planned_structure(store.manifest.project_id, store.project().brief).model_dump(mode="json", by_alias=True)
    mapping = bind_branches(BranchSuggestion.model_validate(proposal(seed)), seed)
    data = mapping.model_dump(mode="json", by_alias=True)
    control = next(section for section in data["sections"] if section["footageMode"] == "route_only")
    control["footageMode"] = "footage"
    with pytest.raises(ValidationError, match="author provenance"):
        SectionMap.model_validate(data)
    assert store.source_outline_state().accepted_section_map is None
    data["topologyOrigin"] = "author"
    saved = save(store, SectionMap.model_validate(data))
    installed = store.install_section_map_graph(install_request(saved, graph_draft_revision(store)))
    assert installed.accepted_section_map.mapping.seed_topology.model_dump(mode="json", by_alias=True) == seed
    graph = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORY_GRAPH)
    assert next(node for node in graph.nodes if node.id == control["sectionId"]).footage_mode == "footage"


def test_graph_draft_has_only_the_exact_root_admission_identity(source_project):
    from types import SimpleNamespace
    from plotloom.persistence.project.drafts import ProjectDraftPersistence

    store = source_project
    draft = GraphAuthoringDraft(binding_hash=store.graph_workbench_state().binding_hash, detached_endpoints={}, field_buffers={}, mapping=authored_map(store).model_dump(mode="json", by_alias=True),
        row_hints={}, selected_node_id=None)
    with pytest.raises(ValueError, match="root identity"):
        store.save_authoring_draft(editor_scope="story_graph", entity_id="another-graph",
            base_canonical_revision=0, expected_draft_revision=0,
            payload=draft.model_dump(mode="json", by_alias=True))
    assert store.authoring_drafts() == []
    with pytest.raises(ValueError, match="root identity"):
        ProjectDraftPersistence._authoring_draft(SimpleNamespace(editor_scope="story_graph", entity_id="another-graph"))


def test_state_admission_preserves_effects_and_requires_truthful_control_footage(source_project):
    graph = compile_section_map_graph(authored_map(source_project)).model_dump(mode="json", by_alias=True)
    bible = make_story_bible().model_dump(mode="json", by_alias=True)
    bible["characters"] = [{"id": "lin", "name": "Lin", "description": "Pilot",
        "visualAnchors": [], "soundAnchors": [], "allowedStates": ["calm"],
        "continuityRules": [], "role": None, "goal": "Return", "traits": [], "voiceAnchors": []}]
    bible = StoryBibleV2.model_validate(bible)
    effect = {"entityType": "character", "entityId": "lin", "state": "calm"}
    next(edge for edge in graph["edges"] if edge["id"] == "option-123")["entityStateEffects"] = [effect]
    validate_section_map_graph(StoryGraphV2.model_validate(graph), source_project.project().brief, bible)
    next(edge for edge in graph["edges"] if edge["id"] == "opening-choice")["entityStateEffects"] = [effect]
    with pytest.raises(DomainValidationError) as rejected:
        validate_section_map_graph(StoryGraphV2.model_validate(graph), source_project.project().brief, bible)
    assert {issue["code"] for issue in rejected.value.issues} == {"route_only_entity_entry_required"}
    next(node for node in graph["nodes"] if node["id"] == "choose")["footageMode"] = "footage"
    validate_section_map_graph(StoryGraphV2.model_validate(graph), source_project.project().brief, bible)
    graph["joinContracts"][0]["requiredStateKeys"] = ["arrival"]
    for edge in graph["edges"]:
        if edge["targetNodeId"] == "merge":
            edge["stateEffects"]["arrival"] = "resolved"
    with pytest.raises(DomainValidationError) as rejected:
        validate_section_map_graph(StoryGraphV2.model_validate(graph), source_project.project().brief, bible)
    assert {issue["code"] for issue in rejected.value.issues} == {"route_only_join_scene_required"}
    next(node for node in graph["nodes"] if node["id"] == "merge")["footageMode"] = "footage"
    admitted = StoryGraphV2.model_validate(graph)
    validate_section_map_graph(admitted, source_project.project().brief, bible)
    assert next(edge for edge in admitted.edges if edge.id == "opening-choice").entity_state_effects[0].state == "calm"

def test_generic_graph_stage_write_is_retired(source_project):
    graph = compile_section_map_graph(authored_map(source_project))
    with pytest.raises(InvalidTransitionError, match="共享图工作台"):
        source_project.update_stage(StageName.STORY_GRAPH, graph, expected_revision=0)
