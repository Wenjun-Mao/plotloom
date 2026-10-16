"""Immutable host admission and exact-status reconciliation."""
from __future__ import annotations

import signal
import time
from contextlib import closing
from uuid import UUID

from codex_exec_supervisor_errors import CodexExecSupervisorError


class CodexExecSupervisorAdmissionMixin:
    def admit(self, raw_attempt):
        return self._admit_with_authorization(raw_attempt, enabled=True)

    def _admit_with_authorization(self, raw_attempt, *, enabled):
        from plotloom.codex_exec_contracts import (
            CodexExecAttempt,
            CodexExecProfile,
            transition_exec_attempt,
        )
        attempt = CodexExecAttempt.model_validate(raw_attempt)
        self._namespace_assert_attempt(attempt, check_profile=True)
        if attempt.state != "spawn_intent":
            raise CodexExecSupervisorError("Codex Exec admission requires the persisted spawn-intent snapshot")
        with self._guard:
            existing = self._row(attempt.attempt_id)
            if existing is not None:
                prior = CodexExecAttempt.model_validate_json(existing["attempt_json"])
                if self._identity(prior) != self._identity(attempt):
                    raise CodexExecSupervisorError("Codex Exec attempt ID was reused with different frozen identity")
                status = self._refresh_active_attempt(existing) if enabled else self._load(existing).attempt
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
            original_json = attempt.model_dump_json(by_alias=True)
            queued = transition_exec_attempt(attempt, state="queued")
            private_dir_created = False
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                duplicate = connection.execute(
                    "SELECT * FROM exec_attempts WHERE project_id=? AND job_id=?",
                    (str(attempt.project_id), attempt.job_id),
                ).fetchone()
                if duplicate is not None:
                    connection.rollback()
                    prior = CodexExecAttempt.model_validate_json(duplicate["attempt_json"])
                    if self._identity(prior) == self._identity(attempt):
                        return self._load(duplicate)
                    raise CodexExecSupervisorError("immutable Codex Exec job already has a host attempt")
                if not self._qualification_admission(connection, attempt, enabled=enabled):
                    connection.commit()
                    raise CodexExecSupervisorError("qualification arm held before admission")
                try:
                    # The tentative queue insertion and oldest eligible grant
                    # share one transaction. A full queue rolls both back and
                    # leaves no private path poisoning a later exact admission.
                    private_dir.mkdir(mode=0o700)
                    private_dir_created = True
                    connection.execute(
                        "INSERT INTO exec_attempts "
                        "(attempt_id,project_id,job_id,attempt_json,status_json,receipt_json,manifest_json,"
                        "project_home,job_root,private_dir,worker_pid,worker_group_id,worker_birth_identity,updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (str(attempt.attempt_id), str(attempt.project_id), attempt.job_id,
                         original_json, queued.model_dump_json(by_alias=True), None, None, str(home), str(job_root),
                         str(private_dir), None, None, None, time.time()),
                    )
                    connection.execute("INSERT INTO exec_queue(attempt_id,enabled) VALUES (?,?)", (str(attempt.attempt_id), int(enabled)))
                    granted = self._grant_one_in_transaction(connection) if enabled else None
                    if self._pending_queue_count(connection) > self.pool_limits.max_queued_jobs:
                        connection.rollback()
                        self._remove_empty_private_attempt_dir(private_dir)
                        return self._status(capacity_deferred=True)
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    if private_dir_created:
                        self._remove_empty_private_attempt_dir(private_dir)
                    raise
            if granted is not None:
                self._start_worker(granted)
            return self._load(self._row(attempt.attempt_id))

    def status(self, attempt_id):
        self._namespace_assert_attempt(attempt_id=attempt_id, check_profile=True)
        row = self._row(UUID(str(attempt_id)))
        if row is None:
            return self._status()
        attempt = self._refresh_active_attempt(row)
        # Reconnecting an already granted helper consumes this operation's
        # single launch allowance; otherwise grant one FIFO continuation.
        if row["worker_pid"] is not None or self._load(row).state != "spawn_intent":
            self._drain_queue()
        row = self._row(attempt.attempt_id)
        self._ensure_manifest(row, attempt)
        return self._load(self._row(attempt.attempt_id))

    def _refresh_active_attempt(self, row):
        from plotloom.codex_exec_contracts import CodexExecAttempt
        attempt = CodexExecAttempt.model_validate_json(row["status_json"])
        self._namespace_assert_attempt(attempt, check_profile=True)
        if attempt.state == "outcome_unknown":
            validation = self._active_validation_process(attempt.attempt_id)
            if validation is not None and validation["spawn_state"] == "running" and self._owns_validation_process(validation):
                self._terminate_active_validation(attempt.attempt_id, sig=signal.SIGKILL)
            return attempt
        if attempt.state not in {"spawn_intent", "running", "validating", "cancel_requested"}:
            return attempt
        validation = self._active_validation_process(attempt.attempt_id)
        if validation is not None and not self._owns_worker(row):
            if validation["spawn_state"] == "running" and self._owns_validation_process(validation):
                self._terminate_active_validation(attempt.attempt_id, sig=signal.SIGKILL)
            return self._mark_unknown(attempt)
        if row["worker_pid"] is None:
            if attempt.state == "spawn_intent" and self._dispatch_enabled(attempt.attempt_id):
                self._start_worker(attempt.attempt_id)
            elif attempt.state == "cancel_requested" and attempt.process_id is None:
                self._finish_not_started(attempt)
            return CodexExecAttempt.model_validate_json(self._row(attempt.attempt_id)["status_json"])
        if not self._owns_worker(row):
            return self._mark_unknown(attempt)
        return attempt

    @staticmethod
    def _remove_empty_private_attempt_dir(private_dir):
        if private_dir.is_dir() and not private_dir.is_symlink() and not any(private_dir.iterdir()):
            private_dir.rmdir()
