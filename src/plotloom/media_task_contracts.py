from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from plotloom.brief_contracts import ProjectBrief
from plotloom.canonical_schema import ShotV2, StoryBibleV2
from plotloom.contract_identity import new_id, utc_now
from plotloom.domain_base import CamelModel
from plotloom.public_values import (
    contains_secret_setting,
    contains_secret_value,
    validate_public_base_urls,
)


class MediaKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MediaTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_MEDIA_TASK_STATUSES: frozenset[MediaTaskStatus] = frozenset(
    {
        MediaTaskStatus.SUCCEEDED,
        MediaTaskStatus.FAILED,
        MediaTaskStatus.CANCELLED,
    }
)


class MediaTask(CamelModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    shot_id: str
    storyboard_revision: Annotated[int, Field(ge=1)]
    kind: MediaKind
    status: MediaTaskStatus = MediaTaskStatus.QUEUED
    derived_prompt: Annotated[str, Field(min_length=1)]
    prompt_components: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    public_settings: dict[str, Any] = Field(default_factory=dict)
    provider_task_id: str | None = None
    output_uri: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("provider")
    @classmethod
    def validate_public_provider_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if contains_secret_value(normalized):
            raise ValueError("provider must be a public identifier, not a credential")
        return normalized or None

    @model_validator(mode="after")
    def validate_lifecycle_and_public_settings(self) -> MediaTask:
        if contains_secret_setting(self.public_settings) or contains_secret_value(
            self.public_settings
        ):
            raise ValueError(
                "publicSettings must not contain credentials or other secrets"
            )
        validate_public_base_urls(self.public_settings)
        if self.status == MediaTaskStatus.QUEUED:
            if self.started_at is not None or self.finished_at is not None:
                raise ValueError("queued media tasks cannot have lifecycle timestamps")
        elif self.status == MediaTaskStatus.RUNNING:
            if self.started_at is None or self.finished_at is not None:
                raise ValueError(
                    "running media tasks require startedAt and no finishedAt"
                )
        else:
            if self.started_at is None or self.finished_at is None:
                raise ValueError(
                    "terminal media tasks require startedAt and finishedAt"
                )
        if self.status == MediaTaskStatus.SUCCEEDED and not self.output_uri:
            raise ValueError("succeeded media tasks require outputUri")
        if self.status == MediaTaskStatus.FAILED and not self.error:
            raise ValueError("failed media tasks require an error")
        return self


class MediaPromptContext(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    brief: ProjectBrief
    story_bible: StoryBibleV2
    shot: ShotV2
    storyboard_revision: Annotated[int, Field(ge=1)]
