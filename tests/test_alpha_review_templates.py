from __future__ import annotations

import json
from pathlib import Path

import pytest

from plotloom import alpha_acceptance
from plotloom.alpha_review_templates import (
    CodexExternalReviewTemplate,
    build_codex_external_review_template,
    score_sheet_path,
    write_codex_external_review_templates,
)


def _review_pack() -> alpha_acceptance.ReviewPackManifest:
    return alpha_acceptance.ReviewPackManifest(
        commit="a" * 40,
        contract_hash="b" * 64,
        samples=tuple(
            alpha_acceptance.ReviewSampleManifest(
                review_id=f"review-{ordinal:032x}",
                content_hash=f"{ordinal:064x}",
            )
            for ordinal in range(1, 7)
        ),
    )


def test_public_score_sheet_draft_is_closed_prefilled_and_editable(tmp_path: Path) -> None:
    pack = _review_pack()
    sample = pack.samples[0]
    paths = write_codex_external_review_templates(
        tmp_path,
        ((item.review_id, item.content_hash) for item in pack.samples),
        commit=pack.commit,
        contract_hash=pack.contract_hash,
    )

    assert paths == tuple(score_sheet_path(tmp_path, item.review_id) for item in pack.samples)
    draft = json.loads(paths[0].read_text(encoding="utf-8"))
    assert CodexExternalReviewTemplate.model_validate(draft).review_id == sample.review_id
    assert draft == build_codex_external_review_template(
        commit=pack.commit,
        contract_hash=pack.contract_hash,
        review_id=sample.review_id,
        content_hash=sample.content_hash,
    )
    assert draft["scores"] == {
        "narrativeClarity": 0,
        "branchCausality": 0,
        "continuity": 0,
        "performanceReadability": 0,
        "shotLanguage": 0,
        "pacingAndEditCost": 0,
    }
    assert draft["fatalContradiction"] == "PENDING"
    sheet_text = paths[0].read_text(encoding="utf-8")
    for forbidden in ("profile", "story", "sample", "provider", "run", "prompt", "response"):
        assert forbidden not in sheet_text


def test_external_review_receipt_strictly_rejects_an_unfilled_public_draft() -> None:
    pack = _review_pack()
    sample = pack.samples[0]
    draft = build_codex_external_review_template(
        commit=pack.commit,
        contract_hash=pack.contract_hash,
        review_id=sample.review_id,
        content_hash=sample.content_hash,
    )

    with pytest.raises(ValueError, match="unfilled Codex external review template"):
        alpha_acceptance.codex_external_review_receipt((draft,), review_pack=pack)

    partially_filled = {
        **draft,
        "fatalContradiction": False,
        "scores": {**draft["scores"], "narrativeClarity": 4},
    }
    with pytest.raises(ValueError, match="unfilled Codex external review template"):
        alpha_acceptance.codex_external_review_receipt((partially_filled,), review_pack=pack)
