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


class KeyframeAdmission:
    """Own session-local reviewed-keyframe currentness and approval admission."""

    def __init__(self, access: ProjectPersistenceAccess) -> None:
        self._access = access

    @staticmethod
    def latest_visual_intent_for_role_in_session(
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
        latest_intent = self.latest_visual_intent_for_role_in_session(
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
                approval = self.approval_is_active_in_session(session, binding.approval_id)
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
                if self.reviewed_binding_admission_eligible_in_session(session, project_id, row)
            ]


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
    def selection_state_in_session(session: Session, project_id: str, now: datetime) -> VisualSelectionStateRow:
        state = session.get(VisualSelectionStateRow, project_id)
        if state is None:
            state = VisualSelectionStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state
