"""Project-owned F1A source and upstream-outline review contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value


SourceKind = Literal["synopsis", "imported_text", "existing_work"]
CandidateStatus = Literal["prepared", "ready", "accepted", "cancelled"]
OutlineReviewStatus = Literal["missing", "candidate_ready", "accepted", "reopened"]
SectionMapStatus = Literal["missing", "current", "stale"]


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


class StorySection(CamelModel):
    """One explicitly authored, stable source section; this is not a graph node."""

    section_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=8_000)
    ending: bool = False


class BranchOutcome(CamelModel):
    """A labelled author choice and the explicit consequence/ending it reaches."""

    outcome_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    label: str = Field(min_length=1, max_length=300)
    consequence: str = Field(min_length=1, max_length=8_000)
    ending_section_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")


class SectionChoice(CamelModel):
    choice_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    section_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    prompt: str = Field(min_length=1, max_length=2_000)
    outcomes: list[BranchOutcome] = Field(min_length=2, max_length=2)


class SectionMap(CamelModel):
    """The F1B bounded branch map: sections plus exactly one binary decision."""

    sections: list[StorySection] = Field(min_length=3, max_length=32)
    choice: SectionChoice

    @field_validator("sections")
    @classmethod
    def require_unique_section_ids(cls, sections: list[StorySection]) -> list[StorySection]:
        if len({section.section_id for section in sections}) != len(sections):
            raise ValueError("section IDs must be unique")
        return sections

    @field_validator("choice")
    @classmethod
    def require_unique_outcomes(cls, choice: SectionChoice) -> SectionChoice:
        if len({outcome.outcome_id for outcome in choice.outcomes}) != len(choice.outcomes):
            raise ValueError("outcome IDs must be unique")
        return choice

    def validate_links(self) -> None:
        sections = {section.section_id: section for section in self.sections}
        if self.choice.section_id not in sections:
            raise ValueError("choice section must be an explicit section")
        if sections[self.choice.section_id].ending:
            raise ValueError("an ending section cannot own the choice")
        ending_ids = [outcome.ending_section_id for outcome in self.choice.outcomes]
        if len(set(ending_ids)) != 2:
            raise ValueError("each outcome must lead to a distinct ending section")
        if any(section_id not in sections or not sections[section_id].ending for section_id in ending_ids):
            raise ValueError("each outcome must lead to an explicit ending section")


class AcceptedSectionMapRevision(CamelModel):
    revision: int = Field(ge=1)
    source_revision: int = Field(ge=1)
    outline_revision: int = Field(ge=1)
    outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mapping: SectionMap
    accepted_at: datetime


class SourceOutlineReviewState(CamelModel):
    source: SourceRevision | None = None
    candidate: OutlineCandidate | None = None
    accepted_outline: AcceptedOutlineRevision | None = None
    outline_status: OutlineReviewStatus
    accepted_section_map: AcceptedSectionMapRevision | None = None
    section_map_status: SectionMapStatus
    section_map_stale_reasons: list[str] = Field(default_factory=list)


class SourceSaveRequest(CamelModel):
    expected_source_revision: int = Field(ge=0)
    material: SourceMaterial


class OutlineAcceptRequest(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_source_revision: int = Field(ge=1)
    expected_outline_revision: int = Field(ge=0)


class OutlineReopenRequest(CamelModel):
    expected_outline_revision: int = Field(ge=1)


class SectionMapSaveRequest(CamelModel):
    expected_section_map_revision: int = Field(ge=0)
    expected_source_revision: int = Field(ge=1)
    expected_outline_revision: int = Field(ge=1)
    expected_outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mapping: SectionMap
