"""Per-shot presentation review, projection and currentness ownership."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, new_id, utc_now
from ...exceptions import (
    InvalidTransitionError,
    NotFoundError,
    RevisionConflictError,
    SchemaResetRequiredError,
)
from ...shot_presentation import (
    ShotPresentationRequest,
    effective_projection,
    reviewed_projection,
    source_package,
)
from ..schema import ReviewedShotBindingRow, VisualSelectionStateRow
from ..schema.project_shot_presentation import ShotPresentationRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence

if TYPE_CHECKING:
    from .media_admission import KeyframeAdmission


class ShotPresentations:
    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence, admission: KeyframeAdmission):
        self._access = access
        self._canonical = canonical
        self._admission = admission

    @staticmethod
    def latest(session: Session, project_id: str, shot_id: str) -> ShotPresentationRow | None:
        return session.scalar(select(ShotPresentationRow).where(
            ShotPresentationRow.project_id == project_id, ShotPresentationRow.shot_id == shot_id
        ).order_by(ShotPresentationRow.revision.desc()).limit(1))

    def sources(self, session: Session, project_id: str, shot_id: str) -> dict[str, Any]:
        from .media_image_currentness import ImageJobCurrentness
        board = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
        bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
        beats = self._canonical._load_stage_payload(session, project_id, StageName.SCENE_BEATS)
        shot = next((item for item in board.shots if item.id == shot_id), None)
        if shot is None:
            raise InvalidTransitionError("presentation must target a current storyboard shot")
        ordered = sorted((item for item in board.shots if item.scene_id == shot.scene_id), key=lambda item: item.order)
        index = next(index for index, item in enumerate(ordered) if item.id == shot_id)
        predecessor = ordered[index - 1].model_dump(mode="json", by_alias=True) if index else None
        context = ImageJobCurrentness.image_job_resolved_context(shot=shot, storyboard=board, story_bible=bible, scene_beats=beats)
        return source_package(shot.model_dump(mode="json", by_alias=True), context, predecessor)

    def current(self, session: Session, project_id: str, shot_id: str) -> dict[str, Any] | None:
        row = self.latest(session, project_id, shot_id)
        if row is None:
            return None
        try:
            review = ShotPresentationRequest.model_validate(row.decision["review"])
            source = self.sources(session, project_id, shot_id)
            if reviewed_projection(source, review) != row.decision["effectiveShot"]:
                raise ValueError("effective presentation differs from reviewed sources")
        except (ValueError, KeyError, TypeError) as error:
            raise InvalidTransitionError("shot presentation is stale or malformed; explicitly review it again") from error
        approval = self._admission.approval_is_active_in_session(session, review.approval_id)
        if approval.project_id != project_id or approval.subject_revision != review.storyboard_revision:
            raise InvalidTransitionError("shot presentation approval is stale; explicitly review it again")
        if row.decision["sourceHash"] != source["sourceHash"]:
            raise InvalidTransitionError("shot presentation source is stale; explicitly review it again")
        return {"id": row.id, "revision": row.revision, **row.decision}

    def matches(self, session: Session, project_id: str, shot_id: str, frozen: dict | None) -> bool:
        try:
            return self.current(session, project_id, shot_id) == frozen
        except (InvalidTransitionError, ValueError, NotFoundError, SchemaResetRequiredError):
            return False

    @classmethod
    def binding_matches(cls, session: Session, binding: ReviewedShotBindingRow) -> bool:
        row = cls.latest(session, binding.project_id, binding.shot_id)
        return row is None or binding.selection_revision > row.decision["bindingRevisionFloor"]

    def project(self, session: Session, project_id: str, shot: Any, context: dict) -> tuple[Any, dict, dict | None]:
        decision = self.current(session, project_id, shot.id)
        effective, resolved = effective_projection(shot, context, decision)
        return effective, resolved, decision

    def get(self, project_id: str, shot_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            source = self.sources(session, project_id, shot_id)
            row = self.latest(session, project_id, shot_id)
            decision = {"id": row.id, "revision": row.revision, **row.decision} if row else None
            try:
                self.current(session, project_id, shot_id)
                current = True
            except (InvalidTransitionError, ValueError, NotFoundError, SchemaResetRequiredError):
                current = False
            return {"source": source, "revision": row.revision if row else 0,
                    "decision": decision, "current": current}

    def review(self, project_id: str, shot_id: str, request: ShotPresentationRequest) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            approval = self._admission.approval_is_active_in_session(session, request.approval_id)
            if approval.project_id != project_id or approval.subject_revision != request.storyboard_revision:
                raise InvalidTransitionError("presentation approval does not match storyboard revision")
            previous = self.latest(session, project_id, shot_id)
            revision = previous.revision if previous else 0
            if revision != request.expected_revision:
                raise RevisionConflictError("shot-presentation", request.expected_revision, revision)
            source = self.sources(session, project_id, shot_id)
            try:
                effective = reviewed_projection(source, request)
                from ...canonical_schema import ShotV2
                ShotV2.model_validate(effective)
            except ValueError as error:
                raise InvalidTransitionError(str(error)) from error
            decision = {"sourceHash": source["sourceHash"], "source": source,
                        "review": request.model_dump(mode="json", by_alias=True), "effectiveShot": effective}
            state = session.get(VisualSelectionStateRow, project_id)
            decision["bindingRevisionFloor"] = state.revision if state else 0
            session.add(ShotPresentationRow(id=new_id(), project_id=project_id, shot_id=shot_id,
                                           revision=revision + 1, decision=decision, created_at=utc_now()))
        return self.get(project_id, shot_id)
