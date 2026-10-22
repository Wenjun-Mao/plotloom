"""Project-owned reservation and receipt-only reconciliation for serial CLI jobs."""
from .autopilot_contracts import OperationScope
from .autopilot_exec_reservation import (
    assert_prepared_attempt,
    new_reserved_attempt,
    prepared_exec_inputs,
)
from .codex_exec_attempt_contracts import ATTEMPT_OBSERVED_FIELDS
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError

_RECONCILED_FIELDS = ATTEMPT_OBSERVED_FIELDS


def cancel_codex_exec(store, registry, run_id, checkpoint):
    """Cancel one persisted attempt using its complete immutable identity."""
    evidence = checkpoint["evidence"]
    attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
        run_id, checkpoint["operationKey"]
    )
    if attempt is None or str(attempt.attempt_id) != str(evidence.get("executorAttemptId")):
        raise InvalidTransitionError("checkpoint and persisted Codex Exec attempt identities differ")
    host_status = registry.codex_exec_cancel(attempt)
    if host_status.state == "not_found" or host_status.attempt is None:
        raise InvalidTransitionError("Mac supervisor did not retain the exact cancelled Codex Exec attempt")
    if _identity(host_status.attempt) != _identity(attempt):
        raise InvalidTransitionError("Mac supervisor cancellation returned a different Codex Exec attempt")
    return host_status


def suspend_pending_codex_exec(store, registry, view):
    """Acknowledge pause only after every retained unstarted identity is fenced."""
    if view.policy.executor_binding is None or view.policy.executor_binding.contract_version != "plotloom.codex-exec.v8":
        return
    for checkpoint in view.checkpoints:
        if checkpoint["evidence"].get("executorAttemptId") is None:
            continue
        attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
        if attempt is None:
            raise InvalidTransitionError("pause checkpoint has no retained Codex Exec identity")
        # Losing admission acknowledgment makes the project UNKNOWN even when
        # the exact host still has an enabled, unstarted intent. Only its typed
        # suspend owner can distinguish that from running or unknown host work.
        if attempt.state in {"spawn_intent", "queued", "outcome_unknown"}:
            status = registry.codex_exec_suspend(attempt)
            if status.attempt is None or _identity(status.attempt) != _identity(attempt):
                raise InvalidTransitionError("pause was not acknowledged for the exact retained job")
            if status.state in {"queued", "spawn_intent"} and status.dispatch_enabled is not False:
                raise InvalidTransitionError("pause did not fence unstarted host dispatch")


def reconcile_codex_exec(
    store,
    registry,
    view,
    claim,
    checkpoint,
    *,
    domain: str,
    package_path: str,
    command_factory,
    allow_admission: bool = True,
    before_spawn=None,
    operation_scope: OperationScope | None = None,
    on_settlement=None,
):
    """Reserve one exact package, dispatch its immutable ID once, and poll only that ID."""
    inputs = prepared_exec_inputs(registry, view, checkpoint, domain=domain, package_path=package_path,
                                  allow_admission=allow_admission)
    evidence, profile, _package_hash, _validation_hash = inputs
    operation_key = checkpoint["operationKey"]
    machine_scope = operation_scope or (OperationScope.IMAGE if domain == "image" else OperationScope.TEXT)
    attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, operation_key)

    if attempt is None:
        if not allow_admission:
            return None, None, profile
        if evidence.executor_attempt_id is not None:
            raise InvalidTransitionError("checkpoint names a CLI attempt absent from the project store")
        registry.require_codex_exec_readiness()
        reserved = new_reserved_attempt(view, checkpoint, domain, inputs)
        with command_factory(store, view, claim, machine_scope):
            attempt = store.repository.autopilot.reserve_exec_attempt(
                reserved, expected_checkpoint_revision=checkpoint["revision"]
            )
            if before_spawn is not None:
                before_spawn()
            current_checkpoint = _current_checkpoint(store, view.project_id, operation_key)
            attempt = store.repository.autopilot.mark_exec_spawn_intent(
                attempt.attempt_id, expected_checkpoint_revision=current_checkpoint["revision"]
            )
        host_status = registry.codex_exec_admit(attempt)
    else:
        assert_prepared_attempt(attempt, view, checkpoint, domain, inputs)
        if attempt.state == "reserved":
            if not allow_admission:
                return attempt, receipt, profile
            registry.require_codex_exec_readiness()
            current_checkpoint = _current_checkpoint(store, view.project_id, operation_key)
            with command_factory(store, view, claim, machine_scope):
                if before_spawn is not None:
                    before_spawn()
                attempt = store.repository.autopilot.mark_exec_spawn_intent(
                    attempt.attempt_id, expected_checkpoint_revision=current_checkpoint["revision"]
                )
            host_status = registry.codex_exec_admit(attempt)
        else:
            if not allow_admission and attempt.state in {"queued", "spawn_intent"} and profile.contract_version == "plotloom.codex-exec.v8":
                host_status = registry.codex_exec_suspend(attempt)
            else:
                host_status = registry.codex_exec_status(attempt.attempt_id)
            if allow_admission and host_status.dispatch_enabled is False:
                # Keep the project command fence across exact queue resume.
                # A concurrent pause cannot acknowledge before this grant,
                # then lose to an already stale controller authorization.
                with command_factory(store, view, claim, machine_scope):
                    host_status = registry.codex_exec_resume(attempt)
            # A host admission is durable before process start and idempotent by
            # attempt ID. Reconcile an absent record only with the same frozen
            # spawn-intent snapshot; never construct a replacement attempt.
            if allow_admission and host_status.state == "not_found" and attempt.state == "spawn_intent":
                host_status = registry.codex_exec_admit(attempt)

    return settle_exec_status(store, view, claim, attempt, receipt, profile, host_status,
        command_factory=command_factory, allow_admission=allow_admission,
        machine_scope=machine_scope, on_settlement=on_settlement)


def settle_exec_status(store, view, claim, attempt, receipt, profile, host_status, *,
        command_factory, allow_admission=False, machine_scope=None, on_settlement=None):
    """Persist only typed host facts; no dispatch or creative adoption here."""
    operation_key = attempt.operation_key
    host_attempt = host_status.attempt
    if host_status.state == "not_found":
        if host_status.capacity_deferred:
            raise ImageJobError("codex_exec_capacity_deferred", "Codex Exec capacity is full; the original job is waiting for a known admission slot.")
        return attempt, receipt, profile
    if host_attempt is None:
        raise InvalidTransitionError("Mac supervisor status omitted its typed attempt snapshot")
    if _identity(host_attempt) != _identity(attempt):
        raise InvalidTransitionError("Mac supervisor returned a different frozen CLI attempt")
    if host_status.capacity_deferred:
        raise ImageJobError("codex_exec_capacity_deferred", "Codex Exec capacity is full; the original job is waiting for a known admission slot.")
    if (allow_admission and host_status.state != "outcome_unknown" and view.blocker
            and view.blocker.get("code") == "codex_exec_capacity_deferred"):
        # An exact admission acknowledgement resolves this capacity wait. The
        # phase stays unchanged; no receipt or creative adoption is implied.
        with command_factory(store, view, claim, machine_scope):
            store.repository.autopilot.progress(view.phase)
    changes = {field: getattr(host_attempt, field) for field in _RECONCILED_FIELDS}
    terminal_callback = on_settlement is not None and host_attempt.state in {"completed", "failed", "settled"}
    if changes != {field: getattr(attempt, field) for field in _RECONCILED_FIELDS} or host_status.receipt != receipt or terminal_callback:
        with command_factory(store, view, claim, OperationScope.EVIDENCE):
            updated = store.repository.autopilot.update_exec_attempt(
                attempt.attempt_id,
                receipt=host_status.receipt,
                **changes,
            )
            if terminal_callback:
                on_settlement(updated)
        attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, operation_key)
    return attempt, receipt, profile


def _identity(attempt):
    return (
        attempt.attempt_id, attempt.run_id, attempt.project_id, attempt.job_id,
        attempt.operation_key, attempt.domain, attempt.request_hash,
        attempt.package_hash, attempt.profile_hash, attempt.plotloom_code_revision,
        attempt.validation_plan_hash, attempt.reserved_image_outputs,
    )


def _current_checkpoint(store, run_id, operation_key):
    current = store.repository.autopilot.current(run_id)
    checkpoint = next((item for item in current.checkpoints if item["operationKey"] == operation_key), None)
    if checkpoint is None:
        raise InvalidTransitionError("reserved CLI attempt lost its stage checkpoint")
    return checkpoint
