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

from h3_configuration import read_h3_configuration

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
    command = ["docker", "compose", "-f", str(SERVICE / "compose.yaml")]
    if config.get("h3_config"):
        environment["PLOTLOOM_CREATOR_H3_CONFIG"] = config["h3_config"]
        command.extend(["-f", str(SERVICE / "compose.h3.yaml")])
    return run(
        [*command, *arguments],
        env=environment,
    )


def configure_h3(config, path=None, *, disable=False):
    selected = str(path.absolute()) if path is not None else config.get("h3_config")
    if disable:
        selected = None
    if selected:
        candidate = Path(selected)
        data = Path(config["data"]).resolve()
        if candidate.resolve().is_relative_to(data) or candidate.resolve().is_relative_to(
            SERVICE
        ):
            raise ValueError("H3 credentials must remain outside creator data and service source")
        read_h3_configuration(candidate)
    if selected != config.get("h3_config"):
        config["h3_config"] = selected
        CONFIG.write_text(json.dumps(config, indent=2) + "\n")


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
    h3 = parser.add_mutually_exclusive_group()
    h3.add_argument(
        "--h3-config", type=Path,
        help="Enable the existing private H3 gateway using an owner-only configuration file",
    )
    h3.add_argument(
        "--disable-h3", action="store_true",
        help="Disable H3 without deleting job evidence or credentials",
    )
    args = parser.parse_args()
    if args.action != "start" and (args.h3_config is not None or args.disable_h3):
        parser.error("H3 configuration changes require start")
    if sys.platform != "darwin":
        parser.error(
            "this creator deployment requires Docker on macOS and the native Codex app"
        )
    config = load_config(args.data_root)
    if args.action == "start":
        configure_h3(config, args.h3_config, disable=args.disable_h3)
        compose(config, "build")
        install_bridge(config)
        # Mounted Python edits do not change the image/config identity used by
        # Compose. Explicit start must activate them, not reuse cached imports.
        compose(config, "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "90")
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
