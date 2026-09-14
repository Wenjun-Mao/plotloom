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
        return ProjectStore.initialize(home, manifest, project)

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
                store = ProjectStore.open(candidate)
                store.close()
            except (ProjectStorageError, ValueError, SQLAlchemyError):
                continue
            homes.append(ProjectHome(path=candidate.resolve(), manifest=manifest))
        return homes

    def open(self, project_id: str) -> ProjectStore:
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
        return ProjectStore.open(matches[0].path)
