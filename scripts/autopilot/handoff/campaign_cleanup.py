"""Typed passive cleanup observations; no replay, cancellation or budget changes."""
from contextlib import closing
from dataclasses import asdict
import os
import sqlite3

from admission_observation import LedgerRow
from parking_observation import CleanupFacts, classify_cleanup
from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReceipt


def ledger_row(row, queue):
    current = CodexExecAttempt.model_validate_json(row["status_json"])
    return LedgerRow(CodexExecAttempt.model_validate_json(row["attempt_json"]), current,
        dispatch_enabled=bool(queue[str(current.attempt_id)]) if str(current.attempt_id) in queue else None,
        worker_pid=row["worker_pid"], worker_group_id=row["worker_group_id"],
        worker_birth_identity=row["worker_birth_identity"],
        receipt=CodexExecReceipt.model_validate_json(row["receipt_json"]) if row["receipt_json"] else None)


def group_observation(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return "absent"
    except OSError:
        return "unproved"
    return "present"


def cleanup_snapshot(runtime, projects, *, material_qualified):
    host = runtime.bridge.exec_supervisor()
    with sqlite3.connect(f"file:{host.database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        queue = {key: bool(enabled) for key, enabled in connection.execute("SELECT attempt_id,enabled FROM exec_queue")}
        rows = tuple(ledger_row(row, queue) for row in connection.execute("SELECT * FROM exec_attempts"))
        validators = tuple(dict(row) for row in connection.execute("SELECT * FROM exec_validation_process"))
        held = connection.execute("SELECT COUNT(*) FROM exec_slot").fetchone()[0]
    states, attempts, handoff = {}, [], False
    storage = runtime.app.state.project_folder_storage
    for project in projects.values():
        with closing(storage.projects.inspect(project, passive=True)) as store:
            view = store.repository.autopilot.current(project)
            if view is None:
                raise RuntimeError("cleanup lost an original project run")
            states[str(project)] = view.state
            handoff |= view.handoff is not None
            for checkpoint in view.checkpoints:
                attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
                if attempt is not None:
                    attempts.append(attempt)
    groups = {group for row in rows for group in (row.worker_group_id, row.current.process_group_id) if group is not None}
    groups.update(row["process_group_id"] for row in validators if row["process_group_id"] is not None)
    observed_groups = {group: group_observation(group) for group in sorted(groups)}
    facts = CleanupFacts(rows=rows, project_attempts=tuple(attempts), project_states=states,
        queue=queue, held=held, validators=len(validators), group_observations=observed_groups,
        material_qualified=material_qualified, human_handoff=handoff)
    result = classify_cleanup(facts)
    evidence = {"classification": asdict(result), "attemptCount": len(rows), "projectStates": states,
        "held": held, "queue": queue, "validators": validators, "groupObservations": observed_groups,
        "projectAttempts": [attempt.model_dump(mode="json", by_alias=True) for attempt in attempts],
        "hostRows": [{"original": row.original.model_dump(mode="json", by_alias=True),
            "current": row.current.model_dump(mode="json", by_alias=True), "dispatchEnabled": row.dispatch_enabled,
            "workerPid": row.worker_pid, "workerGroupId": row.worker_group_id,
            "workerBirthIdentity": row.worker_birth_identity,
            "receipt": row.receipt.model_dump(mode="json", by_alias=True) if row.receipt is not None else None} for row in rows]}
    return result, evidence
