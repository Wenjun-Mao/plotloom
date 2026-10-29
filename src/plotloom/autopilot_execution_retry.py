"""Current physical job selection and bounded native execution retries."""
from __future__ import annotations

from .autopilot_contracts import CheckpointEvidence, OperationScope
from .generation_retry_policy import repeatable_failure


def retry_root(key):
    return key.rsplit(":retry:", 1)[0] if ":retry:" in key else key


def retry_ordinal(checkpoint):
    return checkpoint["evidence"]["result"].get("executionRetry", {}).get("ordinal", 0)


def current_checkpoint(view, key):
    root = retry_root(key)
    return max((c for c in view.checkpoints if retry_root(c["operationKey"]) == root),
               key=retry_ordinal, default=None)


def retry_native_execution(controller, store, view, claim, checkpoint, attempt):
    """Never spins or repeats an ID; one durable successor per stopped parent."""
    limit = view.policy.automatic_retry_limit
    if limit is None or not repeatable_failure(attempt):
        return False
    status = controller.registry.codex_exec_status(attempt.attempt_id)
    if status.attempt != attempt or not status.local_execution_stopped:
        return True  # Keep observing this exact local owner; no successor yet.
    active = store.repository.autopilot.current(view.project_id)
    if active.id != view.id or active.policy != view.policy or active.state not in {"running","waiting"} or not active.material_current:
        return True
    checkpoint = next(c for c in active.checkpoints if c["operationKey"] == checkpoint["operationKey"])
    if current_checkpoint(active,checkpoint["operationKey"]) != checkpoint:
        return True
    view = active
    evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
    if evidence.result.get("executionRetry", {}).get("automaticRetriesUsed", retry_ordinal(checkpoint)) >= limit:
        if not evidence.result.get("executionRetryExhausted"):
            with controller.command(store, view, claim, OperationScope.EVIDENCE):
                store.repository.autopilot.checkpoint(checkpoint["operationKey"], state=checkpoint["state"],
                    expected_revision=checkpoint["revision"],
                    evidence=evidence.model_copy(update={"result": evidence.result | {"executionRetryExhausted": True}}))
        return True
    scope = OperationScope.IMAGE if attempt.domain == "image" else OperationScope.TEXT
    if evidence.owner.startswith("bridge-"):
        scope = OperationScope.INSTALL
    with controller.command(store, view, claim, scope):
        from .autopilot_launch import assert_frozen_execution
        assert_frozen_execution(store, controller.registry, view.policy)
        store.repository.autopilot.prepare_execution_retry(checkpoint["operationKey"], attempt)
    return True
