"""Regression coverage for the exact-path ImageGen staging cleanup helper."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def cleanup_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_imagegen_staging.py"
    spec = importlib.util.spec_from_file_location("cleanup_imagegen_staging", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, content: bytes = b"generated-image") -> tuple[Path, Path, Path]:
    package = tmp_path / "exchange" / "jobs" / "ij_1234567890abcdefghij" / "package"
    output_root = package.parent / "delivery" / "outputs"
    package.mkdir(parents=True)
    output_root.mkdir(parents=True)
    request_hash = "a" * 64
    (package / "request.json").write_text(json.dumps({"jobId": "ij_1234567890abcdefghij", "requestHash": request_hash}))
    (package.parent / "delivery" / "completion.json").write_text(json.dumps({
        "schemaVersion": 1,
        "jobId": "ij_1234567890abcdefghij",
        "requestHash": request_hash,
        "deliveryId": "fixture-delivery",
        "actualPrompt": "Fixture only.",
        "outputs": [{"filename": "candidate.png", "sha256": sha256(content).hexdigest(), "role": "original"}],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "fixture", "available": True},
    }))
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_THREAD_ID", "fixture-task")
    staging = codex_home / "generated_images" / "fixture-task"
    staging.mkdir(parents=True)
    os.chmod(staging, 0o700)
    os.chmod(package.parent / "delivery", 0o700)
    os.chmod(output_root, 0o700)
    staged = staging / "candidate.png"
    staged.write_bytes(content)
    return package, staging, staged


def test_cleanup_copies_verifies_and_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)

    result = cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])

    destination = package.parent / "delivery" / "outputs" / "candidate.png"
    assert result.copied == (destination,)
    assert result.removed == (staged,)
    assert destination.read_bytes() == b"generated-image"
    assert not staged.exists()

    repeat = cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])
    assert repeat.already_present == (destination,)
    assert repeat.already_removed == (staged,)


def test_cleanup_keeps_staging_when_manifest_hash_does_not_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch, content=b"real-bytes")
    completion = package.parent / "delivery" / "completion.json"
    payload = json.loads(completion.read_text())
    payload["outputs"][0]["sha256"] = "b" * 64
    completion.write_text(json.dumps(payload))

    with pytest.raises(cleanup_module.CleanupError, match="does not match"):
        cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])

    assert staged.read_bytes() == b"real-bytes"
    assert not (package.parent / "delivery" / "outputs" / "candidate.png").exists()


def test_cleanup_rejects_foreign_paths_and_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)
    foreign = tmp_path / "foreign.png"
    foreign.write_bytes(staged.read_bytes())

    with pytest.raises(cleanup_module.CleanupError, match="direct child"):
        cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[foreign])
    assert staged.exists()

    staged.unlink()
    staged.symlink_to(foreign)
    with pytest.raises(cleanup_module.CleanupError, match="without following a symlink"):
        cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])
    assert staged.is_symlink()


def test_cleanup_never_overwrites_an_incompatible_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)
    destination = package.parent / "delivery" / "outputs" / "candidate.png"
    destination.write_bytes(b"different-bytes")

    with pytest.raises(cleanup_module.CleanupError, match="overwritten incompatibly"):
        cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])

    assert staged.exists()
    assert destination.read_bytes() == b"different-bytes"


def test_cleanup_requires_all_manifest_outputs_in_one_verified_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)
    second = staging / "second.png"
    second.write_bytes(b"second-image")
    completion = package.parent / "delivery" / "completion.json"
    payload = json.loads(completion.read_text())
    payload["outputs"].append({
        "filename": second.name,
        "sha256": sha256(second.read_bytes()).hexdigest(),
        "role": "refinement",
    })
    completion.write_text(json.dumps(payload))

    result = cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged, second])
    assert set(result.removed) == {staged, second}
    assert {path.name for path in result.copied} == {"candidate.png", "second.png"}


def test_cleanup_rejects_another_real_staging_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, _staging, staged = _delivery(tmp_path, monkeypatch)
    unrelated = tmp_path / "unrelated-staging"
    unrelated.mkdir()
    foreign = unrelated / staged.name
    foreign.write_bytes(staged.read_bytes())

    with pytest.raises(cleanup_module.CleanupError, match="does not match this task"):
        cleanup_module.cleanup_staging(package=package, staging_root=unrelated, staged_paths=[foreign])
    assert foreign.exists()


@pytest.mark.parametrize("task_id", ["../outside", "/tmp/outside", "fixture/task", r"fixture\\task", "fixture:task", "fixture task", " fixture-task", "fixture-task ", ".", ".."])
def test_cleanup_rejects_path_shaped_task_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module, task_id: str) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setenv("CODEX_THREAD_ID", task_id)

    with pytest.raises(cleanup_module.CleanupError, match="path-safe task identifier"):
        cleanup_module._task_staging_root()


def test_cleanup_rejects_a_symlinked_delivery_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)
    delivery = package.parent / "delivery"
    outside = tmp_path / "outside-delivery"
    outside.mkdir()
    for entry in delivery.iterdir():
        entry.rename(outside / entry.name)
    delivery.rmdir()
    delivery.symlink_to(outside, target_is_directory=True)

    with pytest.raises(cleanup_module.CleanupError, match="delivery must be a real directory"):
        cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])
    assert staged.exists()


@pytest.mark.parametrize("directory_name", ["staging", "delivery", "outputs"])
def test_cleanup_refuses_non_private_transaction_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module, directory_name: str) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)
    directories = {
        "staging": staging,
        "delivery": package.parent / "delivery",
        "outputs": package.parent / "delivery" / "outputs",
    }
    os.chmod(directories[directory_name], 0o755)

    with pytest.raises(cleanup_module.CleanupError, match="private to the current user"):
        cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])
    assert staged.exists()


def test_cleanup_refuses_a_concurrent_staging_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_module) -> None:
    package, staging, staged = _delivery(tmp_path, monkeypatch)
    holder = subprocess.Popen(
        [sys.executable, "-c", "import fcntl, os, sys; fd = os.open(sys.argv[1], os.O_RDONLY); fcntl.flock(fd, fcntl.LOCK_EX); print('locked', flush=True); sys.stdin.readline()", str(staging)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None and holder.stdout.readline().strip() == "locked"
        with pytest.raises(cleanup_module.CleanupError, match="busy"):
            cleanup_module.cleanup_staging(package=package, staging_root=staging, staged_paths=[staged])
        assert staged.exists()
    finally:
        assert holder.stdin is not None
        holder.communicate("\n", timeout=5)
