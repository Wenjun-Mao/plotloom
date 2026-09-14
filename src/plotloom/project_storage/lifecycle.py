"""Folder lifecycle orchestration over project-local and application-owned state."""

from __future__ import annotations

from ..domain import Project, ProjectDuplicateResult
from ..persistence.codec import stable_hash
from .application_store import ApplicationStore
from .registry import ProjectDirectoryRegistry


class ProjectFolderLifecycleService:
    """Route lifecycle actions without reviving the retained shared repository."""

    def __init__(
        self, registry: ProjectDirectoryRegistry, application: ApplicationStore
    ) -> None:
        self._registry = registry
        self._application = application

    def archive(
        self, project_id: str, *, expected_lifecycle_revision: int
    ) -> Project:
        return self._registry.archive_project(
            project_id, expected_lifecycle_revision=expected_lifecycle_revision
        )

    def restore(
        self, project_id: str, *, expected_lifecycle_revision: int
    ) -> Project:
        return self._registry.restore_project(
            project_id, expected_lifecycle_revision=expected_lifecycle_revision
        )

    def duplicate(
        self,
        project_id: str,
        *,
        expected_lifecycle_revision: int,
        title: str | None,
        idempotency_key: str | None,
    ) -> ProjectDuplicateResult:
        normalized_title = title.strip() if title is not None else None
        if normalized_title == "":
            raise ValueError("duplicate title must not be blank")
        if idempotency_key is None:
            from ..domain import new_id, utc_now

            return self._registry.duplicate_project(
                project_id,
                expected_lifecycle_revision=expected_lifecycle_revision,
                target_project_id=new_id(),
                target_created_at=utc_now(),
                title=normalized_title,
            )
        reservation = self._application.project_lifecycle.reserve_duplicate(
            key=idempotency_key,
            fingerprint=stable_hash(
                {
                    "projectId": project_id,
                    "expectedLifecycleRevision": expected_lifecycle_revision,
                    "title": normalized_title,
                }
            ),
            source_project_id=project_id,
        )
        if reservation.complete:
            return self._registry.replay_duplicate(
                reservation.target_project_id,
                copied_through=reservation.copied_through,
                omitted_stages=reservation.omitted_stages,
            )
        result = self._registry.duplicate_project(
            project_id,
            expected_lifecycle_revision=expected_lifecycle_revision,
            target_project_id=reservation.target_project_id,
            target_created_at=reservation.target_created_at,
            title=normalized_title,
        )
        self._application.project_lifecycle.complete_duplicate(
            reservation,
            copied_through=(
                result.copied_through.value if result.copied_through is not None else None
            ),
            omitted_stages=tuple(stage.value for stage in result.omitted_stages),
        )
        return result

    def permanently_delete(
        self,
        project_id: str,
        *,
        expected_lifecycle_revision: int,
        confirmation_title: str,
    ) -> None:
        self._registry.permanently_delete_project(
            project_id,
            expected_lifecycle_revision=expected_lifecycle_revision,
            confirmation_title=confirmation_title,
        )
        self._application.project_lifecycle.forget_project_run_routes(project_id)
        self._application.project_lifecycle.forget_project(project_id)
