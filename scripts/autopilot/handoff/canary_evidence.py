"""Typed evidence snapshots for this one ignored canary allocation."""
from __future__ import annotations

import sqlite3
import time

from admission_observation import LedgerSample
from campaign_cleanup import ledger_row

from contextlib import closing, contextmanager
from uuid import uuid4

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecOutputEvidence,
    CodexExecReceipt,
    output_manifest_hash,
)
from plotloom.autopilot_materials import initial_inventory
from plotloom.codex_exec_runtime import frozen_package_snapshot


@contextmanager
def opened_project(projects, project_id: str):
    """Match ProjectStore's documented close-only ownership protocol."""
    with closing(projects.open(project_id)) as store:
        yield store


def summarize_attempt(attempt, receipt, checkpoint: dict, host_status) -> dict:
    """Serialize only typed IDs and hashes using each model's public JSON shape."""
    attempt_json = attempt.model_dump(mode="json", by_alias=True)
    receipt_json = receipt.model_dump(mode="json", by_alias=True) if receipt is not None else None
    return {
        "attemptId": attempt_json["attemptId"],
        "runId": attempt_json["runId"],
        "projectId": attempt_json["projectId"],
        "jobId": attempt_json["jobId"],
        "operationKey": attempt_json["operationKey"],
        "domain": attempt_json["domain"],
        "state": attempt_json["state"],
        "terminalResult": attempt_json["terminalResult"],
        "imageBudgetState": attempt_json["imageBudgetState"],
        "reservedImageOutputs": attempt_json["reservedImageOutputs"],
        "sessionId": attempt_json["sessionId"],
        "processId": attempt_json["processId"],
        "processGroupId": attempt_json["processGroupId"],
        "processBirthIdentity": attempt_json["processBirthIdentity"],
        "exitCode": attempt_json["processExitCode"],
        "profileHash": attempt_json["profileHash"],
        "requestHash": attempt_json["requestHash"],
        "packageHash": attempt_json["packageHash"],
        "evidenceHash": attempt_json["evidenceHash"],
        "outputHash": attempt_json["outputHash"],
        "remoteOutputHash": attempt_json["remoteOutputHash"],
        "hostState": host_status.state if host_status is not None else None,
        "hostObservationKind": "present" if host_status is not None else "absent",
        "plotloomCodeRevision": attempt_json.get("plotloomCodeRevision"),
        "validationPlanHash": attempt_json.get("validationPlanHash"),
        "receiptHash": checkpoint["evidence"].get("executorReceiptHash"),
        "outputs": receipt_json["outputs"] if receipt_json else [],
        "referenceViews": receipt_json["referenceViews"] if receipt_json else [],
        "imageEvidence": receipt_json["imageEvidence"] if receipt_json else [],
    }


def snapshot(runtime, project_id: str, capture) -> dict:
    """Read actual project/ledger facts; only captured original RPCs explain absence."""
    started_ns = time.monotonic_ns()
    storage = runtime.app.state.project_folder_storage
    host = runtime.bridge.exec_supervisor()
    with sqlite3.connect(f"file:{host.database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        rows = {row["attempt_id"]: row for row in connection.execute("SELECT * FROM exec_attempts")}
        queue = dict(connection.execute("SELECT attempt_id,enabled FROM exec_queue"))
    with closing(storage.projects.inspect(project_id, passive=True)) as store:
        view = store.repository.autopilot.current(project_id)
        if view is None:
            raise RuntimeError("the arm run disappeared")
        attempts = []
        for checkpoint in view.checkpoints:
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
            if attempt is None:
                continue
            stored = rows.get(str(attempt.attempt_id))
            row = ledger_row(stored, queue) if stored is not None else None
            status = (CodexExecHostStatus(state=row.current.state, attempt=row.current,
                receipt=row.receipt, dispatchEnabled=row.dispatch_enabled
                if row.current.state in {"queued", "spawn_intent"} else None) if row is not None else None)
            # Absence gets a fresh package-byte proof. A present ledger row
            # never grants absent-row waiting permission; its immutable package
            # identity is checked against owner preparation and project facts.
            current_hash = prepared_package_hash(runtime, project_id, checkpoint) if row is None else attempt.package_hash
            sample = LedgerSample(started_ns, time.monotonic_ns(), row)
            classification = capture.classify(attempt, checkpoint, sample, current_hash)
            summarized = summarize_attempt(attempt, receipt, checkpoint, status)
            summarized["admissionObservation"] = classification
            attempts.append(summarized)
        return {"run": view.model_dump(mode="json", by_alias=True), "attempts": attempts}


def prepared_package_snapshot(runtime, project_id: str, checkpoint: dict) -> tuple[str, bytes]:
    job_id = checkpoint["evidence"]["jobId"]
    home = runtime.app.state.project_folder_storage.projects._project_home(project_id).path
    text_job = home / "outputs/creative-handoff/jobs" / job_id
    if text_job.is_dir() and not text_job.is_symlink():
        job_root = text_job
    else:
        matches = list((home / "runs").glob(f"*/jobs/{job_id}"))
        if len(matches) != 1 or matches[0].is_symlink():
            raise RuntimeError("prepared image package does not resolve to one exact project-owned path")
        job_root = matches[0]
    package = job_root / "package"
    if package.is_symlink() or not package.is_dir():
        raise RuntimeError("prepared package is not a confined project-owned directory")
    return frozen_package_snapshot(job_root, max_total_bytes=500_000_000)


def prepared_package_hash(runtime, project_id: str, checkpoint: dict) -> str:
    return prepared_package_snapshot(runtime, project_id, checkpoint)[0]


def current_inventory(runtime, project_id: str) -> dict:
    storage = runtime.app.state.project_folder_storage
    with opened_project(storage.projects, project_id) as store:
        run = store.repository.autopilot.current(project_id)
        if run is None:
            raise RuntimeError("the canary run disappeared before inventory")
        inventory = initial_inventory(store, run.policy, enforce_limits=False)
        return inventory.model_dump(mode="json", by_alias=True)


def verify_typed_snapshot_serialization() -> dict:
    """Exercise the exact attempt/receipt/status schema without a host or provider."""
    digest = lambda char: char * 64
    attempt_id, run_id, project_id, session_id = (uuid4() for _ in range(4))
    output = CodexExecOutputEvidence(
        outputHash=digest("e"), outputRelativePath="delivery/candidate.json", sizeBytes=42
    )
    outputs = (output,)
    output_hash = output_manifest_hash(outputs)
    facts = {
        "attemptId": attempt_id, "runId": run_id, "projectId": project_id,
        "jobId": "ch_" + "a" * 32, "operationKey": "outline", "domain": "text",
        "requestHash": digest("f"), "packageHash": digest("d"), "profileHash": digest("c"),
        "reservedImageOutputs": 0, "imageBudgetState": "none", "state": "completed",
        "sessionId": session_id, "processId": 1234, "processGroupId": 1234,
        "processBirthIdentity": "pid:1234:birth:sample", "processExitCode": 0,
        "terminalResult": "success", "remoteToolState": "not_applicable",
        "evidenceHash": digest("b"), "outputHash": output_hash,
    }
    attempt = CodexExecAttempt.model_validate(facts)
    receipt = CodexExecReceipt(
        attemptId=attempt_id, sessionId=session_id, profileHash=digest("c"), requestHash=digest("f"),
        packageHash=digest("d"), processId=1234, processGroupId=1234,
        processBirthIdentity="pid:1234:birth:sample", processExitCode=0, expectedImageOutputs=0,
        evidenceHash=digest("b"), outputHash=output_hash, outputs=outputs,
        remoteToolState="not_applicable",
    )
    status = CodexExecHostStatus(state="completed", attempt=attempt, receipt=receipt)
    summarized = summarize_attempt(attempt, receipt, {"evidence": {"executorReceiptHash": digest("a")}}, status)
    if summarized["sessionId"] != str(session_id) or summarized["outputs"] != [output.model_dump(mode="json", by_alias=True)]:
        raise RuntimeError("typed canary evidence snapshot serialization did not preserve the production model fields")
    class CloseOnlyStore:
        closed = False

        def close(self):
            self.closed = True

    class ProjectFactory:
        store = CloseOnlyStore()

        def open(self, _project_id):
            return self.store

    projects = ProjectFactory()
    with opened_project(projects, str(project_id)) as store:
        if store is not projects.store:
            raise RuntimeError("close-only project open returned a different store")
    if not projects.store.closed:
        raise RuntimeError("close-only ProjectStore was not closed after the snapshot helper scope")
    return {"status": "typed_model_snapshot_and_close_only_store_passed", "domain": summarized["domain"],
            "attemptId": summarized["attemptId"], "sessionId": summarized["sessionId"],
            "outputHash": summarized["outputs"][0]["outputHash"], "receiptHash": summarized["receiptHash"]}
