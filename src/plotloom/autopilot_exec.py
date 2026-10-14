"""Project-owned reservation and receipt-only reconciliation for serial CLI jobs."""
from pathlib import Path
from uuid import uuid4
import json

from .autopilot_contracts import CheckpointEvidence, OperationScope
from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
)
from .codex_exec_runtime import frozen_package_snapshot
from .exceptions import InvalidTransitionError

_RECONCILED_FIELDS = (
    "state", "session_id", "process_id", "process_group_id", "process_birth_identity",
    "process_exit_code", "terminal_result", "remote_tool_state", "evidence_hash",
    "output_hash", "remote_output_hash", "image_budget_state",
)


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
):
    """Reserve one exact package, dispatch its immutable ID once, and poll only that ID."""
    evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
    profile = CodexExecProfile.model_validate(registry.codex_exec_profile())
    if profile != view.policy.executor_binding:
        raise InvalidTransitionError("Codex Exec profile changed after the launch was frozen.")
    if (profile.contract_version in {"plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7"}
            and not view.policy.code_revision):
        raise InvalidTransitionError("Codex Exec launch omits its frozen Plotloom source revision.")
    if evidence.job_id is None or evidence.request_hash is None:
        raise InvalidTransitionError("prepared CLI checkpoint has no frozen job identity")

    operation_key = checkpoint["operationKey"]
    machine_scope = operation_scope or (OperationScope.IMAGE if domain == "image" else OperationScope.TEXT)
    package_directory = Path(package_path).resolve(strict=True)
    if package_directory.name != "package":
        raise InvalidTransitionError("prepared CLI package path is not the frozen package directory")
    package_root = package_directory.parent
    package_hash, package_request_bytes = frozen_package_snapshot(
        package_root, max_total_bytes=profile.max_output_bytes
    )
    validation_plan_hash = None
    if domain == "text" and profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7"}:
        try:
            package_request = json.loads(package_request_bytes)
            from .codex_exec_validation import validation_plan_from_package
            validation_plan_hash = validation_plan_from_package(package_request).plan_hash
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise InvalidTransitionError("frozen text package has no valid trusted validation plan") from error
    attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, operation_key)

    if attempt is None:
        if not allow_admission:
            return None, None, profile
        if evidence.executor_attempt_id is not None:
            raise InvalidTransitionError("checkpoint names a CLI attempt absent from the project store")
        registry.require_codex_exec_readiness()
        reserved = CodexExecAttempt(
            attemptId=uuid4(),
            runId=view.id,
            projectId=view.project_id,
            jobId=evidence.job_id,
            operationKey=operation_key,
            domain=domain,
            requestHash=evidence.request_hash,
            packageHash=package_hash,
            profileHash=profile.profile_hash,
            plotloomCodeRevision=view.policy.code_revision,
            validationPlanHash=validation_plan_hash,
            reservedImageOutputs=1 if domain == "image" else 0,
            imageBudgetState="reserved" if domain == "image" else "none",
            state="reserved",
        )
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
        if (attempt.job_id != evidence.job_id or attempt.request_hash != evidence.request_hash
                or attempt.package_hash != package_hash or attempt.domain != domain
                or attempt.operation_key != operation_key
                or attempt.plotloom_code_revision != view.policy.code_revision
                or attempt.validation_plan_hash != validation_plan_hash):
            raise InvalidTransitionError("retained CLI attempt differs from its frozen package or stage")
        if evidence.executor_attempt_id != attempt.attempt_id:
            raise InvalidTransitionError("checkpoint and project CLI attempt identities differ")
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
            host_status = registry.codex_exec_status(attempt.attempt_id)
            # A host admission is durable before process start and idempotent by
            # attempt ID. Reconcile an absent record only with the same frozen
            # spawn-intent snapshot; never construct a replacement attempt.
            if allow_admission and host_status.state == "not_found" and attempt.state == "spawn_intent":
                host_status = registry.codex_exec_admit(attempt)

    host_attempt = host_status.attempt
    if host_status.state == "not_found":
        return attempt, receipt, profile
    if host_attempt is None:
        raise InvalidTransitionError("Mac supervisor status omitted its typed attempt snapshot")
    if _identity(host_attempt) != _identity(attempt):
        raise InvalidTransitionError("Mac supervisor returned a different frozen CLI attempt")
    changes = {field: getattr(host_attempt, field) for field in _RECONCILED_FIELDS}
    if changes != {field: getattr(attempt, field) for field in _RECONCILED_FIELDS} or host_status.receipt != receipt:
        with command_factory(store, view, claim, OperationScope.EVIDENCE):
            store.repository.autopilot.update_exec_attempt(
                attempt.attempt_id,
                receipt=host_status.receipt,
                **changes,
            )
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
