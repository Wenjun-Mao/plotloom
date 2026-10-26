"""Run frozen text validators and renderers as owned, sandboxed host work."""
from __future__ import annotations

import json
import os
import time
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import (
    CodexExecValidationFailure,
    CodexExecValidationOwnershipUnknown,
)
from codex_exec_supervisor_validation_process import (
    CodexExecSupervisorValidationProcessMixin,
)


class CodexExecSupervisorValidationMixin(CodexExecSupervisorValidationProcessMixin):
    STEP_TIMEOUT_SECONDS = 300
    def _validate_text_delivery(
        self, attempt, profile, package_request, job_root, private_dir, source_resources,
    ):
        from plotloom.codex_exec_files import scan_regular_tree
        from plotloom.codex_exec_resources import codex_exec_source_resources
        from plotloom.codex_exec_runtime import package_tree_hash
        from plotloom.codex_exec_validation import (
            CodexExecTextValidationEvidence,
            CodexExecValidationStepEvidence,
            expand_validation_argv,
            validation_plan_from_package,
        )
        from plotloom.public_values import contains_secret_value

        try:
            plan = validation_plan_from_package(package_request)
        except (KeyError, TypeError, ValueError) as error:
            raise self._validation_failure("validation_plan_invalid", "0" * 64) from error
        if attempt.validation_plan_hash != plan.plan_hash:
            raise self._validation_failure("validation_plan_attempt_mismatch", plan.plan_hash)
        if (attempt.plotloom_code_revision != plan.source_revision
                or package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes) != attempt.package_hash):
            raise self._validation_failure("validation_frozen_input_changed", plan.plan_hash)
        if self.profile().profile_hash != profile.profile_hash:
            raise self._validation_failure("validation_profile_changed", plan.plan_hash)
        try:
            current_resources = codex_exec_source_resources(self.source_root, package_request)
        except (OSError, ValueError, RuntimeError) as error:
            raise self._validation_failure("validation_runtime_unavailable", plan.plan_hash) from error
        if current_resources != source_resources:
            raise self._validation_failure("validation_runtime_changed", plan.plan_hash)
        self._validate_plan_inputs(plan, job_root)

        initial = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
        if {item.relative_path for item in initial} != {plan.candidate_filename}:
            raise self._validation_failure("candidate_inventory_invalid", plan.plan_hash)
        candidate_before = initial[0]
        if candidate_before.size_bytes > 2_000_000:
            raise self._validation_failure("candidate_too_large", plan.plan_hash)
        if plan.stage == "outline":
            from plotloom.codex_exec_files import (
                CodexExecFileError,
                read_confined_regular_file,
            )
            from plotloom.outline_report_metadata import assert_outline_report_metadata

            try:
                raw = read_confined_regular_file(job_root, "delivery/" + plan.candidate_filename, max_bytes=2_000_000)
            except CodexExecFileError as error:
                raise self._validation_failure("candidate_read_invalid", plan.plan_hash) from error
            if (sha256(raw).hexdigest(), len(raw)) != (candidate_before.sha256, candidate_before.size_bytes):
                raise self._validation_failure("validation_candidate_changed", plan.plan_hash)
            try:
                candidate = json.loads(raw)
                assert_outline_report_metadata(candidate)
            except (ValueError, UnicodeError) as error:
                raise self._validation_failure("outline_report_metadata_invalid", plan.plan_hash) from error

        validation_root = private_dir / "validation"
        if validation_root.exists() or validation_root.is_symlink():
            if validation_root.is_symlink() or not validation_root.is_dir() or any(validation_root.iterdir()):
                raise self._validation_failure("validation_workspace_unsafe", plan.plan_hash)
        else:
            validation_root.mkdir(mode=0o700)
        sandbox_home = private_dir / "sandbox-home"
        try:
            sandbox_home.mkdir(mode=0o700)
        except FileExistsError as error:
            raise self._validation_failure("validation_home_already_exists", plan.plan_hash) from error
        if sandbox_home.is_symlink() or not sandbox_home.is_dir():
            raise self._validation_failure("validation_home_unsafe", plan.plan_hash)

        tool_paths = dict(source_resources.tools)
        step_evidence = []
        for step in plan.steps:
            argv = expand_validation_argv(
                step,
                source_root=self.source_root,
                submodule_root=self.source_root / "third_party" / "shuohao-skills",
                job_root=job_root,
                candidate_filename=plan.candidate_filename,
                tool_paths=tool_paths,
            )
            if argv[0] != str(tool_paths[step.program]):
                raise self._validation_failure("validation_program_mismatch", plan.plan_hash)
            argv_hash = _hash_json(list(argv))
            stdout_path = validation_root / f"{step.step_id}.stdout"
            stderr_path = validation_root / f"{step.step_id}.stderr"
            if step.stdout_is_report:
                stdout_path = job_root / "delivery" / plan.report_filename
            stdout_fd = _create_once(stdout_path)
            stderr_fd = _create_once(stderr_path)
            stdout_context = os.fdopen(stdout_fd, "wb")
            stderr_context = os.fdopen(stderr_fd, "wb")
            environment = self._cli_environment(
                private_dir,
                source_root=self.source_root,
                domain="text",
                source_resources=source_resources,
                profile=profile,
            )
            environment["CODEX_HOME"] = str(sandbox_home)
            command = self._sandbox_validation_command(
                profile, job_root, private_dir, validation_root, argv, source_resources,
            )
            started = time.monotonic()
            process = None
            identity = None
            try:
                with stdout_context as stdout, stderr_context as stderr:
                    process, identity = self._spawn_validation_process(
                        attempt, step.step_id, command, environment, validation_root, stdout, stderr,
                    )
                    exit_code = self._wait_validation_process(
                        attempt, step.step_id, process, identity, started=started, timeout_seconds=self.STEP_TIMEOUT_SECONDS,
                        stdout_path=stdout_path, stderr_path=stderr_path,
                        max_bytes=min(profile.max_output_bytes, 50_000_000),
                    )
            except CodexExecValidationFailure:
                raise
            except CodexExecValidationOwnershipUnknown:
                raise
            except BaseException as error:
                if process is not None and identity is not None:
                    self._stop_spawned_validation(process, attempt, step.step_id, identity)
                raise self._validation_failure(
                    f"validation_process_failed_{step.step_id}", plan.plan_hash,
                    (stdout_path, stderr_path), argv_hash=argv_hash,
                ) from error

            stdout_hash, stdout_size = _hash_file(stdout_path, max_bytes=50_000_000)
            stderr_hash, stderr_size = _hash_file(stderr_path, max_bytes=50_000_000)
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            if exit_code != 0:
                failure = self._validation_failure(
                    f"validation_step_failed_{step.step_id}", plan.plan_hash,
                    (stdout_path, stderr_path), argv_hash=argv_hash, exit_code=exit_code,
                )
                if (step.step_id == "validate" and exit_code == 42
                        and plan.stage in {"outline", "characters", "art"}
                        and package_request.get("contentValidationContract") == "plotloom.typed-content-result.v1"
                        and (profile.text_correction_contract == "plotloom.text-correction.v2"
                            or profile.text_correction_limit == 1)):
                    # Recheck all immutable authority before promoting this source API's
                    # normal result. Neither stderr nor arbitrary exits grant correction.
                    self._require_validation_not_cancelled(attempt, plan.plan_hash)
                    if (package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes) != attempt.package_hash
                            or self.profile().profile_hash != profile.profile_hash
                            or codex_exec_source_resources(self.source_root, package_request) != source_resources
                            or scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes) != initial):
                        raise self._validation_failure("validation_rejection_authority_changed", plan.plan_hash)
                    from plotloom.text_correction_contracts import (
                        TextContentIssue,
                        TextContentRejection,
                    )
                    try:
                        result = json.loads(self._read_regular(stdout_path, max_bytes=64_000))
                        if (set(result) != {"contract", "candidateHash", "issues", "displayDiagnostics"}
                                or result["contract"] != "plotloom.typed-content-result.v1"
                                or result["candidateHash"] != candidate_before.sha256):
                            raise ValueError("typed content result mismatch")
                        failure.content_rejection = TextContentRejection(
                            source_attempt_id=attempt.attempt_id, run_id=attempt.run_id, stage=plan.stage,
                            job_id=attempt.job_id, candidate_hash=candidate_before.sha256,
                            validation_evidence_hash=failure.evidence_hash, request_hash=attempt.request_hash,
                            package_hash=attempt.package_hash, plan_hash=plan.plan_hash,
                            profile_hash=profile.profile_hash, source_revision=attempt.plotloom_code_revision,
                            issues=tuple(TextContentIssue.model_validate(issue) for issue in result["issues"]),
                            display_diagnostics=tuple("[redacted]" if contains_secret_value(value)
                                else value for value in result["displayDiagnostics"]),
                        )
                    except (ValueError, TypeError, KeyError):
                        raise self._validation_failure("validation_rejection_packet_invalid", plan.plan_hash) from None
                raise failure
            if package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes) != attempt.package_hash:
                raise self._validation_failure("validation_package_changed", plan.plan_hash)
            self._require_validation_not_cancelled(attempt, plan.plan_hash)
            delivery_now = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
            expected_now = {plan.candidate_filename} | (
                {plan.report_filename} if step.stdout_is_report else set()
            )
            if {item.relative_path for item in delivery_now} != expected_now:
                raise self._validation_failure("validation_output_inventory_changed", plan.plan_hash)
            candidate_after = next(item for item in delivery_now if item.relative_path == plan.candidate_filename)
            if candidate_after != candidate_before:
                raise self._validation_failure("validation_candidate_changed", plan.plan_hash)
            if step.stdout_is_report:
                report_output = next(item for item in delivery_now if item.relative_path == plan.report_filename)
                if (stdout_hash, stdout_size) != (report_output.sha256, report_output.size_bytes):
                    raise self._validation_failure("renderer_report_bytes_mismatch", plan.plan_hash)
                report_bytes = stdout_path.read_bytes()
                if not report_bytes.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                    raise self._validation_failure("renderer_report_not_html", plan.plan_hash)
            step_evidence.append(CodexExecValidationStepEvidence(
                stepId=step.step_id,
                argvHash=argv_hash,
                exitCode=0,
                stdoutHash=stdout_hash,
                stdoutSizeBytes=stdout_size,
                stderrHash=stderr_hash,
                stderrSizeBytes=stderr_size,
                durationMs=duration_ms,
            ))

        if package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes) != attempt.package_hash:
            raise self._validation_failure("validation_final_package_changed", plan.plan_hash)
        try:
            final_profile = self.profile()
            final_resources = codex_exec_source_resources(self.source_root, package_request)
        except (OSError, ValueError, RuntimeError) as error:
            raise self._validation_failure("validation_final_runtime_changed", plan.plan_hash) from error
        if final_profile.profile_hash != profile.profile_hash or final_resources != source_resources:
            raise self._validation_failure("validation_final_runtime_changed", plan.plan_hash)
        self._require_validation_not_cancelled(attempt, plan.plan_hash)
        final = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
        if {item.relative_path for item in final} != {plan.candidate_filename, plan.report_filename}:
            raise self._validation_failure("validation_final_inventory_invalid", plan.plan_hash)
        candidate = next(item for item in final if item.relative_path == plan.candidate_filename)
        report = next(item for item in final if item.relative_path == plan.report_filename)
        if candidate != candidate_before:
            raise self._validation_failure("validation_final_candidate_changed", plan.plan_hash)
        return CodexExecTextValidationEvidence(
            planHash=plan.plan_hash,
            profileHash=profile.profile_hash,
            validatorHash=profile.validator_hash,
            requestHash=attempt.request_hash,
            packageHash=attempt.package_hash,
            sourceRevision=attempt.plotloom_code_revision,
            candidateFilename=plan.candidate_filename,
            candidateHash=candidate.sha256,
            candidateSizeBytes=candidate.size_bytes,
            reportFilename=plan.report_filename,
            reportHash=report.sha256,
            reportSizeBytes=report.size_bytes,
            steps=tuple(step_evidence),
        )

    def _require_validation_not_cancelled(self, attempt, plan_hash):
        latest = self._load(self._row(attempt.attempt_id)).attempt
        if latest is None or latest.state != "validating":
            raise self._validation_failure("validation_cancelled", plan_hash)

    def _validate_plan_inputs(self, plan, job_root):
        try:
            for item in plan.inputs:
                path = job_root / "package" / "inputs" / item.filename
                content = self._read_regular(path, max_bytes=1_000_000)
                if (sha256(content).hexdigest(), len(content)) != (item.sha256, item.size_bytes):
                    raise self._validation_failure("validation_input_changed", plan.plan_hash)
        except OSError as error:
            raise self._validation_failure("validation_input_unavailable", plan.plan_hash) from error

    def _sandbox_validation_command(self, profile, job_root, private_dir, validation_root, argv, source_resources):
        filesystem = self._permission_filesystem_config(
            profile,
            job_root,
            job_root / "delivery",
            private_dir,
            self.codex_home,
            source_resources.read_paths,
            domain="text",
            additional_write_paths=(validation_root,),
        )
        prefix = profile.permission_profile
        return [
            str(self.executable), "sandbox",
            "--permission-profile", prefix,
            "--sandbox-state-disable-network",
            "--cd", str(validation_root),
            "--config", f'default_permissions="{prefix}"',
            "--config", f'permissions.{prefix}.extends=":workspace"',
            "--config", filesystem,
            "--config", f"permissions.{prefix}.network.enabled=false",
            "--", *argv,
        ]

    @staticmethod
    def _validation_failure(code, plan_hash, paths=(), *, argv_hash=None, exit_code=None):
        digest = sha256()
        digest.update(b"plotloom.codex-exec.text-validation-failure.v1\0")
        digest.update(code.encode("utf-8"))
        digest.update((plan_hash or "").encode("ascii", "ignore"))
        digest.update((argv_hash or "").encode("ascii", "ignore"))
        digest.update(str(exit_code).encode("ascii") if exit_code is not None else b"unavailable")
        for path in paths:
            try:
                file_hash, size = _hash_file(path, max_bytes=50_000_000)
            except (OSError, ValueError):
                digest.update(b"missing")
            else:
                digest.update(file_hash.encode("ascii"))
                digest.update(str(size).encode("ascii"))
        return CodexExecValidationFailure(code, digest.hexdigest())


def _create_once(path: Path) -> int:
    return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)


def _hash_json(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _hash_file(path: Path, *, max_bytes: int):
    digest = sha256()
    total = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            total += len(block)
            if total > max_bytes:
                raise ValueError("validation evidence exceeds its byte limit")
            digest.update(block)
    return digest.hexdigest(), total


