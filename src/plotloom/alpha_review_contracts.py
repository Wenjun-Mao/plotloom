"""Closed content-free independent-review contracts for current native Alpha."""
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator
from .alpha_review_templates import (CODEX_EXTERNAL_REVIEW_SCORE_FIELDS, CODEX_EXTERNAL_REVIEWER,
 COMMIT_SHA_PATTERN, CONTENT_HASH_PATTERN, OPAQUE_REVIEW_ID_PATTERN,
 CodexExternalReviewer, CodexExternalReviewRubricVersion)

class _ExternalReviewModel(BaseModel):
    """A closed, text-free receipt model for independent Codex review."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

class CodexExternalReview(_ExternalReviewModel):
    """One blinded rubric score sheet, deliberately incapable of carrying prose."""

    commit: str
    contract_hash: str = Field(alias="contractHash")
    review_id: str = Field(alias="reviewId")
    content_hash: str = Field(alias="contentHash")
    rubric_version: CodexExternalReviewRubricVersion = Field(alias="rubricVersion")
    reviewer: CodexExternalReviewer
    scores: dict[str, StrictInt]
    fatal_contradiction: StrictBool = Field(alias="fatalContradiction")

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
    def _validate_scores(cls, value: dict[str, int]) -> dict[str, int]:
        if set(value) != CODEX_EXTERNAL_REVIEW_SCORE_FIELDS:
            raise ValueError("invalid rubric dimensions")
        if any(
            not isinstance(score, int)
            or isinstance(score, bool)
            or not 1 <= score <= 5
            for score in value.values()
        ):
            raise ValueError("rubric scores must be integers from 1 through 5")
        return dict(value)

class CodexExternalReviewGate(_ExternalReviewModel):
    """Secret-free aggregate that is suitable for a tracked Alpha receipt."""

    gate: CodexExternalReviewer = CODEX_EXTERNAL_REVIEWER
    commit: str
    contract_hash: str = Field(alias="contractHash")
    rubric_version: CodexExternalReviewRubricVersion = Field(alias="rubricVersion")
    reviewer: CodexExternalReviewer
    review_count: int = Field(alias="reviewCount", ge=0)
    expected_review_count: int = Field(alias="expectedReviewCount", ge=0)
    issue_codes: tuple[str, ...] = Field(alias="issueCodes")
    passed: bool
    dimension_medians: dict[str, float] = Field(alias="dimensionMedians")

class CodexExternalReviewReceipt(_ExternalReviewModel):
    """Closed tracked receipt containing only validated blinded score sheets."""

    receipt: CodexExternalReviewer = CODEX_EXTERNAL_REVIEWER
    commit: str
    contract_hash: str = Field(alias="contractHash")
    rubric_version: CodexExternalReviewRubricVersion = Field(alias="rubricVersion")
    reviewer: CodexExternalReviewer
    reviews: tuple[CodexExternalReview, ...]
    gate: CodexExternalReviewGate

@dataclass(frozen=True)
class ReviewSampleManifest:
    """The safe identity/hash pair needed to bind an external score sheet."""

    review_id: str
    content_hash: str

@dataclass(frozen=True)
class ReviewPackManifest:
    """Immutable Alpha-pack provenance plus its three blinded sample hashes."""

    commit: str
    contract_hash: str
    samples: tuple[ReviewSampleManifest, ...]
