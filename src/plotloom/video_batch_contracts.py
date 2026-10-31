"""Bounded batch requests and truthful structured human confirmation."""
from typing import Literal

from pydantic import Field, field_validator

from plotloom.domain_base import CamelModel

from .delegated_qa_contracts import AgentQaAttribution
from .human_confirmation_contracts import UnnamedCreatorConfirmation
from .operator_attribution import CodexTaskAttribution
from .video_contracts import H3DirectionField, VideoJobRequest


class BatchSetup(CamelModel):
    automatic_retry_limit: int = Field(default=1, strict=True, ge=0)
    profile_id: str = Field(min_length=3, max_length=63)
    aspect_policy: Literal["reject_mismatch", "contain_pad", "cover_center_crop"] = "reject_mismatch"
    single_request: VideoJobRequest | None = Field(default=None, exclude_if=lambda value: value is None)
    shot_ids: list[str] | None = Field(default=None, min_length=1, max_length=256, exclude_if=lambda value: value is None)
    max_jobs: int | None = Field(default=None, strict=True, ge=1)
    max_requested_seconds: int | None = Field(default=None, strict=True, ge=5)

class BatchRejectedReplacement(CamelModel):
    attribution: AgentQaAttribution | None = None
    batch_id: str = Field(min_length=36, max_length=36)
    expected_revision: int = Field(strict=True, ge=1)
    rejected_job_ids: list[str] = Field(min_length=1, max_length=256)
    setup: BatchSetup

    @field_validator("rejected_job_ids")
    @classmethod
    def unique_rejected_jobs(cls, values):
        if len(values) != len(set(values)) or any(not value for value in values):
            raise ValueError("replacement requires unique explicit rejected job IDs")
        return values

class BatchDirectionsTarget(CamelModel):
    shot_id: str = Field(min_length=1, max_length=100)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    fields: list[H3DirectionField] = Field(min_length=1, max_length=100)

class BatchDirectionsDraft(CamelModel):
    version: Literal["video-directions.draft.v1"] = "video-directions.draft.v1"
    targets: list[BatchDirectionsTarget] = Field(max_length=256)

class BatchStart(CamelModel):
    attribution: AgentQaAttribution | None = None
    expected_revision: int = Field(strict=True, ge=1)
    manifest_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    basis: Literal["production-intent.v2"]

class BatchControl(CamelModel):
    batch_id: str = Field(min_length=36, max_length=36)
    expected_control_revision: int = Field(strict=True, ge=1)
    action: Literal["pause", "resume", "cancel"]

class BatchConfirmation(CamelModel):
    attribution: CodexTaskAttribution | UnnamedCreatorConfirmation | AgentQaAttribution = Field(
        default_factory=UnnamedCreatorConfirmation)
    expected_revision: int = Field(strict=True, ge=1)
    review_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    basis: Literal["source-bound-selections.v1"]
