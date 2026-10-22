"""Explicit image-only authority union; human admission remains separate."""
from dataclasses import dataclass

from ...autopilot_contracts import OperationScope
from ...exceptions import InvalidTransitionError
from ...validation import STORYBOARD_GATE_SET_VERSION
from .autopilot_authority import machine_image_authority, require_machine_scope


@dataclass(frozen=True)
class ImageAuthorityBinding:
    approval_id: str | None
    machine_decision_id: str | None
    project_id: str
    entity_revision_id: str
    subject_revision: int
    gate_set_version: str
    canonical_input_revisions: dict

    @property
    def id(self):
        if self.approval_id is None:
            raise InvalidTransitionError("machine image authority is not a human approval")
        return self.approval_id


def resolve_image_authority(session, access, admission, project_id, *, approval_id, machine_decision_id, preparing=False):
    if (approval_id is None) == (machine_decision_id is None):
        raise InvalidTransitionError("image unit needs exactly one human or machine authority")
    if machine_decision_id is not None:
        if preparing:
            authority = require_machine_scope(access, OperationScope.IMAGE)
        decision, revision = machine_image_authority(session, access, project_id, machine_decision_id)
        if preparing and decision.run_id != authority.run_id:
            raise InvalidTransitionError("image decision belongs to another run")
        return ImageAuthorityBinding(None, decision.id, project_id, revision.id, revision.revision,
            STORYBOARD_GATE_SET_VERSION, dict(revision.input_revisions))
    if access.authority() is not None and preparing:
        raise InvalidTransitionError("machine image commands cannot borrow a human approval")
    approval = admission.approval_is_active_in_session(session, approval_id)
    return ImageAuthorityBinding(approval.id, None, approval.project_id, approval.entity_revision_id,
        approval.subject_revision, approval.gate_set_version, dict(approval.canonical_input_revisions))
