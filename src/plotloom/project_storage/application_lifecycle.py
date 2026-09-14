"""Installation-only idempotency records for project-folder lifecycle actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from typing import ContextManager

from ..domain import new_id, utc_now
from ..exceptions import IdempotencyConflictError


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
