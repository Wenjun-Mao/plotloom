"""Direct whole-home deletion uses production composition and disposable roots."""

from io import BytesIO
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage, ProjectStorageError
from plotloom.project_storage.deletion import remove_owned_home
from plotloom.runtime import build_runtime_app
from tests.project_storage_fixtures import FixtureResolver


def runtime(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    return build_runtime_app(PlotloomSettings(
        repo_root=tmp_path, outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application", static_dir=static,
        text_auth_mode="none",
    ), text_provider_resolver=FixtureResolver())


def create(client, title="删除测试"):
    result = client.post("/api/v2/projects", json={"brief": FIXED_CHINESE_BRIEF.model_copy(
        update={"title": title}).model_dump(mode="json", by_alias=True)},
        headers={"Idempotency-Key": title.encode("utf-8").hex()})
    assert result.status_code == 201
    return result.json()


def delete(client, project, **overrides):
    return client.post(f"/api/v2/projects/{project['id']}/permanent-delete", json={
        "expectedProjectRevision": project["revision"],
        "expectedLifecycleRevision": project["lifecycleRevision"],
        "confirmationTitle": project["brief"]["title"], **overrides,
    })


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (32, 32), (23, 45, 67)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("state", ["active", "archived", "closed"])
def test_direct_delete_erases_only_owned_home_in_every_directory_state(tmp_path, state):
    app = runtime(tmp_path)
    storage = app.state.project_folder_storage
    original = tmp_path / "external.png"
    original.write_bytes(image_bytes())
    with TestClient(app) as client:
        target, neighbor = create(client), create(client, "保留邻居")
        imported = []
        for project in (target, neighbor):
            response = client.post(f"/api/v2/projects/{project['id']}/managed-assets",
                files={"image": ("image.png", original.read_bytes(), "image/png")},
                data={"origin": "disposable test", "rights": "known"})
            assert response.status_code == 201
            imported.append(response.json())
        assert imported[0]["originalHash"] == imported[1]["originalHash"]
        snapshot = client.post(f"/api/v2/projects/{target['id']}/snapshots")
        assert snapshot.status_code == 201
        snapshot_path = Path(snapshot.json()["location"])
        snapshot_files = {str(file.relative_to(snapshot_path)): file.read_bytes()
            for file in snapshot_path.rglob("*") if file.is_file()}
        store = storage.projects.open(target["id"])
        home = store.home
        store.close()
        (home / "external-link").symlink_to(original)
        before_profiles = client.get("/api/v2/text-provider-profiles").json()
        if state == "archived":
            target = client.post(f"/api/v2/projects/{target['id']}/archive",
                json={"expectedLifecycleRevision": target["lifecycleRevision"]}).json()
        elif state == "closed":
            assert client.post(f"/api/v2/projects/{target['id']}/close").status_code == 200
            assert client.get(f"/api/v2/projects/{target['id']}").json()["code"] == "project_closed"
        response = delete(client, target)
        assert response.status_code == 204, response.text
        assert not home.exists()
        assert original.read_bytes() == image_bytes()
        assert snapshot_files == {str(file.relative_to(snapshot_path)): file.read_bytes()
            for file in snapshot_path.rglob("*") if file.is_file()}
        assert client.get(f"/api/v2/projects/{target['id']}").status_code == 404
        assert client.get(f"/api/v2/projects/{neighbor['id']}/managed-assets/{imported[1]['id']}/original").content == image_bytes()
        assert client.get("/api/v2/text-provider-profiles").json() == before_profiles
        with storage.application._read() as connection:
            assert connection.execute("SELECT target_project_id FROM application_project_create_requests").fetchall()[0][0] == neighbor["id"]


@pytest.mark.parametrize("overrides,status", [
    ({"confirmationTitle": "wrong"}, 409),
    ({"expectedProjectRevision": 0}, 422),
    ({"expectedProjectRevision": 99}, 409),
    ({"expectedLifecycleRevision": 99}, 409),
])
def test_failed_confirmation_and_revision_admission_preserve_every_byte(tmp_path, overrides, status):
    app = runtime(tmp_path)
    with TestClient(app) as client:
        target = create(client)
        store = app.state.project_folder_storage.projects.open(target["id"])
        home = store.home
        store.close()
        before = {file.name: file.read_bytes() for file in home.iterdir() if file.is_file()}
        assert delete(client, target, **overrides).status_code == status
        after = {file.name: file.read_bytes() for file in home.iterdir() if file.is_file()}
        assert after == before


def test_stale_brief_and_held_handle_cannot_delete(tmp_path):
    app = runtime(tmp_path)
    with TestClient(app) as client:
        target = create(client)
        updated = client.patch(f"/api/v2/projects/{target['id']}", json={
            "expectedRevision": target["revision"], "brief": {**target["brief"], "synopsis": "changed"}})
        assert updated.status_code == 200
        assert delete(client, target).status_code == 409
        store = app.state.project_folder_storage.projects.open(target["id"])
        try:
            assert delete(client, updated.json()).json()["code"] == "project_busy"
            assert store.home.is_dir()
        finally:
            store.close()
        assert delete(client, updated.json()).status_code == 204


def test_manifest_withdrawal_denies_late_open_before_lock_removal(tmp_path, monkeypatch):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project, home = store.project(), store.home
    store.close()
    real_remove = shutil.rmtree
    def late_open(path):
        assert Path(path) == home
        assert not (home / "project.json").exists()
        with pytest.raises(ProjectStorageError, match="project not found"):
            storage.projects.open(project.id)
        real_remove(path)
    monkeypatch.setattr("plotloom.project_storage.deletion.shutil.rmtree", late_open)
    # Mock must preserve the platform safety capability being exercised.
    late_open.avoids_symlink_attacks = True
    storage.lifecycle.permanently_delete(project.id, expected_project_revision=project.revision,
        expected_lifecycle_revision=project.lifecycle_revision, confirmation_title=project.brief.title)
    assert not home.exists()


def test_eraser_requires_manifest_bound_exclusive_lease(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        before = store.project()
        with pytest.raises(ProjectStorageError, match="exclusive project lease"):
            remove_owned_home(store.home, outputs_root=storage.projects.outputs_root,
                manifest=store.manifest, lease=store._access_lease, close_repository=store.repository.close)
        assert store.project() == before
    finally:
        store.close()
