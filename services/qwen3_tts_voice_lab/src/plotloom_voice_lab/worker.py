"""One serial, non-replaying inference worker for specialist casting."""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path

from .engine import ModelIntegrityError
from .media import file_sha256, persist_candidate, persist_clone
from .store import BASE_REVISION, DESIGN_REVISION, Store


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
                if kind == "round":
                    self._run_round(task_id)
                else:
                    self._run_clone(task_id)
            except Exception:
                LOGGER.exception("voice lab worker could not finish %s %s", kind, task_id)
                if kind == "round":
                    self.store.mark_round(task_id, "failed", "generation.failed")
                else:
                    self.store.mark_clone(task_id, "failed", "generation.failed")
            finally:
                self.active = None
                self.tasks.task_done()

    def _run_round(self, round_id: str) -> None:
        self.store.mark_round(round_id, "running")
        round_data = self.store.get_round(round_id)
        assert round_data is not None
        candidates = round_data["candidates"]
        if any(candidate["modelRevision"] != DESIGN_REVISION for candidate in candidates):
            for candidate in candidates:
                self.store.fail_candidate(candidate["candidateId"], "model.snapshot_stale")
            self.store.mark_round(round_id, "failed", "model.snapshot_stale")
            return
        try:
            with self.engine.design_session() as session:
                for candidate in candidates:
                    candidate_id = candidate["candidateId"]
                    self.store.mark_candidate_running(candidate_id)
                    try:
                        waveform, sample_rate = session.generate(
                            round_data["auditionText"], candidate["direction"], candidate["seed"],
                        )
                        media = persist_candidate(self.store.data_dir, candidate_id, waveform, sample_rate)
                        self.store.complete_candidate(candidate_id, media)
                    except ValueError:
                        self.store.fail_candidate(candidate_id, "audio.invalid")
                    except Exception:
                        LOGGER.exception("candidate generation failed for %s", candidate_id)
                        self.store.fail_candidate(candidate_id, "generation.failed")
        except FileNotFoundError:
            for candidate in candidates:
                self.store.fail_candidate(candidate["candidateId"], "model.unavailable")
        except ModelIntegrityError:
            for candidate in candidates:
                self.store.fail_candidate(candidate["candidateId"], "model.weights_changed")
        except Exception:
            LOGGER.exception("voice design model could not load for %s", round_id)
            for candidate in candidates:
                self.store.fail_candidate(candidate["candidateId"], "model.load_failed")

        latest = self.store.get_round(round_id)
        assert latest is not None
        statuses = [candidate["status"] for candidate in latest["candidates"]]
        if all(status == "completed" for status in statuses):
            self.store.mark_round(round_id, "completed")
        elif any(status == "completed" for status in statuses):
            self.store.mark_round(round_id, "partial", "generation.partial")
        else:
            self.store.mark_round(round_id, "failed", "generation.failed")

    def _run_clone(self, clone_id: str) -> None:
        clone = self.store.get_clone(clone_id)
        assert clone is not None
        if clone["modelRevision"] != BASE_REVISION:
            self.store.mark_clone(clone_id, "failed", "model.snapshot_stale")
            return
        candidate = self.store.get_candidate(clone["candidateId"], private=True)
        assert candidate is not None
        round_data = self.store.get_round(candidate["roundId"])
        assert round_data is not None
        self.store.mark_clone(clone_id, "running")
        reference = Path(candidate["sourcePath"]) if candidate["sourcePath"] else None
        if reference is None or not reference.is_file() or file_sha256(reference) != clone["sourceSha256"]:
            self.store.mark_clone(clone_id, "failed", "reference.corrupt")
            return
        try:
            with self.engine.clone_session() as session:
                waveform, sample_rate = session.generate(
                    clone["text"], reference, round_data["auditionText"], clone["seed"],
                )
                media = persist_clone(self.store.data_dir, clone_id, waveform, sample_rate)
            self.store.mark_clone(clone_id, "completed", media=media)
        except FileNotFoundError:
            self.store.mark_clone(clone_id, "failed", "model.unavailable")
        except ModelIntegrityError:
            self.store.mark_clone(clone_id, "failed", "model.weights_changed")
        except ValueError:
            self.store.mark_clone(clone_id, "failed", "audio.invalid")
        except Exception:
            LOGGER.exception("clone generation failed for %s", clone_id)
            self.store.mark_clone(clone_id, "failed", "generation.failed")
