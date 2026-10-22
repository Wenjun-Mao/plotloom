"""Provision the fresh, owned copied interpreter used by hosted test jobs."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACTS_CODE = """
import json, platform, sys
from pathlib import Path
print(json.dumps({
    "executable": sys.executable,
    "physicalExecutable": str(Path(sys.executable).resolve()),
    "baseExecutable": str(Path(sys._base_executable).resolve()),
    "prefix": sys.prefix,
    "basePrefix": sys.base_prefix,
    "physicalBasePrefix": str(Path(sys.base_prefix).resolve()),
    "implementation": sys.implementation.name,
    "version": list(sys.version_info[:3]),
    "machine": platform.machine(),
}))
"""


class ProvisionError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise ProvisionError(message)


def file_record(path: Path, *, expected_hash: str | None = None,
                normalize_copy: bool = False) -> dict:
    """Normalize only an already verified owned copy, through its open descriptor."""
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), f"regular file required: {path}")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        opened = os.fstat(stream.fileno())
        require((before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
                f"open identity changed: {path}")
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if expected_hash is not None:
            require(opened.st_uid == os.getuid() and opened.st_nlink == 1,
                    f"owned one-link copy required: {path}")
            require(digest == expected_hash, f"copy hash differs: {path}")
            require(bool(opened.st_mode & stat.S_IXUSR), f"owner executable required: {path}")
            if normalize_copy and opened.st_mode & 0o022:
                os.fchmod(stream.fileno(), stat.S_IMODE(opened.st_mode) & ~0o022)
            require(not os.fstat(stream.fileno()).st_mode & 0o022,
                    f"unsafe copy mode: {path}")
        after = os.fstat(stream.fileno())
        require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                == (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns),
                f"file changed during read: {path}")
        require(path.lstat() == after, f"path identity changed: {path}")
    return {"path": str(path), "device": after.st_dev, "inode": after.st_ino,
            "uid": after.st_uid, "links": after.st_nlink,
            "mode": oct(stat.S_IMODE(after.st_mode)), "bytes": after.st_size,
            "sha256": digest}


def runtime_facts(command: list[str], root: Path) -> dict:
    result = subprocess.run([*command, "-c", FACTS_CODE], cwd=root, check=True,
                            capture_output=True, text=True)
    return json.loads(result.stdout)


def create_environment(root: Path) -> tuple[dict, dict]:
    require(not any(os.environ.get(key) for key in (
        "UV_PROJECT_ENVIRONMENT", "UV_PYTHON", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH")),
        "ambient interpreter selection is not supported")
    source_facts = runtime_facts([sys.executable], root)
    require(source_facts["implementation"] == "cpython"
            and source_facts["version"][:2] == [3, 12], "selected CPython 3.12 required")
    source = file_record(Path(source_facts["baseExecutable"]))
    environment = root / ".venv"
    # Exclusive creation prevents this helper from replacing an existing environment.
    environment.mkdir(mode=0o700)
    subprocess.run([sys.executable, "-m", "venv", "--copies", "--without-pip",
                    str(environment)], cwd=root, check=True)
    for name in ("python", "python3", "python3.12"):
        file_record(environment / "bin" / name, expected_hash=source["sha256"],
                    normalize_copy=True)
    return source, source_facts


def observe(root: Path, source: dict, source_facts: dict,
            command: list[str], *, expected: dict | None = None) -> dict:
    environment = root / ".venv"
    entry = environment / "bin/python"
    copies = [file_record(environment / "bin" / name, expected_hash=source["sha256"])
              for name in ("python", "python3", "python3.12")]
    config = file_record(environment / "pyvenv.cfg")
    require(config["uid"] == os.getuid() and config["links"] == 1
            and not int(config["mode"], 8) & 0o022, "unsafe venv configuration")
    facts = runtime_facts(command, root)
    require(facts["executable"] == facts["physicalExecutable"] == str(entry)
            and facts["prefix"] == str(environment), "copied runtime selection changed")
    require(all(facts[key] == source_facts[key] for key in (
        "baseExecutable", "physicalBasePrefix", "implementation", "version", "machine")),
        "copied runtime facts differ")
    require(copies == [file_record(Path(row["path"]), expected_hash=source["sha256"])
                       for row in copies], "copy identity changed during probe")
    require(config == file_record(environment / "pyvenv.cfg"), "venv configuration changed")
    result = {"copies": copies, "configuration": config,
              "pyvenvCfg": (environment / "pyvenv.cfg").read_text(), "runtime": facts}
    require(expected is None or result == expected, "test environment drift")
    return result


def provision(root: Path = ROOT) -> None:
    source, source_facts = create_environment(root)
    entry = root / ".venv/bin/python"
    baseline = observe(root, source, source_facts, [str(entry)])
    print(json.dumps({"stage": "before-frozen-sync", "source": source,
                      "sourceRuntime": source_facts, **baseline}), flush=True)
    subprocess.run(["uv", "sync", "--all-groups", "--frozen"], cwd=root, check=True)
    for stage, command in (("after-frozen-sync", [str(entry)]),
                           ("subsequent-uv-run", ["uv", "run", "--locked", "--no-sync", "python"]),
                           ("subsequent-uv-sync", ["uv", "run", "--locked", "python"])):
        current = observe(root, source, source_facts, command, expected=baseline)
        print(json.dumps({"stage": stage, **current}), flush=True)
    require(file_record(Path(source["path"])) == source, "source interpreter changed")
    subprocess.run([str(entry), "-c", """
import sys, plotloom, pytest, tests
from pathlib import Path
root = Path.cwd()
assert Path(plotloom.__file__) == root / "src/plotloom/__init__.py"
assert Path(tests.__file__) == root / "tests/__init__.py"
assert Path(pytest.__file__).is_relative_to(Path(sys.prefix))
print("checkout and frozen pytest imports verified", sys.executable)
"""], cwd=root, check=True)


if __name__ == "__main__":
    provision()
