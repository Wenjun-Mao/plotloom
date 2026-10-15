"""Duration predictions cannot own current test selection or qualify a run."""

from copy import deepcopy
import json

import pytest

from scripts.testing import python_suite_schedule as scheduler


def _cases(counts):
    return [f"tests/test_{name}.py::test_{index}" for name, count in counts.items() for index in range(count)]


def _manifest(counts, seconds):
    return {
        "schema_version": 1,
        "native_case_ids_sha256": scheduler.native_case_fingerprint(_cases(counts)),
        "input_fingerprint": "a" * 64,
        "host_fingerprint": "b" * 64,
        "files": [
            {"path": f"tests/test_{name}.py", "case_count": count,
             "setup_seconds": 0, "call_seconds": seconds[name], "teardown_seconds": 0}
            for name, count in counts.items()
        ],
    }


@pytest.fixture(autouse=True)
def fixed_provenance(monkeypatch):
    monkeypatch.setattr(scheduler, "input_fingerprint", lambda _root: "a" * 64)
    monkeypatch.setattr(scheduler, "host_fingerprint", lambda: "b" * 64)


def _schedule(tmp_path, manifest, counts, workers=2):
    return scheduler.schedule_from_timing_text(
        None if manifest is None else json.dumps(manifest),
        cases=_cases(counts), root=tmp_path, worker_count=workers,
    )


def test_exact_manifest_retains_duration_and_balanced_deterministic_plan(tmp_path):
    counts = {"a": 3, "b": 2, "c": 1, "d": 1}
    value = _manifest(counts, {"a": 90, "b": 80, "c": 10, "d": 10})
    # Phase totals, not only calls, own the weight.
    value["files"][0].update(setup_seconds=10, call_seconds=70, teardown_seconds=10)
    plan = _schedule(tmp_path, value, counts)
    assert plan.basis == "duration" and plan.fallback_reason is None and plan.history is None
    assert plan.assignments == (
        ("tests/test_a.py", "tests/test_d.py"),
        ("tests/test_b.py", "tests/test_c.py"),
    )
    assert _schedule(tmp_path, value, counts) == plan


@pytest.mark.parametrize("key,reason", [
    ("input_fingerprint", "executable-inputs-changed"),
    ("native_case_ids_sha256", "native-case-inventory-changed"),
])
def test_changed_source_or_equal_count_case_ids_are_only_historical(tmp_path, key, reason):
    counts = {"a": 1, "b": 1}
    value = _manifest(counts, {"a": 9, "b": 2})
    value[key] = "e" * 64
    original = deepcopy(value)
    plan = _schedule(tmp_path, value, counts)
    assert plan.basis == "historical-duration" and plan.fallback_reason is None
    assert plan.history == scheduler.HistoricalPrediction((reason,), 2, 0, 0, 0)
    assert value == original


def test_changed_new_and_removed_files_use_scaled_and_overlap_median_predictions(tmp_path, monkeypatch):
    value = _manifest({"a": 2, "b": 4, "gone": 1}, {"a": 20, "b": 80, "gone": 10000})
    value["input_fingerprint"] = "e" * 64
    predicted = {}
    partition = scheduler._duration_partition

    def observe(weights, workers):
        predicted.update(weights)
        return partition(weights, workers)

    monkeypatch.setattr(scheduler, "_duration_partition", observe)
    counts = {"a": 4, "b": 2, "new": 3}
    plan = _schedule(tmp_path, value, counts)
    assert predicted == {"tests/test_a.py": 40, "tests/test_b.py": 40, "tests/test_new.py": 45}
    assert plan.history == scheduler.HistoricalPrediction(
        ("native-case-inventory-changed", "executable-inputs-changed",
         "timing-file-coverage-changed", "timing-case-counts-changed"), 0, 2, 1, 1,
    )
    assert plan.basis == "historical-duration"
    assert set(path for group in plan.assignments for path in group) == set(predicted)


@pytest.mark.parametrize("workers", [2, 4, 8])
def test_historical_plan_is_order_independent_and_an_exact_current_cover(tmp_path, workers):
    old = {str(index): 1 for index in range(10)}
    value = _manifest(old, {name: float(int(name) + 1) for name in old})
    counts = {str(index): 2 for index in range(1, 11)}
    plan = _schedule(tmp_path, value, counts, workers)
    value["files"].reverse()
    assert _schedule(tmp_path, value, dict(reversed(list(counts.items()))), workers) == plan
    assigned = [path for group in plan.assignments for path in group]
    assert all(plan.assignments) and len(assigned) == len(set(assigned)) == len(counts)
    assert set(assigned) == {f"tests/test_{name}.py" for name in counts}


@pytest.mark.parametrize("kind,reason", [
    ("missing", "timing-manifest-missing"), ("empty", "timing-history-empty"),
    ("no-overlap", "timing-history-no-overlap"), ("host-drift", "host-or-python-changed"),
])
def test_unusable_history_explicitly_falls_back_to_complete_counts(tmp_path, kind, reason):
    counts = {"a": 3, "b": 2, "c": 1}
    value = _manifest({"gone": 1}, {"gone": 8})
    if kind == "missing":
        value = None
    elif kind == "empty":
        value["files"] = []
    elif kind == "host-drift":
        value["host_fingerprint"] = "e" * 64
        value["input_fingerprint"] = "f" * 64
    plan = _schedule(tmp_path, value, counts)
    assert plan.basis == "case-count" and plan.fallback_reason == reason and plan.history is None
    assert plan.assignments == _schedule(tmp_path, None, counts).assignments


@pytest.mark.parametrize("defect", [
    "fields", "schema", "fingerprint", "rows", "row-fields", "path", "duplicate",
    "bool-count", "zero-count", "bool-phase", "negative", "nonfinite", "empty-phase",
    "row-overflow", "integer-overflow", "suite-overflow",
])
@pytest.mark.parametrize("stale", [False, True])
def test_malformed_history_is_rejected_even_if_removed_or_on_another_host(tmp_path, defect, stale):
    counts = {"a": 1, "b": 1}
    value = _manifest(counts, {"a": 2, "b": 3})
    row = value["files"][0]
    if stale:
        row["path"] = "tests/test_removed.py"
        value["host_fingerprint"] = "e" * 64
    if defect == "fields": value["extra"] = 1
    elif defect == "schema": value["schema_version"] = True
    elif defect == "fingerprint": value["input_fingerprint"] = "bad"
    elif defect == "rows": value["files"] = {}
    elif defect == "row-fields": row["extra"] = 1
    elif defect == "path": row["path"] = "tests/../outside.py"
    elif defect == "duplicate": value["files"].append(dict(row))
    elif defect == "bool-count": row["case_count"] = True
    elif defect == "zero-count": row["case_count"] = 0
    elif defect == "bool-phase": row["call_seconds"] = True
    elif defect == "negative": row["call_seconds"] = -1
    elif defect == "nonfinite": row["call_seconds"] = float("inf")
    elif defect == "empty-phase": row["call_seconds"] = 0
    elif defect == "row-overflow": row.update(setup_seconds=1e308, call_seconds=1e308)
    elif defect == "integer-overflow": row["call_seconds"] = 10**1000
    elif defect == "suite-overflow":
        for item in value["files"]: item["call_seconds"] = 1e308
    with pytest.raises(scheduler.TimingManifestError):
        _schedule(tmp_path, value, counts)


@pytest.mark.parametrize("text", ["{", '{"schema_version":1,"schema_version":1}'])
def test_invalid_json_or_duplicate_keys_fail(tmp_path, text):
    with pytest.raises(scheduler.TimingManifestError, match="invalid timing manifest JSON"):
        scheduler.schedule_from_timing_text(text, cases=_cases({"a": 1, "b": 1}), root=tmp_path)


@pytest.mark.parametrize("kind", ["scaled-overflow", "estimated-overflow", "aggregate-overflow", "underflow", "huge-count"])
def test_nonpositive_or_nonfinite_derived_predictions_fail(tmp_path, kind):
    value = _manifest({"a": 1, "b": 1}, {"a": 8e307, "b": 8e307})
    counts = {"a": 1, "b": 1}
    if kind == "scaled-overflow": counts["a"] = 3
    elif kind == "estimated-overflow": counts["new"] = 3
    elif kind == "aggregate-overflow": counts["new"] = 1
    elif kind == "underflow":
        value["files"][0].update(case_count=2, call_seconds=5e-324)
    elif kind == "huge-count":
        value["files"][0]["case_count"] = 10**1000
    with pytest.raises(scheduler.TimingManifestError):
        _schedule(tmp_path, value, counts)


def test_partial_history_estimates_unrecorded_current_file_and_handles_odd_median(tmp_path, monkeypatch):
    counts = {"a": 1, "b": 1, "c": 1, "new": 2}
    value = _manifest(counts, {"a": 4, "b": 6, "c": 100, "new": 10})
    value["files"].pop()
    observed = {}
    partition = scheduler._duration_partition

    def observe(weights, workers):
        observed.update(weights)
        return partition(weights, workers)

    monkeypatch.setattr(scheduler, "_duration_partition", observe)
    plan = _schedule(tmp_path, value, counts)
    assert observed["tests/test_new.py"] == 12
    assert plan.history.retained == 3 and plan.history.estimated == 1
