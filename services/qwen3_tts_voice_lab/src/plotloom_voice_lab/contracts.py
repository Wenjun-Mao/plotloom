"""Strict project, candidate, generation and publication requests."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CreationEngine = Literal["qwen_design", "moss_design"]
ReuseEngine = Literal["qwen_base", "index_base"]


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
    engineId: CreationEngine

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


class PairedCreation(StrictModel):
    expectedProjectRevision: int = Field(ge=1)
    directions: list[str] = Field(min_length=1, max_length=8)
    engineIds: list[CreationEngine] = Field(default_factory=lambda: ["qwen_design", "moss_design"], min_length=1, max_length=2)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def valid_designs(self):
        if len(set(self.engineIds)) != len(self.engineIds) or any(not d.strip() or len(d) > 300 for d in self.directions):
            raise ValueError("design.invalid")
        self.directions = [d.strip() for d in self.directions]
        return self


class DeliveryControl(StrictModel):
    mode: Literal["none", "text", "manual"] = "none"
    description: str | None = Field(default=None, min_length=1, max_length=300)
    vector: list[float] | None = Field(default=None, min_length=8, max_length=8)

    @model_validator(mode="after")
    def exclusive_controls(self):
        import math
        valid = ((self.mode == "none" and self.description is None and self.vector is None)
                 or (self.mode == "text" and self.description is not None and self.description.strip() and self.vector is None)
                 or (self.mode == "manual" and self.description is None and self.vector is not None))
        if not valid or (self.vector is not None and any(not math.isfinite(v) or not 0 <= v <= 1 for v in self.vector)):
            raise ValueError("delivery.invalid")
        return self


class SelectionCreate(StrictModel):
    generationId: str = Field(pattern=r"^vg_[0-9a-f]{32}$")


class CloneCreate(StrictModel):
    projectId: str = Field(pattern=r"^vp_[0-9a-f]{32}$")
    generationId: str = Field(pattern=r"^vg_[0-9a-f]{32}$")
    text: str = Field(min_length=1, max_length=200)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
    engineId: ReuseEngine
    delivery: DeliveryControl = Field(default_factory=DeliveryControl)

    @model_validator(mode="after")
    def supported_delivery(self):
        if self.engineId == "qwen_base" and self.delivery.mode != "none":
            raise ValueError("engine.delivery_unsupported")
        return self

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("clone.text_blank")
        return value.strip()


class PublishCreate(StrictModel):
    projectId: str = Field(pattern=r"^vp_[0-9a-f]{32}$")
    generationId: str = Field(pattern=r"^vg_[0-9a-f]{32}$")
