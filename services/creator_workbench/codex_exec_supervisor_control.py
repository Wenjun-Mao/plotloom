"""Exact cancellation, unknown holds and settled manifest publication."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorControlMixin:
    def cancel(self, raw_attempt):
        from plotloom.codex_exec_contracts import (
            CodexExecAttempt,
            transition_exec_attempt,
        )
        attempt = CodexExecAttempt.model_validate(raw_attempt)
        self._namespace_assert_attempt(attempt)
        attempt_id = attempt.attempt_id
        with self._guard:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt_id),)
                ).fetchone()
                if row is None:
                    if attempt.state in {"reserved", "queued", "spawn_intent"}:
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
                    elif attempt.state in {"running", "validating", "outcome_unknown", "cancel_requested"}:
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
                        self._reserve_unknown_capacity(connection, status_attempt)
                    self._qualification_terminal(connection,status_attempt)
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

            if attempt.process_id is not None and self._owns_process(attempt):
                try:
                    os.killpg(attempt.process_group_id, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            validation = self._active_validation_process(attempt_id)
            if validation is not None:
                worker_row = self._row(attempt_id)
                if worker_row is None or not self._owns_worker(worker_row):
                    self._mark_unknown(attempt)
                    return self._load(self._row(attempt_id))
                if validation["spawn_state"] == "running":
                    if not self._owns_validation_process(validation):
                        self._mark_unknown(attempt)
                    else:
                        self._terminate_active_validation(attempt_id, sig=signal.SIGTERM)
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
