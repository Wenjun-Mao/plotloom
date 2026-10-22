"""Worker success is an exact case-ID proof, not an exit-code/count estimate."""

from types import SimpleNamespace

import pytest

from scripts.testing.python_suite_completion import (
    RUN_MARKER, CompletionError, validate_worker_completion,
)
from scripts.testing.python_suite_schedule import native_case_fingerprint
from scripts.testing.python_suite_timing_plugin import FilePhaseTotals
from tests.python_suite_runner_support import completion_proof

CASES = ("tests/test_a.py::test_a[first]", "tests/test_a.py::test_a[second]")


def proof(cases=CASES, **changes):
    return completion_proof(cases, **changes)


def test_exact_proof_is_order_independent_but_not_count_only():
    assert validate_worker_completion(proof(), tuple(reversed(CASES))) == native_case_fingerprint(CASES)
    changed = (CASES[0], "tests/test_a.py::test_a[different]")
    with pytest.raises(CompletionError, match="case IDs differ"):
        validate_worker_completion(proof(changed), CASES)


@pytest.mark.parametrize("text", ["", "ordinary report", proof() + "\n" + proof(), RUN_MARKER + "{", RUN_MARKER + "[]"])
def test_missing_duplicate_or_malformed_marker_is_refused(text):
    with pytest.raises(CompletionError):
        validate_worker_completion(text, CASES)


@pytest.mark.parametrize("changes", [
    {"complete": False}, {"complete": 1}, {"exitstatus": 1}, {"exitstatus": False},
    {"files": 2}, {"case_count": 1}, {"case_count": 2.0},
    {"schema_version": 0}, {"native_case_ids_sha256": "0" * 64}, {"extra": "not supported"},
])
def test_incomplete_or_wrong_contract_cannot_qualify(changes):
    with pytest.raises(CompletionError):
        validate_worker_completion(proof(**changes), CASES)


def test_duplicate_json_keys_and_nonfinite_numbers_are_refused():
    for text in (proof().replace('"complete": true', '"complete": false, "complete": true'),
                 proof().replace('"case_count": 2', '"case_count": NaN')):
        with pytest.raises(CompletionError):
            validate_worker_completion(text, CASES)


@pytest.mark.parametrize("cases", [(), (CASES[0], CASES[0])])
def test_coordinator_assignment_itself_must_be_nonempty_and_unique(cases):
    with pytest.raises(CompletionError, match="nonempty and unique"):
        validate_worker_completion(proof(), cases)


@pytest.mark.parametrize("mode", ["complete", "missing", "extra", "duplicate-collection", "failed"])
def test_plugin_proof_binds_observed_and_unique_collected_cases(capsys, mode):
    plugin = FilePhaseTotals()
    collected = CASES + (CASES[0],) if mode == "duplicate-collection" else CASES
    plugin.pytest_collection_finish(SimpleNamespace(items=[SimpleNamespace(nodeid=case) for case in collected]))
    observed = CASES[:1] if mode == "missing" else CASES
    if mode == "extra":
        observed += ("tests/test_a.py::test_extra",)
    for case in observed:
        plugin.pytest_runtest_logreport(SimpleNamespace(nodeid=case, when="call", duration=0.1))
    print(". [100%]", end="")
    plugin.pytest_sessionfinish(SimpleNamespace(), 1 if mode == "failed" else 0)
    output = capsys.readouterr().out
    if mode == "complete":
        assert validate_worker_completion(output, CASES) == native_case_fingerprint(CASES)
        assert "PYTHON_SUITE_FILE_TIMING" in output
    else:
        with pytest.raises(CompletionError):
            validate_worker_completion(output, CASES)
        assert "PYTHON_SUITE_FILE_TIMING" not in output
