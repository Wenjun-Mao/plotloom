"""Fail closed when native test discovery escapes its reviewed module owners."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
MANIFEST = Path(__file__).with_name("module-ownership.json")
SUITES = ("pytest", "vitest", "playwright")
FILTER_ENVIRONMENT = (
    "PYTEST_ADDOPTS",
    "BROWSER_GREP",
    "BROWSER_SHARD",
    "VITEST_FILTER",
    "VITEST_GREP",
    "PLAYWRIGHT_GREP",
    "PLAYWRIGHT_SHARD",
    "PWTEST_GREP",
    "PWTEST_SHARD_INDEX",
    "PWTEST_SHARD_TOTAL",
)
TEST_ROOTS = {
    "pytest": ROOT / "tests",
    "vitest": FRONTEND / "tests",
    "playwright": FRONTEND / "e2e",
}
TEST_SUFFIXES = {
    "pytest": (".py",),
    "vitest": (".test.ts",),
    "playwright": (
        ".spec.ts",
        ".spec.tsx",
        ".spec.js",
        ".spec.jsx",
        ".test.ts",
        ".test.tsx",
        ".test.js",
        ".test.jsx",
    ),
}
PLAYWRIGHT_CASE = re.compile(r"^\s+(.+?):(\d+):(\d+)\s+›\s+(.+)$")


class OwnershipError(ValueError):
    """The ownership map and native test inventory do not agree."""


def _repo_file(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise OwnershipError(f"{label} must be a repository-relative file path")
    candidate = root / value
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError) as error:
        raise OwnershipError(f"stale or unsafe {label}: {value}") from error
    if not resolved.is_file():
        raise OwnershipError(f"{label} is not a file: {value}")
    if resolved.relative_to(root.resolve()).as_posix() != value:
        raise OwnershipError(
            f"{label} must use its normalized repository path: {value}"
        )
    return resolved


def validate_manifest_data(manifest: Any, root: Path = ROOT) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise OwnershipError("unsupported module ownership manifest schema")
    modules = manifest.get("modules")
    if not isinstance(modules, dict) or not modules:
        raise OwnershipError("module ownership must define at least one module")

    module_names = set(modules)
    selectors_by_suite: dict[str, dict[str, str]] = {suite: {} for suite in SUITES}
    for module_name, module in modules.items():
        if not isinstance(module_name, str) or not module_name.strip():
            raise OwnershipError("module names must be nonempty strings")
        description = module.get("description") if isinstance(module, dict) else None
        if not isinstance(description, str) or not description.strip():
            raise OwnershipError(f"module {module_name} needs a description")
        selectors = module.get("selectors")
        if not isinstance(selectors, dict) or set(selectors) != set(SUITES):
            raise OwnershipError(f"module {module_name} must declare all native suites")
        if not any(selectors[suite] for suite in SUITES):
            raise OwnershipError(f"empty test module: {module_name}")

        for suite in SUITES:
            values = selectors[suite]
            if not isinstance(values, list):
                raise OwnershipError(f"{module_name}.{suite} selectors must be a list")
            for value in values:
                path = _repo_file(root, value, f"{module_name}.{suite} selector")
                try:
                    path.relative_to(
                        (root / TEST_ROOTS[suite].relative_to(ROOT)).resolve()
                    )
                except ValueError as error:
                    raise OwnershipError(
                        f"{module_name}.{suite} selector is outside its test root: {value}"
                    ) from error
                if not path.name.endswith(TEST_SUFFIXES[suite]):
                    raise OwnershipError(f"unknown {suite} selector extension: {value}")
                previous = selectors_by_suite[suite].get(value)
                if previous is not None:
                    raise OwnershipError(
                        f"duplicate {suite} selector {value}: {previous}, {module_name}"
                    )
                selectors_by_suite[suite][value] = module_name

    dependencies = manifest.get("support_dependencies")
    if not isinstance(dependencies, list):
        raise OwnershipError("support_dependencies must be a list")
    seen_dependencies: set[tuple[str, str]] = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise OwnershipError("support dependency entries must be objects")
        suite = dependency.get("suite")
        path_value = dependency.get("path")
        consumers = dependency.get("consumers")
        if suite not in SUITES:
            raise OwnershipError(f"unknown support dependency suite: {suite}")
        _repo_file(root, path_value, f"{suite} support dependency")
        if (
            not isinstance(consumers, list)
            or not consumers
            or not all(isinstance(consumer, str) for consumer in consumers)
        ):
            raise OwnershipError(f"support dependency {path_value} needs consumers")
        if len(consumers) != len(set(consumers)):
            raise OwnershipError(
                f"duplicate consumers for support dependency {path_value}"
            )
        for consumer in consumers:
            if consumer not in module_names:
                raise OwnershipError(
                    f"unknown support dependency consumer {consumer}: {path_value}"
                )
            if not modules[consumer]["selectors"][suite]:
                raise OwnershipError(
                    f"support dependency consumer has no {suite} cases: {consumer}"
                )
        key = (suite, path_value)
        if key in seen_dependencies:
            raise OwnershipError(f"duplicate support dependency: {suite} {path_value}")
        seen_dependencies.add(key)
    return selectors_by_suite


def parse_pytest(stdout: str) -> list[str]:
    cases = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("tests/"):
            if "::" not in line:
                raise OwnershipError(f"unrecognized pytest collection row: {line}")
            cases.append(line)
    if not cases:
        raise OwnershipError("pytest collection returned no case IDs")
    return cases


def parse_vitest(stdout: str, frontend: Path = FRONTEND) -> list[str]:
    try:
        rows = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise OwnershipError("Vitest list output is not valid JSON") from error
    if not isinstance(rows, list) or not rows:
        raise OwnershipError("Vitest list output must be a nonempty case array")
    normalized_rows = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise OwnershipError("Vitest list row is missing its native test name")
        file_value = row.get("file")
        if not isinstance(file_value, str):
            raise OwnershipError("Vitest list row is missing its source file")
        try:
            file_path = Path(file_value).resolve(strict=True)
            relative = file_path.relative_to(frontend.resolve(strict=True)).as_posix()
        except (OSError, RuntimeError, ValueError) as error:
            raise OwnershipError(
                f"Vitest returned a source outside frontend: {file_value}"
            ) from error
        if not row["name"]:
            raise OwnershipError(f"Vitest returned an empty case name: {relative}")
        normalized_rows.append((relative, row["name"]))
    totals = Counter(normalized_rows)
    seen: Counter[tuple[str, str]] = Counter()
    cases = []
    for relative, name in normalized_rows:
        key = (relative, name)
        seen[key] += 1
        case_id = f"{relative}::{name}"
        if totals[key] > 1:
            case_id += f" [collection occurrence {seen[key]} of {totals[key]}]"
        cases.append(case_id)
    return cases


def parse_playwright(stdout: str) -> list[str]:
    cases = []
    for raw_line in stdout.splitlines():
        if raw_line.lstrip().startswith("Total:"):
            continue
        if not raw_line.startswith("  "):
            continue
        match = PLAYWRIGHT_CASE.match(raw_line)
        if match:
            path, line, column, title = match.groups()
            cases.append(f"{path}:{line}:{column} › {title}")
        elif ".spec." in raw_line or ".test." in raw_line:
            raise OwnershipError(
                f"unrecognized Playwright collection row: {raw_line.strip()}"
            )
    if not cases:
        raise OwnershipError("Playwright list output returned no case IDs")
    return cases


def _case_file(suite: str, case_id: str) -> str:
    if suite in ("pytest", "vitest"):
        path, separator, _ = case_id.partition("::")
        if not separator:
            raise OwnershipError(f"unrecognized {suite} case ID: {case_id}")
        return f"frontend/{path}" if suite == "vitest" else path
    match = re.match(r"^(.+?):\d+:\d+ › .+$", case_id)
    if match is None:
        raise OwnershipError(f"unrecognized Playwright case ID: {case_id}")
    return f"frontend/e2e/{match.group(1)}"


def _source_test_files(suite: str, root: Path = ROOT) -> set[str]:
    suite_root = root / TEST_ROOTS[suite].relative_to(ROOT)
    paths = set()
    for path in suite_root.rglob("*"):
        if not path.is_file():
            continue
        if suite == "pytest":
            is_test = path.name.startswith("test_") and path.suffix == ".py"
        else:
            is_test = any(path.name.endswith(suffix) for suffix in TEST_SUFFIXES[suite])
        if is_test:
            paths.add(path.relative_to(root).as_posix())
    return paths


def validate_case_ownership(
    manifest: dict[str, Any],
    selectors_by_suite: dict[str, dict[str, str]],
    native_cases: dict[str, list[str]],
    root: Path = ROOT,
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for suite in SUITES:
        cases = native_cases[suite]
        if len(cases) != len(set(cases)):
            raise OwnershipError(
                f"native {suite} collection contains duplicate case IDs"
            )
        owners = selectors_by_suite[suite]
        native_files = {_case_file(suite, case_id) for case_id in cases}
        mapped_files = set(owners)
        if native_files != mapped_files:
            missing = sorted(native_files - mapped_files)
            stale = sorted(mapped_files - native_files)
            raise OwnershipError(
                f"{suite} file ownership mismatch; unowned={missing[:8]}, no_cases={stale[:8]}"
            )
        source_files = _source_test_files(suite, root)
        if source_files != native_files:
            empty = sorted(source_files - native_files)
            outside = sorted(native_files - source_files)
            raise OwnershipError(
                f"{suite} source discovery mismatch; no_native_cases={empty[:8]}, unexpected={outside[:8]}"
            )

        module_cases: dict[str, list[str]] = defaultdict(list)
        for case_id in cases:
            module_cases[owners[_case_file(suite, case_id)]].append(case_id)
        module_union = [
            case_id
            for module_name in manifest["modules"]
            for case_id in module_cases.get(module_name, [])
        ]
        if len(module_union) != len(set(module_union)) or set(module_union) != set(
            cases
        ):
            raise OwnershipError(
                f"{suite} module union is not an exact native case cover"
            )
        summary[suite] = {
            "case_count": len(cases),
            "file_count": len(native_files),
            "module_cases": {
                name: len(module_cases.get(name, [])) for name in manifest["modules"]
            },
            "sha256": hashlib.sha256(
                ("\n".join(sorted(cases)) + "\n").encode("utf-8")
            ).hexdigest(),
        }
    return summary


def _run_collector(command: list[str], cwd: Path, environment: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise OwnershipError(
            f"native collector failed with exit code {result.returncode}: {' '.join(command)}\n{detail}"
        )
    return result.stdout


def collect_native_cases() -> dict[str, list[str]]:
    active_filters = [name for name in FILTER_ENVIRONMENT if os.environ.get(name)]
    if active_filters:
        raise OwnershipError(
            "native ownership check refuses ambient selectors: "
            + ", ".join(active_filters)
        )
    environment = os.environ.copy()
    for name in FILTER_ENVIRONMENT:
        environment.pop(name, None)

    pytest_output = _run_collector(
        ["uv", "run", "--locked", "--no-sync", "pytest", "--collect-only", "-q"],
        ROOT,
        environment,
    )
    vitest_bin = FRONTEND / "node_modules" / ".bin" / "vitest"
    playwright_bin = FRONTEND / "node_modules" / ".bin" / "playwright"
    if not vitest_bin.is_file() or not playwright_bin.is_file():
        raise OwnershipError(
            "frontend dependencies are missing; install the locked frontend dependencies first"
        )
    vitest_output = _run_collector(
        [str(vitest_bin), "list", "--config", "vitest.config.ts", "--json"],
        FRONTEND,
        environment,
    )
    playwright_output = _run_collector(
        [str(playwright_bin), "test", "--config", "playwright.config.ts", "--list"],
        FRONTEND,
        environment,
    )
    return {
        "pytest": parse_pytest(pytest_output),
        "vitest": parse_vitest(vitest_output),
        "playwright": parse_playwright(playwright_output),
    }


def main() -> int:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        selectors_by_suite = validate_manifest_data(manifest)
        native_cases = collect_native_cases()
        summary = validate_case_ownership(manifest, selectors_by_suite, native_cases)
    except (OSError, json.JSONDecodeError, OwnershipError) as error:
        print(f"module ownership refused: {error}", file=sys.stderr)
        return 1

    print("MODULE_OWNERSHIP native discovery passed; no test bodies were executed.")
    for suite, result in summary.items():
        print(
            f"MODULE_OWNERSHIP suite={suite} cases={result['case_count']} "
            f"files={result['file_count']} sha256={result['sha256']}"
        )
        for module_name, count in result["module_cases"].items():
            if count:
                print(
                    f"MODULE_OWNERSHIP module={module_name} suite={suite} cases={count}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
