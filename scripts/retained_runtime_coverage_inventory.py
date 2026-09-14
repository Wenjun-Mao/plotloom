#!/usr/bin/env python3
"""Verify assertion-level coverage retained after the shared-runtime retirement.

The checked-in inventory is an authored review record.  This script derives its
historical population from Git and rejects omitted entries, default policies,
or references to tests that no longer contain executable assertions.  It can
prove reference integrity, not semantic equivalence; reviewers still compare
the recorded baseline and replacement assertions before accepting a change.
"""

from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


BASELINE = "e658057"
RETIREMENT = "f908c51"
INVENTORY = Path("docs/verification/2026-09-14-retained-runtime-coverage-inventory.json")
DISPOSITIONS = {"migrated_current_contract", "existing_equivalent", "truly_retired_contract"}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout


def _literal_or_source(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (TypeError, ValueError):
        return {"source": ast.unparse(node)}


def _json_value(value: Any) -> Any:
    """Match the JSON inventory's list/dict representation exactly."""

    return json.loads(json.dumps(value))


def _assertions(source: str, node: ast.AST) -> list[str]:
    values = [ast.unparse(item.test) for item in ast.walk(node) if isinstance(item, ast.Assert)]
    for item in ast.walk(node):
        if not isinstance(item, ast.With):
            continue
        for context in item.items:
            expression = context.context_expr
            if isinstance(expression, ast.Call) and ast.unparse(expression.func).endswith("raises"):
                values.append(f"raises: {ast.unparse(expression)}")
    return values


def _trigger(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Keep source-level action evidence without trying to infer its meaning."""

    actions: list[str] = []
    for statement in node.body:
        if isinstance(statement, (ast.Assert, ast.With)):
            break
        actions.append(ast.unparse(statement))
        if len(actions) == 8:
            break
    return actions


def _parameter_cases(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for decorator_index, decorator in enumerate(node.decorator_list):
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        if decorator.func.attr != "parametrize" or len(decorator.args) < 2:
            continue
        source_cases = decorator.args[1]
        if isinstance(source_cases, (ast.List, ast.Tuple, ast.Set)):
            values = [_literal_or_source(item) for item in source_cases.elts]
        else:
            values = [_literal_or_source(source_cases)]
        for case_index, value in enumerate(values):
            cases.append(
                {
                    "decorator_index": decorator_index,
                    "case_index": case_index,
                    "argnames": _json_value(_literal_or_source(decorator.args[0])),
                    "value": _json_value(value),
                }
            )
    return cases


def _changed_test_paths() -> list[str]:
    rows = _git("diff", "--name-status", BASELINE, RETIREMENT, "--", "tests").splitlines()
    return sorted(path for row in rows if row and row[0] in {"D", "M"} for path in [row.split("\t")[-1]])


def baseline_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in _changed_test_paths():
        source = _git("show", f"{BASELINE}:{path}")
        tree = ast.parse(source, filename=path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                continue
            test_id = f"{path}::{node.name}"
            baseline = {
                "source_test_id": test_id,
                "source_path": path,
                "source_line": node.lineno,
                "baseline_source_sha256": sha256(ast.get_source_segment(source, node).encode()).hexdigest(),
                "original_trigger": _trigger(node),
                "required_assertions": _assertions(source, node),
                "forbidden_results": [
                    value for value in _assertions(source, node)
                    if " not " in value or "!=" in value or "raises:" in value
                ],
            }
            entries.append({"id": test_id, "entry_kind": "function", **baseline})
            for case in _parameter_cases(node):
                entries.append(
                    {
                        "id": f"{test_id}[{case['decorator_index']}:{case['case_index']}]",
                        "entry_kind": "parameter_case",
                        "parameter_case": case,
                        **baseline,
                    }
                )
    return sorted(entries, key=lambda entry: entry["id"])


def current_assertion_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for path in Path("tests").rglob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                identifier = f"{path.as_posix()}::{node.name}"
                segment = ast.get_source_segment(source, node)
                assert segment is not None
                catalog[identifier] = {
                    "source_sha256": sha256(segment.encode()).hexdigest(),
                    "assertions": _assertions(source, node),
                }
    return catalog


def check_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {entry["id"]: entry for entry in baseline_entries()}
    entries = inventory.get("entries")
    if inventory.get("schema_version") != 2:
        errors.append("inventory must use schema_version 2")
    if inventory.get("baseline_commit") != BASELINE or inventory.get("retirement_commit") != RETIREMENT:
        errors.append("inventory baseline or retirement commit differs from the approved comparison")
    if "policies" in inventory:
        errors.append("inventory must not contain file-level policies or defaults")
    if not isinstance(entries, list):
        return [*errors, "inventory entries must be a list"]
    by_id = {entry.get("id"): entry for entry in entries if isinstance(entry, dict)}
    if len(by_id) != len(entries):
        errors.append("inventory entries must have unique string ids")
    if set(by_id) != set(expected):
        errors.append("inventory does not classify exactly every changed baseline function and parameter case")
    catalog = inventory.get("replacement_assertion_catalog")
    if not isinstance(catalog, dict):
        return [*errors, "inventory replacement_assertion_catalog must be an object"]
    current_catalog = current_assertion_catalog()
    for identifier, baseline in expected.items():
        entry = by_id.get(identifier)
        if entry is None:
            continue
        if entry.get("entry_kind") != baseline["entry_kind"]:
            errors.append(f"entry kind differs from baseline: {identifier}")
        if any(entry.get(key) != value for key, value in baseline.items()):
            errors.append(f"baseline trigger or assertions differ: {identifier}")
        if baseline["entry_kind"] == "parameter_case" and entry.get("parameter_case") != baseline["parameter_case"]:
            errors.append(f"parameter case differs from baseline: {identifier}")
        disposition = entry.get("disposition")
        replacements = entry.get("current_replacements")
        if disposition not in DISPOSITIONS:
            errors.append(f"entry has no explicit valid disposition: {identifier}")
            continue
        if not isinstance(replacements, list) or any(not isinstance(item, str) for item in replacements):
            errors.append(f"entry replacements must be explicit test ids: {identifier}")
            continue
        if disposition == "truly_retired_contract":
            rationale = entry.get("retirement_rationale")
            if replacements or not isinstance(rationale, str) or "breaking project-folder storage" not in rationale:
                errors.append(f"retired entry lacks an individual breaking-storage rationale: {identifier}")
            continue
        if not replacements:
            errors.append(f"retained entry has no exact replacement: {identifier}")
            continue
        for replacement in replacements:
            observed = catalog.get(replacement)
            current = current_catalog.get(replacement)
            if not isinstance(observed, dict) or current is None:
                errors.append(f"replacement is absent: {identifier} -> {replacement}")
            elif observed != current or not observed["assertions"]:
                errors.append(f"replacement assertion record is stale or empty: {identifier} -> {replacement}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify the checked-in inventory")
    args = parser.parse_args()
    if not args.check:
        parser.error("only --check is supported; the inventory is an authored review record")
    errors = check_inventory(json.loads(INVENTORY.read_text(encoding="utf-8")))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
