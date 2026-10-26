"""Independent content review and secret-free quality-gate receipts."""
from collections.abc import Iterable, Mapping
from typing import Any
from statistics import median
from pydantic import ValidationError
from .alpha_review_contracts import CodexExternalReview, CodexExternalReviewGate, CodexExternalReviewReceipt, ReviewPackManifest
from .alpha_review_templates import (CODEX_EXTERNAL_REVIEW_FIELDS, CODEX_EXTERNAL_REVIEW_RUBRIC_VERSION,
 CODEX_EXTERNAL_REVIEW_SCORE_FIELDS, CODEX_EXTERNAL_REVIEWER, CONTENT_HASH_PATTERN,
 OPAQUE_REVIEW_ID_PATTERN, is_unfilled_codex_external_review_template)
from .alpha_provenance import validate_commit_sha
from .alpha_workloads import ALPHA_EXPECTED_REVIEW_COUNT

def parse_codex_external_review(value: Any) -> CodexExternalReview:
    """Parse one untrusted score sheet through the closed, prose-free schema."""

    if not isinstance(value, Mapping) or set(value) != CODEX_EXTERNAL_REVIEW_FIELDS:
        raise ValueError("codex external review has invalid secret-free shape")
    try:
        return CodexExternalReview.model_validate(value)
    except ValidationError as error:
        # Do not expose arbitrary reviewer-controlled values through errors or
        # logs. The model is closed, so a generic outcome is enough to audit a
        # schema failure with the stable gate code below.
        raise ValueError("codex external review has invalid secret-free shape") from error

def codex_external_review_gate(
    reviews: Iterable[Any],
    *,
    review_pack: ReviewPackManifest,
) -> CodexExternalReviewGate:
    """Aggregate blinded Codex review against the exact three published hashes.

    The returned object intentionally carries no sample text or unblinding
    metadata. Its stable codes make a failed quality gate actionable without
    turning a tracked receipt into a provider/profile/story/run ledger.
    """

    expected = tuple(review_pack.samples)
    issues: set[str] = set()
    try:
        normalized_commit = validate_commit_sha(review_pack.commit)
    except ValueError:
        normalized_commit = ""
        issues.add("codex_external_review.expected_commit")
    contract_hash = review_pack.contract_hash
    if not CONTENT_HASH_PATTERN.fullmatch(contract_hash):
        issues.add("codex_external_review.expected_contract_hash")

    parsed: list[CodexExternalReview] = []
    for value in reviews:
        try:
            parsed.append(parse_codex_external_review(value))
        except ValueError:
            issues.add("codex_external_review.schema")

    expected_by_id = {sample.review_id: sample for sample in expected}
    if len(expected) != ALPHA_EXPECTED_REVIEW_COUNT:
        issues.add("codex_external_review.expected_manifest_count")
    if (
        len(expected_by_id) != len(expected)
        or any(
            not OPAQUE_REVIEW_ID_PATTERN.fullmatch(sample.review_id)
            or not CONTENT_HASH_PATTERN.fullmatch(sample.content_hash)
            for sample in expected
        )
    ):
        issues.add("codex_external_review.expected_manifest")
    if len(parsed) != ALPHA_EXPECTED_REVIEW_COUNT or len(parsed) != len(expected):
        issues.add("codex_external_review.count")
    actual_ids = [review.review_id for review in parsed]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected_by_id):
        issues.add("codex_external_review.identity")
    if any(review.commit != normalized_commit for review in parsed):
        issues.add("codex_external_review.commit_identity")
    if any(review.contract_hash != contract_hash for review in parsed):
        issues.add("codex_external_review.contract_identity")
    if any(
        expected_by_id.get(review.review_id) is None
        or expected_by_id[review.review_id].content_hash != review.content_hash
        for review in parsed
    ):
        issues.add("codex_external_review.content_identity")

    dimension_medians: dict[str, float] = {}
    if (
        len(parsed) == ALPHA_EXPECTED_REVIEW_COUNT
        and len(expected) == ALPHA_EXPECTED_REVIEW_COUNT
    ):
        if any(review.fatal_contradiction for review in parsed):
            issues.add("codex_external_review.fatal_contradiction")
        if any(any(score < 3 for score in review.scores.values()) for review in parsed):
            issues.add("codex_external_review.score_floor")
        if any(
            sum(review.scores.values()) / len(CODEX_EXTERNAL_REVIEW_SCORE_FIELDS) < 3.5
            for review in parsed
        ):
            issues.add("codex_external_review.sample_average")
        for dimension in sorted(CODEX_EXTERNAL_REVIEW_SCORE_FIELDS):
            dimension_medians[dimension] = float(median([
                review.scores[dimension] for review in parsed
            ]))
        if any(value < 4 for value in dimension_medians.values()):
            issues.add("codex_external_review.dimension_median")

    return CodexExternalReviewGate(
        commit=normalized_commit,
        contractHash=(contract_hash if CONTENT_HASH_PATTERN.fullmatch(contract_hash) else ""),
        rubricVersion=CODEX_EXTERNAL_REVIEW_RUBRIC_VERSION,
        reviewer=CODEX_EXTERNAL_REVIEWER,
        reviewCount=len(parsed),
        expectedReviewCount=ALPHA_EXPECTED_REVIEW_COUNT,
        issueCodes=tuple(sorted(issues)),
        passed=not issues,
        dimensionMedians=dimension_medians,
    )

def codex_external_review_receipt(
    reviews: Iterable[Any],
    *,
    review_pack: ReviewPackManifest,
) -> CodexExternalReviewReceipt:
    """Build the only structure authorized for a tracked external-review receipt.

    Malformed raw sheets influence the aggregate through a stable schema issue,
    but are never echoed into the returned receipt. Only score sheets that pass
    the closed, prose-free model can cross this persistence boundary.
    """

    normalized_commit = validate_commit_sha(review_pack.commit)
    contract_hash = review_pack.contract_hash
    if not CONTENT_HASH_PATTERN.fullmatch(contract_hash):
        raise ValueError("invalid contract hash")
    raw_reviews = tuple(reviews)
    if any(is_unfilled_codex_external_review_template(value) for value in raw_reviews):
        raise ValueError("unfilled Codex external review template")
    safe_reviews: list[CodexExternalReview] = []
    for value in raw_reviews:
        try:
            safe_reviews.append(parse_codex_external_review(value))
        except ValueError:
            continue
    gate = codex_external_review_gate(
        raw_reviews,
        review_pack=review_pack,
    )
    return CodexExternalReviewReceipt(
        commit=normalized_commit,
        contractHash=contract_hash,
        rubricVersion=CODEX_EXTERNAL_REVIEW_RUBRIC_VERSION,
        reviewer=CODEX_EXTERNAL_REVIEWER,
        reviews=tuple(safe_reviews),
        gate=gate,
    )
