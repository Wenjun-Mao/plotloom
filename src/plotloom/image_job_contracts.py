"""Provider-neutral contracts for the P1 manual image-job boundary.

This module deliberately contains no browser, database, artifact-store, or
filesystem dependency.  It names the immutable facts that Plotloom freezes and
the untrusted declaration returned by a specialist.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import CamelModel


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
    presentation_change: str = Field(min_length=1, max_length=4_000)

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


class ImageJobOutput(CamelModel):
    filename: str = Field(min_length=1, max_length=180)
    sha256: str = Field(pattern=SHA256_PATTERN)
    role: Literal["original", "refinement"]

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


class ImageDeliveryManifest(CamelModel):
    """The specialist's completion declaration; bytes remain untrusted."""

    schema_version: Literal[1] = 1
    job_id: str = Field(pattern=JOB_ID_PATTERN)
    request_hash: str = Field(pattern=SHA256_PATTERN)
    delivery_id: str = Field(pattern=DELIVERY_ID_PATTERN)
    actual_prompt: str = Field(min_length=1, max_length=20_000)
    outputs: list[ImageJobOutput] = Field(min_length=1, max_length=4)
    tool_evidence: ImageToolEvidence
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


def is_image_job_id(value: str) -> bool:
    return re.fullmatch(JOB_ID_PATTERN, value) is not None
