"""Hosted test copies must satisfy admission without changing the source runtime."""

import hashlib
import os
from pathlib import Path

import pytest

from scripts.testing import provision_test_venv as runtime


def _copy(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"test-owned executable bytes")
    source.chmod(0o777)
    candidate = tmp_path / "copy"
    candidate.write_bytes(source.read_bytes())
    candidate.chmod(0o777)
    return source, candidate, hashlib.sha256(source.read_bytes()).hexdigest()


def test_only_verified_owned_copy_is_normalized_and_unsafe_mode_still_refuses(tmp_path):
    source, candidate, digest = _copy(tmp_path)
    before = runtime.file_record(source)
    with pytest.raises(runtime.ProvisionError, match="unsafe copy mode"):
        runtime.file_record(candidate, expected_hash=digest)
    record = runtime.file_record(candidate, expected_hash=digest, normalize_copy=True)
    assert record["mode"] == "0o755" and record["sha256"] == digest
    assert runtime.file_record(source) == before


@pytest.mark.parametrize("fault", ["symlink", "hardlink", "hash", "owner", "not-executable"])
def test_invalid_copy_refuses_before_permission_change(tmp_path, monkeypatch, fault):
    source, candidate, digest = _copy(tmp_path)
    if fault in {"symlink", "hardlink"}:
        candidate.unlink()
        if fault == "symlink":
            candidate.symlink_to(source)
        else:
            os.link(source, candidate)
    elif fault == "hash":
        candidate.write_bytes(b"changed")
    elif fault == "owner":
        uid = os.getuid()
        monkeypatch.setattr(runtime.os, "getuid", lambda: uid + 1)
    else:
        candidate.chmod(0o666)
    mode = candidate.stat().st_mode
    with pytest.raises(runtime.ProvisionError):
        runtime.file_record(candidate, expected_hash=digest, normalize_copy=True)
    assert candidate.stat().st_mode == mode
    assert source.stat().st_mode & 0o777 == 0o777


@pytest.fixture
def copied_environment(tmp_path, monkeypatch):
    for key in ("UV_PROJECT_ENVIRONMENT", "UV_PYTHON", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH"):
        monkeypatch.delenv(key, raising=False)
    source, facts = runtime.create_environment(tmp_path)
    return tmp_path, source, facts


def test_real_copies_preserve_runtime_and_refuse_config_alias_and_hash_drift(
        copied_environment, monkeypatch):
    root, source, facts = copied_environment
    command = [str(root / ".venv/bin/python")]
    baseline = runtime.observe(root, source, facts, command)
    assert baseline["runtime"]["version"] == facts["version"]
    assert baseline["runtime"]["physicalBasePrefix"] == facts["physicalBasePrefix"]
    with monkeypatch.context() as altered:
        altered.setattr(runtime, "runtime_facts", lambda *_: baseline["runtime"] | {"machine": "wrong"})
        with pytest.raises(runtime.ProvisionError, match="runtime facts differ"):
            runtime.observe(root, source, facts, command, expected=baseline)
    config = root / ".venv/pyvenv.cfg"
    original_config = config.read_bytes()
    config.write_bytes(original_config + b"\n# controlled drift\n")
    with pytest.raises(runtime.ProvisionError, match="environment drift"):
        runtime.observe(root, source, facts, command, expected=baseline)
    config.write_bytes(original_config)
    alias = root / ".venv/bin/python3"
    original_alias = alias.read_bytes()
    alias.unlink()
    alias.symlink_to("python")
    with pytest.raises(runtime.ProvisionError, match="regular file required"):
        runtime.observe(root, source, facts, command, expected=baseline)
    alias.unlink()
    alias.write_bytes(original_alias + b"controlled drift")
    alias.chmod(0o755)
    with pytest.raises(runtime.ProvisionError, match="copy hash differs"):
        runtime.observe(root, source, facts, command, expected=baseline)
    assert runtime.file_record(Path(source["path"])) == source


def test_existing_environment_is_never_replaced(copied_environment):
    root, source, _ = copied_environment
    before = (root / ".venv/pyvenv.cfg").read_bytes()
    with pytest.raises(FileExistsError):
        runtime.create_environment(root)
    assert (root / ".venv/pyvenv.cfg").read_bytes() == before
    assert runtime.file_record(Path(source["path"])) == source


def test_ambient_runtime_selection_refuses_before_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", str(tmp_path / "other"))
    with pytest.raises(runtime.ProvisionError, match="ambient interpreter selection"):
        runtime.create_environment(tmp_path)
    assert not (tmp_path / ".venv").exists()
