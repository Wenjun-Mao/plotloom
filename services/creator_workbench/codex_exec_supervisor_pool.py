"""Durable FIFO grants and installation/domain capacity for immutable jobs."""
from __future__ import annotations

from contextlib import closing

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits


class CodexExecSupervisorPoolMixin:
    def _initialize_pool(self, connection):
        connection.execute("BEGIN IMMEDIATE")
        try:
            schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='exec_slot'"
            ).fetchone()
            legacy = []
            if schema is not None and "slot_id" in schema["sql"]:
                slots = connection.execute("SELECT attempt_id FROM exec_slot").fetchall()
                for slot in slots:
                    row = connection.execute("SELECT * FROM exec_attempts WHERE attempt_id=?", (slot["attempt_id"],)).fetchone()
                    if row is None:
                        raise CodexExecSupervisorError("held private capacity has no immutable attempt")
                    attempt = self._held_attempt(row)
                    groups = (row["worker_group_id"], attempt.process_group_id)
                    if any(group is not None and self._process_group_exists(group) for group in groups):
                        raise CodexExecSupervisorError("private pool conversion requires local process quiescence")
                    validation = connection.execute("SELECT * FROM exec_validation_process WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchone()
                    if validation is not None:
                        # Validators own separate process groups. An unresolved
                        # spawn intent supplies no quiescence proof, even when
                        # both the worker and original CLI groups are gone.
                        if validation["spawn_state"] == "spawn_intent" or (
                            validation["process_group_id"] is None
                            or self._process_group_exists(validation["process_group_id"])
                        ):
                            raise CodexExecSupervisorError("private pool conversion requires resolved validator quiescence")
                    legacy.append((str(attempt.attempt_id), attempt.domain))
                connection.execute("ALTER TABLE exec_slot RENAME TO exec_slot_serial")
            connection.execute("""CREATE TABLE IF NOT EXISTS exec_slot (
                attempt_id TEXT PRIMARY KEY REFERENCES exec_attempts(attempt_id),
                domain TEXT NOT NULL CHECK (domain IN ('text','image'))
            )""")
            if schema is not None and "slot_id" in schema["sql"]:
                connection.executemany("INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)", legacy)
                connection.execute("DROP TABLE exec_slot_serial")
            connection.execute("""CREATE TABLE IF NOT EXISTS exec_queue (
                ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id TEXT UNIQUE NOT NULL REFERENCES exec_attempts(attempt_id),
                enabled INTEGER NOT NULL CHECK (enabled IN (0,1))
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS exec_pool_configuration (
                identity INTEGER PRIMARY KEY CHECK (identity = 1),
                version TEXT NOT NULL,
                limits_json TEXT NOT NULL
            )""")
            saved = connection.execute("SELECT * FROM exec_pool_configuration WHERE identity=1").fetchone()
            requested = self._requested_pool_limits
            if saved is None:
                limits = CodexExecPoolLimits.model_validate(requested or CodexExecPoolLimits())
                connection.execute("INSERT INTO exec_pool_configuration VALUES (1,?,?)",
                    ("plotloom.exec-pool.v1", limits.model_dump_json(by_alias=True)))
            else:
                if saved["version"] != "plotloom.exec-pool.v1":
                    raise CodexExecSupervisorError("unsupported private pool configuration")
                limits = CodexExecPoolLimits.model_validate_json(saved["limits_json"])
                if requested is not None and CodexExecPoolLimits.model_validate(requested) != limits:
                    raise CodexExecSupervisorError("persisted pool limits cannot change during an installation")
            connection.commit()
            self.pool_limits = limits
        except BaseException:
            connection.rollback()
            raise

    def _held_attempt(self, row):
        original = CodexExecAttempt.model_validate_json(row["attempt_json"])
        current = CodexExecAttempt.model_validate_json(row["status_json"])
        if self._identity(original) != self._identity(current):
            raise CodexExecSupervisorError("private capacity immutable identity differs")
        if current.state not in {"spawn_intent", "running", "validating", "outcome_unknown", "cancel_requested"}:
            raise CodexExecSupervisorError("capacity must belong to unsettled work")
        return current

    def _capacity_counts(self, connection):
        counts = {"text": 0, "image": 0}
        rows = connection.execute("SELECT s.domain,a.* FROM exec_slot s JOIN exec_attempts a ON a.attempt_id=s.attempt_id").fetchall()
        for row in rows:
            attempt = self._held_attempt(row)
            if attempt.domain != row["domain"]:
                raise CodexExecSupervisorError("private capacity domain differs from its attempt")
            counts[attempt.domain] += 1
        return counts

    @staticmethod
    def _pending_queue_count(connection):
        return connection.execute("""SELECT COUNT(*) FROM exec_queue q JOIN exec_attempts a ON a.attempt_id=q.attempt_id
            WHERE q.enabled=1 AND json_extract(a.status_json,'$.state')='queued'""").fetchone()[0]

    def _grant_one_in_transaction(self, connection):
        self._namespace_assert_connection(connection)
        if not self._qualification_new_work(connection):
            return None
        counts = self._capacity_counts(connection)
        if sum(counts.values()) >= self.pool_limits.max_processes:
            return None
        rows = connection.execute("""SELECT a.* FROM exec_queue q JOIN exec_attempts a ON a.attempt_id=q.attempt_id
            WHERE q.enabled=1 AND json_extract(a.status_json,'$.state')='queued' ORDER BY q.ordinal""").fetchall()
        for row in rows:
            attempt = CodexExecAttempt.model_validate_json(row["status_json"])
            if not self._qualification_new_work(connection, attempt):
                return None
            if counts[attempt.domain] >= self.pool_limits.domain_capacity(attempt.domain):
                continue
            if any(row[name] is not None for name in ("worker_pid", "worker_group_id", "worker_birth_identity")):
                raise CodexExecSupervisorError("queued work cannot acquire a replacement for a registered worker")
            granted = transition_exec_attempt(attempt, state="spawn_intent")
            connection.execute("INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)", (str(attempt.attempt_id), attempt.domain))
            self._persist_status_in_transaction(connection, granted)
            return attempt.attempt_id
        return None

    def _drain_queue(self):
        self._namespace_assert_attempt(check_profile=True)
        with self._guard:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    granted = self._grant_one_in_transaction(connection)
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
            if granted is not None:
                self._start_worker(granted)
            return granted

    def _dispatch_enabled(self, attempt_id):
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT enabled FROM exec_queue WHERE attempt_id=?", (str(attempt_id),)).fetchone()
            return bool(row["enabled"]) if row is not None else None

    @staticmethod
    def _reserve_unknown_capacity(connection, attempt):
        # A newly reported missing-host outcome is uncertainty, not a new launch.
        # Retain even an over-cap hold; ordinary grants then remain fenced.
        connection.execute("INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)", (str(attempt.attempt_id), attempt.domain))

    @staticmethod
    def _forget_terminal_queue(connection, attempt_id):
        connection.execute("DELETE FROM exec_queue WHERE attempt_id=?", (str(attempt_id),))
