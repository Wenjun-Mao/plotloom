"""Host-local dispatch to one dedicated native Codex image specialist.

The package exchange remains the authority. This adapter only delivers its
path to a configured local task; queue acknowledgement is not delivery.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
from collections.abc import Callable
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

    def dispatch(self, *, job_id: str, package_path: str, delivery_path: str, assignment: str | None = None, before_send: Callable[[], None] | None = None) -> None:
        self.state_root.mkdir(parents=True, exist_ok=True)
        root = self.state_root / job_id
        active = self.state_root / "inflight.json"
        with self._lease_lock():
            if root.exists():
                raise ImageJobError(
                    "image_dispatch_already_attempted",
                    "this image job already has a native dispatch attempt; it will not be resent automatically",
                )
            if active.exists():
                raise ImageJobError("image_dispatch_busy", "a native specialist job is already in flight")
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
            # Reserve first, then atomically export, then queue. A failed
            # precondition has not sent anything and can release this empty slot.
            try:
                if before_send is not None:
                    before_send()
            except Exception:
                root.rmdir()
                self._release_if_owner_locked(active, job_id)
                raise
        receipt = root / "receipt.json"
        message = assignment or (
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
        record = {"jobId": job_id, "taskId": self.task_id, "state": "queued"}
        wake_state = _bridge_wake_state(completed.stdout)
        if wake_state is not None:
            record["wakeState"] = wake_state
        receipt.write_text(json.dumps(record), encoding="utf-8")
        if wake_state == "open_unconfirmed":
            raise ImageJobError(
                "image_dispatch_wake_unconfirmed",
                "任务已入队，但无法确认助手聊天已打开。请在 Codex 中打开对应助手；请勿重复发送。",
            )

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


def _bridge_wake_state(stdout: str | None) -> str | None:
    """Read only the Mac shim's bounded acknowledgement, not native CLI prose."""
    try:
        value = json.loads(stdout)
    except (ValueError, TypeError):
        return None
    for state in ("open_requested", "open_unconfirmed"):
        if value == {"protocol": "plotloom.native-queue.v1", "wakeState": state}:
            return state
    return None
