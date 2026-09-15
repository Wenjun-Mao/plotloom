"""Video-job currentness and durable record projections."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ...domain import ProjectLifecycleStatus, StageName
from ...exceptions import InvalidTransitionError, NotFoundError, SchemaResetRequiredError
from ..codec import _stored_utc, stable_hash
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


class VideoJobCurrentness:
    """Own session-local video applicability and stable record projections."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        admission: KeyframeAdmission,
        references: CharacterReferencePersistence,
        same_person: SamePersonReviewPersistence,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._references = references
        self._same_person = same_person

    @staticmethod
    def video_job_id() -> str:
        return new_video_job_id()

    @staticmethod
    def video_job_dict(row: VideoJobRow, *, current: bool, selected: bool = False) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "state": row.state,
            "requestHash": row.request_hash, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "requestedSeconds": row.requested_seconds,
            "providerPredictionId": row.provider_prediction_id,
            "outputHash": row.output_hash, "observed": row.observed, "error": row.error,
            "current": current, "selected": selected,
            "createdAt": _stored_utc(row.created_at).isoformat(),
            "dispatchedAt": _stored_utc(row.dispatched_at).isoformat() if row.dispatched_at else None,
            "cancelRequestedAt": _stored_utc(row.cancel_requested_at).isoformat() if row.cancel_requested_at else None,
        }

    @staticmethod
    def video_job_tracks_paid_wan_pilot(row: VideoJobRow) -> bool:
        """Preserve V1 Wan accounting without charging local backends.

        Historical snapshots have no adapter or cost-policy fields.  Their
        exact documented Atlas capability record is the compatibility signal;
        unknown future contracts fail closed for accounting rather than being
        silently treated as paid Wan work.
        """

        provider = row.snapshot.get("provider")
        if not isinstance(provider, dict):
            return False
        if provider.get("costPolicy") == "wan_paid_pilot_v1":
            return True
        return (
            "costPolicy" not in provider
            and provider.get("provider") == "atlascloud"
            and provider.get("model") == "alibaba/wan-3.0/image-to-video"
            and provider.get("capabilityVersion") == 1
            and provider.get("imageField") == "image"
        )

    def video_job_current_in_session(self, session: Session, row: VideoJobRow) -> bool:
        project = session.get(ProjectRow, row.project_id)
        snapshot = row.snapshot
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        # Currentness must not make a mutated frozen request dispatchable. The
        # row retains both an identity-bound request hash and a content hash so
        # a change to an explicit input-frame mode cannot borrow the original
        # reviewed selection's currentness.
        if (
            stable_hash(snapshot) != row.snapshot_hash
            or stable_hash({"snapshot": snapshot, "idempotencyKey": row.idempotency_key})
            != row.request_hash
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
