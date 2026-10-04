"""Resolve manifest identity separately from catalog admission/availability."""

from dataclasses import dataclass
from pathlib import Path

from .format import (
    PROJECT_MANIFEST_FILENAME,
    ProjectManifest,
    ProjectStorageCorruptionError,
    ProjectStorageError,
    _read_json,
    parse_project_manifest,
)


@dataclass(frozen=True)
class ProjectHome:
    """One project directory and its immutable manifest."""

    path: Path
    manifest: ProjectManifest


def find_project_home(outputs_root: Path, project_id: str) -> ProjectHome:
    # Catalog discovery intentionally hides unavailable homes. Known-ID requests
    # must instead reach their normal admission checks and preserve the reason.
    matches: list[ProjectHome] = []
    for candidate in sorted(outputs_root.iterdir(), key=lambda path: path.name):
        manifest_path = candidate / PROJECT_MANIFEST_FILENAME
        if (
            candidate.name.startswith(".")
            or candidate.is_symlink()
            or not candidate.is_dir()
            or manifest_path.is_symlink()
            or not manifest_path.is_file()
        ):
            continue
        try:
            raw = _read_json(manifest_path)
        except (ProjectStorageError, ValueError):
            continue
        if raw.get("projectId") != project_id and raw.get("project_id") != project_id:
            continue
        manifest = parse_project_manifest(raw)
        matches.append(ProjectHome(path=candidate.resolve(), manifest=manifest))
    if not matches:
        raise ProjectStorageError(f"project not found in outputs root: {project_id}")
    if len(matches) > 1:
        raise ProjectStorageCorruptionError(f"multiple project homes share identity: {project_id}")
    return matches[0]
