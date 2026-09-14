"""Legacy generic media-task persistence and production hard-stop."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...domain import (
    TERMINAL_MEDIA_TASK_STATUSES,
    MediaKind,
    MediaPromptContext,
    MediaTask,
    MediaTaskStatus,
    StageName,
    StageStatus,
    StoryBible,
    Storyboard,
    utc_now,
)
from ...exceptions import (
    InvalidTransitionError,
    NotFoundError,
    ProductionPipelineNotReadyError,
    StagePrerequisiteError,
)
from ..schema import MediaTaskRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence


class GenericMediaTaskPersistence:
    """Own read-safe legacy media tasks while preserving the M2 hard stop."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence) -> None:
        self._access = access
        self._canonical = canonical

    @staticmethod
    def media_task(row: MediaTaskRow) -> MediaTask:
        return MediaTask(
            id=row.id, project_id=row.project_id, shot_id=row.shot_id,
            storyboard_revision=row.storyboard_revision, kind=MediaKind(row.kind),
            status=MediaTaskStatus(row.status), derived_prompt=row.derived_prompt,
            prompt_components=row.prompt_components, provider=row.provider,
            public_settings=row.public_settings, provider_task_id=row.provider_task_id,
            output_uri=row.output_uri, error=row.error, created_at=row.created_at,
            updated_at=row.updated_at, started_at=row.started_at, finished_at=row.finished_at,
        )

    def get_media_prompt_context(self, project_id: str, shot_id: str) -> MediaPromptContext:
        """Freeze canonical facts consumed by an application-layer prompt compiler."""

        with self._access.leases.read() as session:
            project = self._access.codecs.project(self._access.rows.project(session, project_id))
            bible_head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            if bible_head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORY_BIBLE, bible_head.status)
            head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORYBOARD, head.status)
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            assert isinstance(storyboard, Storyboard)
            shot = next((candidate for candidate in storyboard.shots if candidate.id == shot_id), None)
            if shot is None:
                raise NotFoundError(f"shot not found in current storyboard: {shot_id}")
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            assert isinstance(bible, StoryBible)
            return MediaPromptContext(
                brief=project.brief,
                story_bible=bible,
                shot=shot,
                storyboard_revision=head.revision,
            )

    def create_media_task(
        self,
        project_id: str,
        shot_id: str,
        kind: MediaKind,
        *,
        expected_storyboard_revision: int,
        derived_prompt: str,
        prompt_components: dict[str, Any],
        provider: str | None = None,
        public_settings: dict[str, Any] | None = None,
    ) -> MediaTask:
        """Reject the pre-M2 Shot-to-provider path before any data access.

        Approval alone is deliberately not a production input.  M2 will
        replace this compatibility-shaped entry point with one that accepts an
        immutable ProductionSnapshot; keeping the method callable today would
        let an in-process caller bypass the API's hard stop.
        """

        _ = (
            project_id,
            shot_id,
            kind,
            expected_storyboard_revision,
            derived_prompt,
            prompt_components,
            provider,
            public_settings,
        )
        raise ProductionPipelineNotReadyError()

    def get_media_task(self, task_id: str) -> MediaTask:
        with self._access.leases.read() as session:
            return self.media_task(self._access.rows.media_task(session, task_id))

    def list_project_media_tasks(self, project_id: str, *, limit: int = 200) -> list[MediaTask]:
        if not 1 <= limit <= 500:
            raise ValueError("media task list limit must be between 1 and 500")
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(MediaTaskRow)
                .where(MediaTaskRow.project_id == project_id)
                .order_by(MediaTaskRow.created_at.desc())
                .limit(limit)
            ).all()
            return [self.media_task(row) for row in rows]

    def start_media_task(self, task_id: str, *, provider: str | None = None) -> MediaTask:
        # Every task stored before M2 lacks a ProductionSnapshot.  Do not even
        # read it here: callers must not turn a queued historical row into a
        # provider-bound execution by bypassing the HTTP hard stop.
        _ = (task_id, provider)
        raise ProductionPipelineNotReadyError()

    def record_media_submission(
        self,
        task_id: str,
        *,
        provider: str,
        provider_task_id: str | None,
    ) -> MediaTask:
        # A persisted provider task ID would make subsequent polling a new
        # production operation.  Historical rows can only be read or safely
        # terminalized until M2 owns that immutable boundary.
        _ = (task_id, provider, provider_task_id)
        raise ProductionPipelineNotReadyError()

    def finish_media_task(
        self,
        task_id: str,
        status: MediaTaskStatus,
        *,
        output_uri: str | None = None,
        error: str | None = None,
    ) -> MediaTask:
        if status not in TERMINAL_MEDIA_TASK_STATUSES:
            raise InvalidTransitionError("finish_media_task requires a terminal status")
        if status == MediaTaskStatus.SUCCEEDED:
            # Success would attach a new provider-derived URI to a legacy row.
            # Preserve only failure/cancellation for upgrade recovery.
            raise ProductionPipelineNotReadyError()
        normalized_error = error.strip() if error else None
        if status == MediaTaskStatus.FAILED and not normalized_error:
            raise ValueError("failed media tasks require an error")
        with self._access.leases.write() as session:
            row = self._access.rows.media_task(session, task_id)
            if MediaTaskStatus(row.status) != MediaTaskStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish media task from {row.status}")
            now = utc_now()
            row.status = status.value
            row.output_uri = None
            row.error = normalized_error if status == MediaTaskStatus.FAILED else None
            row.finished_at = now
            row.updated_at = now
            return self.media_task(row)
