"""H3-only offline gateway fixture used by the browser acceptance journey."""
from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


class OfflineH3GatewayFake:
    """Strict local gateway-shaped fixture for the browser H3 acceptance path."""

    def preflight(self) -> None:
        return None

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type.startswith("image/")
        return "asset_0123456789abcdef0123456789abcdef"

    def submit(self, payload: dict[str, object]) -> dict[str, object]:
        assert payload["assetId"] == "asset_0123456789abcdef0123456789abcdef"
        assert payload["profileId"] == "minimax_h3_fp8_turbo4_480p"
        assert payload["aspectPolicy"] in {"cover_center_crop", "contain_pad", "reject_mismatch"}
        assert isinstance(payload["seed"], int)
        return {
            "id": "h3_0123456789abcdef0123456789abcdef", "status": "submitted",
            "profileId": payload["profileId"], "aspectPolicy": payload["aspectPolicy"],
            "error": None, "outputReady": False,
        }

    def poll(self, job_id: str) -> dict[str, object]:
        assert job_id == "h3_0123456789abcdef0123456789abcdef"
        return {
            "id": job_id, "status": "succeeded", "profileId": "minimax_h3_fp8_turbo4_480p",
            "aspectPolicy": "cover_center_crop", "error": None, "outputReady": True,
        }

    def download(self, job_id: str) -> bytes:
        assert job_id == "h3_0123456789abcdef0123456789abcdef"
        with TemporaryDirectory(prefix="plotloom-offline-h3-") as directory:
            output = Path(directory) / "clip.mp4"
            completed = subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=864x480:r=24:d=5.166667",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5.166667", "-shortest",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(output),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
            if completed.returncode:
                raise RuntimeError("offline H3 fixture generation failed")
            return output.read_bytes()
