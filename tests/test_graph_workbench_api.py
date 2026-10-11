"""Current shared graph HTTP boundary and explicit recovery, without dispatch."""
import pytest
from fastapi.testclient import TestClient

from plotloom.api.project_folder import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.graph_authoring_drafts import GraphAuthoringDraft
from plotloom.persistence.project.graph_workbench import GraphDraftRebaseRequest
from plotloom.source_structures import planned_structure
from tests.graph_authoring_fixtures import authored_map, install_request
from tests.graph_draft_fixtures import (
    graph_draft_revision,
    graph_map_save_request,
    save_graph_mapping,
)
from tests.source_outline_fixtures import _storage


def test_http_preview_cancel_apply_stale_failure_and_reload(tmp_path):
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"node_budget": 12}))
    project_id = store.manifest.project_id
    client = TestClient(create_project_folder_authoring_app(storage))
    url = f"/api/v2/projects/{project_id}"
    try:
        initial = client.get(f"{url}/graph-workbench").json()
        payload = initial["initialPayload"]
        saved = client.put(f"{url}/authoring-drafts", json={"editorScope": "story_graph", "entityId": "root",
            "baseCanonicalRevision": initial["baseCanonicalRevision"], "expectedDraftRevision": 0, "payload": payload})
        assert saved.status_code == 200
        command = {"operation": "insert", "nodeId": "new-step", "kind": "scene", "rowHint": 1,
            "createPendingChoices": False,
            "edgeId": payload["mapping"]["topology"]["edges"][0]["id"], "continuationEdgeId": "new-output"}
        body = {"expectedDraftRevision": saved.json()["draftRevision"], "command": command}
        preview = client.post(f"{url}/graph-workbench/preview", json=body)
        assert preview.status_code == 200, preview.text
        assert client.get(f"{url}/graph-workbench").json()["draft"] == saved.json()
        tampered = client.post(f"{url}/graph-workbench/apply", json=body | {"previewHash": "0" * 64})
        assert tampered.status_code == 409
        applied = client.post(f"{url}/graph-workbench/apply", json=body | {"previewHash": preview.json()["previewHash"]})
        assert applied.status_code == 200
        assert applied.json()["payload"] == preview.json()["result"]
        assert client.post(f"{url}/graph-workbench/apply", json=body | {"previewHash": preview.json()["previewHash"]}).status_code == 409
        assert client.get(f"{url}/graph-workbench").json()["draft"] == applied.json()
        assert store.authoring.get_stage_head(project_id, StageName.STORY_GRAPH).revision == 0
    finally:
        store.close()


def test_explicit_recovery_after_consumption_requires_current_trusted_seed(source_project):
    store = source_project
    mapping = authored_map(store)
    old = save_graph_mapping(store, mapping)
    saved = store.save_section_map(graph_map_save_request(store, mapping=mapping,
        expected_section_map_revision=0, expected_source_revision=1, expected_outline_revision=1,
        expected_outline_content_hash=store.source_outline_state().accepted_outline.content_hash))
    store.install_section_map_graph(install_request(saved, graph_draft_revision(store)))
    state = store.graph_workbench_state()
    assert state.draft is None and state.base_canonical_revision == 1
    assert state.initial_payload.selected_node_id == mapping.topology.start_node_id
    assert state.initial_payload.selected_node_id in {node.id for node in state.initial_payload.mapping.topology.nodes}
    payload = GraphAuthoringDraft.model_validate(old.payload)
    payload.mapping.sections[0].summary = "Retained unsent prose from the previous base"
    receipt = store.rebase_graph_draft(GraphDraftRebaseRequest(expected_draft_revision=0,
        expected_binding_hash=state.binding_hash, payload=payload))
    assert receipt.base_canonical_revision == 1
    assert receipt.payload["mapping"]["sections"][0]["summary"] == payload.mapping.sections[0].summary
    assert receipt.payload["mapping"]["topologyOrigin"] == "author"
    assert store.source_outline_state().accepted_section_map.mapping == mapping
    assert store.source_outline_state().graph_admission.graph_revision == 1


def test_explicit_recovery_does_not_forge_an_unaccepted_original_seed(source_project):
    store = source_project
    payload = store.graph_workbench_state().initial_payload
    payload.mapping.seed_topology = planned_structure("other-project", store.project().brief)
    with pytest.raises(InvalidTransitionError, match="种子"):
        store.rebase_graph_draft(GraphDraftRebaseRequest(expected_draft_revision=0,
            expected_binding_hash=store.graph_workbench_state().binding_hash, payload=payload))
    assert store.graph_workbench_state().draft is None


def test_absent_root_recovery_validates_author_edits_against_trusted_baseline(source_project):
    store = source_project
    state = store.graph_workbench_state()
    payload = state.initial_payload.model_copy(deep=True)
    edge = payload.mapping.topology.edges[0]
    edge.target_node_id = edge.source_node_id
    payload.mapping.topology_origin = "author"
    with pytest.raises(InvalidTransitionError, match="结构修改"):
        store.rebase_graph_draft(GraphDraftRebaseRequest(expected_draft_revision=0,
            expected_binding_hash=state.binding_hash, payload=payload))
    assert store.graph_workbench_state().draft is None
