"""Video-job currentness and durable record projections."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from ...domain import ProjectLifecycleStatus, StageName
from ...exceptions import InvalidTransitionError, NotFoundError, SchemaResetRequiredError
from ..codec import _stored_utc
from ..schema import (
    ManagedAssetRow,
    ProjectRow,
    ReviewedShotBindingRow,
    SamePersonReviewRow,
    VideoJobRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_identifiers import new_video_job_id
from .media_same_person_reviews import SamePersonReviewPersistence
from .media_video_source import VideoSourceTiming
from .media_video_end_frames import VideoEndFrames
from .media_shot_presentations import ShotPresentations
from .media_video_integrity import frozen_video_request_is_valid


class VideoJobCurrentness:
    """Own session-local video applicability and stable record projections."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        admission: KeyframeAdmission,
        references: CharacterReferencePersistence,
        same_person: SamePersonReviewPersistence,
        source_timing: VideoSourceTiming,
        end_frames: VideoEndFrames,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._references = references
        self._same_person = same_person
        self._source_timing = source_timing
        self._end_frames = end_frames
        self.presentations = ShotPresentations(access, canonical, admission)

    @staticmethod
    def video_job_id() -> str:
        return new_video_job_id()

    def video_job_dict(self, session: Session, row: VideoJobRow, *, current: bool | None = None, selected: bool = False) -> dict[str, Any]:
        project = self._access.rows.project(session, row.project_id)
        lifecycle = ProjectLifecycleStatus(project.lifecycle_status)
        input_status = self.video_job_input_status_in_session(session, row)
        admitted = lifecycle == ProjectLifecycleStatus.ACTIVE and input_status == "current"
        return {
            "id": row.id, "projectId": row.project_id, "state": row.state,
            "requestHash": row.request_hash, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "requestedSeconds": row.requested_seconds,
            "providerPredictionId": row.provider_prediction_id,
            "outputHash": row.output_hash, "observed": row.observed, "error": row.error,
            "lifecycleStatus": lifecycle.value, "inputStatus": input_status,
            "current": admitted if current is None else current and admitted,
            "selected": selected and admitted,
            "createdAt": _stored_utc(row.created_at).isoformat(),
            "dispatchedAt": _stored_utc(row.dispatched_at).isoformat() if row.dispatched_at else None,
            "cancelRequestedAt": _stored_utc(row.cancel_requested_at).isoformat() if row.cancel_requested_at else None,
        }

    @staticmethod
    def video_job_tracks_paid_wan_pilot(row: VideoJobRow) -> bool:
        """Accounting is explicit in the current frozen provider contract."""
        provider = row.snapshot.get("provider") if isinstance(row.snapshot, dict) else None
        return isinstance(provider, dict) and provider.get("costPolicy") == "wan_paid_pilot_v1"

    def video_job_current_in_session(self, session: Session, row: VideoJobRow) -> bool:
        project = session.get(ProjectRow, row.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        return self.video_job_input_status_in_session(session, row) == "current"

    def video_job_input_status_in_session(self, session: Session, row: VideoJobRow) -> Literal["current", "stale", "invalid"]:
        if not frozen_video_request_is_valid(row):
            return "invalid"
        return "current" if self._inputs_match_in_session(session, row) else "stale"

    def _inputs_match_in_session(self, session: Session, row: VideoJobRow) -> bool:
        snapshot = row.snapshot
        frozen_shot = snapshot.get("shot") if isinstance(snapshot, dict) else None
        if not isinstance(frozen_shot, dict) or not isinstance(frozen_shot.get("id"), str) or not self.presentations.matches(
            session, row.project_id, frozen_shot["id"], snapshot.get("shotPresentation")
        ):
            return False
        source_timing = snapshot.get("sourceTiming") if isinstance(snapshot, dict) else None
        if source_timing is not None and (
            not isinstance(frozen_shot, dict)
            or not isinstance(frozen_shot.get("id"), str)
            or not isinstance(frozen_shot.get("durationUnits"), int)
            or not self._source_timing.binding_is_current(
                session, row.project_id, frozen_shot["id"],
                frozen_shot["durationUnits"], source_timing,
            )
        ):
            return False
        if snapshot.get("provider", {}).get("adapterId") == "minimax_h3_gateway" and not self._end_frames.decision_is_current(
            session, row.project_id, frozen_shot["id"], snapshot.get("endFrame")
        ):
            return False
        try:
            approval = self._admission.approval_is_active_in_session(session, str(snapshot["approvalId"]))
        except (KeyError, InvalidTransitionError, NotFoundError):
            return False
        binding = session.get(ReviewedShotBindingRow, snapshot.get("keyframe", {}).get("bindingId"))
        asset = session.get(ManagedAssetRow, snapshot.get("keyframe", {}).get("assetId"))
        identity = snapshot.get("identityLineage", [])
        if not isinstance(identity, list):
            return False
        review_id = snapshot.get("samePersonReviewId")
        if identity:
            try:
                bible = self._canonical._load_stage_payload(session, row.project_id, StageName.STORY_BIBLE)
            except (NotFoundError, SchemaResetRequiredError):
                return False
            characters = {character.id: character for character in bible.characters}
            for frozen in identity:
                if not isinstance(frozen, dict):
                    return False
                character = characters.get(frozen.get("characterId"))
                current = self._references.current_character_reference_in_session(session, row.project_id, character) if character else None
                if (
                    current is None
                    or current.id != frozen.get("referenceDecisionId")
                    or current.reference_revision != frozen.get("referenceRevision")
                    or current.character_context_hash != frozen.get("characterContextHash")
                ):
                    return False
                expected_assets = {item["assetId"]: item["originalHash"] for item in current.asset_hashes}
                frozen_assets = frozen.get("assets")
                if (
                    not isinstance(frozen_assets, list)
                    or len(frozen_assets) != len(expected_assets)
                    or any(
                        not isinstance(item, dict)
                        or expected_assets.get(item.get("assetId")) != item.get("originalHash")
                        for item in frozen_assets
                    )
                ):
                    return False
            # A generated V3 keyframe additionally needs its independent,
            # explicitly attributed same-person review. An imported selected
            # keyframe follows the separate provenance path: its attributed
            # keyframe-selection comparison and current character-reference
            # decision are frozen together below.
            if review_id is not None:
                review = session.get(SamePersonReviewRow, review_id)
                if review is None or not self._same_person.same_person_review_is_current_in_session(session, row.project_id, review):
                    return False
                if binding is None or review.binding_id != binding.id:
                    return False
        return bool(
            approval.project_id == row.project_id
            and approval.entity_revision_id == snapshot.get("storyboardEntityRevisionId")
            and binding is not None and asset is not None
            and binding.project_id == row.project_id
            and binding.shot_id == snapshot.get("shot", {}).get("id")
            and binding.selection_revision == snapshot.get("keyframe", {}).get("selectionRevision")
            and asset.original_hash == snapshot.get("keyframe", {}).get("originalHash")
            and self._admission.reviewed_binding_admission_eligible_in_session(session, row.project_id, binding, approval=approval)
        )
