"""Project-database authority for manual creative handoff execution pins."""
from __future__ import annotations

from typing import Any

from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import execution_pin_for_request, request_hash
from ...domain import utc_now
from ..schema.project_creative_handoff import CreativeHandoffExecutionPinRow


def freeze_execution_pin(
    session: Any, request: CreativeHandoffRequest, pin: dict[str, str]
) -> None:
    """Bind a pin in the same transaction that creates the project candidate."""

    validated = execution_pin_for_request(request, pin)
    session.add(
        CreativeHandoffExecutionPinRow(
            job_id=request.job_id,
            project_id=request.project_id,
            request_hash=request_hash(request),
            stage=request.stage,
            execution_pin=validated,
            created_at=utc_now(),
            recovered_from_revision=None,
        )
    )


def execution_pin_for_candidate(
    session: Any, request: CreativeHandoffRequest
) -> dict[str, str]:
    row = session.get(CreativeHandoffExecutionPinRow, request.job_id)
    if (
        row is None
        or row.project_id != request.project_id
        or row.stage != request.stage
        or row.request_hash != request_hash(request)
    ):
        raise CreativeHandoffError(
            "execution_pin_missing",
            "the project-owned execution pin for this creative handoff is unavailable",
        )
    return execution_pin_for_request(request, row.execution_pin)


def recover_execution_pin(
    session: Any,
    request: CreativeHandoffRequest,
    pin: dict[str, str],
    *,
    trusted_revision: str,
) -> None:
    """Persist an operator-verified historic pin without changing handoff bytes."""

    validated = execution_pin_for_request(request, pin)
    existing = session.get(CreativeHandoffExecutionPinRow, request.job_id)
    if existing is not None:
        if (
            existing.project_id != request.project_id
            or existing.request_hash != request_hash(request)
            or existing.stage != request.stage
            or execution_pin_for_request(request, existing.execution_pin) != validated
        ):
            raise CreativeHandoffError("execution_pin_conflict", "creative handoff already has a different trusted execution pin")
        return
    session.add(
        CreativeHandoffExecutionPinRow(
            job_id=request.job_id,
            project_id=request.project_id,
            request_hash=request_hash(request),
            stage=request.stage,
            execution_pin=validated,
            created_at=utc_now(),
            recovered_from_revision=trusted_revision,
        )
    )
