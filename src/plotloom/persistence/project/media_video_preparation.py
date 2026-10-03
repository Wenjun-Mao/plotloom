"""Frozen video preparation; lifecycle and accounting stay separate."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...domain import StageName, utc_now
from ...exceptions import (
    IdempotencyConflictError,
    InvalidTransitionError,
    KeyframeAspectMismatchError,
    RevisionConflictError,
)
from ...keyframe_preparation import has_matching_aspect
from ...video_provider import VideoBackendBinding, VideoProductionContract
from ..codec import stable_hash
from ..schema import (
    ManagedAssetRow,
    ReviewedShotBindingRow,
    VideoJobRow,
    VisualIntentRow,
)


class VideoJobPreparation:
    def prepare_video_job(
        self, project_id: str, *, approval_id: str, shot_id: str, storyboard_revision: int,
        expected_selection_revision: int, idempotency_key: str, requested_seconds: int = 5,
        resolution: str = "720p", audio: bool = True,
        playback_intent: str = "source_exact",
        production_contract: VideoProductionContract | None = None,
        backend_binding: VideoBackendBinding | None = None,
        reviewed_directions: dict[str, Any] | None = None,
        preview_only: bool = False,
    ) -> dict[str, Any]:
        """Freeze current audiovisual lineage and atomically reserve the shared cap."""
        if production_contract is None:
            if requested_seconds != 5 or resolution != "720p" or audio is not True:
                raise InvalidTransitionError("P2 only admits Wan 5-second 720p native-audio requests")
            compiler_version = "p2-wan-v1"
            provider_snapshot = {
                "provider": "atlascloud", "model": "alibaba/wan-3.0/image-to-video",
                "capabilityVersion": 1, "imageField": "image",
            }
            request_snapshot = {
                "durationSeconds": requested_seconds, "resolution": resolution, "audio": audio,
            }
            tracks_paid_wan_pilot = True
        else:
            requested_seconds = production_contract.requested_seconds
            resolution = production_contract.resolution
            audio = production_contract.audio
            compiler_version = (
                "plotloom.h3-reviewed-frame.v5-presentation" if production_contract.profile_id is not None
                else "p2-video-adapters-v1"
            )
            provider_snapshot = production_contract.provider_snapshot()
            request_snapshot = production_contract.request_snapshot()
            tracks_paid_wan_pilot = production_contract.tracks_paid_wan_pilot
            if backend_binding is not None:
                if (
                    backend_binding.adapter_id != production_contract.adapter_id
                    or backend_binding.adapter_version != production_contract.adapter_version
                ):
                    raise InvalidTransitionError(
                        "video backend binding does not match the adapter production contract"
                    )
                provider_snapshot["backendBinding"] = backend_binding.snapshot()
        with self._access.leases.lifecycle_write() as session:
            now = utc_now()
            self._access.guards.active(self._access.rows.project(session, project_id))
            approval = self._admission.approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("video job approval does not match current storyboard")
            state = self._admission.selection_state_in_session(session, project_id, now)
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            story_bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            scene_beats = self._canonical._load_stage_payload(session, project_id, StageName.SCENE_BEATS)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None:
                raise InvalidTransitionError("video job must target one current storyboard shot")
            source_timing = self._source_timing.binding_in_session(
                session, project_id, shot_id, shot.duration_units
            )
            authored_units = source_timing["durationUnits"]
            if production_contract is not None and production_contract.adapter_id == "minimax_h3_gateway":
                frame_count = production_contract.frame_count
                if authored_units <= 0 or authored_units * 24 % 1_000:
                    raise InvalidTransitionError("authored shot duration is not representable at 24 fps")
                if frame_count is None or frame_count * 1_000 < authored_units * 24:
                    raise InvalidTransitionError("H3 request cannot cover authored shot frames")
                expected_intent = ("source_exact" if frame_count * 1_000 == authored_units * 24
                                   else "segment_required")
                if playback_intent != expected_intent:
                    raise InvalidTransitionError("H3 request needs explicit authored-to-request playback intent")
            elif playback_intent != "source_exact" or (
                authored_units in {6_000, 8_000} or source_timing["kind"] == "f5_bridge"
            ) and requested_seconds * 1_000 != authored_units:
                raise InvalidTransitionError("non-H3 video needs exact authored request timing")
            binding = session.scalar(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == project_id, ReviewedShotBindingRow.shot_id == shot_id).order_by(ReviewedShotBindingRow.selection_revision.desc()).limit(1))
            if binding is None or not self._admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
                raise InvalidTransitionError("video job needs the current reviewed selected keyframe")
            asset = session.get(ManagedAssetRow, binding.asset_id)
            if asset is None or asset.project_id != project_id:
                raise InvalidTransitionError("selected keyframe bytes are unavailable")
            # New catalog-backed H3 contracts use an exact profile geometry.
            # A mismatched source is normally rejected before a row,
            # reservation, or provider call. The narrow exceptions are
            # explicit frozen input-frame modes: letterbox asks the gateway to
            # retain black canvas, while centered crop asks that same gateway
            # to crop the frozen original. Neither waives profile, provenance,
            # or output checks and neither creates a local derivative.
            if (
                production_contract is not None
                and production_contract.profile_id is not None
                and production_contract.width is not None
                and production_contract.height is not None
            ):
                expected_policy = (
                    "cover_center_crop"
                    if production_contract.allow_center_crop
                    else "contain_pad"
                    if production_contract.allow_letterbox
                    else "reject_mismatch"
                )
                if production_contract.aspect_policy != expected_policy:
                    raise InvalidTransitionError(
                        "new H3 video job aspect policy does not match its frozen input-frame mode"
                    )
                if (
                    not production_contract.allow_letterbox
                    and not production_contract.allow_center_crop
                    and not has_matching_aspect(
                        asset.width,
                        asset.height,
                        production_contract.width,
                        production_contract.height,
                    )
                ):
                    raise KeyframeAspectMismatchError(
                        asset.width,
                        asset.height,
                        production_contract.width,
                        production_contract.height,
                    )
            intent = session.get(VisualIntentRow, binding.visual_intent_id)
            if intent is None:
                raise InvalidTransitionError("selected keyframe visual intent is unavailable")
            context = self._image_currentness.image_job_resolved_context(shot=shot, storyboard=storyboard, story_bible=story_bible, scene_beats=scene_beats)
            shot, context, presentation = self._image_currentness.presentations.project(session, project_id, shot, context)
            generated_identity = self._same_person.identity_mapping_for_binding_in_session(session, binding)
            identity_lineage = generated_identity
            if identity_lineage is None:
                characters = {character.id: character for character in story_bible.characters}
                identity_lineage = []
                for character_id in shot.character_ids:
                    character = characters.get(character_id)
                    decision = self._references.current_character_reference_in_session(session, project_id, character) if character else None
                    if decision is None:
                        raise InvalidTransitionError(
                            "video job needs a current explicit character reference for each visible character"
                        )
                    identity_lineage.append({
                        "characterId": character_id,
                        "referenceDecisionId": decision.id,
                        "referenceRevision": decision.reference_revision,
                        "characterContextHash": decision.character_context_hash,
                        "assets": list(decision.asset_hashes),
                    })
            same_person_review = self._same_person.current_same_person_review_for_binding(session, project_id, binding)
            if generated_identity and same_person_review is None:
                raise InvalidTransitionError("identity-aware keyframe requires a current explicit same-person review before video admission")
            snapshot = {
                "snapshotVersion": (
                    1 if production_contract is None
                    else 4 if production_contract.profile_id is not None
                    else 2
                ),
                "compilerVersion": compiler_version, "approvalId": approval.id,
                "approvalGateSetVersion": approval.gate_set_version, "storyboardEntityRevisionId": approval.entity_revision_id,
                "storyboardRevision": storyboard_revision, "canonicalInputRevisions": dict(approval.canonical_input_revisions),
                "shot": shot.model_dump(mode="json", by_alias=True), "resolvedContext": context,
                "keyframe": {"bindingId": binding.id, "selectionRevision": binding.selection_revision,
                    "assetId": asset.id, "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "width": asset.width, "height": asset.height, "visualIntentId": intent.id,
                    "visualIntentRevision": intent.revision, "intent": intent.intent},
                "identityLineage": identity_lineage,
                "samePersonReviewId": same_person_review.id if same_person_review is not None else None,
                "sourceTiming": source_timing, "playbackIntent": playback_intent,
                "endFrame": self._end_frames.current(session, project_id, shot_id, approval_id,
                                                      storyboard_revision, source_timing)
                    if production_contract is not None and production_contract.adapter_id == "minimax_h3_gateway" else None,
                "provider": provider_snapshot,
                "request": request_snapshot,
            }
            end_frame = snapshot["endFrame"]
            if presentation is not None:
                snapshot["shotPresentation"] = presentation
                if production_contract is not None and production_contract.profile_id is not None:
                    snapshot["compilerVersion"] = "plotloom.h3-reviewed-frame.v6-shot-presentation"
            if isinstance(end_frame, dict) and end_frame.get("assetId") is not None:
                if production_contract is None or production_contract.width is None or production_contract.height is None:
                    raise InvalidTransitionError("ending frame requires an H3 profile")
                if end_frame["aspectPolicy"] != production_contract.aspect_policy:
                    raise InvalidTransitionError("H3 start and ending frames need one reviewed gateway aspect treatment")
                if (end_frame["aspectPolicy"] == "reject_mismatch" and not has_matching_aspect(
                    end_frame["width"], end_frame["height"],
                    production_contract.width, production_contract.height,
                )):
                    raise KeyframeAspectMismatchError(
                        end_frame["width"], end_frame["height"],
                        production_contract.width, production_contract.height,
                    )
            if production_contract is not None and production_contract.profile_id is not None:
                from ...video_backends.minimax_h3.directions import direction_sources
                from ...video_backends.minimax_h3.prompt import compile_i2va_prompt

                sources = direction_sources(snapshot)
                if preview_only and reviewed_directions is None:
                    return sources | {"compiledPrompt": None}
                try:
                    snapshot["compiledPrompt"] = compile_i2va_prompt(snapshot, reviewed_directions)
                except ValueError as exc:
                    raise InvalidTransitionError(str(exc)) from exc
                snapshot["reviewedDirections"] = reviewed_directions
                if preview_only:
                    return sources | {
                        "compiledPrompt": snapshot["compiledPrompt"],
                        "compiledPromptSha256": sha256(snapshot["compiledPrompt"].encode("utf-8")).hexdigest(),
                    }
                if reviewed_directions is None or reviewed_directions.get("promptSha256") != sha256(snapshot["compiledPrompt"].encode("utf-8")).hexdigest():
                    raise InvalidTransitionError("H3 final prompt changed or was not previewed; review it before preparation")
            elif preview_only or reviewed_directions is not None:
                raise InvalidTransitionError("reviewed prompt directions require a current H3 profile")
            fingerprint = stable_hash({"snapshot": snapshot, "idempotencyKey": idempotency_key})
            existing = session.scalar(select(VideoJobRow).where(VideoJobRow.project_id == project_id, VideoJobRow.idempotency_key == idempotency_key))
            if existing is not None:
                if existing.request_hash != fingerprint:
                    raise IdempotencyConflictError("video-job idempotency key was reused with different frozen input")
                return self._currentness.video_job_dict(existing, current=self._currentness.video_job_current_in_session(session, existing)) | {"idempotent": True}
            job = VideoJobRow(id=self._currentness.video_job_id(), project_id=project_id, idempotency_key=idempotency_key,
                request_hash=fingerprint, snapshot=snapshot, snapshot_hash=stable_hash(snapshot), requested_seconds=requested_seconds,
                state="prepared", provider_prediction_id=None, output_uri=None, output_hash=None, observed=None, error=None,
                created_at=now, updated_at=now, dispatched_at=None, cancel_requested_at=None)
            session.add(job)
            if tracks_paid_wan_pilot:
                if self._accounting is None:
                    raise InvalidTransitionError(
                        "direct project video cannot use the retained Wan pilot policy"
                    )
                self._accounting.reserve(
                    session, video_job_id=job.id, seconds=requested_seconds, now=now
                )
            session.flush()
            return self._currentness.video_job_dict(job, current=True) | {"idempotent": False}
