"""Read-only activity projection from durable owner records, never host polling."""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, RunActivity, OperationScope
from ...codex_exec_contracts import CodexExecAttempt
from ..schema import AutopilotCheckpointRow, AutopilotExecAttemptRow, AutopilotDecisionRow, AutopilotHandoffRow

ATTEMPT_ACTIVITY = {
    "reserved": "waiting",
    "spawn_intent": "waiting",
    "queued": "queued",
    "running": "generating",
    "validating": "validating",
    "outcome_unknown": "unknown",
    "cancel_requested": "cancelling",
    "completed": "delivered",
    "failed": "failed",
}


def run_timing(session, row, *, state):
    from ...workflow_timing import timing_projection
    handoff = session.scalar(select(AutopilotHandoffRow).where(AutopilotHandoffRow.run_id == row.id)
        .order_by(AutopilotHandoffRow.created_at.desc(), AutopilotHandoffRow.id.desc()).limit(1))
    decisions = session.scalars(select(AutopilotDecisionRow).join(AutopilotCheckpointRow,
        AutopilotCheckpointRow.id == AutopilotDecisionRow.checkpoint_id).where(
            AutopilotDecisionRow.run_id == row.id, AutopilotCheckpointRow.state == "adopted")
        .order_by(AutopilotDecisionRow.created_at.desc(), AutopilotDecisionRow.id.desc()))
    # IMAGE decisions authorize preparation before output exists. SELECT also
    # freezes the inventory; only its nonempty selectedAssets prove adoption.
    adopted = next((decision for decision in decisions if decision.scope in {
        OperationScope.SOURCE.value, OperationScope.TEXT.value, OperationScope.INSTALL.value,
    } or decision.scope == OperationScope.SELECT.value and decision.decision.get("selectedAssets")), None)
    return timing_projection(row.created_at, terminal=state in {"cancelled", "stale", "taken_over", "handed_off"},
        milestone="完整素材审阅已保存" if handoff else "上一项素材已采用" if adopted else None,
        milestone_at=handoff.created_at if handoff else adopted.created_at if adopted else None,
        completed_at=handoff.created_at if handoff and state == "handed_off" else None)


@dataclass(frozen=True)
class _RunViewCheckpoints:
    public: list[dict[str, Any]]
    typed: list[tuple[AutopilotCheckpointRow, CheckpointEvidence]]


def _project_checkpoints(checkpoints: list[AutopilotCheckpointRow]) -> _RunViewCheckpoints:
    """One view owns these derivations; validate then serialize each row in order."""
    public, typed = [], []
    for row in checkpoints:
        checkpoint = {"id": row.id, "operationKey": row.operation_key, "revision": row.revision,
            "state": row.state}
        evidence = CheckpointEvidence.model_validate(row.evidence)
        checkpoint["evidence"] = evidence.model_dump(mode="json", by_alias=True)
        public.append(checkpoint)
        typed.append((row, evidence))
    return _RunViewCheckpoints(public, typed)


def run_activities(session, run_id, checkpoints: _RunViewCheckpoints):
    attempts = {
        row.operation_key: CodexExecAttempt.model_validate(row.snapshot)
        for row in session.scalars(select(AutopilotExecAttemptRow).where(
            AutopilotExecAttemptRow.run_id == run_id,
        )).all()
    }
    activities = []
    for checkpoint, evidence in checkpoints.typed:
        if evidence.job_id is None or evidence.owner == "geometry-preparation":
            continue
        attempt = attempts.get(checkpoint.operation_key)
        if checkpoint.state in {"adopted", "delivered", "failed"}:
            state = checkpoint.state
        elif attempt is not None:
            state = ("delivered" if attempt.terminal_result == "success" else "failed") if attempt.state == "settled" else ATTEMPT_ACTIVITY[attempt.state]
        else:
            # A specialist-chat send has no durable process observation. Its
            # sent checkpoint means waiting for delivery, not known generation.
            state = "unknown" if checkpoint.state == "outcome_unknown" else "waiting"
        activities.append(RunActivity(
            operation_key=checkpoint.operation_key, owner=evidence.owner,
            subject_id=evidence.subject_id, job_id=evidence.job_id,
            domain=attempt.domain if attempt is not None else (
                "image" if evidence.owner in {"image", "character-reference", "art-reference"} else "text"
            ), state=state,
        ))
    return activities
