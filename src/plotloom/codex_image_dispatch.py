"""Host-local dispatch to one dedicated native Codex image specialist.

The package exchange remains the authority. This adapter only delivers its
path to a configured local task; queue acknowledgement is not delivery.
"""
from __future__ import annotations

import json
import os
import subprocess
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
        try:
            root.mkdir(mode=0o700)
        except FileExistsError as error:
            raise ImageJobError(
                "image_dispatch_already_attempted",
                "this image job already has a native dispatch attempt; it will not be resent automatically",
            ) from error
        active = self.state_root / "inflight.json"
        try:
            descriptor = os.open(active, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as error:
            raise ImageJobError(
                "image_dispatch_busy",
                "a native image specialist job is already in flight",
            ) from error
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump({"jobId": job_id}, output)
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
            receipt.write_text(json.dumps({"jobId": job_id, "state": "outcome_unknown"}), encoding="utf-8")
            raise ImageJobError(
                "image_dispatch_outcome_unknown",
                "native image dispatch outcome is unknown; Plotloom will not retry this job",
            ) from error
        if completed.returncode != 0:
            receipt.write_text(json.dumps({"jobId": job_id, "state": "rejected"}), encoding="utf-8")
            raise ImageJobError(
                "image_dispatch_rejected",
                "native image specialist rejected the queue request; the exported package remains preserved",
            )
        receipt.write_text(json.dumps({"jobId": job_id, "state": "queued"}), encoding="utf-8")

    def complete(self, job_id: str) -> None:
        """Release the one-job gate only after terminal repository handling."""

        active = self.state_root / "inflight.json"
        try:
            record = json.loads(active.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return
        if record == {"jobId": job_id}:
            active.unlink()
