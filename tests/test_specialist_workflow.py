"""Real storage/exchange integration; only the external queue is simulated."""
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.runtime import build_runtime_app
from tests.test_project_storage_source_outline import _deliver, _material
from tests.test_project_storage_source_outline_api import _settings


def test_outline_queue_validated_delivery_and_restart_without_acceptance(tmp_path, monkeypatch):
    original = subprocess.run
    messages = []
    def run(command, **kwargs):
        if command[:2] == ["codex", "queue"]:
            messages.append(command)
            return subprocess.CompletedProcess(command, 0)
        return original(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", run)
    settings = _settings(tmp_path)
    app = build_runtime_app(settings)
    with TestClient(app) as client:
        roles = {role: {"name": role, "taskId": str(uuid4())} for role in ["text", "image"]}
        assert client.put("/api/v2/specialists", json=roles).status_code == 200
        project = client.post("/api/v2/projects", json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)}).json()["id"]
        base = f"/api/v2/projects/{project}/source-outline"
        saved = client.put(base + "/source", json={"expectedSourceRevision": 0, "material": _material().model_dump(mode="json", by_alias=True)})
        assert saved.status_code == 200, saved.text
        prepared = client.post(base + "/candidates")
        assert prepared.status_code == 201, prepared.text
        job = prepared.json()["jobId"]
        task = f"/api/v2/projects/{project}/specialist-tasks/outline/{job}"
        package = Path(prepared.json()["packagePath"])
        frozen = {str(p): p.read_bytes() for p in package.rglob("*") if p.is_file()}
        sent = client.post(task + "/send")
        assert sent.status_code == 200, sent.text
        assert sent.json()["state"] == "queued"
        assert client.post(task + "/send").status_code == 409
        assert len(messages) == 1
        assert client.get(base).json()["acceptedOutline"] is None
        assert client.put("/api/v2/specialists", json=roles).status_code == 409
        store = app.state.project_folder_storage.projects.open(project)
        try:
            _deliver(store, store.outline_candidate_request(job))
        finally:
            store.close()
        checked = client.post(task + "/check")
        assert checked.status_code == 200, checked.text
        state = client.get(base).json()
        assert state["candidate"]["status"] == "ready"
        assert state["acceptedOutline"] is None
        assert frozen == {str(p): p.read_bytes() for p in package.rglob("*") if p.is_file()}
        assert not client.get("/api/v2/specialists").json()["busy"]
    with TestClient(build_runtime_app(settings)) as restarted:
        assert restarted.get("/api/v2/specialists").json()["text"] == roles["text"]
        assert restarted.get(task).json()["state"] == "completed"
        assert len(messages) == 1
