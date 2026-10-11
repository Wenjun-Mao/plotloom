"""Protect native test ownership and collection identity checks."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "testing" / "check_module_ownership.py"
SPEC = importlib.util.spec_from_file_location("plotloom_module_ownership", CHECKER_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


def _fixture_repo(
    root: Path,
) -> tuple[dict, dict[str, dict[str, str]], dict[str, list[str]]]:
    files = (
        "tests/test_sample.py",
        "frontend/tests/sample.test.ts",
        "frontend/e2e/sample.spec.ts",
        "docs/testing-support.md",
    )
    for relative in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "modules": {
            "sample": {
                "description": "Sample owner.",
                "selectors": {
                    "pytest": ["tests/test_sample.py"],
                    "vitest": ["frontend/tests/sample.test.ts"],
                    "playwright": ["frontend/e2e/sample.spec.ts"],
                },
            }
        },
        "support_dependencies": [
            {
                "suite": "playwright",
                "path": "docs/testing-support.md",
                "consumers": ["sample"],
            }
        ],
    }
    cases = {
        "pytest": [
            "tests/test_sample.py::test_parameter[one]",
            "tests/test_sample.py::test_parameter[two]",
        ],
        "vitest": ["tests/sample.test.ts::sample suite > keeps full names"],
        "playwright": ["sample.spec.ts:5:1 › keeps the browser title"],
    }
    selectors = CHECKER.validate_manifest_data(manifest, root)
    return manifest, selectors, cases


def test_native_parsers_preserve_parameterized_and_nested_case_ids(tmp_path):
    pytest_cases = CHECKER.parse_pytest(
        "tests/test_sample.py::test_parameter[one]\n"
        "tests/test_sample.py::test_parameter[two]\n2 tests collected\n"
    )
    assert pytest_cases[-2:] == [
        "tests/test_sample.py::test_parameter[one]",
        "tests/test_sample.py::test_parameter[two]",
    ]

    vitest_file = tmp_path / "frontend" / "tests" / "sample.test.ts"
    vitest_file.parent.mkdir(parents=True)
    vitest_file.write_text("", encoding="utf-8")
    vitest_cases = CHECKER.parse_vitest(
        json.dumps(
            [
                {
                    "file": str(vitest_file),
                    "name": "sample suite > keeps full names",
                }
            ]
        ),
        tmp_path / "frontend",
    )
    assert vitest_cases == ["tests/sample.test.ts::sample suite > keeps full names"]
    duplicate_cases = CHECKER.parse_vitest(
        json.dumps(
            [
                {"file": str(vitest_file), "name": "parameterized case"},
                {"file": str(vitest_file), "name": "parameterized case"},
            ]
        ),
        tmp_path / "frontend",
    )
    assert duplicate_cases == [
        "tests/sample.test.ts::parameterized case [collection occurrence 1 of 2]",
        "tests/sample.test.ts::parameterized case [collection occurrence 2 of 2]",
    ]

    browser_cases = CHECKER.parse_playwright(
        "Listing tests:\n"
        "  sample.spec.ts:5:1 › browser suite › keeps viewport title\n"
        "Total: 1 test in 1 file\n"
    )
    assert browser_cases == [
        "sample.spec.ts:5:1 › browser suite › keeps viewport title"
    ]


def test_module_ownership_requires_exactly_one_native_owner(tmp_path):
    manifest, selectors, cases = _fixture_repo(tmp_path)
    summary = CHECKER.validate_case_ownership(manifest, selectors, cases, tmp_path)
    assert summary["pytest"]["case_count"] == 2
    assert summary["vitest"]["file_count"] == 1
    assert summary["playwright"]["module_cases"]["sample"] == 1

    cases["vitest"].append(cases["vitest"][0])
    with pytest.raises(CHECKER.OwnershipError, match="duplicate case IDs"):
        CHECKER.validate_case_ownership(manifest, selectors, cases, tmp_path)
    cases["vitest"].pop()

    cases["vitest"].append("tests/unowned.test.ts::new case")
    with pytest.raises(CHECKER.OwnershipError, match="file ownership mismatch"):
        CHECKER.validate_case_ownership(manifest, selectors, cases, tmp_path)


def test_module_ownership_rejects_empty_modules_and_duplicate_files(tmp_path):
    manifest, _, _ = _fixture_repo(tmp_path)
    manifest["modules"]["empty"] = {
        "description": "No tests.",
        "selectors": {"pytest": [], "vitest": [], "playwright": []},
    }
    with pytest.raises(CHECKER.OwnershipError, match="empty test module"):
        CHECKER.validate_manifest_data(manifest, tmp_path)

    del manifest["modules"]["empty"]
    manifest["modules"]["second"] = {
        "description": "Duplicate owner.",
        "selectors": {
            "pytest": ["tests/test_sample.py"],
            "vitest": [],
            "playwright": [],
        },
    }
    with pytest.raises(CHECKER.OwnershipError, match="duplicate pytest selector"):
        CHECKER.validate_manifest_data(manifest, tmp_path)
    del manifest["modules"]["second"]
    manifest["modules"]["sample"]["selectors"]["pytest"] = ["tests/missing_test.py"]
    with pytest.raises(CHECKER.OwnershipError, match="stale or unsafe"):
        CHECKER.validate_manifest_data(manifest, tmp_path)


def test_module_ownership_rejects_source_test_files_without_native_cases(tmp_path):
    manifest, selectors, cases = _fixture_repo(tmp_path)
    empty_test = tmp_path / "tests" / "test_empty.py"
    empty_test.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(CHECKER.OwnershipError, match="source discovery mismatch"):
        CHECKER.validate_case_ownership(manifest, selectors, cases, tmp_path)


def test_native_ownership_guard_refuses_ambient_selectors_before_collection(
    monkeypatch,
):
    monkeypatch.setenv("BROWSER_SHARD", "1")
    with (
        patch.object(
            CHECKER.subprocess,
            "run",
            side_effect=AssertionError("collector must not launch"),
        ),
        pytest.raises(CHECKER.OwnershipError, match="ambient selectors: BROWSER_SHARD"),
    ):
        CHECKER.collect_native_cases()


def test_manifest_maps_cross_module_pytest_helper_consumers():
    manifest = json.loads(CHECKER.MANIFEST.read_text(encoding="utf-8"))
    owners = {
        selector: module_name
        for module_name, module in manifest["modules"].items()
        for selector in module["selectors"]["pytest"]
    }
    dependencies = {
        dependency["path"]: set(dependency["consumers"])
        for dependency in manifest["support_dependencies"]
        if dependency["suite"] == "pytest"
    }

    known_consumers = {
        "tests/backend_core/conftest.py": {
            "tests/test_current_stage_evidence.py",
            "tests/test_graph_authoring_contract.py",
            "tests/test_media.py",
            "tests/test_project_storage_authoring_control_contracts.py",
            "tests/test_project_storage_route_contracts.py",
            "tests/test_project_storage_source_outline.py",
            "tests/test_project_storage_work_unit_contracts.py",
            "tests/test_production_project_folder_runtime.py",
            "tests/backend_core/test_e2e_listener_ownership.py",
            "tests/generation/test_prompts.py",
            "tests/backend_core/test_domain.py",
            "tests/backend_core/test_jobs.py",
        },
        "tests/identity_review_assertions.py": {
            "tests/test_project_storage_image_identity_contracts.py",
        },
    }
    for helper_path, consumer_files in known_consumers.items():
        assert helper_path in dependencies
        assert consumer_files <= owners.keys()
        expected_modules = {owners[path] for path in consumer_files}
        assert expected_modules <= dependencies[helper_path]
