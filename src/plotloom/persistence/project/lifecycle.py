from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER, AuthoringDraft, AuthoringDraftScope, DialogueTimingProfile,
    EntityRevision, GateEvaluation, GateEvidence, GateResult, InitialStage,
    LatestRunSummary, Project, ProjectBrief, ProjectCreation, ProjectDuplicateResult,
    ProjectLifecycleStatus, ProjectSummary, StageEnvelope, StageHead, StageName,
    StagePayload, StageStatus, downstream_stages, new_id, stage_payload_model,
    utc_now, upstream_stages, validate_initial_stage_prefix,
)
from ...exceptions import (
    IdempotencyConflictError, InvalidTransitionError, NotFoundError, ProjectBusyError,
    ProjectManagedAssetsPresentError, RevisionConflictError, SchemaResetRequiredError,
    StagePrerequisiteError,
)
from ...validation import STORYBOARD_GATE_SET_VERSION, validate_stage_payload
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ApprovalDecisionRow, AuthoringDraftRow, EntityRevisionRow, GateResultRow,
    GenerationRunRow, GenerationWorkUnitRow, ManagedAssetRow, MediaTaskRow,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectRow,
    StageHeadRow,
)
from .constants import CURRENT_STAGE_SCHEMA_VERSION

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository

class ProjectLifecyclePersistence:
    """Typed project persistence collaborator; the facade owns compatibility only."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

    def archive_project(self, project_id: str, expected_lifecycle_revision: int) -> Project:
        with self._repository._lifecycle_write() as session:
            row = self._repository._project_row(session, project_id)
            self._repository._assert_lifecycle_revision(row, expected_lifecycle_revision)
            if ProjectLifecycleStatus(row.lifecycle_status) == ProjectLifecycleStatus.ARCHIVED:
                return self._repository._project(row)
            if self._repository._project_is_busy_in_session(session, project_id):
                raise ProjectBusyError()
            now = utc_now()
            row.lifecycle_status = ProjectLifecycleStatus.ARCHIVED.value
            row.archived_at = now
            row.lifecycle_revision += 1
            row.updated_at = now
            return self._repository._project(row)

    def restore_project(self, project_id: str, expected_lifecycle_revision: int) -> Project:
        with self._repository._lifecycle_write() as session:
            row = self._repository._project_row(session, project_id)
            self._repository._assert_lifecycle_revision(row, expected_lifecycle_revision)
            if ProjectLifecycleStatus(row.lifecycle_status) == ProjectLifecycleStatus.ACTIVE:
                return self._repository._project(row)
            now = utc_now()
            row.lifecycle_status = ProjectLifecycleStatus.ACTIVE.value
            row.archived_at = None
            row.lifecycle_revision += 1
            row.updated_at = now
            return self._repository._project(row)

    def permanent_delete_project(
        self,
        project_id: str,
        expected_lifecycle_revision: int,
        confirmation_title: str,
    ) -> None:
        if not confirmation_title.strip():
            raise ValueError("confirmation title must not be blank")
        with self._repository._lifecycle_write() as session:
            project = self._repository._project_row(session, project_id)
            self._repository._assert_lifecycle_revision(project, expected_lifecycle_revision)
            if ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ARCHIVED:
                raise InvalidTransitionError("only archived projects can be permanently deleted")
            if confirmation_title != ProjectBrief.model_validate(project.brief).title:
                raise InvalidTransitionError("confirmation title does not match the project title")
            if self._repository._project_is_busy_in_session(session, project_id):
                raise ProjectBusyError()
            # The byte store is shared and content addressed.  Until a
            # media-aware whole-project erasure contract exists, deleting the
            # relational project first would orphan protected originals and
            # immutable preview history.  Refuse before any delete mutation.
            if session.scalar(
                select(ManagedAssetRow.id)
                .where(ManagedAssetRow.project_id == project_id)
                .limit(1)
            ) is not None:
                raise ProjectManagedAssetsPresentError()

            # Generation-run repair lineage uses a self-referential RESTRICT
            # foreign key.  Deleting leaf runs first preserves that durable
            # lineage contract while letting every other project-owned record
            # cascade from its run or project parent.
            remaining_run_ids = set(
                session.scalars(
                    select(GenerationRunRow.id).where(GenerationRunRow.project_id == project_id)
                ).all()
            )
            while remaining_run_ids:
                referenced_parents = set(
                    session.scalars(
                        select(GenerationRunRow.parent_run_id).where(
                            GenerationRunRow.parent_run_id.in_(remaining_run_ids)
                        )
                    ).all()
                )
                leaves = remaining_run_ids - {parent for parent in referenced_parents if parent is not None}
                if not leaves:
                    raise InvalidTransitionError("generation run lineage cannot be deleted safely")
                session.execute(delete(GenerationRunRow).where(GenerationRunRow.id.in_(leaves)))
                session.flush()
                remaining_run_ids -= leaves
            session.delete(project)

