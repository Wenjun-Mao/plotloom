from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

import pytest
from pydantic import ValidationError

from plotloom.domain import ProjectBrief
from plotloom.project_storage import (
    DeterministicFakeProvider,
    GlobalAccountingEntry,
    OwnedArtifact,
    ProjectFolderStorage,
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    ProjectStore,
)


def _brief(title: str, synopsis: str) -> ProjectBrief:
    return ProjectBrief(title=title, synopsis=synopsis)


def _table_names(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def test_two_project_homes_edit_and_fake_run_reopen_without_a_shared_project_database(
    tmp_path: Path,
) -> None:
    outputs_root = tmp_path / "outputs"
    application_root = tmp_path / "application"
    storage = ProjectFolderStorage(
        outputs_root=outputs_root,
        application_data_root=application_root,
    )
    profile = storage.application.save_profile(
        "offline_fake",
        {"adapterId": "deterministic_fake", "adapterVersion": "1"},
        expected_revision=0,
    )
    assert storage.application.select_profile(profile.profile_id) == profile
    storage.application.record_accounting(
        GlobalAccountingEntry(
            dispatch_identity="offline-run-1",
            resource="test_units",
            reserved_units=0,
        )
    )

    first = storage.projects.create(_brief("First", "First isolated synopsis."))
    second = storage.projects.create(_brief("Second", "Second isolated synopsis."))
    edited_first = first.update_brief(
        _brief("First, edited", "First isolated synopsis."),
        expected_revision=1,
    )
    edited_second = second.update_brief(
        _brief("Second, edited", "Second isolated synopsis."),
        expected_revision=1,
    )
    first_run = first.run(DeterministicFakeProvider())
    second_run = second.run(DeterministicFakeProvider())

    # This represents the former shared project database. Folder reopening does
    # not configure, read, or need it.
    old_shared_database = tmp_path / "retained-pilot" / "plotloom.sqlite3"
    old_shared_database.parent.mkdir()
    with sqlite3.connect(old_shared_database) as connection:
        connection.execute("CREATE TABLE v2_projects (id TEXT PRIMARY KEY)")
    old_shared_database.unlink()

    reopened = ProjectFolderStorage(
        outputs_root=outputs_root,
        application_data_root=application_root,
    )
    reopened_first = reopened.projects.open(edited_first.id)
    reopened_second = reopened.projects.open(edited_second.id)

    assert reopened_first.project() == edited_first
    assert reopened_second.project() == edited_second
    assert [run.id for run in reopened_first.runs()] == [first_run.id]
    assert [run.id for run in reopened_second.runs()] == [second_run.id]
    assert json.loads(reopened_first.read_artifact(first_run.output)) == {
        "contractVersion": 1,
        "projectId": edited_first.id,
        "projectRevision": 2,
        "synopsis": "First isolated synopsis.",
        "title": "First, edited",
    }
    assert json.loads(reopened_second.read_artifact(second_run.output)) == {
        "contractVersion": 1,
        "projectId": edited_second.id,
        "projectRevision": 2,
        "synopsis": "Second isolated synopsis.",
        "title": "Second, edited",
    }

    discovered = reopened.projects.discover()
    assert {home.manifest.project_id for home in discovered} == {edited_first.id, edited_second.id}
    assert first.home != second.home
    assert first_run.output.relative_path.startswith("assets/")
    assert not Path(first_run.output.relative_path).is_absolute()
    assert set(json.loads((first.home / "project.json").read_text(encoding="utf-8"))) == {
        "createdAt",
        "databasePath",
        "formatVersion",
        "projectId",
    }

    first_tables = _table_names(first.home / "project.sqlite3")
    application_tables = _table_names(application_root / "application.sqlite3")
    assert {"project_state", "project_runs"}.issubset(first_tables)
    assert "v2_projects" not in first_tables
    assert "application_profiles" not in first_tables
    assert {"application_profiles", "application_preferences", "global_accounting"}.issubset(
        application_tables
    )
    assert "project_state" not in application_tables
    assert reopened.application.selected_profile() == profile
    assert reopened.application.accounting_entries()[0].dispatch_identity == "offline-run-1"


def test_project_storage_confines_artifacts_and_refuses_secret_profile_records(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    project = storage.projects.create(_brief("Confinement", "A confined project."))
    run = project.run(DeterministicFakeProvider())

    with pytest.raises(ProjectStorageConfinementError):
        OwnedArtifact(
            content_hash=run.output.content_hash,
            relative_path="../outside.json",
            media_type="application/json",
            size_bytes=run.output.size_bytes,
        )
    with pytest.raises(ValidationError, match="credentials"):
        storage.application.save_profile(
            "unsafe",
            {"baseUrl": "https://example.test", "apiKey": "sk-not-for-storage"},
            expected_revision=0,
        )

    outside = tmp_path / "outside"
    outside.mkdir()
    external_asset = outside / run.output.content_hash
    external_asset.write_bytes(project.read_artifact(run.output))
    hash_directory = project.home / "assets" / run.output.content_hash[:2]
    (hash_directory / run.output.content_hash).unlink()
    hash_directory.rmdir()
    hash_directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProjectStorageConfinementError, match="symlink"):
        project.read_artifact(run.output)


def test_project_storage_refuses_cross_project_links_mismatched_runs_and_overlapping_roots(
    tmp_path: Path,
) -> None:
    outputs_root = tmp_path / "outputs"
    application_root = tmp_path / "application"
    storage = ProjectFolderStorage(
        outputs_root=outputs_root,
        application_data_root=application_root,
    )
    first = storage.projects.create(_brief("First", "First project."))
    first_run = first.run(DeterministicFakeProvider())
    second = storage.projects.create(_brief("Second", "Second project."))
    target = second.home / first_run.output.relative_path
    target.parent.mkdir(parents=True)
    os.link(first.home / first_run.output.relative_path, target)

    with pytest.raises(ProjectStorageConfinementError, match="hard linked"):
        second.read_artifact(first_run.output)

    with sqlite3.connect(first.home / "project.sqlite3") as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("UPDATE project_runs SET project_id = 'other-project'")
    with pytest.raises(ProjectStorageCorruptionError, match="run for another project"):
        ProjectStore.open(first.home)

    with pytest.raises(ProjectStorageConfinementError, match="non-overlapping"):
        ProjectFolderStorage(
            outputs_root=tmp_path / "one-root",
            application_data_root=tmp_path / "one-root",
        )

    snapshots = storage.projects.outputs_root / ".snapshots" / "ignored"
    snapshots.mkdir(parents=True)
    (snapshots / "project.json").write_text(
        json.dumps(
            {
                "formatVersion": 1,
                "projectId": "not-a-live-project",
                "createdAt": "2026-09-13T00:00:00Z",
                "databasePath": "project.sqlite3",
            }
        ),
        encoding="utf-8",
    )
    assert [home.manifest.project_id for home in storage.projects.discover()] == [second.project().id]
