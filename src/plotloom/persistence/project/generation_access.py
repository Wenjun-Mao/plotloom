"""Narrow infrastructure dependencies for generation persistence capabilities.

Generation persistence deliberately receives leases, bound row lookup, codecs,
and profile admission as separate contracts.  It must never reach back through
the retained repository facade for generation policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, ContextManager

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class GenerationLeases:
    """The existing transaction contracts, named rather than flattened."""

    read: Callable[[], ContextManager[Session]]
    write: Callable[[], ContextManager[Session]]
    lifecycle_write: Callable[[], ContextManager[Session]]
    work_unit_claim_write: Callable[[], ContextManager[Session]]


@dataclass(frozen=True)
class GenerationRows:
    """Project-bound lookup callbacks; subclasses retain their admission checks."""

    project: Callable[[Session, str], Any]
    run: Callable[[Session, str], Any]
    stage: Callable[[Session, str, Any], Any]


@dataclass(frozen=True)
class GenerationCodecs:
    """Row/value conversion used by generation capabilities."""

    project: Callable[[Any], Any]
    run: Callable[[Any], Any]
    attempt: Callable[[Any], Any]
    artifact: Callable[[Any], Any]
    stage_head: Callable[[Any], Any]
    stage_plan_trace: Callable[[Any], Any]
    work_unit_trace: Callable[[Any], Any]
    generation_plan_trace: Callable[[Any], Any]
    topology_trace: Callable[[Any], Any]
    sealed_aggregate_trace: Callable[[Any], Any]
    repair_scope: Callable[[Any], Any]
    reuse_binding: Callable[[Any], Any]
    decode_stage_payload: Callable[[Any, dict[str, Any], int | None], Any]
    decode_current_stage_payload: Callable[[Any, dict[str, Any], int | None], Any]


@dataclass(frozen=True)
class GenerationAdmission:
    """The two non-generation ownership guards generation is allowed to invoke."""

    assert_active_project: Callable[[Any], None]
    assert_new_run_profile_enabled: Callable[[Session, dict[str, Any]], None]


@dataclass(frozen=True)
class GenerationPersistenceAccess:
    """Explicit shared infrastructure; this is not a repository service locator."""

    leases: GenerationLeases
    rows: GenerationRows
    codecs: GenerationCodecs
    admission: GenerationAdmission
