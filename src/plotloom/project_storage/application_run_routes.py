"""Installation run routing and frozen-profile deletion protection."""
from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import sqlite3

from plotloom.contract_identity import utc_now
from plotloom.run_contracts import TERMINAL_RUN_STATUSES
from ..exceptions import InvalidTransitionError, NotFoundError
from .format import ProjectStorageConflictError, ProjectStorageCorruptionError


@dataclass(frozen=True)
class ApplicationRunRoute:
    """A rebuildable route and its frozen-profile deletion guard."""

    run_id: str
    project_id: str
    profile_id: str
    status: str


class ApplicationRunRoutes:
    """Two-table capability using the application's existing transaction contexts."""

    def __init__(self, *, read: Callable[[], AbstractContextManager[sqlite3.Connection]],
                 write: Callable[[], AbstractContextManager[sqlite3.Connection]]) -> None:
        self._read = read
        self._write = write

    @staticmethod
    def initialize_schema(connection: sqlite3.Connection) -> None:
        connection.executescript("""
                CREATE TABLE IF NOT EXISTS application_run_routes (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    indexed_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS application_frozen_profile_run_references (
                    run_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL);""")

    @staticmethod
    def require_profile_unreferenced(connection: sqlite3.Connection, profile_id: str) -> None:
        """Check under the caller's profile-deletion BEGIN IMMEDIATE fence."""
        terminal_statuses = tuple(status.value for status in TERMINAL_RUN_STATUSES)
        protected = connection.execute(
            "SELECT run_id FROM application_frozen_profile_run_references "
            "WHERE profile_id = ? AND status NOT IN (?, ?, ?, ?) LIMIT 1",
            (profile_id, *terminal_statuses),
        ).fetchone()
        if protected is not None:
            raise InvalidTransitionError(
                "cannot delete a text provider profile frozen by a nonterminal run"
            )

    def reserve_run_route(self, route: ApplicationRunRoute) -> None:
        """Protect a frozen profile before a project transaction creates its run.

        A crash before project creation leaves only disposable ``pending``
        state, which startup reconstructs. Reversing the order could make a
        canonical project run invisible to every run-ID route.
        """

        with self._write() as connection:
            if connection.execute(
                "SELECT 1 FROM application_profiles WHERE profile_id = ?", (route.profile_id,)
            ).fetchone() is None:
                raise NotFoundError(f"text provider profile not found: {route.profile_id}")
            existing_route = connection.execute(
                "SELECT project_id FROM application_run_routes WHERE run_id = ?", (route.run_id,)
            ).fetchone()
            if existing_route is not None and existing_route["project_id"] != route.project_id:
                raise ProjectStorageConflictError("run ID is already routed to another project")
            existing_reference = connection.execute(
                "SELECT profile_id FROM application_frozen_profile_run_references WHERE run_id = ?",
                (route.run_id,),
            ).fetchone()
            if existing_reference is not None and existing_reference["profile_id"] != route.profile_id:
                raise ProjectStorageConflictError("run ID is already bound to another frozen profile")
            now = utc_now().isoformat()
            connection.execute(
                "INSERT INTO application_run_routes (run_id, project_id, indexed_at) VALUES (?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET indexed_at = excluded.indexed_at",
                (route.run_id, route.project_id, now),
            )
            connection.execute(
                "INSERT INTO application_frozen_profile_run_references "
                "(run_id, profile_id, status, updated_at) VALUES (?, ?, 'pending', ?) "
                "ON CONFLICT(run_id) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at",
                (route.run_id, route.profile_id, now),
            )

    def confirm_run_route(self, run_id: str, *, status: str) -> None:
        """Confirm project-local status once the project transaction commits."""

        with self._write() as connection:
            updated = connection.execute(
                "UPDATE application_frozen_profile_run_references SET status = ?, updated_at = ? "
                "WHERE run_id = ?",
                (status, utc_now().isoformat(), run_id),
            )
            if updated.rowcount != 1:
                raise ProjectStorageCorruptionError("run route has no frozen-profile reservation")

    def discard_pending_run_route(self, run_id: str) -> None:
        """Discard only a reservation that cannot name a project-created run."""

        with self._write() as connection:
            reference = connection.execute(
                "SELECT status FROM application_frozen_profile_run_references WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if reference is None or reference["status"] != "pending":
                return
            connection.execute(
                "DELETE FROM application_frozen_profile_run_references WHERE run_id = ?",
                (run_id,),
            )
            connection.execute("DELETE FROM application_run_routes WHERE run_id = ?", (run_id,))

    def index_run(self, route: ApplicationRunRoute) -> None:
        """Backfill an already-created idempotent run into the application index."""

        self.reserve_run_route(route)
        self.confirm_run_route(route.run_id, status=route.status)

    def project_for_run(self, run_id: str) -> str | None:
        with self._read() as connection:
            row = connection.execute(
                "SELECT project_id FROM application_run_routes WHERE run_id = ?", (run_id,)
            ).fetchone()
        return str(row["project_id"]) if row is not None else None

    def replace_run_index(self, routes: list[ApplicationRunRoute]) -> None:
        """Atomically rebuild routes and frozen-profile evidence from projects."""

        if len({item.run_id for item in routes}) != len(routes):
            raise ProjectStorageCorruptionError("multiple project runs share one run ID")

        with self._write() as connection:
            connection.execute("DELETE FROM application_run_routes")
            connection.execute("DELETE FROM application_frozen_profile_run_references")
            now = utc_now().isoformat()
            connection.executemany(
                "INSERT INTO application_run_routes (run_id, project_id, indexed_at) VALUES (?, ?, ?)",
                [(item.run_id, item.project_id, now) for item in routes],
            )
            connection.executemany(
                "INSERT INTO application_frozen_profile_run_references "
                "(run_id, profile_id, status, updated_at) VALUES (?, ?, ?, ?)",
                [(item.run_id, item.profile_id, item.status, now) for item in routes],
            )
