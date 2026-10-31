"""Optional attributed observations, independent of technical selection."""
from typing import Literal

from pydantic import Field, model_validator

from .domain_base import CamelModel


class IdentityQualityObservation(CamelModel):
    character_id: str = Field(min_length=1, max_length=128)
    judgment: Literal["pass", "fail", "unassessable"] | None = Field(default=None, exclude_if=lambda value: value is None)
    comment: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)
    uncertainty_reason: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)


class MaterialQualityObservation(CamelModel):
    compatibility: Literal["pass", "fail", "hold"] | None = Field(default=None, exclude_if=lambda value: value is None)
    comment: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)
    comparisons: list[IdentityQualityObservation] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def distinct_characters(self):
        ids = [item.character_id for item in self.comparisons]
        if len(ids) != len(set(ids)):
            raise ValueError("optional observations must not duplicate characters")
        return self
