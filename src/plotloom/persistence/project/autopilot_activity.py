"""Read-only activity projection from durable owner records, never host polling."""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, RunActivity
from ...codex_exec_contracts import CodexExecAttempt
from ..schema import AutopilotCheckpointRow, AutopilotExecAttemptRow

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
