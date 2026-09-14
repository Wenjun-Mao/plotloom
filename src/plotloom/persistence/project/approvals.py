from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...domain import (
    STAGE_ORDER, AuthoringDraft, AuthoringDraftScope, DialogueTimingProfile,
    EntityRevision, GateEvaluation, GateEvidence, GateResult, InitialStage,
    LatestRunSummary, Project, ProjectBrief, ProjectCreation, ProjectDuplicateResult,
    ProjectLifecycleStatus, ProjectSummary, StageEnvelope, StageHead, StageName,
    StagePayload, StageStatus, downstream_stages, new_id, stage_payload_model,
    utc_now, upstream_stages, validate_initial_stage_prefix,
)
from ...exceptions import (
    IdempotencyConflictError, InvalidTransitionError, NotFoundError, ProjectBusyError,
    ProjectManagedAssetsPresentError, RevisionConflictError, SchemaResetRequiredError,
    StagePrerequisiteError,
)
from ...validation import STORYBOARD_GATE_SET_VERSION, validate_stage_payload
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ApprovalDecisionRow, AuthoringDraftRow, EntityRevisionRow, GateResultRow,
    GenerationRunRow, GenerationWorkUnitRow, ManagedAssetRow, MediaTaskRow,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectRow,
    StageHeadRow,
)
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from .access import ProjectPersistenceAccess

@dataclass(frozen=True)
class ApprovalDecision:
    """A read projection of one immutable human decision in the approval ledger."""

    id: str
    project_id: str
    entity_revision_id: str
    subject_type: str
    subject_id: str
    subject_revision: int
    content_hash: str
    canonical_input_revisions: tuple[tuple[StageName, int], ...]
    gate_set_version: str
    decision: str
    reviewer: str
    note: str | None
    created_at: datetime


@dataclass(frozen=True)
class ApprovalClosure:
    """Derived current applicability of an append-only approval decision."""

    decision: ApprovalDecision
    active: bool
    stale_reasons: tuple[str, ...]


class ProjectApprovalPersistence:
    """Typed project persistence collaborator; the facade owns compatibility only."""

    def __init__(self, access: ProjectPersistenceAccess) -> None:
        self._access = access

    def append_approval_decision(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        decision: str,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
        subject_type: str = "storyboard",
        subject_id: str = "storyboard",
    ) -> ApprovalDecision:
        """Append (never update) an approval or revocation over an exact board."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            revision = session.get(EntityRevisionRow, entity_revision_id)
            if revision is None or revision.project_id != project_id:
                raise NotFoundError(f"entity revision not found: {entity_revision_id}")
            return self._append_approval_decision_in_session(
                session,
                project_id,
                revision,
                decision=decision,
                reviewer=reviewer,
                gate_set_version=gate_set_version,
                note=note,
                subject_type=subject_type,
                subject_id=subject_id,
            )

    def decide_storyboard_approval(
        self,
        project_id: str,
        *,
        expected_revision: int,
        expected_content_hash: str,
        decision: str,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        """Append a decision only if the exact current storyboard still matches."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
            if head.revision != expected_revision:
                raise RevisionConflictError(
                    "stage:storyboard", expected_revision, head.revision
                )
            if (
                head.status != StageStatus.READY.value
                or head.entity_revision_id is None
                or head.content_hash is None
            ):
                raise InvalidTransitionError(
                    "only the current READY storyboard can receive a review decision"
                )
            if head.content_hash != expected_content_hash:
                raise InvalidTransitionError(
                    "storyboard content hash no longer matches the reviewed content"
                )
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None:
                raise NotFoundError(
                    f"entity revision not found: {head.entity_revision_id}"
                )
            return self._append_approval_decision_in_session(
                session,
                project_id,
                revision,
                decision=decision,
                reviewer=reviewer,
                gate_set_version=gate_set_version,
                note=note,
                subject_type="storyboard",
                subject_id="storyboard",
            )

    def _append_approval_decision_in_session(
        self,
        session: Session,
        project_id: str,
        revision: EntityRevisionRow,
        *,
        decision: str,
        reviewer: str,
        gate_set_version: str,
        note: str | None,
        subject_type: str,
        subject_id: str,
    ) -> ApprovalDecision:
        normalized_decision = decision.strip().lower()
        normalized_reviewer = reviewer.strip()
        normalized_gate_set_version = gate_set_version.strip()
        if normalized_decision not in {"approve", "revoke"}:
            raise ValueError("approval decision must be approve or revoke")
        if not normalized_reviewer or not normalized_gate_set_version:
            raise ValueError("reviewer and gate_set_version must not be blank")
        if normalized_gate_set_version != STORYBOARD_GATE_SET_VERSION:
            raise InvalidTransitionError(
                "approval requires the current canonical storyboard gate set"
            )
        if subject_type != "storyboard" or subject_id != "storyboard":
            raise InvalidTransitionError(
                "only the canonical storyboard subject is approval-eligible"
            )
        if revision.project_id != project_id:
            raise NotFoundError(f"entity revision not found: {revision.id}")
        if revision.stage != StageName.STORYBOARD.value:
            raise InvalidTransitionError(
                "approval decisions can only bind storyboard revisions"
            )
        if revision.schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(
                stage=StageName.STORYBOARD, schema_version=revision.schema_version
            )
        head = self._access.rows.stage(session, project_id, StageName.STORYBOARD)
        if (
            head.status != StageStatus.READY.value
            or head.entity_revision_id != revision.id
            or head.revision != revision.revision
            or head.content_hash != revision.content_hash
        ):
            raise InvalidTransitionError(
                "approval decisions can only bind the current READY storyboard"
            )

        latest = session.scalar(
            select(ApprovalDecisionRow)
            .where(
                ApprovalDecisionRow.entity_revision_id == revision.id,
                ApprovalDecisionRow.subject_type == subject_type,
                ApprovalDecisionRow.subject_id == subject_id,
            )
            .order_by(
                ApprovalDecisionRow.created_at.desc(),
                ApprovalDecisionRow.id.desc(),
            )
            .limit(1)
        )
        if latest is not None and latest.decision == normalized_decision:
            raise InvalidTransitionError(
                f"storyboard revision is already {normalized_decision}d"
            )
        if normalized_decision == "revoke" and (
            latest is None or latest.decision != "approve"
        ):
            raise InvalidTransitionError(
                "only an active approval for this storyboard revision can be revoked"
            )

        gates = session.scalars(
            select(GateResultRow).where(
                GateResultRow.entity_revision_id == revision.id,
                GateResultRow.gate_set_version == normalized_gate_set_version,
            )
        ).all()
        if normalized_decision == "approve":
            if not gates:
                raise InvalidTransitionError(
                    "approval requires a recorded gate evaluation"
                )
            if any(
                gate.content_hash != revision.content_hash
                or gate.revision != revision.revision
                or not self._access.codecs.gate_result(gate).passed
                for gate in gates
            ):
                raise InvalidTransitionError(
                    "approval requires all required gates to pass for the exact revision"
                )

        row = ApprovalDecisionRow(
            id=new_id(),
            project_id=project_id,
            entity_revision_id=revision.id,
            subject_type=subject_type,
            subject_id=subject_id,
            subject_revision=revision.revision,
            content_hash=revision.content_hash,
            canonical_input_revisions=dict(revision.input_revisions),
            gate_set_version=normalized_gate_set_version,
            decision=normalized_decision,
            reviewer=normalized_reviewer,
            note=note,
            created_at=utc_now(),
        )
        session.add(row)
        return self._access.codecs.approval_decision(row)

    def approve_storyboard(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        return self.append_approval_decision(
            project_id,
            entity_revision_id,
            decision="approve",
            reviewer=reviewer,
            gate_set_version=gate_set_version,
            note=note,
        )

    def revoke_storyboard_approval(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        return self.append_approval_decision(
            project_id,
            entity_revision_id,
            decision="revoke",
            reviewer=reviewer,
            gate_set_version=gate_set_version,
            note=note,
        )

    def list_approval_decisions(self, project_id: str) -> list[ApprovalDecision]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(ApprovalDecisionRow)
                .where(ApprovalDecisionRow.project_id == project_id)
                .order_by(ApprovalDecisionRow.created_at, ApprovalDecisionRow.id)
            ).all()
            return [self._access.codecs.approval_decision(row) for row in rows]

    def get_approval_closure(self, decision_id: str) -> ApprovalClosure:
        """Derive applicability from immutable decisions and the current closure."""

        with self._access.leases.read() as session:
            row = session.get(ApprovalDecisionRow, decision_id)
            if row is None:
                raise NotFoundError(f"approval decision not found: {decision_id}")
            decision = self._access.codecs.approval_decision(row)
            reasons: list[str] = []
            if row.decision != "approve":
                reasons.append("decision is a revocation")
            latest = session.scalar(
                select(ApprovalDecisionRow)
                .where(
                    ApprovalDecisionRow.entity_revision_id == row.entity_revision_id,
                    ApprovalDecisionRow.subject_type == row.subject_type,
                    ApprovalDecisionRow.subject_id == row.subject_id,
                )
                .order_by(ApprovalDecisionRow.created_at.desc(), ApprovalDecisionRow.id.desc())
                .limit(1)
            )
            if latest is None or latest.id != row.id:
                reasons.append("superseded or revoked by a later decision")
            revision = session.get(EntityRevisionRow, row.entity_revision_id)
            if revision is None:
                reasons.append("approved revision is unavailable")
            else:
                head = self._access.rows.stage(session, row.project_id, StageName.STORYBOARD)
                if (
                    head.status != StageStatus.READY.value
                    or head.entity_revision_id != row.entity_revision_id
                    or head.content_hash != row.content_hash
                    or revision.revision != row.subject_revision
                    or revision.content_hash != row.content_hash
                ):
                    reasons.append("storyboard head no longer matches the approved revision")
                for stage, expected_revision in row.canonical_input_revisions.items():
                    upstream = self._access.rows.stage(session, row.project_id, StageName(stage))
                    if upstream.status != StageStatus.READY.value or upstream.revision != expected_revision:
                        reasons.append(f"upstream {stage} revision changed")
                gates = session.scalars(
                    select(GateResultRow).where(
                        GateResultRow.entity_revision_id == row.entity_revision_id,
                        GateResultRow.gate_set_version == row.gate_set_version,
                    )
                ).all()
                if (
                    not gates
                    or any(not self._access.codecs.gate_result(gate).passed for gate in gates)
                ):
                    reasons.append("required gate results are absent or no longer passing")
            return ApprovalClosure(decision=decision, active=not reasons, stale_reasons=tuple(reasons))

    def approval_is_revoked(self, decision_id: str) -> bool:
        """Return whether the exact approved revision was subsequently revoked.

        A preview remains an immutable historical projection after revocation,
        but consumers need to distinguish that explicit human decision from an
        ordinary stale canonical head.
        """

        with self._access.leases.read() as session:
            decision = session.get(ApprovalDecisionRow, decision_id)
            if decision is None:
                raise NotFoundError(f"approval decision not found: {decision_id}")
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
            return latest is not None and latest.decision == "revoke"
