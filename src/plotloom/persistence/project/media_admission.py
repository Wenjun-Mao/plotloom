"""Typed currentness and admission queries for reviewed keyframe operations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, StageStatus
from ...exceptions import InvalidTransitionError, NotFoundError
from ..schema import (
    ApprovalDecisionRow,
    EntityRevisionRow,
    GateResultRow,
    ReviewedShotBindingRow,
    VisualIntentRow,
    VisualSelectionStateRow,
)
from .access import ProjectPersistenceAccess
from .media_shot_presentations import ShotPresentations


class KeyframeAdmission:
    """Own session-local reviewed-keyframe currentness and approval admission."""

    def __init__(self, access: ProjectPersistenceAccess, *, generated_source_currentness) -> None:
        self._access = access
        self._generated_source_currentness = generated_source_currentness

    @staticmethod
    def latest_visual_intent_for_role_in_session(
        session: Session, project_id: str, asset_id: str, role: str | None, target_shot_id: str | None = None
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
                and (candidate.intent.get("targetUse") or {}).get("targetShotId") == target_shot_id
            ),
            None,
        )

    def reviewed_binding_admission_eligible_in_session(
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
        try:
            self._generated_source_currentness(session, binding)
        except (InvalidTransitionError, NotFoundError):
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
        return self.reviewed_binding_context_current_in_session(session, project_id, binding, approval=approval)

    def reviewed_binding_context_current_in_session(self, session, project_id, binding, *, approval=None):
        """Exact frozen intent/presentation/approval; selection position is separate."""
        if binding.project_id != project_id or not ShotPresentations.binding_matches(session, binding):
            return False
        if not binding.compatibility_note.strip():
            from .bulk_handoff_basis import binding_has_basis
            if not binding_has_basis(session, binding):
                return False
        intent = session.get(VisualIntentRow, binding.visual_intent_id)
        if (
            intent is None
            or intent.project_id != project_id
            or intent.asset_id != binding.asset_id
            or intent.revision != binding.visual_intent_revision
        ):
            return False
        if "sourceEndorsement" in intent.intent:
            from .handoff_intent_context import assert_source_intent
            try:
                assert_source_intent(session.connection().connection.driver_connection, project_id,
                    {key: value for key, value in intent.intent.items() if key != "targetUse"})
            except (ValueError, TypeError, KeyError):
                return False
        latest_intent = self.latest_visual_intent_for_role_in_session(
            session, project_id, binding.asset_id, intent.intent.get("role"),
            (intent.intent.get("targetUse") or {}).get("targetShotId")
        )
        if (
            latest_intent is None
            or latest_intent.id != intent.id
            or latest_intent.revision != intent.revision
        ):
            return False
        if approval is None:
            try:
                approval = self.approval_is_active_in_session(session, binding.approval_id)
            except (InvalidTransitionError, NotFoundError):
                return False
        from ...delegated_qa import binding_attribution
        try:
            # Image adaptation consumes a narrowed ImageAuthorityBinding. Actor
            # facts belong to its exact retained approval, not that projection.
            attributed_approval = session.get(ApprovalDecisionRow, binding.approval_id)
            if attributed_approval is None:
                return False
            binding_attribution(project_id, attributed_approval, intent.intent, asset_id=binding.asset_id, shot_id=binding.shot_id)
        except (InvalidTransitionError, ValueError):
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
            result = [
                {
                    "id": row.id, "assetId": row.asset_id, "shotId": row.shot_id,
                    "sceneId": row.scene_id, "selectionRevision": row.selection_revision,
                    "visualIntentId": row.visual_intent_id,
                    "visualIntentRevision": row.visual_intent_revision,
                    "compatibilityNote": row.compatibility_note,
                }
                for row in latest.values()
                if self.reviewed_binding_admission_eligible_in_session(session, project_id, row)
            ]
            from .bulk_handoff_basis import receipt_basis
            for item in result:
                intent = session.get(VisualIntentRow, item["visualIntentId"])
                if intent.intent.get("attribution"):
                    item["attribution"] = intent.intent["attribution"]
                basis = receipt_basis(session, project_id, item["id"])
                if basis is not None:
                    item["confirmationBasis"] = basis
            return result


    def approval_is_active_in_session(self, session: Session, decision_id: str) -> ApprovalDecisionRow:
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
        from .canonical_gate_evidence import gates_pass
        if not gates_pass(session, self._access.codecs, decision.entity_revision_id, gate_set_version=decision.gate_set_version):
            raise InvalidTransitionError("reviewed selection approval gates are no longer passing")
        return decision

    @staticmethod
    def selection_state_in_session(session: Session, project_id: str, now: datetime) -> VisualSelectionStateRow:
        state = session.get(VisualSelectionStateRow, project_id)
        if state is None:
            state = VisualSelectionStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state
