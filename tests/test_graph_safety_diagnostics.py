"""Public diagnostics project the same checked facts and never relax admission."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.errors import register_api_error_handlers
from plotloom.api.project_folder import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.graph_authoring_drafts import GraphAuthoringDraft
from plotloom.graph_edit_safety import assert_edit_safe, structural_violations
from plotloom.graph_safety_diagnostics import GraphEditSafetyError
from tests.graph_authoring_fixtures import authored_map
from tests.graph_draft_fixtures import save_graph_mapping
from tests.source_outline_fixtures import _storage


@pytest.mark.parametrize("kind,maximum,actual,limit", [
    ("decision", 6, 7, 6), ("decision", 8, 7, 6), ("decision", 3, 4, 3),
    ("scene", 6, 2, 1), ("ending", 6, 1, 0),
])
def test_degree_facts_use_actual_enforced_limit(source_project, kind, maximum, actual, limit):
    draft = GraphAuthoringDraft.model_validate(save_graph_mapping(source_project, authored_map(source_project)).payload)
    draft.mapping.topology.nodes[1].kind = kind
    edge = draft.mapping.topology.edges[1].model_copy(deep=True)
    edge.target_node_id = None
    edge.kind = "choice" if kind == "decision" else "continuation"
    draft.mapping.topology.edges = []
    after = draft.model_copy(deep=True)
    after.mapping.topology.edges = [edge.model_copy(update={"id": f"edge-{index}"}) for index in range(actual)]
    brief = source_project.project().brief.model_copy(update={"max_out_degree": maximum})
    with pytest.raises(GraphEditSafetyError) as caught:
        assert_edit_safe(draft, after, brief)
    item = next(item for item in caught.value.diagnostics if item["code"] == "out_degree")
    assert item["facts"] == {"nodeId": "choose", "nodeKind": kind, "actual": actual, "limit": limit}
    assert item["severity"] == actual - limit
    assert item["previousSeverity"] == 0


def test_existing_violation_may_remain_but_worsening_reports_measured_facts(source_project):
    draft = GraphAuthoringDraft.model_validate(save_graph_mapping(source_project, authored_map(source_project)).payload)
    brief = source_project.project().brief.model_copy(update={"max_out_degree": 2, "node_budget": 7})
    assert_edit_safe(draft, draft.model_copy(deep=True), brief)
    after = draft.model_copy(deep=True)
    after.mapping.topology.edges.append(after.mapping.topology.edges[1].model_copy(update={"id": "extra", "target_node_id": None}))
    with pytest.raises(GraphEditSafetyError) as caught:
        assert_edit_safe(draft, after, brief)
    assert caught.value.diagnostics == [{"code": "out_degree", "identity": "out_degree:choose", "severity": 2,
        "facts": {"nodeId": "choose", "nodeKind": "decision", "actual": 4, "limit": 2}, "previousSeverity": 1}]
    assert structural_violations(draft, brief)["node_capacity"] == 1


def test_capacity_and_related_checked_facts(source_project):
    draft = GraphAuthoringDraft.model_validate(save_graph_mapping(source_project, authored_map(source_project)).payload)
    after = draft.model_copy(deep=True)
    after.mapping.topology.nodes.append(after.mapping.topology.nodes[2].model_copy(update={"id": "extra"}))
    after.mapping.topology.edges[1].target_node_id = "opening"
    after.mapping.topology.edges[1].kind = "continuation"
    after.mapping.topology.edges[4].target_node_id = "branch-123"
    with pytest.raises(GraphEditSafetyError) as caught:
        assert_edit_safe(draft, after, source_project.project().brief.model_copy(update={"node_budget": 8}))
    items = {item["code"]: item["facts"] for item in caught.value.diagnostics}
    assert items["node_capacity"] == {"actual": 9, "limit": 8}
    assert items["edge_kind"]["requiredKind"] == "choice"
    assert items["edge_kind"]["actualKind"] == "continuation"
    assert items["start_input"] == {"edgeId": "option-123", "nodeId": "opening"}
    assert items["self_link"] == {"edgeId": "branch-input", "nodeId": "branch-123"}
    assert "cycle" in items


def test_http_safety_refusal_keeps_draft_and_all_stage_heads(tmp_path):
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"node_budget": 30, "max_out_degree": 6}))
    project_id = store.manifest.project_id
    client = TestClient(create_project_folder_authoring_app(storage))
    url = f"/api/v2/projects/{project_id}"
    try:
        payload = store.graph_workbench_state().initial_payload
        decision = next(node for node in payload.mapping.topology.nodes if node.kind.value == "decision")
        template = next(edge for edge in payload.mapping.topology.edges if edge.source_node_id == decision.id)
        payload.mapping.topology.edges = [edge for edge in payload.mapping.topology.edges if edge.source_node_id != decision.id]
        payload.mapping.topology.edges.extend(template.model_copy(update={"id": f"option-{index}", "target_node_id": None}) for index in range(6))
        receipt = store.save_authoring_draft(editor_scope="story_graph", entity_id="root", base_canonical_revision=0,
            expected_draft_revision=0, payload=payload.model_dump(mode="json", by_alias=True))
        heads = {stage: store.authoring.get_stage_head(project_id, stage) for stage in StageName}
        response = client.post(f"{url}/graph-workbench/preview", json={"expectedDraftRevision": receipt.draft_revision,
            "command": {"operation": "add_edge", "edgeId": "seventh", "sourceNodeId": decision.id, "targetNodeId": None}})
        assert response.status_code == 409, response.text
        body = response.json()
        assert body["code"] == "graph_edit_unsafe"
        assert body["diagnostics"][0]["facts"] == {"nodeId": decision.id, "nodeKind": "decision", "actual": 7, "limit": 6}
        assert store.graph_workbench_state().draft == receipt
        assert {stage: store.authoring.get_stage_head(project_id, stage) for stage in StageName} == heads
        # The other API composition exposes the identical public error payload.
        app = FastAPI()
        register_api_error_handlers(app)
        @app.get("/refusal")
        def refuse():
            raise GraphEditSafetyError(body["diagnostics"])
        assert TestClient(app).get("/refusal").json() == body
    finally:
        store.close()
