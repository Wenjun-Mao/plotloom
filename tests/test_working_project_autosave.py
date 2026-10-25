"""Draft-only creation and incomplete Brief never install production input."""
from pathlib import Path
from fastapi.testclient import TestClient
from plotloom.api import create_project_folder_authoring_app
from plotloom.project_storage import ProjectFolderStorage


def test_draft_only_creation_replay_incomplete_brief_and_restart(tmp_path: Path):
    roots = dict(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    storage = ProjectFolderStorage(**roots)
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        first = client.post("/api/v2/projects", json={"brief": None}, headers={"Idempotency-Key": "draft-intent-a"})
        assert first.status_code == 201, first.text
        project = first.json()
        assert project["brief"] is None
        listed = client.get("/api/v2/projects")
        assert listed.status_code == 200, listed.text
        assert listed.json()["projects"][0]["id"] == project["id"]
        assert client.post("/api/v2/projects", json={"brief": None}, headers={"Idempotency-Key": "draft-intent-a"}).json()["id"] == project["id"]
        pid = project["id"]
        body = {"editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1, "expectedDraftRevision": 0,
                "payload": {"title": "unfinished", "synopsis": "", "targetPlaythroughSeconds": ""}}
        saved = client.put(f"/api/v2/projects/{pid}/authoring-drafts", json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()["payload"]["targetPlaythroughSeconds"] == ""
        view = client.get(f"/api/v2/projects/{pid}").json()
        assert view["brief"] is None and view["displayTitle"] == "unfinished"
        assert all(stage["head"]["revision"] == 0 for stage in client.get(f"/api/v2/projects/{pid}/stages").json()["stages"])
        assert client.get(f"/api/v2/projects/{pid}/runs").json()["runs"] == []
    storage = ProjectFolderStorage(**roots)
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        assert client.get(f"/api/v2/projects/{pid}").json()["brief"] is None
        assert client.get(f"/api/v2/projects/{pid}/authoring-drafts").json()[0]["payload"]["targetPlaythroughSeconds"] == ""


def test_raw_input_adoption_and_nullable_lifecycle_are_exact(tmp_path: Path):
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        project = client.post("/api/v2/projects", json={"brief": None}).json()
        pid = project["id"]
        base = f"/api/v2/projects/{pid}"
        payload = FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)
        payload["targetPlaythroughSeconds"] = str(payload["targetPlaythroughSeconds"])
        payload["title"] = "   "
        request = {"editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1, "expectedDraftRevision": 0, "payload": payload}
        saved = client.put(base + "/authoring-drafts", json=request)
        assert saved.status_code == 200, saved.text
        bad = client.patch(base, json={"expectedRevision": 1, "brief": {**payload, "synopsis": ""}, "consumedDraft": {"editorScope": "brief", "entityId": "root", "draftRevision": 1}})
        assert bad.status_code == 422
        assert client.get(base).json()["brief"] is None
        assert client.get(base + "/authoring-drafts").json()[0]["draftRevision"] == 1
        archived = client.post(base + "/archive", json={"expectedLifecycleRevision": 1})
        assert archived.status_code == 200 and archived.json()["brief"] is None
        restored = client.post(base + "/restore", json={"expectedLifecycleRevision": 2})
        assert restored.status_code == 200 and restored.json()["brief"] is None
        duplicate = client.post(base + "/duplicate", json={"expectedLifecycleRevision": 3}, headers={"Idempotency-Key": "nullable-copy"})
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json()["project"]["brief"] is None
        adopted = client.patch(base, json={"expectedRevision": 1, "brief": {**FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True), "title": "未命名故事"}, "consumedDraft": {"editorScope": "brief", "entityId": "root", "draftRevision": 1}})
        assert adopted.status_code == 200, adopted.text
        assert adopted.headers["X-Plotloom-Draft-Consumed-Revision"] == "1"
        assert adopted.json()["title"] == "未命名故事" if "title" in adopted.json() else adopted.json()["brief"]["title"] == "未命名故事"
        assert client.get(base + "/authoring-drafts").json() == []


def test_typed_partial_stage_input_and_raw_numeric_bounds(tmp_path: Path):
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    from tests.backend_core.conftest import all_stage_payloads
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    pid = store.project().id
    store.close()
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        base = f"/api/v2/projects/{pid}/authoring-drafts"
        bible = all_stage_payloads()[0].model_dump(mode="json", by_alias=True)
        bible["logline"] = ""
        request = {"editorScope": "story_bible", "entityId": "root", "baseCanonicalRevision": 0, "expectedDraftRevision": 0, "payload": bible}
        result = client.put(base, json=request)
        assert result.status_code == 200, result.text
        assert result.json()["payload"]["logline"] == ""
        assert client.put(base, json={**request, "expectedDraftRevision": 1, "payload": {**bible, "browserState": {}}}).status_code == 422
        raw = {"editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1, "expectedDraftRevision": 0,
               "payload": {"title": "", "synopsis": "", "targetPlaythroughSeconds": "x" * 101}}
        assert client.put(base, json=raw).status_code == 422


def test_unsubmitted_custom_direction_is_independent_bounded_text(tmp_path: Path):
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        project = client.post("/api/v2/projects", json={"brief": None}).json()
        base = f"/api/v2/projects/{project['id']}"
        request = {"editorScope": "review_buffer", "entityId": "brief_custom:narrative", "baseCanonicalRevision": 0, "expectedDraftRevision": 0,
                   "payload": {"editor": "brief_custom", "targetId": "narrative", "basis": "brief-custom:v1", "text": "unfinished custom {"}}
        saved = client.put(base + "/authoring-drafts", json=request)
        assert saved.status_code == 200, saved.text
        assert client.put(base + "/authoring-drafts", json={**request, "entityId": "source", "payload": {"editor": "source", "basis": "source:0", "text": "ordinary"}}).status_code == 409
        assert client.put(base + "/authoring-drafts", json={**request, "expectedDraftRevision": 1, "payload": {**request["payload"], "text": "x" * 121}}).status_code == 422
        result = client.patch(base, json={"expectedRevision": 1, "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)})
        assert result.status_code == 200, result.text
        assert "unfinished custom" not in str(result.json()["brief"])
        assert client.get(base + "/authoring-drafts").json()[0] == saved.json()
        next_input = client.put(base + "/authoring-drafts", json={**request, "expectedDraftRevision": 1, "payload": {**request["payload"], "text": "still unfinished"}})
        assert next_input.status_code == 200, next_input.text


def test_working_display_title_is_independent_of_confirmed_brief():
    from plotloom.working_inputs import working_project_title
    assert working_project_title(None) == "未命名项目"
    assert working_project_title("Confirmed") == "Confirmed"
    assert working_project_title("Confirmed", "") == "未命名项目"
    assert working_project_title("Confirmed", "  ") == "未命名项目"
    assert working_project_title(None, " Draft ") == "Draft"
    assert working_project_title("Confirmed", "Draft") == "Draft"
