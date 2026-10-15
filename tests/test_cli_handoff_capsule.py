"""Native focused entrypoint for Node contracts and reproducible bundle setup."""
import hashlib
import json
import os
import re
import shutil
import subprocess

import pytest

from tests.cli_handoff_fixtures import (
    ROOT,
    builder,
    exclusive,
    private_directory,
)
from tests.cli_handoff_fixtures import (
    capsule_bundle as _capsule_bundle,  # noqa: F401 -- explicit named pytest fixture registration
)


def test_actual_node_capsule_contracts(capsule_bundle):
    c = capsule_bundle
    builder.verify_bundle(c["bundle"], qa_bytes=c["qa"])
    node = shutil.which("node")
    assert node, "Node is required for the native capsule unit contracts"
    command = [node, "--test", "--test-concurrency=1", "--test-reporter=tap", str(ROOT / "tests/cli_handoff_capsule.test.mjs")]
    identities = {}
    streams = []
    for name in ("node-tap.log", "node-stderr.log"):
        target = c["receipts"] / name
        fd = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        identities[name] = os.fstat(fd)
        streams.append(os.fdopen(fd, "wb"))
    try:
        result = subprocess.run(command, cwd=ROOT, env=os.environ | {
            "PLOTLOOM_HANDOFF_TEST_BUNDLE": str(c["bundle"]), "PLOTLOOM_HANDOFF_TEST_ROOT": str(c["cases"])},
            stdout=streams[0], stderr=streams[1], timeout=90, check=False)
        for stream in streams:
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        for stream in streams:
            stream.close()
    logs = {}
    for name, before in identities.items():
        target = c["receipts"] / name
        after = target.lstat()
        assert (after.st_dev, after.st_ino, after.st_uid, after.st_nlink, after.st_mode & 0o777) == (
            before.st_dev, before.st_ino, os.getuid(), 1, 0o600)
        content = target.read_bytes()
        logs[name] = {"path": str(target), "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    tap = (c["receipts"] / "node-tap.log").read_text()
    errors = (c["receipts"] / "node-stderr.log").read_text()
    report = {"evidenceClass": "synthetic_unit_only", "command": command, "exitCode": result.returncode,
        "sourceRoot": str(c["bundle"]), "controlsSha256": c["seal"]["controlsSha256"], "logs": logs}
    exclusive(c["receipts"] / "node-result.json", builder.canonical(report))
    print(json.dumps(report, sort_keys=True))
    assert result.returncode == 0, tap + errors
    total = int(re.search(r"^# tests (\d+)$", tap, re.MULTILINE)[1])
    assert total > 35
    assert re.search(r"^# pass " + str(total) + r"$", tap, re.MULTILINE)
    assert re.search(r"^# fail 0$", tap, re.MULTILINE) and re.search(r"^# skipped 0$", tap, re.MULTILINE)
    builder.verify_bundle(c["bundle"], qa_bytes=c["qa"])


def test_missing_or_stale_bundle_is_refused(tmp_path):
    tmp_path.chmod(0o700)
    with pytest.raises((OSError, RuntimeError)):
        builder.verify_bundle(tmp_path / "missing")
    source = private_directory(tmp_path / "current-source")
    for name in builder.INPUT_FILES:
        exclusive(source / name, (builder.SOURCE / name).read_bytes())
    bundle = private_directory(tmp_path / "bundle")
    builder.seal_bundle(bundle, source=source)
    builder.verify_bundle(bundle, source=source)
    (source / "node_helper.mjs").write_bytes((source / "node_helper.mjs").read_bytes() + b"\n// changed current source\n")
    with pytest.raises(RuntimeError, match="bundle input differs from its actual owner source"):
        builder.verify_bundle(bundle, source=source)


def test_bundle_refuses_overwrite_and_unsafe_binding_path(tmp_path):
    tmp_path.chmod(0o700)
    bundle = private_directory(tmp_path / "bundle")
    builder.seal_bundle(bundle)
    with pytest.raises(RuntimeError, match="fresh and empty"):
        builder.seal_bundle(bundle)
    linked = tmp_path / "linked"
    linked.symlink_to(bundle, target_is_directory=True)
    with pytest.raises(RuntimeError, match="physical absolute"):
        builder.verify_bundle(linked)


def test_capsule_native_owners_include_its_current_support_closure():
    manifest = json.loads((ROOT / "scripts/testing/module-ownership.json").read_text())
    for target in ("tests/test_cli_handoff_capsule.py", "tests/test_cli_handoff_receiver.py"):
        owners = [name for name, module in manifest["modules"].items() if target in module["selectors"]["pytest"]]
        assert owners == ["shared-provider-dispatch"]
    dependencies = {item["path"]: item for item in manifest["support_dependencies"] if item["suite"] == "pytest"}
    for helper in ("tests/cli_handoff_fixtures.py", "tests/cli_handoff_fixtures.mjs", "tests/cli_handoff_capsule.test.mjs"):
        assert dependencies[helper]["consumers"] == ["shared-provider-dispatch"]
