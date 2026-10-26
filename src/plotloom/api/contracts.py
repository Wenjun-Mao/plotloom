from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from ..delegated_qa_contracts import AgentQaAttribution
from plotloom.stage_contracts import STAGE_ORDER, AuthoringDraftScope, InitialStage, StageEnvelope, StageHead, StageName, validate_initial_stage_prefix
from plotloom.domain_base import CamelModel
from plotloom.gate_contracts import GateEvaluation
from plotloom.run_contracts import GenerationRun
from plotloom.media_task_contracts import MediaTask
from plotloom.brief_contracts import ProjectBrief
from plotloom.project_contracts import ProjectSummary
from plotloom.provider_contracts import ProviderAuthMode, ProviderProfileCapabilities
from plotloom.public_values import contains_secret_setting, contains_secret_value, validate_public_api_root
from ..human_confirmation_contracts import UnnamedCreatorConfirmation
from ..image_job_contracts import (
    ImageJobCreateRequest,
)
from ..managed_media import (
    VisualIntentInput,
)
from ..provider_profiles import (
    PROFILE_ID_PATTERN,
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
)


class ProjectCreateRequest(CamelModel):
    brief: ProjectBrief | None = None
    initial_stages: list[InitialStage] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_initial_stages(self) -> ProjectCreateRequest:
        validate_initial_stage_prefix(self.initial_stages)
        if self.brief is None and self.initial_stages:
            raise ValueError("draft-only projects cannot install canonical stages")
        return self


class ProjectPatchRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    brief: ProjectBrief
    consumed_draft: "CanonicalDraftConsumption | None" = None


class LifecycleRequest(CamelModel):
    expected_lifecycle_revision: int = Field(ge=1)


class ProjectDuplicateRequest(LifecycleRequest):
    title: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title must not be blank")
        return value


class ProjectPermanentDeleteRequest(LifecycleRequest):
    expected_project_revision: int = Field(ge=1)
    confirmation_title: str = Field(min_length=1, max_length=200)
    scope_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @field_validator("confirmation_title")
    @classmethod
    def reject_blank_confirmation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("confirmationTitle must not be blank")
        return value


class ProjectAbandonDeleteRequest(ProjectPermanentDeleteRequest):
    preview_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    acknowledge_unknown_remote: bool = False


class ProjectDeletionStopRequest(ProjectPermanentDeleteRequest):
    scope_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_run_id: str = Field(min_length=1)
    expected_run_revision: int = Field(ge=1)


class ProjectListResponse(CamelModel):
    projects: list[ProjectSummary]
    next_cursor: str | None = None


class ProjectOperationalState(CamelModel):
    """Explicit local-folder admission state, not author lifecycle state."""

    project_id: str
    state: Literal["open", "closed"]
    revision: int = Field(ge=1)


class StageEnvelopesResponse(CamelModel):
    stages: list[StageEnvelope]


class ProjectRunsResponse(CamelModel):
    runs: list[GenerationRun]


class ProjectMediaTasksResponse(CamelModel):
    tasks: list[MediaTask]


class StagePatchRequest(CamelModel):
    expected_revision: int = Field(ge=0)
    payload: dict[str, Any]
    consumed_draft: "CanonicalDraftConsumption | None" = None


class CanonicalDraftConsumption(CamelModel):
    """The exact server-acknowledged buffer a canonical save may consume."""

    editor_scope: AuthoringDraftScope
    entity_id: str = Field(min_length=1, max_length=160)
    draft_revision: int = Field(ge=1)


class ProjectFolderVisualIntentRequest(VisualIntentInput):
    """A visual-intent save bound to one acknowledged project draft."""

    shot_id: str = Field(min_length=1, max_length=100)
    consumed_draft: CanonicalDraftConsumption


class ProjectFolderImageJobCreateRequest(ImageJobCreateRequest):
    """A manual job whose direction must match its CAS draft receipt."""

    context_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    consumed_draft: CanonicalDraftConsumption


class AuthoringDraftUpsertRequest(CamelModel):
    editor_scope: AuthoringDraftScope
    entity_id: str = Field(min_length=1, max_length=160)
    base_canonical_revision: int = Field(ge=0)
    expected_draft_revision: int = Field(ge=0)
    payload: dict[str, Any]


class AuthoringDraftDiscardRequest(CamelModel):
    editor_scope: AuthoringDraftScope
    entity_id: str = Field(min_length=1, max_length=160)
    expected_draft_revision: int = Field(ge=1)


class StoryboardApprovalRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approve", "revoke"]
    attribution: UnnamedCreatorConfirmation | AgentQaAttribution
    gate_set_version: str = Field(min_length=1, max_length=128)

    @field_validator("gate_set_version")
    @classmethod
    def reject_blank_review_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("gateSetVersion must not be blank")
        return normalized


class ApprovalDecisionView(CamelModel):
    id: str
    project_id: str
    entity_revision_id: str
    subject_type: str
    subject_id: str
    subject_revision: int
    content_hash: str
    canonical_input_revisions: dict[StageName, int]
    gate_set_version: str
    decision: Literal["approve", "revoke"]
    reviewer: str
    attribution: UnnamedCreatorConfirmation | AgentQaAttribution | None = Field(default=None, exclude_if=lambda value: value is None)
    note: str | None
    created_at: datetime


class ApprovalClosureView(CamelModel):
    decision: ApprovalDecisionView
    active: bool
    stale_reasons: list[str]


class StoryboardReviewResponse(CamelModel):
    head: StageHead
    gate_evaluation: GateEvaluation | None
    decisions: list[ApprovalClosureView]
    active_approval: ApprovalDecisionView | None


class PipelineRunRequest(CamelModel):
    stages: list[StageName] | None = Field(default=None, min_length=1)
    instructions: str | None = None
    provider_profile_id: str | None = Field(default=None, pattern=PROFILE_ID_PATTERN)

    @model_validator(mode="after")
    def reject_duplicate_stages(self) -> PipelineRunRequest:
        if self.stages is not None and len(self.stages) != len(set(self.stages)):
            raise ValueError("stages must not contain duplicates")
        if self.stages:
            first_index = STAGE_ORDER.index(self.stages[0])
            expected = list(STAGE_ORDER[first_index : first_index + len(self.stages)])
            if self.stages != expected:
                raise ValueError(
                    "stages must form one contiguous canonical stage range"
                )
        return self


class RebuildRequest(CamelModel):
    from_stage: StageName
    through_stage: StageName | None = None
    instructions: str | None = None
    provider_profile_id: str | None = Field(default=None, pattern=PROFILE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_range(self) -> RebuildRequest:
        if self.through_stage is not None and STAGE_ORDER.index(
            self.through_stage
        ) < STAGE_ORDER.index(self.from_stage):
            raise ValueError("throughStage must not precede fromStage")
        return self


class ExactWorkUnitRepairRequest(CamelModel):
    """A deliberately empty command body.

    Exact repair replays the frozen author/model contract for one rejected
    work unit. New guidance belongs to the separate whole-stage rebuild flow;
    accepting it here would silently change the target input hash.
    """


class TextProviderProfileView(CamelModel):
    profile_id: str
    display_name: str
    configuration: TextProviderProfileSnapshot | TextProviderProfileSnapshotV3
    revision: int
    enabled: bool
    availability_revision: int
    adapter_id: str
    adapter_version: str
    created_at: datetime
    updated_at: datetime
    server_key_available: bool
    readiness: "TextBackendReadiness"


class TextProviderProfilesResponse(CamelModel):
    profiles: list[TextProviderProfileView]
    active_profile_id: str
    selection_revision: int
    presets: dict[str, dict[str, Any]]
    trusted_adapters: list[dict[str, str]]


class TextProviderProfileCreate(CamelModel):
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    display_name: str = Field(min_length=1, max_length=120)
    configuration: dict[str, Any] | None = None
    copy_from_profile_id: str | None = Field(default=None, pattern=PROFILE_ID_PATTERN)
    adapter_id: str | None = Field(default=None, min_length=1, max_length=120)
    adapter_version: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def require_one_configuration_source(self) -> "TextProviderProfileCreate":
        if (self.configuration is None) == (self.copy_from_profile_id is None):
            raise ValueError(
                "provide exactly one of configuration or copyFromProfileId"
            )
        if (self.adapter_id is None) != (self.adapter_version is None):
            raise ValueError("adapterId and adapterVersion must be provided together")
        if contains_secret_setting(self.configuration) or contains_secret_value(
            self.configuration
        ):
            raise ValueError("text provider profiles must not contain secrets")
        return self


class TextProviderProfileUpdate(CamelModel):
    expected_revision: int = Field(ge=0)
    display_name: str = Field(min_length=1, max_length=120)
    configuration: dict[str, Any]
    adapter_id: str | None = Field(default=None, min_length=1, max_length=120)
    adapter_version: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def reject_profile_secrets(self) -> "TextProviderProfileUpdate":
        if (self.adapter_id is None) != (self.adapter_version is None):
            raise ValueError("adapterId and adapterVersion must be provided together")
        if contains_secret_setting(self.configuration) or contains_secret_value(
            self.configuration
        ):
            raise ValueError("text provider profiles must not contain secrets")
        return self


class TextProviderProfileActivate(CamelModel):
    expected_selection_revision: int = Field(ge=0)


class TextProviderProfileAvailabilityUpdate(CamelModel):
    expected_availability_revision: int = Field(ge=0)
    enabled: bool


class TextBackendReadiness(CamelModel):
    profile_id: str
    profile_revision: int
    state: Literal[
        "disabled",
        "missing_configuration",
        "unverified",
        "checking",
        "available",
        "unreachable",
        "authentication_failed",
        "model_mismatch",
        "capability_mismatch",
    ]
    reason_code: str
    observed_at: datetime | None = None


class TextProviderProbeResponse(TextBackendReadiness):
    """The explicit probe returns the same secret-free observation shown in UI."""




class ImageJobCancellationRequest(CamelModel):
    reason: str = Field(min_length=1, max_length=2_000)


class ProviderSettingsUpdate(CamelModel):
    expected_profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    expected_revision: int = Field(ge=0)
    text_provider: str | None = None
    text_base_url: str | None = None
    text_model: str | None = None
    text_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER
    text_capabilities: ProviderProfileCapabilities = Field(
        default_factory=ProviderProfileCapabilities
    )
    text_context_window_tokens: int = Field(default=32_768, ge=1)
    text_max_output_tokens: int = Field(default=8_192, ge=1)
    text_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    text_max_concurrency: int = Field(default=1, ge=1, le=32)
    text_connect_timeout_seconds: float = Field(default=10.0, gt=0.0, le=300.0)
    text_attempt_timeout_seconds: float = Field(default=300.0, gt=0.0, le=3_600.0)
    image_provider: str | None = None
    image_base_url: str | None = None
    image_model: str | None = None
    image_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER
    video_provider: str | None = None
    video_base_url: str | None = None
    video_model: str | None = None
    video_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER

    @model_validator(mode="before")
    @classmethod
    def reject_secret_material(cls, value: Any) -> Any:
        if contains_secret_setting(value) or contains_secret_value(value):
            raise ValueError("public provider configuration must not contain secrets")
        return value

    @field_validator("text_base_url", "image_base_url", "video_base_url")
    @classmethod
    def validate_provider_api_root(cls, value: str | None) -> str | None:
        return validate_public_api_root(value)
