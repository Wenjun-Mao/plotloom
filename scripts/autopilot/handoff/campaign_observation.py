"""Capture existing registry calls; never drive the host merely to observe it."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import UUID

from admission_observation import AdmissionObserver, FrozenJob, ObservationError
from plotloom.codex_exec_contracts import CodexExecProfile


def json_facts(items):
    return {key: str(value) if isinstance(value, UUID) else value for key, value in items}


class _StreamingObserver(AdmissionObserver):
    """The pinned owner's protected record hook supplies exactly one new record.

    Keep the reviewed module byte-identical. Do not repeatedly copy its complete
    records property, or drain its deque and falsify discarded-record accounting.
    The base implementation retains every original state/ordering/safety decision.
    """

    def __init__(self, sink, **options):
        super().__init__(**options)
        self._sink = sink

    def _record(self, entry, record):
        super()._record(entry, record)
        self._sink(record)


class CampaignObservation:
    def __init__(self, runtime, work, emit, package_reader, *, image_owners, max_records=100_000,
            freeze_attempt=None, halt=None):
        self.runtime, self.work, self.emit = runtime, Path(work), emit
        self.package_reader, self.image_owners = package_reader, set(image_owners)
        self.failure = None
        self.records_emitted = 0
        self.write_work_ns = 0
        self.frozen_jobs = {}
        self.freeze_attempt, self.halt = freeze_attempt, halt
        self.capacity_deferrals = set()
        self.observer = _StreamingObserver(self._record, max_records=max_records)

    def _record(self, record):
        started = time.monotonic_ns()
        try:
            row = {"epoch": record.epoch, "sequence": record.sequence,
                "operation": record.operation, "attemptIdentity": json_facts(record.attempt_identity),
                "startedNs": record.started_ns, "finishedNs": record.finished_ns,
                "status": record.status.model_dump(mode="json", by_alias=True) if record.status is not None else None,
                "errorType": record.error_type}
            with (self.work / "rpc_observations.jsonl").open("ab") as stream:
                stream.write((json.dumps(row, sort_keys=True) + "\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
            self.records_emitted += 1
        except BaseException as error:
            # A capture failure forbids further admission, but must not suppress
            # the exact original cleanup call or replace its typed return object.
            self.failure = self.failure or "RPC evidence persistence failed: " + type(error).__name__
            if not isinstance(error, Exception):
                raise
        finally:
            self.write_work_ns += time.monotonic_ns() - started

    def freeze_prepared(self, project_id, snapshot, role):
        run = snapshot["run"]
        policy = run["policy"]
        profile = CodexExecProfile.model_validate(policy["executorBinding"])
        if str(run["projectId"]) != str(project_id) or not policy["codeRevision"]:
            raise ObservationError("prepared proof has no current source-pinned owner")
        for checkpoint in run["checkpoints"]:
            evidence, operation = checkpoint["evidence"], checkpoint["operationKey"]
            if checkpoint["state"] != "prepared" or not evidence.get("jobId") or evidence.get("executorAttemptId"):
                continue
            image = evidence["owner"] in self.image_owners
            if not image and (operation not in policy["executionPins"] or operation == "image"):
                continue
            package_hash, request = self.package_reader(self.runtime, project_id, checkpoint)
            validation_hash = None
            if not image:
                from plotloom.codex_exec_validation import validation_plan_from_package
                validation_hash = validation_plan_from_package(json.loads(request)).plan_hash
            proof = FrozenJob.from_prepared(project_id=project_id, run_id=run["id"],
                job_id=evidence["jobId"], operation_key=operation,
                domain="image" if image else "text", request_hash=evidence["requestHash"],
                package_hash=package_hash, profile_hash=profile.profile_hash,
                plotloom_code_revision=policy["codeRevision"], validation_plan_hash=validation_hash,
                reserved_image_outputs=int(image))
            self.observer.freeze_job(proof)
            key = (str(project_id), evidence["jobId"])
            if key not in self.frozen_jobs:
                self.emit("before_attempt_admission", role=role, projectId=str(project_id),
                    jobId=evidence["jobId"], operationKey=operation,
                    requestHash=evidence["requestHash"], packageHash=package_hash,
                    observerEpoch=self.observer.epoch, frozenIdentity=json_facts(proof.facts))
                self.frozen_jobs[key] = proof

    def _call(self, operation, argument, original):
        if operation in {"admit", "resume"} and self.failure:
            raise ObservationError(self.failure)
        attempt = self.observer.retained_intent(argument) if operation == "status" else argument
        key = str(attempt.attempt_id)
        try:
            entry = self.observer._entries.get(key)
            if operation == 'admit' and entry is not None and entry.last_issued and key not in self.capacity_deferrals:
                raise ObservationError('original admission cannot be resent from absent/uncertain host state')
            def invoke():
                if self.freeze_attempt and operation in {'admit','suspend','cancel'}:
                    self.freeze_attempt(attempt,settlement_only=operation!='admit')
                return original(argument)
            result = self.observer.observe_call(operation, attempt, invoke)
            if result.state != 'not_found':
                self.capacity_deferrals.discard(key)
            elif operation == 'admit':
                if result.capacity_deferred:
                    self.capacity_deferrals.add(key)
                else:
                    self.observer._poison(self.observer._entries[key],'original admission acknowledgement is uncertain')
            if self.halt and (self.failure or self.observer._halted):
                self.halt(self.failure or self.observer._halted)
            return result
        except BaseException:
            if self.halt:
                try:
                    self.halt('uncertain_original_'+operation)
                except Exception as error:
                    self.failure = self.failure or 'durable HALT failed: '+type(error).__name__
            raise

    @contextmanager
    def installed(self):
        registry = self.runtime.app.state.specialists
        originals = {}
        try:
            for operation in sorted(self.observer.OPERATIONS):
                name = "codex_exec_" + operation
                original = getattr(registry, name)
                originals[name] = (name in registry.__dict__, original)
                def wrapped(argument, operation=operation, original=original):
                    return self._call(operation, argument, original)
                setattr(registry, name, wrapped)
            yield self
        finally:
            for name, (instance_owned, original) in originals.items():
                if instance_owned:
                    setattr(registry, name, original)
                else:
                    delattr(registry, name)

    def classify(self, attempt, checkpoint, sample, current_package_hash):
        if self.failure:
            raise ObservationError(self.failure)
        return self.observer.classify(attempt,
            checkpoint_attempt_id=checkpoint["evidence"].get("executorAttemptId"),
            current_package_hash=current_package_hash, sample=sample)

    def summary(self):
        owner = self.observer
        with owner._guard:
            status = {"epoch": owner.epoch, "recordsEmitted": self.records_emitted,
                "recordsFinished": owner._finished_records, "lastIssuedSequence": owner._sequence,
                "discardedRecords": owner.discarded_records,
                "activeRpcCount": sum(len(entry.active) for entry in owner._entries.values()),
                "halted": owner._halted, "persistenceFailure": self.failure,
                "recordWriteWorkNs": self.write_work_ns, "frozenJobs": len(self.frozen_jobs)}
        path = self.work / "rpc_observations.jsonl"
        status["recordsSha256"] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        return status

    def require_complete(self):
        status = self.summary()
        if (not status["recordsEmitted"] or status["halted"] or status["persistenceFailure"] or status["discardedRecords"]
                or status["activeRpcCount"] or status["recordsEmitted"] != status["recordsFinished"]):
            raise ObservationError("RPC observation epoch is incomplete, truncated or unsafe")
        return status
