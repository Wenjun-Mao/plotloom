"""Bounded batch requests and truthful structured human confirmation."""
from typing import Literal
from pydantic import Field
from .domain import CamelModel
from .video_contracts import H3DirectionField
from .delegated_qa_contracts import AgentQaAttribution, QaAvInspection

class BatchSetup(CamelModel):
    profile_id: str = Field(min_length=3, max_length=63)
    aspect_policy: Literal["reject_mismatch", "contain_pad", "cover_center_crop"] = "reject_mismatch"
    max_jobs: int = Field(default=64, strict=True, ge=1, le=256)
    max_requested_seconds: int = Field(default=512, strict=True, ge=5, le=2048)

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
    basis: Literal["whole-batch-english.v1"]

class BatchControl(CamelModel):
    batch_id: str = Field(min_length=36, max_length=36)
    expected_control_revision: int = Field(strict=True, ge=1)
    action: Literal["pause", "resume", "cancel"]

class BatchConfirmation(CamelModel):
    attribution: AgentQaAttribution | None = None
    inspection: QaAvInspection | None = None
    expected_revision: int = Field(strict=True, ge=1)
    review_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    basis: Literal["whole-pack-video-native-audio.v1"]
    note: str = Field(default="", max_length=2000)
