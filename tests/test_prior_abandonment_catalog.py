"""Deletion-only metadata never grants current-schema or execution admission."""
import shutil
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_abandonment_contracts import AbandonmentPreview
from plotloom.project_storage.project_handle import ProjectStore
from plotloom.project_storage.project_home import ProjectHome
from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
from tests.autopilot_continuation_layout_fixtures import retain_pre_continuation_layout
from tests.test_autopilot_image_safety import reach
from tests.test_autopilot_recovery import storage_at
from tests.test_autopilot_schema_upgrade import retained_bytes


def test_valued_prior_catalog_is_passive_and_first_click_uses_real_preview_and_guarded_erasure(
        tmp_path, monkeypatch, compact_two_cut_text_prefix):
    storage, _registry, service, view, images, texts = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        with closing(storage.projects.open(view.project_id)) as store:
            home, project = store.home, store.project()
        retain_pre_continuation_layout(home)
        (home / ".project-operation.lock").unlink()
        with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as neighbor:
            neighbor_id = neighbor.manifest.project_id
        app = create_project_folder_authoring_app(storage)
        host_calls = []
        def host(packet, *, revoke=False):
            host_calls.append((packet.model_dump(mode="json"), revoke))
            return AbandonmentPreview(project_id=view.project_id, preview_hash="a" * 64,
                eligible=True, blockers=[], unknown_attempt_ids=[str(packet.attempts[-1].attempt_id)], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        before = retained_bytes(home)
        with sqlite3.connect(home / "project.sqlite3") as connection:
            original = connection.execute("SELECT * FROM v2_autopilot_exec_attempts ORDER BY id").fetchall()
            schema = connection.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
        with monkeypatch.context() as passive:
            passive.setattr(ProjectStore, "open", lambda *_a, **_k: pytest.fail("catalog cannot open a canonical store"))
            listed = client.get("/api/v2/project-abandonment-candidates")
        assert listed.status_code == 200
        assert listed.json() == [{"projectId": project.id, "title": project.brief.title,
            "projectRevision": project.revision, "lifecycleRevision": project.lifecycle_revision,
            "kind": "immediate_prior_abandonment_only"}]
        assert not host_calls and retained_bytes(home) == before
        assert not (home / ".project-operation.lock").exists()
        assert storage.application.abandonment.current(project.id) is None
        assert {item["id"] for item in client.get("/api/v2/projects").json()["projects"]} == {neighbor_id}
        assert client.get(f"/api/v2/projects/{project.id}").status_code == 422
        preview = client.get(f"/api/v2/projects/{project.id}/abandonment-preview").json()
        consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "previewHash")}
        path = f"/api/v2/projects/{project.id}/abandon-and-delete"
        assert client.post(path, json=consent).status_code == 409
        assert client.post(path, json=consent | {"acknowledgeUnknownRemote": True, "confirmationTitle": "wrong"}).status_code == 409
        with sqlite3.connect(home / "project.sqlite3") as connection:
            assert connection.execute("SELECT * FROM v2_autopilot_exec_attempts ORDER BY id").fetchall() == original
            assert connection.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall() == schema
        calls_before = list(images), list(texts)
        assert client.post(path, json=consent | {"acknowledgeUnknownRemote": True}).status_code == 204
        assert not home.exists() and not client.get("/api/v2/project-abandonment-candidates").json()
        assert sum(revoke for _, revoke in host_calls) == 1 and (images, texts) == calls_before
        with closing(storage.projects.open(neighbor_id)):
            pass
    finally:
        service.close()


@pytest.mark.parametrize("defect", ["current", "older_serial", "foreign_id", "altered_sql", "bad_brief", "duplicate", "symlink", "pending", "acknowledged"])
def test_catalog_ignores_unsupported_or_nonunique_or_pending_homes(tmp_path, defect):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        home, project, manifest = store.home, store.project(), store.manifest
    if defect != "current":
        retain_pre_continuation_layout(home)
    if defect == "older_serial":
        from tests.test_codex_exec_pool_project_upgrade import _serial_layout
        _serial_layout(home)
    elif defect == "foreign_id":
        with sqlite3.connect(home / "project.sqlite3") as connection:
            connection.execute("UPDATE v2_projects SET id='foreign'")
    elif defect in {"altered_sql", "bad_brief"}:
        with sqlite3.connect(home / "project.sqlite3") as connection:
            connection.execute("CREATE TABLE foreign_contract(id TEXT)" if defect == "altered_sql" else "UPDATE v2_projects SET brief='{}'")
    elif defect == "duplicate":
        # A different/unsupported layout still counts as an identity collision.
        other = home.with_name(home.name + "-duplicate")
        shutil.copytree(home, other)
        with sqlite3.connect(other / "project.sqlite3") as connection:
            connection.execute("CREATE TABLE foreign_contract(id TEXT)")
    elif defect == "symlink":
        database = home / "project.sqlite3"
        moved = home / "actual.sqlite3"
        database.rename(moved)
        database.symlink_to(moved)
    elif defect in {"pending", "acknowledged"}:
        storage.application.abandonment.prepare(ProjectHome(home, manifest), project.id, {"confirmationTitle": project.brief.title})
        if defect == "acknowledged":
            storage.application.abandonment.acknowledge(project.id, AbandonmentPreview(project_id=project.id,
                preview_hash="a" * 64, eligible=True, blockers=[], unknown_attempt_ids=[], revoked=True))
    from plotloom.project_storage.abandonment_catalog import (
        prior_abandonment_candidates,
    )
    assert prior_abandonment_candidates(storage.projects, storage.application.abandonment) == []
