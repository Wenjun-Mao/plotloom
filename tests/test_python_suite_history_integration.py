"""Real native workers treat old timings as predictions, never case authority."""

import json
import os
from pathlib import Path
from textwrap import dedent

import pytest

from scripts.testing import python_suite_schedule as scheduler
from tests.python_suite_runner_support import RUNNER


def _write(root, relative, body):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(body), encoding="utf-8")


def _historical_fixture(root):
    old_cases = (
        "tests/test_a.py::test_case[legacy]",
        "tests/test_b.py::test_case[0]",
        "tests/test_removed.py::test_case",
    )
    # Synthetic weights exercise scheduling; they are not captured performance.
    value = {
        "schema_version": 1,
        "native_case_ids_sha256": scheduler.native_case_fingerprint(old_cases),
        "input_fingerprint": scheduler.input_fingerprint(root),
        "host_fingerprint": scheduler.host_fingerprint(),
        "files": [
            {"path": case.split("::", 1)[0], "case_count": 1,
             "setup_seconds": 1, "call_seconds": 2, "teardown_seconds": 1}
            for case in old_cases
        ],
    }
    path = root / "scripts/testing/python_suite_timings.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


@pytest.mark.skipif(os.name != "posix", reason="qualified owned process groups are POSIX")
@pytest.mark.parametrize("old_worker_ids", [False, True], ids=["fresh-ids", "old-worker-ids"])
def test_real_runner_reports_history_and_requires_current_worker_case_ids(
    tmp_path, capsys, old_worker_ids,
):
    manifest = _historical_fixture(tmp_path)
    retained_provenance = manifest.read_bytes()
    _write(tmp_path, "tests/test_a.py", """
        def test_case(label):
            assert label in {'current', 'legacy'}
    """)
    _write(tmp_path, "tests/test_b.py", """
        import pytest
        @pytest.mark.parametrize('value', [0, 1])
        def test_case(value):
            assert value in {0, 1}
    """)
    _write(tmp_path, "tests/test_new.py", """
        def test_case():
            assert True
    """)
    # The negative case deliberately gives a real successful worker the old
    # equal-count ID. Its own proof is valid, but not for the current assignment.
    _write(tmp_path, "conftest.py", f"""
        def pytest_generate_tests(metafunc):
            if 'label' in metafunc.fixturenames:
                old_worker = {old_worker_ids!r} and not metafunc.config.option.collectonly
                metafunc.parametrize('label', ['legacy' if old_worker else 'current'])
    """)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(RUNNER.ROOT), str(RUNNER.ROOT / "src")))
    result = RUNNER.run_python_suite(root=tmp_path, environment=environment)
    output = capsys.readouterr().out
    assert result == (1 if old_worker_ids else 0), output
    assert "native_cases=4 files=3 workers=2" in output
    assert "schedule=historical-duration" in output
    assert (
        "changes=native-case-inventory-changed,executable-inputs-changed,"
        "timing-file-coverage-changed,timing-case-counts-changed "
        "retained=1 scaled=1 estimated=1 ignored=1"
    ) in output
    current_cases = (
        "tests/test_a.py::test_case[current]",
        "tests/test_b.py::test_case[0]",
        "tests/test_b.py::test_case[1]",
        "tests/test_new.py::test_case",
    )
    assert f"native_case_ids_sha256={scheduler.native_case_fingerprint(current_cases)}" in output
    assert output.count("[python-suite] COMPLETE worker=") == (1 if old_worker_ids else 2)
    if old_worker_ids:
        assert "completion: worker native case IDs differ from the coordinator assignment" in output
    else:
        assert "[python-suite] REFUSED" not in output
    assert "tests/test_removed.py" not in output
    basetemps = [
        Path(line.split("basetemp=", 1)[1]) for line in output.splitlines()
        if line.startswith("[python-suite] START ")
    ]
    assert len(set(basetemps)) == 2
    assert all(not path.parent.exists() for path in basetemps)
    assert manifest.read_bytes() == retained_provenance
