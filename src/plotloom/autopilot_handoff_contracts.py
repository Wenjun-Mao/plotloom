"""Human observations and exact current material review, never machine authority."""
from typing import Literal
from pydantic import Field, field_validator, model_validator
from .geometry_preparation_contracts import GeometryPreparation
from .domain import CamelModel, contains_secret_setting, contains_secret_value
from .managed_media import VisualIntentInput
from .same_person_review_contracts import SamePersonReviewItem
from .autopilot_materials import MaterialInventory


class ReviewAsset(CamelModel):
    asset_id: str
    original_hash: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class ReviewReference(CamelModel):
    owner: Literal["character-reference", "art-reference"]
    subject_id: str
    character_id: str | None = None
    subject_type: Literal["scene", "prop"] | None = None
    decision_id: str
    asset_id: str
    original_hash: str
    name: str
    assets: list[ReviewAsset] = Field(min_length=1, max_length=3)


class ReviewFrame(CamelModel):
    geometry_preparation: GeometryPreparation | None = Field(default=None, exclude_if=lambda value: value is None)
    shot_id: str
    scene_id: str
    title: str
    scene_name: str
    direction: str
    asset_id: str
    original_hash: str
    width: int
    height: int
    character_ids: list[str]
    description: str
    origin: Literal["machine_provisional", "human_binding"]
    source_id: str


class CurrentReviewBundle(CamelModel):
    version: Literal["pre-video.human-review.v1"] = "pre-video.human-review.v1"
    run_id: str
    material_closure: str
    inventory: MaterialInventory
    references: list[ReviewReference]
    frames: list[ReviewFrame]
    story: dict


class FrameObservation(CamelModel):
    shot_id: str
    asset_id: str
    intent: VisualIntentInput
    compatibility_note: str = Field(min_length=1, max_length=2000)
    comparisons: list[SamePersonReviewItem] = Field(max_length=8)

    @field_validator("compatibility_note")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("frame compatibility requires an authored observation")
        return value.strip()

    @model_validator(mode="after")
    def shot_role(self):
        if self.intent.role != "shot_keyframe":
            raise ValueError("handoff frame intent must have shot_keyframe role")
        ids = [item.character_id for item in self.comparisons]
        if len(ids) != len(set(ids)):
            raise ValueError("each character requires exactly one observation")
        return self


class HumanHandoffRequest(CamelModel):
    expected_run_revision: int = Field(ge=1)
    bundle_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer: str = Field(min_length=1, max_length=160)
    notes: str = Field(min_length=1, max_length=2000)
    endorsed_reference_ids: list[str]
    frames: list[FrameObservation]

    @field_validator("reviewer", "notes")
    @classmethod
    def attribution(cls, value):
        if not value.strip():
            raise ValueError("human review attribution must be nonblank")
        return value.strip()

    @model_validator(mode="after")
    def protect_credentials(self):
        raw = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(raw) or contains_secret_value(raw):
            raise ValueError("human review must not contain credentials")
        return self


class HumanHandoffReceipt(CamelModel):
    version: Literal["pre-video.handoff.v1"] = "pre-video.handoff.v1"
    id: str
    run_id: str
    project_id: str
    bundle_hash: str
    bundle: CurrentReviewBundle
    observation: HumanHandoffRequest
    approval_id: str
    approval_origin: Literal["created", "existing_human"]
    bindings: list[dict[str, str]]
    material_closure: str
