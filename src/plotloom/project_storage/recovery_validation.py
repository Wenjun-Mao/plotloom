"""Read-only validation for the portable project-folder recovery boundary."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import sqlite3
from typing import Any, Iterable

from sqlalchemy import create_engine

from ..domain import contains_secret_value, is_secret_setting_name
from ..persistence.schema import Base, PROJECT_TEXT_PIPELINE_TABLE_NAMES
from .format import (
    PROJECT_DATABASE_RELATIVE_PATH,
    PROJECT_MANIFEST_FILENAME,
    ProjectManifest,
    ProjectStorageCorruptionError,
    _read_json,
)
from .recovery_control import RECOVERY_CONTROL_FILENAME, validate_recovery_control
from .snapshot_files import (
    _published_files,
    _safe_regular,
    _sha256_path,
    _source_file,
)
from .snapshot_contract import ProjectSnapshotManifest, SnapshotFile, _Payload
from .video_candidate_transition import expected_project_schema_objects


_ASSET_PREFIX = PurePosixPath("assets")


def _contains_forbidden_database_setting(value: Any) -> bool:
    """Reject configuration-shaped secrets without treating story node `key` as one."""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(character for character in str(key).lower() if character.isalnum())
            if normalized != "key" and is_secret_setting_name(key):
                return True
            if _contains_forbidden_database_setting(child):
                return True
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_database_setting(child) for child in value)
    return False


def database_connection(path: Path) -> sqlite3.Connection:
    _safe_regular(path, label="project database")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA query_only=ON")
    return connection


def _schema_objects(connection: object) -> list[tuple[str, str, str, str | None]]:
    query = getattr(connection, "exec_driver_sql", None)
    rows = (
        query(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
        if query is not None
        else connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
    )
    return [
        (str(kind), str(name), str(table_name), sql if isinstance(sql, str) else None)
        for kind, name, table_name, sql in rows
    ]


def _expected_schema_objects() -> list[tuple[str, str, str, str | None]]:
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(
            engine,
            tables=[Base.metadata.tables[name] for name in PROJECT_TEXT_PIPELINE_TABLE_NAMES],
        )
        with engine.connect() as connection:
            return _schema_objects(connection)
    finally:
        engine.dispose()


_EXPECTED_SCHEMA_OBJECTS = _expected_schema_objects()
_PRE_SELECTION_SCHEMA_OBJECTS = expected_project_schema_objects(
    include_video_candidate_selection=False
)


def _assert_schema_contract(connection: sqlite3.Connection) -> None:
    """Reject schema objects before reading any application-controlled table."""

    actual = _schema_objects(connection)
    if actual == list(_PRE_SELECTION_SCHEMA_OBJECTS):
        raise ProjectStorageCorruptionError(
            "project snapshot requires a writable video selection transition before restore"
        )
    prohibited = {kind for kind, _name, _table, _sql in actual} - {"table", "index"}
    if prohibited or actual != _EXPECTED_SCHEMA_OBJECTS:
        raise ProjectStorageCorruptionError(
            "project database schema is unsupported by this restore format"
        )


def _database_strings(connection: sqlite3.Connection) -> Iterable[str]:
    """Read only known, prevalidated tables; names never come from imported SQL."""

    for table in sorted(PROJECT_TEXT_PIPELINE_TABLE_NAMES):
        for row in connection.execute(f'SELECT * FROM "{table}"'):
            for value in row:
                if isinstance(value, str):
                    yield value


def assert_database_contract(path: Path, manifest: ProjectManifest) -> None:
    """Validate integrity, exact schema, identity, and secret-free contents."""

    try:
        connection = database_connection(path)
        try:
            _assert_schema_contract(connection)
            integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
            foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
            project_rows = list(connection.execute("SELECT id FROM v2_projects"))
            state_rows = list(
                connection.execute(
                    "SELECT state FROM v2_project_operational_states WHERE project_id = ?",
                    (manifest.project_id,),
                )
            )
            values = list(_database_strings(connection))
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ProjectStorageCorruptionError(
            "project database is not a supported SQLite project schema"
        ) from error
    if integrity != ["ok"] or foreign_keys:
        raise ProjectStorageCorruptionError(
            "project database failed integrity or foreign-key verification"
        )
    if project_rows != [(manifest.project_id,)] or len(state_rows) != 1:
        raise ProjectStorageCorruptionError(
            "project database identity does not match its manifest"
        )
    for value in values:
        parsed: Any = value
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            pass
        if contains_secret_value(parsed) or _contains_forbidden_database_setting(parsed):
            raise ProjectStorageCorruptionError(
                "project database contains forbidden secret material"
            )


def database_state(path: Path, project_id: str) -> str:
    connection = database_connection(path)
    try:
        row = connection.execute(
            "SELECT state FROM v2_project_operational_states WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None or row[0] not in {"open", "closed"}:
        raise ProjectStorageCorruptionError("project database has an invalid operational state")
    return str(row[0])


def _asset_path(uri: object) -> PurePosixPath:
    if not isinstance(uri, str):
        raise ProjectStorageCorruptionError("managed asset has no confined storage URI")
    candidate = PurePosixPath(uri)
    if (
        candidate.is_absolute()
        or len(candidate.parts) != 3
        or candidate.parts[0] != _ASSET_PREFIX.name
        or len(candidate.parts[1]) != 2
        or len(candidate.parts[2]) != 64
        or candidate.parts[2][:2] != candidate.parts[1]
        or any(character not in "0123456789abcdef" for character in candidate.parts[2])
    ):
        raise ProjectStorageCorruptionError("managed asset has an unsupported storage URI")
    return candidate


def referenced_asset_paths(database: Path) -> set[PurePosixPath]:
    """Derive owned media from its typed storage columns, never story prose."""

    connection = database_connection(database)
    try:
        rows = list(
            connection.execute(
                "SELECT original_uri, original_hash, display_uri, display_hash "
                "FROM v2_managed_assets ORDER BY id"
            )
        )
    finally:
        connection.close()
    paths: set[PurePosixPath] = set()
    for original_uri, original_hash, display_uri, display_hash in rows:
        for uri, declared_hash in (
            (original_uri, original_hash),
            (display_uri, display_hash),
        ):
            path = _asset_path(uri)
            if path.name != declared_hash:
                raise ProjectStorageCorruptionError(
                    "managed asset storage URI does not match its declared hash"
                )
            paths.add(path)
    connection = database_connection(database)
    try:
        video_rows = list(
            connection.execute(
                "SELECT output_uri, output_hash FROM v2_video_jobs "
            "WHERE state != 'discard_pending' AND (output_uri IS NOT NULL OR output_hash IS NOT NULL)"
            )
        )
    finally:
        connection.close()
    for output_uri, output_hash in video_rows:
        path = _asset_path(output_uri)
        if path.name != output_hash:
            raise ProjectStorageCorruptionError(
                "video output storage URI does not match its declared hash"
            )
        paths.add(path)
    connection = database_connection(database)
    try:
        runtime_rows = list(
            connection.execute(
                "SELECT relative_path, content_hash, size_bytes "
                "FROM v2_run_artifact_blobs ORDER BY run_id, relative_path"
            )
        )
    finally:
        connection.close()
    for relative_path, content_hash, size_bytes in runtime_rows:
        path = _asset_path(relative_path)
        if path.name != content_hash or not isinstance(size_bytes, int) or size_bytes < 0:
            raise ProjectStorageCorruptionError(
                "runtime artifact storage row does not match its confined bytes"
            )
        paths.add(path)
    return paths


def published_run_directories(database: Path) -> set[str]:
    from datetime import datetime

    from .format import _utc_folder_timestamp

    connection = database_connection(database)
    try:
        rows = list(
            connection.execute(
                "SELECT id, created_at FROM v2_image_jobs "
                "WHERE state IN ('delivered', 'rejected')"
            )
        ) + list(
            connection.execute(
                "SELECT id, created_at FROM v2_character_reference_proposals "
                "WHERE state IN ('delivered', 'rejected')"
            )
        )
    finally:
        connection.close()
    result: set[str] = set()
    for identifier, created_at in rows:
        try:
            timestamp = datetime.fromisoformat(str(created_at))
        except ValueError as error:
            raise ProjectStorageCorruptionError(
                "published exchange has an invalid creation time"
            ) from error
        name = f"{_utc_folder_timestamp(timestamp)}__{identifier}"
        if "/" in name or "\\" in name:
            raise ProjectStorageCorruptionError("published exchange has an unsafe identity")
        result.add(name)
    return result


def payload_paths(root: Path, database: Path) -> list[PurePosixPath]:
    paths = {
        PurePosixPath(PROJECT_MANIFEST_FILENAME),
        PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH),
    }
    paths.update(referenced_asset_paths(database))
    for run_name in published_run_directories(database):
        paths.update(_published_files(root, run_name))
    if (root / RECOVERY_CONTROL_FILENAME).exists() or (root / RECOVERY_CONTROL_FILENAME).is_symlink():
        paths.add(PurePosixPath(RECOVERY_CONTROL_FILENAME))
    return sorted(paths, key=lambda item: item.as_posix())


def payload_inventory(root: Path, paths: Iterable[PurePosixPath]) -> dict[PurePosixPath, _Payload]:
    return {
        relative: _Payload(relative, *_sha256_path(_source_file(root, relative)))
        for relative in paths
    }


def assert_payload_inventory(
    root: Path, expected: dict[PurePosixPath, _Payload]
) -> None:
    actual = payload_inventory(root, expected)
    if actual != expected:
        raise ProjectStorageCorruptionError(
            "recovery payload hash changed after its frozen inventory was validated"
        )


def validate_snapshot_payloads(root: Path, manifest: ProjectSnapshotManifest) -> None:
    declared = {PurePosixPath(item.relative_path): item for item in manifest.files}
    required = {
        PurePosixPath(PROJECT_MANIFEST_FILENAME),
        PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH),
        PurePosixPath(RECOVERY_CONTROL_FILENAME),
    }
    if len(declared) != len(manifest.files):
        raise ProjectStorageCorruptionError("snapshot manifest contains duplicate file paths")
    if not required.issubset(declared):
        raise ProjectStorageCorruptionError("snapshot manifest omits required project files")
    try:
        on_disk_manifest = ProjectManifest.model_validate(
            _read_json(root / PROJECT_MANIFEST_FILENAME)
        )
    except ValueError as error:
        raise ProjectStorageCorruptionError("snapshot project manifest is unsupported") from error
    if on_disk_manifest != manifest.project_manifest:
        raise ProjectStorageCorruptionError(
            "snapshot project manifest does not match its declared identity"
        )
    frozen = {
        relative: _Payload(relative, item.content_hash, item.size_bytes)
        for relative, item in declared.items()
    }
    assert_payload_inventory(root, frozen)
    database = root / PROJECT_DATABASE_RELATIVE_PATH
    if declared[PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH)].content_hash != manifest.database_hash:
        raise ProjectStorageCorruptionError(
            "snapshot database hash does not match its manifest"
        )
    assert_database_contract(database, manifest.project_manifest)
    validate_recovery_control(
        root,
        database,
        manifest.project_id,
        required=True,
        snapshot=True,
    )
    if set(declared) != set(payload_paths(root, database)):
        raise ProjectStorageCorruptionError(
            "snapshot manifest does not exactly cover retained project bytes"
        )


def snapshot_inventory(manifest: ProjectSnapshotManifest) -> dict[PurePosixPath, _Payload]:
    return {
        PurePosixPath(item.relative_path): _Payload(
            PurePosixPath(item.relative_path), item.content_hash, item.size_bytes
        )
        for item in manifest.files
    }
