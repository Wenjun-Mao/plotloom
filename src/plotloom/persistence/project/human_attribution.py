"""Truthful creator attribution at explicit human command owners."""

from ...autopilot_contracts import OperationScope
from ...exceptions import InvalidTransitionError
from ...human_confirmation_contracts import UnnamedCreatorConfirmation
from ...delegated_qa import reject_reserved_reviewer


def stored_reviewer(access, reviewer: str | UnnamedCreatorConfirmation) -> str:
    if isinstance(reviewer, UnnamedCreatorConfirmation):
        authority = access.authority()
        if authority is None or authority.scope != OperationScope.HANDOFF:
            raise InvalidTransitionError("unnamed creator confirmation requires human handoff authority")
        return ""
    value = reviewer.strip()
    reject_reserved_reviewer(value)
    if not value:
        raise ValueError("manual reviewer must not be blank")
    return value


def attribution_readback(reviewer: str) -> dict:
    return {"attribution": {"kind": "unnamed_creator"}} if reviewer == "" else {}


def stored_storyboard_reviewer(access, reviewer: str | UnnamedCreatorConfirmation) -> str:
    """Manual board clicks and whole-pack handoff may confirm without a name."""
    from .autopilot_authority import require_human_command

    require_human_command(access)
    if isinstance(reviewer, UnnamedCreatorConfirmation):
        return ""
    return stored_reviewer(access, reviewer)
