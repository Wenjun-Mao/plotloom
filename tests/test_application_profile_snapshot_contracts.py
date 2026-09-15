from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest

from plotloom.domain import ProviderSettings
from plotloom.project_storage.application_profile_snapshot import load_saved_text_profiles
from plotloom.project_storage.application_profiles import ApplicationProfileRepository
from plotloom.project_storage.application_store import ApplicationStore

from tests.project_storage_fixtures import fixture_profile


def _application_data_dir(
    tmp_path: Path, *profile_ids: str
) -> tuple[Path, ApplicationProfileRepository]:
    root = tmp_path / "application"
    root.mkdir()
    profiles = ApplicationProfileRepository(ApplicationStore(root), ProviderSettings())
    for profile_id in profile_ids:
        configuration = fixture_profile().model_dump(mode="json", by_alias=True)
        configuration["profileId"] = profile_id
        profiles.create_text_provider_profile(
            profile_id, profile_id, configuration=configuration
        )
    return root, profiles


def _file_state(path: Path) -> tuple[bytes, int, int, int] | None:
    if not path.exists():
        return None
    metadata = path.stat()
    return path.read_bytes(), metadata.st_size, metadata.st_mtime_ns, metadata.st_ino


def test_saved_profile_snapshot_reads_a_live_wal_without_mutating_application_files(
    tmp_path: Path,
) -> None:
    root, _profiles = _application_data_dir(tmp_path, "fixture_a", "fixture_b")
    database_path = root / "application.sqlite3"
    writer = sqlite3.connect(database_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute(
            "UPDATE application_profiles SET updated_at = ? WHERE profile_id = ?",
            ("2026-09-15T00:00:00+00:00", "fixture_a"),
        )
        writer.commit()
        watched_paths = (
            database_path,
            database_path.with_name("application.sqlite3-wal"),
        )
        before = {path: _file_state(path) for path in watched_paths}
        assert before[watched_paths[1]] is not None

        loaded = load_saved_text_profiles(root, ["fixture_a", "fixture_b"])

        assert [profile.profile_id for profile in loaded] == ["fixture_a", "fixture_b"]
        assert {path: _file_state(path) for path in watched_paths} == before
    finally:
        writer.close()


def test_saved_profile_snapshot_uses_one_transactional_view_during_a_writer_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _profiles = _application_data_dir(tmp_path, "fixture_a", "fixture_b")
    database_path = root / "application.sqlite3"
    writer = sqlite3.connect(database_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.commit()
    finally:
        writer.close()

    import plotloom.project_storage.application_profile_snapshot as snapshots

    real_connect = sqlite3.connect
    changed = False

    class ReadConnection:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self._connection = connection

        def execute(self, statement: str, parameters: tuple[Any, ...] = ()) -> Any:
            nonlocal changed
            result = self._connection.execute(statement, parameters)
            if statement.startswith("SELECT profiles.") and not changed:
                changed = True
                with real_connect(database_path) as update:
                    update.execute(
                        "UPDATE application_profiles SET revision = 2 "
                        "WHERE profile_id IN (?, ?)",
                        ("fixture_a", "fixture_b"),
                    )
            return result

        def rollback(self) -> None:
            self._connection.rollback()

        def close(self) -> None:
            self._connection.close()

    monkeypatch.setattr(
        snapshots.sqlite3,
        "connect",
        lambda *args, **kwargs: ReadConnection(real_connect(*args, **kwargs)),
    )
    snapshot = load_saved_text_profiles(root, ["fixture_a", "fixture_b"])

    assert changed is True
    assert [profile.profile_version for profile in snapshot] == [1, 1]
    assert [
        profile.profile_version
        for profile in load_saved_text_profiles(root, ["fixture_a", "fixture_b"])
    ] == [2, 2]


def test_saved_profile_snapshot_reads_consistently_while_a_rollback_writer_is_reserved(
    tmp_path: Path,
) -> None:
    root, _profiles = _application_data_dir(tmp_path, "fixture_a", "fixture_b")
    database_path = root / "application.sqlite3"
    writer = sqlite3.connect(database_path, timeout=1)
    try:
        assert writer.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() == "delete"
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            "UPDATE application_profiles SET revision = 2 "
            "WHERE profile_id IN (?, ?)",
            ("fixture_a", "fixture_b"),
        )
        started = time.monotonic()
        snapshot = load_saved_text_profiles(root, ["fixture_a", "fixture_b"])
        assert time.monotonic() - started < 1
        assert [profile.profile_version for profile in snapshot] == [1, 1]
        writer.commit()
    finally:
        writer.close()

    assert [
        profile.profile_version
        for profile in load_saved_text_profiles(root, ["fixture_a", "fixture_b"])
    ] == [2, 2]
