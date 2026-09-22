"""Video-job lifecycle and paid-pilot accounting workflow persistence."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, new_id, utc_now
from ...exceptions import (
    IdempotencyConflictError,
    InvalidTransitionError,
    KeyframeAspectMismatchError,
    NotFoundError,
    RevisionConflictError,
)
from ...keyframe_preparation import has_matching_aspect
from ...video_provider import VideoBackendBinding, VideoProductionContract
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ManagedAssetRow,
    ReviewedShotBindingRow,
    RunArtifactBlobRow,
    VideoCandidateSelectionRow,
    VideoJobRow,
    VideoReviewRow,
    VisualIntentRow,
)
from ..schema.project_production_bridge import ProductionBridgeAdmissionRow, ProductionBridgeRevisionRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_image_currentness import ImageJobCurrentness
from .media_same_person_reviews import SamePersonReviewPersistence
from .media_video_currentness import VideoJobCurrentness


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
class VideoJobPersistence:
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
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._admission = admission
        self._references = references
        self._image_currentness = image_currentness
        self._same_person = same_person
        self._currentness = currentness
        self._accounting = accounting
    def video_budget(self) -> dict[str, Any]:
        if self._accounting is None:
            raise InvalidTransitionError(
                "direct project video has no retained Wan pilot accounting"
            )
        return self._accounting.budget()

    def _bridge_cut_seconds_in_session(self, session: Session, project_id: str, shot_id: str) -> int | None:
        """Return a current bridge-owned cut duration or reject stale lineage.

        The admission is not a permissive historical exception: once a source
        cut has been installed, stale provenance blocks a new video row rather
        than allowing a caller to fall back to an arbitrary duration.
        """
        admissions = list(session.scalars(select(ProductionBridgeAdmissionRow).where(
            ProductionBridgeAdmissionRow.project_id == project_id
        ).order_by(ProductionBridgeAdmissionRow.accepted_at.desc())))
        for admission in admissions:
            revision = session.scalar(select(ProductionBridgeRevisionRow).where(
                ProductionBridgeRevisionRow.project_id == project_id,
                ProductionBridgeRevisionRow.revision == admission.proposal_revision,
            ))
            if revision is None:
                continue
            cut = next((item for item in revision.proposal.get("cuts", []) if item.get("shotId") == shot_id), None)
            if not isinstance(cut, dict):
                continue
            current = all(
                self._access.rows.stage(session, project_id, StageName(stage)).revision == expected
                for stage, expected in admission.installed_stage_revisions.items()
            )
            if not current:
                raise InvalidTransitionError("bridge source-cut provenance is stale; reprepare and explicitly reinstall before video admission")
            seconds = cut.get("seconds")
            if not isinstance(seconds, int):
                raise InvalidTransitionError("bridge source-cut duration is unavailable")
            return seconds
        return None

    def prepare_video_job(
        self, project_id: str, *, approval_id: str, shot_id: str, storyboard_revision: int,
        expected_selection_revision: int, idempotency_key: str, requested_seconds: int = 5,
        resolution: str = "720p", audio: bool = True,
        production_contract: VideoProductionContract | None = None,
        backend_binding: VideoBackendBinding | None = None,
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
                "p2-video-adapters-v2" if production_contract.profile_id is not None
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
            bridge_seconds = self._bridge_cut_seconds_in_session(session, project_id, shot_id)
            if bridge_seconds is not None and requested_seconds != bridge_seconds:
                raise InvalidTransitionError("bridge-owned F5 cut requires its exact source duration before any video job is persisted")
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
                "provider": provider_snapshot,
                "request": request_snapshot,
            }
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
            return [self._video_job_projection(session, row, selections) | {"reviews": reviews_by_job.get(row.id, [])} for row in rows]

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
            return {"id": review.id, "videoJobId": job.id, "reviewer": reviewer, "decision": decision, "note": note, "createdAt": _stored_utc(review.created_at).isoformat(), "selectionRevision": selection.revision if selection is not None else actual_revision}

    def discard_video_candidates(
        self, project_id: str, *, shot_id: str, video_job_ids: list[str], expected_selection_revision: int,
    ) -> list[dict[str, str | None]]:
        """Mark exactly named, unselected ingested candidates for recoverable cleanup."""
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
                if row.state not in {"ingested", "discard_pending"}:
                    raise InvalidTransitionError("only an ingested candidate with a known local output can be discarded")
            for row in rows:
                if row.state == "ingested":
                    row.state, row.updated_at = "discard_pending", utc_now()
            return [{"id": row.id, "uri": row.output_uri} for row in rows]

    def finalize_video_candidate_disposal(self, project_id: str, video_job_ids: list[str]) -> None:
        with self._access.leases.lifecycle_write() as session:
            rows = list(session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(video_job_ids))).all())
            if len(rows) != len(video_job_ids) or any(row.project_id != project_id or row.state != "discard_pending" for row in rows):
                raise InvalidTransitionError("video candidate disposal is no longer pending")
            for row in rows:
                row.state, row.output_uri, row.output_hash, row.updated_at = "discarded", None, None, utc_now()

    def video_output_has_retained_reference(self, project_id: str, uri: str) -> bool:
        with self._access.leases.read() as session:
            if session.scalar(select(VideoJobRow.id).where(
                VideoJobRow.project_id == project_id,
                VideoJobRow.output_uri == uri,
                VideoJobRow.state.not_in(("discard_pending", "discarded")),
            ).limit(1)) is not None:
                return True
            if session.scalar(select(ManagedAssetRow.id).where(
                ManagedAssetRow.project_id == project_id,
                (ManagedAssetRow.original_uri == uri) | (ManagedAssetRow.display_uri == uri),
            ).limit(1)) is not None:
                return True
            # One project database owns all of its run-artifact inventories,
            # so a matching path in this table is necessarily project-local.
            return session.scalar(select(RunArtifactBlobRow.run_id).where(
                RunArtifactBlobRow.relative_path == uri
            ).limit(1)) is not None

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
