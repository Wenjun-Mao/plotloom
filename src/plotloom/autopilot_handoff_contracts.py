"""Human observations and exact current material review, never machine authority."""
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator, model_validator

from .autopilot_materials import MaterialInventory
from plotloom.domain_base import CamelModel
from plotloom.public_values import contains_secret_setting, contains_secret_value
from .geometry_preparation_contracts import GeometryPreparation
from .human_confirmation_contracts import UnnamedCreatorConfirmation
from .delegated_qa_contracts import AgentQaAttribution
from .operator_attribution import CodexTaskAttribution
from .managed_media import VisualIntentInput
from .cross_shot_image_contracts import CrossShotTargetUse
from .same_person_review_contracts import SamePersonReviewItem
from .bulk_material_contracts import BulkFrameObservation, SavedIntentContext
from .source_endorsed_intent import SourceEndorsedIntent
from .media_quality_observations import MaterialQualityObservation


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
    intent_context: SavedIntentContext | None = Field(default=None, exclude_if=lambda value: value is None)
    target_use: CrossShotTargetUse | None = Field(default=None, exclude_if=lambda value: value is None)
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
    version: Literal["pre-video.human-review.v1", "pre-video.human-review.v2"] = "pre-video.human-review.v2"
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
    compatibility_note: str = Field(default="", max_length=2000)
    comparisons: list[SamePersonReviewItem] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def shot_role(self):
        if self.intent.role != "shot_keyframe":
            raise ValueError("handoff frame intent must have shot_keyframe role")
        ids = [item.character_id for item in self.comparisons]
        if len(ids) != len(set(ids)):
            raise ValueError("each character requires exactly one observation")
        return self


class LegacyHumanHandoffRequest(CamelModel):
    """Retained v1 observations only; no current endpoint accepts this model."""
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


class HumanHandoffRequest(CamelModel):
    attribution: AgentQaAttribution | None = Field(default=None, exclude_if=lambda value: value is None)
    expected_run_revision: int = Field(ge=1)
    bundle_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    notes: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)
    endorsed_reference_ids: list[str]
    frames: list[FrameObservation]

    @field_validator("notes")
    @classmethod
    def optional_comment(cls, value):
        return value if value is not None and value.strip() else None

    @model_validator(mode="after")
    def protect_credentials(self):
        raw = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(raw) or contains_secret_value(raw):
            raise ValueError("human review must not contain credentials")
        return self


class HandoffReceiptFacts(CamelModel):
    id: str
    run_id: str
    project_id: str
    bundle_hash: str
    bundle: CurrentReviewBundle
    approval_id: str
    approval_origin: Literal["created", "existing_human"]
    bindings: list[dict[str, str]]
    material_closure: str


class BulkHumanHandoffRequest(HumanHandoffRequest):
    basis: Literal["whole-pack-material.v1"]
    frames: list[BulkFrameObservation]


class MaterialSelectionFrame(CamelModel):
    shot_id: str = Field(min_length=1, max_length=100)
    asset_id: str = Field(min_length=1, max_length=36)
    intent_context: SavedIntentContext
    intent: SourceEndorsedIntent | VisualIntentInput
    compatibility_note: str = Field(default="", max_length=2000)
    comparisons: list[SamePersonReviewItem] = Field(default_factory=list, max_length=8)
    quality_observation: MaterialQualityObservation | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def selection_intent(self):
        if self.intent.role != "shot_keyframe":
            raise ValueError("material selection intent must have shot_keyframe role")
        ids = [item.character_id for item in self.comparisons]
        if len(ids) != len(set(ids)):
            raise ValueError("optional identity observations must not duplicate characters")
        return self


class MaterialSelectionHandoffRequest(CamelModel):
    attribution: CodexTaskAttribution | UnnamedCreatorConfirmation | AgentQaAttribution = Field(default_factory=UnnamedCreatorConfirmation)
    expected_run_revision: int = Field(ge=1)
    bundle_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    notes: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)
    endorsed_reference_ids: list[str] = Field(default_factory=list, max_length=256)
    frames: list[MaterialSelectionFrame] = Field(max_length=256)

    @model_validator(mode="after")
    def protect_credentials(self):
        raw = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(raw) or contains_secret_value(raw):
            raise ValueError("material selection must not contain credentials")
        return self


class BulkHumanHandoffReceipt(HandoffReceiptFacts):
    version: Literal["pre-video.handoff.v3"] = "pre-video.handoff.v3"
    attribution: UnnamedCreatorConfirmation
    observation: BulkHumanHandoffRequest

    @property
    def stored_reviewer(self) -> str:
        return ""


class HumanHandoffReceipt(HandoffReceiptFacts):
    version: Literal["pre-video.handoff.v2"] = "pre-video.handoff.v2"
    attribution: UnnamedCreatorConfirmation
    observation: HumanHandoffRequest

    @property
    def stored_reviewer(self) -> str:
        return ""


class QaMaterialHandoffReceipt(HandoffReceiptFacts):
    version: Literal["pre-video.handoff.v4"] = "pre-video.handoff.v4"
    attribution: AgentQaAttribution
    observation: BulkHumanHandoffRequest

    @property
    def stored_reviewer(self) -> str:
        from .delegated_qa import reviewer_for
        return reviewer_for(self.attribution)


class LegacyHumanHandoffReceipt(HandoffReceiptFacts):
    version: Literal["pre-video.handoff.v1"] = "pre-video.handoff.v1"
    observation: LegacyHumanHandoffRequest

    @property
    def stored_reviewer(self) -> str:
        return self.observation.reviewer


class MaterialSelectionHandoffReceipt(HandoffReceiptFacts):
    version: Literal["pre-video.handoff.v5"] = "pre-video.handoff.v5"
    attribution: CodexTaskAttribution | UnnamedCreatorConfirmation | AgentQaAttribution
    observation: MaterialSelectionHandoffRequest

    @property
    def stored_reviewer(self) -> str:
        if isinstance(self.attribution, UnnamedCreatorConfirmation):
            return ""
        if isinstance(self.attribution, CodexTaskAttribution):
            return f"Codex task {self.attribution.task_id}"
        from .delegated_qa import reviewer_for
        return reviewer_for(self.attribution)


_receipt_reader = TypeAdapter(Annotated[QaMaterialHandoffReceipt | BulkHumanHandoffReceipt | HumanHandoffReceipt | LegacyHumanHandoffReceipt | MaterialSelectionHandoffReceipt, Field(discriminator="version")])


def parse_handoff_receipt(raw) -> QaMaterialHandoffReceipt | BulkHumanHandoffReceipt | HumanHandoffReceipt | LegacyHumanHandoffReceipt | MaterialSelectionHandoffReceipt:
    receipt = _receipt_reader.validate_python(raw)
    # The retained v1 observation has an `attribution` validator method, not
    # an actor field. Discriminate the typed receipt before reading actor data.
    if isinstance(receipt, (LegacyHumanHandoffReceipt, MaterialSelectionHandoffReceipt)):
        if isinstance(receipt, MaterialSelectionHandoffReceipt) and receipt.observation.attribution != receipt.attribution:
            raise ValueError("material selection attribution differs from its retained receipt")
        return receipt
    actor = receipt.observation.attribution
    if isinstance(receipt, QaMaterialHandoffReceipt):
        if actor != receipt.attribution:
            raise ValueError("QA handoff observation attribution differs")
    elif actor is not None:
        raise ValueError("creator receipt cannot retain an agent QA observation")
    return receipt
