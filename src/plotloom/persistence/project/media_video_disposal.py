"""Explicit, recoverable disposal of unselected video candidate bytes."""

from __future__ import annotations

from sqlalchemy import select

from ...domain import utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ..schema import (
    ManagedAssetRow,
    RunArtifactBlobRow,
    VideoCandidateSelectionRow,
    VideoJobRow,
    VideoSegmentRow,
)
from .access import ProjectPersistenceAccess


class VideoCandidateDisposal:
    def __init__(self, access: ProjectPersistenceAccess) -> None:
        self._access = access

    @staticmethod
    def _shot_id(row: VideoJobRow) -> str:
        shot = row.snapshot.get("shot")
        if not isinstance(shot, dict) or not isinstance(shot.get("id"), str):
            raise InvalidTransitionError("video candidate has no valid frozen shot")
        return shot["id"]

    def discard(
        self, project_id: str, *, shot_id: str, video_job_ids: list[str],
        expected_selection_revision: int,
    ) -> list[dict[str, str | None]]:
        if not video_job_ids or len(set(video_job_ids)) != len(video_job_ids):
            raise InvalidTransitionError("discard must name each candidate exactly once")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            selection = session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": shot_id})
            actual_revision = selection.revision if selection is not None else 0
            if actual_revision != expected_selection_revision:
                raise RevisionConflictError("video-candidate-selection", expected_selection_revision, actual_revision)
            rows = list(session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(video_job_ids))).all())
            if len(rows) != len(video_job_ids) or any(row.project_id != project_id or self._shot_id(row) != shot_id for row in rows):
                raise NotFoundError("video discard candidate not found for this project shot")
            selected_id = selection.selected_video_job_id if selection is not None else None
            for row in rows:
                if row.id == selected_id:
                    raise InvalidTransitionError("the selected video candidate cannot be discarded")
                if session.scalar(select(VideoSegmentRow.id).where(
                    VideoSegmentRow.project_id == project_id,
                    VideoSegmentRow.video_job_id == row.id,
                ).limit(1)) is not None:
                    raise InvalidTransitionError("a video candidate with retained segment proposals cannot be discarded")
                if row.state not in {"ingested", "discard_pending"}:
                    raise InvalidTransitionError("only an ingested candidate with a known local output can be discarded")
            for row in rows:
                if row.state == "ingested":
                    row.state, row.updated_at = "discard_pending", utc_now()
            return [{"id": row.id, "uri": row.output_uri} for row in rows]

    def finalize(self, project_id: str, video_job_ids: list[str]) -> None:
        with self._access.leases.lifecycle_write() as session:
            rows = list(session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(video_job_ids))).all())
            if len(rows) != len(video_job_ids) or any(row.project_id != project_id or row.state != "discard_pending" for row in rows):
                raise InvalidTransitionError("video candidate disposal is no longer pending")
            for row in rows:
                row.state, row.output_uri, row.output_hash, row.updated_at = "discarded", None, None, utc_now()

    def has_retained_reference(self, project_id: str, uri: str) -> bool:
        with self._access.leases.read() as session:
            if session.scalar(select(VideoJobRow.id).where(
                VideoJobRow.project_id == project_id,
                VideoJobRow.output_uri == uri,
                VideoJobRow.state.not_in(("discard_pending", "discarded")),
            ).limit(1)) is not None:
                return True
            if session.scalar(select(VideoSegmentRow.id).where(
                VideoSegmentRow.project_id == project_id,
                VideoSegmentRow.derivative_uri == uri,
            ).limit(1)) is not None:
                return True
            if session.scalar(select(VideoSegmentRow.id).join(
                VideoJobRow, VideoSegmentRow.video_job_id == VideoJobRow.id,
            ).where(
                VideoSegmentRow.project_id == project_id,
                VideoJobRow.output_uri == uri,
            ).limit(1)) is not None:
                return True
            if session.scalar(select(ManagedAssetRow.id).where(
                ManagedAssetRow.project_id == project_id,
                (ManagedAssetRow.original_uri == uri) | (ManagedAssetRow.display_uri == uri),
            ).limit(1)) is not None:
                return True
            return session.scalar(select(RunArtifactBlobRow.run_id).where(
                RunArtifactBlobRow.relative_path == uri,
            ).limit(1)) is not None
