from __future__ import annotations

from plotloom.api.contracts import ApprovalClosureView, ApprovalDecisionView
from plotloom.persistence import ApprovalClosure, ApprovalDecision


def _approval_decision_view(decision: ApprovalDecision) -> ApprovalDecisionView:
    from ..delegated_qa import attribution_for_reviewer

    return ApprovalDecisionView(
        id=decision.id,
        project_id=decision.project_id,
        entity_revision_id=decision.entity_revision_id,
        subject_type=decision.subject_type,
        subject_id=decision.subject_id,
        subject_revision=decision.subject_revision,
        content_hash=decision.content_hash,
        canonical_input_revisions=dict(decision.canonical_input_revisions),
        gate_set_version=decision.gate_set_version,
        decision=decision.decision,
        reviewer=decision.reviewer,
        attribution=attribution_for_reviewer(decision.project_id, decision.reviewer)
        or ({"kind": "unnamed_creator"} if decision.reviewer == "" else None),
        note=decision.note,
        created_at=decision.created_at,
    )


def _approval_closure_view(closure: ApprovalClosure) -> ApprovalClosureView:
    return ApprovalClosureView(
        decision=_approval_decision_view(closure.decision),
        active=closure.active,
        stale_reasons=list(closure.stale_reasons),
    )
