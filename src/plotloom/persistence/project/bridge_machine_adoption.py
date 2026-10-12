"""Exact machine bridge adoption requires a native job and scoped decision."""
from sqlalchemy import select
from ...autopilot_contracts import MachineDecision, OperationScope
from ...exceptions import InvalidTransitionError
from ...machine_adoption import MachineAdoption
from ..schema import AutopilotDecisionRow, AutopilotRunRow, ProductionBridgeRevisionRow
from .autopilot_authority import require_machine_scope


def bridge_adoption(session, access, project_id, decision_id, owner, revision, digest):
    authority = require_machine_scope(access, OperationScope.INSTALL)
    decision = session.get(AutopilotDecisionRow, decision_id)
    if (decision is None or decision.run_id != authority.run_id or decision.project_id != project_id
            or decision.scope != OperationScope.INSTALL.value):
        raise InvalidTransitionError("bridge adoption decision differs from this run")
    run = session.get(AutopilotRunRow, decision.run_id)
    facts = MachineDecision.model_validate(decision.decision)
    if (facts.policy_hash != run.policy_hash or facts.subject != {"proposalRevision": revision, "proposalHash": digest}
            or facts.evidence.owner != owner or not facts.evidence.delivery_hash):
        raise InvalidTransitionError("bridge decision differs from exact native proposal/delivery")
    return MachineAdoption(run_id=run.id, decision_id=decision.id, policy_hash=run.policy_hash,
        proposal_revision=revision, proposal_hash=digest, job_id=facts.evidence.job_id,
        request_hash=facts.evidence.request_hash, delivery_hash=facts.evidence.delivery_hash)


def assert_bridge_adoption(session, access, project_id, adoption, owner):
    row = session.scalar(select(ProductionBridgeRevisionRow).where(
        ProductionBridgeRevisionRow.project_id == project_id, ProductionBridgeRevisionRow.revision == adoption.proposal_revision))
    if row is None or row.content_hash != adoption.proposal_hash:
        raise InvalidTransitionError("retained machine bridge proposal is unavailable")
    expected = bridge_adoption(session, access, project_id, adoption.decision_id, owner, row.revision, row.content_hash)
    if expected != adoption:
        raise InvalidTransitionError("machine bridge adoption provenance changed")
