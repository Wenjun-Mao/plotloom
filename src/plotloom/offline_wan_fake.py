"""Test-only Wan port; selected only by PLOTLOOM_FAKE_WAN_P2 in owned E2E."""
from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


class OfflineWanFake:
    def preflight(self) -> None:
        return None

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type.startswith("image/")
        return "https://upload.example/offline-keyframe"

    def submit(self, payload: dict[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        _ = idempotency_key
        assert payload["image"] == "https://upload.example/offline-keyframe"
        return {"data": {"id": "offline-prediction-1"}}

    def poll(self, prediction_id: str) -> dict[str, Any]:
        assert prediction_id == "offline-prediction-1"
        return {"data": {"status": "completed", "outputs": ["https://cdn.example/offline.mp4"]}}

    def download(self, url: str) -> bytes:
        assert url == "https://cdn.example/offline.mp4"
        with TemporaryDirectory(prefix="plotloom-offline-wan-") as directory:
            output = Path(directory) / "clip.mp4"
            completed = subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=5",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-shortest",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
            if completed.returncode:
                raise RuntimeError("offline ffmpeg fixture generation failed")
            return output.read_bytes()
