"""Inspection cannot substitute valid bytes, schema or authority evidence."""
from contextlib import closing
from pathlib import Path
import sqlite3
import pytest
from plotloom.project_storage import ProjectStorageCorruptionError
from tests.video_batch_fixtures import batch_environment


def test_pixel_read_uses_inspection_but_still_verifies_requested_hash(tmp_path, monkeypatch):
    storage, client, _service, _provider, project_id, _view = batch_environment(tmp_path)
    import plotloom.project_storage.current_schema as schema
    def forbid_full(*args, **kwargs):
        raise AssertionError("pixel inspection must not admit every retained review")
    monkeypatch.setattr(schema, "assert_current_review_bindings", forbid_full)
    with closing(storage.projects.inspect(project_id)) as store:
        asset = store.media.list_managed_assets(project_id)[0]
        storage_record = store.media.get_managed_asset_storage(project_id, asset["id"])
        original = store.artifacts.get(storage_record["displayUri"])
    response = client.get(f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/display")
    assert response.status_code == 200 and response.content == original
    with pytest.raises(AssertionError): storage.projects.open(project_id)


def test_inspection_does_not_cache_out_of_band_asset_bytes_or_wal_schema(tmp_path):
    storage, client, _service, _provider, project_id, _view = batch_environment(tmp_path)
    with closing(storage.projects.inspect(project_id)) as store:
        assets = store.media.list_managed_assets(project_id)
        asset = assets[0]
        database = store.database_path
        artifact = store.media.get_managed_asset_storage(project_id, asset["id"])
        from plotloom.project_storage.artifacts import _OwnedArtifactStore
        # The confined content-addressed URI is the bytes owner; corrupt exactly that file.
        content = store.artifacts.get(artifact["displayUri"])
        path = next(path for path in store.home.rglob("*") if path.is_file() and path.name == artifact["displayHash"])
    path.write_bytes(b"x" * len(content))
    response = client.get(f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/display")
    assert response.status_code == 422
    assert response.json()["code"] == "project_storage_error"
    assert "bytes do not match" in response.json()["message"]
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE unknown_wal_schema (id TEXT)")
        with pytest.raises(ProjectStorageCorruptionError): storage.projects.inspect(project_id)


@pytest.mark.parametrize("admission", ["inspection", "authority"])
def test_admitted_reads_require_initialized_lock_and_hold_exclusive_exclusion(tmp_path, admission, monkeypatch):
    from plotloom.story_workloads import FIXED_CHINESE_BRIEF
    from plotloom.project_storage import ProjectFolderStorage, ProjectBusyError
    from tests.working_input_preservation import preservation_inventory

    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = store.manifest.project_id, store.home
    storage.projects.close_project(project_id)
    before = preservation_inventory(tmp_path)
    with closing(storage.projects.read_open(project_id, admission=admission)) as reader:
        assert reader.project().id == project_id
        with pytest.raises(ProjectBusyError):
            storage.projects.reopen_project(project_id)
    assert preservation_inventory(tmp_path) == before
    lock = home / ".project-operation.lock"
    lock.unlink()
    before = preservation_inventory(tmp_path)
    from plotloom.project_storage import ProjectStore
    monkeypatch.setattr(ProjectStore, "open", lambda *_a, **_k: pytest.fail("missing operation lock must refuse before database validation"))
    with pytest.raises(ProjectStorageCorruptionError, match="initialized operation lock"):
        storage.projects.read_open(project_id, admission=admission)
    assert not lock.exists()
    assert preservation_inventory(tmp_path) == before


@pytest.mark.parametrize("frozen", [False, True])
def test_requested_media_inspection_ignores_unrelated_damaged_batch_authority(tmp_path, frozen):
    from tests.working_input_preservation import preservation_inventory

    storage, client, _service, _provider, project_id, view = batch_environment(tmp_path)
    with closing(storage.projects.inspect(project_id)) as store:
        database = store.database_path
        asset = store.media.list_managed_assets(project_id)[0]
        record = store.media.get_managed_asset_storage(project_id, asset["id"])
        original = store.artifacts.get(record["displayUri"])
    if frozen:
        storage.projects.close_project(project_id)
    # Corrupt only a different authority domain, not the requested asset/hash.
    with sqlite3.connect(database) as connection:
        changed = connection.execute("UPDATE v2_video_batches SET manifest_hash=? WHERE id=?", ("0" * 64, view["id"]))
        assert changed.rowcount == 1
    before = preservation_inventory(tmp_path)
    with pytest.raises(ProjectStorageCorruptionError, match="video batch contract"):
        storage.projects.read_open(project_id)
    response = client.get(f"/api/v2/projects/{project_id}")
    assert response.status_code == 200, response.text
    authority = client.get(f"/api/v2/projects/{project_id}/visual-workbench")
    assert authority.status_code == 422, authority.text
    metadata = client.get(f"/api/v2/projects/{project_id}/managed-assets")
    assert metadata.status_code == 200, metadata.text
    assert any(item["id"] == asset["id"] for item in metadata.json()["assets"])
    response = client.get(f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/display")
    assert response.status_code == 200 and response.content == original
    assert preservation_inventory(tmp_path) == before
