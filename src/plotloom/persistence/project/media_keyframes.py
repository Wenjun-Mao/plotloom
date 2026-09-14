"""Reviewed-keyframe selection and still-preview persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...domain import StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ImageJobCandidateRow,
    ImageJobRow,
    ManagedAssetRow,
    ReviewedShotBindingRow,
    SamePersonReviewRow,
    StillPreviewRow,
    VisualIntentRow,
    VisualSelectionStateRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_image_currentness import ImageJobCurrentness
from .media_same_person_reviews import SamePersonReviewPersistence


class ReviewedKeyframePersistence:
    """Own reviewed selection history and immutable still-preview receipts."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        admission: KeyframeAdmission,
        image_currentness: ImageJobCurrentness,
        same_person: SamePersonReviewPersistence,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._image_currentness = image_currentness
        self._same_person = same_person

    def select_reviewed_keyframe(
        self,
        project_id: str,
        *,
        asset_id: str,
        shot_id: str,
        scene_id: str,
        expected_selection_revision: int,
        storyboard_revision: int,
        approval_id: str,
        compatibility_note: str,
        visual_intent_id: str,
        visual_intent_revision: int,
    ) -> dict[str, Any]:
        """Append an immutable reviewed binding under one lifecycle writer lease."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            now = utc_now()
            state = self._admission.selection_state_in_session(session, project_id, now)
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            approval = self._admission.approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("approval does not match the requested storyboard revision")
            head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if head.revision != storyboard_revision or head.entity_revision_id != approval.entity_revision_id:
                raise RevisionConflictError("storyboard", storyboard_revision, head.revision)
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            generated_candidate = session.scalar(
                select(ImageJobCandidateRow)
                .where(ImageJobCandidateRow.asset_id == asset_id)
                .order_by(ImageJobCandidateRow.created_at.desc())
                .limit(1)
            )
            if generated_candidate is not None:
                generated_job = session.get(ImageJobRow, generated_candidate.job_id)
                if generated_job is None or not self._image_currentness.image_job_is_current_in_session(session, generated_job):
                    raise InvalidTransitionError(
                        "image-job candidate is no longer applicable and cannot be selected"
                    )
            intent = session.get(VisualIntentRow, visual_intent_id)
            if (
                intent is None or intent.project_id != project_id or intent.asset_id != asset_id
                or intent.revision != visual_intent_revision
            ):
                raise InvalidTransitionError("reviewed keyframe must bind an exact current-project visual intent")
            latest_intent = self._admission.latest_visual_intent_for_role_in_session(
                session, project_id, asset_id, intent.intent.get("role")
            )
            if latest_intent is None or latest_intent.id != intent.id:
                raise InvalidTransitionError("reviewed keyframe must bind the current visual intent revision")
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None or shot.scene_id != scene_id:
                raise InvalidTransitionError("reviewed keyframe must target a current shot in its declared scene")
            state.revision += 1
            state.updated_at = now
            binding = ReviewedShotBindingRow(
                id=new_id(), project_id=project_id, asset_id=asset_id,
                visual_intent_id=intent.id, visual_intent_revision=intent.revision,
                storyboard_entity_revision_id=approval.entity_revision_id,
                approval_id=approval.id, shot_id=shot_id, scene_id=scene_id,
                storyboard_revision=storyboard_revision,
                selection_revision=state.revision, compatibility_note=compatibility_note,
                created_at=now,
            )
            session.add(binding)
            session.flush()
            return {
                "id": binding.id, "assetId": asset_id, "shotId": shot_id,
                "sceneId": scene_id, "selectionRevision": state.revision,
                "storyboardRevision": storyboard_revision, "visualIntentId": intent.id,
                "visualIntentRevision": intent.revision,
            }

    def create_still_preview(
        self,
        project_id: str,
        *,
        scene_id: str,
        shot_ids: list[str],
        expected_selection_revision: int,
        storyboard_revision: int,
        approval_id: str,
    ) -> dict[str, Any]:
        """Freeze one coherent, contiguous reviewed still sequence."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            state = self._admission.selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            approval = self._admission.approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("approval does not match the requested storyboard revision")
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            scene_shots = sorted(
                (item for item in storyboard.shots if item.scene_id == scene_id), key=lambda item: item.order
            )
            ordered_ids = [item.id for item in scene_shots]
            try:
                start = ordered_ids.index(shot_ids[0])
            except ValueError as error:
                raise InvalidTransitionError("preview shots must belong to the requested current scene") from error
            if ordered_ids[start : start + len(shot_ids)] != shot_ids:
                raise InvalidTransitionError("preview shots must be one contiguous scene subset in storyboard order")
            bindings = session.scalars(
                select(ReviewedShotBindingRow)
                .where(ReviewedShotBindingRow.project_id == project_id, ReviewedShotBindingRow.shot_id.in_(shot_ids))
                .order_by(ReviewedShotBindingRow.selection_revision.desc())
            ).all()
            latest: dict[str, ReviewedShotBindingRow] = {}
            for binding in bindings:
                latest.setdefault(binding.shot_id, binding)
            if set(latest) != set(shot_ids):
                raise InvalidTransitionError("preview has missing reviewed keyframes")
            frames = []
            by_id = {shot.id: shot for shot in scene_shots}
            for shot_id in shot_ids:
                binding = latest[shot_id]
                if (
                    binding.scene_id != scene_id
                    or binding.storyboard_entity_revision_id != approval.entity_revision_id
                    or binding.approval_id != approval.id
                ):
                    raise InvalidTransitionError("reviewed keyframe does not match the current approved storyboard")
                intent = session.get(VisualIntentRow, binding.visual_intent_id)
                if intent is None or intent.asset_id != binding.asset_id or intent.revision != binding.visual_intent_revision:
                    raise InvalidTransitionError("reviewed keyframe is missing its exact visual intent")
                if not self._admission.reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding, approval=approval
                ):
                    raise InvalidTransitionError(
                        "reviewed keyframe is no longer current for preview admission"
                    )
                asset = session.get(ManagedAssetRow, binding.asset_id)
                if asset is None:
                    raise InvalidTransitionError("preview references unavailable managed media")
                frame: dict[str, Any] = {
                    "shotId": shot_id, "assetId": asset.id, "displayHash": asset.display_hash,
                    "durationMs": by_id[shot_id].duration_units,
                    "bindingId": binding.id, "visualIntentId": intent.id,
                    "visualIntentRevision": intent.revision,
                }
                identity_mapping = self._same_person.identity_mapping_for_binding_in_session(session, binding)
                if identity_mapping:
                    review = self._same_person.current_same_person_review_for_binding(session, project_id, binding)
                    if review is None:
                        raise InvalidTransitionError(
                            "identity-aware reviewed keyframe needs a current explicit same-person review before preview admission"
                        )
                    frame["identityReviewId"] = review.id
                    frame["identityReferenceDecisionIds"] = [item["referenceDecisionId"] for item in identity_mapping]
                frames.append(frame)
            manifest = {
                "projectionVersion": 1, "sceneId": scene_id, "shotIds": shot_ids,
                "storyboardRevision": storyboard_revision, "storyboardEntityRevisionId": approval.entity_revision_id,
                "approvalId": approval.id, "approvalGateSetVersion": approval.gate_set_version,
                # Database JSON keys are canonical stage strings already;
                # preserve them verbatim so the frozen receipt matches the
                # approval-closure projection used by ``preview_view``.
                "canonicalInputRevisions": dict(approval.canonical_input_revisions),
                "selectionRevision": state.revision, "frames": frames,
            }
            preview = StillPreviewRow(
                id=new_id(), project_id=project_id,
                storyboard_entity_revision_id=approval.entity_revision_id,
                approval_id=approval.id, scene_id=scene_id,
                selection_revision=state.revision, manifest=manifest,
                manifest_hash=stable_hash(manifest), created_at=utc_now(),
            )
            session.add(preview)
            session.flush()
            return {"id": preview.id, "manifest": preview.manifest, "manifestHash": preview.manifest_hash, "createdAt": _stored_utc(preview.created_at).isoformat()}

    def list_still_previews(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            previews = session.scalars(
                select(StillPreviewRow)
                .where(StillPreviewRow.project_id == project_id)
                .order_by(StillPreviewRow.created_at.desc(), StillPreviewRow.id.desc())
            ).all()
            return [
                {"id": item.id, "manifest": item.manifest, "manifestHash": item.manifest_hash, "createdAt": _stored_utc(item.created_at).isoformat()}
                for item in previews
            ]

    def visual_selection_revision(self, project_id: str) -> int:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            state = session.get(VisualSelectionStateRow, project_id)
            return state.revision if state is not None else 0

    def reviewed_preview_dependencies_current(self, project_id: str, frame: dict[str, Any]) -> bool:
        """Check only the frozen frame's reviewed binding and intent stream."""

        with self._access.leases.read() as session:
            binding = session.get(ReviewedShotBindingRow, frame["bindingId"])
            if (
                binding is None or binding.project_id != project_id
                or binding.asset_id != frame["assetId"]
                or binding.visual_intent_id != frame.get("visualIntentId")
                or binding.visual_intent_revision != frame.get("visualIntentRevision")
            ):
                return False
            if not self._admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding):
                return False
            review_id = frame.get("identityReviewId")
            if review_id is None:
                # Historic/P0 frames and V3 character-free shots have no
                # same-person dependency. A visible V3 cast must have had a
                # review attached during preview admission.
                return not self._same_person.identity_mapping_for_binding_in_session(session, binding)
            review = session.get(SamePersonReviewRow, review_id)
            return review is not None and self._same_person.same_person_review_is_current_in_session(session, project_id, review)
