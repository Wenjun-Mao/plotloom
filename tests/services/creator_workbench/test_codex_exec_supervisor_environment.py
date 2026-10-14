"""Freeze runtime and source identities at each trusted child boundary."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from codex_exec_supervisor_errors import (
    CodexExecSupervisorError,
    CodexExecValidationFailure,
)
from codex_exec_supervisor_test_support import _prepared_text_job

from plotloom.codex_exec_resources import codex_exec_source_resources


def test_trusted_python_ignores_valid_bytecode_seeded_in_the_old_cli_writable_cache(supervisor, tmp_path):
    from codex_exec_supervisor_test_support import _write_fake_cli

    from tests.test_codex_exec_resources import _pin, upstream_skill_path_for_stage

    request = {"stage": "branches", "upstreamSkillPath": upstream_skill_path_for_stage("branches"),
               "executionPin": _pin("branches")}
    resources = codex_exec_source_resources(supervisor.source_root, request)
    profile = _write_fake_cli(supervisor, "raise SystemExit(0)\n")
    private = tmp_path / "private-attempt"
    private.mkdir()
    environment = supervisor._cli_environment(
        private, source_root=supervisor.source_root, domain="text", source_resources=resources, profile=profile,
    )
    source = supervisor.source_root / "src/plotloom/validation.py"
    original = source.read_bytes()
    metadata = source.stat()
    seed = private / "tmp/seed.py"
    malicious = b"CODEX_CACHE_PROBE = 'untrusted'\n#"
    seed.write_bytes(malicious + b" " * (len(original) - len(malicious)))
    os.utime(seed, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    old_prefix = private / "tmp/python-bytecode"
    unsafe_environment = environment | {"PYTHONPYCACHEPREFIX": str(old_prefix)}
    interpreter = dict(resources.tools)["python"]
    compile_code = (
        "import importlib.util,pathlib,py_compile,sys; "
        "cache=importlib.util.cache_from_source(sys.argv[2]); pathlib.Path(cache).parent.mkdir(parents=True); "
        "py_compile.compile(sys.argv[1],cfile=cache,dfile=sys.argv[2],doraise=True); print(cache)"
    )
    seeded = subprocess.run([str(interpreter), "-B", "-c", compile_code, str(seed), str(source)],
                            env=unsafe_environment, capture_output=True, text=True, timeout=10, check=False)
    assert seeded.returncode == 0, seeded.stderr
    assert str(old_prefix) in seeded.stdout
    code = "import plotloom.validation as validation; print(getattr(validation,'CODEX_CACHE_PROBE','pinned_source'))"
    unsafe = subprocess.run([str(interpreter), "-B", "-c", code], env=unsafe_environment,
                            capture_output=True, text=True, timeout=10, check=False)
    trusted = subprocess.run([str(interpreter), "-B", "-c", code], env=environment,
                             capture_output=True, text=True, timeout=10, check=False)
    assert unsafe.returncode == trusted.returncode == 0, (unsafe.stderr, trusted.stderr)
    assert unsafe.stdout.strip() == "untrusted"
    assert trusted.stdout.strip() == "pinned_source"
    assert sha256(source.read_bytes()).digest() == sha256(original).digest()


@pytest.mark.parametrize("unowned_kind", ["directory", "symlink", "nonempty"])
def test_python_cache_lookup_cannot_be_seeded_or_redirected(supervisor, tmp_path, unowned_kind):
    private = tmp_path / "private-attempt"
    private.mkdir()
    marker = private / "python-cache-disabled"
    if unowned_kind == "directory":
        marker.mkdir()
        (marker / "seeded.pyc").write_bytes(b"untrusted bytecode")
    elif unowned_kind == "symlink":
        marker.symlink_to(tmp_path)
    else:
        marker.write_bytes(b"untrusted")
    with pytest.raises(ValueError):
        supervisor._disabled_python_cache(private)


def test_changed_python_resources_cannot_construct_a_child_environment(supervisor, tmp_path):
    from tests.test_codex_exec_resources import _pin, upstream_skill_path_for_stage

    request = {"stage": "branches", "upstreamSkillPath": upstream_skill_path_for_stage("branches"),
               "executionPin": _pin("branches")}
    resources = codex_exec_source_resources(supervisor.source_root, request)
    private = tmp_path / "private-attempt"
    private.mkdir()
    from codex_exec_supervisor_test_support import _write_fake_cli
    profile = _write_fake_cli(supervisor, "raise SystemExit(0)\n")
    for stale in (
        replace(resources, python_environment_hash="0" * 64),
        replace(resources, python_source_hash="0" * 64),
        replace(resources, python_environment=supervisor.source_root / ".venv"),
    ):
        with pytest.raises(CodexExecSupervisorError, match="resources changed"):
            supervisor._cli_environment(private, source_root=supervisor.source_root, domain="text",
                                        source_resources=stale, profile=profile)


def test_runtime_drift_after_a_successful_renderer_cannot_create_validation_evidence(
    supervisor, tmp_path, monkeypatch,
):
    _exchange, _request, _pin, job, attempt, profile = _prepared_text_job(supervisor, tmp_path)
    package_request = json.loads((job / "package/request.json").read_bytes())
    resources = codex_exec_source_resources(supervisor.source_root, package_request)
    (job / "delivery").mkdir()
    (job / "delivery/outline.json").write_text("{\"candidate\": true}")
    private = tmp_path / "private-attempt"
    private.mkdir()
    calls = []

    def current_profile():
        calls.append("profile")
        return profile if len(calls) == 1 else SimpleNamespace(profile_hash="0" * 64)

    monkeypatch.setattr(supervisor, "profile", current_profile)
    monkeypatch.setattr(supervisor, "_require_validation_not_cancelled", lambda *_a: None)
    monkeypatch.setattr(supervisor, "_spawn_validation_process", lambda *_a: (object(), (1, 1, "test")))

    def completed_step(_attempt, _step_id, _process, _identity, **options):
        if options["stdout_path"].name == "report.html":
            options["stdout_path"].write_bytes(b"<!doctype html><html><body>trusted renderer</body></html>")
        return 0

    monkeypatch.setattr(supervisor, "_wait_validation_process", completed_step)
    with pytest.raises(CodexExecValidationFailure, match="validation_final_runtime_changed"):
        supervisor._validate_text_delivery(attempt, profile, package_request, job, private, resources)
    assert len(calls) == 2
    assert not (job / "delivery/completion.json").exists()
