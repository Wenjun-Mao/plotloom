"""Explicit infrastructure contracts shared by project persistence capabilities.

Capability modules receive only the leases, row guards, and codecs their domain
operations need.  This keeps the retained runtime repository as composition,
rather than allowing collaborators to reach back into it as a service locator.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ContextManager

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ProjectLeases:
    read: Callable[[], ContextManager[Session]]
    write: Callable[[], ContextManager[Session]]
    bootstrap_write: Callable[[], ContextManager[Session]]
    lifecycle_write: Callable[[], ContextManager[Session]]
    work_unit_claim_write: Callable[[], ContextManager[Session]]


@dataclass(frozen=True)
class ProjectRows:
    project: Callable[[Session, str], Any]
    stage: Callable[[Session, str, Any], Any]
    run: Callable[[Session, str], Any]
    media_task: Callable[[Session, str], Any]


@dataclass(frozen=True)
class ProjectCodecs:
    project: Callable[[Any], Any]
    latest_run_summary: Callable[[Any], Any]
    stage_head: Callable[[Any], Any]
    entity_revision: Callable[[Any], Any]
    decode_current_stage_payload: Callable[[Any, dict[str, Any], int | None], Any]
    gate_result: Callable[[Any], Any]
    approval_decision: Callable[[Any], Any]


@dataclass(frozen=True)
class ProjectGuards:
    active: Callable[[Any], None]
    lifecycle_revision: Callable[[Any, int], None]
    busy: Callable[[Session, str], bool]


@dataclass(frozen=True)
class ProjectPersistenceAccess:
    """Named project infrastructure, deliberately not a repository facade."""

    leases: ProjectLeases
    rows: ProjectRows
    codecs: ProjectCodecs
    guards: ProjectGuards
