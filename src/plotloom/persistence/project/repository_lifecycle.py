"""Explicit lifecycle surface for one manifest-bound project."""

from __future__ import annotations

from ...domain import Project
from .lifecycle import ProjectLifecyclePersistence


class ProjectLifecycleRepository:
    """Expose only archive-state transitions owned by the project database."""

    def __init__(self, lifecycle: ProjectLifecyclePersistence) -> None:
        self._lifecycle = lifecycle

    def archive_project(
        self, project_id: str, expected_lifecycle_revision: int
    ) -> Project:
        return self._lifecycle.archive_project(
            project_id, expected_lifecycle_revision
        )

    def restore_project(
        self, project_id: str, expected_lifecycle_revision: int
    ) -> Project:
        return self._lifecycle.restore_project(
            project_id, expected_lifecycle_revision
        )
