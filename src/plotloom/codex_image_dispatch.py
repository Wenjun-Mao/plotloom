"""Host-local dispatch to one dedicated native Codex image specialist.

The package exchange remains the authority. This adapter only delivers its
path to a configured local task; queue acknowledgement is not delivery.
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import fcntl

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
            # A cancelled or conflicted package is not proof that its specialist
            # stopped. Before rejecting a later job as busy, ask the supported
            # app server whether this exact configured task is authoritatively idle.
            self._reconcile_idle_worker_locked(active)
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
            # before the caller lost acknowledgement, so terminal delivery or
            # authoritative exact-task idle reconciliation may release this
            # one-worker lease.
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

    def reconcile_idle_worker(self) -> bool:
        """Release only when app-server reports this exact task as idle."""

        active = self.state_root / "inflight.json"
        with self._lease_lock():
            return self._reconcile_idle_worker_locked(active)

    def _reconcile_idle_worker_locked(self, active: Path) -> bool:
        try:
            record = json.loads(active.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return False
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("jobId"), str)
            or record.get("taskId") != self.task_id
        ):
            return False
        if self._thread_status() != "idle":
            return False
        self._release_if_owner_locked(active, record["jobId"])
        return not active.exists()

    def _thread_status(self) -> str | None:
        """Read current task state through the supported app-server proxy."""

        requests = "\n".join(
            (
                json.dumps(
                    {
                        "method": "initialize",
                        "id": 1,
                        "params": {
                            "clientInfo": {
                                "name": "plotloom_native_image_dispatch",
                                "title": "Plotloom native image dispatch",
                                "version": "1",
                            }
                        },
                    }
                ),
                json.dumps({"method": "initialized", "params": {}}),
                json.dumps(
                    {
                        "method": "thread/read",
                        "id": 2,
                        "params": {"threadId": self.task_id},
                    }
                ),
            )
        )
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                [self.executable, "app-server", "proxy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if process.stdin is None or process.stdout is None:
                return None
            process.stdin.write(f"{requests}\n")
            process.stdin.flush()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                ready, _, _ = select.select(
                    [process.stdout], [], [], deadline - time.monotonic()
                )
                if not ready:
                    break
                line = process.stdout.readline()
                if not line:
                    break
                try:
                    response = json.loads(line)
                    status = response["result"]["thread"]["status"]["type"]
                except (KeyError, TypeError, json.JSONDecodeError):
                    continue
                return status if isinstance(status, str) else None
        except (OSError, ValueError):
            return None
        finally:
            if process is not None:
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        process.kill()
                    except OSError:
                        pass
        return None

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
