"""Private SQLite ledger and immutable attempt snapshot operations."""
from __future__ import annotations

import os
import stat
import sqlite3
import time
from contextlib import closing
from hashlib import sha256

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorLedgerMixin:
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self):
        descriptor = os.open(self.database, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        metadata = os.fstat(descriptor)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1):
            os.close(descriptor)
            raise CodexExecSupervisorError("Codex Exec supervisor database is unsafe")
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)
        with closing(self._connect()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS exec_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    attempt_json TEXT NOT NULL,
                    status_json TEXT NOT NULL,
                    receipt_json TEXT,
                    manifest_json TEXT,
                    project_home TEXT NOT NULL,
                    job_root TEXT NOT NULL,
                    private_dir TEXT NOT NULL,
                    worker_pid INTEGER,
                    worker_group_id INTEGER,
                    worker_birth_identity TEXT,
                    updated_at REAL NOT NULL,
                    UNIQUE(project_id, job_id)
                );
                CREATE TABLE IF NOT EXISTS exec_slot (
                    slot_id INTEGER PRIMARY KEY CHECK (slot_id = 1),
                    attempt_id TEXT UNIQUE NOT NULL
                );
            """)

    @staticmethod
    def _status(attempt=None, receipt=None):
        from plotloom.codex_exec_contracts import CodexExecHostStatus
        if attempt is None:
            return CodexExecHostStatus(state="not_found")
        return CodexExecHostStatus(
            state=attempt.state,
            attempt=attempt,
            receipt=receipt,
        )

    @staticmethod
    def _identity(attempt):
        return (
            attempt.attempt_id, attempt.run_id, attempt.project_id, attempt.job_id,
            attempt.operation_key, attempt.domain, attempt.request_hash,
            attempt.package_hash, attempt.profile_hash, attempt.reserved_image_outputs,
        )

    def _row(self, attempt_id):
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt_id),)
            ).fetchone()

    def _load(self, row):
        from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReceipt
        if row is None:
            return self._status()
        attempt = CodexExecAttempt.model_validate_json(row["status_json"])
        receipt = CodexExecReceipt.model_validate_json(row["receipt_json"]) if row["receipt_json"] else None
        return self._status(attempt, receipt)

    def _store(self, attempt, *, receipt=None, manifest_json=None, preserve_manifest=True):
        from plotloom.codex_exec_contracts import (
            CodexExecAttempt,
            transition_exec_attempt,
        )
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        with self._guard, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt.attempt_id),)
            ).fetchone()
            if row is None:
                connection.rollback()
                raise CodexExecSupervisorError("Codex Exec attempt ledger entry disappeared")
            original = CodexExecAttempt.model_validate_json(row["attempt_json"])
            if self._identity(original) != self._identity(attempt):
                connection.rollback()
                raise CodexExecSupervisorError("Codex Exec host update changed immutable attempt identity")
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            if current.state in {"completed", "failed", "settled"}:
                receipt_json = row["receipt_json"]
                selected_manifest = row["manifest_json"]
                if receipt is not None and receipt.model_dump_json(by_alias=True) != receipt_json:
                    connection.rollback()
                    raise CodexExecSupervisorError("Codex Exec host receipt cannot be replaced")
                if manifest_json is not None and manifest_json != selected_manifest:
                    connection.rollback()
                    raise CodexExecSupervisorError("Codex Exec host completion manifest cannot be replaced")
                connection.commit()
                return current

            changes = {}
            for field in (
                "session_id", "process_id", "process_group_id", "process_birth_identity",
                "process_exit_code", "terminal_result", "remote_tool_state", "evidence_hash",
                "output_hash", "remote_output_hash",
            ):
                supplied = getattr(attempt, field)
                observed = getattr(current, field)
                if supplied is None:
                    continue
                if observed is not None and observed != supplied:
                    connection.rollback()
                    raise CodexExecSupervisorError(
                        f"Codex Exec host update conflicts with recorded {field}"
                    )
                if observed is None:
                    changes[field] = supplied
            if attempt.image_budget_state != current.image_budget_state:
                changes["image_budget_state"] = attempt.image_budget_state
            if attempt.state != current.state:
                changes["state"] = attempt.state
            # A cancellation may win the race after Popen but before the worker
            # stores its process identity. Persist that identity while keeping
            # the cancellation fence visible to the worker.
            if current.state == "cancel_requested" and attempt.state == "running":
                changes.pop("state", None)
            updated = transition_exec_attempt(current, **changes) if changes else current
            receipt_json = receipt.model_dump_json(by_alias=True) if receipt is not None else row["receipt_json"]
            if row["receipt_json"] and receipt_json != row["receipt_json"]:
                connection.rollback()
                raise CodexExecSupervisorError("Codex Exec host receipt cannot be replaced")
            selected_manifest = manifest_json if manifest_json is not None else (
                row["manifest_json"] if preserve_manifest else None
            )
            if row["manifest_json"] and selected_manifest != row["manifest_json"]:
                connection.rollback()
                raise CodexExecSupervisorError("Codex Exec host completion manifest cannot be replaced")
            connection.execute(
                "UPDATE exec_attempts SET status_json=?,receipt_json=?,manifest_json=?,updated_at=? WHERE attempt_id=?",
                (updated.model_dump_json(by_alias=True), receipt_json, selected_manifest,
                 time.time(), str(attempt.attempt_id)),
            )
            if updated.state in {"completed", "failed", "settled"}:
                connection.execute("DELETE FROM exec_slot WHERE attempt_id=?", (str(attempt.attempt_id),))
            connection.commit()
            return updated

    def _persist_status_in_transaction(self, connection, attempt):
        connection.execute(
            "UPDATE exec_attempts SET status_json=?,updated_at=? WHERE attempt_id=?",
            (attempt.model_dump_json(by_alias=True), time.time(), str(attempt.attempt_id)),
        )
        if attempt.state in {"completed", "failed", "settled"}:
            connection.execute("DELETE FROM exec_slot WHERE attempt_id=?", (str(attempt.attempt_id),))

    def _settle_not_started_in_transaction(self, connection, row, current, *, worker_identity=None):
        from plotloom.codex_exec_contracts import transition_exec_attempt

        if current.state not in {"reserved", "spawn_intent", "cancel_requested"}:
            return current
        if current.process_id is not None:
            return current
        observed_worker = (
            row["worker_pid"], row["worker_group_id"], row["worker_birth_identity"]
        )
        if worker_identity is None:
            if observed_worker != (None, None, None):
                return current
        elif observed_worker != worker_identity:
            return current
        settled = transition_exec_attempt(
            current,
            state="settled",
            terminal_result="not_started",
            remote_tool_state="not_applicable",
            evidence_hash=sha256(
                f"plotloom.codex-exec.not-started.v1:{current.attempt_id}".encode()
            ).hexdigest(),
            image_budget_state="released" if current.domain == "image" else "none",
        )
        self._persist_status_in_transaction(connection, settled)
        return settled

    def _finish_not_started_if_unspawned(self, attempt, *, worker_identity=None):
        from plotloom.codex_exec_contracts import CodexExecAttempt

        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM exec_attempts WHERE attempt_id=?", (str(attempt.attempt_id),)
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            original = CodexExecAttempt.model_validate_json(row["attempt_json"])
            if self._identity(original) != self._identity(attempt):
                connection.rollback()
                raise CodexExecSupervisorError("not-started settlement changed immutable attempt identity")
            current = CodexExecAttempt.model_validate_json(row["status_json"])
            updated = self._settle_not_started_in_transaction(
                connection, row, current, worker_identity=worker_identity
            )
            connection.commit()
            return updated
