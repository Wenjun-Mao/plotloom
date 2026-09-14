"""Filesystem discovery and opening of project homes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from ..domain import Project, ProjectBrief
from .format import (
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
from .project_handle import ProjectStore
from .operational_state import (
    ProjectAccessLease,
    ProjectBusyError,
    ProjectClosedError,
    close_blockers,
)


@dataclass(frozen=True)
class ProjectHome:
    """One discovered project directory and its immutable manifest."""

    path: Path
    manifest: ProjectManifest


class ProjectDirectoryRegistry:
    """Rebuildable project catalog derived only from validated manifests."""

    def __init__(self, outputs_root: Path) -> None:
        self.outputs_root = _require_real_directory(outputs_root, label="outputs root")

    def _new_home(self, project: Project) -> Path:
        directory_name = f"{_utc_folder_timestamp(project.created_at)}__{project.id}"
        home = self.outputs_root / directory_name
        try:
            home.mkdir(mode=0o700)
        except FileExistsError as error:
            raise ProjectStorageConflictError(
                f"project home already exists: {directory_name}"
            ) from error
        return home

    def create(self, brief: ProjectBrief) -> ProjectStore:
        project = Project(brief=brief)
        home = self._new_home(project)
        manifest = ProjectManifest(project_id=project.id, created_at=project.created_at)
        _write_new_file(
            home / PROJECT_MANIFEST_FILENAME,
            (
                _canonical_json(manifest.model_dump(mode="json", by_alias=True)) + "\n"
            ).encode("utf-8"),
        )
        lease = ProjectAccessLease.acquire(home, mode="shared")
        try:
            return ProjectStore.initialize(
                home, manifest, project, access_lease=lease
            )
        except BaseException:
            lease.close()
            raise

    def discover(self) -> list[ProjectHome]:
        homes: list[ProjectHome] = []
        for candidate in sorted(
            self.outputs_root.iterdir(), key=lambda path: path.name
        ):
            if (
                candidate.name.startswith(".")
                or candidate.is_symlink()
                or not candidate.is_dir()
            ):
                continue
            manifest_path = candidate / PROJECT_MANIFEST_FILENAME
            if manifest_path.is_symlink() or not manifest_path.is_file():
                continue
            try:
                manifest = ProjectManifest.model_validate(_read_json(manifest_path))
                lease = ProjectAccessLease.acquire(
                    candidate, mode="shared", create=False
                )
                store = ProjectStore.open(
                    candidate, read_only=True, access_lease=lease
                )
                store.close()
            except (ProjectStorageError, ValueError, SQLAlchemyError):
                continue
            homes.append(ProjectHome(path=candidate.resolve(), manifest=manifest))
        return homes

    def open(self, project_id: str) -> ProjectStore:
        """Open an admitted shared handle; closed homes never reopen implicitly."""

        home = self._project_home(project_id)
        lease = ProjectAccessLease.acquire(home.path, mode="shared")
        try:
            store = ProjectStore.open(
                home.path, defer_wal=True, access_lease=lease
            )
            state, _revision = store.repository.operational_state()
            if state != "open":
                store.close()
                raise ProjectClosedError("project_closed: reopen it explicitly before editing")
            store.repository.enable_sqlite_wal()
            return store
        except BaseException:
            if lease.descriptor >= 0:
                lease.close()
            raise

    def inspect(self, project_id: str) -> ProjectStore:
        """Open a shared read handle without changing closed-project admission."""

        home = self._project_home(project_id)
        lease = ProjectAccessLease.acquire(
            home.path, mode="shared", create=False
        )
        try:
            return ProjectStore.open(
                home.path, read_only=True, access_lease=lease
            )
        except BaseException:
            lease.close()
            raise

    def close_project(self, project_id: str) -> int:
        """Quiesce one folder, checkpoint SQLite, then deny future admission."""

        store = self._exclusive_store(project_id)
        try:
            state, revision = store.repository.operational_state()
            if state == "open":
                blockers = close_blockers(store)
                if blockers:
                    raise ProjectBusyError(
                        "project_busy: " + ", ".join(blockers)
                    )
                _state, revision = store.repository.set_operational_state(
                    expected_revision=revision, state="closed"
                )
            # WAL checkpoint happens before the repository/lease are released;
            # no sidecar can race the successful close transition.
            with store.repository.engine.connect() as connection:
                checkpoint = connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)").one()
            if checkpoint[0] != 0 or checkpoint[1] != checkpoint[2]:
                if state == "open":
                    store.repository.set_operational_state(
                        expected_revision=revision, state="open"
                    )
                raise ProjectBusyError("project_busy: SQLite checkpoint did not quiesce")
            return revision
        finally:
            store.close()

    def reopen_project(self, project_id: str) -> int:
        """Explicitly reopen a closed folder without dispatching or replaying work."""

        store = self._exclusive_store(project_id)
        try:
            state, revision = store.repository.operational_state()
            if state == "open":
                return revision
            _state, revision = store.repository.set_operational_state(
                expected_revision=revision, state="open"
            )
            return revision
        finally:
            store.close()

    def _project_home(self, project_id: str) -> ProjectHome:
        matches = [
            home for home in self.discover() if home.manifest.project_id == project_id
        ]
        if not matches:
            raise ProjectStorageError(
                f"project not found in outputs root: {project_id}"
            )
        if len(matches) > 1:
            raise ProjectStorageCorruptionError(
                f"multiple project homes share identity: {project_id}"
            )
        return matches[0]

    def _exclusive_store(self, project_id: str) -> ProjectStore:
        home = self._project_home(project_id)
        lease = ProjectAccessLease.acquire(home.path, mode="exclusive")
        try:
            return ProjectStore.open(home.path, access_lease=lease)
        except BaseException:
            lease.close()
            raise
