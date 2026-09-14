"""Verified portable snapshots and fail-closed project-folder restore.

The direct project-folder composition deliberately owns this at the filesystem
boundary.  It never delegates recovery to a generic directory copy: the
database is backed up at a committed point, the retained bytes are derived from
that point, and an untrusted incoming folder is fully validated before it is
made discoverable under ``outputs``.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
from typing import Any, Iterable
from uuid import uuid4

from ..domain import contains_secret_value, is_secret_setting_name
from ..persistence.schema import PROJECT_TEXT_PIPELINE_TABLE_NAMES
from .format import (
    PROJECT_DATABASE_RELATIVE_PATH,
    PROJECT_MANIFEST_FILENAME,
    ProjectManifest,
    ProjectStorageConflictError,
    ProjectStorageCorruptionError,
    ProjectStorageError,
    _canonical_json,
    _read_json,
    _require_real_directory,
    _utc_folder_timestamp,
    _write_new_file,
)
from .operational_state import ProjectBusyError
from .snapshot_files import (
    _copy_payload,
    _published_files,
    _safe_directory,
    _safe_regular,
    _sha256_path,
    _source_file,
)
from .snapshot_contract import (
    SNAPSHOT_FORMAT_VERSION,
    SNAPSHOT_MANIFEST_FILENAME,
    ProjectSnapshotManifest,
    ProjectSnapshotReceipt,
    SnapshotFile,
    _Payload,
)
_ASSET_URI = re.compile(r"assets/[0-9a-f]{2}/[0-9a-f]{64}")
_FORBIDDEN_PATH = re.compile(r"(?:file:|(?:^|[\s\"'])/(?:Users|home|tmp|var|private|Volumes)/)", re.IGNORECASE)


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


def _backup_database(source: Path, destination: Path) -> _Payload:
    _safe_regular(source, label="project database")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_connection = sqlite3.connect(source, check_same_thread=False)
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
            destination_connection.execute("PRAGMA journal_mode=DELETE")
            destination_connection.commit()
        finally:
            destination_connection.close()
            source_connection.close()
    except sqlite3.Error as error:
        destination.unlink(missing_ok=True)
        raise ProjectStorageCorruptionError("SQLite backup could not reach a committed point") from error
    digest, size = _sha256_path(destination)
    return _Payload(PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH), digest, size)


def _database_connection(path: Path) -> sqlite3.Connection:
    _safe_regular(path, label="project database")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA query_only=ON")
    return connection


def _database_strings(connection: sqlite3.Connection) -> Iterable[str]:
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )]
    for table in tables:
        for row in connection.execute(f'SELECT * FROM "{table}"'):
            for value in row:
                if isinstance(value, str):
                    yield value


def _assert_database_contract(path: Path, manifest: ProjectManifest) -> None:
    try:
        connection = _database_connection(path)
        try:
            integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
            foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            project_rows = list(connection.execute("SELECT id FROM v2_projects"))
            state_rows = list(connection.execute(
                "SELECT state FROM v2_project_operational_states WHERE project_id = ?", (manifest.project_id,)
            ))
            values = list(_database_strings(connection))
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ProjectStorageCorruptionError("project database is not a supported SQLite project schema") from error
    if integrity != ["ok"] or foreign_keys:
        raise ProjectStorageCorruptionError("project database failed integrity or foreign-key verification")
    if tables != PROJECT_TEXT_PIPELINE_TABLE_NAMES:
        raise ProjectStorageCorruptionError("project database schema is unsupported by this restore format")
    if project_rows != [(manifest.project_id,)] or len(state_rows) != 1:
        raise ProjectStorageCorruptionError("project database identity does not match its manifest")
    for value in values:
        parsed: Any = value
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            pass
        # Project canonical payloads legitimately use domain names such as
        # ``key``.  Configuration-shaped fields are rejected at their owning
        # authoring/profile boundaries; recovery must not reinterpret arbitrary
        # story JSON as provider configuration. Recognizable credential values
        # remain forbidden everywhere in the database.
        if contains_secret_value(parsed) or _contains_forbidden_database_setting(parsed):
            raise ProjectStorageCorruptionError("project database contains forbidden secret material")
        if _FORBIDDEN_PATH.search(value):
            raise ProjectStorageCorruptionError("project database contains a non-portable absolute file dependency")


def _database_state(path: Path, project_id: str) -> str:
    connection = _database_connection(path)
    try:
        row = connection.execute(
            "SELECT state FROM v2_project_operational_states WHERE project_id = ?", (project_id,)
        ).fetchone()
    finally:
        connection.close()
    if row is None or row[0] not in {"open", "closed"}:
        raise ProjectStorageCorruptionError("project database has an invalid operational state")
    return str(row[0])


def _referenced_asset_paths(database: Path) -> set[PurePosixPath]:
    connection = _database_connection(database)
    try:
        values = list(_database_strings(connection))
    finally:
        connection.close()
    paths: set[PurePosixPath] = set()
    for value in values:
        paths.update(PurePosixPath(match) for match in _ASSET_URI.findall(value))
    return paths


def _published_run_directories(database: Path) -> set[str]:
    connection = _database_connection(database)
    try:
        rows = list(connection.execute(
            "SELECT id, created_at FROM v2_image_jobs WHERE state IN ('delivered', 'rejected')"
        )) + list(connection.execute(
            "SELECT id, created_at FROM v2_character_reference_proposals WHERE state IN ('delivered', 'rejected')"
        ))
    finally:
        connection.close()
    result: set[str] = set()
    for identifier, created_at in rows:
        try:
            timestamp = datetime.fromisoformat(str(created_at))
        except ValueError as error:
            raise ProjectStorageCorruptionError("published exchange has an invalid creation time") from error
        name = f"{_utc_folder_timestamp(timestamp)}__{identifier}"
        if "/" in name or "\\" in name:
            raise ProjectStorageCorruptionError("published exchange has an unsafe identity")
        result.add(name)
    return result


def _payload_paths(root: Path, database: Path) -> list[PurePosixPath]:
    paths = {PurePosixPath(PROJECT_MANIFEST_FILENAME), PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH)}
    paths.update(_referenced_asset_paths(database))
    for run_name in _published_run_directories(database):
        paths.update(_published_files(root, run_name))
    return sorted(paths, key=lambda item: item.as_posix())


def _validate_payloads(root: Path, manifest: ProjectSnapshotManifest) -> None:
    declared = {PurePosixPath(item.relative_path): item for item in manifest.files}
    required = {PurePosixPath(PROJECT_MANIFEST_FILENAME), PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH)}
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
        raise ProjectStorageCorruptionError("snapshot project manifest does not match its declared identity")
    for relative, file_entry in declared.items():
        candidate = _source_file(root, relative)
        digest, size = _sha256_path(candidate)
        if digest != file_entry.content_hash or size != file_entry.size_bytes:
            raise ProjectStorageCorruptionError("snapshot file hash does not match its manifest")
    database = root / PROJECT_DATABASE_RELATIVE_PATH
    if declared[PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH)].content_hash != manifest.database_hash:
        raise ProjectStorageCorruptionError("snapshot database hash does not match its manifest")
    _assert_database_contract(database, manifest.project_manifest)
    expected = set(_payload_paths(root, database))
    if set(declared) != expected:
        raise ProjectStorageCorruptionError("snapshot manifest does not exactly cover retained project bytes")


def _read_snapshot(root: Path) -> ProjectSnapshotManifest:
    manifest_path = root / SNAPSHOT_MANIFEST_FILENAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProjectStorageCorruptionError("snapshot has no regular recovery manifest")
    try:
        manifest = ProjectSnapshotManifest.model_validate(_read_json(manifest_path))
    except ValueError as error:
        raise ProjectStorageCorruptionError("snapshot manifest is unsupported") from error
    if manifest.project_id != manifest.project_manifest.project_id:
        raise ProjectStorageCorruptionError("snapshot identity does not match its project manifest")
    _validate_payloads(root, manifest)
    return manifest


def _private_directory(parent: Path, prefix: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink():
        raise ProjectStorageConfinementError("recovery private root must not be a symlink")
    path = parent / f".{prefix}-{uuid4().hex}"
    path.mkdir(mode=0o700)
    return path


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class ProjectRecoveryService:
    """Create verified snapshots and restore only validated portable folders."""

    def __init__(self, outputs_root: Path, registry: Any) -> None:
        self.outputs_root = _require_real_directory(outputs_root, label="outputs root")
        self.registry = registry

    def create_snapshot(self, project_id: str) -> ProjectSnapshotReceipt:
        temporary: Path | None = None
        try:
            store = self.registry._exclusive_store(project_id)
            try:
                blockers = self._specialist_blockers(store)
                if blockers:
                    raise ProjectBusyError("project_busy: " + ", ".join(blockers))
                snapshot_parent = self.outputs_root / ".snapshots" / project_id
                temporary = _private_directory(snapshot_parent, "snapshot")
                copied: list[_Payload] = []
                copied.append(_copy_payload(store.home, temporary, PurePosixPath(PROJECT_MANIFEST_FILENAME)))
                copied.append(_backup_database(store.database_path, temporary / PROJECT_DATABASE_RELATIVE_PATH))
                database = temporary / PROJECT_DATABASE_RELATIVE_PATH
                _assert_database_contract(database, store.manifest)
                for relative in _payload_paths(store.home, database):
                    if relative in {PurePosixPath(PROJECT_MANIFEST_FILENAME), PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH)}:
                        continue
                    copied.append(_copy_payload(store.home, temporary, relative))
                snapshot_id = str(uuid4())
                manifest = ProjectSnapshotManifest(
                    snapshot_id=snapshot_id,
                    project_id=project_id,
                    created_at=datetime.now(timezone.utc),
                    project_manifest=store.manifest,
                    database_hash=next(item.content_hash for item in copied if item.relative_path == PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH)),
                    files=[SnapshotFile(relative_path=item.relative_path.as_posix(), content_hash=item.content_hash, size_bytes=item.size_bytes) for item in sorted(copied, key=lambda item: item.relative_path.as_posix())],
                )
                _write_new_file(
                    temporary / SNAPSHOT_MANIFEST_FILENAME,
                    (_canonical_json(manifest.model_dump(mode="json", by_alias=True)) + "\n").encode("utf-8"),
                )
                _validate_payloads(temporary, manifest)
                final = snapshot_parent / f"{_utc_folder_timestamp(manifest.created_at)}__{snapshot_id}"
                if final.exists():
                    raise ProjectStorageConflictError("snapshot destination already exists")
                _sync_directory(temporary)
                os.replace(temporary, final)
                _sync_directory(snapshot_parent)
                temporary = None
                return ProjectSnapshotReceipt(
                    operation_id=snapshot_id,
                    snapshot_id=snapshot_id,
                    project_id=project_id,
                    location=str(final),
                    manifest=manifest,
                )
            finally:
                store.close()
        finally:
            if temporary is not None:
                shutil.rmtree(temporary, ignore_errors=True)

    def snapshot_status(self, project_id: str, snapshot_id: str) -> ProjectSnapshotReceipt:
        parent = self.outputs_root / ".snapshots" / project_id
        if parent.is_symlink() or not parent.is_dir():
            raise ProjectStorageError("snapshot not found")
        matches: list[tuple[Path, ProjectSnapshotManifest]] = []
        for candidate in parent.iterdir():
            if candidate.name.startswith(".") or candidate.is_symlink() or not candidate.is_dir():
                continue
            try:
                manifest = _read_snapshot(candidate)
            except ProjectStorageError:
                continue
            if manifest.snapshot_id == snapshot_id and manifest.project_id == project_id:
                matches.append((candidate, manifest))
        if len(matches) != 1:
            raise ProjectStorageError("snapshot not found")
        location, manifest = matches[0]
        return ProjectSnapshotReceipt(
            operation_id=snapshot_id, snapshot_id=snapshot_id, project_id=project_id,
            location=str(location), manifest=manifest,
        )

    def restore(self, source: Path) -> Path:
        root = _safe_directory(source.expanduser(), label="restore source")
        incoming_snapshot = root / SNAPSHOT_MANIFEST_FILENAME
        if incoming_snapshot.exists():
            snapshot = _read_snapshot(root)
            manifest = snapshot.project_manifest
            files = [PurePosixPath(item.relative_path) for item in snapshot.files]
        else:
            manifest_path = root / PROJECT_MANIFEST_FILENAME
            try:
                manifest = ProjectManifest.model_validate(_read_json(manifest_path))
            except ValueError as error:
                raise ProjectStorageCorruptionError("restore source has no supported project manifest") from error
            database = root / PROJECT_DATABASE_RELATIVE_PATH
            _assert_database_contract(database, manifest)
            if _database_state(database, manifest.project_id) != "closed":
                raise ProjectBusyError("project_busy: a direct folder must be explicitly closed before restore")
            files = _payload_paths(root, database)
        if any(home.manifest.project_id == manifest.project_id for home in self.registry.discover()):
            raise ProjectStorageConflictError("restore would overwrite an existing project identity")
        final = self.outputs_root / f"{_utc_folder_timestamp(manifest.created_at)}__{manifest.project_id}"
        if final.exists():
            raise ProjectStorageConflictError("restore destination already exists")
        temporary = _private_directory(self.outputs_root, "restore")
        try:
            for relative in files:
                _copy_payload(root, temporary, relative)
            copied_manifest = ProjectManifest.model_validate(_read_json(temporary / PROJECT_MANIFEST_FILENAME))
            if copied_manifest != manifest:
                raise ProjectStorageCorruptionError("restore manifest changed while it was copied")
            _assert_database_contract(temporary / PROJECT_DATABASE_RELATIVE_PATH, manifest)
            expected = set(_payload_paths(temporary, temporary / PROJECT_DATABASE_RELATIVE_PATH))
            if set(files) != expected:
                raise ProjectStorageCorruptionError("restore source omits referenced project bytes")
            _sync_directory(temporary)
            os.replace(temporary, final)
            _sync_directory(self.outputs_root)
            temporary = None
            return final
        finally:
            if temporary is not None:
                shutil.rmtree(temporary, ignore_errors=True)

    @staticmethod
    def _specialist_blockers(store: Any) -> list[str]:
        image_busy = [job for job in store.repository.list_image_jobs(store.manifest.project_id) if job.get("state") not in {"delivered", "rejected"}]
        reference_busy = [proposal for proposal in store.repository.list_character_reference_proposals(store.manifest.project_id) if proposal.get("state") not in {"delivered", "rejected"}]
        return (["image_publication_active"] if image_busy else []) + (["character_reference_publication_active"] if reference_busy else [])
