"""Durable, single-slot owner for local Codex Exec processes."""
from __future__ import annotations

import os
import signal
import stat
import subprocess
import threading
import time
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from uuid import UUID


from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_job import CodexExecSupervisorJobMixin
from codex_exec_supervisor_ledger import CodexExecSupervisorLedgerMixin
from codex_exec_supervisor_process import (
    CodexExecSupervisorProcessMixin,
    _credential_free_environment,
)


class CodexExecSupervisor(
    CodexExecSupervisorProcessMixin,
    CodexExecSupervisorJobMixin,
    CodexExecSupervisorLedgerMixin,
):
    def __init__(self, executable: Path, *, source_root: Path, outputs_root: Path, private_root: Path):
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
        return build_codex_exec_profile(self.executable, source_root=self.source_root)

    def admit(self, raw_attempt):
        from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecProfile
        attempt = CodexExecAttempt.model_validate(raw_attempt)
        if attempt.state != "spawn_intent":
            raise CodexExecSupervisorError("Codex Exec admission requires the persisted spawn-intent snapshot")
        with self._guard:
            existing = self._row(attempt.attempt_id)
            if existing is not None:
                prior = CodexExecAttempt.model_validate_json(existing["attempt_json"])
                if self._identity(prior) != self._identity(attempt):
                    raise CodexExecSupervisorError("Codex Exec attempt ID was reused with different frozen identity")
                status = self._refresh_active_attempt(existing)
                existing = self._row(attempt.attempt_id)
                self._ensure_manifest(existing, status)
                return self._load(self._row(attempt.attempt_id))

            profile = self.profile()
            profile = CodexExecProfile.model_validate(profile)
            home, job_root = self._resolve_job(attempt)
            self._verify_attempt_package(attempt, job_root, profile)
            from plotloom.codex_exec_files import assert_empty_directory
            assert_empty_directory(job_root, "delivery")
            private_dir = self.private_root / "attempts" / str(attempt.attempt_id)
            private_dir.parent.mkdir(mode=0o700, exist_ok=True)
            status_json = attempt.model_dump_json(by_alias=True)
            private_dir_created = False
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                duplicate = connection.execute(
                    "SELECT attempt_id FROM exec_attempts WHERE project_id=? AND job_id=?",
                    (str(attempt.project_id), attempt.job_id),
                ).fetchone()
                if duplicate is not None:
                    connection.rollback()
                    raise CodexExecSupervisorError("immutable Codex Exec job already has a host attempt")
                slot = connection.execute("SELECT attempt_id FROM exec_slot WHERE slot_id=1").fetchone()
                if slot is not None:
                    connection.rollback()
                    raise CodexExecSupervisorError("Mac Codex Exec process slot is already occupied")
                try:
                    # Allocate attempt-private state only after the durable host
                    # slot is known to be free, so a busy refusal leaves no
                    # path that can poison a later same-attempt admission.
                    private_dir.mkdir(mode=0o700)
                    private_dir_created = True
                    (private_dir / "codex-home").mkdir(mode=0o700)
                    connection.execute(
                        "INSERT INTO exec_attempts "
                        "(attempt_id,project_id,job_id,attempt_json,status_json,receipt_json,manifest_json,"
                        "project_home,job_root,private_dir,worker_pid,worker_group_id,worker_birth_identity,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (str(attempt.attempt_id), str(attempt.project_id), attempt.job_id,
                         status_json, status_json, None, None, str(home), str(job_root),
                         str(private_dir), None, None, None, time.time()),
                    )
                    connection.execute("INSERT INTO exec_slot VALUES (1,?)", (str(attempt.attempt_id),))
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    if private_dir_created:
                        self._remove_empty_private_attempt_dir(private_dir)
                    raise
            self._start_worker(attempt.attempt_id)
            return self._load(self._row(attempt.attempt_id))

    def status(self, attempt_id):
        row = self._row(UUID(str(attempt_id)))
        if row is None:
            return self._status()
        attempt = self._refresh_active_attempt(row)
        row = self._row(attempt.attempt_id)
        self._ensure_manifest(row, attempt)
        return self._load(self._row(attempt.attempt_id))

    def _refresh_active_attempt(self, row):
        from plotloom.codex_exec_contracts import CodexExecAttempt
        attempt = CodexExecAttempt.model_validate_json(row["status_json"])
        if attempt.state not in {"spawn_intent", "running", "cancel_requested"}:
            return attempt
        if row["worker_pid"] is None:
            if attempt.state == "spawn_intent":
                self._start_worker(attempt.attempt_id)
            elif attempt.state == "cancel_requested" and attempt.process_id is None:
                self._finish_not_started(attempt)
            return CodexExecAttempt.model_validate_json(self._row(attempt.attempt_id)["status_json"])
        if not self._owns_worker(row):
            return self._mark_unknown(attempt)
        worker = self._workers.get(str(attempt.attempt_id))
        if worker is not None and worker.poll() is not None:
            self._workers.pop(str(attempt.attempt_id), None)
        return attempt

    @staticmethod
    def _remove_empty_private_attempt_dir(private_dir):
        codex_home = private_dir / "codex-home"
        if codex_home.is_dir() and not codex_home.is_symlink() and not any(codex_home.iterdir()):
            codex_home.rmdir()
        if private_dir.is_dir() and not private_dir.is_symlink() and not any(private_dir.iterdir()):
            private_dir.rmdir()

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
        self._run(attempt, profile, package_request, job_root, private_dir)

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

    @staticmethod
    def _worker_environment():
        import sys
        return _credential_free_environment() | {
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(sys.path),
        }

    def cancel(self, raw_attempt):
        from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
        attempt = CodexExecAttempt.model_validate(raw_attempt)
        attempt_id = attempt.attempt_id
        with self._guard:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt_id),)
                ).fetchone()
                if row is None:
                    if attempt.state in {"reserved", "spawn_intent"}:
                        status_attempt = transition_exec_attempt(
                            attempt,
                            state="settled",
                            terminal_result="not_started",
                            remote_tool_state="not_applicable",
                            evidence_hash=sha256(
                                f"plotloom.codex-exec.not-started.v1:{attempt_id}".encode()
                            ).hexdigest(),
                            image_budget_state="released" if attempt.domain == "image" else "none",
                        )
                    elif attempt.state in {"running", "outcome_unknown", "cancel_requested"}:
                        # Missing host state cannot prove that a process or
                        # remote operation never started.
                        status_attempt = transition_exec_attempt(attempt, state="outcome_unknown")
                    else:
                        connection.rollback()
                        raise CodexExecSupervisorError(
                            "Codex Exec cancellation has no host record for a terminal attempt"
                        )
                    connection.execute(
                        "INSERT INTO exec_attempts "
                        "(attempt_id,project_id,job_id,attempt_json,status_json,receipt_json,manifest_json,"
                        "project_home,job_root,private_dir,worker_pid,worker_group_id,worker_birth_identity,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            str(attempt_id),
                            str(attempt.project_id),
                            attempt.job_id,
                            attempt.model_dump_json(by_alias=True),
                            status_attempt.model_dump_json(by_alias=True),
                            None,
                            None,
                            "",
                            "",
                            "",
                            None,
                            None,
                            None,
                            time.time(),
                        ),
                    )
                    if status_attempt.state == "outcome_unknown":
                        slot = connection.execute(
                            "SELECT attempt_id FROM exec_slot WHERE slot_id=1"
                        ).fetchone()
                        if slot is not None:
                            connection.rollback()
                            raise CodexExecSupervisorError(
                                "Mac Codex Exec process slot is occupied while an unrecorded attempt is unknown"
                            )
                        connection.execute("INSERT INTO exec_slot VALUES (1,?)", (str(attempt_id),))
                    connection.commit()
                    return self._status(status_attempt)

                original = CodexExecAttempt.model_validate_json(row["attempt_json"])
                if self._identity(original) != self._identity(attempt):
                    connection.rollback()
                    raise CodexExecSupervisorError(
                        "Codex Exec cancellation identity differs from the admitted attempt"
                    )
                current = CodexExecAttempt.model_validate_json(row["status_json"])
                if current.state in {"completed", "failed", "settled"}:
                    connection.commit()
                    return self._load(row)
                if current.state == "outcome_unknown":
                    connection.commit()
                    attempt = current
                else:
                    if current.process_id is None and row["worker_pid"] is None:
                        current = self._settle_not_started_in_transaction(
                            connection, row, current
                        )
                        if current.state == "settled":
                            connection.commit()
                            return self._status(current)
                    if current.state != "cancel_requested":
                        current = transition_exec_attempt(current, state="cancel_requested")
                        self._persist_status_in_transaction(connection, current)
                    connection.commit()
                    attempt = current

            if attempt.process_id is not None:
                if not self._owns_process(attempt):
                    return self._load(self._row(attempt_id))
                try:
                    os.killpg(attempt.process_group_id, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            return self._load(self._row(attempt_id))

    def _mark_unknown(self, attempt, *, session_id=None):
        from plotloom.codex_exec_contracts import transition_exec_attempt
        if attempt.state in {"completed", "failed", "settled"}:
            return attempt
        changes = {}
        if attempt.state != "outcome_unknown":
            changes["state"] = "outcome_unknown"
        if session_id is not None:
            if attempt.session_id is not None and attempt.session_id != session_id:
                raise CodexExecSupervisorError("Codex Exec unknown settlement conflicts with its session identity")
            if attempt.session_id is None:
                changes["session_id"] = session_id
        if not changes:
            return attempt
        updated = transition_exec_attempt(attempt, **changes)
        self._store(updated)
        return self._load(self._row(attempt.attempt_id)).attempt

    def _ensure_manifest(self, row, attempt):
        if row is None or not row["manifest_json"] or attempt.state != "completed":
            return
        job_root = Path(row["job_root"])
        delivery = job_root / "delivery"
        expected = row["manifest_json"].encode("utf-8")
        marker = delivery / "completion.json"
        if marker.exists() or marker.is_symlink():
            if marker.is_symlink() or self._read_regular(marker, max_bytes=1_000_000) != expected:
                raise CodexExecSupervisorError("Codex Exec completion marker differs from its private host manifest")
            return
        descriptor = os.open(delivery, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            marker_fd = os.open("completion.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=descriptor)
            with os.fdopen(marker_fd, "wb") as output:
                output.write(expected)
                output.flush()
                os.fsync(output.fileno())
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _owns_process(self, attempt):
        try:
            identity = self._process_identity(attempt.process_id)
        except (OSError, subprocess.SubprocessError, ValueError):
            return False
        return identity == (attempt.process_group_id, attempt.process_birth_identity)

    @staticmethod
    def _process_identity(pid):
        start = subprocess.run(["/bin/ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, timeout=2, check=True).stdout.decode().strip()
        group = int(subprocess.run(["/bin/ps", "-o", "pgid=", "-p", str(pid)], capture_output=True, timeout=2, check=True).stdout.decode().strip())
        command = subprocess.run(["/bin/ps", "-o", "command=", "-p", str(pid)], capture_output=True, timeout=2, check=True).stdout.decode().strip()
        if not start or not command:
            raise ProcessLookupError(pid)
        return group, f"{start}|{sha256(command.encode()).hexdigest()[:32]}"
