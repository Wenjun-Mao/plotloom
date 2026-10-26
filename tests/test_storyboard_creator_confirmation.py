"""One explicit unnamed board decision with unchanged admission and history."""
from contextlib import closing
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_contracts import OperationScope
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.stage_contracts import STAGE_ORDER, InitialStage, StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.human_confirmation_contracts import UnnamedCreatorConfirmation
from plotloom.persistence.schema import GateResultRow
from plotloom.project_storage import ProjectFolderStorage
from tests.backend_core.conftest import all_stage_payloads


@pytest.fixture
def board(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF, initial_stages=tuple(
        InitialStage(stage=stage, payload=payload.model_dump(mode="json", by_alias=True))
        for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True)
    ))) as store:
        project_id = store.manifest.project_id
        head = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
    client = TestClient(create_project_folder_authoring_app(storage))
    body = {"expectedRevision": head.revision, "contentHash": head.content_hash,
            "decision": "approve", "gateSetVersion": "storyboard.v2", "attribution": {"kind": "unnamed_creator"}}
    return storage, client, project_id, body


def test_explicit_unnamed_approve_revoke_survive_reopen_without_handoff(board):
    storage, client, project, body = board
    url = f"/api/v2/projects/{project}/storyboard-approval"
    approved = client.post(url, json=body)
    assert approved.status_code == 201, approved.text
    assert approved.json()["active"]
    assert approved.json()["decision"]["reviewer"] == ""
    assert approved.json()["decision"]["attribution"] == body["attribution"]
    assert approved.json()["decision"]["note"] is None
    assert client.post(url, json=body).status_code == 409
    revoked = client.post(url, json=body | {"decision": "revoke"})
    assert revoked.status_code == 201 and not revoked.json()["active"]
    assert revoked.json()["decision"]["attribution"] == body["attribution"]
    with closing(storage.projects.open(project)) as store:
        rows = store.authoring.list_approval_decisions(project)
        assert [row.decision for row in rows] == ["approve", "revoke"]
        assert all(row.reviewer == "" and row.note is None for row in rows)


@pytest.mark.parametrize("change,status", [({"expectedRevision": 99}, 409), ({"contentHash": "0" * 64}, 409),
    ({"gateSetVersion": "forged"}, 409), ({"reviewer": "Invented actor"}, 422),
    ({"note": "Invented explanation"}, 422), ({"attribution": None}, 422), ({"attribution": {"kind": "machine"}}, 422)])
def test_unnamed_action_cannot_bypass_exact_bindings_or_restore_name_form(board, change, status):
    _storage, client, project, body = board
    response = client.post(f"/api/v2/projects/{project}/storyboard-approval", json=body | change)
    assert response.status_code == status, response.text
    assert client.get(f"/api/v2/projects/{project}/storyboard-review").json()["decisions"] == []


def test_unnamed_action_still_requires_passing_server_gates(board):
    storage, client, project, body = board
    with closing(storage.projects.open(project)) as store, store.repository._write() as session:
        gate = session.query(GateResultRow).filter_by(project_id=project).first()
        gate.status, gate.required = "fail", True
    assert client.post(f"/api/v2/projects/{project}/storyboard-approval", json=body).status_code == 409


@pytest.mark.parametrize("scope", [OperationScope.TEXT, OperationScope.IMAGE, OperationScope.EVIDENCE])
def test_machine_scope_cannot_create_unnamed_storyboard_fact(board, monkeypatch, scope):
    storage, _client, project, body = board
    with closing(storage.projects.open(project)) as store:
        owner = store.repository._approvals
        monkeypatch.setattr(owner, "_access", replace(owner._access, authority=lambda: SimpleNamespace(scope=scope)))
        with pytest.raises(InvalidTransitionError, match="machine commands"):
            owner.decide_storyboard_approval(project, expected_revision=body["expectedRevision"],
                expected_content_hash=body["contentHash"], decision="approve",
                reviewer=UnnamedCreatorConfirmation(), gate_set_version="storyboard.v2")
        assert owner.list_approval_decisions(project) == []


def test_retained_named_decision_remains_named_after_new_unnamed_revoke(board):
    storage, client, project, body = board
    with closing(storage.projects.open(project)) as store:
        retained = store.authoring.decide_storyboard_approval(project,
            expected_revision=body["expectedRevision"], expected_content_hash=body["contentHash"],
            decision="approve", reviewer="Retained actual fixture reviewer", gate_set_version="storyboard.v2",
            note="Retained authored note.")
    response = client.post(f"/api/v2/projects/{project}/storyboard-approval", json=body | {"decision": "revoke"})
    assert response.status_code == 201
    history = client.get(f"/api/v2/projects/{project}/storyboard-review").json()["decisions"]
    old = next(row["decision"] for row in history if row["decision"]["id"] == retained.id)
    assert old["reviewer"] == retained.reviewer and old["note"] == retained.note
    assert "attribution" not in old
