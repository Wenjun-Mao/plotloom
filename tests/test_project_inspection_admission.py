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
