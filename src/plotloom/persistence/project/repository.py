"""Bound project database composition and project-local admission guards."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import STAGE_ORDER, Project, ProjectCreation, ProjectDuplicateResult, StageStatus
from ...exceptions import InvalidTransitionError, NotFoundError
from ..codec import stable_hash
from ..schema import GenerationRunRow, ProjectRow, StageHeadRow
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from ..legacy_repository import SQLiteRepository


class ProjectSQLiteRepository(SQLiteRepository):
    """A one-project canonical repository with no application control tables.

    The pipeline and lifecycle runner keep their normal repository contract.
    This adapter supplies the missing ownership boundary: its schema excludes
    installation profiles/accounting and every project route is bound to the
    immutable project-home identity.
    """

    def __init__(
        self,
        database_url: str,
        *,
        project_id: str,
        create_schema: bool = True,
        sqlite_busy_timeout_ms: int = 1_000,
    ) -> None:
        if not project_id:
            raise ValueError("project_id is required for a project repository")
        self.project_id = project_id
        self._admitted_provider_snapshot_hash: str | None = None
        super().__init__(
            database_url,
            create_schema=create_schema,
            sqlite_busy_timeout_ms=sqlite_busy_timeout_ms,
            schema_scope="project",
        )

    @contextmanager
    def admit_provider_snapshot(self, provider_snapshot: dict[str, Any]) -> Iterator[None]:
        """Authorize one application-selected public profile for fresh work.

        The authorization is process-local and short lived.  The immutable
        public snapshot still belongs on each run; selection and credentials do
        not belong in the project database.
        """

        snapshot_hash = stable_hash(provider_snapshot)
        previous = self._admitted_provider_snapshot_hash
        self._admitted_provider_snapshot_hash = snapshot_hash
        try:
            yield
        finally:
            self._admitted_provider_snapshot_hash = previous

    def initialize_project(self, project: Project) -> Project:
        """Create the one project row selected by the immutable folder manifest."""

        if project.id != self.project_id:
            raise InvalidTransitionError("project repository identity does not match project initialization")
        with self._bootstrap_write() as session:
            existing = session.scalar(select(ProjectRow.id).limit(1))
            if existing is not None:
                raise InvalidTransitionError("project repository has already been initialized")
            row = ProjectRow(
                id=project.id,
                revision=project.revision,
                lifecycle_revision=project.lifecycle_revision,
                lifecycle_status=project.lifecycle_status.value,
                archived_at=project.archived_at,
                brief=project.brief.model_dump(mode="json", by_alias=False),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            session.add(row)
            for stage in STAGE_ORDER:
                session.add(
                    StageHeadRow(
                        id=f"{project.id}:{stage.value}",
                        project_id=project.id,
                        stage=stage.value,
                        status=StageStatus.MISSING.value,
                        revision=0,
                        entity_revision_id=None,
                        content_hash=None,
                        schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                        input_revisions={},
                        stale_reasons=[],
                        updated_at=project.updated_at,
                    )
                )
        return self.get_project(project.id)

    def create_project(self, *args: Any, **kwargs: Any) -> ProjectCreation:
        raise InvalidTransitionError(
            "project repositories are initialized only by their project-home manifest"
        )

    def duplicate_project(self, *args: Any, **kwargs: Any) -> ProjectDuplicateResult:
        raise InvalidTransitionError("a project repository cannot create a second project")

    def _project_row(self, session: Session, project_id: str) -> ProjectRow:
        if project_id != self.project_id:
            raise NotFoundError("project does not belong to this project repository")
        return SQLiteRepository._project_row(session, project_id)

    def _run_row(self, session: Session, run_id: str) -> GenerationRunRow:
        row = SQLiteRepository._run_row(session, run_id)
        if row.project_id != self.project_id:
            raise NotFoundError("generation run does not belong to this project repository")
        return row

    def _assert_new_run_profile_enabled(
        self,
        _session: Session,
        provider_snapshot: Mapping[str, Any],
    ) -> None:
        if self._admitted_provider_snapshot_hash != stable_hash(dict(provider_snapshot)):
            raise InvalidTransitionError(
                "project generation requires an application-admitted provider snapshot"
            )

