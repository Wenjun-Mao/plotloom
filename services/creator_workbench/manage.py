"""Install/start the local Docker workbench and its Mac Codex queue bridge."""

import argparse
import json
import os
import plistlib
import secrets
import shutil
import stat
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

SERVICE = Path(__file__).resolve().parent
REPOSITORY = SERVICE.parents[1]
CONFIG = REPOSITORY / ".local" / "creator-workbench" / "deployment.json"
LABEL = "com.plotloom.creator-codex-bridge"


def run(command, *, check=True, env=None):
    return subprocess.run(command, check=check, env=env)


def secure_token(private, *, create):
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = private.lstat()
    if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid():
        raise ValueError(
            "bridge credential directory must be owned by the current user and not a symlink"
        )
    private.chmod(0o700)
    token = private / "bridge-token"
    if create and not token.exists():
        descriptor = os.open(token, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(secrets.token_urlsafe(48))
    metadata = token.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise ValueError(
            "bridge token must be a regular file owned by the current user"
        )
    token.chmod(0o600)
    if len(token.read_text().strip()) < 32:
        raise ValueError("existing bridge token is invalid; it was not replaced")
    return token


def load_config(data_root=None):
    private = (
        Path.home()
        / "Library"
        / "Application Support"
        / "Plotloom"
        / "creator-workbench"
    )
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text())
        if data_root is not None and str(data_root.resolve()) != config["data"]:
            raise ValueError(
                "already configured for another data root; do not relocate active project data"
            )
        if config["token"] != str(private / "bridge-token"):
            raise ValueError(
                "configured bridge token is outside its installation-local credential directory"
            )
        secure_token(private, create=False)
        return config
    if data_root is None:
        raise ValueError("run start --data-root .local/creator-walkthrough first")
    data = data_root.resolve()
    for child in ("outputs", "application"):
        if not (data / child).is_dir():
            raise ValueError(f"existing data directory is missing: {data / child}")
    settings = data / "application" / "specialists" / "settings.json"
    if not settings.is_file():
        raise ValueError("existing specialist settings are missing")
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("the Mac Codex app CLI must be available on PATH")
    token = secure_token(private, create=True)
    config = {"data": str(data), "token": str(token), "codex": executable}
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    return config


def compose(config, *arguments):
    environment = dict(os.environ) | {
        "PLOTLOOM_CHECKOUT": str(REPOSITORY),
        "PLOTLOOM_CREATOR_DATA": config["data"],
        "PLOTLOOM_BRIDGE_TOKEN_FILE": config["token"],
        "PLOTLOOM_UID": str(os.getuid()),
        "PLOTLOOM_GID": str(os.getgid()),
    }
    return run(
        ["docker", "compose", "-f", str(SERVICE / "compose.yaml"), *arguments],
        env=environment,
    )


def install_bridge(config):
    domain = f"gui/{os.getuid()}"
    agent = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    agent.parent.mkdir(parents=True, exist_ok=True)
    existing = plistlib.loads(agent.read_bytes()) if agent.exists() else None
    if existing and existing.get("WorkingDirectory") != str(REPOSITORY):
        raise ValueError("this launchd bridge belongs to another checkout")
    logs = CONFIG.parent
    definition = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(SERVICE / "host_bridge.py"),
            "--executable",
            config["codex"],
            "--settings",
            str(Path(config["data"]) / "application" / "specialists" / "settings.json"),
            "--token-file",
            config["token"],
        ],
        "WorkingDirectory": str(REPOSITORY),
        "RunAtLoad": True,
        "KeepAlive": True,
        "EnvironmentVariables": {
            "PLOTLOOM_BRIDGE_SOURCE_HASH": sha256(
                (SERVICE / "host_bridge.py").read_bytes()
            ).hexdigest()
        },
        "StandardOutPath": str(logs / "bridge.log"),
        "StandardErrorPath": str(logs / "bridge-error.log"),
    }
    if existing == definition:
        loaded = subprocess.run(
            ["launchctl", "print", f"{domain}/{LABEL}"],
            capture_output=True,
            check=False,
        )
        if loaded.returncode == 0:
            return
    elif existing:
        run(["launchctl", "bootout", f"{domain}/{LABEL}"], check=False)
    agent.write_bytes(plistlib.dumps(definition))
    run(["launchctl", "bootstrap", domain, str(agent)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["start", "status", "logs", "stop", "check-bridge"]
    )
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error(
            "this creator deployment requires Docker on macOS and the native Codex app"
        )
    config = load_config(args.data_root)
    if args.action == "start":
        compose(config, "build")
        install_bridge(config)
        compose(config, "up", "-d", "--wait", "--wait-timeout", "90")
        compose(config, "exec", "-T", "workbench", "codex", "bridge-health")
        print("Creator workbench is available at http://127.0.0.1:8841/v2/")
    elif args.action == "status":
        compose(config, "ps")
    elif args.action == "logs":
        compose(config, "logs", "--tail", "100", "workbench")
    elif args.action == "check-bridge":
        compose(config, "exec", "-T", "workbench", "codex", "bridge-health")
    else:
        compose(config, "stop")


if __name__ == "__main__":
    main()
