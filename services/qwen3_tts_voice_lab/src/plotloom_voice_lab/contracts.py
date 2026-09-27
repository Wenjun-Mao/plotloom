"""Request contracts for bounded synthetic voice casting."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoundCreate(StrictModel):
    auditionText: str = Field(min_length=1, max_length=160)
    directions: list[str] = Field(min_length=2, max_length=8)

    @field_validator("auditionText")
    @classmethod
    def audition_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("audition text cannot be blank")
        return value.strip()

    @field_validator("directions")
    @classmethod
    def validate_directions(cls, value: list[str]) -> list[str]:
        if len(value) not in {2, 4, 6, 8}:
            raise ValueError("candidate count must be 2, 4, 6, or 8")
        if any(not item.strip() or len(item) > 300 for item in value):
            raise ValueError("each direction must contain 1-300 characters")
        return [item.strip() for item in value]


class SelectionCreate(StrictModel):
    candidateId: str = Field(pattern=r"^vc_[0-9a-f]{32}$")


class CloneCreate(StrictModel):
    candidateId: str = Field(pattern=r"^vc_[0-9a-f]{32}$")
    text: str = Field(min_length=1, max_length=200)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text cannot be blank")
        return value.strip()
