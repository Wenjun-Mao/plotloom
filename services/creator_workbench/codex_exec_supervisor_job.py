"""Trusted project job resolution and frozen package verification."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorJobMixin:
    def _resolve_job(self, attempt):
        from plotloom.project_storage.project_home import find_project_home
        home = find_project_home(self.outputs_root, str(attempt.project_id)).path
        if home.is_symlink() or not home.is_dir():
            raise CodexExecSupervisorError("Codex Exec project home is unsafe")
        if attempt.domain == "text":
            job_root = home / "outputs" / "creative-handoff" / "jobs" / attempt.job_id
            parents = (home / "outputs", home / "outputs" / "creative-handoff",
                home / "outputs" / "creative-handoff" / "jobs")
            if any(path.is_symlink() or not path.is_dir() for path in parents):
                raise CodexExecSupervisorError("Codex Exec creative job path is unsafe")
        else:
            runs = home / "runs"
            if runs.is_symlink() or not runs.is_dir():
                raise CodexExecSupervisorError("Codex Exec image run root is unavailable")
            candidates = [
                path / "jobs" / attempt.job_id
                for path in runs.iterdir()
                if path.name.endswith("__" + attempt.job_id) and not path.is_symlink()
            ]
            candidates = [path for path in candidates if path.is_dir() and not path.is_symlink()]
            if len(candidates) != 1:
                raise CodexExecSupervisorError("Codex Exec image job has no unique project run directory")
            job_root = candidates[0]
        try:
            resolved_home = home.resolve(strict=True)
            resolved_job = job_root.resolve(strict=True)
        except OSError as error:
            raise CodexExecSupervisorError("Codex Exec frozen job directory is unavailable") from error
        if not resolved_job.is_relative_to(resolved_home):
            raise CodexExecSupervisorError("Codex Exec job directory escapes its project home")
        if job_root.is_symlink() or not job_root.is_dir():
            raise CodexExecSupervisorError("Codex Exec frozen job path is unsafe")
        package = job_root / "package"
        delivery = job_root / "delivery"
        if package.is_symlink() or not package.is_dir():
            raise CodexExecSupervisorError("Codex Exec frozen package directory is unavailable")
        delivery.mkdir(mode=0o700, exist_ok=True)
        if delivery.is_symlink() or not delivery.is_dir():
            raise CodexExecSupervisorError("Codex Exec delivery directory is unsafe")
        return home, job_root

    @staticmethod
    def _read_regular(path: Path, *, max_bytes: int) -> bytes:
        if path.is_symlink():
            raise CodexExecSupervisorError("Codex Exec package contains a symlink")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
                raise CodexExecSupervisorError("Codex Exec package file is not bounded regular data")
            blocks = []
            total = 0
            while True:
                block = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
                if not block:
                    break
                blocks.append(block)
                total += len(block)
                if total > max_bytes:
                    raise CodexExecSupervisorError("Codex Exec package file exceeds its byte limit")
            return b"".join(blocks)
        finally:
            os.close(descriptor)

    def _verify_attempt_package(self, attempt, job_root, profile):
        from plotloom.codex_exec_runtime import package_tree_hash
        if attempt.profile_hash != profile.profile_hash:
            raise CodexExecSupervisorError("Codex Exec attempt profile differs from the current Mac host")
        observed_hash = package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes)
        if observed_hash != attempt.package_hash:
            raise CodexExecSupervisorError("Codex Exec frozen package bytes differ from the project attempt")
        package_request = json.loads(self._read_regular(job_root / "package" / "request.json", max_bytes=2_000_000))
        if (
            package_request.get("jobId") != attempt.job_id
            or package_request.get("requestHash") != attempt.request_hash
            or package_request.get("executorBackend") != "codex_exec"
        ):
            raise CodexExecSupervisorError("Codex Exec package does not bind the exact project attempt")
        if attempt.plotloom_code_revision is None:
            raise CodexExecSupervisorError("Codex Exec attempt omits its frozen Plotloom source revision")
        if attempt.domain == "text":
            package_code_revision = package_request.get("plotloomCodeRevision")
            if package_request.get("packageVersion") != 3 or package_code_revision != attempt.plotloom_code_revision:
                raise CodexExecSupervisorError("Codex Exec text package does not bind the frozen Plotloom source revision")
        else:
            package_code_revision = package_request.get("specialistPreflight", {}).get("codeRevision")
            if package_code_revision != attempt.plotloom_code_revision:
                raise CodexExecSupervisorError("Codex Exec image package does not bind the frozen Plotloom source revision")
        if attempt.domain == "text":
            from plotloom.codex_exec_resources import codex_exec_source_read_paths
            try:
                codex_exec_source_read_paths(self.source_root, package_request)
            except ValueError as error:
                raise CodexExecSupervisorError("Codex Exec source resources do not match the frozen package") from error
        return package_request
