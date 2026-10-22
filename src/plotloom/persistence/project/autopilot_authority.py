"""Shared domain scope admission; machine authority never resolves as approval."""
from sqlalchemy import select

from ...autopilot_contracts import MachineDecision, OperationScope
from ...domain import StageName, StageStatus
from ...exceptions import InvalidTransitionError
from ..schema import AutopilotDecisionRow, AutopilotRunRow, AutopilotHandoffRow, EntityRevisionRow, GateResultRow
from .autopilot_closure import material_closure, production_closure
from .autopilot_lineage import current_run_row


def require_machine_scope(access, scope):
    authority = access.authority()
    if authority is None or authority.scope != scope or scope == OperationScope.HANDOFF:
        raise InvalidTransitionError("operation requires exact trusted pre-video machine authority")
    return authority


def allow_manual_or_machine(access, scope):
    if access.authority() is not None:
        require_machine_scope(access, scope)


def require_manual_command(access):
    if access.authority() is not None:
        raise InvalidTransitionError("machine commands cannot edit author-owned project material")


def receipt_only(access):
    authority = access.authority()
    return authority is not None and authority.scope == OperationScope.EVIDENCE


def require_human_command(access):
    authority = access.authority()
    if authority is not None and authority.scope != OperationScope.HANDOFF:
        raise InvalidTransitionError("machine commands cannot create human review facts")


def machine_image_authority(session, access, project_id, decision_id):
    decision = session.get(AutopilotDecisionRow, decision_id)
    if decision is None or decision.project_id != project_id or decision.scope != OperationScope.IMAGE.value:
        raise InvalidTransitionError("image authority is not a project-owned image decision")
    facts = MachineDecision.model_validate(decision.decision)
    run = session.get(AutopilotRunRow, decision.run_id)
    if run is None or facts.policy_hash != run.policy_hash:
        raise InvalidTransitionError("image decision policy changed")
    subject = facts.subject
    if subject.get("productionHash") != production_closure(session, project_id):
        raise InvalidTransitionError("machine image production source closure changed")
    head = access.rows.stage(session, project_id, StageName.STORYBOARD)
    revision = session.get(EntityRevisionRow, subject.get("entityRevisionId"))
    if (revision is None or revision.project_id != project_id or head.status != StageStatus.READY.value
            or head.entity_revision_id != revision.id or revision.content_hash != subject.get("contentHash")
            or revision.revision != subject.get("revision") or head.content_hash != revision.content_hash):
        raise InvalidTransitionError("machine image decision canonical closure changed")
    for stage, expected in revision.input_revisions.items():
        upstream = access.rows.stage(session, project_id, StageName(stage))
        if upstream.status != "ready" or upstream.revision != expected:
            raise InvalidTransitionError("machine image upstream changed")
    from .canonical_gate_evidence import gates_pass
    if not gates_pass(session, access.codecs, revision.id, content_hash=revision.content_hash):
        raise InvalidTransitionError("machine image requires the current passing canonical gates")
    return decision, revision


def video_eligible(session, project_id):
    run = current_run_row(session, project_id)
    if run is None:
        return True
    if run.state != "handed_off" or not isinstance(run.handoff, dict):
        return False
    retained = session.get(AutopilotHandoffRow, run.handoff.get("receiptId"))
    if retained is None or retained.run_id != run.id or retained.project_id != project_id or retained.receipt_hash != run.handoff.get("receiptHash"):
        return False
    from ...project_storage.handoff_validation import assert_handoff
    try:
        receipt = assert_handoff(session.connection().connection.driver_connection, retained.id, run.id,
            project_id, retained.approval_id, retained.receipt, retained.receipt_hash)
    except (ValueError, TypeError, KeyError):
        return False
    return (receipt.bundle_hash == run.handoff.get("bundleHash") and receipt.material_closure == run.handoff.get("materialClosure")
        and receipt.material_closure == material_closure(session, project_id))


def require_video_authority(access, project_id):
    if access.authority() is not None:
        raise InvalidTransitionError("pre-video commands cannot prepare, preview or dispatch videos")
    with access.leases.read() as session:
        if not video_eligible(session, project_id):
            raise InvalidTransitionError("video requires a current exact human material handoff")
