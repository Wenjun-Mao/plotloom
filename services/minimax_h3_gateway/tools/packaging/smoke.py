"""Exercise an installed CPU artifact without a checkout, models or real data.

Run with ``python -I smoke.py gateway|dashboard`` in the installed environment.
The dashboard uses its real fixed loopback port, so run in an isolated container
or ensure local port 8091 is free. This never submits a generation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import site
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(base: str, route: str, *, data=None, headers=None):
    req = urllib.request.Request(base + route, data=data, headers=headers or {})
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.read()


def check_install(role: str) -> Path:
    import plotloom_h3_gateway

    package = Path(plotloom_h3_gateway.__file__).resolve().parent
    assert any(package.is_relative_to(Path(p).resolve()) for p in site.getsitepackages()), package
    for name in ("plotloom", "plotloom_voice_lab", "torch", "transformers", "sglang"):
        assert importlib.util.find_spec(name) is None, f"unexpected dependency: {name}"
    if role == "dashboard":
        from plotloom_h3_gateway.dashboard.api import create_dashboard

        assert callable(create_dashboard)
        assert "plotloom_h3_gateway.gateway" not in sys.modules
        assert "plotloom_h3_gateway.worker" not in sys.modules
        assert importlib.util.find_spec("PIL") is None, "dashboard installed gateway-only Pillow"
    else:
        from plotloom_h3_gateway.workflow import load_h3_template

        assert load_h3_template()["prompt"]["105:104"]["class_type"] == "MiniMaxH3ImageToVideo"
    return package


def available_port(role: str) -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 8091 if role == "dashboard" else 0))
        return listener.getsockname()[1]


def verify(role: str) -> dict:
    package = check_install(role)
    executable = shutil.which("plotloom-h3-" + role)
    assert executable, "installed console entrypoint missing"
    port = available_port(role)
    with tempfile.TemporaryDirectory(prefix="plotloom-artifact-smoke-") as directory:
        root = Path(directory)
        env = {k: v for k, v in os.environ.items() if not k.startswith("H3_") and k != "PYTHONPATH"}
        env.update({
            "H3_API_KEY": "isolated-smoke-key", "H3_BIND_ADDRESS": "127.0.0.1",
            "H3_PORT": str(port), "H3_GATEWAY_DATA_DIR": str(root / "data"),
            "H3_COMFY_INPUT_DIR": str(root / "input"), "H3_COMFY_OUTPUT_DIR": str(root / "output"),
            "H3_COMFY_URL": "http://127.0.0.1:1", "H3_QWEN_IMAGE_URL": "http://127.0.0.1:1",
            "H3_DISPATCH_WORKER_ENABLED": "false", "H3_DASHBOARD_DATA_DIR": str(root / "absent"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        base = f"http://127.0.0.1:{port}"
        route = "/dashboard/" if role == "dashboard" else "/openapi.json"
        with (root / "server.log").open("w+") as log:
            server = subprocess.Popen([executable], cwd=root, env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 15
                while True:
                    if server.poll() is not None:
                        raise RuntimeError("artifact entrypoint exited before readiness")
                    try:
                        status, _ = request(base, route)
                        assert status == 200
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("artifact startup timed out") from None
                        time.sleep(0.1)
                if role == "dashboard":
                    verify_dashboard(base, root, package)
                else:
                    verify_gateway(base)
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
    return {"role": role, "status": "passed", "package": str(package), "generationCalls": 0}


def verify_dashboard(base: str, root: Path, package: Path) -> None:
    assert json.loads(request(base, "/dashboard/api/generation")[1]) == {"enabled": False}
    status, body = request(base, "/dashboard/api/jobs")
    assert status == 503 and json.loads(body)["error"] == "dashboard_database_unavailable"
    assert not (root / "absent").exists(), "viewer initialized persistent storage"
    for path in (package / "dashboard/static").iterdir():
        if path.name == "index.html":
            continue
        status, body = request(base, "/dashboard/assets/" + path.name)
        assert status == 200 and body == path.read_bytes(), path.name
    status, body = request(base, "/dashboard/api/generation", data=b"{}", headers={
        "Origin": base, "X-Dashboard-Request": "1", "Content-Type": "application/json",
    })
    assert status == 503 and json.loads(body)["error"] == "submission_not_configured"


def verify_gateway(base: str) -> None:
    status, body = request(base, "/health")
    # The artifact runs without inference backends; do not conflate API startup
    # with model readiness or weaken the existing fail-closed health contract.
    assert status == 503 and json.loads(body) == {"error": "comfy_unavailable"}
    assert request(base, "/v1/video-jobs/h3_" + "a" * 32)[0] == 401
    assert request(base, "/v1/video-jobs/from-text", data=b"{}", headers={
        "Authorization": "Bearer isolated-smoke-key", "Content-Type": "application/json",
    })[0] == 422


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("gateway", "dashboard"))
    print(json.dumps(verify(parser.parse_args().role), sort_keys=True))
