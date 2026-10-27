"""Disposable real host/validator/API; deterministic candidate-only Codex fixture."""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback
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


def startup_phase(phase, **facts):
    """Opt-in fixture metadata, outside every copied source/package tree."""
    directory = os.environ.get("PLOTLOOM_E2E_STARTUP_DIAGNOSTICS")
    if directory:
        record = {"phase": phase, "monotonicNs": time.monotonic_ns(),
            "wallTimeNs": time.time_ns(), "pid": os.getpid(), "pgid": os.getpgid(0), **facts}
        with (Path(directory) / f"backend-{os.getpid()}.jsonl").open("a") as output:
            output.write(json.dumps(record) + "\n")


def observe_startup_exception(kind, value, frames):
    try:
        startup_phase("uncaught-exception", exceptionType=f"{kind.__module__}.{kind.__qualname__}",
            frames=[{"file": frame.filename, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_tb(frames)])
    finally:
        sys.__excepthook__(kind, value, frames)


def main():
    if os.environ.get("PLOTLOOM_E2E_STARTUP_DIAGNOSTICS"):
        sys.excepthook = observe_startup_exception
        startup_phase("main-entered-imports-complete", birth=subprocess.check_output(
            ["/bin/ps", "-p", str(os.getpid()), "-o", "lstart="], text=True).strip())
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    arguments = parser.parse_args()
    fixture_root = Path(os.environ["PLOTLOOM_OUTPUTS_DIR"]).parent
    fixture_root.mkdir(parents=True, exist_ok=True)
    fixture_root = fixture_root / "text-runtime"
    fixture_root.mkdir()
    patch = pytest.MonkeyPatch()
    startup_phase("clone-start")
    source = build_codex_exec_test_source(FixtureRoots(fixture_root))
    startup_phase("clone-complete")
    startup_phase("supervisor-setup-start")
    host = supervisor.__wrapped__(fixture_root, patch, source)
    startup_phase("supervisor-setup-complete")
    startup_phase("journey-setup-start")
    storage, registry, service, run = _journey_environment(host, fixture_root, patch, exhaust=True, correction_limit=0)
    startup_phase("journey-setup-complete", projectId=run.project_id, runId=run.id)
    try:
        from contextlib import closing
        deadline = time.monotonic() + 40
        startup_phase("seed-start", deadlineMonotonicNs=int(deadline * 1_000_000_000))
        previous = None
        while time.monotonic() < deadline:
            step_started = time.monotonic_ns()
            service.step(run.project_id)
            with closing(storage.projects.open(run.project_id)) as store:
                current = store.repository.autopilot.current(run.project_id)
            if os.environ.get("PLOTLOOM_E2E_STARTUP_DIAGNOSTICS"):
                summary = {"state": current.state, "runPhase": current.phase,
                    "blockerCode": current.blocker.get("code") if current.blocker else None,
                    "checkpoints": [{"operation": item["operationKey"], "state": item["state"]}
                        for item in current.checkpoints],
                    "activities": [{"operation": item.operation_key, "state": item.state, "jobId": item.job_id}
                        for item in current.activities]}
                if summary != previous:
                    startup_phase("seed-transition", stepElapsedNs=time.monotonic_ns() - step_started, **summary)
                    previous = summary
            if current.state == "blocked":
                startup_phase("seed-blocked", blockerCode=current.blocker.get("code") if current.blocker else None)
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("fixture did not reach its real Art validation failure")
        startup_phase("seed-service-close-start")
        service.close()
        startup_phase("seed-service-close-complete")
        patch.setattr("plotloom.api.project_folder.SpecialistRegistry", lambda *args, **kwargs: registry)
        app = create_project_folder_authoring_app(storage)
        app.state.autopilot_service.interval_seconds = 0.1

        @app.get("/api/v2/fixture/text-retry")
        def fixture_identity():
            return {"projectId": run.project_id}

        print("PLOTLOOM_E2E_PREPARED " + json.dumps(
            {"role": "backend", "fixture": "text-retry", "version": 1}), flush=True)
        startup_phase("preparation-complete")
        startup_phase("about-to-start-server")
        with owned_loopback_listener(arguments.port) as listener:
            address, port = listener.getsockname()
            print("PLOTLOOM_E2E_LISTENER " + json.dumps({"role": "backend", "host": address, "port": port}), flush=True)
            uvicorn.Server(uvicorn.Config(app, host=address, port=port)).run(sockets=[listener])
    finally:
        service.close()
        patch.undo()


if __name__ == "__main__":
    main()
