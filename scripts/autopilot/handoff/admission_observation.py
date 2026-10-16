"""Observation only: original typed RPC acknowledgements are not ledger rows."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic_ns
from uuid import UUID, uuid4

from plotloom.codex_exec_attempt_contracts import _ATTEMPT_IDENTITY_FIELDS
from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecHostStatus


class ObservationError(RuntimeError):
    pass


def identity(attempt):
    """Use the pinned owner's complete immutable field list, not a subset."""
    current = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
    return tuple((name, getattr(current, name)) for name in _ATTEMPT_IDENTITY_FIELDS)


@dataclass(frozen=True)
class FrozenJob:
    facts: tuple

    @classmethod
    def from_prepared(cls, **facts):
        names = set(_ATTEMPT_IDENTITY_FIELDS) - {"attempt_id"}
        if set(facts) != names:
            raise ObservationError("prepared proof must cover every immutable job field")
        domain = facts["domain"]
        attempt = CodexExecAttempt(attempt_id=UUID(int=0), **facts, state="spawn_intent",
            image_budget_state="reserved" if domain == "image" else "none")
        return cls(tuple(item for item in identity(attempt) if item[0] != "attempt_id"))

    def matches(self, attempt):
        return self.facts == tuple(item for item in identity(attempt) if item[0] != "attempt_id")


@dataclass(frozen=True)
class LedgerRow:
    original: CodexExecAttempt
    current: CodexExecAttempt
    dispatch_enabled: bool | None = None
    worker_pid: int | None = None
    worker_group_id: int | None = None
    worker_birth_identity: str | None = None
    receipt: object | None = None


@dataclass(frozen=True)
class LedgerSample:
    started_ns: int
    finished_ns: int
    row: LedgerRow | None


@dataclass(frozen=True)
class RpcRecord:
    epoch: str
    sequence: int
    operation: str
    attempt_identity: tuple
    started_ns: int
    finished_ns: int
    status: CodexExecHostStatus | None
    error_type: str | None = None


@dataclass
class _Entry:
    attempt_identity: tuple
    intent: CodexExecAttempt
    active: set = field(default_factory=set)
    last_issued: int = 0
    latest: RpcRecord | None = None
    ever_admitted: bool = False
    unsafe: str | None = None


class AdmissionObserver:
    """One owner epoch; never reload deferred acknowledgements from history.

    Wrap only calls production already makes. Every new call revokes the previous
    acknowledgement before delegating. Exceptions/unknowns poison this epoch;
    host presence or project progress permanently revoke absent-row permission.
    """

    OPERATIONS = {"admit", "status", "suspend", "resume", "cancel"}
    CLEANUP_OPERATIONS = {"status", "suspend", "cancel"}

    def __init__(self, *, clock=monotonic_ns, max_records=100_000):
        if type(max_records) is not int or not 1 <= max_records <= 100_000:
            raise ObservationError("observation record bound must be 1..100000")
        self.epoch = str(uuid4())
        self._clock = clock
        self._max_records = max_records
        self._guard = RLock()
        self._jobs = {}
        self._job_attempts = {}
        self._entries = {}
        self._sequence = 0
        self._finished_records = 0
        self._halted = None
        self._records = deque(maxlen=max_records)

    @property
    def records(self):
        with self._guard:
            return tuple(self._records)

    @property
    def discarded_records(self):
        with self._guard:
            return self._finished_records - len(self._records)

    def _poison(self, entry, reason):
        entry.unsafe = entry.unsafe or reason
        self._halted = self._halted or reason

    def _record(self, entry, record):
        entry.active.discard(record.sequence)
        if record.sequence == entry.last_issued:
            entry.latest = record
        self._records.append(record)
        self._finished_records += 1

    def freeze_job(self, proof):
        values = dict(proof.facts)
        checked = FrozenJob.from_prepared(**values)
        if checked != proof:
            raise ObservationError("prepared proof is not the canonical immutable shape")
        job = (str(values["project_id"]), values["job_id"])
        with self._guard:
            prior = self._jobs.setdefault(job, proof)
            if prior != proof:
                for entry in self._entries.values():
                    if (str(entry.intent.project_id), entry.intent.job_id) == job:
                        self._poison(entry, "prepared frozen job changed")
                self._halted = self._halted or "prepared frozen job changed"
                raise ObservationError("prepared frozen job changed")

    def register_intent(self, attempt):
        """Cold owners may read intents; this creates no RPC acknowledgement."""
        with self._guard:
            return self._bind(attempt).intent

    def retained_intent(self, attempt_id):
        """Correlate an already-issued status(id) call without another RPC."""
        with self._guard:
            return self._entries[str(attempt_id)].intent

    def _bind(self, attempt):
        facts = identity(attempt)
        key = str(attempt.attempt_id)
        job = (str(attempt.project_id), attempt.job_id)
        if job not in self._jobs or not self._jobs[job].matches(attempt):
            self._halted = self._halted or "frozen identity or package changed"
            if key in self._entries:
                self._poison(self._entries[key], "frozen identity or package changed")
            raise ObservationError("attempt differs from its prepared immutable proof")
        prior_id = self._job_attempts.setdefault(job, key)
        if prior_id != key:
            self._poison(self._entries[prior_id], "frozen job observed another attempt identity")
            raise ObservationError("one frozen job acquired another attempt identity")
        entry = self._entries.setdefault(key, _Entry(facts, attempt))
        if entry.attempt_identity != facts:
            self._poison(entry, "immutable identity changed")
            raise ObservationError(entry.unsafe)
        entry.intent = attempt
        if attempt.state not in {"reserved", "spawn_intent"}:
            entry.ever_admitted = True
        if attempt.state in {"outcome_unknown", "cancel_requested", "failed"}:
            self._poison(entry, "actual project reports " + attempt.state)
        return entry

    def observe_call(self, operation, attempt, delegate):
        """Delegate this existing call exactly once and return its exact object.

        The closure performs the original call, with its original arguments.
        Capture status/resume/suspend/cancel as well as admit: their later facts
        must supersede old capacity acknowledgements. Status/suspend/cancel still
        delegate during uncertainty, including concurrent original cleanup;
        admit/resume stop across this epoch. No observer-initiated RPC.
        """
        if operation not in self.OPERATIONS:
            raise ObservationError("unsupported existing RPC observation")
        with self._guard:
            entry = self._bind(attempt)
            cleanup = operation in self.CLEANUP_OPERATIONS
            if not cleanup and (self._halted or entry.unsafe or entry.active):
                raise ObservationError(self._halted or entry.unsafe or "same identity has an RPC in flight")
            if self._sequence >= self._max_records:
                self._poison(entry, "observation record limit reached")
                if not cleanup:
                    raise ObservationError(entry.unsafe)
            if operation == "admit" and attempt.state != "spawn_intent":
                raise ObservationError("original admit must use the persisted spawn intent")
            self._sequence += 1
            sequence, started = self._sequence, self._clock()
            entry.active.add(sequence)
            entry.last_issued, entry.latest = sequence, None
        try:
            result = delegate()
        except BaseException as error:
            with self._guard:
                self._poison(entry, "newer RPC raised " + type(error).__name__)
                self._record(entry, RpcRecord(self.epoch, sequence, operation, entry.attempt_identity,
                    started, self._clock(), None, type(error).__name__))
            raise
        with self._guard:
            try:
                if not isinstance(result, CodexExecHostStatus):
                    raise ObservationError("existing RPC did not return the typed host contract")
                status = CodexExecHostStatus.model_validate(result.model_dump(mode="python"))
                if status.attempt is not None and identity(status.attempt) != entry.attempt_identity:
                    raise ObservationError("typed RPC returned another immutable identity")
            except (ValueError, TypeError, ObservationError) as error:
                self._poison(entry, "invalid typed RPC result")
                self._record(entry, RpcRecord(self.epoch, sequence, operation, entry.attempt_identity,
                    started, self._clock(), None, type(error).__name__))
                raise ObservationError(entry.unsafe) from error
            self._record(entry, RpcRecord(self.epoch, sequence, operation, entry.attempt_identity,
                started, self._clock(), status))
            if status.state != "not_found":
                entry.ever_admitted = True
            if status.state in {"outcome_unknown", "cancel_requested", "failed"}:
                self._poison(entry, "newer typed RPC reports " + status.state)
        return result

    def classify(self, project_attempt, *, checkpoint_attempt_id, current_package_hash, sample):
        """Classify a fresh passive observation without fabricating an RPC result."""
        with self._guard:
            entry = self._bind(project_attempt)
            if str(checkpoint_attempt_id) != str(project_attempt.attempt_id) or current_package_hash != project_attempt.package_hash:
                self._poison(entry, "checkpoint or current package differs")
            if self._halted or entry.unsafe:
                raise ObservationError(self._halted or entry.unsafe)
            if sample.finished_ns < sample.started_ns:
                raise ObservationError("invalid passive sampling interval")
            if entry.active:
                raise ObservationError("fresh observation must follow the already-issued RPC")
            latest = entry.latest
            if latest is not None and sample.started_ns < latest.finished_ns:
                raise ObservationError("passive sample predates the newest RPC outcome")
            row = sample.row
            if row is not None:
                if identity(row.original) != entry.attempt_identity or identity(row.current) != entry.attempt_identity:
                    self._poison(entry, "ledger immutable identity differs")
                    raise ObservationError(entry.unsafe)
                entry.ever_admitted = True
                current = row.current
                if current.state in {"outcome_unknown", "cancel_requested", "failed"}:
                    self._poison(entry, "actual ledger reports " + current.state)
                    raise ObservationError(entry.unsafe)
                if current.state == "completed":
                    CodexExecHostStatus(state=current.state, attempt=current, receipt=row.receipt)
                return "host_" + current.state
            if (latest is not None and latest.operation == "admit" and latest.status is not None
                    and latest.status.state == "not_found" and latest.status.capacity_deferred
                    and project_attempt.state == "spawn_intent" and not entry.ever_admitted):
                return "known_capacity_wait"
            raise ObservationError("absent ledger row has no current exact admission deferral proof")
