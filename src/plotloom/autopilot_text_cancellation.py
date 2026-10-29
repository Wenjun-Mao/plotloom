"""Explicit cancellation may retire publication of an exact known stopped failure."""
from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_identity import request_hash
from .exceptions import InvalidTransitionError


def settle_stopped_bridge_publication(store, view, checkpoint, evidence, status):
    if (view.state not in {"running", "waiting", "paused", "blocked"}
            or checkpoint["state"] != "failed" or not status.local_execution_stopped):
        return False
    attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
    if (attempt is None or attempt != status.attempt or status.state != attempt.state
            or attempt.state not in {"failed", "settled"}
            or attempt.terminal_result not in {"failure", "not_started", "no_remote_dispatch"}
            or receipt is not None or status.receipt is not None):
        return False
    owner = store.repository.production_bridge_intent
    data = owner.load_job(view.project_id, evidence.job_id)
    request = CreativeHandoffRequest.model_validate(data["nativeRequest"])
    if (data["transport"] != "codex_native" or request.stage != evidence.owner
            or request.stage not in {"bridge-intent", "bridge-presentation"}
            or request.job_id != evidence.job_id or attempt.job_id != request.job_id
            or request.project_id != view.project_id or str(attempt.project_id) != view.project_id
            or str(attempt.run_id) != view.id or attempt.operation_key != checkpoint["operationKey"]
            or attempt.attempt_id != evidence.executor_attempt_id
            or request_hash(request) != attempt.request_hash or attempt.request_hash != evidence.request_hash
            or attempt.profile_hash != view.policy.executor_binding.profile_hash
            or attempt.plotloom_code_revision != view.policy.code_revision):
        raise InvalidTransitionError("known bridge failure differs from its exact frozen publication owner")
    owner.finish_failure(view.project_id, request.job_id, status="failed", code="execution.failed",
        message="Exact persisted terminal failure was confirmed locally stopped during explicit cancellation.")
    return True
