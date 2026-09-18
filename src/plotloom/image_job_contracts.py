"""Provider-neutral contracts for the P1 manual image-job boundary.

This module deliberately contains no browser, database, artifact-store, or
filesystem dependency.  It names the immutable facts that Plotloom freezes and
the untrusted declaration returned by a specialist.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value


SHA256_PATTERN = r"^[a-f0-9]{64}$"
JOB_ID_PATTERN = r"^ij_[a-z0-9]{20,64}$"
DELIVERY_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"


class ImageJobError(ValueError):
    """A stable, non-secret P1 admission or delivery error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ImageJobCreateRequest(CamelModel):
    """Browser input for one frozen, creator-reviewed image-job brief."""

    approval_id: str = Field(min_length=1, max_length=36)
    shot_id: str = Field(min_length=1, max_length=100)
    storyboard_revision: int = Field(ge=1)
    parent_candidate_asset_id: str | None = Field(default=None, max_length=36)
    # An aspect-adaptation job starts from the current reviewed keyframe,
    # including an imported keyframe that has no prior image-job candidate.
    # The API resolves this opaque ID against the reviewed H3 catalog; callers
    # never choose free-form output dimensions.
    keyframe_adaptation_profile_id: str | None = Field(default=None, min_length=3, max_length=128)
    presentation_change: str = Field(min_length=1, max_length=4_000)
    # V2 remains the historical/default wire contract so an older client never
    # silently starts claiming cross-shot identity. P1.5 clients opt into V3.
    contract_version: Literal[2, 3] = 2

    @field_validator("presentation_change")
    @classmethod
    def creator_direction_is_nonblank(cls, value: str) -> str:
        """Keep creator direction explicit without granting narrative authority.

        The browser may describe the intended presentation or refinement, but
        it cannot supply canonical facts, a VisualIntent identity, or a path.
        Those remain resolved by trusted code when the job is prepared.
        """

        normalized = value.strip()
        if not normalized:
            raise ValueError("presentationChange must not be blank")
        return normalized

    @model_validator(mode="after")
    def adaptation_request_has_one_source_mode(self) -> "ImageJobCreateRequest":
        if self.keyframe_adaptation_profile_id is not None:
            if self.parent_candidate_asset_id is not None:
                raise ValueError("keyframe adaptation cannot also name a refinement parent")
            if self.contract_version != 3:
                raise ValueError("keyframe adaptation requires the identity-aware image-job contract")
        return self


class CharacterReferenceDecisionRequest(CamelModel):
    """An explicit, revision-checked choice of project-owned identity assets."""

    character_id: str = Field(min_length=1, max_length=128)
    authority: Literal["cast", "story_bible"]
    primary_asset_id: str = Field(min_length=1, max_length=36)
    complementary_asset_ids: list[str] = Field(default_factory=list, max_length=2)
    expected_reference_revision: int = Field(ge=0)
    reviewer: str = Field(min_length=1, max_length=160)
    notes: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def reference_assets_are_distinct(self) -> "CharacterReferenceDecisionRequest":
        assets = [self.primary_asset_id, *self.complementary_asset_ids]
        if len(assets) != len(set(assets)):
            raise ValueError("character reference assets must be distinct")
        return self


class CharacterReferenceRevocationRequest(CamelModel):
    expected_reference_revision: int = Field(ge=1)
    reviewer: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=2_000)


class CharacterReferenceProposalRequest(CamelModel):
    """Exploratory cast appearance work with no Bible, shot, or Approval."""

    character_id: str = Field(min_length=1, max_length=128)
    cast_revision: int = Field(ge=1)
    visual_direction: str = Field(min_length=1, max_length=4_000)
    parent_candidate_asset_id: str | None = Field(default=None, max_length=36)

    @field_validator("visual_direction")
    @classmethod
    def proposal_direction_is_nonblank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("visualDirection must not be blank")
        return normalized


class SamePersonReviewItem(CamelModel):
    character_id: str = Field(min_length=1, max_length=128)
    judgment: Literal["pass", "fail"]
    identity_notes: str = Field(min_length=1, max_length=2_000)
    state_notes: str = Field(min_length=1, max_length=2_000)


class SamePersonReviewRequest(CamelModel):
    binding_id: str = Field(min_length=1, max_length=36)
    expected_review_revision: int = Field(ge=0)
    reviewer: str = Field(min_length=1, max_length=160)
    comparisons: list[SamePersonReviewItem] = Field(min_length=1, max_length=8)
    notes: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def character_reviews_are_distinct(self) -> "SamePersonReviewRequest":
        character_ids = [item.character_id for item in self.comparisons]
        if len(character_ids) != len(set(character_ids)):
            raise ValueError("same-person comparisons must name each character once")
        return self


class ImageJobOutput(CamelModel):
    filename: str = Field(min_length=1, max_length=180)
    sha256: str = Field(pattern=SHA256_PATTERN)
    role: Literal["original", "refinement", "keyframe_adaptation"]

    @field_validator("filename")
    @classmethod
    def confined_filename(cls, value: str) -> str:
        # The exchange layer adds the fixed outputs/ directory. A delivery
        # declaration never gets to name a relative directory or a platform
        # specific absolute path.
        if value in {".", ".."} or "/" in value or "\\" in value or value.startswith("."):
            raise ValueError("filename must be a plain output filename")
        return value


class ImageToolEvidence(CamelModel):
    tool: Literal["codex_imagegen"]
    task_id: str = Field(min_length=1, max_length=160)
    # A P1 candidate is specifically evidence of an observed built-in-imagegen
    # run. A no-tool manifest is not a weaker success state; it is invalid.
    available: Literal[True] = True


class ImageReferenceUse(CamelModel):
    """A specialist attestation, never a substitute for creator visual review."""

    viewed_reference_hashes: list[str] = Field(min_length=1, max_length=24)
    identity_notes: str = Field(min_length=1, max_length=2_000)

    @field_validator("viewed_reference_hashes")
    @classmethod
    def reference_hashes_are_distinct(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("viewedReferenceHashes must not contain duplicates")
        if any(re.fullmatch(SHA256_PATTERN, item) is None for item in value):
            raise ValueError("viewedReferenceHashes must contain SHA-256 values")
        return value


class ImageExecutorProvenance(CamelModel):
    """Observed executor details retained beside, never inside, creative authority."""

    code_revision: str = Field(min_length=7, max_length=64, pattern=r"^[a-f0-9]+$")
    skill_version: str = Field(min_length=1, max_length=80)
    skill_hash: str = Field(pattern=SHA256_PATTERN)
    model: str | None = Field(default=None, max_length=128)
    reasoning_effort: str | None = Field(default=None, max_length=32)


class ImageDeliveryManifest(CamelModel):
    """The specialist's completion declaration; bytes remain untrusted."""

    schema_version: Literal[1, 2] = 1
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    request_hash: str = Field(pattern=SHA256_PATTERN)
    delivery_id: str = Field(pattern=DELIVERY_ID_PATTERN)
    actual_prompt: str = Field(min_length=1, max_length=20_000)
    outputs: list[ImageJobOutput] = Field(min_length=1, max_length=4)
    tool_evidence: ImageToolEvidence
    reference_use: ImageReferenceUse | None = None
    executor_provenance: ImageExecutorProvenance | None = None
    limitations: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("limitations")
    @classmethod
    def bounded_limitations(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 2_000 for item in value):
            raise ValueError("limitations must be nonblank and at most 2,000 characters")
        return value

    @model_validator(mode="after")
    def outputs_are_unique(self) -> "ImageDeliveryManifest":
        filenames = [item.filename for item in self.outputs]
        hashes = [item.sha256 for item in self.outputs]
        if len(filenames) != len(set(filenames)):
            raise ValueError("outputs must not declare a filename twice")
        if len(hashes) != len(set(hashes)):
            raise ValueError("outputs must not declare the same bytes twice")
        return self

    def assert_secret_free(self) -> None:
        """Reject specialist-controlled text before it can enter project history."""

        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ImageJobError(
                "delivery_manifest_secret",
                "completion manifest must not contain credentials or secret-shaped values",
            )


def is_image_job_id(value: str) -> bool:
    return re.fullmatch(JOB_ID_PATTERN, value) is not None
