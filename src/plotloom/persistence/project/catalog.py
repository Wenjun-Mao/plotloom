from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER, AuthoringDraft, AuthoringDraftScope, DialogueTimingProfile,
    EntityRevision, GateEvaluation, GateEvidence, GateResult, InitialStage,
    LatestRunSummary, Project, ProjectBrief, ProjectCreation, ProjectDuplicateResult,
    ProjectLifecycleStatus, ProjectSummary, StageEnvelope, StageHead, StageName,
    StagePayload, StageStatus, downstream_stages, new_id, stage_payload_model,
    utc_now, upstream_stages, brief_for_new_project, validate_initial_stage_prefix,
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
from .access import ProjectPersistenceAccess

class ProjectCatalogPersistence:
    """Typed project persistence collaborator; the facade owns compatibility only."""

    def __init__(self, access: ProjectPersistenceAccess) -> None:
        self._access = access
        self._canonical: Any | None = None

    def bind_canonical(self, canonical: Any) -> None:
        self._canonical = canonical

    def _require_canonical(self) -> Any:
        if self._canonical is None:
            raise RuntimeError("project catalog was used before canonical persistence was composed")
        return self._canonical

    @staticmethod
    def _creation_fingerprint(brief: ProjectBrief, stages: Sequence[InitialStage]) -> str:
        return stable_hash(
            {
                "brief": brief.model_dump(mode="json", by_alias=False),
                "initialStages": [
                    {"stage": stage.stage.value, "payload": stage.payload}
                    for stage in stages
                ],
            }
        )

    def _create_project_row_in_session(
        self,
        session: Session,
        brief: ProjectBrief,
        now: datetime,
    ) -> ProjectRow:
        project = Project(brief=brief, created_at=now, updated_at=now)
        row = ProjectRow(
            id=project.id,
            revision=project.revision,
            lifecycle_revision=project.lifecycle_revision,
            lifecycle_status=project.lifecycle_status.value,
            archived_at=None,
            brief=brief.model_dump(mode="json", by_alias=False),
            created_at=now,
            updated_at=now,
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
                    updated_at=now,
                )
            )
        return row

    def _stage_envelopes_in_session(self, session: Session, project_id: str) -> list[StageEnvelope]:
        rows = session.scalars(
            select(StageHeadRow).where(StageHeadRow.project_id == project_id)
        ).all()
        by_stage = {StageName(row.stage): row for row in rows}
        envelopes: list[StageEnvelope] = []
        for stage in STAGE_ORDER:
            row = by_stage[stage]
            payload: StagePayload | None = None
            if row.entity_revision_id is not None:
                revision = session.get(EntityRevisionRow, row.entity_revision_id)
                if revision is None:
                    raise NotFoundError(f"entity revision not found: {row.entity_revision_id}")
                payload = self._access.codecs.decode_current_stage_payload(
                    stage, revision.payload, revision.schema_version
                )
            envelopes.append(StageEnvelope(head=self._access.codecs.stage_head(row), payload=payload))
        return envelopes

    def _project_creation_in_session(self, session: Session, project_row: ProjectRow) -> ProjectCreation:
        return ProjectCreation(
            **self._access.codecs.project(project_row).model_dump(mode="python"),
            stages=self._stage_envelopes_in_session(session, project_row.id),
        )

    def create_project(
        self,
        brief: ProjectBrief,
        *,
        initial_stages: Sequence[InitialStage | dict[str, Any]] = (),
        idempotency_key: str | None = None,
    ) -> ProjectCreation:
        brief = brief_for_new_project(brief)
        normalized_stages = [InitialStage.model_validate(stage) for stage in initial_stages]
        validate_initial_stage_prefix(normalized_stages)
        fingerprint = self._creation_fingerprint(brief, normalized_stages)
        key = idempotency_key.strip() if idempotency_key is not None else None
        if key is not None and (not key or len(key) > 255):
            raise ValueError("idempotency key must contain between 1 and 255 characters")

        with self._access.leases.bootstrap_write() as session:
            if key is not None:
                existing = session.get(ProjectCreationIdempotencyRow, key)
                if existing is not None:
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflictError()
                    return self._project_creation_in_session(
                        session, self._access.rows.project(session, existing.project_id)
                    )

            now = utc_now()
            project_row = self._create_project_row_in_session(session, brief, now)
            for initial_stage in normalized_stages:
                payload = stage_payload_model(
                    initial_stage.stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION
                ).model_validate(initial_stage.payload)
                self._require_canonical()._install_stage_in_session(
                    session,
                    project_row,
                    initial_stage.stage,
                    payload,
                    expected_revision=0,
                    now=now,
                    allow_noop=False,
                )
            if key is not None:
                # Persist the aggregate before its durable key binding.  The
                # ORM rows intentionally have no relationship attributes, so
                # this explicit boundary makes the foreign-key ordering part
                # of the bootstrap contract rather than a unit-of-work
                # implementation detail.
                session.flush()
                session.add(
                    ProjectCreationIdempotencyRow(
                        idempotency_key=key,
                        request_fingerprint=fingerprint,
                        project_id=project_row.id,
                        created_at=now,
                    )
                )
            return self._project_creation_in_session(session, project_row)

    def get_project(self, project_id: str) -> Project:
        with self._access.leases.read() as session:
            return self._access.codecs.project(self._access.rows.project(session, project_id))

    def list_projects(
        self,
        *,
        lifecycle_status: ProjectLifecycleStatus | None = ProjectLifecycleStatus.ACTIVE,
        limit: int = 50,
        cursor: tuple[datetime, str] | None = None,
    ) -> tuple[list[ProjectSummary], tuple[datetime, str] | None]:
        """Return one stable page ordered by immutable `(created_at, id)` facts.

        The cursor is deliberately represented internally as the actual sort
        tuple.  The HTTP layer alone owns its opaque encoding, keeping storage
        ordering independent from a presentation format.
        """

        if not 1 <= limit <= 200:
            raise ValueError("project list limit must be between 1 and 200")
        with self._access.leases.read() as session:
            statement = select(ProjectRow)
            if lifecycle_status is not None:
                statement = statement.where(ProjectRow.lifecycle_status == lifecycle_status.value)
            if cursor is not None:
                created_at, project_id = cursor
                statement = statement.where(
                    (ProjectRow.created_at < created_at)
                    | ((ProjectRow.created_at == created_at) & (ProjectRow.id < project_id))
                )
            rows = session.scalars(
                statement.order_by(ProjectRow.created_at.desc(), ProjectRow.id.desc()).limit(limit + 1)
            ).all()
            page_rows = rows[:limit]
            has_more = len(rows) > limit
            summaries: list[ProjectSummary] = []
            for row in page_rows:
                stage_rows = session.scalars(
                    select(StageHeadRow).where(StageHeadRow.project_id == row.id)
                ).all()
                statuses = {StageName(head.stage): StageStatus(head.status) for head in stage_rows}
                latest_run = session.scalar(
                    select(GenerationRunRow)
                    .where(GenerationRunRow.project_id == row.id)
                    .order_by(GenerationRunRow.created_at.desc(), GenerationRunRow.id.desc())
                    .limit(1)
                )
                summaries.append(
                    ProjectSummary(
                        **self._access.codecs.project(row).model_dump(mode="python"),
                        stage_statuses=statuses,
                        latest_run=self._access.codecs.latest_run_summary(latest_run) if latest_run else None,
                    )
                )
            next_cursor = None
            if has_more and page_rows:
                last = page_rows[-1]
                next_cursor = (last.created_at, last.id)
            return summaries, next_cursor

    @staticmethod
    def _duplicate_fingerprint(
        project_id: str,
        expected_lifecycle_revision: int,
        title: str | None,
    ) -> str:
        return stable_hash(
            {
                "projectId": project_id,
                "expectedLifecycleRevision": expected_lifecycle_revision,
                "title": title,
            }
        )

    def _duplicate_result_in_session(
        self,
        session: Session,
        project_id: str,
        copied_through: str | None,
        omitted_stages: Sequence[str],
    ) -> ProjectDuplicateResult:
        return ProjectDuplicateResult(
            project=self._project_creation_in_session(session, self._access.rows.project(session, project_id)),
            copied_through=StageName(copied_through) if copied_through else None,
            omitted_stages=[StageName(stage) for stage in omitted_stages],
        )

    def duplicate_project(
        self,
        project_id: str,
        expected_lifecycle_revision: int,
        *,
        title: str | None = None,
        idempotency_key: str | None = None,
    ) -> ProjectDuplicateResult:
        normalized_title = title.strip() if title is not None else None
        if normalized_title == "":
            raise ValueError("duplicate title must not be blank")
        key = idempotency_key.strip() if idempotency_key is not None else None
        if key is not None and (not key or len(key) > 255):
            raise ValueError("idempotency key must contain between 1 and 255 characters")
        fingerprint = self._duplicate_fingerprint(
            project_id, expected_lifecycle_revision, normalized_title
        )

        # Duplicate-key decisions must be made at SQLite's immediate write
        # boundary, exactly like project creation.  Otherwise two processes
        # can both observe an unbound key and create distinct copies.
        with self._access.leases.bootstrap_write() as session:
            if key is not None:
                existing = session.get(ProjectDuplicateIdempotencyRow, key)
                if existing is not None:
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflictError()
                    return self._duplicate_result_in_session(
                        session,
                        existing.project_id,
                        existing.copied_through,
                        existing.omitted_stages,
                    )

            source = self._access.rows.project(session, project_id)
            self._access.guards.lifecycle_revision(source, expected_lifecycle_revision)
            source_brief = ProjectBrief.model_validate(source.brief)
            brief_data = source_brief.model_dump(mode="python")
            if normalized_title is not None:
                brief_data["title"] = normalized_title
            duplicate_brief = ProjectBrief.model_validate(brief_data)
            now = utc_now()
            duplicate = self._create_project_row_in_session(session, duplicate_brief, now)

            copied: list[StageName] = []
            for stage in STAGE_ORDER:
                source_head = self._access.rows.stage(session, source.id, stage)
                if source_head.status != StageStatus.READY.value:
                    break
                payload = self._require_canonical()._load_stage_payload(session, source.id, stage)
                self._require_canonical()._install_stage_in_session(
                    session,
                    duplicate,
                    stage,
                    payload,
                    expected_revision=0,
                    now=now,
                    allow_noop=False,
                )
                copied.append(stage)
            copied_through = copied[-1] if copied else None
            omitted = list(STAGE_ORDER[len(copied) :])
            if key is not None:
                session.flush()
                session.add(
                    ProjectDuplicateIdempotencyRow(
                        idempotency_key=key,
                        request_fingerprint=fingerprint,
                        project_id=duplicate.id,
                        copied_through=copied_through.value if copied_through else None,
                        omitted_stages=[stage.value for stage in omitted],
                        created_at=now,
                    )
                )
            return self._duplicate_result_in_session(
                session,
                duplicate.id,
                copied_through.value if copied_through else None,
                [stage.value for stage in omitted],
            )
