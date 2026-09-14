"""Bound project database composition and project-local admission guards."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER,
    Project,
    ProjectCreation,
    ProjectDuplicateResult,
    StageStatus,
    StartupRecoveryPlan,
    utc_now,
)
from ...exceptions import InvalidTransitionError, NotFoundError
from ..codec import stable_hash
from ..schema import GenerationRunRow, ProjectOperationalStateRow, ProjectRow, StageHeadRow
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
        self._recovered_run_ids: Callable[[], set[str]] = set
        self._recovery_operations_present: Callable[[], bool] = lambda: False
        super().__init__(
            database_url,
            create_schema=create_schema,
            sqlite_busy_timeout_ms=sqlite_busy_timeout_ms,
            schema_scope="project",
        )

    def _set_recovery_admission(
        self,
        *,
        recovered_run_ids: Callable[[], set[str]],
        recovery_operations_present: Callable[[], bool],
    ) -> None:
        """Install the project-home control without expanding this public API."""

        self._recovered_run_ids = recovered_run_ids
        self._recovery_operations_present = recovery_operations_present

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
            # The operational row is intentionally a separate table, so make
            # the project FK visible before inserting its first open receipt.
            session.flush()
            session.add(
                ProjectOperationalStateRow(
                    project_id=project.id,
                    state="open",
                    revision=1,
                    changed_at=project.created_at,
                )
            )
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

    def operational_state(self) -> tuple[str, int]:
        """Return the durable copy-safety state for this one project home."""

        with self._read() as session:
            row = session.get(ProjectOperationalStateRow, self.project_id)
            if row is None:
                raise InvalidTransitionError("project has no operational state")
            return row.state, row.revision

    def set_operational_state(self, *, expected_revision: int, state: str) -> tuple[str, int]:
        if state not in {"open", "closed"}:
            raise ValueError("project operational state must be open or closed")
        with self._write() as session:
            row = session.get(ProjectOperationalStateRow, self.project_id)
            if row is None:
                raise InvalidTransitionError("project has no operational state")
            if row.revision != expected_revision:
                raise InvalidTransitionError("project operational state is stale")
            if row.state == state:
                return row.state, row.revision
            row.state = state
            row.revision += 1
            row.changed_at = utc_now()
            return row.state, row.revision

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

    def reconcile_startup_jobs(self) -> StartupRecoveryPlan:
        """Never turn portable recovered work into an automatic replay."""

        if self._recovery_operations_present():
            return StartupRecoveryPlan()
        return super().reconcile_startup_jobs()

    def start_run(self, run_id: str):
        """Block both scheduler recovery and an explicit resume until acknowledged."""

        if run_id in self._recovered_run_ids():
            raise InvalidTransitionError(
                "recovery_required: restored unfinished work cannot be resumed"
            )
        return super().start_run(run_id)
