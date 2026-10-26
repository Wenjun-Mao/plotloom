"""Explicit installation-local client for authenticated Codex Exec host commands."""
from __future__ import annotations
import json
import subprocess
from uuid import UUID
from .codex_exec_contracts import CodexExecAttempt, CodexExecHostStatus, CodexExecProfile, CodexExecReadiness
from .image_job_contracts import ImageJobError


class CodexExecHostClient:
    """Own command bounds, error classification and the explicit child environment."""

    def __init__(self, executable: str | None, environment: dict[str, str] | None):
        self.executable = executable
        self.environment = environment

    def codex_exec_profile(self) -> CodexExecProfile:
        """Read the source and CLI profile from the authenticated Mac host."""
        if not self.executable:
            raise ImageJobError(
                "codex_exec_unavailable",
                "Codex Exec is unavailable because the authenticated Mac host is not configured.",
            )
        try:
            result = subprocess.run(
                [self.executable, "exec-profile"],
                capture_output=True,
                timeout=20,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ImageJobError(
                "codex_exec_profile_unavailable",
                "The Mac host could not report its qualified Codex Exec profile.",
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ImageJobError(
                "codex_exec_profile_unavailable",
                "The Mac host could not report its qualified Codex Exec profile.",
            )
        try:
            profile = CodexExecProfile.model_validate_json(result.stdout)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "codex_exec_profile_invalid",
                "The Mac host returned an unsupported Codex Exec profile.",
            ) from error
        return profile

    def codex_exec_readiness(self) -> CodexExecReadiness:
        """Read the host's dynamic login readiness without freezing it into policy."""
        if not self.executable:
            raise ImageJobError(
                "codex_exec_unavailable",
                "Codex Exec is unavailable because the authenticated Mac host is not configured.",
            )
        try:
            result = subprocess.run(
                [self.executable, "exec-readiness"],
                capture_output=True,
                timeout=20,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ImageJobError(
                "codex_exec_readiness_unavailable",
                "The Mac host could not report Codex Exec login readiness.",
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ImageJobError(
                "codex_exec_readiness_unavailable",
                "The Mac host could not report Codex Exec login readiness.",
            )
        try:
            return CodexExecReadiness.model_validate_json(result.stdout)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "codex_exec_readiness_invalid",
                "The Mac host returned an unsupported Codex Exec readiness state.",
            ) from error

    def require_codex_exec_readiness(self) -> CodexExecReadiness:
        readiness = self.codex_exec_readiness()
        if not readiness.ready:
            raise ImageJobError(
                "codex_exec_not_ready",
                "Codex Exec has no usable local file-store login. Sign in through the existing Codex app CLI, then retry before starting a run.",
            )
        return readiness

    def codex_exec_admit(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        """Request one idempotent initial attempt from the Mac-owned supervisor."""
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        if attempt.state != "spawn_intent":
            raise ImageJobError("codex_exec_attempt_invalid", "Codex Exec admission requires a persisted spawn intent.")
        return self._codex_exec_request(
            "exec-admit",
            "--attempt-json",
            json.dumps(attempt.model_dump(mode="json", by_alias=True), separators=(",", ":")),
        )

    def codex_exec_status(self, attempt_id) -> CodexExecHostStatus:
        return self._codex_exec_request("exec-status", "--attempt-id", str(UUID(str(attempt_id))))

    def codex_exec_abandonment(self, packet, *, revoke=False):
        from .project_abandonment_contracts import AbandonmentPreview
        if not self.executable:
            raise ImageJobError("codex_exec_unavailable", "无法验证原 Codex Exec 主机；项目保留。")
        try:
            result = subprocess.run([self.executable, "exec-project-revoke" if revoke else "exec-abandonment-preview",
                "--packet-json", packet.model_dump_json(by_alias=True)], capture_output=True,
                timeout=30, check=False, env=self.environment)
            if result.returncode != 0 or result.stderr:
                raise ValueError("unacknowledged abandonment")
            return AbandonmentPreview.model_validate_json(result.stdout)
        except (OSError, subprocess.TimeoutExpired, TypeError, ValueError) as error:
            raise ImageJobError("project_abandonment_unconfirmed", "主机未确认项目放弃；项目保留，请重新核对原任务。") from error

    def codex_exec_cancel(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        """Fence a stop against the exact attempt, including pre-admission races."""
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        return self._codex_exec_request(
            "exec-cancel",
            "--attempt-json",
            json.dumps(attempt.model_dump(mode="json", by_alias=True), separators=(",", ":")),
        )

    def codex_exec_suspend(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        return self._codex_exec_authorize("exec-suspend", attempt)

    def codex_exec_resume(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        return self._codex_exec_authorize("exec-resume", attempt)

    def _codex_exec_authorize(self, command, attempt):
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        return self._codex_exec_request(command, "--attempt-json",
            json.dumps(attempt.model_dump(mode="json", by_alias=True), separators=(",", ":")))

    def _codex_exec_request(self, command: str, *arguments: str) -> CodexExecHostStatus:
        if not self.executable:
            raise ImageJobError(
                "codex_exec_unavailable",
                "Codex Exec is unavailable because the authenticated Mac host is not configured.",
            )
        try:
            result = subprocess.run(
                [self.executable, command, *arguments],
                capture_output=True,
                timeout=30,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ImageJobError(
                "codex_exec_outcome_unknown",
                "The Mac supervisor did not acknowledge this Codex Exec operation; inspect the original attempt.",
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ImageJobError(
                "codex_exec_outcome_unknown",
                "The Mac supervisor did not acknowledge this Codex Exec operation; inspect the original attempt.",
            )
        try:
            return CodexExecHostStatus.model_validate_json(result.stdout)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "codex_exec_status_invalid",
                "The Mac supervisor returned an unsupported Codex Exec status.",
            ) from error
