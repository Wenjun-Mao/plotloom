"""Narrow shared-owner encoding; unnamed facts require handoff authority."""

from ...autopilot_contracts import OperationScope
from ...exceptions import InvalidTransitionError
from ...human_confirmation_contracts import UnnamedCreatorConfirmation


def stored_reviewer(access, reviewer: str | UnnamedCreatorConfirmation) -> str:
    if isinstance(reviewer, UnnamedCreatorConfirmation):
        authority = access.authority()
        if authority is None or authority.scope != OperationScope.HANDOFF:
            raise InvalidTransitionError("unnamed creator confirmation requires human handoff authority")
        return ""
    value = reviewer.strip()
    if not value:
        raise ValueError("manual reviewer must not be blank")
    return value


def attribution_readback(reviewer: str) -> dict:
    return {"attribution": {"kind": "unnamed_creator"}} if reviewer == "" else {}
