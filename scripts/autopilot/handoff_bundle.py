"""Offline fixed-source binding; never a runtime module/URI loader."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handoff.handoff_source import ENTRY_REGISTRY, WORKFLOW_FILES, source_identity

SOURCE = Path(__file__).absolute().parent / "handoff"
INPUT_FILES = (*WORKFLOW_FILES, "qa-interpreter.json")
FILES = (*INPUT_FILES, "source-identity.json", "paid-allocation.json")
BUILTINS = ["node:fs/promises", "node:fs", "node:crypto", "node:os", "node:path", "node:url"]


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def owned_directory(root):
    root = Path(root)
    if not root.is_absolute() or root != root.resolve(strict=True) or not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(root)):
        raise RuntimeError("bundle requires a physical absolute literal-safe path")
    for at in [*reversed(root.parents), root]:
        if not stat.S_ISDIR(at.lstat().st_mode):
            raise RuntimeError("linked bundle ancestor")
    info = root.lstat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError("bundle requires owner 0700")
    return root, [info.st_dev, info.st_ino, info.st_uid]


def read_regular(path, *, private=False):
    before = path.lstat()
    def identity(s):
        return (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1:
        raise RuntimeError("unsafe source regular file")
    if (private and stat.S_IMODE(before.st_mode) != 0o600) or before.st_mode & 0o022:
        raise RuntimeError("unsafe source mode")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if identity(before) != identity(os.fstat(stream.fileno())):
            raise RuntimeError("source open identity changed")
        raw = stream.read(1_000_001)
        if len(raw) > 1_000_000 or identity(before) != identity(os.fstat(stream.fileno())) or identity(before) != identity(path.lstat()):
            raise RuntimeError("source read identity changed")
    return raw


def bound_sources(root, *, source=SOURCE, qa_bytes=None, allocation_bytes=None):
    inputs = {name: read_regular(Path(source) / name) for name in INPUT_FILES}
    result = dict(inputs)
    template = result["capsule.mjs"].decode()
    if template.count("@SEALED_BUNDLE_ROOT@") != 4:
        raise RuntimeError("fixed capsule binding token contract")
    result["capsule.mjs"] = template.replace("@SEALED_BUNDLE_ROOT@", str(root)).encode()
    if qa_bytes is not None:
        result["qa-interpreter.json"] = qa_bytes
    qa_template = result["handoff_qa.py"].decode()
    if qa_template.count("@QA_PIN_SHA256@") != 1:
        raise RuntimeError("fixed QA pin token contract")
    result["handoff_qa.py"] = qa_template.replace("@QA_PIN_SHA256@", digest(result["qa-interpreter.json"])).encode()
    qa = json.loads(result["qa-interpreter.json"])
    owner = source_identity(Path(qa["projectRoot"]))
    for name in WORKFLOW_FILES:
        if owner["files"]["scripts/autopilot/handoff/" + name] != digest(inputs[name]):
            raise RuntimeError("bundle input differs from its actual owner source: " + name)
    result["source-identity.json"] = canonical(owner)
    if allocation_bytes is not None:
        from handoff.paid_outline_contracts import PaidOutlineAllocation
        allocation = PaidOutlineAllocation.model_validate_json(allocation_bytes)
        if canonical(json.loads(allocation_bytes)) != allocation_bytes:
            raise RuntimeError("paid allocation must be canonical")
        if (not owner["committed"] or allocation.bundle_root.path != str(root)
                or allocation.source.revision != owner["revision"] or allocation.source.tree != owner["tree"]
                or allocation.source.workflow_closure_sha256 != owner["closureSha256"]
                or allocation.source.bundle_source_identity_sha256 != digest(result["source-identity.json"])
                or allocation.validator_runtime.qa_pin_sha256 != digest(result["qa-interpreter.json"])
                or allocation.namespace.source_root.path != qa["projectRoot"]):
            raise RuntimeError("paid allocation source/QA/bundle binding differs")
        result["paid-allocation.json"] = allocation_bytes
    return result, {name: digest(value) for name, value in inputs.items()}


def controls_for(root, identity, contents):
    capsule = contents["capsule.mjs"].decode()
    prefix, suffix = "export const Capsule = ", ";\n"
    if not capsule.startswith(prefix) or not capsule.endswith(suffix):
        raise RuntimeError("named capsule source contract")
    helper = contents["node_helper.mjs"].decode()
    start = helper.index("export async function dispatch(")
    helper_source = helper[start:].removeprefix("export ").rstrip()
    owner = json.loads(contents["source-identity.json"])
    return {"version": 3, "kind": "capsule_source_controls.v3", "sourceRoot": str(root), "sourceIdentity": identity,
        "sourceRevision": owner["revision"], "sourceTree": owner["tree"],
        "files": {name: digest(value) for name, value in contents.items()},
        "registry": ENTRY_REGISTRY,
        "builtinImports": BUILTINS, "capsuleSourceSha256": digest(capsule[len(prefix):-len(suffix)].encode()),
        "helperExportSha256": digest(helper_source.encode())}


def seal_bundle(root, *, source=SOURCE, qa_bytes=None, allocation_bytes=None):
    root, identity = owned_directory(root)
    if list(root.iterdir()):
        raise RuntimeError("bundle must be fresh and empty; no overwrite or repair")
    contents, inputs = bound_sources(root, source=source, qa_bytes=qa_bytes, allocation_bytes=allocation_bytes)
    controls = controls_for(root, identity, contents)
    for name, raw in {**contents, "source-controls.json": canonical(controls)}.items():
        fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if read_regular(root / name, private=True) != raw:
            raise RuntimeError("bundle readback changed")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return {"kind": "owned_handoff_bundle_seal.v3", "sourceRoot": str(root), "sourceIdentity": identity,
        "sourceInputs": inputs, "qaOverrideForSyntheticTests": qa_bytes is not None,
        "controlsSha256": digest(canonical(controls)), "capsuleSourceSha256": controls["capsuleSourceSha256"],
        "helperExportSha256": controls["helperExportSha256"], "files": controls["files"],
        "paidPositiveCriterion": "OPEN: source/test evidence is not actual paid qualification", "immutableAfterSeal": True}


def verify_bundle(root, *, source=SOURCE, qa_bytes=None, allocation_bytes=None):
    root, identity = owned_directory(root)
    contents, inputs = bound_sources(root, source=source, qa_bytes=qa_bytes, allocation_bytes=allocation_bytes)
    controls = controls_for(root, identity, contents)
    if {p.name for p in root.iterdir()} != {*contents, "source-controls.json"}:
        raise RuntimeError("missing or extra bundle closure")
    for name, expected in {**contents, "source-controls.json": canonical(controls)}.items():
        if read_regular(root / name, private=True) != expected:
            raise RuntimeError("stale bundle source: " + name)
    return {"sourceInputs": inputs, "controlsSha256": digest(canonical(controls))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(seal_bundle(args.root), sort_keys=True))
