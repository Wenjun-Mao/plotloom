"""F5A contracts for raw, source-bound upstream storyboard review evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .domain import CamelModel
from .script_contracts import ScriptBinding, ScriptSectionBinding, ScriptSectionDurationCap


StoryboardReviewStatus = Literal["missing", "prepared", "candidate_ready", "accepted", "stale"]


class StoryboardReviewBinding(ScriptBinding):
    """The F4 input binding plus the exact accepted script review identity."""

    script_revision: int = Field(ge=1)
    script_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class StoryboardReviewCandidate(CamelModel):
    job_id: str = Field(pattern=r"^ch_[a-z0-9]{20,64}$")
    expected_review_revision: int = Field(ge=0)
    binding: StoryboardReviewBinding
    status: Literal["prepared", "ready", "accepted", "cancelled"]
    delivery_id: str | None = None
    manifest_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    storyboard: dict[str, Any] | None = None
    report_available: bool = False
    created_at: datetime
    delivered_at: datetime | None = None


class StoryboardReviewCandidatePreparation(StoryboardReviewCandidate):
    package_path: str
    delivery_path: str
    assignment: str


class AcceptedStoryboardReviewRevision(CamelModel):
    revision: int = Field(ge=1)
    candidate_job_id: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    binding: StoryboardReviewBinding
    storyboard: dict[str, Any]
    accepted_at: datetime


class StoryboardReviewState(CamelModel):
    candidate: StoryboardReviewCandidate | None = None
    accepted_review: AcceptedStoryboardReviewRevision | None = None
    status: StoryboardReviewStatus
    stale_reasons: list[str] = Field(default_factory=list)


class StoryboardReviewAcceptRequest(CamelModel):
    job_id: str
    expected_review_revision: int = Field(ge=0)
    binding: StoryboardReviewBinding


def ordered_episode_mapping(binding: StoryboardReviewBinding) -> list[ScriptSectionBinding]:
    """Expose F4's ordered routing seam without inventing a shot projection."""

    return binding.section_bindings


# ScriptBinding deliberately names its section members forward for its own
# module. F5A subclasses it, so resolve those same members in this module too.
StoryboardReviewBinding.model_rebuild()
