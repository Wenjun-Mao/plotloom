"""Bounded reuse for successful, deterministic Cast and Art rule derivation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import threading
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MAX_ENTRIES = 64
_LOCK = threading.RLock()


@dataclass(frozen=True)
class _NodeIdentity:
    path: str
    device: int
    inode: int
    size: int
    mode: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class _CacheKey:
    owner: str
    script: str
    style: str
    direction_json: str
    dependencies: tuple[tuple[str, int, int, int, int, int, int, str], ...]
    node: _NodeIdentity
    path: str | None
    node_options_digest: str | None


_CACHE: OrderedDict[_CacheKey, str] = OrderedDict()
_LAST_EXECUTION_CONTEXT: tuple[str | None, str | None, _NodeIdentity | None] | None = None


def _node_identity(path: str | None) -> _NodeIdentity | None:
    if path is None:
        return None
    try:
        executable = Path(path).resolve(strict=True)
        metadata = executable.stat()
    except (OSError, RuntimeError):
        return None
    if not stat.S_ISREG(metadata.st_mode) or not os.access(executable, os.X_OK):
        return None
    return _NodeIdentity(
        path=str(executable),
        device=metadata.st_dev,
        inode=metadata.st_ino,
        size=metadata.st_size,
        mode=metadata.st_mode,
        modified_ns=metadata.st_mtime_ns,
        changed_ns=metadata.st_ctime_ns,
    )


def _file_fingerprint(path: Path) -> tuple[str, int, int, int, int, int, int, str] | None:
    try:
        resolved = path.resolve(strict=True)
        before = resolved.stat()
        content = resolved.read_bytes()
        after = resolved.stat()
    except (OSError, RuntimeError):
        return None
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mode,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mode,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if before_identity != after_identity:
        return None
    return (str(resolved), *after_identity, hashlib.sha256(content).hexdigest())


def _cache_key(
    owner: str,
    script: Path,
    dependencies: Sequence[Path],
    style: str,
    direction_json: str,
    path_value: str | None,
    node_options: str | None,
) -> _CacheKey | None:
    if node_options:
        return None
    executable = _node_identity(shutil.which("node", path=path_value))
    if executable is None:
        return None
    try:
        script_path = script.resolve(strict=True)
        dependency_paths = {script_path, *(item.resolve() for item in dependencies)}
    except (OSError, RuntimeError):
        return None
    fingerprints: list[tuple[str, int, int, int, int, int, int, str]] = []
    for dependency in sorted(dependency_paths, key=str):
        fingerprint = _file_fingerprint(dependency)
        if fingerprint is None:
            return None
        fingerprints.append(fingerprint)
    options_digest = (
        hashlib.sha256(node_options.encode("utf-8")).hexdigest()
        if node_options is not None
        else None
    )
    return _CacheKey(
        owner=owner,
        script=str(script_path),
        style=style,
        direction_json=direction_json,
        dependencies=tuple(fingerprints),
        node=executable,
        path=path_value,
        node_options_digest=options_digest,
    )


def _execution_context(
    path_value: str | None, node_options: str | None
) -> tuple[str | None, str | None, _NodeIdentity | None]:
    options_digest = (
        hashlib.sha256(node_options.encode("utf-8")).hexdigest()
        if node_options is not None
        else None
    )
    executable = _node_identity(shutil.which("node", path=path_value))
    return path_value, options_digest, executable


def _observe_execution_context(
    context: tuple[str | None, str | None, _NodeIdentity | None],
) -> None:
    global _LAST_EXECUTION_CONTEXT
    if _LAST_EXECUTION_CONTEXT != context:
        _CACHE.clear()
        _LAST_EXECUTION_CONTEXT = context


def _derive_json(
    script: Path, style: str, direction_json: str, error_context: str
) -> tuple[str, Any]:
    result = subprocess.run(
        ["node", str(script), "contract", "--style", style, "--author-direction", direction_json],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"{error_context}: {(result.stderr or result.stdout).strip()}")
    return result.stdout, json.loads(result.stdout)


def derive_style_contract(
    *,
    owner: str,
    script: Path,
    dependencies: Sequence[Path],
    style: str,
    direction: str | None,
    error_context: str,
) -> Any:
    """Derive a current contract, reusing only a fully fingerprinted Node result."""

    direction_json = json.dumps(direction)
    with _LOCK:
        path_value = os.environ.get("PATH")
        node_options = os.environ.get("NODE_OPTIONS")
        context = _execution_context(path_value, node_options)
        _observe_execution_context(context)
        key = _cache_key(
            owner, script, dependencies, style, direction_json, path_value, node_options
        )
        if key is not None and key in _CACHE:
            cached_json = _CACHE.pop(key)
            _CACHE[key] = cached_json
            return json.loads(cached_json)

        output, contract = _derive_json(script, style, direction_json, error_context)
        if key is not None:
            post_context = _execution_context(os.environ.get("PATH"), os.environ.get("NODE_OPTIONS"))
            _observe_execution_context(post_context)
            post_key = _cache_key(
                owner,
                script,
                dependencies,
                style,
                direction_json,
                os.environ.get("PATH"),
                os.environ.get("NODE_OPTIONS"),
            )
            if post_key == key:
                _CACHE[key] = output
                _CACHE.move_to_end(key)
                while len(_CACHE) > _MAX_ENTRIES:
                    _CACHE.popitem(last=False)
        return contract
