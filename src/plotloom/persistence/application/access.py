"""Typed application-control transaction access."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ApplicationControlAccess:
    """Only application-wide leases; project state is never reachable here."""

    read: Callable[[], AbstractContextManager[Session]]
    write: Callable[[], AbstractContextManager[Session]]
