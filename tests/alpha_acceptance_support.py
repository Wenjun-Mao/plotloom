"""Non-collected blinded-review builders; no provider execution fixtures."""
from plotloom import alpha_review_contracts

def _review_manifests() -> tuple[alpha_review_contracts.ReviewSampleManifest, ...]:
    return tuple(
        alpha_review_contracts.ReviewSampleManifest(
            review_id=f"review-{ordinal:032x}", content_hash=f"{ordinal:064x}"
        )
        for ordinal in range(1, 4)
    )

def _review_pack() -> alpha_review_contracts.ReviewPackManifest:
    return alpha_review_contracts.ReviewPackManifest(
        commit="a" * 40,
        contract_hash="b" * 64,
        samples=_review_manifests(),
    )

def _external_review(
    manifest: alpha_review_contracts.ReviewSampleManifest, *, fatal: bool = False, score: int = 4
) -> dict[str, object]:
    return {
        "commit": "a" * 40,
        "contractHash": "b" * 64,
        "reviewId": manifest.review_id,
        "contentHash": manifest.content_hash,
        "rubricVersion": "m1c_authoring_quality.v1",
        "reviewer": "codex_external_review",
        "scores": {
            "narrativeClarity": score,
            "branchCausality": score,
            "continuity": score,
            "performanceReadability": score,
            "shotLanguage": score,
            "pacingAndEditCost": score,
        },
        "fatalContradiction": fatal,
    }


from plotloom.alpha_workloads import SAMPLE_KEYS, NATIVE_OPERATIONS

def native_receipts(first_pass=72):
    rows = []
    for index, sample_id in enumerate(SAMPLE_KEYS):
        operations = []
        for stage_index, stage in enumerate(NATIVE_OPERATIONS):
            # Corrections only on the production allowlist; select the earliest
            # eligible slots to place the exact requested failures.
            eligible = stage in {"outline", "characters", "art"}
            corrected = eligible and first_pass < 72
            if corrected:
                first_pass += 1
            operations.append({"stage": stage, "attemptCount": 2 if corrected else 1,
                "accepted": True, "firstPass": not corrected, "bindingHash": "e" * 64})
        rows.append({"version": "alpha_native_codex_three_story.v3", "commit": "a" * 40,
            "contractHash": "b" * 64, "profileHash": "c" * 64, "sampleId": sample_id,
            "status": "installed", "operations": operations, "installationHash": "d" * 64, "contentHash": "f" * 64,
            "durationMilliseconds": 0, "issueCodes": []})
    return rows
