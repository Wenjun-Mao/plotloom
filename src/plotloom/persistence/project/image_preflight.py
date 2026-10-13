"""One current image execution contract, optionally bound to admitted policy."""
from ...autopilot_contracts import OperationScope
from ..schema import AutopilotRunRow
from .autopilot_authority import require_machine_scope


def image_preflight(access, session):
    if access.authority() is None:
        return {"version": "p1.5-pin.v2", "skillVersion": "plotloom-image-specialist.v4", "executionContract": "codex_specialist.v3"}
    authority = require_machine_scope(access, OperationScope.IMAGE)
    run = session.get(AutopilotRunRow, authority.run_id)
    return dict(run.policy["executionPins"]["image"])
