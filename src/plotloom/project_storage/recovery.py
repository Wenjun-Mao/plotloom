"""Verified portable snapshots and fail-closed project-folder restore.

The direct project-folder composition deliberately owns this at the filesystem
boundary.  It never delegates recovery to a generic directory copy: the
database is backed up at a committed point, the retained bytes are derived from
that point, and an untrusted incoming folder is fully validated before it is
made discoverable under ``outputs``.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
from typing import Any
from uuid import uuid4

from .format import (
    PROJECT_DATABASE_RELATIVE_PATH,
    PROJECT_MANIFEST_FILENAME,
    ProjectManifest,
    ProjectStorageConflictError,
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    ProjectStorageError,
    _canonical_json,
    _read_json,
    _require_real_directory,
    _utc_folder_timestamp,
    _write_new_file,
)
from .operational_state import (
    ProjectAccessLease,
    ProjectBusyError,
    cast_publication_blockers,
    source_outline_publication_blockers,
)
from .recovery_control import (
    ProjectRecoveryControl,
    acknowledge_recovery_control,
    capture_recovery_control,
    write_snapshot_recovery_control,
)
from .recovery_validation import (
    assert_database_contract,
    assert_payload_inventory,
    database_state,
    payload_inventory,
    payload_paths,
    snapshot_inventory,
    validate_snapshot_payloads,
)
from .snapshot_files import (
    _assert_closed_project_tree,
    _assert_snapshot_tree,
    _copy_payload,
    _safe_directory,
    _safe_regular,
    _sha256_path,
)
from .snapshot_contract import (
    SNAPSHOT_FORMAT_VERSION,
    SNAPSHOT_MANIFEST_FILENAME,
    ProjectSnapshotManifest,
    ProjectSnapshotReceipt,
    SnapshotFile,
    _Payload,
)


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
    declared = [PurePosixPath(item.relative_path) for item in manifest.files]
    _assert_snapshot_tree(root, [*declared, PurePosixPath(SNAPSHOT_MANIFEST_FILENAME)])
    validate_snapshot_payloads(root, manifest)
    return manifest


def _private_directory(parent: Path, prefix: str, *, confinement_root: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink():
        raise ProjectStorageConfinementError("recovery private root must not be a symlink")
    resolved_parent = parent.resolve()
    resolved_root = confinement_root.resolve()
    if resolved_parent != resolved_root and resolved_root not in resolved_parent.parents:
        raise ProjectStorageConfinementError(
            "recovery private root escapes the outputs directory"
        )
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
                temporary = _private_directory(
                    snapshot_parent, "snapshot", confinement_root=self.outputs_root
                )
                copied: list[_Payload] = []
                copied.append(_copy_payload(store.home, temporary, PurePosixPath(PROJECT_MANIFEST_FILENAME)))
                copied.append(_backup_database(store.database_path, temporary / PROJECT_DATABASE_RELATIVE_PATH))
                database = temporary / PROJECT_DATABASE_RELATIVE_PATH
                assert_database_contract(database, store.manifest)
                for relative in payload_paths(store.home, database):
                    if relative in {
                        PurePosixPath(PROJECT_MANIFEST_FILENAME),
                        PurePosixPath(PROJECT_DATABASE_RELATIVE_PATH),
                        PurePosixPath("recovery.json"),
                    }:
                        continue
                    copied.append(_copy_payload(store.home, temporary, relative))
                write_snapshot_recovery_control(
                    temporary, capture_recovery_control(database, project_id)
                )
                copied.append(
                    _Payload(
                        PurePosixPath("recovery.json"),
                        *_sha256_path(temporary / "recovery.json"),
                    )
                )
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
                _assert_snapshot_tree(
                    temporary,
                    [
                        *(item.relative_path for item in copied),
                        PurePosixPath(SNAPSHOT_MANIFEST_FILENAME),
                    ],
                )
                validate_snapshot_payloads(temporary, manifest)
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
        source_lease: ProjectAccessLease | None = None
        temporary: Path | None = None
        try:
            if incoming_snapshot.exists() or incoming_snapshot.is_symlink():
                snapshot = _read_snapshot(root)
                manifest = snapshot.project_manifest
                files = [PurePosixPath(item.relative_path) for item in snapshot.files]
                frozen_inventory = snapshot_inventory(snapshot)
                control_required = True
            else:
                # A closed direct project remains an active local filesystem
                # object. Hold its existing cross-process barrier from source
                # validation through copying so no supported opener can race.
                source_lease = ProjectAccessLease.acquire(root, mode="exclusive")
                manifest_path = root / PROJECT_MANIFEST_FILENAME
                try:
                    manifest = ProjectManifest.model_validate(_read_json(manifest_path))
                except ValueError as error:
                    raise ProjectStorageCorruptionError("restore source has no supported project manifest") from error
                database = root / PROJECT_DATABASE_RELATIVE_PATH
                assert_database_contract(database, manifest)
                if database_state(database, manifest.project_id) != "closed":
                    raise ProjectBusyError("project_busy: a direct folder must be explicitly closed before restore")
                files = payload_paths(root, database)
                _assert_closed_project_tree(root, files)
                from .recovery_control import validate_recovery_control

                validate_recovery_control(
                    root,
                    database,
                    manifest.project_id,
                    required=False,
                    snapshot=False,
                )
                frozen_inventory = payload_inventory(root, files)
                control_required = PurePosixPath("recovery.json") in frozen_inventory
            if any(home.manifest.project_id == manifest.project_id for home in self.registry.discover()):
                raise ProjectStorageConflictError("restore would overwrite an existing project identity")
            final = self.outputs_root / f"{_utc_folder_timestamp(manifest.created_at)}__{manifest.project_id}"
            if final.exists():
                raise ProjectStorageConflictError("restore destination already exists")
            temporary = _private_directory(
                self.outputs_root, "restore", confinement_root=self.outputs_root
            )
            for relative in files:
                copied = _copy_payload(root, temporary, relative)
                if copied != frozen_inventory[relative]:
                    raise ProjectStorageCorruptionError(
                        "restore source changed while its frozen payload was copied"
                    )
            _assert_snapshot_tree(temporary, files)
            assert_payload_inventory(temporary, frozen_inventory)
            copied_manifest = ProjectManifest.model_validate(_read_json(temporary / PROJECT_MANIFEST_FILENAME))
            if copied_manifest != manifest:
                raise ProjectStorageCorruptionError("restore manifest changed while it was copied")
            destination_database = temporary / PROJECT_DATABASE_RELATIVE_PATH
            assert_database_contract(destination_database, manifest)
            from .recovery_control import validate_recovery_control

            validate_recovery_control(
                temporary,
                destination_database,
                manifest.project_id,
                required=control_required,
                snapshot=False,
            )
            expected = set(payload_paths(temporary, destination_database))
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
            if source_lease is not None:
                source_lease.close()

    def acknowledge_recovery(self, project_id: str) -> ProjectRecoveryControl:
        """Acknowledge restored work without dispatching or changing history."""

        store = self.registry._exclusive_store(project_id)
        try:
            return acknowledge_recovery_control(store.home, project_id)
        finally:
            store.close()

    @staticmethod
    def _specialist_blockers(store: Any) -> list[str]:
        image_busy = [job for job in store.media.list_image_jobs(store.manifest.project_id) if job.get("state") not in {"delivered", "rejected", "cancelled"}]
        reference_busy = [proposal for proposal in store.media.list_character_reference_proposals(store.manifest.project_id) if proposal.get("state") not in {"delivered", "rejected"}]
        return (
            (["image_publication_active"] if image_busy else [])
            + (["character_reference_publication_active"] if reference_busy else [])
            + source_outline_publication_blockers(store)
            + cast_publication_blockers(store)
        )
