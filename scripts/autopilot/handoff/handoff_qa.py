"""Explicit existing QA interpreter; no production imports or fallback selection."""
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

I = Path(__file__).absolute().parent
PIN_SHA256 = "@QA_PIN_SHA256@"


def admit(role):
    # Keep the entry gate parseable by the rejected ambient 3.9 interpreter.
    # Selection/version precede workflow imports, argument handling or writes.
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        raise RuntimeError("explicit CPython 3.12 QA interpreter required")
    path = I / "qa-interpreter.json"
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise RuntimeError("unsafe QA pin")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino) or opened.st_size > 100000:
            raise RuntimeError("QA pin identity changed")
        raw = stream.read(100001)
    if hashlib.sha256(raw).hexdigest() != PIN_SHA256:
        raise RuntimeError("QA pin bytes changed")
    pin = json.loads(raw)
    facts = {"implementation": sys.implementation.name, "majorMinor": list(sys.version_info[:2]),
        "prefix": str(Path(sys.prefix).resolve()), "physicalBasePrefix": str(Path(sys.base_prefix).resolve()),
        "executable": os.path.abspath(sys.executable), "physicalExecutable": str(Path(sys.executable).resolve())}
    if not Path(pin["projectRoot"]).is_absolute() or role not in {"outer", "inner"}:
        raise RuntimeError("wrong QA project or role")
    for key in ("implementation", "majorMinor", "prefix", "physicalBasePrefix", "physicalExecutable"):
        if facts[key] != pin[key]:
            raise RuntimeError("QA identity: " + key)
    allowed = [pin["entrypoint"]] if role == "outer" else pin["allowedInnerExecutables"]
    if facts["executable"] not in allowed:
        raise RuntimeError("QA executable selection changed")
    for name, expected in pin["identities"].items():
        candidate = Path(name)
        meta = candidate.lstat()
        if stat.S_ISLNK(meta.st_mode):
            actual = {"kind": "symlink", "target": os.readlink(candidate)}
        elif stat.S_ISREG(meta.st_mode):
            content = candidate.read_bytes()
            actual = {"kind": "regular", "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
        else:
            raise RuntimeError("QA identity type changed")
        if actual != expected:
            raise RuntimeError("QA configuration/alias/binary drift")
    return {"role": role, **facts, "qaPinSha256": PIN_SHA256}
