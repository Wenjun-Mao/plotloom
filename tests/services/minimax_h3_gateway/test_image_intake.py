"""URL and file start/end-frame admission regression coverage."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.app import GatewaySettings, create_app


RESOLUTION = "832x480"
AUTH = {"Authorization": "Bearer test-key"}


class _Response:
    def __init__(self, content: bytes) -> None:
        self.headers: dict[str, str] = {}; self.content = content; self.closed = False
    def raise_for_status(self) -> None: return None
    def iter_content(self, *, chunk_size: int) -> list[bytes]:
        assert chunk_size == 64 * 1024; return [self.content]
    def close(self) -> None: self.closed = True


class _SourceSession:
    def __init__(self, contents: list[bytes]) -> None:
        self.contents = contents; self.calls: list[str] = []; self.max_redirects: int | None = None
    def get(self, url: str, **_: Any) -> _Response:
        self.calls.append(url)
        return _Response(self.contents.pop(0))


def _png(width: int = 832, height: int = 480) -> bytes:
    image = Image.new("RGB", (width, height), "#355070")
    buffer = BytesIO(); image.save(buffer, "PNG")
    return buffer.getvalue()


def _client(tmp_path: Path, source: _SourceSession) -> TestClient:
    return TestClient(create_app(GatewaySettings(api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "input", comfy_output_dir=tmp_path / "output", dispatch_worker_enabled=False), session=object(), source_session=source))


def test_json_url_start_end_fetches_and_persists_no_source_url(tmp_path: Path) -> None:
    source = _SourceSession([_png(), _png()]); client = _client(tmp_path, source)
    response = client.post("/v1/video-jobs/from-image", headers=AUTH, json={
        "sourceUrl": "http://100.64.35.71/start.png", "endSourceUrl": "http://100.64.35.71/end.png",
        "prompt": "A return signal becomes clear.", "resolution": RESOLUTION,
        "aspectPolicy": "reject_mismatch", "seed": 2,
    })
    assert response.status_code == 202
    assert source.calls == ["http://100.64.35.71/start.png", "http://100.64.35.71/end.png"]
    frames = client.app.state.gateway.store.get_job_frames(response.json()["id"])
    assert [frame["role"] for frame in frames] == ["start", "end"]
    with client.app.state.gateway.store._connect() as connection:
        assert "100.64.35.71" not in " ".join(str(value) for row in connection.execute("SELECT * FROM assets") for value in row)


def test_invalid_end_frame_cleans_the_accepted_start_frame(tmp_path: Path) -> None:
    client = _client(tmp_path, _SourceSession([]))
    response = client.post("/v1/video-jobs/from-image", headers=AUTH, data={"prompt": "A quiet turn.", "resolution": RESOLUTION, "aspectPolicy": "reject_mismatch"}, files={"image": ("start.png", _png(), "image/png"), "endImage": ("end.bin", b"not an image", "image/png")})
    assert response.status_code == 422
    assert response.json() == {"error": "image_decode_invalid"}
    with client.app.state.gateway.store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_rejected_aspect_or_unknown_profile_never_orphans_start_or_fetches(tmp_path: Path) -> None:
    source = _SourceSession([_png()]); client = _client(tmp_path, source)
    rejected = client.post("/v1/video-jobs/from-image", headers=AUTH, data={"prompt": "x", "resolution": RESOLUTION, "aspectPolicy": "reject_mismatch"}, files={"image": ("portrait.png", _png(576, 1024), "image/png")})
    assert rejected.json() == {"error": "input_aspect_mismatch"}
    assert list((tmp_path / "data" / "assets").iterdir()) == []
    unsupported = client.post("/v1/video-jobs/from-image", headers=AUTH, json={"sourceUrl": "http://100.64.35.71/a.png", "prompt": "x", "resolution": "900x900", "aspectPolicy": "reject_mismatch"})
    assert unsupported.json() == {"error": "resolution_not_supported"}
    assert source.calls == []
