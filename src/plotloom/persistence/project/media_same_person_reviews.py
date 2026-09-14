"""Explicit same-person review persistence for identity-aware image candidates."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError, SchemaResetRequiredError
from ..codec import _stored_utc
from ..schema import (
    ImageJobCandidateRow,
    ImageJobRow,
    ReviewedShotBindingRow,
    SamePersonReviewRow,
    SamePersonReviewStateRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence


class SamePersonReviewPersistence:
    """Own the human identity-review facts required for preview admission."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        admission: KeyframeAdmission,
        references: CharacterReferencePersistence,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._references = references

    @staticmethod
    def _same_person_review_state_in_session(
        session: Session, project_id: str, now: datetime
    ) -> SamePersonReviewStateRow:
        state = session.get(SamePersonReviewStateRow, project_id)
        if state is None:
            state = SamePersonReviewStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _same_person_review_dict(row: SamePersonReviewRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "bindingId": row.binding_id,
            "reviewRevision": row.review_revision, "referenceBindings": list(row.reference_bindings),
            "comparisons": list(row.comparisons), "reviewer": row.reviewer, "notes": row.notes,
            "current": current, "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def identity_mapping_for_binding_in_session(
        self, session: Session, binding: ReviewedShotBindingRow
    ) -> list[dict[str, Any]] | None:
        candidate = session.scalar(
            select(ImageJobCandidateRow)
            .where(ImageJobCandidateRow.asset_id == binding.asset_id)
            .order_by(ImageJobCandidateRow.created_at.desc()).limit(1)
        )
        if candidate is None:
            return None
        job = session.get(ImageJobRow, candidate.job_id)
        if job is None or job.request.get("schemaVersion") != 3:
            return None
        snapshot = job.request.get("frozenSnapshot")
        mapping = snapshot.get("characterIdentity") if isinstance(snapshot, dict) else None
        if not isinstance(mapping, list) or any(not isinstance(item, dict) for item in mapping):
            return None
        return mapping

    def same_person_review_is_current_in_session(
        self, session: Session, project_id: str, review: SamePersonReviewRow
    ) -> bool:
        binding = session.get(ReviewedShotBindingRow, review.binding_id)
        if binding is None or binding.project_id != project_id:
            return False
        try:
            approval = self._admission.approval_is_active_in_session(session, binding.approval_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not self._admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
            return False
        mapping = self.identity_mapping_for_binding_in_session(session, binding)
        if mapping is None:
            return False
        if any(item.get("judgment") != "pass" for item in review.comparisons):
            return False
        expected = {item.get("characterId"): item for item in mapping}
        review_refs = {item.get("characterId"): item for item in review.reference_bindings}
        if set(expected) != set(review_refs):
            return False
        try:
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
        except (NotFoundError, SchemaResetRequiredError):
            return False
        characters = {item.id: item for item in bible.characters}
        for character_id, frozen in expected.items():
            character = characters.get(character_id)
            current = self._references.current_character_reference_in_session(session, project_id, character) if character else None
            reviewed = review_refs[character_id]
            if (
                current is None
                or current.id != frozen.get("referenceDecisionId")
                or current.reference_revision != frozen.get("referenceRevision")
                or reviewed.get("referenceDecisionId") != current.id
                or reviewed.get("referenceRevision") != current.reference_revision
                or reviewed.get("assetHashes") != [item.get("originalHash") for item in frozen.get("assets", [])]
            ):
                return False
        return True

    def record_same_person_review(
        self,
        project_id: str,
        *,
        binding_id: str,
        expected_review_revision: int,
        reviewer: str,
        comparisons: list[dict[str, Any]],
        notes: str,
    ) -> dict[str, Any]:
        """Persist an explicit human judgment about a v3 generated keyframe."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if binding is None or binding.project_id != project_id:
                raise NotFoundError("reviewed keyframe binding not found")
            mapping = self.identity_mapping_for_binding_in_session(session, binding)
            if mapping is None:
                raise InvalidTransitionError("same-person review is only required for identity-aware generated keyframes")
            expected_ids = [item["characterId"] for item in mapping]
            comparison_ids = [item["characterId"] for item in comparisons]
            if comparison_ids != expected_ids:
                raise InvalidTransitionError("same-person review must cover each frozen visible character in role-mapped order")
            now = utc_now()
            state = self._same_person_review_state_in_session(session, project_id, now)
            if state.revision != expected_review_revision:
                raise RevisionConflictError("same-person-review", expected_review_revision, state.revision)
            reference_bindings = [{
                "characterId": item["characterId"], "referenceDecisionId": item["referenceDecisionId"],
                "referenceRevision": item["referenceRevision"],
                "assetHashes": [asset["originalHash"] for asset in item["assets"]],
            } for item in mapping]
            state.revision += 1
            state.updated_at = now
            review = SamePersonReviewRow(
                id=new_id(), project_id=project_id, binding_id=binding_id, review_revision=state.revision,
                reference_bindings=reference_bindings, comparisons=comparisons, reviewer=reviewer.strip(),
                notes=notes.strip(), created_at=now,
            )
            session.add(review)
            session.flush()
            return self._same_person_review_dict(review, current=self.same_person_review_is_current_in_session(session, project_id, review)) | {"stateRevision": state.revision}

    def list_same_person_reviews(self, project_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            state = session.get(SamePersonReviewStateRow, project_id)
            rows = session.scalars(
                select(SamePersonReviewRow).where(SamePersonReviewRow.project_id == project_id)
                .order_by(SamePersonReviewRow.created_at.desc(), SamePersonReviewRow.id.desc())
            ).all()
            return {"revision": state.revision if state else 0, "reviews": [
                self._same_person_review_dict(row, current=self.same_person_review_is_current_in_session(session, project_id, row))
                for row in rows
            ]}

    def current_same_person_review_for_binding(
        self, session: Session, project_id: str, binding: ReviewedShotBindingRow
    ) -> SamePersonReviewRow | None:
        mapping = self.identity_mapping_for_binding_in_session(session, binding)
        if mapping is None:
            return None
        rows = session.scalars(
            select(SamePersonReviewRow)
            .where(SamePersonReviewRow.project_id == project_id, SamePersonReviewRow.binding_id == binding.id)
            .order_by(SamePersonReviewRow.review_revision.desc())
        ).all()
        return next((row for row in rows if self.same_person_review_is_current_in_session(session, project_id, row)), None)
