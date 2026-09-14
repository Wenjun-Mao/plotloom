"""Application-owned Wan pilot accounting within caller-owned transactions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import new_id
from ...exceptions import InvalidTransitionError
from ..codec import _stored_utc
from ..schema import VideoPilotLedgerEventRow, VideoPilotLedgerRow
from .access import ApplicationControlAccess


class VideoPilotAccounting:
    """Ledger policy only; project-video state remains project-owned.

    Reservation callers supply their existing lifecycle transaction so a job
    row and its application accounting event commit or roll back together.
    """

    # This durable primary key predates capability extraction. Keeping it
    # byte-for-byte preserves reservations, event history, and the global cap.
    _LEDGER_ID = "wan-3.0-pilot-100-requested-seconds"
    _LIMIT_SECONDS = 100

    def __init__(self, access: ApplicationControlAccess) -> None:
        self._access = access

    @classmethod
    def _ledger_in_session(cls, session: Session, now: datetime) -> VideoPilotLedgerRow:
        row = session.get(VideoPilotLedgerRow, cls._LEDGER_ID)
        if row is None:
            row = VideoPilotLedgerRow(
                id=cls._LEDGER_ID, limit_seconds=cls._LIMIT_SECONDS,
                reserved_seconds=0, created_at=now, updated_at=now,
            )
            session.add(row)
            session.flush()
        return row

    def budget(self) -> dict[str, Any]:
        with self._access.read() as session:
            row = session.get(VideoPilotLedgerRow, self._LEDGER_ID)
            if row is None:
                return {
                    "limitSeconds": self._LIMIT_SECONDS, "reservedSeconds": 0,
                    "remainingSeconds": self._LIMIT_SECONDS, "attempts": [],
                }
            events = session.scalars(
                select(VideoPilotLedgerEventRow)
                .where(VideoPilotLedgerEventRow.ledger_id == row.id)
                .order_by(VideoPilotLedgerEventRow.created_at, VideoPilotLedgerEventRow.id)
            ).all()
            return {
                "limitSeconds": row.limit_seconds,
                "reservedSeconds": row.reserved_seconds,
                "remainingSeconds": row.limit_seconds - row.reserved_seconds,
                "attempts": [
                    {
                        "videoJobId": event.video_job_id, "event": event.event,
                        "seconds": event.seconds,
                        "createdAt": _stored_utc(event.created_at).isoformat(),
                    }
                    for event in events
                ],
            }

    def reserve(self, session: Session, *, video_job_id: str, seconds: int, now: datetime) -> None:
        ledger = self._ledger_in_session(session, now)
        if ledger.reserved_seconds + seconds > ledger.limit_seconds:
            raise InvalidTransitionError("P2 requested-second allowance would be exceeded")
        ledger.reserved_seconds += seconds
        ledger.updated_at = now
        session.add(VideoPilotLedgerEventRow(
            id=new_id(), ledger_id=ledger.id, video_job_id=video_job_id,
            event="reserved", seconds=seconds, created_at=now,
        ))

    def record_dispatch(self, session: Session, *, video_job_id: str, seconds: int, now: datetime) -> None:
        ledger = self._ledger_in_session(session, now)
        session.add(VideoPilotLedgerEventRow(
            id=new_id(), ledger_id=ledger.id, video_job_id=video_job_id,
            event="dispatch_claimed", seconds=seconds, created_at=now,
        ))

    def release_before_dispatch(self, session: Session, *, video_job_id: str, seconds: int, now: datetime) -> None:
        ledger = self._ledger_in_session(session, now)
        ledger.reserved_seconds -= seconds
        ledger.updated_at = now
        session.add(VideoPilotLedgerEventRow(
            id=new_id(), ledger_id=ledger.id, video_job_id=video_job_id,
            event="released_before_dispatch", seconds=-seconds, created_at=now,
        ))
