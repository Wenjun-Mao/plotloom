"""Durable, revision-bound video segment proposals and creator selection."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...video_segments import DerivedSegment
from ..codec import _stored_utc, stable_hash
from ..schema import (
    VideoCandidateSelectionRow,
    VideoJobRow,
    VideoReviewRow,
    VideoSegmentRow,
)
from .access import ProjectPersistenceAccess
from .media_video_currentness import VideoJobCurrentness


class VideoSegmentPersistence:
    """One per-shot selection owner; derivative creation itself stays outside SQL."""

    def __init__(self, access: ProjectPersistenceAccess, currentness: VideoJobCurrentness) -> None:
        self._access = access
        self._currentness = currentness

    @staticmethod
    def _source(row: VideoJobRow) -> dict[str, Any]:
        binding = row.snapshot.get("sourceTiming") if isinstance(row.snapshot, dict) else None
        shot = row.snapshot.get("shot") if isinstance(row.snapshot, dict) else None
        if not isinstance(binding, dict) or not isinstance(shot, dict) or not isinstance(shot.get("id"), str):
            raise InvalidTransitionError("video job has no frozen authored-timing source")
        if binding.get("durationUnits") != shot.get("durationUnits"):
            raise InvalidTransitionError("video job source timing does not match its shot")
        return binding

    @staticmethod
    def _selection(session: Session, project_id: str, shot_id: str) -> VideoCandidateSelectionRow | None:
        return session.get(VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": shot_id})

    @staticmethod
    def _immutable(row: VideoSegmentRow) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "shotId": row.shot_id,
            "videoJobId": row.video_job_id, "sourceBinding": row.source_binding,
            "sourceBindingHash": row.source_binding_hash,
            "originalHash": row.original_hash, "inFrame": row.in_frame,
            "outFrame": row.out_frame, "authoredDurationUnits": row.authored_duration_units,
            "sourceProbe": row.source_probe, "derivativeProbe": row.derivative_probe,
            "derivativeUri": row.derivative_uri, "derivativeHash": row.derivative_hash,
        }

    @classmethod
    def _valid_metadata(cls, row: VideoSegmentRow, job: VideoJobRow) -> bool:
        try:
            binding = cls._source(job)
        except InvalidTransitionError:
            return False
        frames = row.out_frame - row.in_frame
        return bool(
            job.state == "ingested" and job.output_uri is not None
            and row.project_id == job.project_id
            and row.shot_id == job.snapshot["shot"]["id"]
            and row.original_hash == job.output_hash
            and row.source_binding == binding
            and row.source_binding_hash == stable_hash(binding)
            and row.proposal_hash == stable_hash(cls._immutable(row))
            and row.authored_duration_units == binding["durationUnits"]
            and row.in_frame >= 0 and frames > 0
            and frames * 1_000 == row.authored_duration_units * 24
            and row.derivative_probe.get("frameCount") == frames
            and row.derivative_probe.get("fps") == "24/1"
        )

    def candidate_storage(
        self, project_id: str, video_job_id: str, *, expected_selection_revision: int,
    ) -> dict[str, Any]:
        with self._access.leases.read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id or job.state != "ingested" or not job.output_uri or not job.output_hash:
                raise NotFoundError("ingested video candidate not found")
            if not self._currentness.video_job_current_in_session(session, job):
                raise InvalidTransitionError("video candidate source is stale")
            source = self._source(job)
            if job.snapshot.get("provider", {}).get("adapterId") != "minimax_h3_gateway":
                raise InvalidTransitionError("segment proposal requires a qualified H3 take")
            authored_units = source["durationUnits"]
            request = job.snapshot.get("request", {})
            expected_frames = request.get("frameCount")
            if (type(authored_units) is not int or authored_units <= 0
                    or authored_units * 24 % 1_000 != 0
                    or type(expected_frames) is not int
                    or expected_frames * 1_000 < authored_units * 24):
                raise InvalidTransitionError("segment proposal needs a frame-representable shot covered by its frozen H3 request")
            expected_intent = "source_exact" if expected_frames * 1_000 == authored_units * 24 else "segment_required"
            if job.snapshot.get("playbackIntent") != expected_intent:
                raise InvalidTransitionError("video job lacks its explicit authored-to-request timing intent")
            shot_id = job.snapshot["shot"]["id"]
            selection = self._selection(session, project_id, shot_id)
            actual = selection.revision if selection is not None else 0
            if actual != expected_selection_revision:
                raise RevisionConflictError("video-candidate-selection", expected_selection_revision, actual)
            return {"uri": job.output_uri, "hash": job.output_hash, "source": source,
                    "durationUnits": source["durationUnits"], "shotId": shot_id}

    def save_proposal(
        self, project_id: str, video_job_id: str, *, expected_selection_revision: int,
        original_hash: str, derivative_uri: str, derived: DerivedSegment,
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id or job.state != "ingested":
                raise NotFoundError("ingested video candidate not found")
            if not self._currentness.video_job_current_in_session(session, job) or job.output_hash != original_hash:
                raise InvalidTransitionError("video candidate changed during segment preparation")
            source = self._source(job)
            shot_id = job.snapshot["shot"]["id"]
            selection = self._selection(session, project_id, shot_id)
            actual = selection.revision if selection is not None else 0
            if actual != expected_selection_revision:
                raise RevisionConflictError("video-candidate-selection", expected_selection_revision, actual)
            row = VideoSegmentRow(
                id=new_id(), project_id=project_id, shot_id=shot_id, video_job_id=job.id,
                source_binding=source, source_binding_hash=stable_hash(source),
                original_hash=original_hash, in_frame=derived.in_frame,
                out_frame=derived.out_frame, authored_duration_units=source["durationUnits"],
                source_probe=derived.source_probe, derivative_probe=derived.output_probe,
                derivative_uri=derivative_uri, derivative_hash=derived.digest,
                proposal_hash="", selected_revision=None, created_at=utc_now(),
            )
            row.proposal_hash = stable_hash(self._immutable(row))
            session.add(row)
            session.flush()
            return self._projection(row, current=True, selected=False)

    def select(
        self, project_id: str, segment_id: str, *, reviewer: str, note: str,
        expected_selection_revision: int, expected_derivative_hash: str,
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            segment = session.get(VideoSegmentRow, segment_id)
            if segment is None or segment.project_id != project_id:
                raise NotFoundError("video segment proposal not found")
            job = session.get(VideoJobRow, segment.video_job_id)
            if job is None or job.state != "ingested" or not self._currentness.video_job_current_in_session(session, job):
                raise InvalidTransitionError("video segment source is stale")
            if not self._valid_metadata(segment, job) or segment.derivative_hash != expected_derivative_hash:
                raise InvalidTransitionError("video segment evidence changed")
            selection = self._selection(session, project_id, segment.shot_id)
            actual = selection.revision if selection is not None else 0
            if actual != expected_selection_revision:
                raise RevisionConflictError("video-candidate-selection", expected_selection_revision, actual)
            latest_reject = session.scalar(
                select(VideoReviewRow).where(VideoReviewRow.video_job_id == job.id)
                .order_by(VideoReviewRow.created_at.desc(), VideoReviewRow.id.desc()).limit(1)
            )
            if latest_reject is not None and latest_reject.decision == "reject":
                raise InvalidTransitionError("rejected audiovisual take cannot be selected as a segment")
            now = utc_now()
            revision = actual + 1
            if selection is None:
                selection = VideoCandidateSelectionRow(
                    project_id=project_id, shot_id=segment.shot_id,
                    selected_video_job_id=job.id, revision=revision, updated_at=now,
                )
                session.add(selection)
            else:
                selection.selected_video_job_id = job.id
                selection.revision = revision
                selection.updated_at = now
            segment.selected_revision = revision
            session.add(VideoReviewRow(
                id=new_id(), video_job_id=job.id, reviewer=reviewer,
                decision="select", note=note, created_at=now,
            ))
            return self._projection(segment, current=True, selected=True)

    def reopen_rejected_h3_review(
        self, project_id: str, video_job_id: str, *, reviewer: str, reason: str,
        expected_selection_revision: int,
    ) -> dict[str, Any]:
        """Append explicit reconsideration while preserving current shot playback."""
        reviewer, reason = reviewer.strip(), reason.strip()
        if not reviewer or not reason:
            raise InvalidTransitionError("reopening a rejected H3 take requires a reviewer and reason")

        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            snapshot = job.snapshot
            provider = snapshot.get("provider") if isinstance(snapshot, dict) else None
            if (
                job.state != "ingested"
                or not isinstance(provider, dict)
                or provider.get("adapterId") != "minimax_h3_gateway"
                or not self._currentness.video_job_current_in_session(session, job)
            ):
                raise InvalidTransitionError("only a current ingested H3 take can be reopened")

            latest = session.scalar(
                select(VideoReviewRow)
                .where(VideoReviewRow.video_job_id == job.id)
                .order_by(VideoReviewRow.created_at.desc(), VideoReviewRow.id.desc())
                .limit(1)
            )
            if latest is None or latest.decision != "reject":
                raise InvalidTransitionError("only the latest rejected H3 review can be reopened")

            self._source(job)
            shot_id = snapshot["shot"]["id"]
            selection = self._selection(session, project_id, shot_id)
            actual_revision = selection.revision if selection is not None else 0
            if actual_revision != expected_selection_revision:
                raise RevisionConflictError(
                    "video-candidate-selection", expected_selection_revision, actual_revision
                )
            if actual_revision < 0:
                raise InvalidTransitionError("video selection revision is invalid")
            if selection is not None and selection.selected_video_job_id == job.id:
                raise InvalidTransitionError("a rejected H3 take cannot remain the selected video job")

            next_revision = actual_revision + 1
            if selection is None:
                selection = VideoCandidateSelectionRow(
                    project_id=project_id, shot_id=shot_id,
                    selected_video_job_id=None, revision=next_revision, updated_at=utc_now(),
                )
                session.add(selection)
            else:
                selected_id = selection.selected_video_job_id
                if selected_id is not None:
                    selected_job = session.get(VideoJobRow, selected_id)
                    selected_snapshot = selected_job.snapshot if selected_job is not None else None
                    selected_shot = selected_snapshot.get("shot") if isinstance(selected_snapshot, dict) else None
                    if (
                        selected_job is None
                        or selected_job.project_id != project_id
                        or not isinstance(selected_shot, dict)
                        or selected_shot.get("id") != shot_id
                    ):
                        raise InvalidTransitionError("current video selection is inconsistent")
                    active_segments = session.scalars(
                        select(VideoSegmentRow).where(
                            VideoSegmentRow.project_id == project_id,
                            VideoSegmentRow.shot_id == shot_id,
                            VideoSegmentRow.video_job_id == selected_id,
                            VideoSegmentRow.selected_revision == actual_revision,
                        )
                    ).all()
                    if len(active_segments) > 1:
                        raise InvalidTransitionError("current video selection has multiple active segments")
                    if active_segments:
                        active_segments[0].selected_revision = next_revision
                selection.revision = next_revision
                selection.updated_at = utc_now()

            # Review projection sorts by createdAt and then id. Keep the
            # explicit reopen event after its rejection even within one clock tick.
            created_at = max(
                utc_now(), _stored_utc(latest.created_at) + timedelta(microseconds=1)
            )
            review = VideoReviewRow(
                id=new_id(), video_job_id=job.id, reviewer=reviewer,
                decision="reopen", note=reason, created_at=created_at,
            )
            session.add(review)
            return {
                "id": review.id, "videoJobId": job.id, "reviewer": reviewer,
                "decision": "reopen", "note": reason,
                "createdAt": _stored_utc(created_at).isoformat(),
                "selectionRevision": next_revision,
            }

    def proposal_storage(self, project_id: str, segment_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            segment = session.get(VideoSegmentRow, segment_id)
            if segment is None or segment.project_id != project_id:
                raise NotFoundError("video segment proposal not found")
            job = session.get(VideoJobRow, segment.video_job_id)
            if job is None or not self._currentness.video_job_current_in_session(session, job) or not self._valid_metadata(segment, job):
                raise InvalidTransitionError("video segment proposal is stale")
            return {"uri": segment.derivative_uri, "hash": segment.derivative_hash, "mimeType": "video/mp4"}

    def selected_storage(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id or not self._currentness.video_job_current_in_session(session, job):
                raise NotFoundError("current selected video job not found")
            shot_id = self._source(job).get("cut", {}).get("shotId") or job.snapshot["shot"]["id"]
            selection = self._selection(session, project_id, shot_id)
            if selection is None or selection.selected_video_job_id != job.id:
                raise NotFoundError("video job has no reviewed playback segment")
            segment = session.scalar(
                select(VideoSegmentRow).where(
                    VideoSegmentRow.project_id == project_id,
                    VideoSegmentRow.shot_id == shot_id,
                    VideoSegmentRow.video_job_id == job.id,
                    VideoSegmentRow.selected_revision == selection.revision,
                )
            )
            if segment is None or not self._valid_metadata(segment, job):
                raise NotFoundError("video job has no current reviewed playback segment")
            return {"uri": segment.derivative_uri, "hash": segment.derivative_hash, "mimeType": "video/mp4"}

    def segments_for_jobs(self, session: Session, jobs: list[VideoJobRow]) -> dict[str, list[VideoSegmentRow]]:
        result: dict[str, list[VideoSegmentRow]] = {}
        if not jobs:
            return result
        for row in session.scalars(
            select(VideoSegmentRow).where(VideoSegmentRow.video_job_id.in_([job.id for job in jobs]))
            .order_by(VideoSegmentRow.created_at.asc(), VideoSegmentRow.id.asc())
        ):
            result.setdefault(row.video_job_id, []).append(row)
        return result

    @staticmethod
    def _projection(row: VideoSegmentRow, *, current: bool, selected: bool) -> dict[str, Any]:
        return {
            "id": row.id, "videoJobId": row.video_job_id, "shotId": row.shot_id,
            "inFrame": row.in_frame, "outFrame": row.out_frame,
            "authoredDurationUnits": row.authored_duration_units,
            "sourceProbe": row.source_probe, "derivativeProbe": row.derivative_probe,
            "derivativeHash": row.derivative_hash, "current": current,
            "selected": selected, "selectedRevision": row.selected_revision,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def project_segments(
        self, session: Session, job: VideoJobRow,
        rows: list[VideoSegmentRow], selection: VideoCandidateSelectionRow | None,
        *, job_current: bool,
    ) -> list[dict[str, Any]]:
        return [
            self._projection(
                row, current=job_current and self._valid_metadata(row, job),
                selected=bool(
                    job_current and selection is not None
                    and selection.selected_video_job_id == job.id
                    and row.selected_revision == selection.revision
                    and self._valid_metadata(row, job)
                ),
            )
            for row in rows
        ]
