"""Disposable real host/validator/API; deterministic candidate-only Codex fixture."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pytest
import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services/creator_workbench"))

from owned_listener import owned_loopback_listener

from plotloom.api import create_project_folder_authoring_app
from tests.codex_exec_runtime_fixtures import build_codex_exec_test_source
from tests.services.creator_workbench.conftest import supervisor
from tests.services.creator_workbench.test_text_content_correction import (
    _journey_environment,
)


class FixtureRoots:
    def __init__(self, root):
        self.root = root

    def mktemp(self, name):
        path = self.root / name
        path.mkdir()
        return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    arguments = parser.parse_args()
    fixture_root = Path(os.environ["PLOTLOOM_OUTPUTS_DIR"]).parent
    fixture_root.mkdir(parents=True, exist_ok=True)
    fixture_root = fixture_root / "text-runtime"
    fixture_root.mkdir()
    patch = pytest.MonkeyPatch()
    host = supervisor.__wrapped__(fixture_root, patch, build_codex_exec_test_source(FixtureRoots(fixture_root)))
    storage, registry, service, run = _journey_environment(host, fixture_root, patch, exhaust=True, correction_limit=0)
    try:
        from contextlib import closing
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            service.step(run.project_id)
            with closing(storage.projects.open(run.project_id)) as store:
                current = store.repository.autopilot.current(run.project_id)
            if current.state == "blocked":
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("fixture did not reach its real Art validation failure")
        service.close()
        patch.setattr("plotloom.api.project_folder.SpecialistRegistry", lambda *args, **kwargs: registry)
        app = create_project_folder_authoring_app(storage)
        app.state.autopilot_service.interval_seconds = 0.1

        @app.get("/api/v2/fixture/text-retry")
        def fixture_identity():
            return {"projectId": run.project_id}

        with owned_loopback_listener(arguments.port) as listener:
            address, port = listener.getsockname()
            print("PLOTLOOM_E2E_LISTENER " + json.dumps({"role": "backend", "host": address, "port": port}), flush=True)
            uvicorn.Server(uvicorn.Config(app, host=address, port=port)).run(sockets=[listener])
    finally:
        service.close()
        patch.undo()


if __name__ == "__main__":
    main()
