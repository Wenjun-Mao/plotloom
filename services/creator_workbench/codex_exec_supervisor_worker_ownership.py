"""Attempt-scoped worker claims, process ownership and launch."""
from __future__ import annotations

import logging
import os
import subprocess
import time
from contextlib import closing
from pathlib import Path
from queue import Queue
from threading import Thread

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_auth import (
    credential_free_environment as _credential_free_environment,
)

logger = logging.getLogger(__name__)


class _WorkerExitReaper:
    """Allocate the waiter before a child can exist; wait only for that Popen."""

    def __init__(self, on_exit):
        self._spawn_result = Queue(maxsize=1)
        self._on_exit = on_exit
        self._thread = Thread(target=self._wait, name="plotloom-codex-helper-reaper", daemon=True)

    def start(self):
        self._thread.start()

    def spawned(self, worker):
        self._spawn_result.put(worker)

    def _wait(self):
        worker = self._spawn_result.get()
        if worker is None:
            return
        try:
            worker.wait()
        except OSError as error:
            # Failed wait is not absence. Keep the exact child handle and all
            # durable attempt facts; the failure must remain visible.
            logger.error("Codex Exec helper wait failed (%s); exact child handle retained", type(error).__name__)
            return
        self._on_exit(worker)


class CodexExecSupervisorWorkerOwnershipMixin:
    def _register_worker(self, attempt_id):
        """Persist the attempt-scoped worker identity before it can launch Codex."""
        self._namespace_assert_attempt(attempt_id=attempt_id, check_profile=True)
        pid = os.getpid()
        group_id, birth_identity = self._process_identity(pid)
        if group_id != pid:
            raise CodexExecSupervisorError("Codex Exec worker must own its isolated process group")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._namespace_assert_connection(connection)
            row = connection.execute(
                "SELECT status_json,worker_pid,worker_group_id,worker_birth_identity "
                "FROM exec_attempts WHERE attempt_id=?", (str(attempt_id),)
            ).fetchone()
            if row is None:
                connection.rollback()
                raise CodexExecSupervisorError("Codex Exec worker has no durable attempt reservation")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            attempt = CodexExecAttempt.model_validate_json(row["status_json"])
            if attempt.state not in {"spawn_intent", "running", "validating", "cancel_requested"}:
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
        self._namespace_assert_attempt(attempt_id=attempt_id, check_profile=True)
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
        self._namespace_assert_attempt(attempt_id=attempt_id, check_profile=True)
        with self._guard:
            row = self._row(attempt_id)
            if row is None:
                raise CodexExecSupervisorError("Codex Exec attempt disappeared before worker start")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            attempt = CodexExecAttempt.model_validate_json(row["status_json"])
            if attempt.state != "spawn_intent":
                return
            if not self._dispatch_enabled(attempt_id):
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
            if self._namespace is not None:
                command.extend(["--namespace-binding-sha256", self._namespace_sha256])
            reaper = self._start_worker_reaper(attempt.attempt_id)
            worker = None
            try:
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
            finally:
                # Popen failure must also release the preallocated waiter.
                # Success keeps reaping independent of bridge/RPC lifetime.
                reaper.spawned(worker)
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
                    current_attempt = self._load(current).attempt
                    if current_attempt.state == "queued":
                        return
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
            if self._load(self._row(attempt_id)).state == "queued":
                return
            settled = self._finish_not_started(attempt)
            if settled is not None and settled.state == "settled":
                worker.terminate()
                try:
                    worker.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait(timeout=2)
                self._workers.pop(str(attempt.attempt_id), None)

    def _start_worker_reaper(self, attempt_id):
        reaper = _WorkerExitReaper(lambda worker: self._forget_reaped_worker(attempt_id, worker))
        reaper.start()
        return reaper

    def _forget_reaped_worker(self, attempt_id, worker):
        if worker.returncode is None:
            raise CodexExecSupervisorError("cannot forget an un-reaped helper")
        with self._guard:
            if self._workers.get(str(attempt_id)) is worker:
                self._workers.pop(str(attempt_id))

    def _worker_environment(self):
        import sys
        return _credential_free_environment() | {
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(sys.path),
            "CODEX_HOME": str(self.codex_home),
        }
