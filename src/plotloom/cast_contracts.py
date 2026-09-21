"""F2A review contracts for one accepted upstream-shaped ``cast.json``."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .domain import CamelModel


CastStatus = Literal["missing", "prepared", "candidate_ready", "accepted", "reopened", "stale"]


class CastBinding(CamelModel):
    """Exact F1 records and installed graph that a cast proposal may describe."""

    source_revision: int = Field(ge=1)
    source_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    outline_revision: int = Field(ge=1)
    outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_map_revision: int = Field(ge=1)
    section_map_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    graph_revision: int = Field(ge=1)
    graph_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_ids: list[str] = Field(min_length=3, max_length=3)

    @field_validator("section_ids")
    @classmethod
    def section_ids_are_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not item.strip() for item in value):
            raise ValueError("section IDs must be unique and nonblank")
        return value


class CastCandidate(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_cast_revision: int = Field(ge=0)
    binding: CastBinding
    status: Literal["prepared", "ready", "accepted", "cancelled"]
    delivery_id: str | None = None
    manifest_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    cast: dict[str, Any] | None = None
    report_available: bool = False
    created_at: datetime
    delivered_at: datetime | None = None


class CastCandidatePreparation(CastCandidate):
    package_path: str
    delivery_path: str
    assignment: str


class CastConsumerMapping(CamelModel):
    """Explicit seam to the existing reference/media character key namespace."""

    cast_character_id: str = Field(min_length=1, max_length=128)
    consumer_character_id: str = Field(min_length=1, max_length=128)


class AcceptedCastRevision(CamelModel):
    revision: int = Field(ge=1)
    candidate_job_id: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    binding: CastBinding
    cast: dict[str, Any]
    consumer_mappings: list[CastConsumerMapping]
    accepted_at: datetime


class CastReviewState(CamelModel):
    candidate: CastCandidate | None = None
    accepted_cast: AcceptedCastRevision | None = None
    status: CastStatus
    stale_reasons: list[str] = Field(default_factory=list)


class CastAcceptRequest(CamelModel):
    job_id: str
    expected_cast_revision: int = Field(ge=0)
    binding: CastBinding
    consumer_mappings: list[CastConsumerMapping] = Field(min_length=1)
    # The author may refine proposal-owned direction in ordinary forms. Stable
    # upstream character IDs remain frozen by the prepared candidate.
    cast: dict[str, Any] | None = None


class CastSaveRequest(CamelModel):
    """CAS-protected author save after explicitly reopening accepted cast work."""

    expected_cast_revision: int = Field(ge=1)
    binding: CastBinding
    cast: dict[str, Any]
    consumer_mappings: list[CastConsumerMapping] = Field(min_length=1)


class CastReopenRequest(CamelModel):
    expected_cast_revision: int = Field(ge=1)


class CastCancelReopenRequest(CamelModel):
    """CAS-protected abandonment of a durable reopened-cast editing session."""

    expected_cast_revision: int = Field(ge=1)
