"""Installation-owned dispatch reservations for direct project H3 work."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
import sqlite3
from typing import Any, Literal

from pydantic import Field, model_validator

from ..domain import CamelModel, contains_secret_value, utc_now
from .format import ProjectStorageConflictError, ProjectStorageError


class VideoDispatchLease(CamelModel):
    """An installation-only dispatch identity with no project content."""

    dispatch_identity: str = Field(min_length=20, max_length=96)
    resource: str = Field(min_length=1, max_length=120)
    reserved_units: int = Field(ge=0)
    requires_accounting: bool = False
    state: Literal["reserved", "dispatch_claimed", "released"]
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def reject_secret_fields(self) -> "VideoDispatchLease":
        if contains_secret_value(self.dispatch_identity) or contains_secret_value(
            self.resource
        ):
            raise ValueError("video dispatch identifiers must be public")
        return self


class DirectVideoDispatchAccounting:
    """Own the cross-project reservation/event ledger and nothing else."""

    def __init__(
        self,
        *,
        read: Callable[[], AbstractContextManager[sqlite3.Connection]],
        write: Callable[[], AbstractContextManager[sqlite3.Connection]],
    ) -> None:
        self._read = read
        self._write = write

    def initialize_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS direct_video_accounting (
                ledger_id TEXT PRIMARY KEY CHECK (ledger_id = 'direct-video'),
                limit_units INTEGER NOT NULL CHECK (limit_units >= 0),
                reserved_units INTEGER NOT NULL CHECK (reserved_units >= 0),
                initialized_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS direct_video_dispatch_leases (
                dispatch_identity TEXT PRIMARY KEY,
                resource TEXT NOT NULL,
                reserved_units INTEGER NOT NULL CHECK (reserved_units >= 0),
                requires_accounting INTEGER NOT NULL DEFAULT 0 CHECK (requires_accounting IN (0, 1)),
                state TEXT NOT NULL CHECK (state IN ('reserved', 'dispatch_claimed', 'released')),
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS direct_video_dispatch_events (
                event_id TEXT PRIMARY KEY,
                dispatch_identity TEXT NOT NULL REFERENCES direct_video_dispatch_leases(dispatch_identity),
                event TEXT NOT NULL CHECK (event IN ('reserved', 'dispatch_claimed', 'released_before_dispatch')),
                units INTEGER NOT NULL,
                created_at TEXT NOT NULL);""")
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(direct_video_dispatch_leases)")
        }
        if "requires_accounting" not in columns:
            connection.execute(
                "ALTER TABLE direct_video_dispatch_leases ADD COLUMN requires_accounting INTEGER NOT NULL DEFAULT 0 CHECK (requires_accounting IN (0, 1))"
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> VideoDispatchLease:
        return VideoDispatchLease(
            dispatch_identity=row["dispatch_identity"],
            resource=row["resource"],
            reserved_units=row["reserved_units"],
            requires_accounting=bool(row["requires_accounting"]),
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def initialize(self, *, limit_units: int) -> None:
        if limit_units < 0:
            raise ValueError("video accounting limit must be non-negative")
        now = utc_now().isoformat()
        with self._write() as connection:
            if connection.execute(
                "SELECT 1 FROM direct_video_accounting WHERE ledger_id = 'direct-video'"
            ).fetchone() is not None:
                raise ProjectStorageConflictError(
                    "direct video accounting is already initialized"
                )
            connection.execute(
                "INSERT INTO direct_video_accounting (ledger_id, limit_units, reserved_units, initialized_at, updated_at) VALUES ('direct-video', ?, 0, ?, ?)",
                (limit_units, now, now),
            )

    def reserve(
        self,
        *,
        dispatch_identity: str,
        resource: str,
        reserved_units: int,
        requires_accounting: bool,
    ) -> VideoDispatchLease:
        """Reserve exactly one immutable dispatch identity before project claim."""

        if reserved_units < 0:
            raise ValueError("video dispatch units must be non-negative")
        now = utc_now()
        with self._write() as connection:
            existing = connection.execute(
                "SELECT dispatch_identity, resource, reserved_units, requires_accounting, state, created_at, updated_at FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
                (dispatch_identity,),
            ).fetchone()
            if existing is not None:
                lease = self._from_row(existing)
                if (
                    lease.resource != resource
                    or lease.reserved_units != reserved_units
                    or lease.requires_accounting != requires_accounting
                ):
                    raise ProjectStorageConflictError(
                        "video dispatch identity conflicts with its immutable reservation"
                    )
                return lease
            if requires_accounting:
                ledger = connection.execute(
                    "SELECT limit_units, reserved_units FROM direct_video_accounting WHERE ledger_id = 'direct-video'"
                ).fetchone()
                if ledger is None:
                    raise ProjectStorageError(
                        "paid video dispatch is disabled: application accounting is not initialized"
                    )
                if ledger["reserved_units"] + reserved_units > ledger["limit_units"]:
                    raise ProjectStorageConflictError(
                        "video requested-unit allowance would be exceeded"
                    )
                connection.execute(
                    "UPDATE direct_video_accounting SET reserved_units = reserved_units + ?, updated_at = ? WHERE ledger_id = 'direct-video'",
                    (reserved_units, now.isoformat()),
                )
            connection.execute(
                "INSERT INTO direct_video_dispatch_leases (dispatch_identity, resource, reserved_units, requires_accounting, state, created_at, updated_at) VALUES (?, ?, ?, ?, 'reserved', ?, ?)",
                (dispatch_identity, resource, reserved_units, int(requires_accounting), now.isoformat(), now.isoformat()),
            )
            connection.execute(
                "INSERT INTO direct_video_dispatch_events (event_id, dispatch_identity, event, units, created_at) VALUES (?, ?, 'reserved', ?, ?)",
                (f"{dispatch_identity}:reserved", dispatch_identity, reserved_units, now.isoformat()),
            )
            return VideoDispatchLease(
                dispatch_identity=dispatch_identity,
                resource=resource,
                reserved_units=reserved_units,
                requires_accounting=requires_accounting,
                state="reserved",
                created_at=now,
                updated_at=now,
            )

    def record_claim(self, dispatch_identity: str) -> VideoDispatchLease:
        """Append the app-side claim event after the project-side claim commits."""

        now = utc_now()
        with self._write() as connection:
            row = connection.execute(
                "SELECT dispatch_identity, resource, reserved_units, requires_accounting, state, created_at, updated_at FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
                (dispatch_identity,),
            ).fetchone()
            if row is None:
                raise ProjectStorageError("video dispatch lease is missing")
            lease = self._from_row(row)
            if lease.state == "dispatch_claimed":
                return lease
            if lease.state != "reserved":
                raise ProjectStorageConflictError("video dispatch lease cannot be claimed")
            connection.execute(
                "UPDATE direct_video_dispatch_leases SET state = 'dispatch_claimed', updated_at = ? WHERE dispatch_identity = ?",
                (now.isoformat(), dispatch_identity),
            )
            connection.execute(
                "INSERT INTO direct_video_dispatch_events (event_id, dispatch_identity, event, units, created_at) VALUES (?, ?, 'dispatch_claimed', ?, ?)",
                (f"{dispatch_identity}:claimed", dispatch_identity, lease.reserved_units, now.isoformat()),
            )
            return lease.model_copy(update={"state": "dispatch_claimed", "updated_at": now})

    def release_before_dispatch(self, dispatch_identity: str) -> VideoDispatchLease | None:
        """Release only a reservation that has no durable dispatch claim."""

        now = utc_now()
        with self._write() as connection:
            row = connection.execute(
                "SELECT dispatch_identity, resource, reserved_units, requires_accounting, state, created_at, updated_at FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
                (dispatch_identity,),
            ).fetchone()
            if row is None:
                return None
            lease = self._from_row(row)
            if lease.state == "released":
                return lease
            if lease.state != "reserved":
                return lease
            if lease.requires_accounting and lease.reserved_units:
                updated = connection.execute(
                    "UPDATE direct_video_accounting SET reserved_units = reserved_units - ?, updated_at = ? WHERE ledger_id = 'direct-video' AND reserved_units >= ?",
                    (lease.reserved_units, now.isoformat(), lease.reserved_units),
                )
                if updated.rowcount != 1:
                    raise ProjectStorageError(
                        "video accounting reservation cannot be safely released"
                    )
            connection.execute(
                "UPDATE direct_video_dispatch_leases SET state = 'released', updated_at = ? WHERE dispatch_identity = ?",
                (now.isoformat(), dispatch_identity),
            )
            connection.execute(
                "INSERT INTO direct_video_dispatch_events (event_id, dispatch_identity, event, units, created_at) VALUES (?, ?, 'released_before_dispatch', ?, ?)",
                (f"{dispatch_identity}:released", dispatch_identity, -lease.reserved_units, now.isoformat()),
            )
            return lease.model_copy(update={"state": "released", "updated_at": now})

    def budget(self) -> dict[str, Any]:
        with self._read() as connection:
            ledger = connection.execute(
                "SELECT limit_units, reserved_units FROM direct_video_accounting WHERE ledger_id = 'direct-video'"
            ).fetchone()
        if ledger is None:
            return {
                "configured": False,
                "limitUnits": None,
                "reservedUnits": None,
                "remainingUnits": None,
                "limitSeconds": 0,
                "reservedSeconds": 0,
                "remainingSeconds": 0,
                "attempts": [],
            }
        return {
            "configured": True,
            "limitUnits": ledger["limit_units"],
            "reservedUnits": ledger["reserved_units"],
            "remainingUnits": ledger["limit_units"] - ledger["reserved_units"],
            "limitSeconds": ledger["limit_units"],
            "reservedSeconds": ledger["reserved_units"],
            "remainingSeconds": ledger["limit_units"] - ledger["reserved_units"],
            "attempts": [],
        }
