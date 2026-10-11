"""Build explicit native selectors from the reviewed product-module map."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUITES = ("pytest", "vitest", "playwright")
TEST_ROOTS = {
    "pytest": "tests",
    "vitest": "frontend/tests",
    "playwright": "frontend/e2e",
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
DEPTH_SUITES = {
    "contract": ("pytest", "vitest"),
    "browser": ("playwright",),
    "complete": SUITES,
}
REQUIRED_COMPLETE_GATE_STEPS = {
    "locked-dependencies": ("locked dependencies",),
    "static-bundle": (
        "deterministic production bundle",
        "checked production bundle parity",
    ),
    "browser-allocation": ("unfiltered browser shard coverage",),
    "wheel-package": ("wheel build", "installed wheel smoke"),
}


@dataclass(frozen=True)
class ModulePlan:
    names: tuple[str, ...]
    depth: str
    suites: tuple[str, ...]
    descriptions: tuple[tuple[str, str], ...]
    selectors: tuple[tuple[str, tuple[str, ...]], ...]
    dependencies: tuple[dict[str, Any], ...]
    required_gates: tuple[str, ...]


@dataclass(frozen=True)
class ModuleStep:
    label: str
    command: tuple[str, ...]
    cwd: Path


def build_module_plan(
    manifest: Any,
    module_names: list[str],
    depth: str,
    *,
    root: Path,
) -> ModulePlan:
    if depth not in DEPTH_SUITES:
        raise ValueError(f"unknown module depth: {depth}")
    if not module_names:
        raise ValueError("module requires at least one --module")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("modules"), dict):
        raise TypeError("module ownership manifest must define a module map")
    if not all(isinstance(name, str) and name for name in module_names):
        raise TypeError("module names must be nonempty strings")

    modules = manifest["modules"]
    names = tuple(dict.fromkeys(module_names))
    unknown = [name for name in names if name not in modules]
    if unknown:
        raise ValueError(
            f"unknown module(s): {', '.join(unknown)}; known: {', '.join(sorted(modules))}"
        )

    suites = DEPTH_SUITES[depth]
    descriptions = []
    selectors_by_suite: dict[str, tuple[str, ...]] = {}
    for name in names:
        module = modules[name]
        if not isinstance(module, dict):
            raise TypeError(f"invalid module entry: {name}")
        description = module.get("description")
        selectors = module.get("selectors")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"module needs a description: {name}")
        if not isinstance(selectors, dict) or set(selectors) != set(SUITES):
            raise ValueError(f"module needs selectors for every native suite: {name}")
        descriptions.append((name, description))

    selected_suites = []
    for suite in suites:
        selected: list[str] = []
        for name in names:
            values = modules[name]["selectors"][suite]
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise ValueError(f"invalid {suite} selector list: {name}")
            selected.extend(values)
        unique = tuple(dict.fromkeys(selected))
        if not unique:
            if depth == "browser":
                raise ValueError(
                    f"selection has no {suite} tests at depth {depth}: {', '.join(names)}"
                )
            continue
        for value in unique:
            try:
                path = (root / value).resolve(strict=True)
                path.relative_to((root / TEST_ROOTS[suite]).resolve(strict=True))
            except (OSError, RuntimeError, ValueError) as error:
                raise ValueError(
                    f"stale or unsafe {suite} selector: {value}"
                ) from error
            if (
                not path.is_file()
                or path.relative_to(root.resolve()).as_posix() != value
                or not path.name.endswith(TEST_SUFFIXES[suite])
            ):
                raise ValueError(f"invalid {suite} selector path: {value}")
        selectors_by_suite[suite] = unique
        selected_suites.append(suite)
    if not selected_suites:
        raise ValueError(f"selection has no tests at depth {depth}: {', '.join(names)}")

    raw_dependencies = manifest.get("support_dependencies", [])
    if not isinstance(raw_dependencies, list):
        raise TypeError("module support dependencies must be a list")
    module_set = set(names)
    dependencies_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for dependency in raw_dependencies:
        if not isinstance(dependency, dict):
            raise TypeError("invalid support dependency in module map")
        suite = dependency.get("suite")
        path = dependency.get("path")
        consumers = dependency.get("consumers")
        if suite not in SUITES or not isinstance(path, str):
            raise ValueError("invalid support dependency identity in module map")
        if not isinstance(consumers, list) or not all(
            isinstance(consumer, str) for consumer in consumers
        ):
            raise ValueError(f"invalid support dependency consumers: {path}")
        if suite not in suites or not module_set.intersection(consumers):
            continue
        try:
            resolved = (root / path).resolve(strict=True)
            resolved.relative_to(root.resolve(strict=True))
        except (OSError, RuntimeError, ValueError) as error:
            raise ValueError(f"stale or unsafe support dependency: {path}") from error
        if (
            not resolved.is_file()
            or resolved.relative_to(root.resolve()).as_posix() != path
        ):
            raise ValueError(f"invalid support dependency path: {path}")
        dependencies_by_key[(suite, path)] = dependency

    raw_complete_gates = manifest.get("required_complete_gates", {})
    if not isinstance(raw_complete_gates, dict):
        raise TypeError("required complete gates must be an object")
    required_gates = []
    for gate, consumers in raw_complete_gates.items():
        if gate not in REQUIRED_COMPLETE_GATE_STEPS:
            raise ValueError(f"unknown required complete gate: {gate}")
        if (
            not isinstance(consumers, list)
            or not consumers
            or not all(
                isinstance(consumer, str) and consumer in modules
                for consumer in consumers
            )
        ):
            raise ValueError(f"invalid module owners for complete gate: {gate}")
        if len(consumers) != len(set(consumers)):
            raise ValueError(f"duplicate module owners for complete gate: {gate}")
        if depth == "complete" and module_set.intersection(consumers):
            required_gates.append(gate)

    return ModulePlan(
        names=names,
        depth=depth,
        suites=tuple(selected_suites),
        descriptions=tuple(descriptions),
        selectors=tuple(
            (suite, selectors_by_suite[suite]) for suite in selected_suites
        ),
        dependencies=tuple(
            dependencies_by_key[key] for key in sorted(dependencies_by_key)
        ),
        required_gates=tuple(required_gates),
    )


def format_module_plan(plan: ModulePlan) -> list[str]:
    omitted_suites = [suite for suite in SUITES if suite not in plan.suites]
    lines = [
        f"MODULE_PLAN depth={plan.depth} modules={','.join(plan.names)} gate=module-scoped",
        "MODULE_PLAN native ownership preflight validates the complete case union without test bodies.",
    ]
    for name, description in plan.descriptions:
        lines.append(f"MODULE_PLAN module={name} rationale={description}")
    for suite, selectors in plan.selectors:
        lines.append(f"MODULE_PLAN suite={suite} files={len(selectors)}")
        lines.extend(f"MODULE_PLAN selector={value}" for value in selectors)
    for dependency in plan.dependencies:
        consumers = sorted(set(dependency["consumers"]).intersection(plan.names))
        lines.append(
            "MODULE_PLAN shared_dependency="
            f"{dependency['suite']}:{dependency['path']} "
            f"kind={dependency.get('kind', 'support')} consumers={','.join(consumers)}"
        )
    lines.append(
        "MODULE_PLAN omitted_suites="
        + (",".join(omitted_suites) if omitted_suites else "none")
    )
    lines.append(
        "MODULE_PLAN required_complete_gates="
        + (",".join(plan.required_gates) if plan.required_gates else "none")
    )
    lines.append(
        "MODULE_PLAN omitted_shared_gates=ffmpeg/ffprobe,API-lint,archived-reader,unfiltered-browser-suite,tests-owned-by-other-modules; this is not full release verification."
    )
    return lines


def build_module_steps(plan: ModulePlan, root: Path) -> tuple[ModuleStep, ...]:
    steps = [
        ModuleStep(
            "complete native module ownership preflight",
            (
                "uv",
                "run",
                "--locked",
                "--no-sync",
                "python",
                "scripts/testing/check_module_ownership.py",
            ),
            root,
        )
    ]
    if "vitest" in plan.suites or "playwright" in plan.suites:
        steps.append(
            ModuleStep(
                "frontend type contracts",
                ("npm", "--prefix", "frontend", "run", "typecheck"),
                root,
            )
        )
    if "playwright" in plan.suites:
        steps.append(
            ModuleStep(
                "browser fixture type contracts",
                ("npm", "--prefix", "frontend", "run", "typecheck:e2e"),
                root,
            )
        )
    for suite, selectors in plan.selectors:
        local_selectors = tuple(value.removeprefix("frontend/") for value in selectors)
        if suite == "pytest":
            command = (
                "uv",
                "run",
                "--locked",
                "--no-sync",
                "pytest",
                "-q",
                *local_selectors,
            )
        elif suite == "vitest":
            command = (
                "npm",
                "--prefix",
                "frontend",
                "test",
                "--",
                *local_selectors,
            )
        else:
            command = (
                "npm",
                "--prefix",
                "frontend",
                "run",
                "test:e2e",
                "--",
                *local_selectors,
            )
        label = {
            "pytest": "module pytest",
            "vitest": "module Vitest",
            "playwright": "module Playwright",
        }[suite]
        steps.append(ModuleStep(label, command, root))
    return tuple(steps)


def format_module_commands(steps: Sequence[Any], root: Path) -> list[str]:
    lines = []
    for step in steps:
        cwd = step.cwd.relative_to(root) if step.cwd != root else Path(".")
        lines.append(
            f"MODULE_PLAN command label={step.label} cwd={cwd}: "
            f"{shlex.join(step.command)}"
        )
    return lines


def add_module_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--module", action="append", default=[], metavar="NAME")
    parser.add_argument(
        "--depth", required=True, choices=("contract", "browser", "complete")
    )
    parser.add_argument(
        "--show",
        "--plan",
        action="store_true",
        dest="show_plan",
        help="print expanded selectors and commands without running checks",
    )


def run_module_command(
    args: argparse.Namespace,
    *,
    root: Path,
    environment: Mapping[str, str],
    filter_names: Sequence[str],
    command_factory,
    full_steps_builder,
    run_steps,
) -> int:
    active_filters = sorted(name for name in filter_names if environment.get(name))
    if active_filters:
        print(
            "module verification refused ambient selectors: "
            + ", ".join(active_filters),
            file=sys.stderr,
            flush=True,
        )
        print(
            "VERIFY_SUMMARY tier=module elapsed_seconds=0.000 exit_code=2", flush=True
        )
        return 2

    with tempfile.TemporaryDirectory(prefix="plotloom-module-wheel-") as directory:
        try:
            manifest = json.loads(
                (root / "scripts" / "testing" / "module-ownership.json").read_text(
                    encoding="utf-8"
                )
            )
            plan = build_module_plan(manifest, args.module, args.depth, root=root)
            steps = [
                command_factory(step.label, *step.command, cwd=step.cwd)
                for step in build_module_steps(plan, root)
            ]
            if plan.required_gates:
                release_steps = {
                    step.label: step for step in full_steps_builder(Path(directory))
                }
                gate_labels = [
                    label
                    for gate in plan.required_gates
                    for label in REQUIRED_COMPLETE_GATE_STEPS[gate]
                ]
                gate_steps = [release_steps[label] for label in gate_labels]
                ownership = steps[:1]
                typechecks = [
                    step
                    for step in steps[1:]
                    if step.label
                    in ("frontend type contracts", "browser fixture type contracts")
                ]
                native_suites = [step for step in steps[1:] if step not in typechecks]
                steps = [*ownership, *typechecks, *gate_steps, *native_suites]
        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            print(f"module selection refused: {error}", file=sys.stderr, flush=True)
            print(
                "VERIFY_SUMMARY tier=module elapsed_seconds=0.000 exit_code=2",
                flush=True,
            )
            return 2

        for line in [*format_module_plan(plan), *format_module_commands(steps, root)]:
            print(line, flush=True)
        if args.show_plan:
            print(
                "VERIFY_SUMMARY tier=module-plan elapsed_seconds=0.000 exit_code=0",
                flush=True,
            )
            return 0
        return run_steps(f"module:{args.depth}", steps)
