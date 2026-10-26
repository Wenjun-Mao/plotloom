"""Process lifecycle and exact-evidence tests for the Mac supervisor."""
import json

import pytest
from codex_exec_supervisor_test_support import _prepared_text_job


def test_worker_environment_does_not_inherit_credentials(monkeypatch, supervisor):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("PLOTLOOM_CREATOR_WORKBENCH_TOKEN", "bridge-secret")
    monkeypatch.setenv("PLOTLOOM_DATABASE_PASSWORD", "database-secret")

    environment = supervisor._worker_environment()

    assert not {"OPENAI_API_KEY", "PLOTLOOM_CREATOR_WORKBENCH_TOKEN", "PLOTLOOM_DATABASE_PASSWORD"} & environment.keys()
    assert environment["PYTHONUNBUFFERED"] == "1"



def test_cli_environment_uses_only_the_frozen_text_runtime(monkeypatch, supervisor, tmp_path):
    from codex_exec_supervisor_test_support import _write_fake_cli

    from plotloom.codex_exec_profile import NODE_OPENSSL_CONFIG
    from plotloom.codex_exec_python_environment import (
        inspect_checked_python_environment,
    )
    from plotloom.codex_exec_resources import CodexExecSourceResources
    from plotloom.codex_exec_runtime_tree import python_source_identity

    monkeypatch.setenv("PYTHONPATH", "/untrusted/python-path")
    monkeypatch.setenv("NODE_OPTIONS", "--require=/untrusted/hook.js")
    monkeypatch.setenv("PLOTLOOM_SOURCE_ROOT", "/untrusted/source")
    monkeypatch.setenv("OPENSSL_CONF", "/untrusted/openssl.cnf")
    monkeypatch.setenv("UV_NO_MANAGED_PYTHON", "1")
    monkeypatch.setenv("UV_PYTHON", "/untrusted/python")
    private_dir = tmp_path / "private-attempt"
    private_dir.mkdir()
    checked = inspect_checked_python_environment(supervisor.source_root)
    source_resources = CodexExecSourceResources(
        read_paths=(),
        tools=(
            ("uv", tmp_path / "uv"),
            ("python", checked.interpreter),
        ),
        python_environment=checked.root,
        python_environment_hash=checked.identity_hash,
        python_source_hash=python_source_identity(supervisor.source_root)[1],
    )

    profile = _write_fake_cli(supervisor, "raise SystemExit(0)\n")
    text_environment = supervisor._cli_environment(
        private_dir, source_root=supervisor.source_root, domain="text",
        source_resources=source_resources, profile=profile,
    )
    image_environment = supervisor._cli_environment(
        private_dir, source_root=supervisor.source_root, domain="image", profile=profile
    )

    assert text_environment["PLOTLOOM_SOURCE_ROOT"] == str(supervisor.source_root)
    assert text_environment["PYTHONPATH"] == str(supervisor.source_root / "src")
    assert text_environment["UV_PROJECT_ENVIRONMENT"] == str(checked.root)
    assert text_environment["UV_PYTHON"] == str(checked.base_interpreter)
    assert "UV_NO_MANAGED_PYTHON" not in text_environment
    assert text_environment["PYTHONPYCACHEPREFIX"] == str(private_dir / "python-cache-disabled")
    assert (private_dir / "python-cache-disabled").is_file()
    assert text_environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert text_environment["PYTHONNOUSERSITE"] == "1"
    assert text_environment["PLOTLOOM_UV"] == str(tmp_path / "uv")
    assert text_environment["PLOTLOOM_PYTHON"] == str(checked.interpreter)
    assert text_environment["UV_CACHE_DIR"] == str(private_dir / "uv-cache")
    assert text_environment["TMPDIR"] == str(private_dir / "tmp")
    assert text_environment["TMPPREFIX"] == str(private_dir / "tmp" / "zsh")
    assert text_environment["OPENSSL_CONF"] == str(NODE_OPENSSL_CONFIG)
    assert "NODE_OPTIONS" not in text_environment
    assert "PLOTLOOM_SOURCE_ROOT" not in image_environment
    assert "PYTHONPATH" not in image_environment
    assert "NODE_OPTIONS" not in image_environment
    assert "OPENSSL_CONF" not in image_environment
    node_environment = supervisor._cli_environment(
        private_dir, source_root=supervisor.source_root, domain="text",
        source_resources=CodexExecSourceResources((), (("node", tmp_path / "node"),)), profile=profile,
    )
    assert "PYTHONPATH" not in node_environment and "UV_PROJECT_ENVIRONMENT" not in node_environment
    assert node_environment["OPENSSL_CONF"] == str(NODE_OPENSSL_CONFIG)

    text_filesystem = supervisor._permission_filesystem_config(
        profile, private_dir, private_dir / "delivery", private_dir, supervisor.codex_home,
        domain="text",
    )
    image_filesystem = supervisor._permission_filesystem_config(
        profile, private_dir, private_dir / "delivery", private_dir, supervisor.codex_home,
        domain="image",
    )
    assert f'{json.dumps(str(NODE_OPENSSL_CONFIG))}="read"' in text_filesystem
    assert f'{json.dumps(str(NODE_OPENSSL_CONFIG))}="read"' not in image_filesystem
    assert '":slash_tmp"="deny"' in text_filesystem
    assert '":slash_tmp"="deny"' in image_filesystem



def test_admission_persists_exact_spawn_intent_before_starting_private_worker(supervisor, tmp_path):
    _exchange, _request, _pin, _job_root, attempt, _profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source="import sys, time\nsys.stdin.read()\ntime.sleep(30)\n"
    )
    try:
        status = supervisor.admit(attempt)
        assert status.state in {"spawn_intent", "running"}
        assert supervisor._row(attempt.attempt_id)["attempt_json"] == attempt.model_dump_json(by_alias=True)
        assert supervisor._row(attempt.attempt_id)["private_dir"].endswith(str(attempt.attempt_id))
        row = supervisor._row(attempt.attempt_id)
        assert row["worker_pid"] is not None
        assert supervisor._owns_worker(row)
    finally:
        current = supervisor.status(attempt.attempt_id)
        if current.attempt is not None and current.state in {"running", "spawn_intent"}:
            supervisor.cancel(current.attempt)
        worker = supervisor._workers.get(str(attempt.attempt_id))
        if worker is not None:
            worker.wait(timeout=5)



@pytest.mark.parametrize("revision", [None, "f" * 40], ids=["missing", "forged"])
def test_admission_rejects_missing_or_forged_plotloom_revision_before_reserving(
    supervisor, tmp_path, revision
):
    from codex_exec_supervisor_errors import CodexExecSupervisorError
    from pydantic import ValidationError

    _exchange, _request, _pin, _job_root, attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    unbound = attempt.model_copy(update={"plotloom_code_revision": revision})
    if revision is None:
        with pytest.raises(ValidationError, match="source-pinned text attempt"):
            supervisor.admit(unbound)
    else:
        with pytest.raises(CodexExecSupervisorError, match="Plotloom source revision"):
            supervisor.admit(unbound)
    assert supervisor._row(attempt.attempt_id) is None
    assert not supervisor._workers
