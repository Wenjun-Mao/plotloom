"""Human identity judgments and explicit acceptance of unobservable identity."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import CamelModel


class SamePersonReviewItem(CamelModel):
    character_id: str = Field(min_length=1, max_length=128)
    judgment: Literal["pass", "fail", "unassessable"]
    identity_notes: str = Field(min_length=1, max_length=2_000)
    state_notes: str = Field(min_length=1, max_length=2_000)
    production_decision: Literal["hold", "authorize"] | None = None
    uncertainty_reason: str | None = Field(default=None, max_length=2_000)

    @field_validator("identity_notes", "state_notes", "uncertainty_reason")
    @classmethod
    def explicit_nonblank_observation(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("review observations and uncertainty reason must be nonblank")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def uncertainty_requires_separate_decision(self) -> "SamePersonReviewItem":
        if self.judgment == "unassessable":
            if self.production_decision is None or self.uncertainty_reason is None:
                raise ValueError("unassessable identity requires an explicit hold/authorize decision and framing/uncertainty reason")
        elif self.production_decision is not None or self.uncertainty_reason is not None:
            raise ValueError("uncertainty authorization belongs only to an unassessable judgment")
        return self


class SamePersonReviewRequest(CamelModel):
    binding_id: str = Field(min_length=1, max_length=36)
    expected_review_revision: int = Field(ge=0)
    reviewer: str = Field(min_length=1, max_length=160)
    comparisons: list[SamePersonReviewItem] = Field(min_length=1, max_length=8)
    notes: str = Field(min_length=1, max_length=2_000)

    @field_validator("reviewer", "notes")
    @classmethod
    def explicit_attribution(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review attribution and notes must be nonblank")
        return value.strip()

    @model_validator(mode="after")
    def character_reviews_are_distinct(self) -> "SamePersonReviewRequest":
        character_ids = [item.character_id for item in self.comparisons]
        if len(character_ids) != len(set(character_ids)):
            raise ValueError("same-person comparisons must name each character once")
        return self
