"""Session leases and scoped atomic run commands for the project composition."""
from __future__ import annotations
from collections.abc import Iterator
from contextlib import contextmanager
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from ...domain import utc_now
from ...exceptions import InvalidTransitionError
from ..transactions import bootstrap_lease, lifecycle_lease, read_lease, work_unit_claim_lease, write_lease


class ProjectCommandTransactions:
    @contextmanager
    def _read(self) -> Iterator[Session]:
        command = self._command_context.get()
        if command:
            command[0].flush()
            yield command[0]
            return
        with read_lease(self._sessions) as session:
            yield session

    @contextmanager
    def _write(self) -> Iterator[Session]:
        command = self._command_context.get()
        if command:
            yield command[0]
            return
        with write_lease(self._sessions, self._write_lock) as session:
            yield session

    @contextmanager
    def _bootstrap_write(self) -> Iterator[Session]:
        with bootstrap_lease(self._sessions, self._write_lock, retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            yield session

    @contextmanager
    def _lifecycle_write(self) -> Iterator[Session]:
        command = self._command_context.get()
        if command:
            yield command[0]
            return
        with lifecycle_lease(self._sessions, self._write_lock, dialect_name=self.engine.dialect.name, retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            from .autopilot_closure import material_closure
            run = self.autopilot.row(session, self.project_id)
            before = material_closure(session, self.project_id) if run else None
            yield session
            if run and before != material_closure(session, self.project_id):
                if run.state != "cancelled":
                    run.state = "taken_over"
                run.revision += 1
                run.updated_at = utc_now()
                run.blocker = {"code": "manual_takeover", "message": "手动编辑已接管；自动运行不会覆盖你的修改。"}

    @contextmanager
    def autopilot_command(self, authority):
        """Atomic existing-owner command plus run evidence, scoped to this handle."""
        if self._command_context.get() is not None:
            raise InvalidTransitionError("autopilot commands cannot nest")
        with lifecycle_lease(self._sessions, self._write_lock, dialect_name=self.engine.dialect.name,
                retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            run = self.autopilot.validate_command(session, authority)
            from .autopilot_closure import material_closure, MATERIAL_TABLES
            receipt_tables = tuple(name for name in MATERIAL_TABLES if name != "v2_managed_assets")
            protected_before = material_closure(session, self.project_id, tables=receipt_tables)
            session.info["autopilot_run_id"] = run.id
            token = self._command_context.set((session, authority))
            try:
                yield session
                from .autopilot_closure import material_closure
                if authority.scope.value == "receipt_reconciliation" and protected_before != material_closure(session, self.project_id, tables=receipt_tables):
                    raise InvalidTransitionError("receipt reconciliation cannot change creative or human authority")
                if authority.scope.value != "receipt_reconciliation" or run.state in {"running", "waiting"}:
                    run.expected_closure = material_closure(session, self.project_id)
                run.revision += 1
                run.updated_at = utc_now()
            finally:
                self._command_context.reset(token)

    @contextmanager
    def _work_unit_claim_write(self) -> Iterator[Session]:
        with work_unit_claim_lease(self._sessions, self._write_lock, is_contention=self._is_sqlite_lock_contention) as session:
            yield session

    @staticmethod
    def _is_sqlite_lock_contention(error: OperationalError) -> bool:
        message = str(error).lower()
        return "database is locked" in message or "database table is locked" in message
