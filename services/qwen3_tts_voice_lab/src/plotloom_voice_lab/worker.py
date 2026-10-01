"""One serial worker, with model lifetime bounded by each supervised process."""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path

from .engines.process import EngineFailure
from .media import file_sha256, persist_candidate_file, persist_clone_file, persist_reference_file
from .dispatch import ExecutionGrant, LaneClient, RegistrationWorker
from .store import Store

LOGGER = logging.getLogger(__name__)


class Worker:
    def __init__(self, store: Store, engine, lane_client=None):
        self.store = store
        self.engine = engine
        self.tasks = queue.Queue()
        self.lane_client = lane_client or LaneClient()
        self.registration = RegistrationWorker(store, self.lane_client)
        self.thread = threading.Thread(target=self._loop, name="voice-lab-worker", daemon=True)
        self.active: tuple[str, str] | None = None
        self.phase: str | None = None
        self.started_at: float | None = None
        self.state_lock = threading.Lock()
        self.stopping = threading.Event()

    def start(self) -> None:
        self.thread.start()
        self.registration.start()

    def stop(self) -> None:
        self.stopping.set()
        self.registration.stop()
        if hasattr(self.lane_client, "stop"):
            self.lane_client.stop()
        self.engine.stop()
        self.tasks.put(None)
        self.thread.join(timeout=8)
        if self.thread.is_alive():
            raise RuntimeError("worker.shutdown_failed")

    def submit(self, kind: str, task_id: str) -> None:
        if kind not in {"generation", "clone", "take"}:
            raise ValueError("worker.unknown_job_kind")
        if self.stopping.is_set():
            raise ValueError("worker.stopping")
        # Domain admission already wrote its outbox transactionally. Only a
        # private shared-lane grant can put inference on the execution queue.

    def execute(self, grant: ExecutionGrant):
        if self.stopping.is_set():
            raise ValueError("worker.stopping")
        if self.store.dispatch.authorize(grant):
            self.tasks.put((grant.kind, grant.jobId, grant.grantId))
        return self.store.dispatch.execution(grant.grantId)

    def progress(self, kind: str, task_id: str) -> dict:
        """Project the actual serial queue, never an inferred model percentage."""
        target = (kind, task_id)
        with self.state_lock:
            active, phase, started_at = self.active, self.phase, self.started_at
        if active == target:
            return {"queueAhead": 0, "phase": phase,
                    "elapsedSeconds": round(time.monotonic() - started_at, 1) if started_at is not None else None}
        try:
            result = self.lane_client.progress(task_id)
            return {**result, "elapsedSeconds": None}
        except (ValueError, OSError):
            return {"queueAhead": None, "phase": "waiting_for_registration", "elapsedSeconds": None}

    def _phase(self, value: str) -> None:
        with self.state_lock:
            self.phase = value

    def _loop(self) -> None:
        while True:
            task = self.tasks.get()
            if task is None:
                self.tasks.task_done()
                return
            kind, task_id, grant_id = task
            if self.stopping.is_set():
                self._fail(kind, task_id, "generation.interrupted")
                self.store.dispatch.release(grant_id, confirmed=self.engine.release_confirmed())
                self.tasks.task_done()
                continue
            with self.state_lock:
                self.active, self.phase, self.started_at = (kind, task_id), "starting", time.monotonic()
            try:
                if kind == "generation":
                    self._run_generation(task_id)
                elif kind == "clone":
                    self._run_clone(task_id)
                else:
                    self._run_take(task_id)
            except EngineFailure as error:
                self._fail(kind, task_id, str(error))
            except ValueError:
                LOGGER.exception("invalid voice lab result for %s %s", kind, task_id)
                self._fail(kind, task_id, "audio.invalid")
            except Exception:
                LOGGER.exception("voice lab worker could not finish %s %s", kind, task_id)
                self._fail(kind, task_id, "generation.failed")
            finally:
                native = self.store.data_dir / "runs" / task_id / "audio.wav"
                with self.store.connection() as db:
                    self.store.enqueue_cleanup(db, [str(native)])
                self.store.run_cleanup()
                self.store.dispatch.release(grant_id, confirmed=self.engine.release_confirmed())
                with self.state_lock:
                    self.active, self.phase, self.started_at = None, None, None
                self.tasks.task_done()

    def _fail(self, kind: str, task_id: str, code: str) -> None:
        if kind == "generation":
            self.store.generations.fail(task_id, code)
        elif kind == "clone":
            self.store.clones.mark(task_id, "interrupted" if code == "generation.interrupted" else "failed", code)
        elif self.store.takes.get(task_id)["status"] in {"queued", "running"}:
            self.store.takes.mark(task_id, "interrupted" if code == "generation.interrupted" else "failed", code)

    def _run_generation(self, generation_id: str) -> None:
        generation = self.store.generations.get(generation_id)
        self.store.generations.mark_running(generation_id)
        native, _metrics = self.engine.run(
            generation["executionSnapshot"],
            {"text": generation["auditionText"], "direction": "\n".join(
                value for value in (generation["brief"], generation["direction"]) if value),
             "seed": generation["seed"]},
            self.store.data_dir / "runs" / generation_id, self._phase, lambda _value: None,
        )
        self._phase("preparing_audio")
        media = persist_candidate_file(self.store.data_dir, generation["candidateId"], generation_id,
                                       native, generation["executionSnapshot"]["sampleRate"])
        media["audioDetails"]["executionMetrics"] = _metrics
        self._phase("finalizing")
        self.store.generations.complete(generation_id, media)

    def _run_clone(self, trial_id: str) -> None:
        trial = self.store.clones.get(trial_id, private=True)
        reference = Path(trial["referencePath"]) if trial["referencePath"] else None
        if reference is None or not reference.is_file() or file_sha256(reference) != trial["sourceSha256"]:
            raise EngineFailure("reference.corrupt")
        self.store.clones.mark(trial_id, "running")
        native, _metrics = self.engine.run(
            trial["executionSnapshot"],
            {"text": trial["text"], "seed": trial["seed"], "reference": str(reference),
             "referenceText": trial["referenceText"], "delivery": trial["delivery"]},
            self.store.data_dir / "runs" / trial_id, self._phase,
            lambda value: self.store.clones.record_execution(trial_id, value),
        )
        self._phase("preparing_audio")
        media = persist_clone_file(self.store.data_dir, trial_id, native, trial["executionSnapshot"]["sampleRate"])
        media["audioDetails"]["executionMetrics"] = _metrics
        self._phase("finalizing")
        self.store.clones.mark(trial_id, "completed", media=media)

    def _run_take(self, take_id):
        take = self.store.takes.get(take_id, private=True)
        reference = Path(take["referencePath"])
        if not reference.is_file() or file_sha256(reference) != take["referenceSha256"]:
            raise EngineFailure("reference.corrupt")
        self.store.takes.mark(take_id, "running")
        native, metrics = self.engine.run(
            take["executionSnapshot"],
            {"text": take["text"], "seed": take["seed"], "reference": str(reference),
             "referenceText": take["referenceText"], "delivery": take["delivery"]},
            self.store.data_dir / "runs" / take_id, self._phase,
            lambda value: self.store.takes.record_execution(take_id, value),
        )
        self._phase("preparing_audio")
        target = self.store.data_dir / "takes" / take_id
        try:
            media = persist_reference_file(target, native, take["executionSnapshot"]["sampleRate"])
            media["audioDetails"]["executionMetrics"] = metrics
            self._phase("finalizing")
            self.store.takes.mark(take_id, "completed", media=media)
        except Exception:
            with self.store.connection() as db:
                self.store.enqueue_cleanup(db, [str(target / "source.wav"), str(target / "h3.wav")])
            raise
