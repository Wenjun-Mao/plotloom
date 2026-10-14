"""Checked-lock environment drift and import-boundary regressions."""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from plotloom.codex_exec_python_environment import (
    ENVIRONMENT_PATH,
    RECEIPT_PATH,
    CodexExecPythonEnvironmentError,
    _snapshot,
    inspect_checked_python_environment,
    provision_checked_python_environment,
)
from plotloom.codex_exec_runtime_tree import (
    CodexExecRuntimeTreeError,
    python_source_identity,
    runtime_tree_hash,
)


def _source(tmp_path):
    source = tmp_path.resolve() / "checkout"
    source.mkdir()
    (source / "pyproject.toml").write_text("checked project")
    (source / "uv.lock").write_text("checked lock")
    (source / "src/plotloom").mkdir(parents=True)
    (source / "src/plotloom/__init__.py").write_text("VALUE = 1\n")
    runtime = tmp_path.resolve() / "cpython-3.12.13-fixture"
    (runtime / "bin").mkdir(parents=True)
    base = runtime / "bin/python3.12"
    base.write_bytes(b"physical interpreter bytes")
    base.chmod(0o700)
    return source, base


def _make_copy(root, base):
    (root / "bin").mkdir(parents=True)
    copied = root / "bin/python"
    copied.write_bytes(base.read_bytes())
    copied.chmod(0o700)
    (root / "pyvenv.cfg").write_text(
        f"home = {base.parent}\ninclude-system-site-packages = false\nversion = 3.12.13\n"
        f"executable = {base}\ncommand = exact copies setup\n"
    )
    (root / "lib").mkdir()
    (root / "lib/dependency.py").write_text("checked dependency")


@pytest.fixture
def checked_environment(tmp_path):
    source, base = _source(tmp_path)
    _make_copy(source / ENVIRONMENT_PATH, base)
    receipt = source / RECEIPT_PATH
    receipt.write_text(json.dumps(_snapshot(source)))
    return source, base


def test_inspection_is_read_only_and_rejects_missing_setup(tmp_path, monkeypatch):
    source, _base = _source(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("inspection must never provision"))
    with pytest.raises(CodexExecPythonEnvironmentError, match="explicit provisioning"):
        inspect_checked_python_environment(source)
    assert not (source / ".local").exists()


def test_readiness_rejects_missing_environment_before_authentication_probe(tmp_path, monkeypatch):
    from plotloom.codex_exec_auth import check_codex_exec_readiness

    source, base = _source(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("missing setup must not reach auth"))
    assert check_codex_exec_readiness(base, source_root=source).state == "unavailable"


def test_readiness_rejects_missing_validator_tools_without_any_child(checked_environment, monkeypatch):
    import plotloom.codex_exec_resources as resources
    from plotloom.codex_exec_auth import check_codex_exec_readiness

    source, base = checked_environment
    monkeypatch.setattr(resources.shutil, "which", lambda _name: None)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("missing tools must not launch"))
    assert check_codex_exec_readiness(base, source_root=source).state == "unavailable"


@pytest.mark.parametrize("target", ["lock", "project", "dependency", "configuration", "interpreter", "runtime", "receipt"])
def test_environment_identity_rejects_each_owned_drift(checked_environment, target):
    source, base = checked_environment
    paths = {
        "lock": source / "uv.lock", "project": source / "pyproject.toml",
        "dependency": source / ENVIRONMENT_PATH / "lib/dependency.py",
        "configuration": source / ENVIRONMENT_PATH / "pyvenv.cfg",
        "interpreter": source / ENVIRONMENT_PATH / "bin/python",
        "runtime": base, "receipt": source / RECEIPT_PATH,
    }
    before = inspect_checked_python_environment(source)
    assert before.root == source / ENVIRONMENT_PATH
    paths[target].write_bytes(paths[target].read_bytes() + b"changed")
    with pytest.raises(CodexExecPythonEnvironmentError):
        inspect_checked_python_environment(source)


@pytest.mark.parametrize("target", ["interpreter", "dependency"])
def test_environment_rejects_aliases_even_when_their_target_bytes_match(checked_environment, target):
    source, base = checked_environment
    path = source / ENVIRONMENT_PATH / ("bin/python" if target == "interpreter" else "lib/dependency.py")
    outside = base if target == "interpreter" else base.parent / "dependency.py"
    if target != "interpreter":
        outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(CodexExecPythonEnvironmentError):
        inspect_checked_python_environment(source)


def test_changed_configuration_cannot_redirect_the_inspector_to_an_unbound_runtime(
    checked_environment, monkeypatch,
):
    import plotloom.codex_exec_python_environment as environment_module

    source, _base = checked_environment
    cfg = source / ENVIRONMENT_PATH / "pyvenv.cfg"
    cfg.write_text(cfg.read_text().replace("executable = ", "executable = /unbound/"))
    monkeypatch.setattr(environment_module, "stable_file_hash", lambda *_a: pytest.fail("unbound path must not be read"))
    with pytest.raises(CodexExecPythonEnvironmentError):
        inspect_checked_python_environment(source)


def test_source_parent_rejects_siblings_and_nested_symlink_escape(tmp_path):
    source, base = _source(tmp_path)
    parent, original_hash = python_source_identity(source)
    assert parent == source / "src"
    (parent / "unrelated").mkdir()
    with pytest.raises(CodexExecRuntimeTreeError, match="siblings"):
        python_source_identity(source)
    (parent / "unrelated").rmdir()
    (parent / "plotloom/escaped.py").symlink_to(base)
    with pytest.raises(CodexExecRuntimeTreeError, match="symlink"):
        python_source_identity(source)
    (parent / "plotloom/escaped.py").unlink()
    os.link(base, parent / "plotloom/hardlink.py")
    with pytest.raises(CodexExecRuntimeTreeError, match="distinct regular"):
        python_source_identity(source)
    (parent / "plotloom/hardlink.py").unlink()
    assert python_source_identity(source)[1] == original_hash


def test_generated_bytecode_is_excluded_but_cannot_hide_other_readable_content(tmp_path):
    source, _base = _source(tmp_path)
    original_hash = python_source_identity(source)[1]
    cache = source / "src/plotloom/__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-312.pyc").write_bytes(b"unused generated bytes")
    assert python_source_identity(source)[1] == original_hash
    (cache / "unexpected.txt").write_text("unowned")
    with pytest.raises(CodexExecRuntimeTreeError, match="unexpected content"):
        python_source_identity(source)


def test_versioned_runtime_allows_only_confined_internal_aliases(checked_environment):
    source, base = checked_environment
    runtime = base.parent.parent
    (base.parent / "python3").symlink_to("python3.12")
    assert runtime_tree_hash(runtime, internal_links=True)
    (base.parent / "escaped").symlink_to(source / "uv.lock")
    with pytest.raises(CodexExecRuntimeTreeError, match="symlink escape"):
        runtime_tree_hash(runtime, internal_links=True)


def test_explicit_provisioning_preserves_copy_and_requests_the_physical_base(tmp_path, monkeypatch):
    source, base = _source(tmp_path)
    uv = tmp_path.resolve() / "uv"
    uv.write_bytes(b"pinned uv")
    uv.chmod(0o700)
    commands = []
    monkeypatch.setenv("UV_PYTHON", "/untrusted/alias")
    monkeypatch.setenv("UV_NO_MANAGED_PYTHON", "1")
    monkeypatch.setenv("PYTHONPATH", "/untrusted/site-packages")

    def setup(argv, **options):
        commands.append((argv, options))
        assert "UV_PYTHON" not in options["env"] and "PYTHONPATH" not in options["env"]
        assert "UV_NO_MANAGED_PYTHON" not in options["env"]
        if len(commands) == 1:
            assert argv[:6] == [str(base), "-I", "-B", "-m", "venv", "--copies"]
            _make_copy(source / ENVIRONMENT_PATH, base)
        else:
            assert argv[argv.index("--python") + 1] == str(base)
            assert "--no-managed-python" not in argv
            assert {"--locked", "--offline", "--no-install-project", "--link-mode"} <= set(argv)
            assert options["env"]["UV_PROJECT_ENVIRONMENT"] == str(source / ENVIRONMENT_PATH)
        return subprocess.CompletedProcess(argv, 0, b"setup result", b"")

    monkeypatch.setattr(subprocess, "run", setup)
    installed = provision_checked_python_environment(source, interpreter=base, uv=uv)
    assert installed == inspect_checked_python_environment(source)
    assert len(commands) == 2
    with pytest.raises(CodexExecPythonEnvironmentError, match="already exists"):
        provision_checked_python_environment(source, interpreter=base, uv=uv)
    assert len(commands) == 2
