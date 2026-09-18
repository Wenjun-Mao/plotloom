"""F3A source- and cast-bound review contracts for one ``art.json`` proposal."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .domain import CamelModel


ArtStatus = Literal["missing", "prepared", "candidate_ready", "accepted", "reopened", "stale"]


class ArtBinding(CamelModel):
    """Frozen creative inputs. Code owns this receipt, not art semantics."""

    source_revision: int = Field(ge=1)
    source_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    outline_revision: int = Field(ge=1)
    outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_map_revision: int = Field(ge=1)
    section_map_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    graph_revision: int = Field(ge=1)
    graph_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    cast_revision: int = Field(ge=1)
    cast_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_ids: list[str] = Field(min_length=3, max_length=3)

    @field_validator("section_ids")
    @classmethod
    def section_ids_are_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not item.strip() for item in value):
            raise ValueError("section IDs must be unique and nonblank")
        return value


class ArtCandidate(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_art_revision: int = Field(ge=0)
    binding: ArtBinding
    status: Literal["prepared", "ready", "accepted", "cancelled"]
    delivery_id: str | None = None
    manifest_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    art: dict[str, Any] | None = None
    report_available: bool = False
    created_at: datetime
    delivered_at: datetime | None = None


class ArtCandidatePreparation(ArtCandidate):
    package_path: str
    delivery_path: str
    assignment: str


class AcceptedArtRevision(CamelModel):
    revision: int = Field(ge=1)
    candidate_job_id: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    binding: ArtBinding
    art: dict[str, Any]
    accepted_at: datetime


class ArtReviewState(CamelModel):
    candidate: ArtCandidate | None = None
    accepted_art: AcceptedArtRevision | None = None
    status: ArtStatus
    stale_reasons: list[str] = Field(default_factory=list)


class ArtAcceptRequest(CamelModel):
    job_id: str
    expected_art_revision: int = Field(ge=0)
    binding: ArtBinding
    art: dict[str, Any] | None = None


class ArtSaveRequest(CamelModel):
    expected_art_revision: int = Field(ge=1)
    binding: ArtBinding
    art: dict[str, Any]


class ArtReopenRequest(CamelModel):
    expected_art_revision: int = Field(ge=1)
