"""Explicit authoring and approval operations for a bound project."""

from __future__ import annotations

from typing import Any

from ...domain import (
    AuthoringDraft, AuthoringDraftScope, GateEvaluation, Project, ProjectBrief,
    StageEnvelope, StageHead, StageName, StagePayload,
)
from .approvals import ApprovalClosure, ApprovalDecision, ProjectApprovalPersistence
from .canonical import ProjectCanonicalPersistence
from .catalog import ProjectCatalogPersistence
from .drafts import ProjectDraftPersistence
from .gates import ProjectGatePersistence
from .workflow import ProjectAuthoringWorkflow


class ProjectAuthoringRepository:
    """Public authoring surface with only the owners it routes to."""

    def __init__(
        self,
        *,
        catalog: ProjectCatalogPersistence,
        gates: ProjectGatePersistence,
        drafts: ProjectDraftPersistence,
        canonical: ProjectCanonicalPersistence,
        workflow: ProjectAuthoringWorkflow,
        approvals: ProjectApprovalPersistence,
    ) -> None:
        self._catalog = catalog
        self._gates = gates
        self._drafts = drafts
        self._canonical = canonical
        self._workflow = workflow
        self._approvals = approvals

    def get_project(self, project_id: str) -> Project:
        return self._catalog.get_project(project_id)

    def list_stage_heads(self, project_id: str) -> list[StageHead]:
        return self._gates.list_stage_heads(project_id)

    def list_stage_envelopes(self, project_id: str) -> list[StageEnvelope]:
        return self._gates.list_stage_envelopes(project_id)

    def get_stage_head(self, project_id: str, stage: StageName) -> StageHead:
        return self._gates.get_stage_head(project_id, stage)

    def update_project(self, project_id: str, expected_revision: int, brief: ProjectBrief) -> Project:
        return self._drafts.update_project(project_id, expected_revision, brief)

    def update_project_consuming_authoring_draft(
        self, project_id: str, expected_revision: int, brief: ProjectBrief, *,
        entity_id: str, expected_draft_revision: int,
    ) -> Project:
        return self._drafts.update_project_consuming_authoring_draft(
            project_id, expected_revision, brief, entity_id=entity_id,
            expected_draft_revision=expected_draft_revision,
        )

    def update_stage(
        self, project_id: str, stage: StageName, expected_revision: int,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        return self._canonical.update_stage(project_id, stage, expected_revision, payload)

    def update_stage_consuming_authoring_draft(
        self, project_id: str, stage: StageName, expected_revision: int,
        payload: StagePayload | dict[str, Any], *, entity_id: str,
        expected_draft_revision: int,
    ) -> StageHead:
        return self._workflow.update_stage_consuming_authoring_draft(
            project_id, stage, expected_revision, payload, entity_id=entity_id,
            expected_draft_revision=expected_draft_revision,
        )

    def list_authoring_drafts(self, project_id: str) -> list[AuthoringDraft]:
        return self._drafts.list_authoring_drafts(project_id)

    def upsert_authoring_draft(
        self, project_id: str, *, editor_scope: AuthoringDraftScope, entity_id: str,
        base_canonical_revision: int, expected_draft_revision: int,
        payload: dict[str, Any],
    ) -> AuthoringDraft:
        return self._drafts.upsert_authoring_draft(
            project_id, editor_scope=editor_scope, entity_id=entity_id,
            base_canonical_revision=base_canonical_revision,
            expected_draft_revision=expected_draft_revision, payload=payload,
        )

    def discard_authoring_draft(
        self, project_id: str, *, editor_scope: AuthoringDraftScope, entity_id: str,
        expected_draft_revision: int,
    ) -> bool:
        return self._drafts.discard_authoring_draft(
            project_id, editor_scope=editor_scope, entity_id=entity_id,
            expected_draft_revision=expected_draft_revision,
        )

    def get_stage_payload(self, project_id: str, stage: StageName) -> StagePayload:
        return self._canonical.get_stage_payload(project_id, stage)

    def get_gate_evaluation(
        self, entity_revision_id: str, gate_set_version: str
    ) -> GateEvaluation:
        return self._gates.get_gate_evaluation(entity_revision_id, gate_set_version)

    def decide_storyboard_approval(
        self, project_id: str, *, expected_revision: int,
        expected_content_hash: str, decision: str, reviewer: str,
        gate_set_version: str, note: str | None = None,
    ) -> ApprovalDecision:
        return self._approvals.decide_storyboard_approval(
            project_id, expected_revision=expected_revision,
            expected_content_hash=expected_content_hash, decision=decision,
            reviewer=reviewer, gate_set_version=gate_set_version, note=note,
        )

    def get_approval_closure(self, decision_id: str) -> ApprovalClosure:
        return self._approvals.get_approval_closure(decision_id)

    def list_approval_decisions(self, project_id: str) -> list[ApprovalDecision]:
        return self._approvals.list_approval_decisions(project_id)

    def approval_is_revoked(self, decision_id: str) -> bool:
        return self._approvals.approval_is_revoked(decision_id)
