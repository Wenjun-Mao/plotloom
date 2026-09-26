"""Typed media operations for a bound project database."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from .media_admission import KeyframeAdmission
from .media_assets import ManagedAssetPersistence
from .media_character_references import CharacterReferencePersistence
from .media_direct_video import DirectVideoJobPersistence
from .media_image_delivery import ImageJobDeliveryPersistence
from .media_image_preparation import ImageJobPreparationPersistence
from .media_keyframes import ReviewedKeyframePersistence
from .media_reference_proposals import CharacterReferenceProposalPersistence
from .media_art_reference_proposals import ArtReferenceProposalPersistence
from .media_same_person_reviews import SamePersonReviewPersistence
from .media_video_currentness import VideoJobCurrentness
from .media_video_segments import VideoSegmentPersistence
from .media_video_end_frames import VideoEndFrames
from .media_visual_intents import VisualIntentPersistence


JsonObject = dict[str, Any]


class ProjectMediaRepository:
    """Public media surface with fixed, named project-media owners."""

    def __init__(
        self,
        *,
        assets: ManagedAssetPersistence,
        intents: VisualIntentPersistence,
        admission: KeyframeAdmission,
        keyframes: ReviewedKeyframePersistence,
        references: CharacterReferencePersistence,
        proposals: CharacterReferenceProposalPersistence,
        art_references: ArtReferenceProposalPersistence,
        same_person: SamePersonReviewPersistence,
        image_preparation: ImageJobPreparationPersistence,
        image_delivery: ImageJobDeliveryPersistence,
        direct_video: DirectVideoJobPersistence,
        video_currentness: VideoJobCurrentness,
        video_segments: VideoSegmentPersistence,
        video_end_frames: VideoEndFrames,
    ) -> None:
        self._assets = assets
        self._intents = intents
        self._admission = admission
        self._keyframes = keyframes
        self._references = references
        self._proposals = proposals
        self._art_references = art_references
        self._same_person = same_person
        self._image_preparation = image_preparation
        self._image_delivery = image_delivery
        # These are intentionally narrow project-video ports, not access to a
        # media composition object or repository internals.
        self.direct_video = direct_video
        self.video_currentness = video_currentness
        self.video_segments = video_segments
        self.video_end_frames = video_end_frames

    def record_managed_import(
        self, project_id: str, *, original_hash: str, display_hash: str,
        mime_type: str, byte_size: int, width: int, height: int,
        declaration: JsonObject, publish: Callable[[], tuple[str, str]],
    ) -> JsonObject:
        return self._assets.record_managed_import(
            project_id, original_hash=original_hash, display_hash=display_hash,
            mime_type=mime_type, byte_size=byte_size, width=width, height=height,
            declaration=declaration, publish=publish,
        )

    def get_managed_asset_storage(self, project_id: str, asset_id: str) -> JsonObject:
        return self._assets.get_managed_asset_storage(project_id, asset_id)

    def list_managed_assets(self, project_id: str) -> list[JsonObject]:
        return self._assets.list_managed_assets(project_id)

    def create_visual_intent(
        self, project_id: str, asset_id: str, intent: JsonObject, *,
        consumed_draft: tuple[str, int, JsonObject] | None = None,
    ) -> JsonObject:
        return self._intents.create_visual_intent(
            project_id, asset_id, intent, consumed_draft=consumed_draft
        )

    def list_visual_intents(self, project_id: str) -> list[JsonObject]:
        return self._intents.list_visual_intents(project_id)

    def select_reviewed_keyframe(
        self, project_id: str, *, asset_id: str, shot_id: str, scene_id: str,
        expected_selection_revision: int, storyboard_revision: int, approval_id: str,
        compatibility_note: str, visual_intent_id: str, visual_intent_revision: int,
    ) -> JsonObject:
        return self._keyframes.select_reviewed_keyframe(
            project_id, asset_id=asset_id, shot_id=shot_id, scene_id=scene_id,
            expected_selection_revision=expected_selection_revision,
            storyboard_revision=storyboard_revision, approval_id=approval_id,
            compatibility_note=compatibility_note, visual_intent_id=visual_intent_id,
            visual_intent_revision=visual_intent_revision,
        )

    def create_still_preview(
        self, project_id: str, *, scene_id: str, shot_ids: list[str],
        expected_selection_revision: int, storyboard_revision: int, approval_id: str,
    ) -> JsonObject:
        return self._keyframes.create_still_preview(
            project_id, scene_id=scene_id, shot_ids=shot_ids,
            expected_selection_revision=expected_selection_revision,
            storyboard_revision=storyboard_revision, approval_id=approval_id,
        )

    def list_still_previews(self, project_id: str) -> list[JsonObject]:
        return self._keyframes.list_still_previews(project_id)

    def visual_selection_revision(self, project_id: str) -> int:
        return self._keyframes.visual_selection_revision(project_id)

    def list_current_reviewed_keyframes(self, project_id: str) -> list[JsonObject]:
        return self._admission.list_current_reviewed_keyframes(project_id)

    def reviewed_preview_dependencies_current(self, project_id: str, frame: JsonObject) -> bool:
        return self._keyframes.reviewed_preview_dependencies_current(project_id, frame)

    def create_character_reference_decision(
        self, project_id: str, *, character_id: str, primary_asset_id: str,
        complementary_asset_ids: list[str], expected_reference_revision: int,
        reviewer: str | None, notes: str | None, authority: str,
    ) -> JsonObject:
        return self._references.create_character_reference_decision(
            project_id, character_id=character_id, primary_asset_id=primary_asset_id,
            complementary_asset_ids=complementary_asset_ids,
            expected_reference_revision=expected_reference_revision, reviewer=reviewer,
            notes=notes, authority=authority,
        )

    def revoke_character_reference_decision(
        self, project_id: str, *, character_id: str, expected_reference_revision: int,
        reviewer: str, reason: str,
    ) -> JsonObject:
        return self._references.revoke_character_reference_decision(
            project_id, character_id=character_id,
            expected_reference_revision=expected_reference_revision, reviewer=reviewer,
            reason=reason,
        )

    def list_character_reference_decisions(self, project_id: str) -> list[JsonObject]:
        return self._references.list_character_reference_decisions(project_id)

    def attach_imported_character_appearance(self, project_id: str, *, character_id: str, asset_id: str, label: str, expected_cast_revision: int) -> JsonObject:
        return self._references.attach_imported_appearance(project_id, character_id=character_id, asset_id=asset_id, label=label, expected_cast_revision=expected_cast_revision)

    def list_imported_character_appearances(self, project_id: str) -> list[JsonObject]:
        return self._references.list_imported_appearances(project_id)

    def prepare_character_reference_proposal(
        self, project_id: str, *, character_id: str, cast_revision: int,
        visual_direction: str, parent_candidate_asset_id: str | None,
    ) -> JsonObject:
        return self._proposals.prepare_character_reference_proposal(
            project_id, character_id=character_id,
            cast_revision=cast_revision, visual_direction=visual_direction,
            parent_candidate_asset_id=parent_candidate_asset_id,
        )

    def character_reference_proposal_package_sources(
        self, project_id: str, proposal_id: str
    ) -> JsonObject:
        return self._proposals.character_reference_proposal_package_sources(project_id, proposal_id)

    def mark_character_reference_proposal_exported(
        self, project_id: str, proposal_id: str
    ) -> JsonObject:
        return self._proposals.mark_character_reference_proposal_exported(project_id, proposal_id)

    def cancel_character_reference_proposal(
        self, project_id: str, proposal_id: str, reason: str
    ) -> JsonObject:
        return self._proposals.cancel_character_reference_proposal(
            project_id, proposal_id, reason
        )

    def character_reference_proposal_delivery_context(
        self, project_id: str, proposal_id: str
    ) -> JsonObject:
        return self._proposals.character_reference_proposal_delivery_context(project_id, proposal_id)

    def record_character_reference_proposal_rejection(
        self, project_id: str, proposal_id: str, code: str, *, publication_phase: str | None = None,
    ) -> None:
        self._proposals.record_character_reference_proposal_rejection(
            project_id, proposal_id, code, publication_phase=publication_phase,
        )

    def record_character_reference_proposal_delivery(
        self, project_id: str, proposal_id: str, *, delivery_id: str,
        manifest: JsonObject, manifest_hash: str, outputs: list[JsonObject],
        publish: Callable[[JsonObject], tuple[str, str]],
    ) -> JsonObject:
        return self._proposals.record_character_reference_proposal_delivery(
            project_id, proposal_id, delivery_id=delivery_id, manifest=manifest,
            manifest_hash=manifest_hash, outputs=outputs, publish=publish,
        )

    def list_character_reference_proposals(self, project_id: str) -> list[JsonObject]:
        return self._proposals.list_character_reference_proposals(project_id)

    def prepare_art_reference_proposal(
        self, project_id: str, *, subject_type: str, subject_id: str, render_direction: str,
    ) -> JsonObject:
        return self._art_references.prepare_art_reference_proposal(
            project_id, subject_type=subject_type, subject_id=subject_id, render_direction=render_direction
        )

    def art_reference_proposal_package_sources(self, project_id: str, proposal_id: str) -> JsonObject:
        return self._art_references.art_reference_proposal_package_sources(project_id, proposal_id)

    def mark_art_reference_proposal_exported(self, project_id: str, proposal_id: str) -> JsonObject:
        return self._art_references.mark_art_reference_proposal_exported(project_id, proposal_id)

    def cancel_art_reference_proposal(self, project_id: str, proposal_id: str, reason: str) -> JsonObject:
        return self._art_references.cancel_art_reference_proposal(project_id, proposal_id, reason)

    def art_reference_proposal_delivery_context(self, project_id: str, proposal_id: str) -> JsonObject:
        return self._art_references.art_reference_proposal_delivery_context(project_id, proposal_id)

    def record_art_reference_proposal_rejection(self, project_id: str, proposal_id: str, code: str) -> None:
        self._art_references.record_art_reference_proposal_rejection(project_id, proposal_id, code)

    def record_art_reference_proposal_delivery(
        self, project_id: str, proposal_id: str, *, delivery_id: str, manifest: JsonObject,
        manifest_hash: str, outputs: list[JsonObject], publish: Callable[[JsonObject], tuple[str, str]],
    ) -> JsonObject:
        return self._art_references.record_art_reference_proposal_delivery(
            project_id, proposal_id, delivery_id=delivery_id, manifest=manifest,
            manifest_hash=manifest_hash, outputs=outputs, publish=publish,
        )

    def list_art_reference_proposals(self, project_id: str) -> list[JsonObject]:
        return self._art_references.list_art_reference_proposals(project_id)

    def create_art_reference_decision(
        self, project_id: str, *, subject_type: str, subject_id: str, asset_id: str,
        expected_reference_revision: int,
    ) -> JsonObject:
        return self._art_references.create_art_reference_decision(
            project_id, subject_type=subject_type, subject_id=subject_id, asset_id=asset_id,
            expected_reference_revision=expected_reference_revision,
        )

    def list_art_reference_decisions(self, project_id: str) -> JsonObject:
        return self._art_references.list_art_reference_decisions(project_id)

    def record_same_person_review(
        self, project_id: str, *, binding_id: str, expected_review_revision: int,
        reviewer: str, comparisons: list[JsonObject], notes: str,
    ) -> JsonObject:
        return self._same_person.record_same_person_review(
            project_id, binding_id=binding_id,
            expected_review_revision=expected_review_revision, reviewer=reviewer,
            comparisons=comparisons, notes=notes,
        )

    def list_same_person_reviews(self, project_id: str) -> list[JsonObject]:
        return self._same_person.list_same_person_reviews(project_id)

    def prepare_image_job(
        self, project_id: str, *, approval_id: str, shot_id: str,
        storyboard_revision: int, presentation_change: str,
        parent_candidate_asset_id: str | None = None,
        keyframe_adaptation: JsonObject | None = None, contract_version: int = 2,
        consumed_draft: tuple[str, int, JsonObject] | None = None,
    ) -> JsonObject:
        return self._image_preparation.prepare_image_job(
            project_id, approval_id=approval_id, shot_id=shot_id,
            storyboard_revision=storyboard_revision,
            parent_candidate_asset_id=parent_candidate_asset_id,
            keyframe_adaptation=keyframe_adaptation,
            presentation_change=presentation_change, contract_version=contract_version,
            consumed_draft=consumed_draft,
        )

    def image_job_package_sources(self, project_id: str, job_id: str) -> JsonObject:
        return self._image_delivery.image_job_package_sources(project_id, job_id)

    def mark_image_job_exported(self, project_id: str, job_id: str) -> JsonObject:
        return self._image_delivery.mark_image_job_exported(project_id, job_id)

    def cancel_image_job(self, project_id: str, job_id: str, reason: str) -> JsonObject:
        return self._image_delivery.cancel_image_job(project_id, job_id, reason)

    def image_job_delivery_context(self, project_id: str, job_id: str) -> JsonObject:
        return self._image_delivery.image_job_delivery_context(project_id, job_id)

    def record_image_job_delivery_rejection(
        self, project_id: str, job_id: str, code: str
    ) -> None:
        self._image_delivery.record_image_job_delivery_rejection(project_id, job_id, code)

    def record_image_job_delivery(
        self, project_id: str, job_id: str, *, delivery_id: str, manifest: JsonObject,
        manifest_hash: str, outputs: Sequence[JsonObject],
        publish: Callable[[JsonObject], tuple[str, str]],
    ) -> JsonObject:
        return self._image_delivery.record_image_job_delivery(
            project_id, job_id, delivery_id=delivery_id, manifest=manifest,
            manifest_hash=manifest_hash, outputs=outputs, publish=publish,
        )

    def list_image_jobs(self, project_id: str) -> list[JsonObject]:
        return self._image_delivery.list_image_jobs(project_id)
