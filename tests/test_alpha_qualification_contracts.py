"""Current native operation arithmetic and closed qualification receipts."""
import json
from copy import deepcopy
import pytest
from plotloom import alpha_reviews, alpha_review_contracts
from plotloom.alpha_receipts import NativeSampleReceipt, native_qualification_issue_codes
from plotloom.alpha_workloads import SAMPLE_KEYS, NATIVE_OPERATIONS
from tests.alpha_acceptance_support import _review_pack, _external_review, native_receipts

def test_external_engineering_review_is_not_a_product_approval_or_human_acceptance() -> None:
    pack = _review_pack()
    reviews = [_external_review(sample) for sample in pack.samples]
    receipt = alpha_reviews.codex_external_review_receipt(
        reviews, review_pack=pack
    ).model_dump(mode="json", by_alias=True)

    assert set(receipt) == {
        "receipt",
        "commit",
        "contractHash",
        "rubricVersion",
        "reviewer",
        "reviews",
        "gate",
    }
    assert receipt["receipt"] == "codex_external_review"
    serialized = json.dumps(receipt).lower()
    for forbidden in ("approval", "human", "acceptance", "profile", "story", "run", "prompt"):
        assert forbidden not in serialized

    different_pack = alpha_review_contracts.ReviewPackManifest(
        commit="c" * 40,
        contract_hash=pack.contract_hash,
        samples=pack.samples,
    )
    gate = alpha_reviews.codex_external_review_gate(
        reviews, review_pack=different_pack
    )
    rebound_receipt = alpha_reviews.codex_external_review_receipt(
        reviews, review_pack=different_pack
    )
    assert gate.commit == different_pack.commit
    assert "codex_external_review.commit_identity" in gate.issue_codes
    assert rebound_receipt.commit == different_pack.commit
    assert rebound_receipt.gate.passed is False




def test_native_exact_nine_and_sixty_of_seventy_two_boundary():
    assert native_qualification_issue_codes(native_receipts(60)) == []
    assert native_qualification_issue_codes(native_receipts(59)) == ["alpha.first_pass"]
    rows = native_receipts()
    assert sum(len(row["operations"]) for row in rows) == 72
    assert "alpha.sample_matrix" in native_qualification_issue_codes(rows[:-1])
    assert "alpha.sample_matrix" in native_qualification_issue_codes(rows[:-1] + [rows[0]])
    assert "alpha.sample_matrix" in native_qualification_issue_codes(rows * 2)


@pytest.mark.parametrize("change", ["legacy-version", "retired-native-v2", "secret", "float", "extra-stage", "expanded-retry", "false-install", "identity"])
def test_native_receipts_reject_legacy_secret_or_fabricated_accounting(change):
    rows = native_receipts()
    row = rows[0]
    if change == "legacy-version": row["version"] = "alpha_chinese_three_story.v1"
    if change == "retired-native-v2": row["version"] = "alpha_native_codex_three_story.v2"
    if change == "secret": row["apiKey"] = "secret-marker"
    if change == "float": row["operations"][0]["attemptCount"] = 1.0
    if change == "extra-stage": row["operations"].append(deepcopy(row["operations"][0]))
    if change == "expanded-retry": row["operations"][1]["attemptCount"] = 2
    if change == "false-install": row["operations"][0].update(accepted=False, firstPass=False)
    if change == "identity": row["sampleId"] = "legacy-profile-story-01"
    assert "alpha.receipt.schema" in native_qualification_issue_codes(rows)


def test_native_gate_preserves_unknown_and_rejects_mixed_execution_inputs():
    rows = native_receipts()
    rows[0].update(status="outcome_unknown", installationHash=None, issueCodes=["codex_exec_outcome_unknown"])
    assert "alpha.installation" in native_qualification_issue_codes(rows)
    rows[1]["profileHash"] = "f" * 64
    assert "alpha.execution_identity" in native_qualification_issue_codes(rows)
