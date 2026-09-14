"""Project-owned managed media, manual-production, review, and video facts.

This capability receives named leases, project guards, and canonical read helpers
at composition time.  It never reaches into the retained runtime repository.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    TERMINAL_MEDIA_TASK_STATUSES, ArtifactKind, MediaKind, MediaPromptContext,
    MediaTask, MediaTaskStatus, ProjectLifecycleStatus, StageName, StageStatus,
    contains_secret_setting, contains_secret_value, new_id, utc_now,
)
from ...exceptions import (
    IdempotencyConflictError, InvalidTransitionError, KeyframeAspectMismatchError,
    NotFoundError, ProductionPipelineNotReadyError, RevisionConflictError,
)
from ...image_job_contracts import ImageJobError
from ...keyframe_preparation import has_matching_aspect
from ...video_provider import VideoProductionContract
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ApprovalDecisionRow, CharacterReferenceDecisionRow, CharacterReferenceProposalCandidateRow,
    CharacterReferenceProposalDeliveryRow, CharacterReferenceProposalRow, CharacterReferenceStateRow,
    EntityRevisionRow, GateResultRow, ImageJobCandidateRow, ImageJobDeliveryRow, ImageJobRow, ManagedAssetProvenanceRow,
    ManagedAssetRow, MediaTaskRow, ProductionUnitRow, ProjectRow, ReviewedShotBindingRow,
    SamePersonReviewRow, SamePersonReviewStateRow, StillPreviewRow, VideoJobRow,
    VideoReviewRow, VisualIntentRow,
    VisualSelectionStateRow,
)
from .access import ProjectPersistenceAccess


class ProjectMediaPersistence:
    """Own all portable project-media facts and their explicit review lineage."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: Any, drafts: Any, accounting: Any) -> None:
        self._access = access
        self._canonical = canonical
        self._drafts = drafts
        self._accounting = accounting

    @staticmethod
    def _media_task(row: MediaTaskRow) -> MediaTask:
        return MediaTask(
            id=row.id, project_id=row.project_id, shot_id=row.shot_id,
            storyboard_revision=row.storyboard_revision, kind=MediaKind(row.kind),
            status=MediaTaskStatus(row.status), derived_prompt=row.derived_prompt,
            prompt_components=row.prompt_components, provider=row.provider,
            public_settings=row.public_settings, provider_task_id=row.provider_task_id,
            output_uri=row.output_uri, error=row.error, created_at=row.created_at,
            updated_at=row.updated_at, started_at=row.started_at, finished_at=row.finished_at,
        )

    @staticmethod
    def _managed_asset_dict(row: ManagedAssetRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "projectId": row.project_id,
            "originalHash": row.original_hash,
            "displayHash": row.display_hash,
            "mimeType": row.mime_type,
            "byteSize": row.byte_size,
            "width": row.width,
            "height": row.height,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def record_managed_import(
        self,
        project_id: str,
        *,
        original_hash: str,
        display_hash: str,
        mime_type: str,
        byte_size: int,
        width: int,
        height: int,
        declaration: dict[str, Any],
        publish: Callable[[], tuple[str, str]],
    ) -> dict[str, Any]:
        """Publish one independent project provenance record over stored bytes."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            # Publish under the same lifecycle writer lease that admits the
            # immutable metadata, so a rejected/archived project never leaves
            # a newly written unowned blob behind.
            original_uri, display_uri = publish()
            now = utc_now()
            asset = ManagedAssetRow(
                id=new_id(), project_id=project_id, original_uri=original_uri,
                original_hash=original_hash, display_uri=display_uri,
                display_hash=display_hash, mime_type=mime_type, byte_size=byte_size,
                width=width, height=height, created_at=now,
            )
            session.add(asset)
            # These rows intentionally have no ORM relationship (their
            # history stays one-way immutable), so establish the asset FK
            # before adding the independent provenance declaration.
            session.flush()
            session.add(ManagedAssetProvenanceRow(
                id=new_id(), project_id=project_id, asset_id=asset.id,
                declaration=declaration, created_at=now,
            ))
            session.flush()
            return self._managed_asset_dict(asset)

    def get_managed_asset_storage(self, project_id: str, asset_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            return {
                **self._managed_asset_dict(asset),
                "originalUri": asset.original_uri,
                "displayUri": asset.display_uri,
            }

    def reviewed_keyframe_crop_source(
        self,
        project_id: str,
        *,
        binding_id: str,
        expected_selection_revision: int,
    ) -> dict[str, Any]:
        """Read the exact current selected source for a proposed crop.

        The write method repeats these checks. This read projection only lets
        the API obtain bytes for a transform; it does not authorize publishing
        a derivative after a selection has changed.
        """

        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            state = self._selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "visual-selection", expected_selection_revision, state.revision
                )
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if (
                binding is None
                or not self._reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding
                )
            ):
                raise InvalidTransitionError(
                    "keyframe crop needs the current reviewed selected keyframe"
                )
            asset = session.get(ManagedAssetRow, binding.asset_id)
            if asset is None or asset.project_id != project_id:
                raise InvalidTransitionError("selected keyframe bytes are unavailable")
            return {
                "bindingId": binding.id,
                "selectionRevision": binding.selection_revision,
                "assetId": asset.id,
                "originalHash": asset.original_hash,
                "mimeType": asset.mime_type,
                "width": asset.width,
                "height": asset.height,
                "originalUri": asset.original_uri,
            }

    def record_reviewed_keyframe_center_crop(
        self,
        project_id: str,
        *,
        source: dict[str, Any],
        target_profile: dict[str, Any],
        expected_selection_revision: int,
        original_hash: str,
        display_hash: str,
        mime_type: str,
        byte_size: int,
        width: int,
        height: int,
        publish: Callable[[], tuple[str, str]],
    ) -> dict[str, Any]:
        """Persist a source-bound crop without selecting it for the Shot."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            state = self._selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "visual-selection", expected_selection_revision, state.revision
                )
            binding = session.get(ReviewedShotBindingRow, source["bindingId"])
            if (
                binding is None
                or binding.asset_id != source["assetId"]
                or binding.selection_revision != source["selectionRevision"]
                or not self._reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding
                )
            ):
                raise InvalidTransitionError(
                    "keyframe crop source is no longer the current reviewed keyframe"
                )
            source_asset = session.get(ManagedAssetRow, binding.asset_id)
            if (
                source_asset is None
                or source_asset.project_id != project_id
                or source_asset.original_hash != source["originalHash"]
            ):
                raise InvalidTransitionError("keyframe crop source bytes are unavailable")
            target_width, target_height = int(target_profile["width"]), int(target_profile["height"])
            if has_matching_aspect(
                source_asset.width, source_asset.height, target_width, target_height
            ):
                raise InvalidTransitionError(
                    "keyframe already matches the requested profile aspect"
                )
            if (width, height) != (target_width, target_height):
                raise InvalidTransitionError(
                    "derived keyframe crop does not match the requested profile"
                )
            original_uri, display_uri = publish()
            now = utc_now()
            asset = ManagedAssetRow(
                id=new_id(), project_id=project_id, original_uri=original_uri,
                original_hash=original_hash, display_uri=display_uri,
                display_hash=display_hash, mime_type=mime_type,
                byte_size=byte_size, width=width, height=height, created_at=now,
            )
            session.add(asset)
            session.flush()
            session.add(ManagedAssetProvenanceRow(
                id=new_id(), project_id=project_id, asset_id=asset.id,
                declaration={
                    "origin": "plotloom_keyframe_center_crop",
                    "sourceBindingId": binding.id,
                    "sourceAssetId": source_asset.id,
                    "sourceOriginalHash": source_asset.original_hash,
                    "targetProfile": dict(target_profile),
                    "transform": {
                        "version": 1,
                        "strategy": "cover_center_crop",
                        "centering": [0.5, 0.5],
                    },
                },
                created_at=now,
            ))
            session.flush()
            return self._managed_asset_dict(asset)

    def list_managed_assets(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(ManagedAssetRow)
                .where(ManagedAssetRow.project_id == project_id)
                .order_by(ManagedAssetRow.created_at, ManagedAssetRow.id)
            ).all()
            result = []
            for row in rows:
                provenance = session.scalar(
                    select(ManagedAssetProvenanceRow)
                    .where(ManagedAssetProvenanceRow.asset_id == row.id)
                    .order_by(ManagedAssetProvenanceRow.created_at)
                    .limit(1)
                )
                result.append({
                    **self._managed_asset_dict(row),
                    "provenance": provenance.declaration if provenance else None,
                })
            return result

    def create_visual_intent(
        self,
        project_id: str,
        asset_id: str,
        intent: dict[str, Any],
        *,
        consumed_draft: tuple[str, int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            if consumed_draft is not None:
                entity_id, draft_revision, draft_payload = consumed_draft
                self._drafts._consume_exact_authoring_draft_in_session(
                    session,
                    project,
                    editor_scope="visual_intent",
                    entity_id=entity_id,
                    expected_draft_revision=draft_revision,
                    canonical_base_revision=self._access.rows.stage(
                        session, project_id, StageName.STORYBOARD
                    ).revision,
                    canonical_payload=draft_payload,
                )
            previous = session.scalar(
                select(VisualIntentRow.revision)
                .where(VisualIntentRow.project_id == project_id, VisualIntentRow.asset_id == asset_id)
                .order_by(VisualIntentRow.revision.desc()).limit(1)
            ) or 0
            row = VisualIntentRow(
                id=new_id(), project_id=project_id, asset_id=asset_id,
                revision=previous + 1, intent=intent, created_at=utc_now(),
            )
            session.add(row)
            session.flush()
            return {"id": row.id, "assetId": asset_id, "revision": row.revision, "intent": row.intent}

    def list_visual_intents(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(VisualIntentRow)
                .where(VisualIntentRow.project_id == project_id)
                .order_by(VisualIntentRow.asset_id, VisualIntentRow.revision.desc())
            ).all()
            # A single imported still can legitimately serve more than one
            # authoring role.  Currentness is role-scoped, so do not hide the
            # latest location reference behind a later shot-keyframe revision.
            latest: dict[tuple[str, str | None], VisualIntentRow] = {}
            for row in rows:
                latest.setdefault((row.asset_id, row.intent.get("role")), row)
            return [
                {"id": row.id, "assetId": row.asset_id, "revision": row.revision, "intent": row.intent}
                for row in latest.values()
            ]

    @staticmethod
    def _latest_visual_intent_for_role_in_session(
        session: Session, project_id: str, asset_id: str, role: str | None
    ) -> VisualIntentRow | None:
        """Return the latest intent in the asset's role-specific stream."""

        return next(
            (
                candidate
                for candidate in session.scalars(
                    select(VisualIntentRow)
                    .where(
                        VisualIntentRow.project_id == project_id,
                        VisualIntentRow.asset_id == asset_id,
                    )
                    .order_by(VisualIntentRow.revision.desc())
                )
                if candidate.intent.get("role") == role
            ),
            None,
        )

    def _reviewed_binding_admission_eligible_in_session(
        self,
        session: Session,
        project_id: str,
        binding: ReviewedShotBindingRow,
        *,
        approval: ApprovalDecisionRow | None = None,
    ) -> bool:
        """Whether a binding can contribute to a new preview right now.

        Historical rows deliberately remain readable.  New projections may use
        only the latest binding for the Shot, latest intent in the bound
        asset/role stream, and the current exact storyboard approval.
        """

        if binding.project_id != project_id:
            return False
        latest_binding = session.scalar(
            select(ReviewedShotBindingRow)
            .where(
                ReviewedShotBindingRow.project_id == project_id,
                ReviewedShotBindingRow.shot_id == binding.shot_id,
            )
            .order_by(ReviewedShotBindingRow.selection_revision.desc())
            .limit(1)
        )
        if latest_binding is None or latest_binding.id != binding.id:
            return False
        intent = session.get(VisualIntentRow, binding.visual_intent_id)
        if (
            intent is None
            or intent.project_id != project_id
            or intent.asset_id != binding.asset_id
            or intent.revision != binding.visual_intent_revision
        ):
            return False
        latest_intent = self._latest_visual_intent_for_role_in_session(
            session, project_id, binding.asset_id, intent.intent.get("role")
        )
        if (
            latest_intent is None
            or latest_intent.id != intent.id
            or latest_intent.revision != intent.revision
        ):
            return False
        if approval is None:
            try:
                approval = self._approval_is_active_in_session(session, binding.approval_id)
            except (InvalidTransitionError, NotFoundError):
                return False
        return (
            approval.project_id == project_id
            and binding.approval_id == approval.id
            and binding.storyboard_entity_revision_id == approval.entity_revision_id
            and binding.storyboard_revision == approval.subject_revision
        )

    def list_current_reviewed_keyframes(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(ReviewedShotBindingRow)
                .where(ReviewedShotBindingRow.project_id == project_id)
                .order_by(ReviewedShotBindingRow.selection_revision.desc())
            ).all()
            latest: dict[str, ReviewedShotBindingRow] = {}
            for row in rows:
                latest.setdefault(row.shot_id, row)
            return [
                {
                    "id": row.id, "assetId": row.asset_id, "shotId": row.shot_id,
                    "sceneId": row.scene_id, "selectionRevision": row.selection_revision,
                    "visualIntentId": row.visual_intent_id,
                    "visualIntentRevision": row.visual_intent_revision,
                    "compatibilityNote": row.compatibility_note,
                }
                for row in latest.values()
                if self._reviewed_binding_admission_eligible_in_session(session, project_id, row)
            ]

    def _approval_is_active_in_session(self, session: Session, decision_id: str) -> ApprovalDecisionRow:
        decision = session.get(ApprovalDecisionRow, decision_id)
        if decision is None:
            raise NotFoundError(f"approval decision not found: {decision_id}")
        if decision.decision != "approve":
            raise InvalidTransitionError("reviewed selection requires an active approval")
        latest = session.scalar(
            select(ApprovalDecisionRow)
            .where(
                ApprovalDecisionRow.entity_revision_id == decision.entity_revision_id,
                ApprovalDecisionRow.subject_type == decision.subject_type,
                ApprovalDecisionRow.subject_id == decision.subject_id,
            )
            .order_by(ApprovalDecisionRow.created_at.desc(), ApprovalDecisionRow.id.desc())
            .limit(1)
        )
        if latest is None or latest.id != decision.id:
            raise InvalidTransitionError("reviewed selection approval is revoked or superseded")
        revision = session.get(EntityRevisionRow, decision.entity_revision_id)
        head = self._access.rows.stage(session, decision.project_id, StageName.STORYBOARD)
        if revision is None or (
            head.status != StageStatus.READY.value
            or head.entity_revision_id != decision.entity_revision_id
            or head.content_hash != decision.content_hash
            or revision.revision != decision.subject_revision
        ):
            raise InvalidTransitionError("reviewed selection approval is stale")
        gates = session.scalars(
            select(GateResultRow).where(
                GateResultRow.entity_revision_id == decision.entity_revision_id,
                GateResultRow.gate_set_version == decision.gate_set_version,
            )
        ).all()
        if not gates or any(not self._access.codecs.gate_result(gate).passed for gate in gates):
            raise InvalidTransitionError("reviewed selection approval gates are no longer passing")
        return decision

    @staticmethod
    def _selection_state_in_session(session: Session, project_id: str, now: datetime) -> VisualSelectionStateRow:
        state = session.get(VisualSelectionStateRow, project_id)
        if state is None:
            state = VisualSelectionStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state

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
            state = self._selection_state_in_session(session, project_id, now)
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            approval = self._approval_is_active_in_session(session, approval_id)
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
                if generated_job is None or not self._image_job_is_current_in_session(session, generated_job):
                    raise InvalidTransitionError(
                        "image-job candidate is no longer applicable and cannot be selected"
                    )
            intent = session.get(VisualIntentRow, visual_intent_id)
            if (
                intent is None or intent.project_id != project_id or intent.asset_id != asset_id
                or intent.revision != visual_intent_revision
            ):
                raise InvalidTransitionError("reviewed keyframe must bind an exact current-project visual intent")
            latest_intent = self._latest_visual_intent_for_role_in_session(
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
            state = self._selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            approval = self._approval_is_active_in_session(session, approval_id)
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
                if not self._reviewed_binding_admission_eligible_in_session(
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
                identity_mapping = self._identity_mapping_for_binding_in_session(session, binding)
                if identity_mapping:
                    review = self.current_same_person_review_for_binding(session, project_id, binding)
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
            if not self._reviewed_binding_admission_eligible_in_session(session, project_id, binding):
                return False
            review_id = frame.get("identityReviewId")
            if review_id is None:
                # Historic/P0 frames and V3 character-free shots have no
                # same-person dependency. A visible V3 cast must have had a
                # review attached during preview admission.
                return not self._identity_mapping_for_binding_in_session(session, binding)
            review = session.get(SamePersonReviewRow, review_id)
            return review is not None and self._same_person_review_is_current_in_session(session, project_id, review)

    @staticmethod
    def _video_job_id() -> str:
        return f"vj_{new_id().replace('-', '')}"

    @staticmethod
    def _video_job_dict(row: VideoJobRow, *, current: bool, selected: bool = False) -> dict[str, Any]:
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
    def _video_job_tracks_paid_wan_pilot(row: VideoJobRow) -> bool:
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

    def _video_job_current_in_session(self, session: Session, row: VideoJobRow) -> bool:
        project = session.get(ProjectRow, row.project_id)
        snapshot = row.snapshot
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        try:
            approval = self._approval_is_active_in_session(session, str(snapshot["approvalId"]))
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
                current = self._current_character_reference_in_session(session, row.project_id, character) if character else None
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
                if review is None or not self._same_person_review_is_current_in_session(session, row.project_id, review):
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
            and self._reviewed_binding_admission_eligible_in_session(session, row.project_id, binding, approval=approval)
        )

    def video_budget(self) -> dict[str, Any]:
        return self._accounting.budget()

    def prepare_video_job(
        self, project_id: str, *, approval_id: str, shot_id: str, storyboard_revision: int,
        expected_selection_revision: int, idempotency_key: str, requested_seconds: int = 5,
        resolution: str = "720p", audio: bool = True,
        production_contract: VideoProductionContract | None = None,
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
        with self._access.leases.lifecycle_write() as session:
            now = utc_now()
            self._access.guards.active(self._access.rows.project(session, project_id))
            approval = self._approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("video job approval does not match current storyboard")
            state = self._selection_state_in_session(session, project_id, now)
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            story_bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            scene_beats = self._canonical._load_stage_payload(session, project_id, StageName.SCENE_BEATS)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None:
                raise InvalidTransitionError("video job must target one current storyboard shot")
            binding = session.scalar(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == project_id, ReviewedShotBindingRow.shot_id == shot_id).order_by(ReviewedShotBindingRow.selection_revision.desc()).limit(1))
            if binding is None or not self._reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
                raise InvalidTransitionError("video job needs the current reviewed selected keyframe")
            asset = session.get(ManagedAssetRow, binding.asset_id)
            if asset is None or asset.project_id != project_id:
                raise InvalidTransitionError("selected keyframe bytes are unavailable")
            # New catalog-backed H3 contracts use an exact profile geometry.
            # A mismatched source is normally rejected before a row,
            # reservation, or provider call. The narrow exception is an
            # explicit frozen letterbox request: the creator is asking the
            # gateway to retain black canvas as part of the input, not asking
            # Plotloom to waive profile, provenance, or output checks.
            if (
                production_contract is not None
                and production_contract.profile_id is not None
                and production_contract.width is not None
                and production_contract.height is not None
            ):
                expected_policy = (
                    "contain_pad"
                    if production_contract.allow_letterbox
                    else "reject_mismatch"
                )
                if production_contract.aspect_policy != expected_policy:
                    raise InvalidTransitionError(
                        "new H3 video job aspect policy does not match its frozen input-frame mode"
                    )
                if (
                    not production_contract.allow_letterbox
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
            context = self._image_job_resolved_context(shot=shot, storyboard=storyboard, story_bible=story_bible, scene_beats=scene_beats)
            generated_identity = self._identity_mapping_for_binding_in_session(session, binding)
            identity_lineage = generated_identity
            if identity_lineage is None:
                characters = {character.id: character for character in story_bible.characters}
                identity_lineage = []
                for character_id in shot.character_ids:
                    character = characters.get(character_id)
                    decision = self._current_character_reference_in_session(session, project_id, character) if character else None
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
            same_person_review = self.current_same_person_review_for_binding(session, project_id, binding)
            if generated_identity and same_person_review is None:
                raise InvalidTransitionError("identity-aware keyframe requires a current explicit same-person review before video admission")
            snapshot = {
                "snapshotVersion": (
                    1 if production_contract is None
                    else 3 if production_contract.profile_id is not None
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
                return self._video_job_dict(existing, current=self._video_job_current_in_session(session, existing)) | {"idempotent": True}
            job = VideoJobRow(id=self._video_job_id(), project_id=project_id, idempotency_key=idempotency_key,
                request_hash=fingerprint, snapshot=snapshot, snapshot_hash=stable_hash(snapshot), requested_seconds=requested_seconds,
                state="prepared", provider_prediction_id=None, output_uri=None, output_hash=None, observed=None, error=None,
                created_at=now, updated_at=now, dispatched_at=None, cancel_requested_at=None)
            session.add(job)
            if tracks_paid_wan_pilot:
                self._accounting.reserve(
                    session, video_job_id=job.id, seconds=requested_seconds, now=now
                )
            session.flush()
            return self._video_job_dict(job, current=True) | {"idempotent": False}

    def claim_video_dispatch(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        """Cross the durable dispatch boundary before any POST; never retry it."""
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "prepared":
                raise InvalidTransitionError("video job cannot be submitted again; reconcile its existing attempt")
            if not self._video_job_current_in_session(session, job):
                raise InvalidTransitionError("video job frozen inputs are stale; prepare a new attempt")
            now = utc_now()
            job.state, job.dispatched_at, job.updated_at = "dispatching", now, now
            if self._video_job_tracks_paid_wan_pilot(job):
                self._accounting.record_dispatch(
                    session, video_job_id=job.id, seconds=job.requested_seconds, now=now
                )
            return self._video_job_dict(job, current=True)

    def record_video_submission(self, project_id: str, video_job_id: str, prediction_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "dispatching" or job.provider_prediction_id is not None:
                raise InvalidTransitionError("video submission cannot be recorded from this state")
            job.provider_prediction_id, job.state, job.updated_at = prediction_id, "submitted", utc_now()
            return self._video_job_dict(job, current=self._video_job_current_in_session(session, job))

    def record_video_outcome_unknown(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"dispatching", "submitted"}:
                raise InvalidTransitionError("only a dispatched video job can have unknown outcome")
            job.state, job.error, job.updated_at = "outcome_unknown", message[:2_000], utc_now()
            return self._video_job_dict(job, current=False)

    def record_video_output(self, project_id: str, video_job_id: str, *, uri: str, digest: str, observed: dict[str, Any]) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("video output can only be ingested from a known submitted attempt")
            job.output_uri, job.output_hash, job.observed, job.state, job.updated_at = uri, digest, observed, "ingested", utc_now()
            return self._video_job_dict(job, current=self._video_job_current_in_session(session, job))

    def record_video_retrieve_needed(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("only a known submitted video can await retrieval")
            job.state, job.error, job.updated_at = "retrieve_needed", message[:2_000], utc_now()
            return self._video_job_dict(job, current=self._video_job_current_in_session(session, job))

    def record_video_remote_failed(self, project_id: str, video_job_id: str, code: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("only a known submitted video can record remote failure")
            job.state, job.error, job.updated_at = "failed", code, utc_now()
            return self._video_job_dict(job, current=False)

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
                if self._video_job_tracks_paid_wan_pilot(job):
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
            return self._video_job_dict(job, current=False)

    def list_video_jobs(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(select(VideoJobRow).where(VideoJobRow.project_id == project_id).order_by(VideoJobRow.created_at.desc(), VideoJobRow.id.desc())).all()
            decisions = session.scalars(select(VideoReviewRow).where(VideoReviewRow.video_job_id.in_([row.id for row in rows])).order_by(VideoReviewRow.created_at.desc(), VideoReviewRow.id.desc())).all()
            latest: dict[str, VideoReviewRow] = {}
            jobs_by_id = {row.id: row for row in rows}
            latest_by_shot: dict[str, VideoReviewRow] = {}
            for decision in decisions:
                latest.setdefault(decision.video_job_id, decision)
                source = jobs_by_id.get(decision.video_job_id)
                if source is not None:
                    latest_by_shot.setdefault(str(source.snapshot.get("shot", {}).get("id")), decision)
            return [self._video_job_dict(row, current=self._video_job_current_in_session(session, row), selected=(latest_by_shot.get(str(row.snapshot.get("shot", {}).get("id"))) is not None and latest_by_shot[str(row.snapshot.get("shot", {}).get("id"))].video_job_id == row.id and latest_by_shot[str(row.snapshot.get("shot", {}).get("id"))].decision == "select" and self._video_job_current_in_session(session, row))) for row in rows]

    def get_video_output_storage(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id or job.state != "ingested" or not job.output_uri or not job.output_hash:
                raise NotFoundError("locally ingested video candidate not found")
            return {"uri": job.output_uri, "hash": job.output_hash, "mimeType": "video/mp4"}

    def review_video_job(self, project_id: str, video_job_id: str, *, reviewer: str, decision: str, note: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "ingested" or not self._video_job_current_in_session(session, job):
                raise InvalidTransitionError("only a current locally ingested video candidate can be reviewed")
            review = VideoReviewRow(id=new_id(), video_job_id=job.id, reviewer=reviewer, decision=decision, note=note, created_at=utc_now())
            session.add(review)
            return {"id": review.id, "videoJobId": job.id, "reviewer": reviewer, "decision": decision, "note": note, "createdAt": _stored_utc(review.created_at).isoformat()}

    @staticmethod
    def _character_reference_context(character: Any) -> dict[str, Any]:
        """Freeze only identity-relevant canonical facts; display-name edits do not transfer identity."""

        payload = character.model_dump(mode="json", by_alias=True)
        return {
            "characterId": payload["id"],
            "description": payload["description"],
            "visualAnchors": payload["visualAnchors"],
            "traits": payload["traits"],
            "continuityRules": payload["continuityRules"],
            "allowedStates": payload["allowedStates"],
        }

    @staticmethod
    def _character_reference_state_in_session(
        session: Session, project_id: str, character_id: str, now: datetime
    ) -> CharacterReferenceStateRow:
        state = session.get(CharacterReferenceStateRow, (project_id, character_id))
        if state is None:
            state = CharacterReferenceStateRow(
                project_id=project_id, character_id=character_id, revision=0,
                active_decision_id=None, updated_at=now,
            )
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _reference_decision_dict(row: CharacterReferenceDecisionRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "characterId": row.character_id,
            "referenceRevision": row.reference_revision, "characterContext": row.character_context,
            "characterContextHash": row.character_context_hash, "primaryAssetId": row.primary_asset_id,
            "complementaryAssetIds": list(row.complementary_asset_ids), "assetHashes": list(row.asset_hashes),
            "reviewer": row.reviewer, "notes": row.notes, "current": current,
            "revokedAt": _stored_utc(row.revoked_at).isoformat() if row.revoked_at else None,
            "revokedBy": row.revoked_by, "revocationReason": row.revocation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _current_character_reference_in_session(
        self, session: Session, project_id: str, character: Any
    ) -> CharacterReferenceDecisionRow | None:
        state = session.get(CharacterReferenceStateRow, (project_id, character.id))
        if state is None or state.active_decision_id is None:
            return None
        decision = session.get(CharacterReferenceDecisionRow, state.active_decision_id)
        if decision is None or decision.project_id != project_id or decision.character_id != character.id:
            return None
        if decision.revoked_at is not None:
            return None
        context = self._character_reference_context(character)
        if decision.character_context_hash != stable_hash(context):
            return None
        asset_ids = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
        assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
        if any(asset is None or asset.project_id != project_id for asset in assets):
            return None
        by_id = {item["assetId"]: item["originalHash"] for item in decision.asset_hashes}
        if any(asset is None or by_id.get(asset.id) != asset.original_hash for asset in assets):
            return None
        return decision

    def create_character_reference_decision(
        self,
        project_id: str,
        *,
        character_id: str,
        primary_asset_id: str,
        complementary_asset_ids: list[str],
        expected_reference_revision: int,
        reviewer: str,
        notes: str,
    ) -> dict[str, Any]:
        """Select, never infer, a compact stable-identity reference set."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            character = next((item for item in bible.characters if item.id == character_id), None)
            if character is None:
                raise InvalidTransitionError("character reference must name a current canonical character")
            now = utc_now()
            state = self._character_reference_state_in_session(session, project_id, character_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("character-reference", expected_reference_revision, state.revision)
            asset_ids = [primary_asset_id, *complementary_asset_ids]
            if len(asset_ids) > 3 or len(asset_ids) != len(set(asset_ids)):
                raise InvalidTransitionError("character reference requires one primary and at most two distinct complementary assets")
            assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
            if any(asset is None or asset.project_id != project_id for asset in assets):
                raise NotFoundError("character reference asset not found in this project")
            context = self._character_reference_context(character)
            state.revision += 1
            state.updated_at = now
            decision = CharacterReferenceDecisionRow(
                id=new_id(), project_id=project_id, character_id=character_id,
                reference_revision=state.revision, character_context=context,
                character_context_hash=stable_hash(context), primary_asset_id=primary_asset_id,
                complementary_asset_ids=complementary_asset_ids,
                asset_hashes=[{"assetId": asset.id, "originalHash": asset.original_hash} for asset in assets if asset is not None],
                reviewer=reviewer.strip(), notes=notes.strip(), revoked_at=None, revoked_by=None,
                revocation_reason=None, created_at=now,
            )
            session.add(decision)
            session.flush()
            state.active_decision_id = decision.id
            session.flush()
            return self._reference_decision_dict(decision, current=True) | {"stateRevision": state.revision}

    def revoke_character_reference_decision(
        self,
        project_id: str,
        *,
        character_id: str,
        expected_reference_revision: int,
        reviewer: str,
        reason: str,
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            now = utc_now()
            state = self._character_reference_state_in_session(session, project_id, character_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("character-reference", expected_reference_revision, state.revision)
            if state.active_decision_id is None:
                raise InvalidTransitionError("character has no active reference decision to revoke")
            decision = session.get(CharacterReferenceDecisionRow, state.active_decision_id)
            if decision is None or decision.project_id != project_id:
                raise InvalidTransitionError("active character reference decision is unavailable")
            decision.revoked_at = now
            decision.revoked_by = reviewer.strip()
            decision.revocation_reason = reason.strip()
            state.revision += 1
            state.active_decision_id = None
            state.updated_at = now
            session.flush()
            return self._reference_decision_dict(decision, current=False) | {"stateRevision": state.revision}

    def list_character_reference_decisions(self, project_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            characters = {item.id: item for item in bible.characters}
            rows = session.scalars(
                select(CharacterReferenceDecisionRow)
                .where(CharacterReferenceDecisionRow.project_id == project_id)
                .order_by(CharacterReferenceDecisionRow.created_at.desc(), CharacterReferenceDecisionRow.id.desc())
            ).all()
            states = session.scalars(
                select(CharacterReferenceStateRow).where(CharacterReferenceStateRow.project_id == project_id)
            ).all()
            state_by_character = {item.character_id: item for item in states}
            return {
                "states": [{
                    "characterId": character_id, "revision": state.revision,
                    "activeDecisionId": state.active_decision_id,
                    "current": self._current_character_reference_in_session(session, project_id, characters[character_id]) is not None
                    if character_id in characters else False,
                } for character_id, state in sorted(state_by_character.items())],
                "decisions": [self._reference_decision_dict(
                    row,
                    current=(
                        row.revoked_at is None
                        and row.character_id in characters
                        and state_by_character.get(row.character_id) is not None
                        and state_by_character[row.character_id].active_decision_id == row.id
                        and self._current_character_reference_in_session(session, project_id, characters[row.character_id]) is not None
                    ),
                ) for row in rows],
            }

    @staticmethod
    def _proposal_dict(row: CharacterReferenceProposalRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "characterId": row.character_id,
            "parentCandidateAssetId": row.parent_candidate_asset_id, "request": row.request,
            "requestHash": row.request_hash, "state": row.state, "current": current,
            "exportedAt": _stored_utc(row.exported_at).isoformat() if row.exported_at else None,
            "cancelledAt": _stored_utc(row.cancelled_at).isoformat() if row.cancelled_at else None,
            "cancellationReason": row.cancellation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _proposal_is_current_in_session(
        self, session: Session, proposal: CharacterReferenceProposalRow
    ) -> bool:
        if proposal.state == "cancelled":
            return False
        project = session.get(ProjectRow, proposal.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        try:
            bible = self._canonical._load_stage_payload(session, proposal.project_id, StageName.STORY_BIBLE)
        except (NotFoundError, SchemaResetRequiredError):
            return False
        character = next((item for item in bible.characters if item.id == proposal.character_id), None)
        snapshot = proposal.request.get("frozenSnapshot")
        if character is None or not isinstance(snapshot, dict):
            return False
        return snapshot.get("characterContextHash") == stable_hash(self._character_reference_context(character))

    def prepare_character_reference_proposal(
        self,
        project_id: str,
        *,
        character_id: str,
        story_bible_revision: int,
        visual_direction: str,
        parent_candidate_asset_id: str | None,
    ) -> dict[str, Any]:
        """Freeze a story-first exploratory request without creating a fake Shot or Approval."""

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            if head.revision != story_bible_revision:
                raise RevisionConflictError("story-bible", story_bible_revision, head.revision)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            character = next((item for item in bible.characters if item.id == character_id), None)
            if character is None:
                raise InvalidTransitionError("character reference proposal must name a current canonical character")
            references: list[dict[str, Any]] = []
            if parent_candidate_asset_id is not None:
                candidate = session.scalar(
                    select(CharacterReferenceProposalCandidateRow)
                    .where(CharacterReferenceProposalCandidateRow.asset_id == parent_candidate_asset_id)
                    .order_by(CharacterReferenceProposalCandidateRow.created_at.desc()).limit(1)
                )
                parent = session.get(CharacterReferenceProposalRow, candidate.proposal_id) if candidate else None
                asset = session.get(ManagedAssetRow, parent_candidate_asset_id)
                if (
                    candidate is None or parent is None or asset is None or asset.project_id != project_id
                    or parent.character_id != character_id or not self._proposal_is_current_in_session(session, parent)
                ):
                    raise InvalidTransitionError("proposal refinement must name a current candidate for the same character")
                references.append({
                    "assetId": asset.id, "role": "parent_output", "required": True,
                    "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                })
            context = self._character_reference_context(character)
            job_id = self._image_job_id()
            snapshot = {
                "snapshotVersion": 3, "compilerVersion": "plotloom.character-reference-proposal.v1",
                "projectId": project_id, "target": "character_reference_proposal",
                "characterId": character_id, "storyBibleRevision": story_bible_revision,
                "storyBibleEntityRevisionId": head.entity_revision_id,
                "characterContext": context, "characterContextHash": stable_hash(context),
                "visualDirection": visual_direction.strip(), "references": references,
                "authority": "exploratory_only_no_storyboard_approval_or_keyframe_selection",
            }
            request = {
                "schemaVersion": 3, "jobId": job_id, "executionContract": "codex_specialist.v2",
                "specialistPreflight": {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3", "executionContract": "codex_specialist.v2"},
                "kind": "refinement" if parent_candidate_asset_id else "original",
                "target": "character_reference_proposal", "frozenSnapshot": snapshot,
            }
            proposal = CharacterReferenceProposalRow(
                id=job_id, project_id=project_id, character_id=character_id,
                parent_candidate_asset_id=parent_candidate_asset_id, request=request,
                request_hash=stable_hash(request), state="prepared", exported_at=None,
                cancelled_at=None, cancellation_reason=None, created_at=utc_now(),
            )
            session.add(proposal)
            session.flush()
            return {"proposal": self._proposal_dict(proposal, current=True)}

    def character_reference_proposal_package_sources(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("character reference proposal is no longer current and cannot be copied")
            sources: list[dict[str, Any]] = []
            for reference in proposal.request["frozenSnapshot"].get("references", []):
                asset = session.get(ManagedAssetRow, reference.get("assetId"))
                if asset is None or asset.project_id != project_id or asset.original_hash != reference.get("originalHash"):
                    raise InvalidTransitionError("frozen proposal reference bytes are unavailable")
                sources.append({
                    "role": reference["role"], "contentHash": asset.original_hash,
                    "mimeType": asset.mime_type, "originalUri": asset.original_uri,
                })
            return {"proposal": self._proposal_dict(proposal, current=True), "references": sources}

    def mark_character_reference_proposal_exported(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("character reference proposal is no longer current and cannot be copied")
            if proposal.exported_at is None:
                proposal.exported_at = utc_now()
                proposal.state = "exported"
                session.flush()
            return self._proposal_dict(proposal, current=True)

    def character_reference_proposal_delivery_context(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            return self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal))

    def record_character_reference_proposal_rejection(self, project_id: str, proposal_id: str, code: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            session.add(CharacterReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, created_at=utc_now(),
            ))

    def record_character_reference_proposal_delivery(
        self,
        project_id: str,
        proposal_id: str,
        *,
        delivery_id: str,
        manifest: dict[str, Any],
        manifest_hash: str,
        outputs: list[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            existing = session.scalar(
                select(CharacterReferenceProposalDeliveryRow)
                .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal_id, CharacterReferenceProposalDeliveryRow.delivery_id == delivery_id)
                .limit(1)
            )
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "proposal delivery identity was already recorded with different content")
                candidates = session.scalars(
                    select(CharacterReferenceProposalCandidateRow)
                    .where(CharacterReferenceProposalCandidateRow.delivery_id == existing.id)
                    .order_by(CharacterReferenceProposalCandidateRow.created_at, CharacterReferenceProposalCandidateRow.id)
                ).all()
                return {"deliveryId": delivery_id, "state": existing.state, "diagnosticCode": existing.diagnostic_code,
                        "idempotent": True, "candidates": [self._proposal_candidate_dict(session, item) for item in candidates]}
            finalized = session.scalar(
                select(CharacterReferenceProposalDeliveryRow)
                .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal_id, CharacterReferenceProposalDeliveryRow.delivery_id.is_not(None))
                .limit(1)
            )
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "character proposal already has a final delivery")
            current = proposal.state in {"exported", "delivered"} and self._proposal_is_current_in_session(session, proposal)
            delivery = CharacterReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                        "idempotent": False, "candidates": []}
            candidates: list[CharacterReferenceProposalCandidateRow] = []
            for output in outputs:
                original_uri, display_uri = publish(output)
                asset = ManagedAssetRow(
                    id=new_id(), project_id=project_id, original_uri=original_uri,
                    original_hash=output["originalHash"], display_uri=display_uri,
                    display_hash=output["displayHash"], mime_type=output["mimeType"], byte_size=output["byteSize"],
                    width=output["width"], height=output["height"], created_at=utc_now(),
                )
                session.add(asset)
                session.flush()
                session.add(ManagedAssetProvenanceRow(
                    id=new_id(), project_id=project_id, asset_id=asset.id,
                    declaration={
                        "origin": "character_reference_proposal", "rights": "unknown", "proposalId": proposal.id,
                        "rightsNote": None, "declaredAdditions": [], "deliveryId": delivery_id,
                        "outputFilename": output["filename"], "actualPrompt": manifest["actualPrompt"],
                        "toolEvidence": manifest["toolEvidence"], "executorProvenance": manifest.get("executorProvenance"),
                        "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                candidate = CharacterReferenceProposalCandidateRow(
                    id=new_id(), proposal_id=proposal.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                )
                session.add(candidate)
                candidates.append(candidate)
            proposal.state = "delivered"
            session.flush()
            return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": None,
                    "idempotent": False, "candidates": [self._proposal_candidate_dict(session, item) for item in candidates]}

    @staticmethod
    def _proposal_candidate_dict(session: Session, row: CharacterReferenceProposalCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "proposalId": row.proposal_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": ProjectMediaPersistence._managed_asset_dict(asset) if asset is not None else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def list_character_reference_proposals(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            proposals = session.scalars(
                select(CharacterReferenceProposalRow).where(CharacterReferenceProposalRow.project_id == project_id)
                .order_by(CharacterReferenceProposalRow.created_at.desc(), CharacterReferenceProposalRow.id.desc())
            ).all()
            result: list[dict[str, Any]] = []
            for proposal in proposals:
                deliveries = session.scalars(
                    select(CharacterReferenceProposalDeliveryRow)
                    .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal.id)
                    .order_by(CharacterReferenceProposalDeliveryRow.created_at.desc(), CharacterReferenceProposalDeliveryRow.id.desc())
                ).all()
                result.append({
                    **self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal)),
                    "deliveries": [{
                        "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                        "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                        "createdAt": _stored_utc(delivery.created_at).isoformat(),
                        "candidates": [self._proposal_candidate_dict(session, item) for item in session.scalars(
                            select(CharacterReferenceProposalCandidateRow)
                            .where(CharacterReferenceProposalCandidateRow.delivery_id == delivery.id)
                            .order_by(CharacterReferenceProposalCandidateRow.created_at, CharacterReferenceProposalCandidateRow.id)
                        ).all()],
                    } for delivery in deliveries],
                })
            return result

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

    def _identity_mapping_for_binding_in_session(
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

    def _same_person_review_is_current_in_session(
        self, session: Session, project_id: str, review: SamePersonReviewRow
    ) -> bool:
        binding = session.get(ReviewedShotBindingRow, review.binding_id)
        if binding is None or binding.project_id != project_id:
            return False
        try:
            approval = self._approval_is_active_in_session(session, binding.approval_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not self._reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
            return False
        mapping = self._identity_mapping_for_binding_in_session(session, binding)
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
            current = self._current_character_reference_in_session(session, project_id, character) if character else None
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
            mapping = self._identity_mapping_for_binding_in_session(session, binding)
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
            return self._same_person_review_dict(review, current=self._same_person_review_is_current_in_session(session, project_id, review)) | {"stateRevision": state.revision}

    def list_same_person_reviews(self, project_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            state = session.get(SamePersonReviewStateRow, project_id)
            rows = session.scalars(
                select(SamePersonReviewRow).where(SamePersonReviewRow.project_id == project_id)
                .order_by(SamePersonReviewRow.created_at.desc(), SamePersonReviewRow.id.desc())
            ).all()
            return {"revision": state.revision if state else 0, "reviews": [
                self._same_person_review_dict(row, current=self._same_person_review_is_current_in_session(session, project_id, row))
                for row in rows
            ]}

    def current_same_person_review_for_binding(
        self, session: Session, project_id: str, binding: ReviewedShotBindingRow
    ) -> SamePersonReviewRow | None:
        mapping = self._identity_mapping_for_binding_in_session(session, binding)
        if mapping is None:
            return None
        rows = session.scalars(
            select(SamePersonReviewRow)
            .where(SamePersonReviewRow.project_id == project_id, SamePersonReviewRow.binding_id == binding.id)
            .order_by(SamePersonReviewRow.review_revision.desc())
        ).all()
        return next((row for row in rows if self._same_person_review_is_current_in_session(session, project_id, row)), None)

    @staticmethod
    def _image_job_id() -> str:
        return f"ij_{new_id().replace('-', '')}"

    @staticmethod
    def _image_job_dict(row: ImageJobRow, *, current: bool) -> dict[str, Any]:
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
    def _production_unit_dict(row: ProductionUnitRow) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "approvalId": row.approval_id,
            "shotId": row.shot_id, "sceneId": row.scene_id,
            "storyboardRevision": row.storyboard_revision, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _image_job_is_current_in_session(self, session: Session, job: ImageJobRow) -> bool:
        if job.state == "cancelled":
            return False
        project = session.get(ProjectRow, job.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        unit = session.get(ProductionUnitRow, job.production_unit_id)
        if unit is None or unit.project_id != job.project_id:
            return False
        try:
            approval = self._approval_is_active_in_session(session, unit.approval_id)
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
            if not self._reviewed_binding_admission_eligible_in_session(
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
            decision = self._current_character_reference_in_session(session, job.project_id, character)
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
    def _image_job_resolved_context(
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
            approval = self._approval_is_active_in_session(session, approval_id)
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
                    decision = self._current_character_reference_in_session(session, project_id, character)
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
                    or not self._image_job_is_current_in_session(session, parent_job)
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
                    or not self._reviewed_binding_admission_eligible_in_session(
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
                if binding is None or not self._reviewed_binding_admission_eligible_in_session(
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
            resolved_context = self._image_job_resolved_context(
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
            job_id = self._image_job_id()
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
            return {"job": self._image_job_dict(job, current=True), "productionUnit": self._production_unit_dict(unit)}

    def image_job_package_sources(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state == "cancelled" or not self._image_job_is_current_in_session(session, job):
                raise InvalidTransitionError("image job is no longer current and cannot be copied")
            sources: list[dict[str, Any]] = []
            for reference in job.request["frozenSnapshot"].get("references", []):
                if reference.get("role") not in {
                    "parent_output", "source_keyframe", "character_identity"
                }:
                    continue
                asset = session.get(ManagedAssetRow, reference.get("assetId"))
                if (
                    asset is None or asset.project_id != project_id
                    or asset.original_hash != reference.get("originalHash")
                ):
                    raise InvalidTransitionError("frozen image-job reference bytes are unavailable")
                sources.append({
                    "role": reference["role"], "contentHash": asset.original_hash,
                    "mimeType": asset.mime_type, "originalUri": asset.original_uri,
                    "characterId": reference.get("characterId"),
                })
            return {"job": self._image_job_dict(job, current=True), "references": sources}

    def mark_image_job_exported(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state == "cancelled" or not self._image_job_is_current_in_session(session, job):
                raise InvalidTransitionError("image job is no longer current and cannot be copied")
            if job.exported_at is None:
                job.exported_at = utc_now()
                job.state = "exported"
                session.flush()
            return self._image_job_dict(job, current=True)

    def cancel_image_job(self, project_id: str, job_id: str, reason: str) -> dict[str, Any]:
        reason = reason.strip()
        if not reason or len(reason) > 2_000:
            raise ValueError("image job cancellation reason must be between 1 and 2,000 characters")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state != "cancelled":
                job.state = "cancelled"
                job.cancelled_at = utc_now()
                job.cancellation_reason = reason
                session.flush()
            return self._image_job_dict(job, current=False)

    def image_job_delivery_context(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            return self._image_job_dict(job, current=self._image_job_is_current_in_session(session, job))

    def record_image_job_delivery_rejection(self, project_id: str, job_id: str, code: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            session.add(ImageJobDeliveryRow(
                id=new_id(), job_id=job_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, created_at=utc_now(),
            ))

    @staticmethod
    def _image_candidate_dict(session: Session, row: ImageJobCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "jobId": row.job_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": ProjectMediaPersistence._managed_asset_dict(asset) if asset else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def record_image_job_delivery(
        self, project_id: str, job_id: str, *, delivery_id: str, manifest: dict[str, Any],
        manifest_hash: str, outputs: Sequence[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        """Atomically admit one verified delivery, publishing only after admission.

        The artifact callback runs under the lifecycle writer only after the
        durable final-delivery, project-lifecycle, and currentness checks pass.
        It keeps a duplicate, cancelled, revoked, or archived Refresh from
        creating unowned content-addressed blobs before repository admission.
        """

        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            existing = session.scalar(
                select(ImageJobDeliveryRow)
                .where(ImageJobDeliveryRow.job_id == job_id, ImageJobDeliveryRow.delivery_id == delivery_id)
                .limit(1)
            )
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "delivery identity was already recorded with different content")
                candidates = session.scalars(
                    select(ImageJobCandidateRow).where(ImageJobCandidateRow.delivery_id == existing.id)
                    .order_by(ImageJobCandidateRow.created_at, ImageJobCandidateRow.id)
                ).all()
                return {"deliveryId": delivery_id, "state": existing.state, "diagnosticCode": existing.diagnostic_code,
                        "idempotent": True, "candidates": [self._image_candidate_dict(session, item) for item in candidates]}
            finalized = session.scalar(
                select(ImageJobDeliveryRow)
                .where(ImageJobDeliveryRow.job_id == job_id, ImageJobDeliveryRow.delivery_id.is_not(None))
                .limit(1)
            )
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "image job already has a final delivery")
            current = job.state in {"exported", "delivered"} and self._image_job_is_current_in_session(session, job)
            delivery = ImageJobDeliveryRow(
                id=new_id(), job_id=job_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                        "idempotent": False, "candidates": []}
            candidates: list[ImageJobCandidateRow] = []
            for output in outputs:
                original_uri, display_uri = publish(output)
                asset = ManagedAssetRow(
                    id=new_id(), project_id=project_id, original_uri=original_uri,
                    original_hash=output["originalHash"], display_uri=display_uri,
                    display_hash=output["displayHash"], mime_type=output["mimeType"], byte_size=output["byteSize"],
                    width=output["width"], height=output["height"], created_at=utc_now(),
                )
                session.add(asset)
                session.flush()
                session.add(ManagedAssetProvenanceRow(
                    id=new_id(), project_id=project_id, asset_id=asset.id,
                    declaration={
                        "origin": "codex_image_job", "rights": "unknown", "jobId": job.id,
                        "rightsNote": None, "declaredAdditions": [],
                        "deliveryId": delivery_id, "outputFilename": output["filename"],
                        "actualPrompt": manifest["actualPrompt"], "toolEvidence": manifest["toolEvidence"],
                        "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                candidate = ImageJobCandidateRow(
                    id=new_id(), job_id=job.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                )
                session.add(candidate)
                candidates.append(candidate)
            job.state = "delivered"
            session.flush()
            return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": None,
                    "idempotent": False, "candidates": [self._image_candidate_dict(session, item) for item in candidates]}

    def list_image_jobs(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            jobs = session.scalars(
                select(ImageJobRow).where(ImageJobRow.project_id == project_id)
                .order_by(ImageJobRow.created_at.desc(), ImageJobRow.id.desc())
            ).all()
            result: list[dict[str, Any]] = []
            for job in jobs:
                deliveries = session.scalars(
                    select(ImageJobDeliveryRow).where(ImageJobDeliveryRow.job_id == job.id)
                    .order_by(ImageJobDeliveryRow.created_at.desc(), ImageJobDeliveryRow.id.desc())
                ).all()
                result.append({
                    **self._image_job_dict(job, current=self._image_job_is_current_in_session(session, job)),
                    "deliveries": [
                        {
                            "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                            "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                            "createdAt": _stored_utc(delivery.created_at).isoformat(),
                            "candidates": [self._image_candidate_dict(session, candidate) for candidate in session.scalars(
                                select(ImageJobCandidateRow).where(ImageJobCandidateRow.delivery_id == delivery.id)
                                .order_by(ImageJobCandidateRow.created_at, ImageJobCandidateRow.id)
                            ).all()],
                        }
                        for delivery in deliveries
                    ],
                })
            return result

    def get_media_prompt_context(self, project_id: str, shot_id: str) -> MediaPromptContext:
        """Freeze canonical facts consumed by an application-layer prompt compiler."""

        with self._access.leases.read() as session:
            project = self._access.codecs.project(self._access.rows.project(session, project_id))
            bible_head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            if bible_head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORY_BIBLE, bible_head.status)
            head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORYBOARD, head.status)
            storyboard = self._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
            assert isinstance(storyboard, Storyboard)
            shot = next((candidate for candidate in storyboard.shots if candidate.id == shot_id), None)
            if shot is None:
                raise NotFoundError(f"shot not found in current storyboard: {shot_id}")
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            assert isinstance(bible, StoryBible)
            return MediaPromptContext(
                brief=project.brief,
                story_bible=bible,
                shot=shot,
                storyboard_revision=head.revision,
            )

    def create_media_task(
        self,
        project_id: str,
        shot_id: str,
        kind: MediaKind,
        *,
        expected_storyboard_revision: int,
        derived_prompt: str,
        prompt_components: dict[str, Any],
        provider: str | None = None,
        public_settings: dict[str, Any] | None = None,
    ) -> MediaTask:
        """Reject the pre-M2 Shot-to-provider path before any data access.

        Approval alone is deliberately not a production input.  M2 will
        replace this compatibility-shaped entry point with one that accepts an
        immutable ProductionSnapshot; keeping the method callable today would
        let an in-process caller bypass the API's hard stop.
        """

        _ = (
            project_id,
            shot_id,
            kind,
            expected_storyboard_revision,
            derived_prompt,
            prompt_components,
            provider,
            public_settings,
        )
        raise ProductionPipelineNotReadyError()

    def get_media_task(self, task_id: str) -> MediaTask:
        with self._access.leases.read() as session:
            return self._media_task(self._access.rows.media_task(session, task_id))

    def list_project_media_tasks(self, project_id: str, *, limit: int = 200) -> list[MediaTask]:
        if not 1 <= limit <= 500:
            raise ValueError("media task list limit must be between 1 and 500")
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(MediaTaskRow)
                .where(MediaTaskRow.project_id == project_id)
                .order_by(MediaTaskRow.created_at.desc())
                .limit(limit)
            ).all()
            return [self._media_task(row) for row in rows]

    def start_media_task(self, task_id: str, *, provider: str | None = None) -> MediaTask:
        # Every task stored before M2 lacks a ProductionSnapshot.  Do not even
        # read it here: callers must not turn a queued historical row into a
        # provider-bound execution by bypassing the HTTP hard stop.
        _ = (task_id, provider)
        raise ProductionPipelineNotReadyError()

    def record_media_submission(
        self,
        task_id: str,
        *,
        provider: str,
        provider_task_id: str | None,
    ) -> MediaTask:
        # A persisted provider task ID would make subsequent polling a new
        # production operation.  Historical rows can only be read or safely
        # terminalized until M2 owns that immutable boundary.
        _ = (task_id, provider, provider_task_id)
        raise ProductionPipelineNotReadyError()

    def finish_media_task(
        self,
        task_id: str,
        status: MediaTaskStatus,
        *,
        output_uri: str | None = None,
        error: str | None = None,
    ) -> MediaTask:
        if status not in TERMINAL_MEDIA_TASK_STATUSES:
            raise InvalidTransitionError("finish_media_task requires a terminal status")
        if status == MediaTaskStatus.SUCCEEDED:
            # Success would attach a new provider-derived URI to a legacy row.
            # Preserve only failure/cancellation for upgrade recovery.
            raise ProductionPipelineNotReadyError()
        normalized_error = error.strip() if error else None
        if status == MediaTaskStatus.FAILED and not normalized_error:
            raise ValueError("failed media tasks require an error")
        with self._access.leases.write() as session:
            row = self._access.rows.media_task(session, task_id)
            if MediaTaskStatus(row.status) != MediaTaskStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish media task from {row.status}")
            now = utc_now()
            row.status = status.value
            row.output_uri = None
            row.error = normalized_error if status == MediaTaskStatus.FAILED else None
            row.finished_at = now
            row.updated_at = now
            return self._media_task(row)
