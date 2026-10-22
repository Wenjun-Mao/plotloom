"""Explicit reservation, single-use admission and receipt-only observation.

These operations do not run the controller or adopt creative output. Callers
carry known owner revisions across claim/resume; refreshing a stale view is not
an authorization step.
"""
from .autopilot_contracts import OperationScope
from .autopilot_exec import _identity, settle_exec_status
from .autopilot_exec_reservation import (
    assert_prepared_attempt,
    new_reserved_attempt,
    prepared_exec_inputs,
)
from .exceptions import InvalidTransitionError


def reserve_prepared_codex_exec(store, registry, view, claim, checkpoint, *,
        domain, package_path, command_factory, operation_scope=None):
    """Return the actual persisted UUID without spawn intent or host admission."""
    inputs = prepared_exec_inputs(registry, view, checkpoint, domain=domain, package_path=package_path)
    existing = store.repository.autopilot.exec_attempt_for_operation(view.id, checkpoint["operationKey"])
    if existing is not None:
        raise InvalidTransitionError("prepared CLI job already has its initial reservation")
    if inputs[0].executor_attempt_id is not None:
        raise InvalidTransitionError("checkpoint names a missing project CLI reservation")
    reserved = new_reserved_attempt(view, checkpoint, domain, inputs)
    scope = operation_scope or (OperationScope.IMAGE if domain == "image" else OperationScope.TEXT)
    with command_factory(store, view, claim, scope):
        return store.repository.autopilot.reserve_exec_attempt(
            reserved, expected_checkpoint_revision=checkpoint["revision"])


def admit_reserved_codex_exec_once(store, registry, view, claim, checkpoint, *,
        expected_attempt, expected_run_revision, package_path, command_factory,
        operation_scope=None, before_spawn=None):
    """Commit one intent before the sole host call. Lost acknowledgment stays spent."""
    if view.revision != expected_run_revision:
        raise InvalidTransitionError("strict CLI admission requires the expected run view")
    registry.require_codex_exec_readiness()
    scope = operation_scope or (OperationScope.IMAGE if expected_attempt.domain == "image" else OperationScope.TEXT)
    with command_factory(store, view, claim, scope):
        from .autopilot_launch import assert_frozen_execution
        assert_frozen_execution(store, registry, view.policy)
        inputs = prepared_exec_inputs(registry, view, checkpoint,
            domain=expected_attempt.domain, package_path=package_path)
        assert_prepared_attempt(expected_attempt, view, checkpoint, expected_attempt.domain, inputs)
        if (str(expected_attempt.run_id) != str(view.id)
                or str(expected_attempt.project_id) != str(view.project_id)
                or expected_attempt.profile_hash != inputs[1].profile_hash):
            raise InvalidTransitionError("strict CLI attempt differs from its frozen run or profile")
        if before_spawn is not None:
            before_spawn()
        attempt = store.repository.autopilot.consume_reserved_exec_attempt_once(
            expected_attempt, expected_checkpoint_revision=checkpoint["revision"],
            expected_run_revision=expected_run_revision)
    try:
        status = registry.codex_exec_admit(attempt)
    except Exception:
        _hold_unknown(store, view, claim, attempt, command_factory)
        raise
    if status.state == "not_found":
        _hold_unknown(store, view, claim, attempt, command_factory)
        return store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, attempt.operation_key)
    return settle_exec_status(store, view, claim, attempt, None, inputs[1], status,
        command_factory=command_factory)[:2]


def observe_existing_codex_exec(store, registry, view, claim, *, expected_attempt, command_factory):
    """Observe the retained identity; never admit, resume, suspend or create it."""
    attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
        view.id, expected_attempt.operation_key)
    if attempt is None or _identity(attempt) != _identity(expected_attempt):
        raise InvalidTransitionError("observation requires the exact existing project CLI attempt")
    if attempt.state == "reserved":
        return attempt, receipt
    status = registry.codex_exec_status(attempt.attempt_id)
    if status.state == "not_found":
        if attempt.state not in {"completed", "failed", "settled", "outcome_unknown"}:
            _hold_unknown(store, view, claim, attempt, command_factory)
        return store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, attempt.operation_key)
    return settle_exec_status(store, view, claim, attempt, receipt, view.policy.executor_binding,
        status, command_factory=command_factory)[:2]


def _hold_unknown(store, view, claim, attempt, command_factory):
    with command_factory(store, view, claim, OperationScope.EVIDENCE):
        store.repository.autopilot.update_exec_attempt(attempt.attempt_id, state="outcome_unknown")
