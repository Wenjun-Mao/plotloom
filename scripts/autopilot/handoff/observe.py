"""Passive current-ledger/process observer; never dispatches or settles an attempt."""
import json
import sqlite3
import subprocess
import threading
import time

from plotloom.codex_exec_contracts import CodexExecAttempt


class Observer:
    def __init__(self, host, emit):
        self.host, self.emit = host, emit
        self.stop = threading.Event()
        self.gates = {}
        self.failure = None
        self.latest = []
        self.samples = 0
        self.work_ns = 0
        self.thread = threading.Thread(target=self.run, name="native-proof-observer", daemon=True)

    def run(self):
        previous = None
        stable_samples = 0
        previous_states = {}
        previous_validators = None
        previous_sample_ns = None
        try:
            while not self.stop.is_set():
                work_started = time.monotonic_ns()
                with sqlite3.connect(f"file:{self.host.database}?mode=ro", uri=True) as connection:
                    connection.row_factory = sqlite3.Row
                    connection.execute("BEGIN")
                    rows = connection.execute("SELECT * FROM exec_attempts").fetchall()
                    held = connection.execute("SELECT domain,COUNT(*) FROM exec_slot GROUP BY domain").fetchall()
                    queue = dict(connection.execute("SELECT attempt_id,enabled FROM exec_queue"))
                    validators = [dict(row) for row in connection.execute("SELECT * FROM exec_validation_process")]
                for row in rows:
                    current = CodexExecAttempt.model_validate_json(row["status_json"])
                    identity = str(current.attempt_id)
                    facts = {"attemptId": identity, "state": current.state, "domain": current.domain,
                        "operationKey": current.operation_key, "projectId": str(current.project_id),
                        "processId": current.process_id, "processGroupId": current.process_group_id,
                        "processBirthIdentity": current.process_birth_identity,
                        "workerPid": row["worker_pid"], "workerGroupId": row["worker_group_id"],
                        "workerBirthIdentity": row["worker_birth_identity"], "dispatchEnabled": queue.get(identity),
                        "imageBudgetState": current.image_budget_state, "reservedImageOutputs": current.reserved_image_outputs}
                    if previous_states.get(identity) != facts:
                        self.emit("host_state_observed", **facts, hostLastUpdatedUtcUnix=row["updated_at"],
                            observationWindowStartNs=previous_sample_ns, sampleStartedNs=work_started)
                        previous_states[identity] = facts
                if validators != previous_validators:
                    self.emit("validator_state_observed", validators=validators, observationWindowStartNs=previous_sample_ns, sampleStartedNs=work_started)
                    previous_validators = validators
                live = []
                for row in rows:
                    attempt = json.loads(row["status_json"])
                    pid = attempt.get("processId")
                    if not pid or attempt["state"] != "running":
                        continue
                    try:
                        identity = self.host._process_identity(pid)
                    except (OSError, subprocess.SubprocessError, ValueError):
                        continue
                    if identity != (attempt["processGroupId"], attempt["processBirthIdentity"]):
                        continue
                    live.append({key: attempt[key] for key in ("attemptId", "projectId", "domain", "processId", "processGroupId", "processBirthIdentity")})
                counts = {domain: sum(item["domain"] == domain for item in live) for domain in ("text", "image")}
                limits = self.host.pool_limits
                if len(live) > limits.max_processes or counts["text"] > limits.max_text_processes or counts["image"] > limits.max_image_processes:
                    raise RuntimeError("actual native process count exceeds frozen pool capacity")
                held_counts = {row[0]: row[1] for row in held}
                if sum(held_counts.values()) > limits.max_processes or any(held_counts.get(domain, 0) > limits.domain_capacity(domain) for domain in ("text", "image")):
                    raise RuntimeError("durable capacity exceeds frozen pool limits")
                if sum(enabled for identity, enabled in queue.items() if json.loads(next(row["status_json"] for row in rows if row["attempt_id"] == identity))["state"] == "queued") > limits.max_queued_jobs:
                    raise RuntimeError("enabled queue exceeds frozen authorization")
                signature = tuple(sorted((item["attemptId"], item["processId"], item["processGroupId"], item["processBirthIdentity"]) for item in live))
                previous_sample_ns = work_started
                stable_samples = stable_samples + 1 if signature == previous else 1
                self.latest = live
                if signature != previous:
                    self.emit("live_native_processes", processes=live, held=held_counts)
                    previous = signature
                if stable_samples < 2:
                    self.samples += 1
                    self.work_ns += time.monotonic_ns() - work_started
                    self.stop.wait(1)
                    continue
                if counts["text"] >= 1 and counts["image"] >= 1 and "cross" not in self.gates:
                    self.gates["cross"] = time.monotonic_ns()
                    self.emit("ordered_gate", gate="cross", processes=live)
                if "cross" in self.gates and counts["image"] == 2 and "images" not in self.gates:
                    self.gates["images"] = time.monotonic_ns()
                    self.emit("ordered_gate", gate="images", processes=live)
                text_projects = {item["projectId"] for item in live if item["domain"] == "text"}
                if "images" in self.gates and len(text_projects) == 2 and "texts" not in self.gates:
                    self.gates["texts"] = time.monotonic_ns()
                    self.emit("ordered_gate", gate="texts", processes=live)
                self.samples += 1
                self.work_ns += time.monotonic_ns() - work_started
                self.stop.wait(1)
        except BaseException as error:
            self.failure = type(error).__name__ + ": " + str(error)
            self.emit("observer_failure", error=self.failure)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(timeout=35)
        if self.thread.is_alive():
            raise RuntimeError("passive observer did not finish")
        self.emit("observer_summary", samples=self.samples, elapsedWorkNs=self.work_ns, cadenceSeconds=1)
        if self.failure:
            raise RuntimeError(self.failure)
