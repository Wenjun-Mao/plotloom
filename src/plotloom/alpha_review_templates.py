"""Public, blinded score-sheet drafts for Alpha review packs.

This module intentionally knows only the public identity/hash binding needed by
an external reviewer.  It has no path to the private unblinding map or to
generation metadata.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
)

from .generation.prompts import canonical_json


CODEX_EXTERNAL_REVIEWER = "codex_external_review"
CODEX_EXTERNAL_REVIEW_RUBRIC_VERSION = "m1c_authoring_quality.v1"
CodexExternalReviewer = Literal["codex_external_review"]
CodexExternalReviewRubricVersion = Literal["m1c_authoring_quality.v1"]
SCORE_SHEET_SUFFIX = ".score-sheet.json"
PENDING_SCORE = 0
PENDING_FATAL_CONTRADICTION = "PENDING"

# Alpha's public draft and final score sheet deliberately share this one
# contract definition. The final receipt builder imports these values rather
# than maintaining a parallel copy that could quietly drift from the files it
# asks reviewers to edit.
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
CONTENT_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
OPAQUE_REVIEW_ID_PATTERN = re.compile(r"^review-[0-9a-f]{32}$")
CODEX_EXTERNAL_REVIEW_FIELDS = frozenset({
    "commit",
    "contractHash",
    "reviewId",
    "contentHash",
    "rubricVersion",
    "reviewer",
    "scores",
    "fatalContradiction",
})
CODEX_EXTERNAL_REVIEW_SCORE_FIELDS = frozenset({
    "narrativeClarity",
    "branchCausality",
    "continuity",
    "performanceReadability",
    "shotLanguage",
    "pacingAndEditCost",
})


class CodexExternalReviewTemplate(BaseModel):
    """A closed, editable draft that cannot be mistaken for a final review.

    Final reviews use 1--5 integers and a boolean fatal flag.  Drafts reserve
    zero and ``PENDING`` so a reviewer can change only the seven judgement
    values without needing any private provenance.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    commit: str
    contract_hash: str = Field(alias="contractHash")
    review_id: str = Field(alias="reviewId")
    content_hash: str = Field(alias="contentHash")
    rubric_version: CodexExternalReviewRubricVersion = Field(alias="rubricVersion")
    reviewer: CodexExternalReviewer
    scores: dict[str, StrictInt]
    fatal_contradiction: Literal["PENDING"] = Field(alias="fatalContradiction")

    @field_validator("commit")
    @classmethod
    def _validate_commit(cls, value: str) -> str:
        if not COMMIT_SHA_PATTERN.fullmatch(value):
            raise ValueError("invalid commit")
        return value.lower()

    @field_validator("contract_hash", "content_hash")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        if not CONTENT_HASH_PATTERN.fullmatch(value):
            raise ValueError("invalid hash")
        return value

    @field_validator("review_id")
    @classmethod
    def _validate_review_id(cls, value: str) -> str:
        if not OPAQUE_REVIEW_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid opaque review ID")
        return value

    @field_validator("scores")
    @classmethod
    def _validate_pending_scores(cls, value: dict[str, int]) -> dict[str, int]:
        if (
            set(value) != CODEX_EXTERNAL_REVIEW_SCORE_FIELDS
            or any(score != PENDING_SCORE for score in value.values())
        ):
            raise ValueError("draft scores must all be PENDING")
        return dict(value)


def score_sheet_path(review_directory: Path, review_id: str) -> Path:
    """Return the public draft location for one opaque review ID."""

    if not OPAQUE_REVIEW_ID_PATTERN.fullmatch(review_id):
        raise ValueError("score sheet needs an opaque review ID")
    return review_directory / f"{review_id}{SCORE_SHEET_SUFFIX}"


def build_codex_external_review_template(
    *,
    commit: str,
    contract_hash: str,
    review_id: str,
    content_hash: str,
) -> dict[str, Any]:
    """Create the public prefilled draft without any private association."""

    return CodexExternalReviewTemplate(
        commit=commit,
        contractHash=contract_hash,
        reviewId=review_id,
        contentHash=content_hash,
        rubricVersion=CODEX_EXTERNAL_REVIEW_RUBRIC_VERSION,
        reviewer=CODEX_EXTERNAL_REVIEWER,
        scores={field: PENDING_SCORE for field in sorted(CODEX_EXTERNAL_REVIEW_SCORE_FIELDS)},
        fatalContradiction=PENDING_FATAL_CONTRADICTION,
    ).model_dump(mode="json", by_alias=True)


def write_codex_external_review_templates(
    review_directory: Path,
    samples: Iterable[tuple[str, str]],
    *,
    commit: str,
    contract_hash: str,
) -> tuple[Path, ...]:
    """Write one exclusive, public draft per blinded content sample.

    Callers stage these files beside their content samples before atomically
    exposing the directory.  The input deliberately carries no profile, story,
    sample, provider, run, prompt, or response data.
    """

    paths: list[Path] = []
    for review_id, content_hash in samples:
        path = score_sheet_path(review_directory, review_id)
        payload = build_codex_external_review_template(
            commit=commit,
            contract_hash=contract_hash,
            review_id=review_id,
            content_hash=content_hash,
        )
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as score_sheet:
                score_sheet.write(canonical_json(payload) + "\n")
        finally:
            try:
                os.close(descriptor)
            except OSError:
                pass
        paths.append(path)
    return tuple(paths)


def is_unfilled_codex_external_review_template(value: Any) -> bool:
    """Identify a wholly or partly unfilled published draft.

    Reviewers may edit the seven decision values in any order.  Detecting the
    sentinels directly rather than validating only the pristine draft makes the
    final builder reject a partially completed sheet too.
    """

    if not isinstance(value, Mapping) or set(value) != CODEX_EXTERNAL_REVIEW_FIELDS:
        return False
    scores = value.get("scores")
    if isinstance(scores, Mapping) and set(scores) == CODEX_EXTERNAL_REVIEW_SCORE_FIELDS:
        if any(type(score) is int and score == PENDING_SCORE for score in scores.values()):
            return True
    return value.get("fatalContradiction") == PENDING_FATAL_CONTRADICTION
