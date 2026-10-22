"""Process-local reuse keeps Node rules authoritative and project checks live."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from plotloom import style_contract_cache
from plotloom.art_style import ADAPTER, freeze_art_style, validate_art_style
from plotloom.art_style import STYLE_RULE_DEPENDENCIES as ART_RULES
from plotloom.cast_style import (
    STYLE_OWNER,
    cast_style_current,
    freeze_cast_style,
    validate_cast_style,
)
from plotloom.cast_style import (
    STYLE_RULE_DEPENDENCIES as CAST_RULES,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAST_UPSTREAM = (
    PROJECT_ROOT
    / "third_party"
    / "shuohao-skills"
    / "skills"
    / "novel-characters"
    / "scripts"
    / "novel-characters.mjs"
)
ART_UPSTREAM = (
    PROJECT_ROOT / "third_party" / "shuohao-skills" / "skills" / "novel-art" / "scripts" / "novel-art.mjs"
)
ART_GATE_SUMMARY = ART_UPSTREAM.with_name("gate-summary.mjs")


def _clear_cache() -> None:
    with style_contract_cache._LOCK:
        style_contract_cache._CACHE.clear()
        style_contract_cache._LAST_EXECUTION_CONTEXT = None


def _derive(
    *,
    owner: str,
    script: Path = STYLE_OWNER,
    dependencies: tuple[Path, ...] = CAST_RULES,
    style: str = "realistic",
    direction: str | None = "cache contract test",
):
    return style_contract_cache.derive_style_contract(
        owner=owner,
        script=script,
        dependencies=dependencies,
        style=style,
        direction=direction,
        error_context="character render validation failed",
    )


def _copied_cast_rules(tmp_path: Path) -> tuple[Path, Path]:
    script = tmp_path / "scripts" / "cast-style.mjs"
    upstream = tmp_path / "third_party" / "shuohao-skills" / "skills" / "novel-characters" / "scripts" / "novel-characters.mjs"
    script.parent.mkdir(parents=True)
    upstream.parent.mkdir(parents=True)
    script.write_bytes(STYLE_OWNER.read_bytes())
    upstream.write_bytes(CAST_UPSTREAM.read_bytes())
    return script, upstream


def _edit_rule_same_size_and_timestamp(path: Path) -> None:
    before = path.stat()
    original = path.read_bytes()
    old = b"visible brush texture"
    new = b"visible brush pattern"
    assert len(old) == len(new)
    assert original.count(old) == 1
    path.write_bytes(original.replace(old, new, 1))
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = path.stat()
    assert after.st_size == before.st_size
    assert after.st_mtime_ns == before.st_mtime_ns


def _local_imports(path: Path) -> set[Path]:
    source = path.read_text(encoding="utf-8")
    assert not re.search(r"\bimport\s*\(", source), f"dynamic import in cached rule owner: {path}"
    imports = re.findall(r"(?ms)^\s*(?:import|export)\b.*?;", source)
    dependencies = set()
    for statement in imports:
        match = re.search(r"\bfrom\s*['\"]([^'\"]+)['\"]|^\s*import\s*['\"]([^'\"]+)['\"]", statement)
        if not match:
            continue
        specifier = next(value for value in match.groups() if value is not None)
        if specifier.startswith("node:"):
            continue
        assert specifier.startswith(("./", "../")), f"unbounded Node dependency {specifier!r} in {path}"
        dependencies.add((path.parent / specifier).resolve())
    return dependencies


def _dependency_closure(entrypoint: Path) -> set[Path]:
    seen = {entrypoint.resolve()}
    pending = [entrypoint.resolve()]
    while pending:
        owner = pending.pop()
        for dependency in _local_imports(owner) - seen:
            seen.add(dependency)
            pending.append(dependency)
    return seen


def test_fingerprints_cover_complete_local_rule_import_closures():
    assert _dependency_closure(STYLE_OWNER) == {STYLE_OWNER.resolve(), CAST_UPSTREAM.resolve()}
    assert _dependency_closure(ADAPTER) == {
        ADAPTER.resolve(),
        ART_UPSTREAM.resolve(),
        ART_GATE_SUMMARY.resolve(),
    }
    assert set(CAST_RULES) == {CAST_UPSTREAM}
    assert set(ART_RULES) == {ART_UPSTREAM, ART_GATE_SUMMARY}


def test_cache_hit_returns_independent_json_and_currentness_stays_a_comparison():
    _clear_cache()
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        first = freeze_cast_style("ghibli", "cache-isolation direction 20261010")
        first["preset"]["tags"].append("caller mutation")
        second = freeze_cast_style("ghibli", "cache-isolation direction 20261010")
        assert run.call_count == 1
    assert "caller mutation" not in second["preset"]["tags"]
    assert cast_style_current(second, "cache-isolation direction 20261010")
    assert not cast_style_current(second, "changed cache-isolation direction")


def test_owner_style_and_none_versus_empty_direction_are_distinct_keys():
    _clear_cache()
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        _derive(owner="cast-owner-key", direction=None)
        _derive(owner="cast-owner-key", direction=None)
        _derive(owner="cast-owner-key", direction="")
        _derive(owner="other-owner-key", direction=None)
        assert run.call_count == 3


def test_upstream_rule_content_invalidates_even_with_same_size_and_timestamp(tmp_path):
    _clear_cache()
    script, upstream = _copied_cast_rules(tmp_path)
    dependencies = (upstream,)
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        before = _derive(owner="copied-rule", script=script, dependencies=dependencies, direction=None)
        _edit_rule_same_size_and_timestamp(upstream)
        after = _derive(owner="copied-rule", script=script, dependencies=dependencies, direction=None)
        assert run.call_count == 2
    assert before["preset"]["render"] != after["preset"]["render"]


def test_rule_change_during_derivation_is_not_cached(tmp_path):
    _clear_cache()
    script, upstream = _copied_cast_rules(tmp_path)
    dependencies = (upstream,)
    real_run = subprocess.run
    calls = 0

    def run_then_edit(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = real_run(*args, **kwargs)
        if calls == 1:
            _edit_rule_same_size_and_timestamp(upstream)
        return result

    with patch.object(style_contract_cache.subprocess, "run", side_effect=run_then_edit):
        first = _derive(owner="mid-derivation-edit", script=script, dependencies=dependencies, direction=None)
        second = _derive(owner="mid-derivation-edit", script=script, dependencies=dependencies, direction=None)
    assert calls == 2
    assert first["preset"]["render"] != second["preset"]["render"]


def test_unavailable_or_changed_node_path_and_identity_never_return_a_hit(tmp_path, monkeypatch):
    _clear_cache()
    real_node = Path(shutil.which("node")).resolve()
    missing = tmp_path / "missing-bin"
    first_bin, second_bin = tmp_path / "first-bin", tmp_path / "second-bin"
    missing.mkdir()
    first_bin.mkdir()
    second_bin.mkdir()
    (first_bin / "node").symlink_to(real_node)
    (second_bin / "node").symlink_to(real_node)
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        _derive(owner="node-identity", direction="node identity test")
        monkeypatch.setenv("PATH", str(missing))
        with pytest.raises(FileNotFoundError):
            _derive(owner="node-identity", direction="node identity test")
        monkeypatch.setenv("PATH", str(first_bin))
        _derive(owner="node-identity", direction="node identity test")
        monkeypatch.setenv("PATH", str(second_bin))
        _derive(owner="node-identity", direction="node identity test")
        monkeypatch.setenv("PATH", str(first_bin))
        _derive(owner="node-identity", direction="node identity test")

        replacement = first_bin / "node.replacement"
        replacement.write_text(f"#!/bin/sh\nexec {shlex.quote(str(real_node))} \"$@\"\n", encoding="utf-8")
        replacement.chmod(0o755)
        os.replace(replacement, first_bin / "node")
        _derive(owner="node-identity", direction="node identity test")
        assert run.call_count == 6


def test_node_options_failure_after_warmup_fails_closed(monkeypatch):
    _clear_cache()
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        freeze_cast_style("realistic", "node-options-failure 20261010")
        monkeypatch.setenv("NODE_OPTIONS", "--plotloom-invalid-option")
        with pytest.raises(ValueError, match="character render validation failed") as error:
            freeze_cast_style("realistic", "node-options-failure 20261010")
        assert "--plotloom-invalid-option" in str(error.value)
        assert run.call_count == 2


def test_node_and_json_failures_are_not_cached_or_replaced_by_last_good():
    _clear_cache()
    real_run = subprocess.run
    calls = 0

    def fail_json_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return subprocess.CompletedProcess(args[0], 0, "not-json", "")
        return real_run(*args, **kwargs)

    with patch.object(style_contract_cache.subprocess, "run", side_effect=fail_json_once):
        with pytest.raises(json.JSONDecodeError):
            freeze_cast_style("ghibli", "json-failure 20261010")
        valid = freeze_cast_style("ghibli", "json-failure 20261010")
    assert valid["style"] == "ghibli"
    assert calls == 2


def test_real_cast_and_art_validators_still_refuse_stale_contracts():
    _clear_cache()
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        cast_contract = freeze_cast_style("realistic", "real-validator-cast 20261010")
        stale_cast = json.loads(json.dumps(cast_contract))
        stale_cast["preset"]["render"] = "tampered"
        with pytest.raises(ValueError, match="stale"):
            validate_cast_style({"style": "realistic", "characters": []}, stale_cast)

        art_contract = freeze_art_style("realistic", "real-validator-art 20261010")
        stale_art = json.loads(json.dumps(art_contract))
        stale_art["preset"]["render"] = "tampered"
        with pytest.raises(ValueError, match="stale"):
            validate_art_style({}, {"characters": []}, stale_art)
        assert run.call_count == 4


def test_concurrent_derivation_and_lru_eviction_preserve_results():
    _clear_cache()
    with patch.object(style_contract_cache.subprocess, "run", wraps=subprocess.run) as run:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: _derive(owner="concurrent", direction="same"), range(8)))
        assert all(result == results[0] for result in results)
        assert run.call_count == 1

        first_direction = "lru-0"
        first = _derive(owner="bounded-lru", direction=first_direction)
        for index in range(1, 65):
            _derive(owner="bounded-lru", direction=f"lru-{index}")
        assert len(style_contract_cache._CACHE) == style_contract_cache._MAX_ENTRIES
        calls_before_evicted_lookup = run.call_count
        assert _derive(owner="bounded-lru", direction=first_direction) == first
        assert run.call_count == calls_before_evicted_lookup + 1
