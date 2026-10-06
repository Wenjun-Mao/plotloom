"""The one-time operator must follow actual gateway states without replay."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def canary():
    path = Path(__file__).resolve().parents[3] / "services/minimax_h3_gateway/tools/vae_adoption/canary.py"
    spec = importlib.util.spec_from_file_location("vae_canary_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gateway_terminal_state_is_succeeded_not_completed(canary):
    assert canary.succeeded({"status": "succeeded"})
    assert not canary.succeeded({"status": "completed"})
    assert not canary.succeeded({"status": "running"})


@pytest.mark.parametrize("state", ["outcome_unknown", "failed", "request_rejected", "passed"])
def test_unknown_or_failed_claims_cannot_be_reconciled(canary, tmp_path, state):
    path = tmp_path / "canaries.json"
    path.write_text(json.dumps({"status": "running", "cap": 2, "casesHash": canary.CASES_HASH,
                               "calls": [{"case": "portrait", "state": state, "jobId": "h3_test"}]}))
    with pytest.raises(RuntimeError, match="acknowledged accepted"):
        canary.existing_receipt(path, True)
    with pytest.raises(RuntimeError, match="no replay"):
        canary.existing_receipt(path, False)


def test_acknowledged_claim_is_preserved_for_get_only_reconciliation(canary, tmp_path):
    path = tmp_path / "canaries.json"
    value = {"status": "running", "cap": 2, "casesHash": canary.CASES_HASH,
             "calls": [{"case": "portrait", "state": "accepted", "jobId": "h3_original"}]}
    path.write_text(json.dumps(value))
    assert canary.existing_receipt(path, True) == value


@pytest.mark.parametrize("count", [1, 2])
def test_stopped_observer_requires_both_claims_acknowledged_and_no_post_remaining(canary, tmp_path, count):
    path = tmp_path / "canaries.json"
    calls = [{"case": "portrait", "state": "passed", "jobId": "h3_first"},
             {"case": "voice", "state": "accepted", "jobId": "h3_second"}]
    value = {"status": "stopped", "errorType": "ConnectionError", "cap": 2,
             "casesHash": canary.CASES_HASH, "calls": calls[:count]}
    path.write_text(json.dumps(value))
    if count == 2:
        assert canary.existing_receipt(path, True) == value
    else:
        with pytest.raises(RuntimeError, match="acknowledged accepted"):
            canary.existing_receipt(path, True)
