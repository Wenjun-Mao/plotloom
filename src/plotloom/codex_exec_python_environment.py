"""Explicit checked-lock provisioning and read-only Python runtime admission."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .codex_exec_files import read_confined_regular_file
from .codex_exec_runtime_tree import (
    physical_directory,
    runtime_tree_hash,
    stable_file_hash,
)

ENVIRONMENT_PATH = ".local/codex-exec/python-env"
RECEIPT_PATH = ".local/codex-exec/python-environment.json"
ENVIRONMENT_CONTRACT = "plotloom.codex-python-environment.v1"
_SNAPSHOT_FIELDS = {
    "contract", "sourceRoot", "environmentRoot", "runtimeRoot", "interpreterSha256", "pythonVersion",
    "configurationSha256", "projectSha256", "lockSha256", "environmentSha256", "runtimeSha256",
}


class CodexExecPythonEnvironmentError(ValueError):
    """The explicit checkout environment is missing, aliased or has drifted."""


@dataclass(frozen=True)
class CheckedPythonEnvironment:
    root: Path
    interpreter: Path
    runtime_root: Path
    identity_hash: str
    base_interpreter: Path


def _configuration(root: Path, expected_hash: str | None = None) -> tuple[dict[str, str], bytes]:
    payload = read_confined_regular_file(root, "pyvenv.cfg", max_bytes=16384)
    if expected_hash is not None and sha256(payload).hexdigest() != expected_hash:
        raise CodexExecPythonEnvironmentError("Python environment configuration has drifted")
    values = {}
    for line in payload.decode("utf-8", "strict").splitlines():
        key, separator, value = line.partition("=")
        if not separator or key.strip() in values:
            raise CodexExecPythonEnvironmentError("Python environment configuration is malformed")
        values[key.strip()] = value.strip()
    if set(values) != {"home", "include-system-site-packages", "version", "executable", "command"}:
        raise CodexExecPythonEnvironmentError("Python environment configuration is unsupported")
    return values, payload


def _copy_identity(root: Path, *, expected_receipt=None, expected_base=None) -> tuple[Path, dict[str, str], bytes]:
    physical_directory(root)
    configuration, payload = _configuration(root, expected_receipt["configurationSha256"] if expected_receipt else None)
    base = Path(configuration["executable"])
    if ((expected_base is not None and base != expected_base)
            or (expected_receipt is not None and str(base.parent.parent) != expected_receipt["runtimeRoot"])):
        raise CodexExecPythonEnvironmentError("Python base interpreter differs from its explicit setup")
    if not base.is_absolute() or base.absolute().resolve(strict=True) != base:
        raise CodexExecPythonEnvironmentError("base interpreter must be physical and versioned")
    runtime = physical_directory(base.parent.parent)
    if configuration["home"] != str(base.parent) or configuration["include-system-site-packages"] != "false":
        raise CodexExecPythonEnvironmentError("Python environment uses an alias or external site-packages")
    version_parts = configuration["version"].split(".")
    if len(version_parts) != 3 or not all(part.isdecimal() for part in version_parts):
        raise CodexExecPythonEnvironmentError("Python runtime version is not exact")
    if base.name != f"python{'.'.join(version_parts[:2])}":
        raise CodexExecPythonEnvironmentError("Python base executable is not its versioned interpreter")
    if configuration["version"] not in runtime.name:
        raise CodexExecPythonEnvironmentError("Python base runtime directory must name its exact version")
    interpreter = root / "bin/python"
    if not os.access(interpreter, os.X_OK) or stable_file_hash(interpreter) != stable_file_hash(base):
        raise CodexExecPythonEnvironmentError("Python environment interpreter is not a regular runtime copy")
    return runtime, configuration, payload


def _snapshot(source_root: Path, *, expected_receipt=None) -> dict[str, str]:
    root = source_root / ENVIRONMENT_PATH
    runtime, configuration, payload = _copy_identity(root, expected_receipt=expected_receipt)
    return {
        "contract": ENVIRONMENT_CONTRACT,
        "sourceRoot": str(source_root),
        "environmentRoot": str(root),
        "runtimeRoot": str(runtime),
        "interpreterSha256": stable_file_hash(root / "bin/python"),
        "pythonVersion": configuration["version"],
        "configurationSha256": sha256(payload).hexdigest(),
        "projectSha256": stable_file_hash(source_root / "pyproject.toml"),
        "lockSha256": stable_file_hash(source_root / "uv.lock"),
        "environmentSha256": runtime_tree_hash(root, ignore_bytecode=True),
        "runtimeSha256": runtime_tree_hash(runtime, internal_links=True, ignore_bytecode=True),
    }


def inspect_checked_python_environment(source_root: Path) -> CheckedPythonEnvironment:
    """Recompute identity without creating, syncing or repairing any files."""
    try:
        source_root = physical_directory(source_root)
        payload = read_confined_regular_file(source_root, RECEIPT_PATH, max_bytes=16384)
        receipt = json.loads(payload)
        if (not isinstance(receipt, dict) or set(receipt) != _SNAPSHOT_FIELDS
                or not all(isinstance(value, str) for value in receipt.values())
                or receipt["contract"] != ENVIRONMENT_CONTRACT
                or receipt["sourceRoot"] != str(source_root)
                or receipt["environmentRoot"] != str(source_root / ENVIRONMENT_PATH)):
            raise CodexExecPythonEnvironmentError("Python environment receipt is malformed or belongs to another checkout")
        actual = _snapshot(source_root, expected_receipt=receipt)
        if receipt != actual:
            raise CodexExecPythonEnvironmentError("checked Python environment identity has drifted")
    except (OSError, UnicodeError, ValueError) as error:
        raise CodexExecPythonEnvironmentError(
            "checked Python environment is unavailable or changed; explicit provisioning is required"
        ) from error
    identity_hash = sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    root = source_root / ENVIRONMENT_PATH
    version = actual["pythonVersion"].split(".")
    runtime = Path(actual["runtimeRoot"])
    return CheckedPythonEnvironment(
        root, root / "bin/python", runtime, identity_hash, runtime / "bin" / f"python{'.'.join(version[:2])}",
    )


def _write_once(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _setup_environment() -> dict[str, str]:
    # Provisioning needs no active-environment, loader, logging or credential settings.
    return {"HOME": str(Path.home()), "PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8"}


def provision_checked_python_environment(source_root: Path, *, interpreter: Path, uv: Path) -> CheckedPythonEnvironment:
    """One explicit setup; refuse existing or partial state instead of repairing it."""
    source_root = physical_directory(source_root)
    if interpreter.expanduser().absolute().resolve(strict=True) != interpreter.expanduser().absolute():
        raise CodexExecPythonEnvironmentError("provisioning requires an alias-free physical interpreter")
    interpreter = interpreter.expanduser().absolute()
    uv = uv.expanduser().resolve(strict=True)
    if not os.access(interpreter, os.X_OK) or not os.access(uv, os.X_OK):
        raise CodexExecPythonEnvironmentError("provisioning tools must be executable")
    root = source_root / ENVIRONMENT_PATH
    receipt_path = source_root / RECEIPT_PATH
    setup_root = receipt_path.parent
    for directory in (source_root / ".local", setup_root):
        if directory.exists() or directory.is_symlink():
            physical_directory(directory)
        else:
            directory.mkdir(mode=0o700)
    if any(path.exists() or path.is_symlink() for path in (root, receipt_path, setup_root / "provisioning.json")):
        raise CodexExecPythonEnvironmentError("checkout Python setup already exists; no automatic replacement")
    environment = _setup_environment()
    environment["PATH"] = f"{uv.parent}:/usr/bin:/bin"
    environment["UV_PROJECT_ENVIRONMENT"] = str(root)
    create = [str(interpreter), "-I", "-B", "-m", "venv", "--copies", "--without-pip", str(root)]
    # uv's requested interpreter is the physical base, not the environment copy:
    # requesting the copy makes uv recreate that environment through a managed alias.
    sync = [str(uv), "--no-config", "sync", "--project", str(source_root), "--python", str(interpreter),
            "--locked", "--offline", "--no-install-project", "--no-python-downloads",
            "--link-mode", "copy"]
    input_pins = {name: stable_file_hash(source_root / name) for name in ("pyproject.toml", "uv.lock")}
    plan = {"contract": ENVIRONMENT_CONTRACT, "argv": [create, sync], "inputs": input_pins,
            "physicalInterpreterSha256": stable_file_hash(interpreter), "uvSha256": stable_file_hash(uv)}
    _write_once(setup_root / "provisioning.json", (json.dumps(plan, sort_keys=True, indent=2) + "\n").encode())
    before_sync = None
    for index, argv in enumerate((create, sync)):
        result = subprocess.run(argv, cwd=source_root, env=environment, capture_output=True,
                                timeout=300 if index else 60, check=False)
        _write_once(setup_root / f"provision-{index}.stdout", result.stdout)
        _write_once(setup_root / f"provision-{index}.stderr", result.stderr)
        _write_once(setup_root / f"provision-{index}.json", json.dumps({"exitCode": result.returncode}).encode())
        if result.returncode != 0:
            raise CodexExecPythonEnvironmentError(f"explicit Python provisioning step {index} failed; state retained")
        runtime, _configuration_value, configuration_bytes = _copy_identity(root, expected_base=interpreter)
        copy_identity = (str(runtime), stable_file_hash(root / "bin/python"), sha256(configuration_bytes).hexdigest())
        if index == 0:
            before_sync = copy_identity
        elif copy_identity != before_sync:
            raise CodexExecPythonEnvironmentError("locked sync changed the physical interpreter/configuration")
    if input_pins != {name: stable_file_hash(source_root / name) for name in input_pins}:
        raise CodexExecPythonEnvironmentError("provisioning source inputs changed")
    snapshot = _snapshot(source_root)
    _write_once(receipt_path, (json.dumps(snapshot, sort_keys=True, indent=2) + "\n").encode())
    return inspect_checked_python_environment(source_root)
