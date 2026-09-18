"""Image-job preparation and frozen production-unit persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...domain import StageName, utc_now, new_id
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...image_job_contracts import ImageJobError
from ...keyframe_preparation import has_matching_aspect
from ..codec import stable_hash
from ..schema import (
    ImageJobCandidateRow,
    ImageJobRow,
    ManagedAssetRow,
    ProductionUnitRow,
    ReviewedShotBindingRow,
    VisualIntentRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .drafts import ProjectDraftPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_image_currentness import ImageJobCurrentness


class ImageJobPreparationPersistence:
    """Own validated image-job preparation and immutable production snapshots."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        drafts: ProjectDraftPersistence,
        admission: KeyframeAdmission,
        references: CharacterReferencePersistence,
        currentness: ImageJobCurrentness,
    ) -> None:
        self._access = access
        self._canonical = canonical
        self._drafts = drafts
        self._admission = admission
        self._references = references
        self._currentness = currentness

    def prepare_image_job(
        self,
        project_id: str,
        *,
        approval_id: str,
        shot_id: str,
        storyboard_revision: int,
        parent_candidate_asset_id: str | None = None,
        keyframe_adaptation: dict[str, Any] | None = None,
        presentation_change: str,
        contract_version: int = 2,
        consumed_draft: tuple[str, int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Freeze an approved single-shot production unit and manual request."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            approval = self._admission.approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("image job approval does not match the requested storyboard revision")
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            story_bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            scene_beats = self._canonical._load_stage_payload(session, project_id, StageName.SCENE_BEATS)
            head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if head.revision != storyboard_revision or head.entity_revision_id != approval.entity_revision_id:
                raise RevisionConflictError("storyboard", storyboard_revision, head.revision)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None:
                raise InvalidTransitionError("image job must target one current storyboard shot")

            if consumed_draft is not None:
                entity_id, draft_revision, draft_payload = consumed_draft
                self._drafts._consume_exact_authoring_draft_in_session(
                    session,
                    project,
                    editor_scope="image_direction",
                    entity_id=entity_id,
                    expected_draft_revision=draft_revision,
                    canonical_base_revision=head.revision,
                    canonical_payload=draft_payload,
                )

            if contract_version not in {2, 3}:
                raise InvalidTransitionError("image job contract version is unsupported")
            if keyframe_adaptation is not None and (
                parent_candidate_asset_id is not None or contract_version != 3
            ):
                raise InvalidTransitionError(
                    "keyframe adaptation requires the identity-aware original-image path"
                )

            references: list[dict[str, Any]] = []
            identity_mappings: list[dict[str, Any]] = []
            if contract_version == 3:
                characters_by_id = {item.id: item for item in story_bible.characters}
                for character_id in shot.character_ids:
                    character = characters_by_id.get(character_id)
                    if character is None:
                        raise InvalidTransitionError("shot character membership is not resolvable in the current story bible")
                    decision = self._references.current_character_reference_in_session(session, project_id, character)
                    if decision is None:
                        raise ImageJobError(
                            "identity_reference_missing",
                            f"shot character {character_id} needs an explicitly current character reference before an identity-aware job can be prepared",
                        )
                    asset_ids = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
                    assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
                    if any(asset is None or asset.project_id != project_id for asset in assets):
                        raise ImageJobError("identity_reference_missing", "character reference asset is unavailable")
                    identity_assets: list[dict[str, Any]] = []
                    for ordinal, asset in enumerate(assets):
                        assert asset is not None
                        entry = {
                            "assetId": asset.id, "role": "character_identity", "characterId": character_id,
                            "referenceDecisionId": decision.id, "referenceRevision": decision.reference_revision,
                            "view": "primary" if ordinal == 0 else "complementary",
                            "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                            "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                        }
                        references.append(entry)
                        identity_assets.append({
                            "assetId": asset.id, "originalHash": asset.original_hash,
                            "view": entry["view"],
                        })
                    identity_mappings.append({
                        "characterId": character_id, "referenceDecisionId": decision.id,
                        "referenceRevision": decision.reference_revision,
                        "characterContextHash": decision.character_context_hash,
                        "acceptedCast": decision.character_context.get("acceptedCast"),
                        "assets": identity_assets,
                    })

            parent_job_id: str | None = None
            reviewed_visual_intent: dict[str, Any] | None = None
            if parent_candidate_asset_id is not None:
                candidate = session.scalar(
                    select(ImageJobCandidateRow)
                    .where(ImageJobCandidateRow.asset_id == parent_candidate_asset_id)
                    .order_by(ImageJobCandidateRow.created_at.desc()).limit(1)
                )
                parent_job = session.get(ImageJobRow, candidate.job_id) if candidate else None
                asset = session.get(ManagedAssetRow, parent_candidate_asset_id)
                if (
                    candidate is None or parent_job is None or asset is None or asset.project_id != project_id
                    or not self._currentness.image_job_is_current_in_session(session, parent_job)
                ):
                    raise InvalidTransitionError("refinement must name a current Plotloom image-job candidate")
                binding = session.scalar(
                    select(ReviewedShotBindingRow)
                    .where(
                        ReviewedShotBindingRow.project_id == project_id,
                        ReviewedShotBindingRow.shot_id == shot_id,
                    )
                    .order_by(ReviewedShotBindingRow.selection_revision.desc())
                    .limit(1)
                )
                if (
                    binding is None
                    or binding.asset_id != parent_candidate_asset_id
                    or not self._admission.reviewed_binding_admission_eligible_in_session(
                        session, project_id, binding, approval=approval
                    )
                ):
                    raise InvalidTransitionError(
                        "refinement must name the current creator-reviewed keyframe for this shot"
                    )
                intent = session.get(VisualIntentRow, binding.visual_intent_id)
                if intent is None:
                    raise InvalidTransitionError("refinement reviewed VisualIntent is unavailable")
                parent_job_id = parent_job.id
                reviewed_visual_intent = {
                    "bindingId": binding.id,
                    "assetId": binding.asset_id,
                    "selectionRevision": binding.selection_revision,
                    "visualIntentId": intent.id,
                    "visualIntentRevision": intent.revision,
                    "intent": intent.intent,
                }
                references.append({
                    "assetId": asset.id, "role": "parent_output", "required": True,
                    "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                })

            adaptation_snapshot: dict[str, Any] | None = None
            if keyframe_adaptation is not None:
                binding = session.scalar(
                    select(ReviewedShotBindingRow)
                    .where(
                        ReviewedShotBindingRow.project_id == project_id,
                        ReviewedShotBindingRow.shot_id == shot_id,
                    )
                    .order_by(ReviewedShotBindingRow.selection_revision.desc())
                    .limit(1)
                )
                if binding is None or not self._admission.reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding, approval=approval
                ):
                    raise InvalidTransitionError(
                        "keyframe adaptation needs the current reviewed selected keyframe"
                    )
                asset = session.get(ManagedAssetRow, binding.asset_id)
                intent = session.get(VisualIntentRow, binding.visual_intent_id)
                if (
                    asset is None
                    or asset.project_id != project_id
                    or intent is None
                    or intent.project_id != project_id
                    or intent.asset_id != asset.id
                    or intent.revision != binding.visual_intent_revision
                ):
                    raise InvalidTransitionError(
                        "keyframe adaptation source is unavailable or no longer reviewable"
                    )
                target_width = int(keyframe_adaptation["targetProfile"]["width"])
                target_height = int(keyframe_adaptation["targetProfile"]["height"])
                if has_matching_aspect(asset.width, asset.height, target_width, target_height):
                    raise InvalidTransitionError(
                        "reviewed keyframe already matches the requested adaptation profile"
                    )
                references.append({
                    "assetId": asset.id,
                    "role": "source_keyframe",
                    "required": True,
                    "originalHash": asset.original_hash,
                    "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size,
                    "width": asset.width,
                    "height": asset.height,
                })
                adaptation_snapshot = {
                    "sourceBindingId": binding.id,
                    "sourceSelectionRevision": binding.selection_revision,
                    "sourceAssetId": asset.id,
                    "sourceOriginalHash": asset.original_hash,
                    "sourceVisualIntentId": intent.id,
                    "sourceVisualIntentRevision": intent.revision,
                    "targetProfile": dict(keyframe_adaptation["targetProfile"]),
                    "outputContract": {
                        "width": target_width,
                        "height": target_height,
                        "mimeTypes": ["image/jpeg", "image/png"],
                    },
                }

            if len(references) > 9:
                raise ImageJobError(
                    "identity_reference_excessive",
                    "identity-aware job has more than nine frozen reference attachments; reduce the authored visible cast or reference views",
                )

            shot_payload = shot.model_dump(mode="json", by_alias=True)
            visual_proposal = {
                "title": shot.title, "action": shot.action, "composition": shot.composition,
                "visualIntent": shot.visual_intent, "cameraAngle": shot.camera_angle,
                "cameraMovement": shot.camera_movement,
            }
            resolved_context = self._currentness.image_job_resolved_context(
                shot=shot,
                storyboard=storyboard,
                story_bible=story_bible,
                scene_beats=scene_beats,
            )
            snapshot = {
                "snapshotVersion": contract_version, "compilerVersion": f"plotloom.codex-image-job.v{contract_version}",
                "projectId": project_id, "approvalId": approval.id,
                "approvalGateSetVersion": approval.gate_set_version,
                "storyboardEntityRevisionId": approval.entity_revision_id,
                "storyboardRevision": storyboard_revision,
                "canonicalInputRevisions": dict(approval.canonical_input_revisions),
                "shot": shot_payload, "visualProposal": visual_proposal,
                "creatorDirection": {"presentationChange": presentation_change},
                "resolvedContext": resolved_context,
                "references": references,
                "audioContext": shot_payload.get("audioPlan", {}),
            }
            if contract_version == 3:
                snapshot["visibleCharacterIds"] = list(shot.character_ids)
                snapshot["characterIdentity"] = identity_mappings
            if reviewed_visual_intent is not None:
                snapshot["reviewedVisualIntent"] = reviewed_visual_intent
            if adaptation_snapshot is not None:
                snapshot["keyframeAdaptation"] = adaptation_snapshot
            snapshot_hash = stable_hash(snapshot)
            now = utc_now()
            unit = ProductionUnitRow(
                id=new_id(), project_id=project_id, approval_id=approval.id,
                storyboard_entity_revision_id=approval.entity_revision_id, shot_id=shot.id,
                scene_id=shot.scene_id, storyboard_revision=storyboard_revision,
                snapshot=snapshot, snapshot_hash=snapshot_hash, created_at=now,
            )
            session.add(unit)
            session.flush()
            job_id = self._currentness.image_job_id()
            request = {
                "schemaVersion": contract_version, "jobId": job_id, "productionUnitId": unit.id,
                "productionSnapshotHash": snapshot_hash,
                "executionContract": "codex_specialist.v2" if contract_version == 3 else "codex_specialist.v1",
                "kind": (
                    "keyframe_adaptation"
                    if adaptation_snapshot is not None
                    else "refinement" if parent_candidate_asset_id else "original"
                ),
                "visualProposal": visual_proposal, "frozenSnapshot": snapshot,
            }
            if contract_version == 3:
                request["specialistPreflight"] = {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3", "executionContract": "codex_specialist.v2"}
            job = ImageJobRow(
                id=job_id, project_id=project_id, production_unit_id=unit.id,
                parent_job_id=parent_job_id, parent_candidate_asset_id=parent_candidate_asset_id,
                request=request, request_hash=stable_hash(request), state="prepared", exported_at=None,
                cancelled_at=None, cancellation_reason=None, created_at=now,
            )
            session.add(job)
            session.flush()
            return {"job": self._currentness.image_job_dict(job, current=True), "productionUnit": self._currentness.production_unit_dict(unit)}
