"""Exact authored-timing lineage for a frozen video request or segment."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, StageStatus
from ...exceptions import InvalidTransitionError
from ..codec import stable_hash
from ..schema import (
    ProductionBridgeAdmissionRow,
    ProductionBridgeHeadRow,
    ProductionBridgeRevisionRow,
)
from .access import ProjectPersistenceAccess


class VideoSourceTiming:
    """Separate F5 bridge authority from canonical-only shot timing."""

    def __init__(self, access: ProjectPersistenceAccess, bridge: Any | None) -> None:
        self._access = access
        self._bridge = bridge

    def binding_in_session(
        self, session: Session, project_id: str, shot_id: str, duration_units: int
    ) -> dict[str, Any]:
        admissions = session.scalars(
            select(ProductionBridgeAdmissionRow)
            .where(ProductionBridgeAdmissionRow.project_id == project_id)
            .order_by(ProductionBridgeAdmissionRow.accepted_at.desc(), ProductionBridgeAdmissionRow.id.desc())
        )
        for admission in admissions:
            revision = session.scalar(
                select(ProductionBridgeRevisionRow).where(
                    ProductionBridgeRevisionRow.project_id == project_id,
                    ProductionBridgeRevisionRow.revision == admission.proposal_revision,
                )
            )
            if revision is None:
                continue
            cut = next(
                (item for item in revision.proposal.get("cuts", []) if item.get("shotId") == shot_id), None
            )
            if not isinstance(cut, dict):
                continue
            head = session.get(ProductionBridgeHeadRow, project_id)
            current = bool(
                head is not None and head.status == "accepted"
                and head.revision == admission.proposal_revision
                and admission.proposal_content_hash == revision.content_hash
            )
            if current:
                for stage, expected_revision in admission.installed_stage_revisions.items():
                    stage_head = self._access.rows.stage(session, project_id, StageName(stage))
                    if stage_head.revision != expected_revision or stage_head.status != StageStatus.READY.value:
                        current = False
                        break
            if current and self._bridge is not None:
                current = not self._bridge._current(session, project_id, admission.inputs)
            if not current:
                raise InvalidTransitionError("bridge source-cut provenance is stale")
            seconds = cut.get("seconds")
            if not isinstance(seconds, int) or seconds * 1_000 != duration_units:
                raise InvalidTransitionError("bridge source-cut duration differs from canonical shot")
            return {
                "kind": "f5_bridge", "admissionId": admission.id,
                "proposalRevision": revision.revision, "proposalContentHash": revision.content_hash,
                "cut": cut, "cutHash": stable_hash(cut),
                "durationUnits": duration_units,
                "installedStageRevisions": dict(admission.installed_stage_revisions),
            }
        storyboard_head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
        if storyboard_head.status != StageStatus.READY.value:
            raise InvalidTransitionError("canonical Storyboard is not current for video timing")
        return {
            "kind": "canonical", "shotId": shot_id,
            "storyboardRevision": storyboard_head.revision,
            "durationUnits": duration_units,
        }

    def binding_is_current(
        self, session: Session, project_id: str, shot_id: str,
        duration_units: int, frozen: object,
    ) -> bool:
        if not isinstance(frozen, dict):
            return False
        try:
            return self.binding_in_session(session, project_id, shot_id, duration_units) == frozen
        except (InvalidTransitionError, KeyError, TypeError, ValueError):
            return False
