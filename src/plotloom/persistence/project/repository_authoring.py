"""Explicit authoring and approval operations for a bound project."""

from __future__ import annotations

from typing import Any

from ...domain import AuthoringDraftScope, ProjectBrief, StageName


class ProjectAuthoringRepository:
    def __init__(self, root: Any) -> None:
        self._root = root

    def get_project(self, project_id: str):
        return self._root._catalog.get_project(project_id)

    def list_stage_heads(self, project_id: str):
        return self._root._gates.list_stage_heads(project_id)

    def list_stage_envelopes(self, project_id: str):
        return self._root._gates.list_stage_envelopes(project_id)

    def get_stage_head(self, project_id: str, stage: StageName):
        return self._root._gates.get_stage_head(project_id, stage)

    def update_project(self, project_id: str, expected_revision: int, brief: ProjectBrief):
        return self._root._drafts.update_project(project_id, expected_revision, brief)

    def update_project_consuming_authoring_draft(self, project_id: str, expected_revision: int, brief: ProjectBrief, *, entity_id: str, expected_draft_revision: int):
        return self._root._drafts.update_project_consuming_authoring_draft(project_id, expected_revision, brief, entity_id=entity_id, expected_draft_revision=expected_draft_revision)

    def update_stage(self, project_id: str, stage: StageName, expected_revision: int, payload: Any):
        return self._root._canonical.update_stage(project_id, stage, expected_revision, payload)

    def update_stage_consuming_authoring_draft(self, project_id: str, stage: StageName, expected_revision: int, payload: Any, *, entity_id: str, expected_draft_revision: int):
        return self._root._workflow.update_stage_consuming_authoring_draft(project_id, stage, expected_revision, payload, entity_id=entity_id, expected_draft_revision=expected_draft_revision)

    def list_authoring_drafts(self, project_id: str):
        return self._root._drafts.list_authoring_drafts(project_id)

    def upsert_authoring_draft(self, project_id: str, *, editor_scope: AuthoringDraftScope, entity_id: str, base_canonical_revision: int, expected_draft_revision: int, payload: dict[str, Any]):
        return self._root._drafts.upsert_authoring_draft(project_id, editor_scope=editor_scope, entity_id=entity_id, base_canonical_revision=base_canonical_revision, expected_draft_revision=expected_draft_revision, payload=payload)

    def discard_authoring_draft(self, project_id: str, *, editor_scope: AuthoringDraftScope, entity_id: str, expected_draft_revision: int):
        return self._root._drafts.discard_authoring_draft(project_id, editor_scope=editor_scope, entity_id=entity_id, expected_draft_revision=expected_draft_revision)

    def get_stage_payload(self, project_id: str, stage: StageName):
        return self._root._canonical.get_stage_payload(project_id, stage)

    def get_gate_evaluation(self, entity_revision_id: str, gate_set_version: str):
        return self._root._gates.get_gate_evaluation(entity_revision_id, gate_set_version)

    def decide_storyboard_approval(self, project_id: str, *, expected_revision: int, expected_content_hash: str, decision: str, reviewer: str, gate_set_version: str, note: str | None = None):
        return self._root._approvals.decide_storyboard_approval(project_id, expected_revision=expected_revision, expected_content_hash=expected_content_hash, decision=decision, reviewer=reviewer, gate_set_version=gate_set_version, note=note)

    def get_approval_closure(self, decision_id: str):
        return self._root._approvals.get_approval_closure(decision_id)

    def list_approval_decisions(self, project_id: str):
        return self._root._approvals.list_approval_decisions(project_id)

    def approval_is_revoked(self, decision_id: str) -> bool:
        return self._root._approvals.approval_is_revoked(decision_id)
