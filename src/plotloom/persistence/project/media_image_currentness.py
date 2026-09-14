"""Image-job currentness, frozen context, and durable projections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from ...domain import ProjectLifecycleStatus, StageName
from ...exceptions import InvalidTransitionError, NotFoundError, SchemaResetRequiredError
from ..codec import _stored_utc
from ..schema import ImageJobRow, ProductionUnitRow, ProjectRow, ReviewedShotBindingRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_identifiers import new_image_job_id


class ImageJobCurrentness:
    """Own image-job applicability checks and frozen authoring-context projection."""

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
    def image_job_id() -> str:
        return new_image_job_id()

    @staticmethod
    def image_job_dict(row: ImageJobRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "productionUnitId": row.production_unit_id,
            "parentJobId": row.parent_job_id, "parentCandidateAssetId": row.parent_candidate_asset_id,
            "request": row.request, "requestHash": row.request_hash, "state": row.state,
            "current": current,
            "exportedAt": _stored_utc(row.exported_at).isoformat() if row.exported_at else None,
            "cancelledAt": _stored_utc(row.cancelled_at).isoformat() if row.cancelled_at else None,
            "cancellationReason": row.cancellation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    @staticmethod
    def production_unit_dict(row: ProductionUnitRow) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "approvalId": row.approval_id,
            "shotId": row.shot_id, "sceneId": row.scene_id,
            "storyboardRevision": row.storyboard_revision, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def image_job_is_current_in_session(self, session: Session, job: ImageJobRow) -> bool:
        if job.state == "cancelled":
            return False
        project = session.get(ProjectRow, job.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        unit = session.get(ProductionUnitRow, job.production_unit_id)
        if unit is None or unit.project_id != job.project_id:
            return False
        try:
            approval = self._admission.approval_is_active_in_session(session, unit.approval_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not (
            approval.project_id == job.project_id
            and approval.entity_revision_id == unit.storyboard_entity_revision_id
            and approval.subject_revision == unit.storyboard_revision
        ):
            return False

        # V1 original jobs predate the reviewed-keyframe refinement binding and
        # intentionally retain their historical currentness rule.  V2
        # refinements freeze an exact creator-reviewed VisualIntent, so a new
        # intent revision after Copy makes the resulting delivery inapplicable
        # rather than silently applying it to a changed presentation contract.
        reviewed_intent = unit.snapshot.get("reviewedVisualIntent")
        if reviewed_intent is not None:
            if not isinstance(reviewed_intent, dict):
                return False
            binding_id = reviewed_intent.get("bindingId")
            if not isinstance(binding_id, str):
                return False
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if binding is None:
                return False
            if (
                binding.project_id != job.project_id
                or binding.shot_id != unit.shot_id
                or binding.asset_id != reviewed_intent.get("assetId")
                or binding.selection_revision != reviewed_intent.get("selectionRevision")
                or binding.visual_intent_id != reviewed_intent.get("visualIntentId")
                or binding.visual_intent_revision != reviewed_intent.get("visualIntentRevision")
            ):
                return False
            if not self._admission.reviewed_binding_admission_eligible_in_session(
                session, job.project_id, binding, approval=approval
            ):
                return False

        # V3 freezes one explicit reference decision per visible character.
        # This runs after refinement validation so a parent image cannot
        # override or mask an invalid identity dependency.
        if unit.snapshot.get("snapshotVersion") != 3:
            return True
        identity = unit.snapshot.get("characterIdentity")
        frozen_shot = unit.snapshot.get("shot")
        if not isinstance(identity, list) or not isinstance(frozen_shot, dict):
            return False
        visible = frozen_shot.get("characterIds")
        if (
            not isinstance(visible, list)
            or any(not isinstance(item, dict) for item in identity)
            or [item.get("characterId") for item in identity] != visible
        ):
            return False
        try:
            bible = self._canonical._load_stage_payload(session, job.project_id, StageName.STORY_BIBLE)
        except (NotFoundError, SchemaResetRequiredError):
            return False
        characters = {item.id: item for item in bible.characters}
        for mapping in identity:
            if not isinstance(mapping, dict):
                return False
            character = characters.get(mapping.get("characterId"))
            if character is None:
                return False
            decision = self._references.current_character_reference_in_session(session, job.project_id, character)
            if (
                decision is None
                or decision.id != mapping.get("referenceDecisionId")
                or decision.reference_revision != mapping.get("referenceRevision")
                or decision.character_context_hash != mapping.get("characterContextHash")
            ):
                return False
            expected_assets = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
            frozen_assets = mapping.get("assets")
            if not isinstance(frozen_assets, list) or [item.get("assetId") for item in frozen_assets if isinstance(item, dict)] != expected_assets:
                return False
            hashes = {item["assetId"]: item["originalHash"] for item in decision.asset_hashes}
            if any(not isinstance(item, dict) or hashes.get(item.get("assetId")) != item.get("originalHash") for item in frozen_assets):
                return False
        return True

    @staticmethod
    def image_job_resolved_context(
        *,
        shot: Any,
        storyboard: Any,
        story_bible: Any,
        scene_beats: Any,
    ) -> dict[str, Any]:
        """Resolve just the authored facts a specialist needs for one Shot.

        The frozen projection deliberately travels only through canonical
        objects already admitted by the approved storyboard.  It does not
        expose project-wide notes, provider configuration, or any filesystem
        location.  Models from the retained V1 schema do not carry V2 dialogue
        and state links, so their corresponding narrow lists are empty.
        """

        def dump(value: Any) -> dict[str, Any]:
            return value.model_dump(mode="json", by_alias=True)

        def ordered_unique(values: Sequence[str | None]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []
            for value in values:
                if value is not None and value not in seen:
                    seen.add(value)
                    result.append(value)
            return result

        scene = next((item for item in scene_beats.scenes if item.id == shot.scene_id), None)
        linked_beat_ids = ordered_unique([
            link.beat_id for link in storyboard.shot_beat_links if link.shot_id == shot.id
        ])
        beats_by_id = {item.id: item for item in scene_beats.beats}
        beats = [beats_by_id[beat_id] for beat_id in linked_beat_ids if beat_id in beats_by_id]
        cue_ids = ordered_unique(list(getattr(shot, "cue_ids", [])))
        cues_by_id = {
            item.id: item for item in getattr(scene_beats, "dialogue_cues", [])
        }
        cues = [cues_by_id[cue_id] for cue_id in cue_ids if cue_id in cues_by_id]

        required_entity_states = list(getattr(shot, "required_entity_states", []))
        # `Shot.character_ids` is the authoritative on-screen cast. Scene
        # members, dialogue speakers, and state references remain useful
        # narrative context but cannot silently become visible people in an
        # image request or identity-reference mapping.
        character_ids = ordered_unique(list(getattr(shot, "character_ids", [])))
        prop_ids = ordered_unique([
            *list(getattr(shot, "prop_ids", [])),
            *(state.entity_id for state in required_entity_states if state.entity_type == "prop"),
        ])
        location_ids = ordered_unique([
            getattr(shot, "location_id", None),
            None if scene is None else getattr(scene, "location_id", None),
            *(state.entity_id for state in required_entity_states if state.entity_type == "location"),
        ])
        characters_by_id = {item.id: item for item in story_bible.characters}
        props_by_id = {item.id: item for item in story_bible.props}
        locations_by_id = {item.id: item for item in story_bible.locations}

        return {
            "scene": dump(scene) if scene is not None else None,
            "beats": [dump(item) for item in beats],
            "dialogueCues": [dump(item) for item in cues],
            "characters": [dump(characters_by_id[item_id]) for item_id in character_ids if item_id in characters_by_id],
            "locations": [dump(locations_by_id[item_id]) for item_id in location_ids if item_id in locations_by_id],
            "props": [dump(props_by_id[item_id]) for item_id in prop_ids if item_id in props_by_id],
            "requiredEntityStates": [dump(item) for item in required_entity_states],
        }
