"""Exact selector coverage and collector ancestry for native pytest commands."""
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from scripts.testing.module_selection import ModulePlan, build_module_steps, order_pytest_selectors
from tests.python_suite_runner_support import RUNNER
from tests.test_verify_script import VERIFY

ROOT = Path(__file__).resolve().parents[1]


def assert_ancestor_branches_contiguous(selectors, root):
    paths = [(root / value.split("::", 1)[0]).resolve().parts for value in selectors]
    prefixes = {path[:length] for path in paths for length in range(1, len(path))}
    for prefix in prefixes:
        positions = [i for i, path in enumerate(paths) if path[:len(prefix)] == prefix]
        assert positions == list(range(min(positions), max(positions) + 1))


def test_component_order_preserves_values_multiplicity_and_stable_same_file_cases(tmp_path):
    selectors = ["tests/pkg/test_z.py::test_z[slash/value]", "tests/pkg_extra/test_a.py",
        "tests/pkg/nested/test_a.py::test_second", "tests/test_root.py", "tests/pkg-other/test_a.py",
        str(tmp_path / "tests/pkg/test_z.py") + "::test_first", "tests/pkg/nested/test_b.py",
        "tests/pkg/nested/test_a.py::test_first", "tests/pkg/test_z.py::test_z[slash/value]"]
    original = list(selectors)
    ordered = order_pytest_selectors(selectors, root=tmp_path)
    assert Counter(ordered) == Counter(original) and selectors == original
    assert_ancestor_branches_contiguous(ordered, tmp_path)
    for filename in {value.split("::", 1)[0] for value in selectors}:
        identity = (tmp_path / filename).resolve()
        before = [value for value in original if (tmp_path / value.split("::", 1)[0]).resolve() == identity]
        after = [value for value in ordered if (tmp_path / value.split("::", 1)[0]).resolve() == identity]
        assert after == before
    assert order_pytest_selectors([], root=tmp_path) == ()


def test_focused_and_module_commands_apply_the_same_exact_selection_order():
    selectors = ["tests/backend_core/test_runtime_recovery.py", "tests/test_authored_route_timing.py",
        "tests/backend_core/test_jobs.py"]
    expected = order_pytest_selectors(selectors, root=ROOT)
    args = VERIFY._parser().parse_args(["focused", *[part for s in selectors for part in ("--pytest", s)]])
    focused = next(step for step in VERIFY._focused_steps(args) if step.label == "focused pytest")
    plan = ModulePlan(names=("fixture",), depth="contract", suites=("pytest",), descriptions=(),
        selectors=(("pytest", tuple(selectors)),), dependencies=(), required_gates=())
    module = next(step for step in build_module_steps(plan, ROOT) if step.label == "module pytest")
    assert focused.command[-3:] == module.command[-3:] == expected
    assert Counter(expected) == Counter(selectors)


def test_full_workers_keep_existing_assignment_and_contiguous_file_invariant():
    files = ["tests/pkg/test_z.py", "tests/pkg/nested/test_a.py", "tests/pkg_extra/test_b.py",
        "tests/pkg/nested/test_b.py", "tests/pkg/test_a.py", "tests/test_root.py"]
    cases = [f"{path}::test_{i}" for i, path in enumerate(files)]
    assignments = RUNNER.partition_test_files(cases)
    assert Counter(path for worker in assignments for path in worker) == Counter(files)
    for worker in assignments:
        assert worker == tuple(sorted(worker))
        assert_ancestor_branches_contiguous(worker, ROOT)


def test_real_native_minimal_collection_keeps_all_eight_job_fixtures_visible():
    selectors = ["tests/backend_core/test_runtime_recovery.py", "tests/test_authored_route_timing.py",
        "tests/backend_core/test_jobs.py"]
    ordered = order_pytest_selectors(selectors, root=ROOT)
    program = '''
import json,sys,pytest
class Probe:
    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self,items):
        jobs=[item for item in items if item.path.name=='test_jobs.py']
        print('FIXTURE_VISIBILITY '+json.dumps({
            'cases':[item.nodeid for item in jobs],
            'visible':[bool(item._fixtureinfo.name2fixturedefs.get('project_store')) for item in jobs]}))
raise SystemExit(pytest.main(['--collect-only','-q','-s',*json.loads(sys.argv[1])],plugins=[Probe()]))
'''
    result = subprocess.run([sys.executable, "-c", program, json.dumps(ordered)], cwd=ROOT,
        env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    facts = json.loads(next(line.removeprefix("FIXTURE_VISIBILITY ") for line in result.stdout.splitlines()
        if line.startswith("FIXTURE_VISIBILITY ")))
    assert len(facts["cases"]) == 8 and len(set(facts["cases"])) == 8
    assert facts["visible"] == [True] * 8
