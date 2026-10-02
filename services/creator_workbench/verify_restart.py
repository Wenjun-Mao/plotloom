"""Bounded deployment acceptance; requires an idle workbench, never queues jobs."""

import argparse
import json
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen

from manage import compose, load_config

ORIGIN = "http://127.0.0.1:8841"


def read(path):
    with urlopen(ORIGIN + path, timeout=10) as response:
        return json.load(response)


def snapshot(project):
    return {
        "art": read(f"/api/v2/projects/{project}/art")["acceptedArt"],
        "proposals": read(f"/api/v2/projects/{project}/art-reference-proposals"),
        "specialists": read("/api/v2/specialists"),
    }


def wait_ready():
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            if read("/healthz")["status"] == "ok":
                return
        except (URLError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError("workbench did not recover within 45 seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    config = load_config()
    before = snapshot(args.project)
    if before["specialists"]["busy"]:
        raise RuntimeError("restart verification requires no specialist work in flight")
    container = subprocess.check_output(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=plotloom-creator",
            "--filter",
            "label=com.docker.compose.service=workbench",
        ],
        text=True,
    ).strip()
    if not container or "\n" in container:
        raise RuntimeError("expected exactly one creator workbench container")
    crash = (
        "import os, signal; from pathlib import Path; "
        "children=Path('/proc/1/task/1/children').read_text().split(); "
        "servers=[int(pid) for pid in children if b'/opt/plotloom-service/server.py' in Path('/proc/'+pid+'/cmdline').read_bytes()]; "
        "assert len(servers)==1; os.kill(servers[0], signal.SIGKILL)"
    )
    subprocess.run(["docker", "exec", container, "python", "-c", crash], check=True)
    wait_ready()
    after_crash = snapshot(args.project)
    if before != after_crash:
        raise RuntimeError("creator state changed across automatic crash recovery")
    compose(config, "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "90")
    if before != snapshot(args.project):
        raise RuntimeError("creator state changed across container recreation")
    compose(config, "exec", "-T", "workbench", "codex", "bridge-health")
    print(
        f"Crash recovery and recreation preserved art r{before['art']['revision']} ({before['art']['contentHash'][:12]}), image requests and specialist state."
    )


if __name__ == "__main__":
    main()
