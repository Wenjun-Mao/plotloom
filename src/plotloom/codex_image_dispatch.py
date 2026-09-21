"""Host-local dispatch to one dedicated native Codex image specialist.

The package exchange remains the authority. This adapter only delivers its
path to a configured local task; queue acknowledgement is not delivery.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .image_job_contracts import ImageJobError


@dataclass(frozen=True)
class NativeCodexImageDispatcher:
    """Queue one immutable package once with a crash-safe local reservation."""

    task_id: str
    state_root: Path
    executable: str = "codex"

    def dispatch(self, *, job_id: str, package_path: str, delivery_path: str) -> None:
        self.state_root.mkdir(parents=True, exist_ok=True)
        root = self.state_root / job_id
        active = self.state_root / "inflight.json"
        with self._lease_lock():
            if root.exists():
                raise ImageJobError(
                    "image_dispatch_already_attempted",
                    "this image job already has a native dispatch attempt; it will not be resent automatically",
                )
            try:
                descriptor = os.open(
                    active, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
            except FileExistsError as error:
                raise ImageJobError(
                    "image_dispatch_busy",
                    "a native image specialist job is already in flight",
                ) from error
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump({"jobId": job_id, "taskId": self.task_id}, output)
            try:
                root.mkdir(mode=0o700)
            except FileExistsError as error:
                self._release_if_owner_locked(active, job_id)
                raise ImageJobError(
                    "image_dispatch_already_attempted",
                    "this image job already has a native dispatch attempt; it will not be resent automatically",
                ) from error
        receipt = root / "receipt.json"
        message = (
            f"Frozen Plotloom image package assignment for {job_id}. Read and obey the "
            f"project-local plotloom-image-specialist skill. The package is complete authority: "
            f"{package_path}. Deliver only under {delivery_path}. Do not modify Plotloom code, "
            "canonical data, selections, or this package. Do not use H3 or Qwen."
        )
        try:
            completed = subprocess.run(
                [self.executable, "queue", "--thread", self.task_id, "--message", message],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            receipt.write_text(json.dumps({"jobId": job_id, "taskId": self.task_id, "state": "outcome_unknown"}), encoding="utf-8")
            raise ImageJobError(
                "image_dispatch_outcome_unknown",
                "native image dispatch outcome is unknown; Plotloom will not retry this job",
            ) from error
        if completed.returncode != 0:
            # The supported queue CLI exposes no receipt identity or outcome
            # guarantee for a nonzero exit.  It may have accepted the message
            # before the caller lost acknowledgement. Only terminal delivery
            # may release this one-worker lease.
            receipt.write_text(json.dumps({"jobId": job_id, "taskId": self.task_id, "state": "outcome_unknown"}), encoding="utf-8")
            raise ImageJobError(
                "image_dispatch_outcome_unknown",
                "native image dispatch outcome is unknown; Plotloom will not retry this job",
            )
        receipt.write_text(json.dumps({"jobId": job_id, "taskId": self.task_id, "state": "queued"}), encoding="utf-8")

    def complete(self, job_id: str) -> None:
        """Release the one-job gate only after terminal repository handling."""

        active = self.state_root / "inflight.json"
        with self._lease_lock():
            self._release_if_owner_locked(active, job_id)

    @contextmanager
    def _lease_lock(self):
        self.state_root.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_root / "inflight.lock"
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _release_if_owner_locked(self, active: Path, job_id: str) -> None:
        try:
            record = json.loads(active.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return
        if record == {"jobId": job_id, "taskId": self.task_id}:
            active.unlink()
