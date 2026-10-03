"""Video-job lifecycle and paid-pilot accounting workflow persistence."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import new_id, utc_now
from ...exceptions import (
    InvalidTransitionError,
    NotFoundError,
    RevisionConflictError,
)
from ..codec import _stored_utc
from ..schema import (
    VideoCandidateSelectionRow,
    VideoJobRow,
    VideoReviewRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_image_currentness import ImageJobCurrentness
from .media_same_person_reviews import SamePersonReviewPersistence
from .media_video_currentness import VideoJobCurrentness
from .media_video_disposal import VideoCandidateDisposal
from .media_video_end_frames import VideoEndFrames
from .media_video_preparation import VideoJobPreparation
from .media_video_segments import VideoSegmentPersistence
from .media_video_source import VideoSourceTiming


class VideoPilotAccountingPort(Protocol):
    """Legacy runtime's transaction-local pilot-accounting contract."""

    def budget(self) -> dict[str, Any]: ...

    def reserve(self, session: Session, *, video_job_id: str, seconds: int, now: Any) -> None: ...

    def record_dispatch(
        self, session: Session, *, video_job_id: str, seconds: int, now: Any
    ) -> None: ...

    def release_before_dispatch(
        self, session: Session, *, video_job_id: str, seconds: int, now: Any
    ) -> None: ...


class VideoJobPersistence(VideoJobPreparation):
    """Own video lifecycle facts and atomic application-accounting mutations."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        admission: KeyframeAdmission,
        references: CharacterReferencePersistence,
        image_currentness: ImageJobCurrentness,
        same_person: SamePersonReviewPersistence,
        currentness: VideoJobCurrentness,
        accounting: VideoPilotAccountingPort | None,
        source_timing: VideoSourceTiming,
        segments: VideoSegmentPersistence,
        end_frames: VideoEndFrames,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._references = references
        self._image_currentness = image_currentness
        self._same_person = same_person
        self._currentness = currentness
        self._accounting = accounting
        self._source_timing = source_timing
        self._segments = segments
        self._end_frames = end_frames
        self._disposal = VideoCandidateDisposal(access)

    def video_budget(self) -> dict[str, Any]:
        if self._accounting is None:
            raise InvalidTransitionError(
                "direct project video has no retained Wan pilot accounting"
            )
        return self._accounting.budget()


    def claim_video_dispatch(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        """Cross the durable dispatch boundary before any POST; never retry it."""
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "prepared":
                raise InvalidTransitionError("video job cannot be submitted again; reconcile its existing attempt")
            if not self._currentness.video_job_current_in_session(session, job):
                raise InvalidTransitionError("video job frozen inputs are stale; prepare a new attempt")
            now = utc_now()
            job.state, job.dispatched_at, job.updated_at = "dispatching", now, now
            if self._currentness.video_job_tracks_paid_wan_pilot(job):
                if self._accounting is None:
                    raise InvalidTransitionError(
                        "direct project video cannot use the retained Wan pilot policy"
                    )
                self._accounting.record_dispatch(
                    session, video_job_id=job.id, seconds=job.requested_seconds, now=now
                )
            return self._currentness.video_job_dict(job, current=True)

    def record_video_submission(self, project_id: str, video_job_id: str, prediction_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "dispatching" or job.provider_prediction_id is not None:
                raise InvalidTransitionError("video submission cannot be recorded from this state")
            job.provider_prediction_id, job.state, job.updated_at = prediction_id, "submitted", utc_now()
            return self._currentness.video_job_dict(job, current=self._currentness.video_job_current_in_session(session, job))

    def record_video_outcome_unknown(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"dispatching", "submitted"}:
                raise InvalidTransitionError("only a dispatched video job can have unknown outcome")
            job.state, job.error, job.updated_at = "outcome_unknown", message[:2_000], utc_now()
            return self._currentness.video_job_dict(job, current=False)

    def record_video_output(self, project_id: str, video_job_id: str, *, uri: str, digest: str, observed: dict[str, Any]) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("video output can only be ingested from a known submitted attempt")
            job.output_uri, job.output_hash, job.observed, job.state, job.updated_at = uri, digest, observed, "ingested", utc_now()
            return self._currentness.video_job_dict(job, current=self._currentness.video_job_current_in_session(session, job))

    def record_video_retrieve_needed(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("only a known submitted video can await retrieval")
            job.state, job.error, job.updated_at = "retrieve_needed", message[:2_000], utc_now()
            return self._currentness.video_job_dict(job, current=self._currentness.video_job_current_in_session(session, job))

    def record_video_remote_failed(self, project_id: str, video_job_id: str, code: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("only a known submitted video can record remote failure")
            job.state, job.error, job.updated_at = "failed", code, utc_now()
            return self._currentness.video_job_dict(job, current=False)

    def recover_video_dispatches(self) -> list[str]:
        """A restart never replays a POST whose durable claim was entered."""
        with self._access.leases.lifecycle_write() as session:
            rows = session.scalars(select(VideoJobRow).where(VideoJobRow.state == "dispatching")).all()
            now = utc_now()
            for row in rows:
                row.state, row.error, row.updated_at = "outcome_unknown", "restart_dispatch_outcome_unknown", now
            return [row.id for row in rows]

    def cancel_video_job(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state == "prepared":
                # Only this proven pre-dispatch path releases a reservation.
                if self._currentness.video_job_tracks_paid_wan_pilot(job):
                    if self._accounting is None:
                        raise InvalidTransitionError(
                            "direct project video cannot use the retained Wan pilot policy"
                        )
                    self._accounting.release_before_dispatch(
                        session, video_job_id=job.id, seconds=job.requested_seconds,
                        now=utc_now(),
                    )
                job.state = "cancelled"
            elif job.state in {"dispatching", "submitted", "retrieve_needed", "outcome_unknown"}:
                # Cancellation is local adoption intent, not a fabricated
                # remote state. Keep the known task state recoverable.
                job.cancel_requested_at = utc_now()
            job.updated_at = utc_now()
            return self._currentness.video_job_dict(job, current=False)

    def list_video_jobs(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(select(VideoJobRow).where(VideoJobRow.project_id == project_id).order_by(VideoJobRow.created_at.desc(), VideoJobRow.id.desc())).all()
            reviews_by_job: dict[str, list[dict[str, str]]] = {}
            for review in session.scalars(
                select(VideoReviewRow).where(VideoReviewRow.video_job_id.in_([row.id for row in rows]))
                .order_by(VideoReviewRow.created_at.asc(), VideoReviewRow.id.asc())
            ):
                reviews_by_job.setdefault(review.video_job_id, []).append({
                    "id": review.id, "reviewer": review.reviewer, "decision": review.decision,
                    "note": review.note, "createdAt": _stored_utc(review.created_at).isoformat(),
                })
            selections = {
                row.shot_id: row
                for row in session.scalars(
                    select(VideoCandidateSelectionRow).where(
                        VideoCandidateSelectionRow.project_id == project_id
                    )
                )
            }
            segments = self._segments.segments_for_jobs(session, rows)
            result = []
            for row in rows:
                job = self._video_job_projection(session, row, selections)
                selection = selections.get(self._shot_id(row))
                proposals = self._segments.project_segments(
                    session, row, segments.get(row.id, []), selection,
                    job_current=job["current"],
                )
                job["segments"] = proposals
                job["playbackSegment"] = next((item for item in proposals if item["selected"]), None)
                result.append(job | {"reviews": reviews_by_job.get(row.id, [])})
            return result

    def get_video_output_storage(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id or job.state != "ingested" or not job.output_uri or not job.output_hash:
                raise NotFoundError("locally ingested video candidate not found")
            return {"uri": job.output_uri, "hash": job.output_hash, "mimeType": "video/mp4"}

    def review_video_job(self, project_id: str, video_job_id: str, *, reviewer: str, decision: str, note: str, expected_selection_revision: int) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "ingested" or not self._currentness.video_job_current_in_session(session, job):
                raise InvalidTransitionError("only a current locally ingested video candidate can be reviewed")
            shot_id = self._shot_id(job)
            selection = session.get(
                VideoCandidateSelectionRow, {"project_id": project_id, "shot_id": shot_id}
            )
            actual_revision = selection.revision if selection is not None else 0
            if actual_revision != expected_selection_revision:
                raise RevisionConflictError("video-candidate-selection", expected_selection_revision, actual_revision)
            if decision == "select" and job.snapshot.get("provider", {}).get("adapterId") == "minimax_h3_gateway":
                raise InvalidTransitionError("H3 selection requires a reviewed playback segment")
            review = VideoReviewRow(id=new_id(), video_job_id=job.id, reviewer=reviewer, decision=decision, note=note, created_at=utc_now())
            session.add(review)
            if decision == "select":
                now = utc_now()
                if selection is None:
                    selection = VideoCandidateSelectionRow(
                        project_id=project_id, shot_id=shot_id,
                        selected_video_job_id=job.id, revision=1, updated_at=now,
                    )
                    session.add(selection)
                else:
                    selection.selected_video_job_id = job.id
                    selection.revision += 1
                    selection.updated_at = now
            elif decision == "reject" and selection is not None and selection.selected_video_job_id == job.id:
                selection.selected_video_job_id = None
                selection.revision += 1
                selection.updated_at = utc_now()
            return {"id": review.id, "videoJobId": job.id, "reviewer": reviewer, "decision": decision, "note": note, "createdAt": _stored_utc(review.created_at).isoformat(), "selectionRevision": selection.revision if selection is not None else actual_revision}

    def reopen_video_job_review(
        self, project_id: str, video_job_id: str, *, reviewer: str, reason: str,
        expected_selection_revision: int,
    ) -> dict[str, Any]:
        return self._segments.reopen_rejected_h3_review(
            project_id, video_job_id, reviewer=reviewer, reason=reason,
            expected_selection_revision=expected_selection_revision,
        )

    def discard_video_candidates(
        self, project_id: str, *, shot_id: str, video_job_ids: list[str], expected_selection_revision: int,
    ) -> list[dict[str, str | None]]:
        return self._disposal.discard(
            project_id, shot_id=shot_id, video_job_ids=video_job_ids,
            expected_selection_revision=expected_selection_revision,
        )

    def finalize_video_candidate_disposal(self, project_id: str, video_job_ids: list[str]) -> None:
        self._disposal.finalize(project_id, video_job_ids)

    def video_output_has_retained_reference(self, project_id: str, uri: str) -> bool:
        return self._disposal.has_retained_reference(project_id, uri)

    @staticmethod
    def _shot_id(row: VideoJobRow) -> str:
        shot = row.snapshot.get("shot")
        if not isinstance(shot, dict) or not isinstance(shot.get("id"), str):
            raise InvalidTransitionError("video candidate has no valid frozen shot")
        return shot["id"]

    def _video_job_projection(self, session: Session, row: VideoJobRow, selections: dict[str, VideoCandidateSelectionRow]) -> dict[str, Any]:
        current = self._currentness.video_job_current_in_session(session, row)
        selection = selections.get(self._shot_id(row))
        return self._currentness.video_job_dict(
            row, current=current,
            selected=bool(selection and selection.selected_video_job_id == row.id and current),
        ) | {"selectionRevision": selection.revision if selection is not None else 0}
