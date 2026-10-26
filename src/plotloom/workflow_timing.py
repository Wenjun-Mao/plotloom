"""Response-only workflow facts; mutable updated_at is never progress evidence."""
from datetime import datetime, timezone

from plotloom.domain_base import CamelModel
from plotloom.contract_identity import utc_now


class WorkflowTiming(CamelModel):
    observed_at: datetime
    created_at: datetime
    terminal: bool
    milestone: str | None = None
    milestone_at: datetime | None = None
    completed_at: datetime | None = None


def timing_projection(created_at, *, terminal, milestone=None, milestone_at=None, completed_at=None):
    def utc(value):
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value
    return WorkflowTiming(observed_at=utc_now(), created_at=utc(created_at), terminal=terminal,
        milestone=milestone, milestone_at=utc(milestone_at), completed_at=utc(completed_at))
