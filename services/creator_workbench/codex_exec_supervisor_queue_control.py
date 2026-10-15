"""Exact pause authorization and proven pre-spawn parking for queued work."""
from __future__ import annotations

import time
from contextlib import closing

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt


class CodexExecSupervisorQueueControlMixin:
    def suspend(self, raw_attempt):
        return self._set_queue_authorization(raw_attempt, enabled=False)

    def resume(self, raw_attempt):
        return self._set_queue_authorization(raw_attempt, enabled=True)

    def _set_queue_authorization(self, raw_attempt, *, enabled):
        attempt = CodexExecAttempt.model_validate(raw_attempt)
        self._namespace_assert_attempt(attempt, check_profile=enabled)
        granted = None
        if not enabled and self._row(attempt.attempt_id) is None and attempt.state == "spawn_intent":
            # Fence an in-flight initial admission by retaining this exact
            # frozen job as inactive. A later admit cannot reenable it.
            self._admit_with_authorization(attempt, enabled=False)
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute("SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
                if row is None:
                    connection.rollback()
                    return self._status()
                original = CodexExecAttempt.model_validate_json(row["attempt_json"])
                if self._identity(original) != self._identity(attempt):
                    raise CodexExecSupervisorError("queue authorization changed immutable attempt identity")
                current = CodexExecAttempt.model_validate_json(row["status_json"])
                if current.state not in {"queued", "spawn_intent"}:
                    connection.commit()
                    return self._load(row)
                queue = connection.execute("SELECT enabled FROM exec_queue WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
                if queue is None:
                    raise CodexExecSupervisorError("unstarted attempt has no durable queue authorization")
                connection.execute("UPDATE exec_queue SET enabled=? WHERE attempt_id=?", (int(enabled), str(attempt.attempt_id)))
                if not enabled and current.state == "spawn_intent":
                    self._park_before_spawn_in_transaction(connection, row, current)
                if enabled:
                    granted = self._grant_one_in_transaction(connection)
                    if self._pending_queue_count(connection) > self.pool_limits.max_queued_jobs:
                        connection.rollback()
                        return self._status(current, capacity_deferred=True, dispatch_enabled=bool(queue["enabled"]))
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        if granted is not None:
            self._start_worker(granted)
        return self._load(self._row(attempt.attempt_id))

    def _park_before_spawn_in_transaction(self, connection, row, attempt, *, worker_identity=None):
        """Only no registration or the executing worker's own branch proves no spawn."""
        if attempt.state != "spawn_intent" or attempt.process_id is not None:
            return False
        queue = connection.execute("SELECT enabled FROM exec_queue WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
        if queue is None or queue["enabled"]:
            return False
        observed = (row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"])
        if worker_identity is None:
            if observed != (None, None, None):
                return False
        elif observed != worker_identity:
            return False
        validation = connection.execute("SELECT attempt_id FROM exec_validation_process WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
        if validation is not None:
            raise CodexExecSupervisorError("pre-spawn parking cannot discard a validator intent")
        parked = transition_exec_attempt(attempt, state="queued")
        self._persist_status_in_transaction(connection, parked)
        connection.execute("DELETE FROM exec_slot WHERE attempt_id=?", (str(attempt.attempt_id),))
        connection.execute("UPDATE exec_attempts SET worker_pid=NULL,worker_group_id=NULL,worker_birth_identity=NULL,updated_at=? WHERE attempt_id=?", (time.time(), str(attempt.attempt_id)))
        return True
