"""F4 contracts: upstream script JSON plus a deliberately thin section binding."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .art_contracts import ArtBinding
from .authored_route_timing import route_budget_hash
from .domain import CamelModel

ScriptStatus = Literal["missing", "prepared", "candidate_ready", "accepted", "reopened", "stale"]


class ScriptBinding(ArtBinding):
    art_revision: int = Field(ge=1)
    art_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    target_playthrough_seconds: int = Field(ge=3)
    route_budget_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_bindings: list["ScriptSectionBinding"] = Field(min_length=1, max_length=128)
    complete_route_section_ids: list[list[str]] = Field(min_length=1)
    route_only_section_ids: list[str]

    @model_validator(mode="after")
    def require_exact_footage_membership(self) -> "ScriptBinding":
        footage_ids = [item.section_id for item in self.section_bindings]
        route_ids = self.route_only_section_ids
        if len(set(footage_ids)) != len(footage_ids) or len(set(route_ids)) != len(route_ids):
            raise ValueError("section footage membership must be unique")
        if set(footage_ids) & set(route_ids) or set(footage_ids) | set(route_ids) != set(self.section_ids):
            raise ValueError("footage and route-only membership must exactly cover graph sections")
        if any(section not in self.section_ids for route in self.complete_route_section_ids for section in route):
            raise ValueError("complete routes must retain only actual graph sections")
        if {node for route in self.complete_route_section_ids for node in route} != set(self.section_ids):
            raise ValueError("complete routes must cover every section")
        expected = route_budget_hash(
            target_seconds=self.target_playthrough_seconds,
            section_bindings=[item.model_dump(mode="json", by_alias=True) for item in self.section_bindings],
            routes=self.complete_route_section_ids, route_only_ids=route_ids,
        )
        if self.route_budget_hash != expected:
            raise ValueError("routeBudgetHash must match the frozen authored timing contract")
        return self


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
