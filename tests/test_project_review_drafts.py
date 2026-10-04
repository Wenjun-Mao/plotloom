import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage


@pytest.fixture
def draft_client(tmp_path: Path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    project = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = project.project().id
    project.close()
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        yield client, project_id


def put(client, project_id, editor="source", text="unfinished", revision=0, **patch):
    body = {"editorScope": "review_buffer", "entityId": editor, "baseCanonicalRevision": 1,
            "expectedDraftRevision": revision, "payload": {"editor": editor, "basis": "source:0", "text": text}}
    body.update(patch)
    return client.put(f"/api/v2/projects/{project_id}/authoring-drafts", json=body)


def test_partial_review_drafts_close_and_reopen_without_acceptance(draft_client):
    client, project_id = draft_client
    before = client.get(f"/api/v2/projects/{project_id}").json()
    for editor in ["source", "section_map", "cast", "art", "script"]:
        assert put(client, project_id, editor, '{"unfinished":').status_code == 200
    assert client.post(f"/api/v2/projects/{project_id}/close").status_code == 200
    assert client.post(f"/api/v2/projects/{project_id}/open").status_code == 200
    drafts = client.get(f"/api/v2/projects/{project_id}/authoring-drafts").json()
    assert len(drafts) == 5
    assert all(draft["payload"]["text"] == '{"unfinished":' for draft in drafts)
    assert client.get(f"/api/v2/projects/{project_id}").json() == before
    assert client.get(f"/api/v2/projects/{project_id}/source-outline").json()["source"] is None
    assert client.get(f"/api/v2/projects/{project_id}/runs").json()["runs"] == []


def test_review_draft_cas_identity_and_closed_admission(draft_client):
    client, project_id = draft_client
    assert put(client, project_id).status_code == 200
    assert put(client, project_id).status_code == 409
    assert put(client, project_id, revision=1, baseCanonicalRevision=0).status_code == 409
    assert put(client, project_id, entityId="art").status_code == 422
    assert put(client, project_id, editor="settings").status_code == 422
    assert client.post(f"/api/v2/projects/{project_id}/close").status_code == 200
    assert put(client, project_id, revision=1).status_code == 409


@pytest.mark.parametrize("text", ['{"apiKey":"not-allowed"}', '{"password":',
    json.dumps({"sectionId": "opening", "text": '{"refresh_token":"not-allowed"}'}), "Bearer secret-value"])
def test_review_draft_never_retains_credentials(draft_client, text):
    client, project_id = draft_client
    assert put(client, project_id, text=text).status_code == 422
    assert client.get(f"/api/v2/projects/{project_id}/authoring-drafts").json() == []
