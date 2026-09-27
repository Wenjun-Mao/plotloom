"""Strict project, candidate, generation and publication requests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project.name_blank")
        return value.strip()


class ProjectUpdate(ProjectCreate):
    expectedRevision: int = Field(ge=1)
    brief: str = Field(max_length=2000)
    auditionText: str = Field(max_length=160)


class ProjectDelete(StrictModel):
    expectedRevision: int = Field(ge=1)
    confirmName: str


class CandidateCreate(StrictModel):
    expectedProjectRevision: int = Field(ge=1)
    direction: str = Field(min_length=1, max_length=300)

    @field_validator("direction")
    @classmethod
    def direction_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidate.direction_blank")
        return value.strip()


class CandidateUpdate(CandidateCreate):
    expectedCandidateRevision: int = Field(ge=1)


class CandidateDelete(StrictModel):
    expectedProjectRevision: int = Field(ge=1)
    expectedCandidateRevision: int = Field(ge=1)


class GenerationCreate(StrictModel):
    expectedProjectRevision: int = Field(ge=1)
    expectedCandidateRevision: int = Field(ge=1)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)


class SelectionCreate(StrictModel):
    generationId: str = Field(pattern=r"^vg_[0-9a-f]{32}$")


class CloneCreate(StrictModel):
    projectId: str = Field(pattern=r"^vp_[0-9a-f]{32}$")
    generationId: str = Field(pattern=r"^vg_[0-9a-f]{32}$")
    text: str = Field(min_length=1, max_length=200)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("clone.text_blank")
        return value.strip()


class PublishCreate(StrictModel):
    projectId: str = Field(pattern=r"^vp_[0-9a-f]{32}$")
    generationId: str = Field(pattern=r"^vg_[0-9a-f]{32}$")
