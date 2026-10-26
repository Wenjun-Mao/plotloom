from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from plotloom.brief_contracts import ProjectBrief
from plotloom.contract_identity import new_id, utc_now
from plotloom.domain_base import CamelModel
from plotloom.run_contracts import LatestRunSummary
from plotloom.stage_contracts import StageEnvelope, StageName, StageStatus


class ProjectLifecycleStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(CamelModel):
    id: str = Field(default_factory=new_id)
    revision: Annotated[int, Field(ge=1)] = 1
    lifecycle_revision: Annotated[int, Field(ge=1)] = 1
    lifecycle_status: ProjectLifecycleStatus = ProjectLifecycleStatus.ACTIVE
    archived_at: datetime | None = None
    brief: ProjectBrief | None = None
    display_title: str = "未命名项目"
    operational_state: Literal["open", "closed"] | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def require_brief(self) -> ProjectBrief:
        return ProjectBrief.require_confirmed(self.brief)

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> Project:
        if (
            self.lifecycle_status == ProjectLifecycleStatus.ACTIVE
            and self.archived_at is not None
        ):
            raise ValueError("active projects cannot have an archived_at timestamp")
        if (
            self.lifecycle_status == ProjectLifecycleStatus.ARCHIVED
            and self.archived_at is None
        ):
            raise ValueError("archived projects require an archived_at timestamp")
        return self


class ProjectCreation(Project):
    """Authoritative aggregate returned by project creation and replay."""

    stages: list[StageEnvelope]


class ProjectSummary(Project):
    stage_statuses: dict[StageName, StageStatus]
    latest_run: LatestRunSummary | None = None
    operational_state: Literal["open", "closed"] | None = None


class ProjectDuplicateResult(CamelModel):
    project: ProjectCreation
    copied_through: StageName | None = None
    omitted_stages: list[StageName]
