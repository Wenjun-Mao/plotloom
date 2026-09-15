"""H3-only offline gateway fixture used by the browser acceptance journey."""
from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from plotloom.video_backends.minimax_h3 import H3_PROFILES_BY_ID
from plotloom.video_provider import VideoBackendInstanceIdentity


class OfflineH3GatewayFake:
    """Strict local gateway-shaped fixture for the browser H3 acceptance path."""

    def configured_backend_identity(self) -> VideoBackendInstanceIdentity:
        """Match the production transport's secret-free instance contract."""

        return VideoBackendInstanceIdentity.from_public_configuration(
            "offline_h3_fixture_endpoint_v1", {"endpoint": "http://127.0.0.1:9010"}
        )

    def preflight(self) -> None:
        return None

    def submit_image(self, image: bytes, *, mime_type: str, payload: dict[str, object]) -> dict[str, object]:
        """Mirror the direct multipart image boundary used by Plotloom."""

        assert image and mime_type.startswith("image/")
        assert isinstance(payload["profileId"], str) and payload["profileId"] in H3_PROFILES_BY_ID
        assert payload["aspectPolicy"] in {"cover_center_crop", "contain_pad", "reject_mismatch"}
        assert isinstance(payload["seed"], int)
        assert payload["durationSeconds"] == 5
        self.profile_id = payload["profileId"]
        return self._job("submitted", output_ready=False, aspect_policy=payload["aspectPolicy"])

    def poll(self, job_id: str) -> dict[str, object]:
        assert job_id == "h3_0123456789abcdef0123456789abcdef"
        return self._job("succeeded", output_ready=True, aspect_policy="cover_center_crop")

    def _job(self, status: str, *, output_ready: bool, aspect_policy: object) -> dict[str, object]:
        return {
            "id": "h3_0123456789abcdef0123456789abcdef", "status": status,
            "inputMode": "image", "profileId": self.profile_id,
            "aspectPolicy": aspect_policy, "seed": 1,
            "requestedDurationSeconds": 5, "frameCount": 124,
            "actualDurationSeconds": 124 / 24,
            "generationSubmittedAt": None, "generationCompletedAt": None,
            "generationElapsedMs": None, "error": None, "outputReady": output_ready,
        }

    def download(self, job_id: str) -> bytes:
        assert job_id == "h3_0123456789abcdef0123456789abcdef"
        if self.profile_id is None:
            raise RuntimeError("offline H3 fixture has no frozen profile")
        profile = H3_PROFILES_BY_ID[self.profile_id]
        with TemporaryDirectory(prefix="plotloom-offline-h3-") as directory:
            output = Path(directory) / "clip.mp4"
            completed = subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={profile.width}x{profile.height}:r=24:d=5.166667",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5.166667", "-shortest",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(output),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
            if completed.returncode:
                raise RuntimeError("offline H3 fixture generation failed")
            return output.read_bytes()
    def __init__(self) -> None:
        self.profile_id: str | None = None
