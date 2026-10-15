"""Frozen package checks and project-owned CLI reservation construction."""
import json
from pathlib import Path
from uuid import uuid4

from .autopilot_contracts import CheckpointEvidence
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile
from .codex_exec_runtime import frozen_package_snapshot
from .exceptions import InvalidTransitionError


def prepared_exec_inputs(registry, view, checkpoint, *, domain, package_path):
    evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
    profile = CodexExecProfile.model_validate(registry.codex_exec_profile())
    if profile != view.policy.executor_binding:
        raise InvalidTransitionError("Codex Exec profile changed after the launch was frozen.")
    if (profile.contract_version in {"plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
            and not view.policy.code_revision):
        raise InvalidTransitionError("Codex Exec launch omits its frozen Plotloom source revision.")
    if evidence.job_id is None or evidence.request_hash is None:
        raise InvalidTransitionError("prepared CLI checkpoint has no frozen job identity")
    directory = Path(package_path).resolve(strict=True)
    if directory.name != "package":
        raise InvalidTransitionError("prepared CLI package path is not the frozen package directory")
    package_hash, request_bytes = frozen_package_snapshot(directory.parent, max_total_bytes=profile.max_output_bytes)
    validation_hash = None
    if domain == "text" and profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}:
        try:
            from .codex_exec_validation import validation_plan_from_package
            validation_hash = validation_plan_from_package(json.loads(request_bytes)).plan_hash
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise InvalidTransitionError("frozen text package has no valid trusted validation plan") from error
    return evidence, profile, package_hash, validation_hash


def new_reserved_attempt(view, checkpoint, domain, inputs):
    evidence, profile, package_hash, validation_hash = inputs
    return CodexExecAttempt(
        attemptId=uuid4(), runId=view.id, projectId=view.project_id,
        jobId=evidence.job_id, operationKey=checkpoint["operationKey"], domain=domain,
        requestHash=evidence.request_hash, packageHash=package_hash,
        profileHash=profile.profile_hash, plotloomCodeRevision=view.policy.code_revision,
        validationPlanHash=validation_hash, reservedImageOutputs=1 if domain == "image" else 0,
        imageBudgetState="reserved" if domain == "image" else "none", state="reserved",
    )


def assert_prepared_attempt(attempt, view, checkpoint, domain, inputs):
    evidence, _profile, package_hash, validation_hash = inputs
    if (attempt.job_id != evidence.job_id or attempt.request_hash != evidence.request_hash
            or attempt.package_hash != package_hash or attempt.domain != domain
            or attempt.operation_key != checkpoint["operationKey"]
            or attempt.plotloom_code_revision != view.policy.code_revision
            or attempt.validation_plan_hash != validation_hash):
        raise InvalidTransitionError("retained CLI attempt differs from its frozen package or stage")
    if evidence.executor_attempt_id != attempt.attempt_id:
        raise InvalidTransitionError("checkpoint and project CLI attempt identities differ")
