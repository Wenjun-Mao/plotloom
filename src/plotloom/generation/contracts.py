"""Stable versioned contracts shared by prompts, providers, and orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PromptVariableSpec(FrozenModel):
    required: bool = True
    default: Any = None
    description: str = ""
    sensitive: bool = False


class PromptOutputSpec(FrozenModel):
    format: Literal["json", "text"]
    schema_id: str | None = None
    structured_output_mode: Literal["prefer", "require", "none"] = "none"


class PromptSpec(FrozenModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    version: str = Field(pattern=r"^2\.[0-9]+\.[0-9]+$")
    stage: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    description: str = ""
    system: str
    user: str
    variables: dict[str, PromptVariableSpec]
    output: PromptOutputSpec


class PromptMessage(FrozenModel):
    role: Literal["system", "user"]
    content: str


class PromptTrace(FrozenModel):
    prompt_id: str
    prompt_version: str
    stage: str
    spec_hash: str
    input_hash: str
    rendered_hash: str
    source: str
    rendered_at: datetime = Field(default_factory=utc_now)
    variable_names: tuple[str, ...]


class RenderedPrompt(FrozenModel):
    messages: tuple[PromptMessage, ...]
    output: PromptOutputSpec
    trace: PromptTrace


class ProviderCapabilities(FrozenModel):
    chat_completions: bool = True
    json_object: bool = False
    json_schema: bool = False
    # This is deliberately a capability rather than a model-name heuristic.
    # Some OpenAI-compatible servers expose template controls while others
    # reject unknown top-level request fields.
    chat_template_kwargs: bool = False


class RequestExtension(str, Enum):
    """Explicit, audited extensions to the OpenAI-compatible request shape."""

    NONE = "none"
    CHAT_TEMPLATE_KWARGS = "chat_template_kwargs"


class ReasoningMode(str, Enum):
    PROVIDER_DEFAULT = "provider_default"
    ENABLED = "enabled"
    DISABLED = "disabled"


class GenerationRequest(FrozenModel):
    messages: tuple[PromptMessage, ...]
    model: str = Field(min_length=1, max_length=200)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    response_schema: dict[str, Any] | None = None
    response_schema_name: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    request_extension: RequestExtension = RequestExtension.NONE
    reasoning_mode: ReasoningMode = ReasoningMode.PROVIDER_DEFAULT


class ProviderUsage(FrozenModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class ProviderResponse(FrozenModel):
    provider: str
    model: str
    raw: dict[str, Any]
    request_id: str | None = None
    finish_reason: str | None = None
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    # ``raw`` remains the complete durable evidence envelope.  These fields
    # are a deliberately narrow, content-only read of its first assistant
    # message, so downstream parsing can never accidentally promote hidden
    # reasoning to canonical output.
    final_content: str | None = None
    reasoning_present: bool = False
    outcome_code: str | None = None


class ExtractionPolicy(FrozenModel):
    markdown_fence: bool = False
    reasoning_tags: bool = False
    embedded_json: bool = False


class ExtractedResponse(FrozenModel):
    raw_text: str
    normalized_text: str
    value: Any
    transformations: tuple[str, ...] = ()


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(FrozenModel):
    code: str
    message: str
    path: tuple[str | int, ...] = ()
    severity: ValidationSeverity = ValidationSeverity.ERROR


class ValidationReport(BaseModel):
    """Validation reports stay generic so adapters can return domain objects."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    accepted: bool
    value: Any = None
    issues: tuple[ValidationIssue, ...] = ()


class AttemptKind(str, Enum):
    PRIMARY = "primary"
    REPAIR = "repair"


class AttemptStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class GenerationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: str
    number: int = Field(ge=1)
    kind: AttemptKind
    status: AttemptStatus
    prompt_trace: PromptTrace
    rendered_messages: tuple[PromptMessage, ...]
    schema_id: str
    structured_output_mode: Literal["prefer", "require", "none"]
    native_json_schema_used: bool = False
    provider: str
    model: str
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    response_hash: str | None = None
    raw_response: str | None = None
    provider_request_id: str | None = None
    finish_reason: str | None = None
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    transformations: tuple[str, ...] = ()
    validation_accepted: bool | None = None
    validation_issues: tuple[ValidationIssue, ...] = ()
    error_type: str | None = None
    error_message: str | None = None


class QuarantineRecord(FrozenModel):
    quarantine_id: str
    run_id: str
    attempt_id: str
    stage: str
    schema_id: str
    reason: str
    response_hash: str
    raw_response: str
    validation_issues: tuple[ValidationIssue, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)


class GenerationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    stage: str
    kind: Literal["generation", "repair"] = "generation"
    parent_run_id: str | None = None
    source_quarantine_id: str | None = None
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    attempts: list[GenerationAttempt] = Field(default_factory=list)
    quarantine_ids: list[str] = Field(default_factory=list)
    result_hash: str | None = None


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    run: GenerationRun
    value: Any
