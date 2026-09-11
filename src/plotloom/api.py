from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic
from typing import Annotated, Any, Callable, Literal, Mapping, Protocol

from fastapi import FastAPI, HTTPException, Header, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, ValidationError, field_validator, model_validator

from .domain import (
    PUBLIC_PROVIDER_SETTING_FIELDS,
    STAGE_ORDER,
    CamelModel,
    GenerationRun,
    GateEvaluation,
    InitialStage,
    MediaKind,
    MediaPromptContext,
    MediaTask,
    Project,
    ProjectBrief,
    ProjectCreation,
    ProjectDuplicateResult,
    ProjectLifecycleStatus,
    ProjectSummary,
    ProviderAuthMode,
    ProviderProfileCapabilities,
    ProviderSettings,
    ProviderSnapshot,
    RunKind,
    RunExecutionTrace,
    RunProgress,
    RunTrace,
    StageEnvelope,
    StageHead,
    StageName,
    contains_secret_setting,
    contains_secret_value,
    validate_public_api_root,
    validate_public_provider_snapshot,
    validate_initial_stage_prefix,
)
from .exceptions import (
    BootstrapContentionError,
    IdempotencyConflictError,
    InvalidTransitionError,
    LifecycleContentionError,
    NotFoundError,
    ProductionPipelineNotReadyError,
    ProjectBusyError,
    RepairEligibilityError,
    RevisionConflictError,
    SchemaResetRequiredError,
    StagePrerequisiteError,
)
from .persistence import ApprovalClosure, ApprovalDecision, SQLiteRepository
from .provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PROFILE_ID_PATTERN,
    PresetId,
    ProviderProfileSelection,
    StageMaxOutputTokens,
    TextProviderCapabilities,
    TextProviderProfile,
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    V2ExtractionPolicy,
    execution_preset,
    preset_values,
)
from .generation.contracts import ProviderCapabilities
from .generation.exceptions import SecretLeaseError
from .generation.providers import ProviderAdapter
from .generation.secrets import InMemorySecretVault, SecretLease
from .generation.story_graph_topology import StoryGraphTopologyError
from .text_adapters import DEFAULT_TEXT_ADAPTER_REGISTRY
from .validation import DomainValidationError, STORYBOARD_GATE_SET_VERSION, pydantic_issues


class RunScheduler(Protocol):
    def submit(self, run_id: str, *, session_api_key: str | None = None) -> Any: ...

    def request_cancel(self, run_id: str) -> GenerationRun: ...


class MediaScheduler(Protocol):
    def submit(self, task_id: str, *, session_api_key: str | None = None) -> Any: ...


class MediaPromptCompiler(Protocol):
    def compile(self, context: MediaPromptContext, kind: MediaKind) -> tuple[str, dict[str, Any]]: ...


class TextProviderResolver(Protocol):
    def resolve(self, provider_snapshot: Mapping[str, Any]) -> tuple[ProviderAdapter, str]: ...


class TextProfileSecretSource(Protocol):
    def server_key_available(self, profile_id: str = "default") -> bool: ...

    def lease_for_profile(
        self,
        profile_id: str,
        *,
        auth_mode: ProviderAuthMode,
    ) -> SecretLease | None: ...


class ProjectCreateRequest(CamelModel):
    brief: ProjectBrief
    initial_stages: list[InitialStage] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_initial_stages(self) -> ProjectCreateRequest:
        validate_initial_stage_prefix(self.initial_stages)
        return self


class ProjectPatchRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    brief: ProjectBrief


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
    confirmation_title: str = Field(min_length=1, max_length=200)

    @field_validator("confirmation_title")
    @classmethod
    def reject_blank_confirmation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("confirmationTitle must not be blank")
        return value


class ProjectListResponse(CamelModel):
    projects: list[ProjectSummary]
    next_cursor: str | None = None


class StageEnvelopesResponse(CamelModel):
    stages: list[StageEnvelope]


class ProjectRunsResponse(CamelModel):
    runs: list[GenerationRun]


class ProjectMediaTasksResponse(CamelModel):
    tasks: list[MediaTask]


class StagePatchRequest(CamelModel):
    expected_revision: int = Field(ge=0)
    payload: dict[str, Any]


class StoryboardApprovalRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approve", "revoke"]
    reviewer: str = Field(
        min_length=1,
        max_length=256,
        description="User-supplied local-workbench label; not an authenticated identity.",
    )
    gate_set_version: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=4_000)

    @field_validator("reviewer", "gate_set_version")
    @classmethod
    def reject_blank_review_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reviewer and gateSetVersion must not be blank")
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
                raise ValueError("stages must form one contiguous canonical stage range")
        return self


class RebuildRequest(CamelModel):
    from_stage: StageName
    through_stage: StageName | None = None
    instructions: str | None = None
    provider_profile_id: str | None = Field(default=None, pattern=PROFILE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_range(self) -> RebuildRequest:
        if self.through_stage is not None and STAGE_ORDER.index(self.through_stage) < STAGE_ORDER.index(self.from_stage):
            raise ValueError("throughStage must not precede fromStage")
        return self


class RepairRequest(CamelModel):
    stage: StageName | None = None
    instructions: str | None = None
    provider_profile_id: str | None = Field(default=None, pattern=PROFILE_ID_PATTERN)


class ExactWorkUnitRepairRequest(CamelModel):
    """A deliberately empty command body.

    Exact repair replays the frozen author/model contract for one rejected
    work unit. New guidance belongs to the separate whole-stage rebuild flow;
    accepting it here would silently change the target input hash.
    """


class TextProviderProfileView(CamelModel):
    profile_id: str
    display_name: str
    configuration: TextProviderProfileSnapshot
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

    @model_validator(mode="after")
    def require_one_configuration_source(self) -> "TextProviderProfileCreate":
        if (self.configuration is None) == (self.copy_from_profile_id is None):
            raise ValueError("provide exactly one of configuration or copyFromProfileId")
        if contains_secret_setting(self.configuration) or contains_secret_value(self.configuration):
            raise ValueError("text provider profiles must not contain secrets")
        return self


class TextProviderProfileUpdate(CamelModel):
    expected_revision: int = Field(ge=0)
    display_name: str = Field(min_length=1, max_length=120)
    configuration: dict[str, Any]

    @model_validator(mode="after")
    def reject_profile_secrets(self) -> "TextProviderProfileUpdate":
        if contains_secret_setting(self.configuration) or contains_secret_value(self.configuration):
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
        "disabled", "missing_configuration", "unverified", "checking", "available",
        "unreachable", "authentication_failed", "model_mismatch", "capability_mismatch",
    ]
    reason_code: str
    observed_at: datetime | None = None


class TextProviderProbeResponse(TextBackendReadiness):
    """The explicit probe returns the same secret-free observation shown in UI."""


def _session_api_key(request: Request) -> str | None:
    value = (request.headers.get("X-Plotloom-Session-API-Key") or "").strip()
    if len(value) > 4096:
        raise HTTPException(status_code=400, detail="session API key is too long")
    return value or None


def _normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Idempotency-Key must not be blank")
    if len(normalized) > 255:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be at most 255 characters")
    return normalized


def _encode_project_cursor(cursor: tuple[datetime, str] | None) -> str | None:
    if cursor is None:
        return None
    created_at, project_id = cursor
    payload = json.dumps(
        {"createdAt": created_at.isoformat(), "id": project_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_project_cursor(value: str | None) -> tuple[datetime, str] | None:
    if value is None:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if set(payload) != {"createdAt", "id"} or not isinstance(payload["id"], str):
            raise ValueError("wrong cursor shape")
        created_at = datetime.fromisoformat(payload["createdAt"])
        if created_at.tzinfo is not None:
            raise ValueError("cursor timestamp must use the database's local UTC representation")
        if not payload["id"]:
            raise ValueError("blank project ID")
        return created_at, payload["id"]
    except (TypeError, ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid project cursor") from error


def _submit_with_optional_session_key(scheduler: Any, resource_id: str, request: Request) -> Any:
    session_key = _session_api_key(request)
    if session_key is None:
        return scheduler.submit(resource_id)
    return scheduler.submit(resource_id, session_api_key=session_key)


class MediaTaskRequest(CamelModel):
    kind: MediaKind
    provider: str | None = None
    public_settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_secrets(self) -> MediaTaskRequest:
        if contains_secret_value(self.provider):
            raise ValueError("provider must be a public identifier, not a credential")
        if self.provider is not None:
            raise ValueError(
                "media tasks cannot override the provider; save a trusted provider profile first"
            )
        if contains_secret_setting(self.public_settings) or contains_secret_value(
            self.public_settings
        ):
            raise ValueError("publicSettings must not contain API keys, tokens, credentials, or other secrets")
        for key in self.public_settings:
            normalized = "".join(character for character in str(key).lower() if character.isalnum())
            if (
                normalized.endswith("baseurl")
                or normalized.endswith("endpoint")
                or normalized.endswith("authmode")
                or normalized.endswith("provider")
                or normalized.endswith("model")
            ):
                raise ValueError(
                    "media tasks cannot override the trusted provider profile; save profile settings first"
                )
        return self


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


def _merge_provider_settings(
    persisted: ProviderSettings,
    defaults: ProviderSettings,
    key_availability: Mapping[str, bool],
) -> ProviderSettings:
    if persisted.revision == 0:
        # No row means environment-owned defaults still define the profile.
        values = {
            field: getattr(defaults, field) for field in PUBLIC_PROVIDER_SETTING_FIELDS
        }
    else:
        values = {
            field: getattr(persisted, field)
            if getattr(persisted, field) is not None
            else getattr(defaults, field)
            for field in PUBLIC_PROVIDER_SETTING_FIELDS
        }
    values.update(
        profile_version=persisted.revision,
        revision=persisted.revision,
        updated_at=persisted.updated_at,
        text_key_available=bool(key_availability.get("text_key_available", False)),
        image_key_available=bool(key_availability.get("image_key_available", False)),
        video_key_available=bool(key_availability.get("video_key_available", False)),
    )
    return ProviderSettings.model_validate(values)


def _public_provider_snapshot(settings: ProviderSettings) -> dict[str, Any]:
    snapshot = ProviderSnapshot.model_validate(
        settings.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields),
        )
    )
    return validate_public_provider_snapshot(snapshot.model_dump(mode="json", by_alias=True))


def _default_text_profile_snapshot(defaults: ProviderSettings) -> TextProviderProfileSnapshot:
    """Translate the old runtime defaults into the first V2 named profile."""

    preset = execution_preset(PresetId.COMPATIBLE_V1)
    values: dict[str, Any] = {
        "profile_schema_version": 2,
        "profile_id": DEFAULT_PROVIDER_PROFILE_ID,
        "profile_version": 0,
        "text_provider": defaults.text_provider or "openai-compatible",
        "text_base_url": defaults.text_base_url or "https://api.atlascloud.ai/v1",
        "text_model": defaults.text_model or "deepseek-v3",
        "text_auth_mode": defaults.text_auth_mode.value,
        "text_capabilities": TextProviderCapabilities(
            chat_completions=defaults.text_capabilities.chat_completions,
            json_object=defaults.text_capabilities.json_object,
            json_schema=defaults.text_capabilities.json_schema,
            chat_template_kwargs=False,
        ),
        "text_context_window_tokens": defaults.text_context_window_tokens,
        "text_max_output_tokens": defaults.text_max_output_tokens,
        "text_temperature": defaults.text_temperature,
        "text_max_concurrency": defaults.text_max_concurrency,
        "text_connect_timeout_seconds": defaults.text_connect_timeout_seconds,
        "text_attempt_timeout_seconds": defaults.text_attempt_timeout_seconds,
        "redirect_policy": "no_follow",
        "request_extension": preset.request_extension,
        "reasoning_mode": preset.reasoning_mode,
        "extraction_policy": V2ExtractionPolicy(),
        "stage_max_output_tokens": StageMaxOutputTokens(
            story_bible=min(8192, defaults.text_max_output_tokens),
            story_graph=min(8192, defaults.text_max_output_tokens),
            scene_beats=min(4096, defaults.text_max_output_tokens),
            storyboard=min(4096, defaults.text_max_output_tokens),
        ),
        "max_semantic_corrections": 2,
        "preset_id": PresetId.COMPATIBLE_V1,
        "preset_version": preset.preset_version,
    }
    try:
        return TextProviderProfileSnapshot.model_validate(values)
    except ValueError:
        values["preset_id"] = PresetId.CUSTOM
        return TextProviderProfileSnapshot.model_validate(values)


def _approval_decision_view(decision: ApprovalDecision) -> ApprovalDecisionView:
    return ApprovalDecisionView(
        id=decision.id,
        project_id=decision.project_id,
        entity_revision_id=decision.entity_revision_id,
        subject_type=decision.subject_type,
        subject_id=decision.subject_id,
        subject_revision=decision.subject_revision,
        content_hash=decision.content_hash,
        canonical_input_revisions=dict(decision.canonical_input_revisions),
        gate_set_version=decision.gate_set_version,
        decision=decision.decision,
        reviewer=decision.reviewer,
        note=decision.note,
        created_at=decision.created_at,
    )


def _approval_closure_view(closure: ApprovalClosure) -> ApprovalClosureView:
    return ApprovalClosureView(
        decision=_approval_decision_view(closure.decision),
        active=closure.active,
        stale_reasons=list(closure.stale_reasons),
    )


def create_app(
    repository: SQLiteRepository | None = None,
    *,
    run_scheduler: RunScheduler | None = None,
    media_scheduler: MediaScheduler | None = None,
    media_prompt_compiler: MediaPromptCompiler | None = None,
    static_dir: Path | None = None,
    provider_defaults: ProviderSettings | None = None,
    key_availability: Mapping[str, bool] | None = None,
    text_profile_default: TextProviderProfileSnapshot | None = None,
    profile_key_available: Callable[[str], bool] | None = None,
    text_provider_resolver: TextProviderResolver | None = None,
    text_secret_source: TextProfileSecretSource | None = None,
    lifespan: Any | None = None,
) -> FastAPI:
    repo = repository or SQLiteRepository()
    public_defaults = provider_defaults or ProviderSettings()
    availability = dict(key_availability or {})
    repo.bootstrap_default_text_provider_profile(
        text_profile_default or _default_text_profile_snapshot(public_defaults)
    )
    app = FastAPI(title="Plotloom", version="2.0.0", lifespan=lifespan)
    app.state.repository = repo
    app.state.run_scheduler = run_scheduler
    app.state.media_scheduler = media_scheduler
    # Observations are intentionally application-lifetime state: no secrets,
    # no persistence, and no implication that a profile is qualified.
    readiness_observations: dict[str, TextBackendReadiness] = {}

    def has_server_key(profile_id: str) -> bool:
        if profile_key_available is not None:
            return bool(profile_key_available(profile_id))
        if text_secret_source is not None:
            return bool(text_secret_source.server_key_available(profile_id))
        return profile_id == DEFAULT_PROVIDER_PROFILE_ID and bool(
            availability.get("text_key_available", False)
        )

    def active_text_profile() -> TextProviderProfile:
        selection = repo.get_provider_profile_selection()
        return repo.get_text_provider_profile(selection.active_profile_id)

    def provider_settings_projection(
        profile: TextProviderProfile,
        media: ProviderSettings,
    ) -> ProviderSettings:
        """Project one text profile and the global media singleton."""

        text = profile.configuration
        return ProviderSettings(
            profile_id=profile.profile_id,
            text_provider=text.text_provider,
            text_base_url=text.text_base_url,
            text_model=text.text_model,
            text_auth_mode=ProviderAuthMode(text.text_auth_mode),
            text_capabilities=ProviderProfileCapabilities(
                chat_completions=text.text_capabilities.chat_completions,
                json_object=text.text_capabilities.json_object,
                json_schema=text.text_capabilities.json_schema,
            ),
            text_context_window_tokens=text.text_context_window_tokens,
            text_max_output_tokens=text.text_max_output_tokens,
            text_temperature=text.text_temperature,
            text_max_concurrency=text.text_max_concurrency,
            text_connect_timeout_seconds=text.text_connect_timeout_seconds,
            text_attempt_timeout_seconds=text.text_attempt_timeout_seconds,
            image_provider=media.image_provider,
            image_base_url=media.image_base_url,
            image_model=media.image_model,
            image_auth_mode=media.image_auth_mode,
            video_provider=media.video_provider,
            video_base_url=media.video_base_url,
            video_model=media.video_model,
            video_auth_mode=media.video_auth_mode,
            profile_version=profile.revision,
            profile_hash=text.profile_hash,
            text_key_available=has_server_key(profile.profile_id),
            image_key_available=media.image_key_available,
            video_key_available=media.video_key_available,
            revision=profile.revision,
            updated_at=profile.updated_at,
        )

    def effective_provider_settings() -> ProviderSettings:
        """Compatibility projection: active text profile plus global media settings."""

        media = _merge_provider_settings(repo.get_provider_settings(), public_defaults, availability)
        return provider_settings_projection(active_text_profile(), media)

    def provider_snapshot(profile_id: str | None = None) -> dict[str, Any]:
        selected = (
            repo.get_text_provider_profile(profile_id)
            if profile_id is not None
            else active_text_profile()
        )
        if not selected.enabled:
            raise InvalidTransitionError(
                f"text provider profile {selected.profile_id} is disabled; enable it before admitting a new run"
            )
        # Existing V2 profile settings keep their exact stored/hash contract.
        # Only a newly admitted run gets the additive V3 frozen adapter fields.
        values = selected.configuration.model_dump(
            mode="python", by_alias=False, exclude={"profile_hash"}
        )
        values.update(
            profile_schema_version=3,
            profile_id=selected.profile_id,
            profile_version=selected.revision,
            profile_hash="",
            adapter_id=selected.adapter_id,
            adapter_version=selected.adapter_version,
        )
        return TextProviderProfileSnapshotV3.model_validate(values).model_dump(
            mode="json", by_alias=True
        )

    def readiness_for(profile: TextProviderProfile) -> TextBackendReadiness:
        if not profile.enabled:
            return TextBackendReadiness(
                profile_id=profile.profile_id, profile_revision=profile.revision,
                state="disabled", reason_code="readiness.profile_disabled",
            )
        observation = readiness_observations.get(profile.profile_id)
        if observation is None or observation.profile_revision != profile.revision:
            return TextBackendReadiness(
                profile_id=profile.profile_id, profile_revision=profile.revision,
                state="unverified", reason_code="readiness.not_checked",
            )
        return observation

    def store_readiness(
        profile: TextProviderProfile, state: str, reason_code: str
    ) -> TextBackendReadiness:
        observation = TextBackendReadiness(
            profile_id=profile.profile_id, profile_revision=profile.revision,
            state=state, reason_code=reason_code,
            observed_at=datetime.now(timezone.utc),
        )
        readiness_observations[profile.profile_id] = observation
        return observation

    def profile_view(profile: TextProviderProfile) -> TextProviderProfileView:
        return TextProviderProfileView(
            **profile.model_dump(mode="python"),
            server_key_available=has_server_key(profile.profile_id),
            readiness=readiness_for(profile),
        )

    def profiles_response() -> TextProviderProfilesResponse:
        selection = repo.get_provider_profile_selection()
        return TextProviderProfilesResponse(
            profiles=[profile_view(profile) for profile in repo.list_text_provider_profiles()],
            active_profile_id=selection.active_profile_id,
            selection_revision=selection.revision,
            presets={
                preset.value: preset_values(preset)
                for preset in (
                    PresetId.COMPATIBLE_V1,
                    PresetId.QUALITY_REASONING_V1,
                    PresetId.FINAL_ONLY_V1,
                )
            },
            trusted_adapters=DEFAULT_TEXT_ADAPTER_REGISTRY.supported(),
        )

    def text_submission_session_key(
        snapshot: Mapping[str, Any], request: Request
    ) -> str | None:
        """Resolve request-scoped auth without touching a key for authMode=none."""

        auth_mode = str(
            snapshot.get("textAuthMode")
            or snapshot.get("text_auth_mode")
            or ProviderAuthMode.BEARER.value
        )
        if auth_mode == ProviderAuthMode.NONE.value:
            return None
        profile_id = str(
            snapshot.get("profileId")
            or snapshot.get("profile_id")
            or DEFAULT_PROVIDER_PROFILE_ID
        )
        session_key = _session_api_key(request)
        if session_key is None and not has_server_key(profile_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"text provider profile {profile_id!r} requires a server key "
                    "or a browser-session key"
                ),
            )
        return session_key

    def submit_text_run(run: GenerationRun, request: Request) -> None:
        if run_scheduler is None:
            return
        session_key = text_submission_session_key(run.provider_snapshot, request)
        try:
            if session_key is None:
                run_scheduler.submit(run.id)
            else:
                run_scheduler.submit(run.id, session_api_key=session_key)
        except SecretLeaseError as error:
            # Safe restart recovery can leave a bearer run queued while its
            # browser-only credential is unavailable.  It remains resumable;
            # never turn the missing ephemeral value into durable evidence.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="this queued run needs its profile's browser-session key",
            ) from error

    def check_text_backend(
        profile: TextProviderProfile,
        request: Request,
        *,
        snapshot: Mapping[str, Any] | None = None,
        record_observation: bool = True,
    ) -> TextBackendReadiness:
        """Perform one optional non-generative adapter preflight.

        A missing cheap check is explicitly unverified.  The temporary browser
        lease is never stored in the observation or profile state.
        """

        if not profile.enabled and snapshot is None:
            return readiness_for(profile)
        frozen_snapshot = snapshot or provider_snapshot(profile.profile_id)

        def observed(state: str, reason_code: str) -> TextBackendReadiness:
            if record_observation:
                return store_readiness(profile, state, reason_code)
            return TextBackendReadiness(
                profile_id=str(
                    frozen_snapshot.get("profileId")
                    or frozen_snapshot.get("profile_id")
                    or profile.profile_id
                ),
                profile_revision=int(
                    frozen_snapshot.get("profileVersion")
                    or frozen_snapshot.get("profile_version")
                    or profile.revision
                ),
                state=state,
                reason_code=reason_code,
            )
        # Lightweight embedding/tests that do not install a runtime resolver
        # cannot claim a protocol preflight.  They remain explicitly
        # unverified; the production runtime always injects its resolver.
        if text_provider_resolver is None:
            return observed("unverified", "readiness.check_unsupported")
        temporary_vault: InMemorySecretVault | None = None
        lease: SecretLease | None = None
        try:
            if frozen_snapshot["textAuthMode"] == ProviderAuthMode.BEARER.value:
                session_key = _session_api_key(request)
                if session_key is not None:
                    temporary_vault = InMemorySecretVault()
                    temporary_vault.put("preflight", session_key)
                    lease = temporary_vault.lease("preflight", ttl_seconds=60, max_uses=1)
                elif text_secret_source is not None:
                    lease = text_secret_source.lease_for_profile(
                        profile.profile_id, auth_mode=ProviderAuthMode.BEARER
                    )
                else:
                    return observed("authentication_failed", "readiness.credential_unavailable")
            adapter, _model = text_provider_resolver.resolve(frozen_snapshot)
            checker = getattr(adapter, "check_readiness", None)
            if checker is None:
                return observed("unverified", "readiness.check_unsupported")
            result = checker(str(frozen_snapshot["textModel"]), lease)
            return observed(result.state, result.reason_code)
        except SecretLeaseError:
            return observed("authentication_failed", "readiness.credential_unavailable")
        except ValueError:
            return observed("capability_mismatch", "readiness.adapter_unsupported")
        except Exception:
            # A preflight has no creative request body, so its failed request
            # is a definite inability to establish readiness, not an unknown
            # generation outcome.  Keep all transport details server-private.
            return observed("unreachable", "readiness.preflight_failed")
        finally:
            if lease is not None:
                lease.revoke()
            if temporary_vault is not None:
                temporary_vault.clear()

    def admit_text_backend(
        profile_id: str | None,
        request: Request,
        *,
        frozen_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected = repo.get_text_provider_profile(profile_id) if profile_id else active_text_profile()
        snapshot = dict(frozen_snapshot) if frozen_snapshot is not None else provider_snapshot(selected.profile_id)
        frozen_revision = snapshot.get("profileVersion") or snapshot.get("profile_version")
        observation = check_text_backend(
            selected,
            request,
            snapshot=snapshot,
            record_observation=(frozen_revision is None or int(frozen_revision) == selected.revision),
        )
        if observation.state in {
            "disabled", "missing_configuration", "unreachable", "authentication_failed",
            "model_mismatch", "capability_mismatch",
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"selected text backend is {observation.state} "
                    f"({observation.reason_code}); re-probe or correct this profile before creating a run"
                ),
            )
        return snapshot

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"code": "not_found", "message": str(error)})

    @app.exception_handler(RevisionConflictError)
    async def revision_conflict_handler(_request: Request, error: RevisionConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "revision_conflict",
                "message": str(error),
                "resource": error.resource,
                "expectedRevision": error.expected_revision,
                "actualRevision": error.actual_revision,
            },
        )

    @app.exception_handler(StagePrerequisiteError)
    async def prerequisite_handler(_request: Request, error: StagePrerequisiteError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "stage_prerequisite",
                "message": str(error),
                "stage": error.stage.value,
                "prerequisite": error.prerequisite.value,
                "status": error.status,
            },
        )

    @app.exception_handler(InvalidTransitionError)
    async def transition_handler(_request: Request, error: InvalidTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"code": "invalid_transition", "message": str(error)})

    @app.exception_handler(SchemaResetRequiredError)
    async def schema_reset_required_handler(
        _request: Request, error: SchemaResetRequiredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": error.code,
                "message": str(error),
                "stage": error.stage.value,
                "schemaVersion": error.schema_version,
            },
        )

    @app.exception_handler(RepairEligibilityError)
    async def repair_eligibility_handler(
        _request: Request, error: RepairEligibilityError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ProductionPipelineNotReadyError)
    async def production_pipeline_not_ready_handler(
        _request: Request, error: ProductionPipelineNotReadyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": error.code, "message": str(error)},
        )

    @app.exception_handler(ProjectBusyError)
    async def project_busy_handler(_request: Request, error: ProjectBusyError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"code": "project_busy", "message": str(error)})

    @app.exception_handler(LifecycleContentionError)
    async def lifecycle_contention_handler(
        _request: Request, error: LifecycleContentionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"code": "lifecycle_contention", "message": str(error)},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        _request: Request, error: IdempotencyConflictError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"code": "idempotency_conflict", "message": str(error)})

    @app.exception_handler(BootstrapContentionError)
    async def bootstrap_contention_handler(
        _request: Request, error: BootstrapContentionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"code": "bootstrap_contention", "message": str(error)},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_handler(_request: Request, error: DomainValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "domain_validation", "message": str(error), "issues": error.issues},
        )

    def schema_validation_response(issues: list[Mapping[str, Any]]) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "schema_validation",
                "message": "validated payload does not match its current schema",
                "issues": issues,
            },
        )

    @app.exception_handler(ValidationError)
    async def canonical_schema_validation_handler(_request: Request, error: ValidationError) -> JSONResponse:
        return schema_validation_response(pydantic_issues(error))

    @app.exception_handler(RequestValidationError)
    async def request_schema_validation_handler(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        # FastAPI's default response includes each rejected ``input`` value.
        # That is unsafe for endpoints which defensively reject API-key-shaped
        # fields, and it also bypasses the workbench's stable issue contract.
        # Project only the three public fields we own and remove FastAPI's
        # transport-level ``body`` prefix from author-facing paths.
        issues = []
        for item in error.errors():
            location = [str(part) for part in item.get("loc", ())]
            if location and location[0] == "body":
                location = location[1:]
            issues.append(
                {
                    "code": "schema_validation",
                    "path": ".".join(location),
                    "message": str(item.get("msg") or "invalid request value"),
                }
            )
        return schema_validation_response(issues)

    @app.exception_handler(StoryGraphTopologyError)
    async def topology_planning_handler(
        _request: Request, error: StoryGraphTopologyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": error.code, "message": str(error)},
        )

    @app.post("/api/v2/projects", response_model=ProjectCreation, status_code=status.HTTP_201_CREATED)
    def create_project(
        body: ProjectCreateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ProjectCreation:
        return repo.create_project(
            body.brief,
            initial_stages=body.initial_stages,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
        )

    @app.get("/api/v2/projects", response_model=ProjectListResponse)
    def list_projects(
        project_status: Annotated[
            Literal["active", "archived", "all"], Query(alias="status")
        ] = "active",
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = None,
    ) -> ProjectListResponse:
        lifecycle_status = (
            None if project_status == "all" else ProjectLifecycleStatus(project_status)
        )
        projects, next_cursor = repo.list_projects(
            lifecycle_status=lifecycle_status,
            limit=limit,
            cursor=_decode_project_cursor(cursor),
        )
        return ProjectListResponse(projects=projects, next_cursor=_encode_project_cursor(next_cursor))

    @app.get("/api/v2/projects/{project_id}", response_model=Project)
    def get_project(project_id: str) -> Project:
        return repo.get_project(project_id)

    @app.post("/api/v2/projects/{project_id}/archive", response_model=Project)
    def archive_project(project_id: str, body: LifecycleRequest) -> Project:
        return repo.archive_project(project_id, body.expected_lifecycle_revision)

    @app.post("/api/v2/projects/{project_id}/restore", response_model=Project)
    def restore_project(project_id: str, body: LifecycleRequest) -> Project:
        return repo.restore_project(project_id, body.expected_lifecycle_revision)

    @app.post("/api/v2/projects/{project_id}/duplicate", response_model=ProjectDuplicateResult)
    def duplicate_project(
        project_id: str,
        body: ProjectDuplicateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ProjectDuplicateResult:
        return repo.duplicate_project(
            project_id,
            body.expected_lifecycle_revision,
            title=body.title,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
        )

    @app.post("/api/v2/projects/{project_id}/permanent-delete", status_code=status.HTTP_204_NO_CONTENT)
    def permanent_delete_project(project_id: str, body: ProjectPermanentDeleteRequest) -> None:
        repo.permanent_delete_project(
            project_id,
            body.expected_lifecycle_revision,
            body.confirmation_title,
        )

    @app.patch("/api/v2/projects/{project_id}", response_model=Project)
    def patch_project(project_id: str, body: ProjectPatchRequest) -> Project:
        return repo.update_project(project_id, body.expected_revision, body.brief)

    @app.get("/api/v2/projects/{project_id}/stages", response_model=StageEnvelopesResponse)
    def get_stages(project_id: str) -> StageEnvelopesResponse:
        return StageEnvelopesResponse(stages=repo.list_stage_envelopes(project_id))

    @app.get("/api/v2/projects/{project_id}/runs", response_model=ProjectRunsResponse)
    def get_project_runs(project_id: str) -> ProjectRunsResponse:
        return ProjectRunsResponse(runs=repo.list_project_runs(project_id))

    @app.get("/api/v2/projects/{project_id}/media-tasks", response_model=ProjectMediaTasksResponse)
    def get_project_media_tasks(project_id: str) -> ProjectMediaTasksResponse:
        return ProjectMediaTasksResponse(tasks=repo.list_project_media_tasks(project_id))

    @app.patch("/api/v2/projects/{project_id}/stages/{stage}", response_model=StageHead)
    def patch_stage(project_id: str, stage: StageName, body: StagePatchRequest) -> StageHead:
        return repo.update_stage(project_id, stage, body.expected_revision, body.payload)

    @app.get(
        "/api/v2/projects/{project_id}/storyboard-review",
        response_model=StoryboardReviewResponse,
    )
    def get_storyboard_review(project_id: str) -> StoryboardReviewResponse:
        head = repo.get_stage_head(project_id, StageName.STORYBOARD)
        gate_evaluation: GateEvaluation | None = None
        if head.entity_revision_id is not None:
            try:
                gate_evaluation = repo.get_gate_evaluation(
                    head.entity_revision_id,
                    STORYBOARD_GATE_SET_VERSION,
                )
            except NotFoundError:
                # A V1 read-only storyboard, or an interrupted pre-gate V2
                # migration, has no production-quality receipt.
                gate_evaluation = None

        decisions = [
            _approval_closure_view(repo.get_approval_closure(decision.id))
            for decision in repo.list_approval_decisions(project_id)
        ]
        active = next(
            (
                item.decision
                for item in reversed(decisions)
                if item.active and item.decision.decision == "approve"
            ),
            None,
        )
        return StoryboardReviewResponse(
            head=head,
            gate_evaluation=gate_evaluation,
            decisions=decisions,
            active_approval=active,
        )

    @app.post(
        "/api/v2/projects/{project_id}/storyboard-approval",
        response_model=ApprovalClosureView,
        status_code=status.HTTP_201_CREATED,
    )
    def decide_storyboard_approval(
        project_id: str,
        body: StoryboardApprovalRequest,
    ) -> ApprovalClosureView:
        decision = repo.decide_storyboard_approval(
            project_id,
            expected_revision=body.expected_revision,
            expected_content_hash=body.content_hash,
            decision=body.decision,
            reviewer=body.reviewer,
            gate_set_version=body.gate_set_version,
            note=body.note,
        )
        return _approval_closure_view(repo.get_approval_closure(decision.id))

    @app.post(
        "/api/v2/projects/{project_id}/pipeline-runs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_pipeline_run(project_id: str, body: PipelineRunRequest, request: Request) -> GenerationRun:
        snapshot = admit_text_backend(body.provider_profile_id, request)
        if run_scheduler is not None:
            # Fail before creating a durable run if no credential can possibly
            # reach a bearer-authenticated provider.
            text_submission_session_key(snapshot, request)
        run = repo.create_run(
            project_id,
            RunKind.PIPELINE,
            body.stages or list(STAGE_ORDER),
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit_text_run(run, request)
        return run

    @app.post(
        "/api/v2/projects/{project_id}/rebuilds",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_rebuild(project_id: str, body: RebuildRequest, request: Request) -> GenerationRun:
        start_index = STAGE_ORDER.index(body.from_stage)
        end_index = STAGE_ORDER.index(body.through_stage) if body.through_stage else len(STAGE_ORDER) - 1
        snapshot = admit_text_backend(body.provider_profile_id, request)
        if run_scheduler is not None:
            text_submission_session_key(snapshot, request)
        run = repo.create_run(
            project_id,
            RunKind.REBUILD,
            STAGE_ORDER[start_index : end_index + 1],
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit_text_run(run, request)
        return run

    @app.get("/api/v2/runs/{run_id}", response_model=GenerationRun)
    def get_run(run_id: str) -> GenerationRun:
        return repo.get_run(run_id)

    @app.get("/api/v2/runs/{run_id}/trace", response_model=RunTrace)
    def get_run_trace(run_id: str) -> RunTrace:
        return repo.get_run_trace(run_id)

    @app.get("/api/v2/runs/{run_id}/execution-trace", response_model=RunExecutionTrace)
    def get_run_execution_trace(run_id: str) -> RunExecutionTrace:
        """Additive shard-level trace; legacy /trace remains compact and stable."""

        return repo.get_run_execution_trace(run_id)

    @app.get("/api/v2/runs/{run_id}/progress", response_model=RunProgress)
    def get_run_progress(run_id: str) -> RunProgress:
        """Return bounded polling state without prompt or response evidence."""

        return repo.get_run_progress(run_id)

    @app.post(
        "/api/v2/runs/{run_id}/resume",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def resume_run(run_id: str, request: Request) -> GenerationRun:
        run = repo.get_run(run_id)
        if run.status.value not in {"queued", "running"}:
            raise InvalidTransitionError(
                f"cannot resume a generation run while it is {run.status.value}"
            )
        if run_scheduler is not None:
            auth_mode = str(
                run.provider_snapshot.get("textAuthMode")
                or run.provider_snapshot.get("text_auth_mode")
                or ProviderAuthMode.BEARER.value
            )
            # Let the real scheduler return an already-live Future before it
            # asks for a new credential.  After a restart, the same call raises
            # SecretLeaseError until the browser supplies the frozen profile's
            # session key (or a server key becomes available).
            session_key = (
                _session_api_key(request)
                if auth_mode == ProviderAuthMode.BEARER.value
                else None
            )
            try:
                if session_key is None:
                    run_scheduler.submit(run.id)
                else:
                    run_scheduler.submit(run.id, session_api_key=session_key)
            except SecretLeaseError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="this queued run needs its profile's browser-session key",
                ) from error
        return repo.get_run(run_id)

    @app.post("/api/v2/runs/{run_id}/cancel", response_model=GenerationRun)
    def cancel_run(run_id: str) -> GenerationRun:
        if run_scheduler is not None:
            return run_scheduler.request_cancel(run_id)
        return repo.cancel_run(run_id)

    @app.post(
        "/api/v2/runs/{run_id}/repairs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
        deprecated=True,
    )
    def create_repair(run_id: str, body: RepairRequest, request: Request) -> GenerationRun:
        snapshot = admit_text_backend(body.provider_profile_id, request)
        if run_scheduler is not None:
            text_submission_session_key(snapshot, request)
        run = repo.create_repair_run(
            run_id,
            stage=body.stage,
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit_text_run(run, request)
        return run

    @app.post(
        "/api/v2/runs/{run_id}/work-units/{work_unit_id}/repairs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_exact_work_unit_repair(
        run_id: str,
        work_unit_id: str,
        _body: ExactWorkUnitRepairRequest,
        request: Request,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=255),
        ],
    ) -> GenerationRun:
        # Validate credentials against the source run's frozen profile before
        # creating a durable child. The active UI profile is not authority.
        source = repo.get_run(run_id)
        frozen_profile_id = str(
            source.provider_snapshot.get("profileId")
            or source.provider_snapshot.get("profile_id")
            or DEFAULT_PROVIDER_PROFILE_ID
        )
        # Exact repair keeps the source's frozen snapshot but still refuses a
        # definitely doomed new child before persistence.
        admit_text_backend(
            frozen_profile_id,
            request,
            frozen_snapshot=source.provider_snapshot,
        )
        if run_scheduler is not None:
            text_submission_session_key(source.provider_snapshot, request)
        normalized_key = _normalize_idempotency_key(idempotency_key)
        assert normalized_key is not None
        creation = repo.create_work_unit_repair_run(
            run_id,
            work_unit_id,
            idempotency_key=normalized_key,
        )
        if creation.created:
            submit_text_run(creation.run, request)
        return creation.run

    @app.post(
        "/api/v2/projects/{project_id}/shots/{shot_id}/media-tasks",
        response_model=MediaTask,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_media_task(project_id: str, shot_id: str, body: MediaTaskRequest, request: Request) -> MediaTask:
        # ADR 0012 keeps this route shape so old clients receive an actionable
        # contract error instead of an ambiguous 404. Rejection occurs before
        # canonical lookup, prompt compilation, credential leasing, persistence,
        # or scheduler dispatch. Reopening it requires an immutable approved
        # ProductionSnapshot.
        _ = (project_id, shot_id, body, request)
        raise ProductionPipelineNotReadyError()

    @app.get("/api/v2/media-tasks/{task_id}", response_model=MediaTask)
    def get_media_task(task_id: str) -> MediaTask:
        return repo.get_media_task(task_id)

    @app.get("/api/v2/provider-settings", response_model=ProviderSettings)
    def get_provider_settings() -> ProviderSettings:
        return effective_provider_settings()

    @app.put("/api/v2/provider-settings", response_model=ProviderSettings)
    def put_provider_settings(body: ProviderSettingsUpdate) -> ProviderSettings:
        updates = body.model_dump(
            mode="python",
            by_alias=False,
            exclude_unset=True,
            exclude={"expected_profile_id", "expected_revision"},
        )
        profile, persisted_media = repo.update_provider_settings_projection(
            expected_profile_id=body.expected_profile_id,
            expected_profile_revision=body.expected_revision,
            updates=updates,
            defaults=public_defaults,
        )
        media = _merge_provider_settings(persisted_media, public_defaults, availability)
        return provider_settings_projection(profile, media)

    @app.get(
        "/api/v2/text-provider-profiles",
        response_model=TextProviderProfilesResponse,
    )
    def list_text_provider_profiles() -> TextProviderProfilesResponse:
        return profiles_response()

    @app.post(
        "/api/v2/text-provider-profiles",
        response_model=TextProviderProfileView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_text_provider_profile(
        body: TextProviderProfileCreate,
    ) -> TextProviderProfileView:
        try:
            profile = repo.create_text_provider_profile(
                body.profile_id,
                body.display_name,
                configuration=body.configuration,
                copy_from_profile_id=body.copy_from_profile_id,
            )
        except ValidationError:
            raise
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="invalid text provider profile configuration",
            ) from error
        readiness_observations.pop(profile.profile_id, None)
        return profile_view(profile)

    @app.get(
        "/api/v2/text-provider-profiles/{profile_id}",
        response_model=TextProviderProfileView,
    )
    def get_text_provider_profile(profile_id: str) -> TextProviderProfileView:
        return profile_view(repo.get_text_provider_profile(profile_id))

    @app.put(
        "/api/v2/text-provider-profiles/{profile_id}",
        response_model=TextProviderProfileView,
    )
    def update_text_provider_profile(
        profile_id: str,
        body: TextProviderProfileUpdate,
    ) -> TextProviderProfileView:
        try:
            updated = repo.update_text_provider_profile(
                    profile_id,
                    body.expected_revision,
                    display_name=body.display_name,
                    configuration=body.configuration,
                )
            if updated.revision != body.expected_revision:
                readiness_observations.pop(profile_id, None)
            return profile_view(updated)
        except ValidationError:
            raise
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="invalid text provider profile configuration",
            ) from error

    @app.delete(
        "/api/v2/text-provider-profiles/{profile_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_text_provider_profile(
        profile_id: str,
        expected_revision: Annotated[int, Query(alias="expectedRevision", ge=0)],
    ) -> None:
        repo.delete_text_provider_profile(profile_id, expected_revision)

    @app.post(
        "/api/v2/text-provider-profiles/{profile_id}/activate",
        response_model=ProviderProfileSelection,
    )
    def activate_text_provider_profile(
        profile_id: str,
        body: TextProviderProfileActivate,
    ) -> ProviderProfileSelection:
        return repo.activate_text_provider_profile(
            profile_id, body.expected_selection_revision
        )

    @app.put(
        "/api/v2/text-provider-profiles/{profile_id}/availability",
        response_model=TextProviderProfileView,
    )
    def set_text_provider_profile_availability(
        profile_id: str,
        body: TextProviderProfileAvailabilityUpdate,
    ) -> TextProviderProfileView:
        updated = repo.set_text_provider_profile_enabled(
                profile_id,
                body.expected_availability_revision,
                enabled=body.enabled,
            )
        if updated.availability_revision != body.expected_availability_revision:
            readiness_observations.pop(profile_id, None)
        return profile_view(updated)

    @app.post(
        "/api/v2/text-provider-profiles/{profile_id}/probe",
        response_model=TextProviderProbeResponse,
    )
    def probe_text_provider_profile(
        profile_id: str,
        request: Request,
    ) -> TextProviderProbeResponse:
        profile = repo.get_text_provider_profile(profile_id)
        return TextProviderProbeResponse.model_validate(
            check_text_backend(profile, request).model_dump(mode="python")
        )

    def observe_definite_generation_failure(run: GenerationRun) -> None:
        """Reflect only certain provider failures into ephemeral readiness."""

        code = run.failure_code or ""
        if code == "provider.outcome_unknown" or not (
            code == "provider.request_not_sent" or code.startswith("provider.http_")
        ):
            return
        profile_id = str(
            run.provider_snapshot.get("profileId")
            or run.provider_snapshot.get("profile_id")
            or DEFAULT_PROVIDER_PROFILE_ID
        )
        try:
            profile = repo.get_text_provider_profile(profile_id)
        except NotFoundError:
            return
        frozen_revision = (
            run.provider_snapshot.get("profileVersion")
            or run.provider_snapshot.get("profile_version")
        )
        if frozen_revision is not None and int(frozen_revision) != profile.revision:
            return
        if code in {"provider.http_401", "provider.http_403"}:
            store_readiness(profile, "authentication_failed", "readiness.generation_authentication_rejected")
        else:
            store_readiness(profile, "unreachable", "readiness.generation_transport_failed")

    set_completion_observer = getattr(run_scheduler, "set_completion_observer", None)
    if callable(set_completion_observer):
        set_completion_observer(observe_definite_generation_failure)

    if static_dir is not None:
        app.mount("/v2", StaticFiles(directory=static_dir, html=True, check_dir=False), name="v2-static")

    return app
