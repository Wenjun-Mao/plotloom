"""Checkpoint CAS and monotonic reconciliation; uncertainty is never erased."""
from ...autopilot_contracts import CheckpointEvidence
from ...exceptions import InvalidTransitionError, RevisionConflictError

TRANSITIONS = {
    "prepared": {"prepared", "sent", "outcome_unknown", "delivered"},
    "sent": {"sent", "outcome_unknown", "delivered"},
    "outcome_unknown": {"outcome_unknown", "delivered"},
    "delivered": {"delivered", "adopted"},
    "adopted": {"adopted"},
}


def assert_checkpoint_update(checkpoint, expected_revision, state, evidence):
    actual = checkpoint.revision if checkpoint else 0
    if actual != expected_revision:
        raise RevisionConflictError("autopilot checkpoint", expected_revision, actual)
    if state not in TRANSITIONS:
        raise InvalidTransitionError("unknown checkpoint state")
    if checkpoint is None:
        if evidence.job_id and state != "prepared":
            raise InvalidTransitionError("native job checkpoint must start prepared before dispatch")
        return
    previous = CheckpointEvidence.model_validate(checkpoint.evidence)
    if state not in TRANSITIONS[checkpoint.state]:
        raise InvalidTransitionError("checkpoint cannot regress its dispatch state")
    for field in ("owner", "subject_id", "job_id", "request_hash", "execution_pin"):
        if getattr(previous, field) != getattr(evidence, field):
            raise InvalidTransitionError("checkpoint cannot replace its frozen owner/execution identity")
    if previous.delivery_hash is not None and previous.delivery_hash != evidence.delivery_hash:
        raise InvalidTransitionError("checkpoint delivery evidence is immutable")
    if any(evidence.result.get(key) != value for key, value in previous.result.items()):
        raise InvalidTransitionError("checkpoint retained result evidence is immutable")
    if checkpoint.state == "adopted" and checkpoint.evidence != evidence.model_dump(mode="json", by_alias=True):
        raise InvalidTransitionError("adopted checkpoint evidence is immutable")
