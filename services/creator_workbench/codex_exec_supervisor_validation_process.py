"""Durable subprocess ownership and cancellation for trusted text validators."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from contextlib import closing

from codex_exec_supervisor_errors import (
    CodexExecSupervisorError,
    CodexExecValidationOwnershipUnknown,
)


class CodexExecSupervisorValidationProcessMixin:
    def _spawn_validation_process(self, attempt, step_id, command, environment, cwd, stdout, stderr):
        self._record_validation_spawn_intent(attempt, step_id)
        if not self._validation_launch_is_allowed(attempt, step_id):
            raise self._validation_failure(
                "validation_cancelled_before_spawn", attempt.validation_plan_hash,
            )

        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
        except OSError:
            # Popen reports exec/setup errors only after reaping its child.
            # The durable intent can therefore be cleared for this known
            # pre-execution failure.
            self._clear_validation_spawn_intent(attempt.attempt_id, step_id)
            raise
        except BaseException as error:
            # Interruption during process creation has no exact child identity
            # to reconcile. Retain the intent so restart cannot launch again.
            raise CodexExecValidationOwnershipUnknown(
                "validator spawn was interrupted before its exact owner was recorded"
            ) from error

        try:
            group_id, birth_identity = self._process_identity(process.pid)
            identity = (process.pid, group_id, birth_identity)
            if group_id != process.pid:
                raise CodexExecValidationOwnershipUnknown(
                    "validator did not create its isolated process group"
                )
            state = self._register_validation_process(attempt, step_id, identity)
        except BaseException as error:
            identity = locals().get("identity")
            if identity is not None:
                self._stop_spawned_validation(process, attempt, step_id, identity)
            else:
                # Popen owns the exact child PID, but without a recorded birth
                # identity its descendants cannot be safely addressed.
                try:
                    process.kill()
                    process.wait(timeout=2)
                except (OSError, subprocess.SubprocessError):
                    pass
            if isinstance(error, CodexExecValidationOwnershipUnknown):
                raise
            raise CodexExecValidationOwnershipUnknown(
                "validator identity could not be durably registered"
            ) from error

        identity = (process.pid, group_id, birth_identity)
        if state != "running":
            # Cancellation may have committed after the launch fence and
            # before registration. The intent retained the race; now that the
            # exact process is durable, stop that exact group immediately.
            self._signal_validation_owner(identity, signal.SIGTERM)
        return process, identity

    def _record_validation_spawn_intent(self, attempt, step_id):
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT attempt_json,status_json,worker_pid,worker_group_id,worker_birth_identity "
                "FROM exec_attempts WHERE attempt_id=?", (str(attempt.attempt_id),),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise CodexExecSupervisorError("validator has no retained project attempt")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            original = CodexExecAttempt.model_validate_json(row["attempt_json"])
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            if self._identity(original) != self._identity(attempt):
                connection.rollback()
                raise CodexExecSupervisorError("validator spawn changed immutable attempt identity")
            expected_worker = (row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"])
            if (current.state != "running" or expected_worker != (
                    os.getpid(), *self._process_identity(os.getpid()))):
                connection.rollback()
                raise self._validation_failure(
                    "validation_cancelled_before_spawn", attempt.validation_plan_hash,
                )
            existing = connection.execute(
                "SELECT attempt_id FROM exec_validation_process WHERE attempt_id=?",
                (str(attempt.attempt_id),),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                raise CodexExecSupervisorError("another trusted validator already owns this attempt")
            connection.execute(
                "INSERT INTO exec_validation_process "
                "(attempt_id,step_id,spawn_state,process_id,process_group_id,process_birth_identity,updated_at) "
                "VALUES (?,?, 'spawn_intent', NULL,NULL,NULL,?)",
                (str(attempt.attempt_id), step_id, time.time()),
            )
            connection.commit()

    def _validation_launch_is_allowed(self, attempt, step_id):
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status_json FROM exec_attempts WHERE attempt_id=?",
                (str(attempt.attempt_id),),
            ).fetchone()
            owner = connection.execute(
                "SELECT step_id,spawn_state FROM exec_validation_process WHERE attempt_id=?",
                (str(attempt.attempt_id),),
            ).fetchone()
            if owner is None or (owner["step_id"], owner["spawn_state"]) != (step_id, "spawn_intent"):
                connection.rollback()
                raise CodexExecSupervisorError("trusted validator lost its durable spawn intent")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            current = CodexExecAttempt.model_validate_json(row["status_json"]) if row else None
            if current is not None and current.state == "running":
                connection.commit()
                return True
            # No child has been started on this path, so the exact intent can
            # be removed before reporting the observed cancellation fence.
            connection.execute(
                "DELETE FROM exec_validation_process WHERE attempt_id=? AND step_id=? AND spawn_state='spawn_intent'",
                (str(attempt.attempt_id), step_id),
            )
            connection.commit()
            return False

    def _register_validation_process(self, attempt, step_id, identity):
        pid, group_id, birth_identity = identity
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            attempt_row = connection.execute(
                "SELECT attempt_json,status_json,worker_pid,worker_group_id,worker_birth_identity "
                "FROM exec_attempts WHERE attempt_id=?",
                (str(attempt.attempt_id),),
            ).fetchone()
            owner = connection.execute(
                "SELECT step_id,spawn_state FROM exec_validation_process WHERE attempt_id=?",
                (str(attempt.attempt_id),),
            ).fetchone()
            if attempt_row is None or owner is None or (owner["step_id"], owner["spawn_state"]) != (
                    step_id, "spawn_intent"):
                connection.rollback()
                raise CodexExecSupervisorError("trusted validator spawn intent disappeared")
            worker_identity = (
                attempt_row["worker_pid"], attempt_row["worker_group_id"],
                attempt_row["worker_birth_identity"],
            )
            expected_worker = (os.getpid(), *self._process_identity(os.getpid()))
            if worker_identity != expected_worker:
                connection.rollback()
                raise CodexExecSupervisorError("validator registration is outside its owning worker")
            from plotloom.codex_exec_contracts import CodexExecAttempt
            original = CodexExecAttempt.model_validate_json(attempt_row["attempt_json"])
            current = CodexExecAttempt.model_validate_json(attempt_row["status_json"])
            if self._identity(original) != self._identity(attempt):
                connection.rollback()
                raise CodexExecSupervisorError("validator registration changed immutable attempt identity")
            cursor = connection.execute(
                "UPDATE exec_validation_process SET spawn_state='running',process_id=?,process_group_id=?,"
                "process_birth_identity=?,updated_at=? WHERE attempt_id=? AND step_id=? AND spawn_state='spawn_intent'",
                (pid, group_id, birth_identity, time.time(), str(attempt.attempt_id), step_id),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise CodexExecSupervisorError("trusted validator spawn intent changed during registration")
            connection.commit()
            return current.state

    def _stop_spawned_validation(self, process, attempt, step_id, identity):
        self._signal_validation_owner(identity, signal.SIGKILL)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired as error:
            raise CodexExecValidationOwnershipUnknown("validator leader did not exit after cleanup") from error
        if not self._wait_for_process_group_exit(identity[1], grace_seconds=2.0):
            raise CodexExecValidationOwnershipUnknown("validator descendants remain after cleanup")
        self._clear_validation_process(
            attempt.attempt_id, step_id, identity=identity, allow_intent=True,
        )

    def _wait_validation_process(
        self, attempt, step_id, process, identity, *, started, timeout_seconds, stdout_path, stderr_path, max_bytes,
    ):
        termination_started = None
        failure_reason = None
        while process.poll() is None:
            now = time.monotonic()
            current = self._load(self._row(attempt.attempt_id)).attempt
            if current is None or current.state == "cancel_requested":
                failure_reason = "validation_cancelled"
                if termination_started is None:
                    self._signal_validation_owner(identity, signal.SIGTERM)
                    termination_started = now
            try:
                output_size = stdout_path.stat().st_size + stderr_path.stat().st_size
            except OSError:
                output_size = max_bytes + 1
                failure_reason = "validation_output_unavailable"
            if output_size > max_bytes:
                failure_reason = "validation_output_limit"
                if termination_started is None:
                    self._signal_validation_owner(identity, signal.SIGTERM)
                    termination_started = now
            if now - started > timeout_seconds:
                failure_reason = "validation_timeout"
                if termination_started is None:
                    self._signal_validation_owner(identity, signal.SIGTERM)
                    termination_started = now
            if termination_started is not None and now - termination_started > 3:
                if process.poll() is None:
                    self._signal_validation_owner(identity, signal.SIGKILL)
                elif self._process_group_exists(identity[1]):
                    raise CodexExecValidationOwnershipUnknown("validator descendants remain after leader exit")
            if process.poll() is None:
                time.sleep(0.1)
        exit_code = process.wait()
        if not self._wait_for_process_group_exit(identity[1], grace_seconds=2.0):
            raise CodexExecValidationOwnershipUnknown("validator descendants remain after leader exit")
        self._clear_validation_process(attempt.attempt_id, step_id, identity=identity)
        if failure_reason is not None:
            raise self._validation_failure(failure_reason, attempt.validation_plan_hash, (stdout_path, stderr_path), exit_code=exit_code)
        return exit_code

    def _signal_validation_owner(self, identity, sig):
        pid, group_id, birth = identity
        if pid != group_id:
            raise CodexExecValidationOwnershipUnknown("validator process group is not its recorded leader")
        try:
            if self._process_identity(pid) != (group_id, birth):
                raise CodexExecValidationOwnershipUnknown("validator leader identity changed before cleanup")
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            if self._process_group_exists(group_id):
                raise CodexExecValidationOwnershipUnknown("validator leader disappeared with descendants still present") from error
            return
        try:
            os.killpg(group_id, sig)
        except ProcessLookupError:
            pass

    def _active_validation_process(self, attempt_id):
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT * FROM exec_validation_process WHERE attempt_id=?", (str(attempt_id),),
            ).fetchone()

    def _clear_validation_process(self, attempt_id, step_id, *, identity, allow_intent=False):
        pid, group_id, birth_identity = identity
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT spawn_state,step_id,process_id,process_group_id,process_birth_identity "
                "FROM exec_validation_process WHERE attempt_id=?",
                (str(attempt_id),),
            ).fetchone()
            matches_running = row is not None and row["spawn_state"] == "running" and (
                row["step_id"], row["process_id"], row["process_group_id"], row["process_birth_identity"],
            ) == (step_id, pid, group_id, birth_identity)
            matches_intent = allow_intent and row is not None and (
                row["spawn_state"], row["step_id"],
            ) == ("spawn_intent", step_id)
            if not (matches_running or matches_intent):
                connection.rollback()
                raise CodexExecValidationOwnershipUnknown("validator owner changed before its intent was cleared")
            connection.execute("DELETE FROM exec_validation_process WHERE attempt_id=?", (str(attempt_id),))
            connection.commit()

    def _clear_validation_spawn_intent(self, attempt_id, step_id):
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM exec_validation_process WHERE attempt_id=? AND step_id=? AND spawn_state='spawn_intent'",
                (str(attempt_id), step_id),
            )
            connection.commit()
            return cursor.rowcount == 1

    def _owns_validation_process(self, row):
        if row is None or row["spawn_state"] != "running" or row["process_id"] is None:
            return False
        try:
            return self._process_identity(row["process_id"]) == (
                row["process_group_id"], row["process_birth_identity"],
            )
        except (OSError, subprocess.SubprocessError, ValueError):
            return False

    def _terminate_active_validation(self, attempt_id, *, sig=signal.SIGTERM):
        row = self._active_validation_process(attempt_id)
        if row is None:
            return False
        if row["spawn_state"] == "spawn_intent":
            return False
        if not self._owns_validation_process(row):
            return False
        try:
            os.killpg(row["process_group_id"], sig)
        except ProcessLookupError:
            pass
        return True

