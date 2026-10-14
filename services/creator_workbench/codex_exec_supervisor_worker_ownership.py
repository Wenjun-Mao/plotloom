"""Attempt-scoped worker claims, process ownership and launch."""
from __future__ import annotations

import os
import subprocess
import time
from contextlib import closing
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_auth import (
    credential_free_environment as _credential_free_environment,
)


class CodexExecSupervisorWorkerOwnershipMixin:
    def _register_worker(self, attempt_id):
        """Persist the attempt-scoped worker identity before it can launch Codex."""
        pid = os.getpid()
        group_id, birth_identity = self._process_identity(pid)
        if group_id != pid:
            raise CodexExecSupervisorError("Codex Exec worker must own its isolated process group")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status_json,worker_pid,worker_group_id,worker_birth_identity "
                "FROM exec_attempts WHERE attempt_id=?", (str(attempt_id),)
            ).fetchone()
            if row is None:
                connection.rollback()
                raise CodexExecSupervisorError("Codex Exec worker has no durable attempt reservation")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            attempt = CodexExecAttempt.model_validate_json(row["status_json"])
            if attempt.state not in {"spawn_intent", "running", "cancel_requested"}:
                connection.rollback()
                return False
            facts = (row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"])
            if facts == (None, None, None):
                connection.execute(
                    "UPDATE exec_attempts SET worker_pid=?,worker_group_id=?,worker_birth_identity=?,updated_at=? "
                    "WHERE attempt_id=? AND worker_pid IS NULL",
                    (pid, group_id, birth_identity, time.time(), str(attempt_id)),
                )
            elif facts != (pid, group_id, birth_identity):
                connection.rollback()
                return False
            connection.commit()
        return True

    def _owns_worker(self, row):
        if row["worker_pid"] is None or row["worker_group_id"] is None or not row["worker_birth_identity"]:
            return False
        try:
            identity = self._process_identity(row["worker_pid"])
        except (OSError, subprocess.SubprocessError, ValueError):
            return False
        return identity == (row["worker_group_id"], row["worker_birth_identity"])

    def _registered_worker_identity(self, attempt_id):
        row = self._row(attempt_id)
        if row is None or row["worker_pid"] != os.getpid():
            return None
        recorded = (row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"])
        try:
            actual = (os.getpid(), *self._process_identity(os.getpid()))
        except (OSError, subprocess.SubprocessError, ValueError):
            return None
        return actual if actual == recorded else None

    def run_worker(self, attempt_id):
        """Execute the one durable host attempt inside its attempt-scoped process."""
        if not self._register_worker(attempt_id):
            return
        row = self._row(attempt_id)
        from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecProfile
        attempt = CodexExecAttempt.model_validate_json(row["status_json"])
        if attempt.state == "cancel_requested" and attempt.process_id is None:
            self._finish_not_started(
                attempt, worker_identity=self._registered_worker_identity(attempt_id)
            )
            return
        if attempt.state != "spawn_intent":
            return
        try:
            profile = CodexExecProfile.model_validate(self.profile())
            _, job_root = self._resolve_job(attempt)
            package_request = self._verify_attempt_package(attempt, job_root, profile)
            source_resources = None
            if attempt.domain == "text":
                from plotloom.codex_exec_resources import codex_exec_source_resources
                source_resources = codex_exec_source_resources(self.source_root, package_request)
            private_dir = Path(row["private_dir"])
            if private_dir.is_symlink() or not private_dir.is_dir():
                raise CodexExecSupervisorError("Codex Exec private attempt directory is unavailable")
        except BaseException:
            current = self._load(self._row(attempt_id)).attempt
            if current is not None and current.state in {"spawn_intent", "cancel_requested"} and current.process_id is None:
                self._finish_not_started(
                    current, worker_identity=self._registered_worker_identity(attempt_id)
                )
            elif current is not None and current.state not in {"completed", "failed", "settled", "outcome_unknown"}:
                self._mark_unknown(current)
            raise
        self._run(attempt, profile, package_request, job_root, private_dir, source_resources)

    def _start_worker(self, attempt_id):
        """Start or reconnect to the one worker assigned to this durable attempt."""
        with self._guard:
            row = self._row(attempt_id)
            if row is None:
                raise CodexExecSupervisorError("Codex Exec attempt disappeared before worker start")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            attempt = CodexExecAttempt.model_validate_json(row["status_json"])
            if attempt.state != "spawn_intent":
                return
            if row["worker_pid"] is not None:
                if self._owns_worker(row):
                    return
                self._mark_unknown(attempt)
                return
            worker_script = self.source_root / "services" / "creator_workbench" / "codex_exec_supervisor_worker.py"
            if worker_script.is_symlink() or not worker_script.is_file() or not worker_script.resolve(strict=True).is_relative_to(self.source_root):
                self._finish_not_started(attempt)
                raise CodexExecSupervisorError("source-owned Codex Exec worker is unavailable")
            import sys
            command = [
                sys.executable, str(worker_script),
                "--attempt-id", str(attempt.attempt_id),
                "--executable", str(self.executable),
                "--source-root", str(self.source_root),
                "--outputs-root", str(self.outputs_root),
                "--private-root", str(self.private_root),
            ]
            worker = subprocess.Popen(
                command,
                cwd=self.source_root,
                env=self._worker_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
            self._workers[str(attempt.attempt_id)] = worker
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current = self._row(attempt_id)
                if current["worker_pid"] is not None:
                    if current["worker_pid"] == worker.pid and self._owns_worker(current):
                        return
                    worker.poll()
                    return
                if worker.poll() is not None:
                    self._workers.pop(str(attempt.attempt_id), None)
                    settled = self._finish_not_started(attempt)
                    latest = self._load(self._row(attempt_id)).attempt
                    if (settled is not None and settled.state != "settled"
                            and latest is not None
                            and latest.state not in {"completed", "failed", "settled", "outcome_unknown"}):
                        self._mark_unknown(latest)
                    return
                time.sleep(0.05)
            # Only settle and terminate the helper if it has not atomically
            # registered itself. If registration won the database race, leave
            # that exact owner running so it can either spawn under the same
            # transaction fence or reconcile cancellation.
            settled = self._finish_not_started(attempt)
            if settled is not None and settled.state == "settled":
                worker.terminate()
                try:
                    worker.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait(timeout=2)
                self._workers.pop(str(attempt.attempt_id), None)

    def _reap_worker(self, attempt_id):
        worker = self._workers.get(str(attempt_id))
        if worker is not None and worker.poll() is not None:
            self._workers.pop(str(attempt_id), None)

    def _worker_environment(self):
        import sys
        return _credential_free_environment() | {
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(sys.path),
            "CODEX_HOME": str(self.codex_home),
        }
