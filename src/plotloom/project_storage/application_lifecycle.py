"""Installation-only idempotency records for project-folder lifecycle actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import sqlite3
from typing import ContextManager

from ..domain import new_id, utc_now
from ..exceptions import BootstrapContentionError, IdempotencyConflictError


_CREATION_LEASE_SECONDS = 30
_CREATION_RETRY_AFTER_SECONDS = 1


@dataclass(frozen=True)
class DuplicateReservation:
    """Stable target identity for a replayable, content-free duplicate request."""

    key: str
    source_project_id: str
    target_project_id: str
    target_created_at: datetime
    copied_through: str | None
    omitted_stages: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.copied_through is not None or bool(self.omitted_stages)


@dataclass(frozen=True)
class CreationReservation:
    """Installation-owned identity for one replayable project bootstrap."""

    key: str
    target_project_id: str
    target_created_at: datetime
    complete: bool
    initialization_token: str | None

    @property
    def initialization_claimed(self) -> bool:
        """Whether this request may initialize or recover the reserved home."""

        return self.initialization_token is not None


class ApplicationProjectLifecycleLedger:
    """Keep retry identity outside project folders without storing project content."""

    def __init__(
        self,
        *,
        read: Callable[[], ContextManager[sqlite3.Connection]],
        write: Callable[[], ContextManager[sqlite3.Connection]],
    ) -> None:
        self._read = read
        self._write = write

    @staticmethod
    def initialize_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS application_project_duplicate_requests (
                idempotency_key TEXT PRIMARY KEY,
                request_fingerprint TEXT NOT NULL,
                source_project_id TEXT NOT NULL,
                target_project_id TEXT NOT NULL UNIQUE,
                target_created_at TEXT NOT NULL,
                copied_through TEXT,
                omitted_stages_json TEXT,
                completed_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS application_project_create_requests (
                idempotency_key TEXT PRIMARY KEY,
                request_fingerprint TEXT NOT NULL,
                target_project_id TEXT NOT NULL UNIQUE,
                target_created_at TEXT NOT NULL,
                initialization_token TEXT,
                initialization_lease_until TEXT,
                completed_at TEXT
            )
            """
        )
        create_columns = {
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(application_project_create_requests)"
            )
        }
        # This table was introduced during the source-only retirement follow-up.
        # Keep its early, incomplete reservations recoverable for a developer
        # who ran that intermediate source before this lease contract landed.
        if "initialization_token" not in create_columns:
            connection.execute(
                "ALTER TABLE application_project_create_requests "
                "ADD COLUMN initialization_token TEXT"
            )
        if "initialization_lease_until" not in create_columns:
            connection.execute(
                "ALTER TABLE application_project_create_requests "
                "ADD COLUMN initialization_lease_until TEXT"
            )

    @staticmethod
    def _reservation(row: sqlite3.Row) -> DuplicateReservation:
        omitted = json.loads(row["omitted_stages_json"] or "[]")
        if not isinstance(omitted, list) or any(
            not isinstance(stage, str) for stage in omitted
        ):
            raise ValueError("duplicate request has malformed omitted-stage metadata")
        return DuplicateReservation(
            key=str(row["idempotency_key"]),
            source_project_id=str(row["source_project_id"]),
            target_project_id=str(row["target_project_id"]),
            target_created_at=datetime.fromisoformat(str(row["target_created_at"])),
            copied_through=(
                str(row["copied_through"])
                if row["copied_through"] is not None
                else None
            ),
            omitted_stages=tuple(omitted),
        )

    def reserve_duplicate(
        self, *, key: str, fingerprint: str, source_project_id: str
    ) -> DuplicateReservation:
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM application_project_duplicate_requests "
                "WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                if (
                    row["request_fingerprint"] != fingerprint
                    or row["source_project_id"] != source_project_id
                ):
                    raise IdempotencyConflictError()
                return self._reservation(row)
            created_at = utc_now()
            target_project_id = new_id()
            connection.execute(
                "INSERT INTO application_project_duplicate_requests "
                "(idempotency_key, request_fingerprint, source_project_id, "
                "target_project_id, target_created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    key,
                    fingerprint,
                    source_project_id,
                    target_project_id,
                    created_at.isoformat(),
                ),
            )
            return DuplicateReservation(
                key=key,
                source_project_id=source_project_id,
                target_project_id=target_project_id,
                target_created_at=created_at,
                copied_through=None,
                omitted_stages=(),
            )

    def complete_duplicate(
        self,
        reservation: DuplicateReservation,
        *,
        copied_through: str | None,
        omitted_stages: tuple[str, ...],
    ) -> DuplicateReservation:
        with self._write() as connection:
            updated = connection.execute(
                "UPDATE application_project_duplicate_requests "
                "SET copied_through = ?, omitted_stages_json = ?, completed_at = ? "
                "WHERE idempotency_key = ? AND target_project_id = ?",
                (
                    copied_through,
                    json.dumps(list(omitted_stages), separators=(",", ":")),
                    utc_now().isoformat(),
                    reservation.key,
                    reservation.target_project_id,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("duplicate request reservation was lost")
        return DuplicateReservation(
            key=reservation.key,
            source_project_id=reservation.source_project_id,
            target_project_id=reservation.target_project_id,
            target_created_at=reservation.target_created_at,
            copied_through=copied_through,
            omitted_stages=omitted_stages,
        )

    def reserve_creation(self, *, key: str, fingerprint: str) -> CreationReservation:
        """Claim a bounded bootstrap lease without copying project content here.

        A replay cannot open a project home while its first initializer owns
        the lease.  If an initializer crashes, one retry claims the expired
        lease and can complete the already reserved project identity.
        """

        with self._write() as connection:
            now = utc_now()
            row = connection.execute(
                "SELECT * FROM application_project_create_requests WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                if row["request_fingerprint"] != fingerprint:
                    raise IdempotencyConflictError()
                if row["completed_at"] is not None:
                    return CreationReservation(
                        key=key,
                        target_project_id=str(row["target_project_id"]),
                        target_created_at=datetime.fromisoformat(
                            str(row["target_created_at"])
                        ),
                        complete=True,
                        initialization_token=None,
                    )
                lease_until_value = row["initialization_lease_until"]
                if (
                    lease_until_value is not None
                    and datetime.fromisoformat(str(lease_until_value)) > now
                ):
                    return CreationReservation(
                        key=key,
                        target_project_id=str(row["target_project_id"]),
                        target_created_at=datetime.fromisoformat(
                            str(row["target_created_at"])
                        ),
                        complete=False,
                        initialization_token=None,
                    )
                token = new_id()
                renewed_until = now + timedelta(seconds=_CREATION_LEASE_SECONDS)
                claimed = connection.execute(
                    "UPDATE application_project_create_requests "
                    "SET initialization_token = ?, initialization_lease_until = ? "
                    "WHERE idempotency_key = ? AND completed_at IS NULL "
                    "AND (initialization_lease_until IS NULL "
                    "OR initialization_lease_until <= ?)",
                    (token, renewed_until.isoformat(), key, now.isoformat()),
                )
                if claimed.rowcount != 1:
                    raise BootstrapContentionError(_CREATION_RETRY_AFTER_SECONDS)
                return CreationReservation(
                    key=key,
                    target_project_id=str(row["target_project_id"]),
                    target_created_at=datetime.fromisoformat(
                        str(row["target_created_at"])
                    ),
                    complete=False,
                    initialization_token=token,
                )
            created_at = now
            project_id = new_id()
            token = new_id()
            lease_until = created_at + timedelta(seconds=_CREATION_LEASE_SECONDS)
            connection.execute(
                "INSERT INTO application_project_create_requests "
                "(idempotency_key, request_fingerprint, target_project_id, target_created_at, "
                "initialization_token, initialization_lease_until) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    key,
                    fingerprint,
                    project_id,
                    created_at.isoformat(),
                    token,
                    lease_until.isoformat(),
                ),
            )
            return CreationReservation(
                key=key,
                target_project_id=project_id,
                target_created_at=created_at,
                complete=False,
                initialization_token=token,
            )

    def complete_creation(self, reservation: CreationReservation) -> CreationReservation:
        if not reservation.initialization_claimed:
            raise ValueError("project creation completion needs its initialization lease")
        with self._write() as connection:
            updated = connection.execute(
                "UPDATE application_project_create_requests "
                "SET completed_at = ?, initialization_token = NULL, "
                "initialization_lease_until = NULL "
                "WHERE idempotency_key = ? AND target_project_id = ? "
                "AND completed_at IS NULL AND initialization_token = ?",
                (
                    utc_now().isoformat(),
                    reservation.key,
                    reservation.target_project_id,
                    reservation.initialization_token,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("project creation reservation was lost")
        return CreationReservation(
            key=reservation.key,
            target_project_id=reservation.target_project_id,
            target_created_at=reservation.target_created_at,
            complete=True,
            initialization_token=None,
        )

    def forget_project_run_routes(self, project_id: str) -> None:
        """Remove disposable run indexes once their canonical home is erased."""

        with self._write() as connection:
            run_ids = [
                str(row["run_id"])
                for row in connection.execute(
                    "SELECT run_id FROM application_run_routes WHERE project_id = ?",
                    (project_id,),
                ).fetchall()
            ]
            if not run_ids:
                return
            placeholders = ", ".join("?" for _ in run_ids)
            connection.execute(
                f"DELETE FROM application_frozen_profile_run_references WHERE run_id IN ({placeholders})",
                run_ids,
            )
            connection.execute(
                "DELETE FROM application_run_routes WHERE project_id = ?", (project_id,)
            )

    def forget_project(self, project_id: str) -> None:
        with self._write() as connection:
            connection.execute(
                "DELETE FROM application_project_duplicate_requests "
                "WHERE source_project_id = ? OR target_project_id = ?",
                (project_id, project_id),
            )
            connection.execute(
                "DELETE FROM application_project_create_requests WHERE target_project_id = ?",
                (project_id,),
            )
