"""Validate advisory file timings and build deterministic whole-file plans."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class TimingManifestError(ValueError):
    """A timing manifest is malformed or unsafe to use."""


@dataclass(frozen=True)
class Schedule:
    assignments: tuple[tuple[str, ...], ...]
    basis: str
    fallback_reason: str | None = None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise TimingManifestError(f"duplicate timing manifest key: {key}")
        value[key] = item
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def native_case_fingerprint(cases: Sequence[str]) -> str:
    return _sha256(("\n".join(sorted(cases)) + "\n").encode())


def input_fingerprint(root: Path) -> str:
    paths = [root / "pyproject.toml", root / "uv.lock", root / ".python-version"]
    for directory in (
        "src/plotloom",
        "scripts",
        "tests",
        "frontend/e2e/fixtures/f5a",
    ):
        paths.extend((root / directory).rglob("*"))
    digest = hashlib.sha256()
    for path in sorted(
        {
            path
            for path in paths
            if path.is_file()
            and path.name != "python_suite_timings.json"
            and not any(part in {".git", "__pycache__", "node_modules"} for part in path.parts)
        }
    ):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    submodule = root / "third_party/shuohao-skills"
    if submodule.is_dir():
        result = subprocess.run(
            ["git", "-C", str(submodule), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        digest.update(
            b"third_party/shuohao-skills-head\0"
            + (result.stdout.strip() if result.returncode == 0 else "unresolved").encode()
        )
        for path in sorted(submodule.rglob("*")):
            if path.is_file() and ".git" not in path.parts:
                digest.update(path.relative_to(root).as_posix().encode() + b"\0")
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    else:
        digest.update(b"third_party/shuohao-skills-head\0uninitialized")
    return digest.hexdigest()


def host_fingerprint() -> str:
    value = "|".join(
        (
            sys.platform,
            platform.node(),
            platform.machine(),
            platform.processor(),
            platform.platform(),
            platform.python_implementation(),
            ".".join(map(str, sys.version_info[:3])),
        )
    )
    return _sha256(value.encode())


def _case_counts(cases: Sequence[str]) -> Counter[str]:
    return Counter(case.split("::", 1)[0] for case in cases)


def _count_partition(counts: Mapping[str, int], worker_count: int):
    groups: list[list[str]] = [[] for _ in range(worker_count)]
    totals = [0] * worker_count
    for path, count in sorted(counts.items(), key=lambda row: (-row[1], row[0])):
        index = min(range(worker_count), key=totals.__getitem__)
        groups[index].append(path)
        totals[index] += count
    return tuple(tuple(sorted(group)) for group in groups)


def _duration_partition(weights: Mapping[str, float], worker_count: int):
    groups: list[list[str]] = [[] for _ in range(worker_count)]
    totals = [0.0] * worker_count
    for path, seconds in sorted(weights.items(), key=lambda row: (-row[1], row[0])):
        index = min(range(worker_count), key=totals.__getitem__)
        groups[index].append(path)
        totals[index] += seconds
    return tuple(tuple(sorted(group)) for group in groups)


def _safe_test_path(path: object) -> bool:
    if not isinstance(path, str) or not path.startswith("tests/") or not path.endswith(".py"):
        return False
    candidate = Path(path)
    return (
        not candidate.is_absolute()
        and candidate.as_posix() == path
        and ".." not in candidate.parts
    )


def schedule_from_timing_text(
    text: str | None,
    *,
    cases: Sequence[str],
    root: Path,
    worker_count: int = 2,
) -> Schedule:
    """Use timings only for a complete, current native file set; otherwise count."""
    if worker_count < 1 or not cases or len(cases) != len(set(cases)):
        raise TimingManifestError("worker count and native case collection must be valid")
    counts = _case_counts(cases)
    if worker_count > len(counts):
        raise TimingManifestError("native pytest file set is too small for all workers")
    if text is None:
        return Schedule(
            _count_partition(counts, worker_count), "case-count", "timing-manifest-missing"
        )
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, TimingManifestError) as error:
        raise TimingManifestError(f"invalid timing manifest JSON: {error}") from error
    required = {
        "schema_version",
        "native_case_ids_sha256",
        "input_fingerprint",
        "host_fingerprint",
        "files",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise TimingManifestError("timing manifest fields are incomplete or unexpected")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != SCHEMA_VERSION
    ):
        raise TimingManifestError("unsupported timing manifest schema")
    for key in (
        "native_case_ids_sha256",
        "input_fingerprint",
        "host_fingerprint",
    ):
        if not isinstance(value[key], str) or re.fullmatch(r"[a-f0-9]{64}", value[key]) is None:
            raise TimingManifestError(f"malformed timing manifest fingerprint: {key}")
    rows = value["files"]
    if not isinstance(rows, list):
        raise TimingManifestError("timing manifest files must be a list")
    weights: dict[str, float] = {}
    row_counts: dict[str, int] = {}
    for row in rows:
        fields = {
            "path",
            "case_count",
            "setup_seconds",
            "call_seconds",
            "teardown_seconds",
        }
        if not isinstance(row, dict) or set(row) != fields:
            raise TimingManifestError("malformed per-file timing row")
        path = row["path"]
        if not _safe_test_path(path) or path in weights:
            raise TimingManifestError(f"unsafe or duplicate timing file path: {path}")
        count = row["case_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise TimingManifestError(f"invalid case count for timing file: {path}")
        phases = []
        for key in ("setup_seconds", "call_seconds", "teardown_seconds"):
            seconds = row[key]
            if isinstance(seconds, bool) or not isinstance(seconds, (float, int)):
                raise TimingManifestError(f"invalid {key} for timing file: {path}")
            try:
                seconds = float(seconds)
            except OverflowError as error:
                raise TimingManifestError(
                    f"out-of-range {key} for timing file: {path}"
                ) from error
            if not math.isfinite(seconds) or seconds < 0:
                raise TimingManifestError(f"nonfinite or negative {key} for timing file: {path}")
            phases.append(seconds)
        total_seconds = sum(phases)
        if not math.isfinite(total_seconds):
            raise TimingManifestError(f"nonfinite aggregate timing for file: {path}")
        if total_seconds <= 0:
            raise TimingManifestError(f"empty phase timing for file: {path}")
        weights[path] = total_seconds
        row_counts[path] = count

    if value["native_case_ids_sha256"] != native_case_fingerprint(cases):
        reason = "native-case-inventory-changed"
    elif value["input_fingerprint"] != input_fingerprint(root):
        reason = "executable-inputs-changed"
    elif value["host_fingerprint"] != host_fingerprint():
        reason = "host-or-python-changed"
    elif set(weights) != set(counts):
        reason = "timing-file-coverage-changed"
    elif row_counts != dict(counts):
        reason = "timing-case-counts-changed"
    else:
        reason = None
    if reason:
        return Schedule(_count_partition(counts, worker_count), "case-count", reason)
    return Schedule(_duration_partition(weights, worker_count), "duration")
