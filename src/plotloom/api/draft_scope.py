from __future__ import annotations

from fastapi import HTTPException, status

from ..stage_contracts import AuthoringDraftScope
from .contracts import CanonicalDraftConsumption


def assert_canonical_draft_scope(
    consumption: CanonicalDraftConsumption | None,
    *,
    required_scope: AuthoringDraftScope,
) -> None:
    if consumption is None:
        return
    if consumption.editor_scope != required_scope:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="canonical save may consume only its own editor draft",
        )


def require_media_draft_scope(
    consumption: CanonicalDraftConsumption,
    *,
    required_scope: AuthoringDraftScope,
    required_entity_id: str,
) -> None:
    if (
        consumption.editor_scope != required_scope
        or consumption.entity_id != required_entity_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="media action must consume its exact editor draft",
        )
