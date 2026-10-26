"""Explicit same-person review persistence for identity-aware image candidates."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import ValidationError

from plotloom.stage_contracts import StageName
from plotloom.contract_identity import new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError, SchemaResetRequiredError
from ...same_person_review_contracts import SamePersonReviewObservations, SamePersonReviewRequest
from ...human_confirmation_contracts import UnnamedCreatorConfirmation
from .human_attribution import attribution_readback, stored_reviewer
from ..codec import _stored_utc
from ..schema import (
    ImageJobCandidateRow,
    ImageJobRow,
    ManagedAssetRow,
    ReviewedShotBindingRow,
    SamePersonReviewRow,
    SamePersonReviewStateRow,
    VisualIntentRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence


class SamePersonReviewPersistence:
    """Own the human identity-review facts required for preview admission."""

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
    def _same_person_review_state_in_session(
        session: Session, project_id: str, now: datetime
    ) -> SamePersonReviewStateRow:
        state = session.get(SamePersonReviewStateRow, project_id)
        if state is None:
            state = SamePersonReviewStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state

    def _same_person_review_dict(self, row: SamePersonReviewRow, *, current: bool, latest: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "bindingId": row.binding_id,
            "reviewRevision": row.review_revision, "referenceBindings": list(row.reference_bindings),
            "comparisons": list(row.comparisons), "reviewer": row.reviewer, "notes": row.notes,
            "current": current, "latest": latest,
            "productionEligible": current and latest and self.comparisons_authorize_production(row.comparisons),
            "createdAt": _stored_utc(row.created_at).isoformat(),
        } | attribution_readback(row.reviewer, row.project_id)

    def identity_mapping_for_binding_in_session(
        self, session: Session, binding: ReviewedShotBindingRow
    ) -> list[dict[str, Any]] | None:
        from .image_reviewed_use import use_in_session
        intent = session.get(VisualIntentRow, binding.visual_intent_id)
        if intent is not None and intent.intent.get("targetUse") is not None:
            from .human_comparison_mapping import human_mapping
            return human_mapping(session, binding, self._canonical, self._references)
        source = use_in_session(session, binding)
        if source is None:
            return None
        job = session.get(ImageJobRow, source.job_id)
        if job is None or job.request.get("schemaVersion") != 3:
            return None
        snapshot = job.request.get("frozenSnapshot")
        mapping = snapshot.get("characterIdentity") if isinstance(snapshot, dict) else None
        if not isinstance(mapping, list) or any(not isinstance(item, dict) for item in mapping):
            return None
        return mapping

    def same_person_review_is_current_in_session(
        self, session: Session, project_id: str, review: SamePersonReviewRow
    ) -> bool:
        from .bulk_handoff_basis import review_has_basis
        if review.reviewer == "" or any("confirmation" in item for item in review.comparisons):
            authority = self._access.authority()
            from ...autopilot_contracts import OperationScope
            detailed_write = authority is not None and authority.scope == OperationScope.HANDOFF and not any("confirmation" in item for item in review.comparisons)
            if not detailed_write and not review_has_basis(session, review):
                return False
        binding = session.get(ReviewedShotBindingRow, review.binding_id)
        if binding is None or binding.project_id != project_id:
            return False
        try:
            approval = self._admission.approval_is_active_in_session(session, binding.approval_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not self._admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
            return False
        from .image_reviewed_use import use_in_session
        try:
            source = use_in_session(session, binding)
            mapping = self.identity_mapping_for_binding_in_session(session, binding)
        except InvalidTransitionError:
            return False
        asset = session.get(ManagedAssetRow, binding.asset_id)
        if asset is None or asset.project_id != project_id:
            return False
        intent = session.get(VisualIntentRow, binding.visual_intent_id)
        cross_shot = intent is not None and intent.intent.get("targetUse") is not None
        cross_shot_context = bool(review.reference_bindings) and all(item.get("comparisonOrigin") == "cross_shot_target_use" for item in review.reference_bindings)
        if cross_shot != cross_shot_context or (cross_shot and any(item.get("frameHash") != asset.original_hash for item in review.reference_bindings)):
            return False
        human_context = bool(review.reference_bindings) and all(item.get("comparisonOrigin") == "human_current_material" for item in review.reference_bindings)
        if not human_context and not cross_shot and source is None:
            return False
        if source and source.geometry:
            if any(item.get("frameHash") != asset.original_hash or item.get("geometryPreparationHash") != source.geometry.preparation_hash for item in review.reference_bindings):
                return False
        if human_context:
            source_job = session.get(ImageJobRow, source.job_id) if source else None
            if source and (source.geometry or source_job.request.get("schemaVersion", 1) not in {1, 2}):
                return False
            from .human_comparison_mapping import human_mapping
            try:
                mapping = human_mapping(session, binding, self._canonical, self._references)
            except (InvalidTransitionError, NotFoundError, SchemaResetRequiredError):
                return False
            if any(item.get("frameHash") != asset.original_hash for item in review.reference_bindings):
                return False
        if mapping is None:
            return False
        expected = {item.get("characterId"): item for item in mapping}
        if [item.get("characterId") for item in review.comparisons] != list(expected):
            return False
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
            current = self._references.current_character_reference_in_session(session, project_id, character) if character else None
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

    @staticmethod
    def comparisons_authorize_production(comparisons: list[dict[str, Any]]) -> bool:
        return bool(comparisons) and all(
            item.get("judgment") == "pass" or (
                item.get("judgment") == "unassessable"
                and item.get("productionDecision") == "authorize"
                and isinstance(item.get("uncertaintyReason"), str)
                and bool(item["uncertaintyReason"].strip())
            ) for item in comparisons
        )

    def same_person_review_is_production_eligible_in_session(
        self, session: Session, project_id: str, review: SamePersonReviewRow
    ) -> bool:
        if not self.same_person_review_is_current_in_session(session, project_id, review):
            return False
        binding = session.get(ReviewedShotBindingRow, review.binding_id)
        latest = self.current_same_person_review_for_binding(session, project_id, binding)
        return latest is not None and latest.id == review.id and self.comparisons_authorize_production(review.comparisons)

    def record_same_person_review(
        self,
        project_id: str,
        *,
        binding_id: str,
        expected_review_revision: int,
        reviewer: str | UnnamedCreatorConfirmation,
        comparisons: list[dict[str, Any]],
        notes: str,
        bulk_basis=None,
    ) -> dict[str, Any]:
        """Persist an explicit human judgment about a v3 generated keyframe."""
        from .autopilot_authority import require_human_command
        require_human_command(self._access)
        from ...delegated_qa_contracts import AgentQaAttribution
        qa_actor = reviewer if isinstance(reviewer, AgentQaAttribution) else None
        if qa_actor is not None and bulk_basis is None:
            raise InvalidTransitionError("QA identity observations require the exact atomic material handoff")
        try:
            from ...delegated_qa import reviewer_for
            normalized_reviewer = reviewer_for(qa_actor) if qa_actor else stored_reviewer(self._access, reviewer)
            fields = dict(binding_id=binding_id, expected_review_revision=expected_review_revision, comparisons=comparisons, notes=notes)
            if bulk_basis is not None:
                bulk_basis.require(self._access)
                from ...bulk_material_contracts import StoredBulkIdentityJudgment
                parsed = [StoredBulkIdentityJudgment.model_validate(item) for item in comparisons]
                if not parsed or any(item.confirmation.receipt_id != bulk_basis.receipt_id or item.confirmation.bundle_hash != bulk_basis.bundle_hash
                        or item.confirmation.shot_id != bulk_basis.shot_id for item in parsed):
                    raise ValueError("bulk comparison authority changed")
                request = None
            else:
                request = (SamePersonReviewObservations(**fields) if isinstance(reviewer, UnnamedCreatorConfirmation)
                    else SamePersonReviewRequest(**fields, reviewer=reviewer))
        except (ValidationError, ValueError) as error:
            raise InvalidTransitionError("same-person review requires complete explicit judgments and uncertainty decisions") from error
        comparisons = [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in (parsed if bulk_basis is not None else request.comparisons)]
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if binding is None or binding.project_id != project_id:
                raise NotFoundError("reviewed keyframe binding not found")
            if qa_actor is not None:
                from ...delegated_qa import require_qa_write, attribution_for_reviewer
                from ..schema import ApprovalDecisionRow
                require_qa_write(session, project_id, qa_actor, asset_id=binding.asset_id, shot_id=binding.shot_id)
                approval = session.get(ApprovalDecisionRow, binding.approval_id)
                if attribution_for_reviewer(project_id, approval.reviewer) != qa_actor.model_dump(mode="json", by_alias=True):
                    raise InvalidTransitionError("QA identity review attribution differs from its material approval")
            if bulk_basis is not None and session.info.get("pending_bulk_bindings", {}).get(binding_id) != bulk_basis:
                raise InvalidTransitionError("bulk identity review must bind its exact pending handoff frame")
            from .image_reviewed_use import use_in_session
            source = use_in_session(session, binding)
            mapping = self.identity_mapping_for_binding_in_session(session, binding)
            human_context = False
            source_job = session.get(ImageJobRow, source.job_id) if source else None
            earlier_native = source is not None and source.geometry is None and source_job.request.get("schemaVersion", 1) in {1, 2}
            if mapping is None and (source is None or earlier_native):
                from ...autopilot_contracts import OperationScope
                authority = self._access.authority()
                if authority is not None and authority.scope == OperationScope.HANDOFF:
                    from .human_comparison_mapping import human_mapping
                    mapping = human_mapping(session, binding, self._canonical, self._references)
                    human_context = True
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
            if source and source.geometry:
                reference_bindings = [item | {"frameHash": source.output_hash, "geometryPreparationHash": source.geometry.preparation_hash} for item in reference_bindings]
            if human_context:
                asset = session.get(ManagedAssetRow, binding.asset_id)
                reference_bindings = [item | {"comparisonOrigin": "human_current_material", "frameHash": asset.original_hash} for item in reference_bindings]
            intent = session.get(VisualIntentRow, binding.visual_intent_id)
            if intent is not None and intent.intent.get("targetUse") is not None:
                asset = session.get(ManagedAssetRow, binding.asset_id)
                reference_bindings = [item | {"comparisonOrigin": "cross_shot_target_use", "frameHash": asset.original_hash} for item in reference_bindings]
            state.revision += 1
            state.updated_at = now
            review = SamePersonReviewRow(
                id=new_id(), project_id=project_id, binding_id=binding_id, review_revision=state.revision,
                reference_bindings=reference_bindings, comparisons=comparisons, reviewer=normalized_reviewer,
                notes=notes if bulk_basis is not None else notes.strip(), created_at=now,
            )
            session.add(review)
            session.flush()
            return self._same_person_review_dict(review, current=self.same_person_review_is_current_in_session(session, project_id, review), latest=True) | {"stateRevision": state.revision}

    def list_same_person_reviews(self, project_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            state = session.get(SamePersonReviewStateRow, project_id)
            rows = session.scalars(
                select(SamePersonReviewRow).where(SamePersonReviewRow.project_id == project_id)
                .order_by(SamePersonReviewRow.review_revision.desc())
            ).all()
            seen_bindings: set[str] = set()
            reviews = []
            for row in rows:
                current = self.same_person_review_is_current_in_session(session, project_id, row)
                latest = current and row.binding_id not in seen_bindings
                if current:
                    seen_bindings.add(row.binding_id)
                reviews.append(self._same_person_review_dict(row, current=current, latest=latest))
            return {"revision": state.revision if state else 0, "reviews": reviews}

    def current_same_person_review_for_binding(
        self, session: Session, project_id: str, binding: ReviewedShotBindingRow
    ) -> SamePersonReviewRow | None:
        rows = session.scalars(
            select(SamePersonReviewRow)
            .where(SamePersonReviewRow.project_id == project_id, SamePersonReviewRow.binding_id == binding.id)
            .order_by(SamePersonReviewRow.review_revision.desc())
        ).all()
        return next((row for row in rows if self.same_person_review_is_current_in_session(session, project_id, row)), None)
