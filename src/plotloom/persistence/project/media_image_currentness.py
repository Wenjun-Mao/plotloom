"""Image-job currentness, frozen context, and durable projections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from plotloom.project_contracts import ProjectLifecycleStatus
from plotloom.stage_contracts import StageName
from ...exceptions import InvalidTransitionError, NotFoundError, SchemaResetRequiredError
from ..codec import _stored_utc
from ..schema import ImageJobRow, ProductionUnitRow, ProjectRow, ReviewedShotBindingRow, ManagedAssetRow
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_identifiers import new_image_job_id
from .media_shot_presentations import ShotPresentations


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
        self.presentations = ShotPresentations(access, canonical, admission)

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
        result = {
            "id": row.id, "projectId": row.project_id, "approvalId": row.approval_id,
            "shotId": row.shot_id, "sceneId": row.scene_id,
            "storyboardRevision": row.storyboard_revision, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "createdAt": _stored_utc(row.created_at).isoformat(),
        }
        if row.machine_decision_id is not None:
            result.pop("approvalId")
            result["authority"] = {"actor": "machine", "scope": "image_generation", "decisionId": row.machine_decision_id}
        return result

    def image_job_is_current_in_session(self, session: Session, job: ImageJobRow) -> bool:
        return self._image_dependencies_current(session, job, ancestors=frozenset(), historical_source=False)

    def image_source_is_current_in_session(self, session: Session, job: ImageJobRow) -> bool:
        """Frozen independently reviewed use does not depend on later source selection."""
        return self._image_dependencies_current(session, job, ancestors=frozenset(), historical_source=True)

    def _image_dependencies_current(self, session, job, *, ancestors, historical_source):
        if job.id in ancestors:
            return False
        ancestors = ancestors | {job.id}
        if job.state == "cancelled":
            return False
        project = session.get(ProjectRow, job.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        unit = session.get(ProductionUnitRow, job.production_unit_id)
        if unit is None or unit.project_id != job.project_id:
            return False
        try:
            from .image_authority import resolve_image_authority
            approval = resolve_image_authority(session, self._access, self._admission, job.project_id,
                approval_id=unit.approval_id, machine_decision_id=unit.machine_decision_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not (
            approval.project_id == job.project_id
            and approval.entity_revision_id == unit.storyboard_entity_revision_id
            and approval.subject_revision == unit.storyboard_revision
        ):
            return False

        if not self.presentations.matches(session, job.project_id, unit.shot_id, unit.snapshot.get("shotPresentation")):
            return False

        continuity = unit.snapshot.get("sceneContinuity")
        if continuity is not None:
            from .image_reviewed_use import connection_for, validate_reviewed_source, require_use_current
            from ..schema import VisualIntentRow
            try:
                source = validate_reviewed_source(connection_for(session), job.project_id, continuity)
                binding = session.get(ReviewedShotBindingRow, continuity["bindingId"])
                if not self._admission.reviewed_binding_context_current_in_session(session, job.project_id, binding):
                    return False
                require_use_current(session, job.project_id, session.get(VisualIntentRow, binding.visual_intent_id).intent, self)
                if source:
                    source_job = session.get(ImageJobRow, source.job_id)
                    if source_job is None or source_job.state != "delivered" or not self._image_dependencies_current(
                        session, source_job, ancestors=ancestors, historical_source=True):
                        return False
            except (ValueError, TypeError, KeyError, InvalidTransitionError, NotFoundError):
                return False

        adaptation = unit.snapshot.get("keyframeAdaptation", {})
        if adaptation.get("sourceAuthority", {}).get("actor") == "machine_provisional":
            source = session.get(ImageJobRow, adaptation.get("sourceJobId"))
            asset = session.get(ManagedAssetRow, adaptation.get("sourceAssetId"))
            if (source is None or source.request.get("kind") != "original" or asset is None
                    or source.project_id != job.project_id or asset.project_id != job.project_id
                    or asset.original_hash != adaptation.get("sourceOriginalHash")
                    or not self._image_dependencies_current(session, source, ancestors=ancestors, historical_source=True)):
                return False
        elif adaptation.get("sourceBindingId") is not None:
            binding = session.get(ReviewedShotBindingRow, adaptation["sourceBindingId"])
            asset = session.get(ManagedAssetRow, adaptation.get("sourceAssetId"))
            if (binding is None or asset is None or binding.project_id != job.project_id
                    or binding.shot_id != unit.shot_id or binding.asset_id != asset.id
                    or binding.selection_revision != adaptation.get("sourceSelectionRevision")
                    or binding.visual_intent_id != adaptation.get("sourceVisualIntentId")
                    or binding.visual_intent_revision != adaptation.get("sourceVisualIntentRevision")
                    or asset.original_hash != adaptation.get("sourceOriginalHash")
                    or not self._admission.reviewed_binding_context_current_in_session(session, job.project_id, binding, approval=approval)):
                return False
            from .image_reviewed_use import require_use_current, use_in_session
            from ..schema import VisualIntentRow
            try:
                source = use_in_session(session, binding)
                require_use_current(session, job.project_id, session.get(VisualIntentRow, binding.visual_intent_id).intent, self)
                if source:
                    parent = session.get(ImageJobRow, source.job_id)
                    if parent is None or not self._image_dependencies_current(session, parent, ancestors=ancestors, historical_source=True):
                        return False
            except (ValueError, InvalidTransitionError, NotFoundError):
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
            if not self._admission.reviewed_binding_context_current_in_session(session, job.project_id, binding, approval=approval):
                return False
            from .image_reviewed_use import require_use_current
            from ..schema import VisualIntentRow
            try:
                require_use_current(session, job.project_id, session.get(VisualIntentRow, binding.visual_intent_id).intent, self)
            except (ValueError, InvalidTransitionError, NotFoundError):
                return False
            # Before selection the frozen parent must remain selected. Once this
            # delivered output is reviewed/selected, that new selection correctly
            # supersedes its parent without erasing the immutable source context.
            latest = session.scalar(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == job.project_id,
                ReviewedShotBindingRow.shot_id == unit.shot_id).order_by(ReviewedShotBindingRow.selection_revision.desc()).limit(1))
            from .image_reviewed_use import use_in_session
            try:
                parent_source = use_in_session(session, binding)
                selected_source = use_in_session(session, latest) if latest else None
            except InvalidTransitionError:
                return False
            parent_job = session.get(ImageJobRow, parent_source.job_id) if parent_source else None
            if parent_job is None or parent_job.id != job.parent_job_id or not self._image_dependencies_current(
                    session, parent_job, ancestors=ancestors, historical_source=True):
                return False
            if not historical_source and (latest is None or (latest.id != binding.id and (job.state != "delivered" or selected_source is None
                    or selected_source.job_id != job.id or not self._admission.reviewed_binding_context_current_in_session(session, job.project_id, latest, approval=approval)))):
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
            # Semantic objectives/purposes and raw evidence are reviewed narrative
            # context, not active image/H3 physical or runtime presentation authority.
            "scene": {key: value for key, value in dump(scene).items() if key != "objective"} if scene is not None else None,
            "beats": [{"id": item.id, "sceneId": item.scene_id, "order": item.order,
                       "visibleEvent": item.visible_event, "entryState": dump(item.entry_state),
                       "exitState": dump(item.exit_state)} for item in beats],
            "dialogueCues": [dump(item) for item in cues],
            "characters": [dump(characters_by_id[item_id]) for item_id in character_ids if item_id in characters_by_id],
            "locations": [dump(locations_by_id[item_id]) for item_id in location_ids if item_id in locations_by_id],
            "props": [dump(props_by_id[item_id]) for item_id in prop_ids if item_id in props_by_id],
            "requiredEntityStates": [dump(item) for item in required_entity_states],
        }
