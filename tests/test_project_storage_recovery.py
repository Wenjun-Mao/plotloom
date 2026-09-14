"""Portable snapshot and restore proof for the direct project-folder format."""

from __future__ import annotations

from io import BytesIO
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage import (
    ProjectBusyError,
    ProjectFolderStorage,
    ProjectStorageConflictError,
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
)
import plotloom.project_storage.recovery as recovery_module
from plotloom.project_storage.operational_state import ProjectAccessLease


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
        asset = restored.media.list_managed_assets(project_id)[0]
        stored = restored.media.get_managed_asset_storage(project_id, asset["id"])
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


@pytest.mark.parametrize("extra_path", ["extra.txt", ".hidden", "review/extra.txt"])
def test_snapshot_restore_rejects_each_extra_regular_tree_entry(
    tmp_path: Path, extra_path: str,
) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    receipt = storage.recovery.create_snapshot(project_id)
    snapshot = Path(receipt.location)
    extra = snapshot / extra_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("unexpected", encoding="utf-8")

    with pytest.raises(ProjectStorageCorruptionError, match="unexpected"):
        _storage(tmp_path, f"fresh-{extra_path.replace('/', '-')}").recovery.restore(snapshot)


def test_snapshot_restore_rejects_extra_links_and_special_entries(tmp_path: Path) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    receipt = storage.recovery.create_snapshot(project_id)
    snapshot = Path(receipt.location)
    (snapshot / "linked-project.json").symlink_to(snapshot / "project.json")
    with pytest.raises(ProjectStorageConfinementError, match="symlink"):
        _storage(tmp_path, "fresh-link").recovery.restore(snapshot)

    (snapshot / "linked-project.json").unlink()
    os.mkfifo(snapshot / "unexpected-pipe")
    with pytest.raises(ProjectStorageConfinementError, match="non-regular"):
        _storage(tmp_path, "fresh-pipe").recovery.restore(snapshot)


def test_restore_compares_same_size_copied_bytes_to_frozen_snapshot_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage, project_id, _media = _portable_fixture(tmp_path)
    receipt = storage.recovery.create_snapshot(project_id)
    snapshot = Path(receipt.location)
    relative = next(snapshot.glob("assets/*/*")).relative_to(snapshot)
    original = recovery_module._copy_payload
    changed = False

    def alter_before_copy(root: Path, destination: Path, path: object):
        nonlocal changed
        if not changed and path == relative:
            target = root / relative
            bytes_before = target.read_bytes()
            target.write_bytes(bytes(reversed(bytes_before)))
            assert len(target.read_bytes()) == len(bytes_before)
            changed = True
        return original(root, destination, path)  # type: ignore[arg-type]

    monkeypatch.setattr(recovery_module, "_copy_payload", alter_before_copy)
    fresh = _storage(tmp_path, "fresh-race")
    with pytest.raises(ProjectStorageCorruptionError, match="source changed"):
        fresh.recovery.restore(snapshot)
    assert changed
    assert fresh.projects.discover() == []


def test_direct_restore_holds_the_closed_folder_lease_through_copy(tmp_path: Path) -> None:
    source, project_id, _media = _portable_fixture(tmp_path)
    store = source.projects.open(project_id)
    home = store.home
    store.close()
    source.projects.close_project(project_id)
    lease = ProjectAccessLease.acquire(home, mode="shared")
    try:
        with pytest.raises(ProjectBusyError, match="another local writer"):
            _storage(tmp_path, "fresh-lease").recovery.restore(home)
    finally:
        lease.close()


@pytest.mark.parametrize("sql", [
    "ALTER TABLE v2_projects ADD COLUMN hostile TEXT",
    "CREATE VIEW hostile_view AS SELECT id FROM v2_projects",
    "CREATE TRIGGER hostile_trigger AFTER INSERT ON v2_projects BEGIN SELECT 1; END",
])
def test_restore_rejects_unsupported_schema_before_any_project_handle_opens(
    tmp_path: Path, sql: str,
) -> None:
    source, project_id, _media = _portable_fixture(tmp_path)
    store = source.projects.open(project_id)
    home = store.home
    store.close()
    source.projects.close_project(project_id)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        connection.execute(sql)

    fresh = _storage(tmp_path, f"fresh-schema-{uuid4().hex}")
    with pytest.raises(ProjectStorageCorruptionError, match="schema"):
        fresh.recovery.restore(home)
    assert fresh.projects.discover() == []


def test_snapshot_does_not_treat_story_prose_as_an_owned_asset_reference(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    prose = "assets/aa/" + "a" * 64
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"title": prose}))
    project_id = store.manifest.project_id
    store.close()

    receipt = storage.recovery.create_snapshot(project_id)
    paths = {item.relative_path for item in receipt.manifest.files}
    assert not any(path.startswith("assets/") for path in paths)


def test_restored_unfinished_known_and_unknown_work_never_replays(tmp_path: Path) -> None:
    source, project_id, _media = _portable_fixture(tmp_path)
    store = source.projects.open(project_id)
    home = store.home
    store.close()
    known_run_id, unknown_run_id = str(uuid4()), str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(home / "project.sqlite3") as connection:
        for run_id in (known_run_id, unknown_run_id):
            connection.execute(
                "INSERT INTO v2_generation_runs "
                "(id, project_id, kind, parent_run_id, repair_stage, repair_source, "
                "work_unit_repair_scope_id, provider_snapshot, requested_stages, status, "
                "canonical_snapshot, instructions, legacy_unsealed, result_revision_ids, "
                "error, failure_code, failed_stage, created_at, started_at, finished_at) "
                "VALUES (?, ?, 'pipeline', NULL, NULL, NULL, NULL, '{}', '[\"story_bible\"]', "
                "'running', '{}', NULL, 1, '[]', NULL, NULL, NULL, ?, ?, NULL)",
                (run_id, project_id, now, now),
            )
        for run_id, provider_request_id in ((known_run_id, "provider-known"), (unknown_run_id, None)):
            connection.execute(
                "INSERT INTO v2_generation_attempts "
                "(id, run_id, work_unit_id, stage, attempt_number, attempt_kind, source_attempt_id, "
                "status, provider, model, error, dispatched_at, response_persisted_at, "
                "provider_request_id, outcome_unknown, outcome_code, started_at, finished_at) "
                "VALUES (?, ?, NULL, 'story_bible', 1, 'primary', NULL, 'running', "
                "'offline', 'fixture', NULL, ?, NULL, ?, 0, NULL, ?, NULL)",
                (str(uuid4()), run_id, now, provider_request_id, now),
            )

    receipt = source.recovery.create_snapshot(project_id)
    fresh = _storage(tmp_path, "fresh-recovery-control")
    restored_path = fresh.recovery.restore(Path(receipt.location))
    restored = fresh.projects.open(project_id)
    try:
        control = restored.recovery_control()
        assert control is not None and control.state == "recovery_required"
        assert {(item.operation_id, item.provider_state) for item in control.operations} == {
            (known_run_id, "known"), (unknown_run_id, "unknown"),
        }
        assert restored.generation.reconcile_startup_jobs().resubmit_run_ids == []
        for run_id in (known_run_id, unknown_run_id):
            with pytest.raises(InvalidTransitionError, match="recovery_required"):
                restored.generation.start_run(run_id)
    finally:
        restored.close()

    acknowledged = fresh.recovery.acknowledge_recovery(project_id)
    assert acknowledged.state == "acknowledged"
    reopened = fresh.projects.open(project_id)
    try:
        # Acknowledgement permits new work in a later slice, but never turns
        # historic provider-facing run IDs into resumable submissions.
        with pytest.raises(InvalidTransitionError, match="recovery_required"):
            reopened.generation.start_run(known_run_id)
    finally:
        reopened.close()
    assert restored_path.is_dir()


def test_private_recovery_roots_reject_symlink_and_escape_paths(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "private-link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProjectStorageConfinementError, match="symlink"):
        recovery_module._private_directory(link, "snapshot", confinement_root=tmp_path)
    with pytest.raises(ProjectStorageConfinementError, match="escapes"):
        recovery_module._private_directory(outside, "restore", confinement_root=tmp_path / "inside")
