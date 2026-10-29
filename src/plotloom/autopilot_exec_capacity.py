"""One consumable, exact-attempt grant from an authenticated capacity refusal."""
import hashlib
import json

from .autopilot_contracts import CheckpointEvidence, ExecutorAdmissionDeferral
from .exceptions import InvalidTransitionError


def admission_identity_hash(attempt):
    fields = ("attemptId", "runId", "projectId", "jobId", "operationKey", "domain",
              "requestHash", "packageHash", "profileHash", "plotloomCodeRevision",
              "validationPlanHash", "reservedImageOutputs")
    data = attempt.model_dump(mode="json", by_alias=True)
    return hashlib.sha256(json.dumps({key: data.get(key) for key in fields},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def assert_admission_deferral(attempt, deferral):
    if (attempt.state != "spawn_intent" or deferral.attempt_id != attempt.attempt_id
            or deferral.identity_hash != admission_identity_hash(attempt)):
        raise InvalidTransitionError("capacity deferral differs from the exact unacknowledged attempt")


def change_admission_deferral(store, view, attempt, *, consume):
    """Caller holds the applicable project command; checkpoint CAS spends first."""
    current = store.repository.autopilot.current(view.project_id)
    checkpoint = next(item for item in current.checkpoints if item["operationKey"] == attempt.operation_key)
    evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
    retained, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, attempt.operation_key)
    if retained != attempt or receipt is not None or attempt.state != "spawn_intent":
        raise InvalidTransitionError("capacity admission grant requires the current unacknowledged attempt")
    if consume:
        if evidence.executor_admission_deferral is None:
            return False
        assert_admission_deferral(attempt, evidence.executor_admission_deferral)
        deferral = None
    else:
        deferral = ExecutorAdmissionDeferral(attempt_id=attempt.attempt_id,
            identity_hash=admission_identity_hash(attempt))
    store.repository.autopilot.checkpoint(attempt.operation_key, state=checkpoint["state"],
        expected_revision=checkpoint["revision"],
        evidence=evidence.model_copy(update={"executor_admission_deferral": deferral}))
    return True
