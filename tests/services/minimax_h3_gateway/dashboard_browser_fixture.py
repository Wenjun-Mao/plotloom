"""Disposable browser harness: real admission, no worker/provider, retained MP4.

Set DASHBOARD_FIXTURE_ROOT and DASHBOARD_FIXTURE_VIDEO, then run uvicorn with
--factory dashboard_browser_fixture:create_fixture --host 127.0.0.1 --port 8091.
Never point this fixture at production data. Its outputs are playback fixtures,
not newly generated results or creative acceptance.
"""
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path

import requests
from fastapi.testclient import TestClient
from PIL import Image
from plotloom_h3_gateway.api import create_app
from plotloom_h3_gateway.contracts import GatewaySettings
from plotloom_h3_gateway.dashboard.api import create_dashboard
from plotloom_h3_gateway.dashboard.submission import GatewaySubmission


class FixtureHealth:
    def get(self):
        return {"status": "ok", "observedAt": "2026-10-21T00:00:00Z"}


class LocalReply:
    def __init__(self, response):
        self.status_code = response.status_code
        self.content = response.content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def iter_content(self, _):
        yield self.content


class LocalAdmission:
    def __init__(self, client, root, video):
        self.client, self.root, self.video = client, root, video
        self.calls = 0

    def post(self, url, **request):
        self.calls += 1
        response = self.client.post("/v1/video-jobs/from-image", content=request["data"], headers=request["headers"])
        if response.status_code == 202:
            job_id = response.json()["id"]
            name = "2026-10-21T00-00-00Z_" + job_id + ".mp4"
            path = self.root / "outputs" / name
            path.parent.mkdir(exist_ok=True)
            shutil.copyfile(self.video, path)
            content = path.read_bytes()
            with sqlite3.connect(self.root / "gateway.sqlite3") as db:
                db.execute("""UPDATE jobs SET status='succeeded',managed_output_name=?,
                    output_sha256=?,output_size_bytes=?,output_mime_type='video/mp4',
                    generation_submitted_at_ms=1000,generation_completed_at_ms=5000,
                    output_expires_at=datetime('now','+1 day') WHERE id=?""",
                    (name, hashlib.sha256(content).hexdigest(), len(content), job_id))
                db.execute("UPDATE generation_lane SET state='completed' WHERE job_id=?", (job_id,))
            if b"fixture-unknown" in request["data"]:
                raise requests.ReadTimeout("fixture: admission committed, reply lost")
        return LocalReply(response)


class LocalImageSource:
    """Only fixture.invalid URLs resolve; never fetch a network image."""
    def __init__(self, content):
        self.content = content

    def get(self, url, **_):
        if not url.startswith("https://fixture.invalid/"):
            raise requests.ConnectionError("fixture rejects external image URLs")
        return self

    @property
    def headers(self):
        return {"Content-Length": str(len(self.content))}

    def raise_for_status(self):
        pass

    def iter_content(self, **_):
        yield self.content

    def close(self):
        pass


def create_fixture():
    root = Path(os.environ["DASHBOARD_FIXTURE_ROOT"])
    if root.exists():
        raise RuntimeError("use a new empty fixture path")
    root.mkdir(parents=True)
    video = Path(os.environ["DASHBOARD_FIXTURE_VIDEO"])
    Image.new("RGB", (576, 1024), "#4e6e7e").save(root / "start.png")
    app = create_app(GatewaySettings(api_key="fixture-server-only", data_dir=root,
        comfy_input_dir=root / "inputs", comfy_output_dir=root / "comfy-output",
        dispatch_worker_enabled=False), source_session=LocalImageSource((root / "start.png").read_bytes()))
    transport = LocalAdmission(TestClient(app), root, video)
    dashboard = create_dashboard(root, health=FixtureHealth(),
        submission=GatewaySubmission("fixture-server-only", session=transport))
    dashboard.state.fixture_transport = transport
    return dashboard
