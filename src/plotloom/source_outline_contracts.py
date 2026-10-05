"""Project-owned F1A source and upstream-outline review contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .canonical_schema import (
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
    V2StoryEdgeKind,
    V2StoryNodeKind,
)
from .generation.story_graph_topology import StoryGraphTopology
from .domain import CamelModel, contains_secret_setting, contains_secret_value
from .source_structures import MAX_SOURCE_OPTIONS


SourceKind = Literal["synopsis", "imported_text", "existing_work"]
CandidateStatus = Literal["prepared", "ready", "accepted", "cancelled"]
OutlineReviewStatus = Literal["missing", "candidate_ready", "accepted", "reopened"]
SectionMapStatus = Literal["missing", "current", "stale"]


class SourceMaterial(CamelModel):
    """Accepted source content; optional metadata never establishes clearance."""

    kind: SourceKind
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=1_000_000)
    attribution: str | None = Field(default=None, max_length=4_000)
    rights_declaration: str | None = Field(default=None, max_length=4_000)
    adaptation_intent: str = Field(default="", max_length=8_000)
    invented_additions: str | None = Field(default=None, max_length=8_000)

    @field_validator("title", "text")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source fields must not be blank")
        return value

    @field_validator("adaptation_intent")
    @classmethod
    def trim_direction(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_imported_adaptation_goal(self) -> "SourceMaterial":
        if self.kind != "synopsis" and not self.adaptation_intent:
            raise ValueError("imported stories require an explicit adaptation goal")
        return self

    @field_validator("attribution", "rights_declaration")
    @classmethod
    def normalize_optional_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

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
    """Reviewed prose for one stable routing section."""

    section_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=8_000)
    ending: bool = False


class BranchOutcome(CamelModel):
    """A labelled option and the explicit consequence/next section it reaches."""

    outcome_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    label: str = Field(min_length=1, max_length=300)
    consequence: str = Field(min_length=1, max_length=8_000)
    ending_section_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")


class SectionChoice(CamelModel):
    choice_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    section_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    prompt: str = Field(min_length=1, max_length=2_000)
    outcomes: list[BranchOutcome] = Field(min_length=2, max_length=MAX_SOURCE_OPTIONS)


class SectionMap(CamelModel):
    """Reviewed planned structure, or a retained explicit binary structure."""

    sections: list[StorySection] = Field(min_length=1, max_length=128)
    choice: SectionChoice | None = None
    topology: StoryGraphTopology | None = None
    choices: list[SectionChoice] = Field(default_factory=list)
    join_reconciliations: dict[str, str] = Field(default_factory=dict)

    @field_validator("sections")
    @classmethod
    def require_unique_section_ids(cls, sections: list[StorySection]) -> list[StorySection]:
        if len({section.section_id for section in sections}) != len(sections):
            raise ValueError("section IDs must be unique")
        return sections

    @field_validator("choice")
    @classmethod
    def require_unique_outcomes(cls, choice: SectionChoice | None) -> SectionChoice | None:
        if choice is None:
            return choice
        if len({outcome.outcome_id for outcome in choice.outcomes}) != len(choice.outcomes):
            raise ValueError("outcome IDs must be unique")
        return choice

    def validate_links(self) -> None:
        if self.topology is not None:
            from .source_structure_validation import validate_structure_links
            validate_structure_links(self)
            return
        if self.choice is None or len(self.choice.outcomes) != 2 or self.choices or self.join_reconciliations:
            raise ValueError("retained binary map requires exactly one choice and two outcomes")
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
        if len(sections) != 3 or len([section for section in sections.values() if section.ending]) != 2:
            raise ValueError("F1B requires exactly one entry section and exactly two ending sections")
        if set(ending_ids) != {section.section_id for section in sections.values() if section.ending}:
            raise ValueError("the two outcomes must reach every explicit ending section")

    @model_validator(mode="after")
    def require_complete_structure(self) -> "SectionMap":
        self.validate_links()
        return self


def compile_section_map_graph(mapping: SectionMap) -> StoryGraphV2:
    """Compile only the admitted structure into the canonical routing owner."""

    mapping.validate_links()
    if mapping.topology is not None:
        from .source_structures import compile_structure
        return compile_structure(mapping)
    sections = {section.section_id: section for section in mapping.sections}
    entry = sections[mapping.choice.section_id]
    return StoryGraphV2(
        start_node_id=entry.section_id,
        nodes=[
            StoryNodeV2(
                id=section.section_id,
                title=section.title,
                summary=section.summary,
                kind=V2StoryNodeKind.START if section.section_id == entry.section_id else V2StoryNodeKind.ENDING,
            )
            for section in mapping.sections
        ],
        edges=[
            StoryEdgeV2(
                id=outcome.outcome_id,
                source_node_id=entry.section_id,
                target_node_id=outcome.ending_section_id,
                kind=V2StoryEdgeKind.CHOICE,
                choice_text=outcome.label,
                state_effects={
                    "sourceMapChoiceId": mapping.choice.choice_id,
                    "sourceMapOutcomeId": outcome.outcome_id,
                    "sourceMapConsequence": outcome.consequence,
                },
                entity_state_effects=[],
            )
            for outcome in mapping.choice.outcomes
        ],
        join_contracts=[],
    )


def validate_section_map_graph(graph: StoryGraphV2, brief: Any) -> None:
    """Validate actual viewer choices and endings against the saved Brief."""

    if any(edge.entity_state_effects for edge in graph.edges):
        raise ValueError("source-map graph admission forbids entity state effects")
    from .validation import validate_story_graph

    validate_story_graph(graph, brief, strict_v2=True, bible=None)



class AcceptedSectionMapRevision(CamelModel):
    revision: int = Field(ge=1)
    source_revision: int = Field(ge=1)
    outline_revision: int = Field(ge=1)
    outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mapping: SectionMap
    accepted_at: datetime


class SourceMapGraphAdmission(CamelModel):
    """A binding receipt, never another copy of the accepted routing graph."""

    source_revision: int = Field(ge=1)
    source_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    outline_revision: int = Field(ge=1)
    outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    section_map_revision: int = Field(ge=1)
    section_map_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    graph_revision: int = Field(ge=1)
    graph_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["current", "stale"]
    stale_reasons: list[str] = Field(default_factory=list)
    installed_at: datetime


class SourceOutlineReviewState(CamelModel):
    source: SourceRevision | None = None
    candidate: OutlineCandidate | None = None
    accepted_outline: AcceptedOutlineRevision | None = None
    outline_status: OutlineReviewStatus
    accepted_section_map: AcceptedSectionMapRevision | None = None
    section_map_status: SectionMapStatus
    section_map_stale_reasons: list[str] = Field(default_factory=list)
    graph_admission: SourceMapGraphAdmission | None = None


class SourceSaveRequest(CamelModel):
    expected_source_revision: int = Field(ge=0)
    material: SourceMaterial


class OutlineAcceptRequest(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_source_revision: int = Field(ge=1)
    expected_outline_revision: int = Field(ge=0)


class OutlineReopenRequest(CamelModel):
    expected_outline_revision: int = Field(ge=1)


class OutlineReturnRequest(OutlineReopenRequest):
    expected_source_revision: int = Field(ge=1)
    expected_outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_candidate_job_id: str | None = None


class SectionMapSaveRequest(CamelModel):
    expected_section_map_revision: int = Field(ge=0)
    expected_source_revision: int = Field(ge=1)
    expected_outline_revision: int = Field(ge=1)
    expected_outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    mapping: SectionMap


class SectionMapGraphInstallRequest(CamelModel):
    expected_source_revision: int = Field(ge=1)
    expected_source_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_outline_revision: int = Field(ge=1)
    expected_outline_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_section_map_revision: int = Field(ge=1)
    expected_section_map_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_graph_revision: int = Field(ge=0)
