"""Fresh current-source fixtures; never reuse retained native-proof packets."""
import hashlib
import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).absolute().parents[1]
BUILDER_PATH = ROOT / "scripts/autopilot/handoff_bundle.py"
spec = importlib.util.spec_from_file_location("_handoff_bundle_tests", BUILDER_PATH)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def private_directory(path):
    path.mkdir(mode=0o700)
    return path


def exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def current_test_qa():
    # Genuine current test-engine metadata, used only in synthetic test bundles.
    # The separately sealed operator bundle retains its approved real QA pin.
    entry = Path(sys.executable).absolute()
    physical = entry.resolve(strict=True)
    identities = {str(physical): {"kind": "regular", "bytes": physical.stat().st_size,
        "sha256": hashlib.sha256(physical.read_bytes()).hexdigest()}}
    if entry.is_symlink():
        identities[str(entry)] = {"kind": "symlink", "target": os.readlink(entry)}
    elif entry != physical:
        identities[str(entry)] = dict(identities[str(physical)])
    return builder.canonical({"kind": "plotloom.qa-project-interpreter.v1", "projectRoot": str(ROOT),
        "entrypoint": str(entry), "prefix": str(Path(sys.prefix).resolve()),
        "physicalBasePrefix": str(Path(sys.base_prefix).resolve()), "physicalExecutable": str(physical),
        "implementation": sys.implementation.name, "majorMinor": list(sys.version_info[:2]),
        "allowedInnerExecutables": [str(entry)], "identities": identities})


class ReadOnlyLoader(importlib.machinery.SourceFileLoader):
    def set_data(self, path, data, *, _mode=0o666):
        # Immutable bundles never become Python bytecode output locations.
        return None


def import_bundle(bundle):
    modules = {}
    for name in ("handoff_files", "handoff_source", "handoff_process", "handoff_phase", "handoff_receiver", "handoff_qa", "handoff_launch"):
        file = bundle / (name + ".py")
        loader = ReadOnlyLoader(name, str(file))
        module_spec = importlib.util.spec_from_file_location(name, file, loader=loader)
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[name] = module
        loader.exec_module(module)
        modules[name] = module
    return modules


@pytest.fixture(scope="session", name="capsule_bundle")
def capsule_bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("capsule-source").resolve()
    root.chmod(0o700)
    info = root.lstat()
    exclusive(root / "owner.json", builder.canonical({"evidenceClass": "synthetic_unit_only",
        "device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid}))
    bundle = private_directory(root / "bundle")
    qa = current_test_qa()
    seal = builder.seal_bundle(bundle, qa_bytes=qa)
    builder.verify_bundle(bundle, qa_bytes=qa)
    exclusive(root / "source-seal.json", builder.canonical(seal))
    return {"root": root, "bundle": bundle, "qa": qa, "seal": seal,
        "cases": private_directory(root / "cases"), "receipts": private_directory(root / "receipts")}


@pytest.fixture(scope="session", name="capsule_modules")
def capsule_modules(capsule_bundle):
    return import_bundle(capsule_bundle["bundle"])


@pytest.fixture(name="receiver_context")
def receiver_context(tmp_path, capsule_bundle, capsule_modules):
    f, binding, receiver = (capsule_modules[n] for n in ("handoff_files", "handoff_phase", "handoff_receiver"))
    tmp_path.chmod(0o700)
    root = private_directory(tmp_path / "synthetic-runtime")
    exclusive(tmp_path / "owner.json", f.canonical({"evidenceClass": "synthetic_unit_only"}))
    bundle = capsule_bundle["bundle"]
    controls_raw = f.read_owned(bundle / "source-controls.json")
    controls = f.parse(controls_raw)
    si, ri = bundle.lstat(), root.lstat()
    phase = {"version": 3, "kind": "handoff_proof_only", "authority": "synthetic_unit", "phaseRoot": str(root),
        "rootIdentity": [ri.st_dev, ri.st_ino, ri.st_uid], "sourceRoot": str(bundle),
        "sourceIdentity": [si.st_dev, si.st_ino, si.st_uid], "namespace": root.name, "nonce": "synthetic-receiver-only-0001",
        "sourceRevision": controls["sourceRevision"], "sourceTree": controls["sourceTree"],
        "controlsSha256": f.digest(controls_raw), "capsuleSha256": controls["capsuleSourceSha256"],
        "helperSha256": controls["files"]["node_helper.mjs"], "qaPinSha256": controls["files"]["qa-interpreter.json"],
        "allocationSha256": None,
        "entryArgvTemplate": binding.entry_argv("handoff_proof_only", root, "@PHASE_SHA256@"), "settlementAuthority": "none"}
    phase_raw = f.canonical(phase)
    exclusive(root / "phase.json", phase_raw)
    phase_sha = f.digest(phase_raw)
    binding.load_phase(root, phase_sha, expected_kind="handoff_proof_only")
    intent = {"version": 3, "authority": "synthetic_unit", "phaseSha256": phase_sha,
        "planSha256": f.digest(b"synthetic plan"), "anchorSha256": f.digest(b"synthetic independent anchor"),
        "capsuleSha256": phase["capsuleSha256"], "controlsSha256": phase["controlsSha256"], "helperSha256": phase["helperSha256"],
        "argvSha256": f.digest(f.canonical(binding.entry_argv(phase["kind"], root, phase_sha))),
        "allocationSha256": None, "invocationCount": 1}
    intent_sha = f.publish_record(root, "invocation-intent.json", intent)
    launch = {"pid": 100, "pgid": 100, "birthStart": "Thu Oct 15 06:09:00 2026", "startedMonotonicNs": "1000000000",
        "startedWallMs": 1000, "phaseSha256": phase_sha, "intentSha256": intent_sha}
    launch_sha = f.publish_record(root, "launch.json", launch)
    tree = {"launcher": {"pid": 100, "ppid": 1, "pgid": 100, "birthStart": launch["birthStart"], "commandSha256": "a" * 64},
        "driver": {"pid": 101, "ppid": 100, "pgid": 100, "birthStart": launch["birthStart"], "commandSha256": "b" * 64},
        "launchSha256": launch_sha}
    tree_sha = f.publish_record(root, "driver-process.json", tree)
    value = {"version": 3, "authority": "synthetic_unit", "phaseSha256": phase_sha, "phaseKind": phase["kind"],
        "namespace": phase["namespace"], "nonce": phase["nonce"], "intentSha256": intent_sha,
        "planSha256": intent["planSha256"], "anchorSha256": intent["anchorSha256"], "argvSha256": intent["argvSha256"],
        "launchSha256": launch_sha, "driverProcessSha256": tree_sha, "controlsSha256": phase["controlsSha256"],
        "capsuleSha256": phase["capsuleSha256"], "helperSha256": phase["helperSha256"],
        "allocationSha256": None, "nativeExecHandle": 42, "observedTree": tree}
    state = {"now": 1_000_000_100}

    def commit(changed=None, raw=None):
        content = raw if raw is not None else f.canonical(value if changed is None else changed)
        f.exclusive_bytes(root, "attendance.json", content)
        name = "attendance.commit-" + f.digest(content)
        f.exclusive_bytes(root, name, b"")
        return root / name

    def accept(wait=None):
        def advance(_seconds):
            state["now"] = 61_000_000_000
        return receiver.accept_attendance(phase, phase_sha, launch, tree,
            clock=lambda: state["now"], wait=wait or advance)

    return {"root": root, "bundle": bundle, "phase": phase, "phase_sha": phase_sha, "intent": intent, "launch": launch,
        "tree": tree, "value": value, "state": state, "commit": commit, "accept": accept, "files": f,
        "binding": binding, "receiver": receiver}
