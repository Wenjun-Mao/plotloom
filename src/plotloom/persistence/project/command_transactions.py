"""Session leases and scoped atomic run commands for the project composition."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ...domain import utc_now
from ...exceptions import InvalidTransitionError
from ..transactions import (
    bootstrap_lease,
    lifecycle_lease,
    read_lease,
    work_unit_claim_lease,
    write_lease,
)


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
    def _controller_claim_write(self) -> Iterator[Session]:
        """Claim metadata cannot edit material; enclosing commands still own it."""
        command = self._command_context.get()
        if command:
            yield command[0]
            return
        with lifecycle_lease(self._sessions, self._write_lock, dialect_name=self.engine.dialect.name,
                retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
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
    def manual_command(self):
        """One ordinary human command may compose existing lifecycle owners."""
        if self._command_context.get() is not None:
            raise InvalidTransitionError("project commands cannot nest")
        with self._lifecycle_write() as session:
            token = self._command_context.set((session, None))
            try:
                yield session
            finally:
                self._command_context.reset(token)

    @contextmanager
    def text_retry_command(self):
        """One creator grant and its exact corrective head, without manual takeover.

        grant_text_retry validates the frozen run/CAS/parent before changing the
        sole head. This command adopts that authorized transport-head change into
        the closure atomically; ordinary manual edits still force takeover.
        """
        if self._command_context.get() is not None:
            raise InvalidTransitionError("project commands cannot nest")
        with lifecycle_lease(self._sessions, self._write_lock, dialect_name=self.engine.dialect.name,
                retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            token = self._command_context.set((session, None))
            try:
                yield session
            finally:
                self._command_context.reset(token)

    @contextmanager
    def autopilot_command(self, authority):
        """Atomic existing-owner command plus run evidence, scoped to this handle."""
        if self._command_context.get() is not None:
            raise InvalidTransitionError("autopilot commands cannot nest")
        with lifecycle_lease(self._sessions, self._write_lock, dialect_name=self.engine.dialect.name,
                retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            run = self.autopilot.validate_command(session, authority)
            from .autopilot_closure import _receipt_material_closures, material_closure
            receipt_reconciliation = authority.scope.value == "receipt_reconciliation"
            if receipt_reconciliation:
                # Receipt admission may outlive creative authority. Only this
                # scope needs a protected snapshot and the old currentness fact.
                protected_before, closure_before = _receipt_material_closures(session, self.project_id)
                closure_was_current = run.expected_closure == closure_before
            connection = session.connection().connection.driver_connection
            changes_before = connection.total_changes
            session.info["autopilot_run_id"] = run.id
            token = self._command_context.set((session, authority))
            try:
                yield session
                if receipt_reconciliation:
                    _, closure = _receipt_material_closures(session, self.project_id, expected_protected=protected_before)
                else:
                    closure = material_closure(session, self.project_id)
                if connection.total_changes != changes_before:
                    if not receipt_reconciliation or closure_was_current:
                        run.expected_closure = closure
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
