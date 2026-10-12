"""Shared domain scope admission; machine authority never resolves as approval."""
from sqlalchemy import select

from ...autopilot_contracts import MachineDecision, OperationScope
from ...domain import StageName, StageStatus
from ...exceptions import InvalidTransitionError
from ..schema import AutopilotDecisionRow, AutopilotRunRow, EntityRevisionRow, GateResultRow
from .autopilot_closure import material_closure, production_closure


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
    gates = session.scalars(select(GateResultRow).where(GateResultRow.entity_revision_id == revision.id)).all()
    if not gates or any(gate.content_hash != revision.content_hash or not access.codecs.gate_result(gate).passed for gate in gates):
        raise InvalidTransitionError("machine image requires the current passing canonical gates")
    return decision, revision


def video_eligible(session, project_id):
    run = session.scalar(select(AutopilotRunRow).where(AutopilotRunRow.project_id == project_id))
    if run is None:
        return True
    return (run.state == "handed_off" and isinstance(run.handoff, dict)
            and run.handoff.get("materialClosure") == material_closure(session, project_id)
            and run.handoff.get("bundleHash") == run.bundle_hash)


def require_video_authority(access, project_id):
    if access.authority() is not None:
        raise InvalidTransitionError("pre-video commands cannot prepare, preview or dispatch videos")
    with access.leases.read() as session:
        if not video_eligible(session, project_id):
            raise InvalidTransitionError("video requires a current exact human material handoff")
