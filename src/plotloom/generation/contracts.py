"""Stable versioned prompt, provider and validation contracts."""

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
    version: str = Field(pattern=r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")
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
