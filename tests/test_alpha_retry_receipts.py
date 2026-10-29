"""Provider-free synthetic record shapes exercise actual collector accounting."""
from types import SimpleNamespace

import pytest

from plotloom.alpha_receipts import collect_native_evidence
from plotloom.alpha_workloads import SAMPLE_KEYS


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
@pytest.mark.parametrize("corrected", [False, True])
def test_collector_accepts_exact_adopted_retry_and_counts_failed_predecessors(stage, corrected):
    checkpoints, records, lookups = [], {}, []
    snapshot = {"profileHash": "a" * 64, "commit": "b" * 40}

    def record(key, state, *, ordinal=0, retry=False):
        evidence = {"owner": stage, "result": {}}
        if ordinal:
            evidence["result"]["correctionOrdinal"] = ordinal
        if retry:
            evidence["result"]["executionRetry"] = {"ordinal": 1}
        checkpoints.append({"operationKey": key, "state": state, "evidence": evidence})
        attempt = {"state": "completed" if state in {"adopted", "delivered"} else "failed", "operationKey": key}
        receipt = {"textValidation": {"synthetic": True}, "processExitCode": 0,
            "profileHash": snapshot["profileHash"], "plotloomCodeRevision": snapshot["commit"]}
        records[key] = (SimpleNamespace(model_dump=lambda **_kwargs: dict(attempt)),
            SimpleNamespace(model_dump=lambda **_kwargs: dict(receipt)) if state != "failed" else None)

    if corrected:
        record(stage, "delivered")
    root = stage + ":correction:1" if corrected else stage
    record(root, "failed", ordinal=int(corrected))
    record(root + ":retry:1", "adopted", ordinal=int(corrected), retry=True)

    def exact_lookup(run_id, operation_key):
        lookups.append((run_id, operation_key))
        return records[operation_key]

    store = SimpleNamespace(repository=SimpleNamespace(autopilot=SimpleNamespace(
        exec_attempt_evidence_for_operation=exact_lookup)))
    view = SimpleNamespace(id="synthetic-run", state="running", blocker=None, checkpoints=checkpoints,
        model_dump=lambda **_kwargs: {"synthetic": True})
    receipt, private = collect_native_evidence(store, view, snapshot=snapshot,
        contract_hash="c" * 64, sample_id=next(iter(SAMPLE_KEYS)), duration_ms=1)
    result = next(item for item in receipt.operations if item.stage == stage)
    assert result.accepted and not result.first_pass
    assert result.attempt_count == (3 if corrected else 2)
    assert lookups == [(view.id, item["operationKey"]) for item in checkpoints]
    assert [item["checkpoint"]["operationKey"] for item in private["operations"][stage]] == [item["operationKey"] for item in checkpoints]
