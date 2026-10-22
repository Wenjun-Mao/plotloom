"""Native project/HTTP batch journey: only Codex/H3 transport is synthetic."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sys
import subprocess
import uvicorn
from plotloom.api import create_project_folder_authoring_app
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_ingestion import probe_video
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.autopilot_controller_fixtures import PIN
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.codex_exec_fixtures import install_profile
from tests.video_batch_fixtures import batch_environment
from tests.video_storage_fixtures import FakeH3

root = Path(os.environ["PLOTLOOM_OUTPUTS_DIR"]).parent
source = root / "source"
take = root / "synthetic-take.mp4"
if not take.exists():
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=576x1024:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=5.1666666667", "-frames:v", "124",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", "-y", str(take)], check=True, timeout=60)

class FixtureH3(FakeH3):
    def submit_image(self, *args, **kwargs):
        result = super().submit_image(*args, **kwargs)
        (root / "fake-provider-request.json").write_text(json.dumps(kwargs["payload"]))
        return result

    def poll(self, prediction_id):
        data = json.loads((root / "fake-provider-request.json").read_text())
        self.duration, self.seed, self.quality = data["durationSeconds"], data["seed"], data["quality"]
        self.resolution, self.aspect_policy = data["resolution"], data["aspectPolicy"]
        return super().poll(prediction_id)

if not (source / "outputs").exists() or not list((source / "outputs").iterdir()):
    storage, _client, _service, _provider, project_id, _view = batch_environment(root)
else:
    storage = ProjectFolderStorage(outputs_root=source / "outputs", application_data_root=source / "application")
provider = FixtureH3(outputs=[take.read_bytes()])
app = create_project_folder_authoring_app(storage, video_provider=provider, video_probe=probe_video)
registry = app.state.specialists
install_profile(registry)
CreativeHandoffExchange.current_execution_pin = lambda _self, stage: PIN

def candidate(store, request):
    return {"version": "video-directions.draft.v1", "targets": [{"shotId": target["shotId"], "sourceHash": target["sourceHash"],
        "fields": [{"path": item["path"], "english": "Soft wind and cloth movement." if item["path"] == "reviewedSoundscape" else "The keeper holds still beside the beacon in soft light."}
            for item in target["sources"]]} for target in request.input_artifacts["video-targets.json"]["targets"]]}

host = FakeCodexExecHost(storage, registry, candidate_factory=candidate)
registry.codex_exec_admit, registry.codex_exec_status = host.admit, host.status
registry.codex_exec_cancel, registry.codex_exec_suspend = host.cancel, host.suspend
registry.codex_exec_resume = host.admit
app.state.video_batch_runtime.interval_seconds = 0.1
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=0)
args = parser.parse_args()
listener = socket.socket()
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", args.port))
listener.listen(128)
print("PLOTLOOM_E2E_LISTENER " + json.dumps({"role": "backend", "host": "127.0.0.1", "port": listener.getsockname()[1]}), flush=True)
uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[listener])
