"""Current native blind review: schema, exact hashes and unchanged quality policy."""
import json
from pathlib import Path
import pytest
from plotloom import alpha_reviews, alpha_publication, alpha_review_contracts
from tests.alpha_acceptance_support import _review_pack, _external_review

def test_external_review_gate_requires_the_full_secret_free_frozen_pack(
    tmp_path: Path,
) -> None:
    pack = _review_pack()
    approved = [_external_review(manifest) for manifest in pack.samples]
    assert alpha_reviews.codex_external_review_gate(
        approved, review_pack=pack
    ).passed

    rejected = [dict(review) for review in approved]
    rejected[0]["fatalContradiction"] = True
    rejected[1]["scores"] = {**rejected[1]["scores"], "continuity": 2}
    gate = alpha_reviews.codex_external_review_gate(rejected, review_pack=pack)
    assert not gate.passed
    assert gate.issue_codes == (
        "codex_external_review.fatal_contradiction",
        "codex_external_review.score_floor",
    )

    mapping_path = tmp_path / "review-mapping.private.json"
    mapping_path.write_text(
        json.dumps(
            {
                "version": "alpha_native_review_mapping.v1",
                "commit": pack.commit,
                "contractHash": pack.contract_hash,
                "reviewCount": 3,
                "entries": [
                    {
                        "reviewId": sample.review_id,
                        "storyId": "story-01",
                        "sampleId": "story-01-repeat-01",
                        "contentHash": sample.content_hash,
                    }
                    for sample in pack.samples
                ],
            }
        ),
        encoding="utf-8",
    )
    mapping_path.chmod(0o600)
    assert alpha_publication.load_private_review_manifest(mapping_path) == pack

def test_external_review_gate_rejects_malformed_sheets_and_frozen_identity_mismatches() -> None:
    pack = _review_pack()
    approved = [_external_review(manifest) for manifest in pack.samples]

    malformed = [dict(review) for review in approved]
    malformed[0]["reviewerComment"] = "Untrusted prose must not cross the receipt boundary."
    malformed[1]["scores"] = {
        **malformed[1]["scores"],
        "continuity": 4.0,
    }
    malformed_gate = alpha_reviews.codex_external_review_gate(
        malformed, review_pack=pack
    )
    assert {
        "codex_external_review.schema",
        "codex_external_review.count",
        "codex_external_review.identity",
    } <= set(malformed_gate.issue_codes)

    mismatched = [dict(review) for review in approved]
    mismatched[0]["commit"] = "c" * 40
    mismatched[1]["contractHash"] = "d" * 64
    mismatched[2]["contentHash"] = "e" * 64
    mismatched[2]["reviewId"] = approved[1]["reviewId"]
    mismatch_gate = alpha_reviews.codex_external_review_gate(
        mismatched, review_pack=pack
    )
    assert {
        "codex_external_review.commit_identity",
        "codex_external_review.contract_identity",
        "codex_external_review.content_identity",
        "codex_external_review.identity",
    } <= set(mismatch_gate.issue_codes)

def test_external_review_gate_enforces_quality_thresholds_and_full_manifest() -> None:
    pack = _review_pack()
    low_quality = [_external_review(manifest, score=3) for manifest in pack.samples]
    quality_gate = alpha_reviews.codex_external_review_gate(
        low_quality, review_pack=pack
    )
    assert {
        "codex_external_review.sample_average",
        "codex_external_review.dimension_median",
    } <= set(quality_gate.issue_codes)

    all_samples = pack.samples + (
        alpha_review_contracts.ReviewSampleManifest(
            review_id=f"review-{7:032x}", content_hash=f"{7:064x}"
        ),
    )
    for count in (0, 1, 2, 4):
        incomplete_pack = alpha_review_contracts.ReviewPackManifest(
            commit=pack.commit,
            contract_hash=pack.contract_hash,
            samples=all_samples[:count],
        )
        manifest_gate = alpha_reviews.codex_external_review_gate(
            [_external_review(manifest) for manifest in incomplete_pack.samples],
            review_pack=incomplete_pack,
        )
        assert manifest_gate.passed is False
        assert manifest_gate.expected_review_count == 3
        assert {
            "codex_external_review.expected_manifest_count",
            "codex_external_review.count",
        } <= set(manifest_gate.issue_codes)

def test_external_review_receipt_filters_invalid_sheets_and_private_mapping_rejects_partial_pack(
    tmp_path: Path,
) -> None:
    pack = _review_pack()
    reviews = [_external_review(manifest) for manifest in pack.samples]
    reviews[0]["reviewerComment"] = "Untrusted prose must not be persisted."

    receipt = alpha_reviews.codex_external_review_receipt(reviews, review_pack=pack)
    serialized = receipt.model_dump_json(by_alias=True)
    assert len(receipt.reviews) == 2
    assert "Untrusted prose" not in serialized
    assert "reviewerComment" not in serialized
    assert "codex_external_review.schema" in receipt.gate.issue_codes

    mapping_path = tmp_path / "partial-review-mapping.private.json"
    mapping_path.write_text(
        json.dumps(
            {
                "version": "alpha_native_review_mapping.v1",
                "commit": pack.commit,
                "contractHash": pack.contract_hash,
                "reviewCount": 3,
                "entries": [
                    {
                        "reviewId": sample.review_id,
                        "storyId": "story-01",
                        "sampleId": "story-01-repeat-01",
                        "contentHash": sample.content_hash,
                    }
                    for sample in pack.samples[:-1]
                ],
            }
        ),
        encoding="utf-8",
    )
    mapping_path.chmod(0o600)
    with pytest.raises(ValueError, match="all three native Alpha samples"):
        alpha_publication.load_private_review_manifest(mapping_path)
