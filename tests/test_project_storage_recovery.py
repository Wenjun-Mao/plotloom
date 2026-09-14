"""Portable snapshot and restore proof for the direct project-folder format."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import (
    ProjectBusyError,
    ProjectFolderStorage,
    ProjectStorageConflictError,
    ProjectStorageCorruptionError,
)
import plotloom.project_storage.recovery as recovery_module


def _png() -> bytes:
    image = Image.new("RGB", (24, 16), (21, 77, 143))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _storage(tmp_path: Path, name: str = "source") -> ProjectFolderStorage:
    return ProjectFolderStorage(
        outputs_root=tmp_path / name / "outputs",
        application_data_root=tmp_path / name / "application",
    )


def _portable_fixture(tmp_path: Path) -> tuple[ProjectFolderStorage, str, bytes]:
    storage = _storage(tmp_path)
    client = TestClient(create_project_folder_authoring_app(storage))
    created = client.post(
        "/api/v2/projects",
        json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]
    draft = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "brief", "entityId": "root", "baseCanonicalRevision": 1,
            "expectedDraftRevision": 0,
            "payload": FIXED_CHINESE_BRIEF.model_copy(update={"title": "可移植草稿"}).model_dump(mode="json", by_alias=True),
        },
    )
    assert draft.status_code == 200, draft.text
    media = _png()
    imported = client.post(
        f"/api/v2/projects/{project_id}/managed-assets",
        files={"image": ("fixture.png", media, "image/png")},
        data={"origin": "offline recovery fixture", "rights": "unknown", "declared_additions_json": "[]"},
    )
    assert imported.status_code == 201, imported.text
    return storage, project_id, media


def test_snapshot_restores_drafts_and_owned_media_without_application_database(tmp_path: Path) -> None:
    storage, project_id, expected_media = _portable_fixture(tmp_path)
    client = TestClient(create_project_folder_authoring_app(storage))

    created = client.post(f"/api/v2/projects/{project_id}/snapshots")
    assert created.status_code == 201, created.text
    receipt = created.json()
    assert receipt["status"] == "complete"
    assert receipt["projectId"] == project_id
    assert any(item["relativePath"].startswith("assets/") for item in receipt["manifest"]["files"])
    assert client.get(
        f"/api/v2/projects/{project_id}/snapshots/{receipt['snapshotId']}"
    ).json()["location"] == receipt["location"]

    source_store = storage.projects.open(project_id)
    source_home = source_store.home
    source_store.close()
    shutil.rmtree(source_home)
    shutil.rmtree(tmp_path / "source" / "application")

    fresh = _storage(tmp_path, "fresh")
    # The snapshot can be selected explicitly even when the former project
    # folder and installation application database no longer exist.
    restored_path = fresh.recovery.restore(Path(receipt["location"]))
    assert restored_path.is_dir()
    restored = fresh.projects.open(project_id)
    try:
        assert restored.authoring_drafts()[0].payload["title"] == "可移植草稿"
        asset = restored.repository.list_managed_assets(project_id)[0]
        stored = restored.repository.get_managed_asset_storage(project_id, asset["id"])
        assert restored.artifacts.get(stored["originalUri"]) == expected_media
    finally:
        restored.close()


def test_snapshot_rejects_corrupt_bytes_without_advertising_a_restored_project(tmp_path: Path) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    receipt = storage.recovery.create_snapshot(project_id)
    snapshot = Path(receipt.location)
    asset = next(snapshot.glob("assets/*/*"))
    asset.write_bytes(b"corrupt")

    fresh = _storage(tmp_path, "fresh")
    with pytest.raises(ProjectStorageCorruptionError, match="hash"):
        fresh.recovery.restore(snapshot)
    assert fresh.projects.discover() == []


def test_snapshot_rejects_corrupt_sqlite_and_missing_referenced_media(tmp_path: Path) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    receipt = storage.recovery.create_snapshot(project_id)
    snapshot = Path(receipt.location)
    (snapshot / "project.sqlite3").write_bytes(b"not sqlite")
    fresh = _storage(tmp_path, "fresh-sqlite")
    with pytest.raises(ProjectStorageCorruptionError, match="hash|SQLite|database"):
        fresh.recovery.restore(snapshot)
    assert fresh.projects.discover() == []

    replacement = storage.recovery.create_snapshot(project_id)
    missing = next(Path(replacement.location).glob("assets/*/*"))
    missing.unlink()
    with pytest.raises(ProjectStorageCorruptionError, match="unavailable|hash"):
        _storage(tmp_path, "fresh-media").recovery.restore(Path(replacement.location))


def test_snapshot_copy_failure_removes_private_work_and_publishes_no_completed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    original = recovery_module._copy_payload

    def fail_after_database(root: Path, destination: Path, relative: object):
        if str(relative).startswith("assets/"):
            raise OSError("simulated process interruption during immutable-media copy")
        return original(root, destination, relative)  # type: ignore[arg-type]

    monkeypatch.setattr(recovery_module, "_copy_payload", fail_after_database)
    with pytest.raises(OSError, match="simulated process interruption"):
        storage.recovery.create_snapshot(project_id)
    snapshot_parent = storage.projects.outputs_root / ".snapshots" / project_id
    assert not [entry for entry in snapshot_parent.iterdir() if not entry.name.startswith(".")]


def test_restore_refuses_open_or_duplicate_direct_project_folders(tmp_path: Path) -> None:
    source, project_id, _media = _portable_fixture(tmp_path)
    source_store = source.projects.open(project_id)
    home = source_store.home
    source_store.close()
    fresh = _storage(tmp_path, "fresh")

    with pytest.raises(ProjectBusyError, match="explicitly closed"):
        fresh.recovery.restore(home)
    source.projects.close_project(project_id)
    fresh.recovery.restore(home)
    with pytest.raises(ProjectStorageConflictError, match="existing project identity"):
        fresh.recovery.restore(home)


def test_snapshot_refuses_an_admitted_writer_until_its_lease_releases(tmp_path: Path) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    writer = storage.projects.open(project_id)
    try:
        with pytest.raises(ProjectBusyError, match="project_busy"):
            storage.recovery.create_snapshot(project_id)
    finally:
        writer.close()
    assert storage.recovery.create_snapshot(project_id).status == "complete"


def test_operator_restore_cli_needs_only_an_explicit_source_and_outputs_root(tmp_path: Path) -> None:
    source, project_id, _media = _portable_fixture(tmp_path)
    source_store = source.projects.open(project_id)
    home = source_store.home
    source_store.close()
    source.projects.close_project(project_id)
    destination = tmp_path / "isolated" / "outputs"

    result = subprocess.run(
        ["uv", "run", "plotloom", "restore", "--source", str(home), "--outputs-dir", str(destination)],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"status": "restored"' in result.stdout
    restored_storage = ProjectFolderStorage(
        outputs_root=destination,
        application_data_root=tmp_path / "isolated" / "new-application",
    )
    restored_storage.projects.reopen_project(project_id)
    restored = restored_storage.projects.open(project_id)
    restored.close()
