"""F4 contracts: upstream script JSON plus a deliberately thin section binding."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .art_contracts import ArtBinding
from .domain import CamelModel

ScriptStatus = Literal["missing", "prepared", "candidate_ready", "accepted", "reopened", "stale"]


class ScriptBinding(ArtBinding):
    art_revision: int = Field(ge=1)
    art_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    target_playthrough_seconds: int = Field(ge=3)


class ScriptSectionBinding(CamelModel):
    """Maps one stable Plotloom section to one upstream episode number."""

    section_id: str = Field(min_length=1)
    episode: int = Field(ge=1)


class ScriptCandidate(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_script_revision: int = Field(ge=0)
    binding: ScriptBinding
    status: Literal["prepared", "ready", "accepted", "cancelled"]
    delivery_id: str | None = None
    manifest_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    script: dict[str, Any] | None = None
    report_available: bool = False
    created_at: datetime
    delivered_at: datetime | None = None


class ScriptCandidatePreparation(ScriptCandidate):
    package_path: str
    delivery_path: str
    assignment: str


class AcceptedScriptRevision(CamelModel):
    revision: int = Field(ge=1)
    candidate_job_id: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    binding: ScriptBinding
    script: dict[str, Any]
    accepted_at: datetime


class ScriptReviewState(CamelModel):
    candidate: ScriptCandidate | None = None
    accepted_script: AcceptedScriptRevision | None = None
    status: ScriptStatus
    stale_reasons: list[str] = Field(default_factory=list)


class ScriptAcceptRequest(CamelModel):
    job_id: str
    expected_script_revision: int = Field(ge=0)
    binding: ScriptBinding
    script: dict[str, Any] | None = None


class ScriptReopenRequest(CamelModel):
    expected_script_revision: int = Field(ge=1)


class ScriptSectionSaveRequest(CamelModel):
    expected_script_revision: int = Field(ge=1)
    binding: ScriptBinding
    section_id: str = Field(min_length=1)
    episode: dict[str, Any]
