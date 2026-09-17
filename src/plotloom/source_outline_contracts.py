"""Project-owned F1A source and upstream-outline review contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value


SourceKind = Literal["synopsis", "imported_text", "existing_work"]
CandidateStatus = Literal["prepared", "ready"]
OutlineReviewStatus = Literal["missing", "candidate_ready", "accepted", "reopened"]


class SourceMaterial(CamelModel):
    """Author-declared source facts; declarations are not rights clearance."""

    kind: SourceKind
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=1_000_000)
    attribution: str = Field(min_length=1, max_length=4_000)
    rights_declaration: str = Field(min_length=1, max_length=4_000)
    adaptation_intent: str = Field(min_length=1, max_length=8_000)
    invented_additions: str | None = Field(default=None, max_length=8_000)

    @field_validator("title", "text", "attribution", "rights_declaration", "adaptation_intent")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source fields must not be blank")
        return value

    def assert_safe(self) -> None:
        if contains_secret_setting(self.model_dump(mode="json", by_alias=True)) or contains_secret_value(self.model_dump(mode="json", by_alias=True)):
            raise ValueError("source material must not contain credentials")


class SourceRevision(CamelModel):
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    material: SourceMaterial
    created_at: datetime


class OutlineCandidate(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    source_revision: int = Field(ge=1)
    expected_outline_revision: int = Field(ge=0)
    status: CandidateStatus
    delivery_id: str | None = None
    manifest_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    outline: dict[str, Any] | None = None
    report_available: bool = False
    created_at: datetime
    delivered_at: datetime | None = None


class OutlineCandidatePreparation(OutlineCandidate):
    package_path: str
    delivery_path: str
    assignment: str


class AcceptedOutlineRevision(CamelModel):
    revision: int = Field(ge=1)
    source_revision: int = Field(ge=1)
    candidate_job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    outline: dict[str, Any]
    accepted_at: datetime


class SourceOutlineReviewState(CamelModel):
    source: SourceRevision | None = None
    candidate: OutlineCandidate | None = None
    accepted_outline: AcceptedOutlineRevision | None = None
    outline_status: OutlineReviewStatus


class SourceSaveRequest(CamelModel):
    expected_source_revision: int = Field(ge=0)
    material: SourceMaterial


class OutlineAcceptRequest(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_source_revision: int = Field(ge=1)
    expected_outline_revision: int = Field(ge=0)


class OutlineReopenRequest(CamelModel):
    expected_outline_revision: int = Field(ge=1)
