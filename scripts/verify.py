"""Transparent quick, focused and full local verification for Plotloom."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
FILTER_ENVIRONMENT = {
    "PYTEST_ADDOPTS": None,
    "BROWSER_GREP": ".*",
    "BROWSER_SHARD": None,
    "VITEST_FILTER": None,
    "VITEST_GREP": None,
    "PLAYWRIGHT_GREP": None,
    "PLAYWRIGHT_SHARD": None,
    "PWTEST_GREP": None,
    "PWTEST_SHARD_INDEX": None,
    "PWTEST_SHARD_TOTAL": None,
}


@dataclass(frozen=True)
class Step:
    label: str
    command: tuple[str, ...]
    cwd: Path = ROOT
    environment: tuple[tuple[str, str], ...] = ()


def _command(
    label: str,
    *parts: str,
    cwd: Path = ROOT,
    environment: Mapping[str, str] | None = None,
) -> Step:
    return Step(label, tuple(parts), cwd, tuple((environment or {}).items()))


def _run_step(tier: str, step: Step) -> int:
    environment = os.environ.copy()
    environment.update(dict(step.environment))
    command = list(step.command)
    print(
        f"[{tier}] COMMAND (cwd={step.cwd.relative_to(ROOT) if step.cwd != ROOT else '.'}): {shlex.join(command)}",
        flush=True,
    )
    for name, value in step.environment:
        print(f"[{tier}] ENV {name}={shlex.quote(value)}", flush=True)
    started = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=step.cwd, env=environment, check=False)
        exit_code = result.returncode
    except OSError as error:
        print(f"[{tier}] command could not start: {error}", file=sys.stderr, flush=True)
        exit_code = 127
    elapsed = time.perf_counter() - started
    print(
        f"[{tier}] STEP label={step.label} elapsed_seconds={elapsed:.3f} exit_code={exit_code}",
        flush=True,
    )
    return exit_code


def _run_steps(tier: str, steps: Sequence[Step]) -> int:
    started = time.perf_counter()
    exit_code = 0
    for step in steps:
        exit_code = _run_step(tier, step)
        if exit_code:
            break
    elapsed = time.perf_counter() - started
    print(
        f"VERIFY_SUMMARY tier={tier} elapsed_seconds={elapsed:.3f} exit_code={exit_code}",
        flush=True,
    )
    return exit_code


def _quick_steps() -> list[Step]:
    return [
        _command("locked dependencies", "uv", "lock", "--check"),
        _command(
            "API unused imports",
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "ruff",
            "check",
            "src/plotloom/api",
            "--select",
            "F401",
        ),
        _command("frontend unit tests", "npm", "--prefix", "frontend", "test"),
        _command(
            "frontend type contracts", "npm", "--prefix", "frontend", "run", "typecheck"
        ),
        _command(
            "browser fixture type contracts",
            "npm",
            "--prefix",
            "frontend",
            "run",
            "typecheck:e2e",
        ),
    ]


def _full_steps(wheel_dir: Path) -> list[Step]:
    return [
        _command("locked dependencies", "uv", "lock", "--check"),
        _command("ffmpeg probe tool", "ffmpeg", "-version"),
        _command("ffprobe probe tool", "ffprobe", "-version"),
        _command(
            "API unused imports",
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "ruff",
            "check",
            "src/plotloom/api",
            "--select",
            "F401",
        ),
        _command(
            "archived prompt reader",
            "npm",
            "--prefix",
            "docs/prompt-pipeline-lab",
            "run",
            "verify",
        ),
        _command("frontend unit tests", "npm", "--prefix", "frontend", "test"),
        _command(
            "frontend type contracts", "npm", "--prefix", "frontend", "run", "typecheck"
        ),
        _command(
            "Python contracts",
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "pytest",
            "-q",
            "--durations=20",
        ),
        _command(
            "deterministic production bundle",
            "npm",
            "--prefix",
            "frontend",
            "run",
            "build:deterministic",
        ),
        _command(
            "checked production bundle parity",
            "git",
            "diff",
            "--exit-code",
            "--",
            "src/plotloom/static",
        ),
        _command(
            "unfiltered browser shard coverage",
            "node",
            "scripts/check_browser_shard_manifest.mjs",
            cwd=FRONTEND,
            environment={"BROWSER_GREP": ".*"},
        ),
        _command(
            "unfiltered browser suite", "npm", "--prefix", "frontend", "run", "test:e2e"
        ),
        _command("wheel build", "uv", "build", "--wheel", "--out-dir", str(wheel_dir)),
        _command(
            "installed wheel smoke",
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "python",
            "scripts/smoke_installed_wheel.py",
            str(wheel_dir),
        ),
    ]


def _validate_full_filters(environment: Mapping[str, str]) -> list[str]:
    refused = []
    for name, allowed in FILTER_ENVIRONMENT.items():
        value = environment.get(name)
        if value and value != allowed:
            refused.append(name)
    return refused


def _project_selector(
    value: str,
    *,
    base: Path,
    required_parent: Path,
    extensions: tuple[str, ...],
    label: str,
) -> str:
    path_value = value.split("::", 1)[0]
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(required_parent.resolve(strict=True))
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError(f"unknown {label} selector: {value}") from error
    if not resolved.is_file() or not resolved.name.endswith(extensions):
        raise ValueError(f"unknown {label} selector: {value}")
    if "::" in value and not value.split("::", 1)[1]:
        raise ValueError(f"unknown {label} selector: {value}")
    return value


def _focused_steps(args: argparse.Namespace) -> list[Step]:
    selectors = {
        "pytest": args.pytest,
        "vitest": args.vitest,
        "playwright": args.playwright,
    }
    if not any(selectors.values()):
        raise ValueError(
            "focused requires at least one --pytest, --vitest or --playwright selector"
        )
    if any(len(values) != len(set(values)) for values in selectors.values()):
        raise ValueError("focused selectors must not be repeated")

    steps: list[Step] = []
    if args.pytest:
        validated = [
            _project_selector(
                value,
                base=ROOT,
                required_parent=ROOT / "tests",
                extensions=(".py",),
                label="pytest",
            )
            for value in args.pytest
        ]
        common = ("uv", "run", "--locked", "--no-sync", "pytest")
        for selector in validated:
            steps.append(
                _command(
                    f"validate pytest selector {selector}",
                    *common,
                    "--collect-only",
                    "-q",
                    selector,
                )
            )
        steps.append(_command("focused pytest", *common, "-q", *validated))
    if args.vitest:
        validated = [
            _project_selector(
                value,
                base=FRONTEND,
                required_parent=FRONTEND,
                extensions=(
                    ".test.ts",
                    ".test.tsx",
                    ".test.js",
                    ".test.jsx",
                    ".spec.ts",
                    ".spec.tsx",
                    ".spec.js",
                    ".spec.jsx",
                ),
                label="Vitest",
            )
            for value in args.vitest
        ]
        steps.append(
            _command(
                "focused Vitest",
                "npm",
                "--prefix",
                "frontend",
                "test",
                "--",
                *validated,
            )
        )
    if args.playwright:
        validated = [
            _project_selector(
                value,
                base=FRONTEND,
                required_parent=FRONTEND / "e2e",
                extensions=(
                    ".spec.ts",
                    ".spec.tsx",
                    ".spec.js",
                    ".spec.jsx",
                    ".test.ts",
                    ".test.tsx",
                    ".test.js",
                    ".test.jsx",
                ),
                label="Playwright",
            )
            for value in args.playwright
        ]
        steps.append(
            _command(
                "focused Playwright",
                "npm",
                "--prefix",
                "frontend",
                "run",
                "test:e2e",
                "--",
                *validated,
            )
        )
    return steps


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="tier", required=True)
    subparsers.add_parser("quick", help="lock, API lint, frontend unit and type checks")
    subparsers.add_parser("full", help="complete local software release verification")
    focused = subparsers.add_parser(
        "focused", help="run explicitly selected native tests"
    )
    focused.add_argument(
        "--pytest", action="append", default=[], metavar="CASE_OR_FILE"
    )
    focused.add_argument("--vitest", action="append", default=[], metavar="FILE")
    focused.add_argument("--playwright", action="append", default=[], metavar="SPEC")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.tier == "quick":
        print(
            "QUICK is local feedback only. Not run: Python integration, browser, archived-reader, bundle build/parity, wheel or installed-wheel smoke.",
            flush=True,
        )
        return _run_steps(args.tier, _quick_steps())
    if args.tier == "focused":
        try:
            steps = _focused_steps(args)
        except ValueError as error:
            print(f"focused selection refused: {error}", file=sys.stderr, flush=True)
            print(
                "VERIFY_SUMMARY tier=focused elapsed_seconds=0.000 exit_code=2",
                flush=True,
            )
            return 2
        return _run_steps(args.tier, steps)

    refused = _validate_full_filters(os.environ)
    if refused:
        print(
            "full verification refused ambient selectors: "
            + ", ".join(sorted(refused)),
            file=sys.stderr,
            flush=True,
        )
        print("VERIFY_SUMMARY tier=full elapsed_seconds=0.000 exit_code=2", flush=True)
        return 2
    print(
        "FULL covers all local software gates; it is not product or creative acceptance.",
        flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="plotloom-verify-wheel-") as directory:
        return _run_steps(args.tier, _full_steps(Path(directory)))


if __name__ == "__main__":
    raise SystemExit(main())
