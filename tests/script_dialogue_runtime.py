"""Genuine locked tools for manual F4/F5 receiving, without Codex admission."""
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace


def _state(paths):
    result = {}
    for path in paths:
        if path.is_symlink():
            result[str(path)] = {"symlink": os.readlink(path)}
        elif path.exists():
            info = path.stat()
            result[str(path)] = {"sha256": sha256(path.read_bytes()).hexdigest(),
                "identity": [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink]}
        else:
            result[str(path)] = None
    return result


@contextmanager
def manual_validation_runtime(source, private):
    """Prove uv's actual engine before executing unchanged source-owned argv."""
    parent_environment = dict(os.environ)
    entry = Path(sys.executable).absolute()
    prefix = Path(sys.prefix).absolute()
    receipt = source / ".local/codex-exec/python-environment.json"
    paths = [source / name for name in ("pyproject.toml", "uv.lock", ".python-version")]
    paths.extend((prefix / "pyvenv.cfg", entry, entry.resolve(strict=True), receipt))
    before = _state(paths)
    work = private / "validation"
    tools = {}
    for name in ("uv", "node"):
        found = shutil.which(name)
        if found is None:
            raise RuntimeError(f"manual composition requires installed {name}")
        tools[name] = Path(found).resolve(strict=True)
    for name in ("tmp", "uv-cache"):
        (private / name).mkdir(mode=0o700)
    environment = {"PATH": os.pathsep.join((str(entry.parent), str(tools["node"].parent), os.defpath)),
        "LANG": "C.UTF-8", "TMPDIR": str(private / "tmp"),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(source / "src"), "PLOTLOOM_NODE": str(tools["node"]),
        "UV_PROJECT_ENVIRONMENT": str(prefix), "UV_NO_CONFIG": "1", "UV_OFFLINE": "1",
        "UV_PYTHON_DOWNLOADS": "never", "UV_CACHE_DIR": str(private / "uv-cache")}
    probe = ("import json,sys; from pathlib import Path; import pytest; import plotloom.script_receiving as app; "
        "print(json.dumps({'executable':sys.executable,'physicalExecutable':str(Path(sys.executable).resolve()),"
        "'prefix':sys.prefix,'physicalPrefix':str(Path(sys.prefix).resolve()),'version':list(sys.version_info[:3]),"
        "'appImport':app.__file__,'pytestImport':pytest.__file__}))")
    try:
        command = [str(tools["uv"]), "run", "--project", str(source), "--locked", "--no-sync", "python", "-B", "-c", probe]
        result = subprocess.run(command, cwd=work, env=environment,
            capture_output=True, text=True, timeout=15, check=True)
        facts = json.loads(result.stdout)
        assert facts["executable"] == str(entry), facts
        assert facts["physicalExecutable"] == str(entry.resolve(strict=True)), facts
        assert facts["prefix"] == sys.prefix and facts["physicalPrefix"] == str(prefix.resolve()), facts
        assert facts["version"] == list(sys.version_info[:3]), facts
        assert Path(facts["appImport"]) == source / "src/plotloom/script_receiving.py", facts
        assert Path(facts["pytestImport"]).resolve().is_relative_to(prefix.resolve()), facts
        node = subprocess.run([str(tools["node"]), "-p", "JSON.stringify({executable:process.execPath,version:process.version})"],
            cwd=work, env=environment, capture_output=True, text=True, timeout=15, check=True)
        node_facts = json.loads(node.stdout)
        assert Path(node_facts["executable"]) == tools["node"], node_facts
        observations = {"python": facts, "node": node_facts, "probeArgv": command,
            "tools": {key: str(value) for key, value in tools.items()},
            "operatorReceiptPresentBefore": receipt.exists(), "validationArgv": []}
        yield SimpleNamespace(tools=tools, environment=environment, observations=observations)
    finally:
        assert dict(os.environ) == parent_environment, "manual validator mutated parent environment"
        assert _state(paths) == before, "manual validator changed source/runtime configuration"
        if "observations" in locals():
            observations.update(parentEnvironmentUnchanged=True, sourceConfigurationUnchanged=True,
                operatorReceiptPresentAfter=receipt.exists())
            with (private / "runtime-observations.json").open("x") as output:
                json.dump(observations, output, indent=2)
                output.write("\n")
