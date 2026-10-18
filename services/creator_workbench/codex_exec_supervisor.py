"""Durable owner for immutable local Codex Exec jobs."""
from __future__ import annotations

import os
import stat
import subprocess
import threading
from pathlib import Path

from codex_exec_supervisor_admission import CodexExecSupervisorAdmissionMixin
from codex_exec_supervisor_abandonment import CodexExecSupervisorAbandonmentMixin
from codex_exec_supervisor_control import CodexExecSupervisorControlMixin
from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_job import CodexExecSupervisorJobMixin
from codex_exec_supervisor_ledger import CodexExecSupervisorLedgerMixin
from codex_exec_supervisor_namespace import CodexExecSupervisorNamespaceMixin
from codex_exec_supervisor_pool import CodexExecSupervisorPoolMixin
from codex_exec_supervisor_process import CodexExecSupervisorProcessMixin
from codex_exec_supervisor_queue_control import CodexExecSupervisorQueueControlMixin
from codex_exec_supervisor_qualification import CodexExecSupervisorQualificationMixin
from codex_exec_supervisor_qualification_admission import CodexExecSupervisorQualificationAdmissionMixin
from codex_exec_supervisor_worker_ownership import (
    CodexExecSupervisorWorkerOwnershipMixin,
)

from plotloom.codex_exec_auth import check_codex_exec_readiness, resolve_codex_home
from plotloom.codex_exec_auth import (
    credential_free_environment as _credential_free_environment,
)


class CodexExecSupervisor(
    CodexExecSupervisorAbandonmentMixin,
    CodexExecSupervisorQualificationMixin,
    CodexExecSupervisorQualificationAdmissionMixin,
    CodexExecSupervisorNamespaceMixin,
    CodexExecSupervisorAdmissionMixin,
    CodexExecSupervisorPoolMixin,
    CodexExecSupervisorQueueControlMixin,
    CodexExecSupervisorWorkerOwnershipMixin,
    CodexExecSupervisorControlMixin,
    CodexExecSupervisorProcessMixin,
    CodexExecSupervisorJobMixin,
    CodexExecSupervisorLedgerMixin,
):
    def __init__(self, executable: Path, *, source_root: Path, outputs_root: Path, private_root: Path,
            pool_limits=None, namespace_binding_sha256=None):
        self.executable = executable.expanduser().resolve(strict=True)
        self.source_root = source_root.expanduser().resolve(strict=True)
        self.outputs_root = outputs_root.expanduser().resolve(strict=True)
        self.private_root = private_root.expanduser().absolute()
        if any(path.is_symlink() for path in (executable, source_root, outputs_root, private_root)):
            raise CodexExecSupervisorError("Codex Exec host roots cannot be symlinks")
        import sys
        source_python = str(self.source_root / "src")
        if source_python not in sys.path:
            sys.path.insert(0, source_python)
        self._requested_pool_limits = pool_limits
        self._configure_namespace(namespace_binding_sha256)
        try:
            self.codex_home = resolve_codex_home(
                forbidden_roots=(self.source_root, self.outputs_root, self.private_root)
            )
        except ValueError as error:
            raise CodexExecSupervisorError(
                "Codex Exec requires an existing user-owned authentication home outside project state"
            ) from error
        self.private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        metadata = self.private_root.stat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise CodexExecSupervisorError("Codex Exec private evidence root must belong to this user")
        self.private_root.chmod(0o700)
        self.database = self.private_root / "supervisor.sqlite3"
        self._guard = threading.RLock()
        self._workers: dict[str, subprocess.Popen] = {}
        self._initialize()

    def profile(self):
        from plotloom.codex_exec_profile import build_codex_exec_profile
        return build_codex_exec_profile(self.executable, source_root=self.source_root, pool_limits=self.pool_limits)

    def codex_exec_readiness(self):
        """Probe local file-store login state without exposing CLI diagnostics."""
        environment = _credential_free_environment()
        environment["CODEX_HOME"] = str(self.codex_home)
        return check_codex_exec_readiness(
            self.executable,
            source_root=self.source_root,
            environment=environment,
            forbidden_roots=(self.source_root, self.outputs_root, self.private_root),
        )
