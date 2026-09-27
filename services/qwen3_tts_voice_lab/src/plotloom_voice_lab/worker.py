"""One serial, non-replaying inference worker for specialist casting."""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path

from .engine import ModelIntegrityError
from .identity import BASE_REVISION, DESIGN_REVISION
from .media import file_sha256, persist_candidate, persist_clone
from .store import Store

LOGGER = logging.getLogger(__name__)


class Worker:
    def __init__(self, store: Store, engine):
        self.store = store
        self.engine = engine
        self.tasks: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self.thread = threading.Thread(target=self._loop, name="voice-lab-worker", daemon=True)
        self.active: tuple[str, str] | None = None

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.tasks.put(None)
        self.thread.join(timeout=2)

    def submit(self, kind: str, task_id: str) -> None:
        if kind not in {"generation", "clone"}:
            raise ValueError("worker.unknown_job_kind")
        self.tasks.put((kind, task_id))

    def _loop(self) -> None:
        while True:
            task = self.tasks.get()
            if task is None:
                self.tasks.task_done()
                return
            self.active = task
            kind, task_id = task
            try:
                if kind == "generation":
                    self._run_generation(task_id)
                else:
                    self._run_clone(task_id)
            except Exception:
                LOGGER.exception("voice lab worker could not finish %s %s", kind, task_id)
                if kind == "generation":
                    self.store.generations.fail(task_id, "generation.failed")
                else:
                    self.store.clones.mark(task_id, "failed", "generation.failed")
            finally:
                self.active = None
                self.tasks.task_done()

    def _run_generation(self, generation_id: str) -> None:
        generation = self.store.generations.get(generation_id)
        if generation["modelRevision"] != DESIGN_REVISION:
            self.store.generations.fail(generation_id, "model.snapshot_stale")
            return
        self.store.generations.mark_running(generation_id)
        try:
            with self.engine.design_session() as session:
                waveform, sample_rate = session.generate(
                    generation["auditionText"],
                    "\n".join(value for value in (generation["brief"], generation["direction"]) if value),
                    generation["seed"],
                )
                media = persist_candidate(
                    self.store.data_dir, generation["candidateId"], generation_id,
                    waveform, sample_rate,
                )
            self.store.generations.complete(generation_id, media)
        except FileNotFoundError:
            self.store.generations.fail(generation_id, "model.unavailable")
        except ModelIntegrityError:
            self.store.generations.fail(generation_id, "model.weights_changed")
        except ValueError:
            self.store.generations.fail(generation_id, "audio.invalid")
        except Exception:
            LOGGER.exception("voice generation failed for %s", generation_id)
            self.store.generations.fail(generation_id, "generation.failed")

    def _run_clone(self, trial_id: str) -> None:
        trial = self.store.clones.get(trial_id, private=True)
        if trial["modelRevision"] != BASE_REVISION:
            self.store.clones.mark(trial_id, "failed", "model.snapshot_stale")
            return
        reference = Path(trial["referencePath"]) if trial["referencePath"] else None
        if reference is None or not reference.is_file() or file_sha256(reference) != trial["sourceSha256"]:
            self.store.clones.mark(trial_id, "failed", "reference.corrupt")
            return
        self.store.clones.mark(trial_id, "running")
        try:
            with self.engine.clone_session() as session:
                waveform, sample_rate = session.generate(
                    trial["text"], reference, trial["referenceText"], trial["seed"],
                )
                media = persist_clone(self.store.data_dir, trial_id, waveform, sample_rate)
            self.store.clones.mark(trial_id, "completed", media=media)
        except FileNotFoundError:
            self.store.clones.mark(trial_id, "failed", "model.unavailable")
        except ModelIntegrityError:
            self.store.clones.mark(trial_id, "failed", "model.weights_changed")
        except ValueError:
            self.store.clones.mark(trial_id, "failed", "audio.invalid")
        except Exception:
            LOGGER.exception("clone generation failed for %s", trial_id)
            self.store.clones.mark(trial_id, "failed", "generation.failed")
