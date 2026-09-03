"""Versioned, secret-free text-provider profile contracts.

This module is intentionally independent of the persistence and HTTP layers.
It gives both layers one canonical V2 representation, while retaining a small
and exact V1 hash helper for historic frozen snapshots.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .generation.contracts import (
    ExtractionPolicy,
    ReasoningMode,
    RequestExtension,
)
from .domain import validate_public_api_root


PROFILE_ID_PATTERN = r"^[a-z][a-z0-9_]{0,62}$"
DEFAULT_PROVIDER_PROFILE_ID = "default"
PROFILE_SCHEMA_VERSION_V2 = 2
PRESET_VERSION_V1 = "1"
_PROFILE_ID_RE = re.compile(PROFILE_ID_PATTERN)


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class _ProfileModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        alias_generator=_to_camel,
    )


class TextProviderCapabilities(_ProfileModel):
    chat_completions: bool = True
    json_object: bool = False
    json_schema: bool = False
    chat_template_kwargs: bool = False


class V2ExtractionPolicy(_ProfileModel):
    """The only non-strict JSON transformations a V2 profile can enable."""

    allow_json_fence: bool = False
    allow_leading_think_block: bool = False

    def to_generation_policy(self) -> ExtractionPolicy:
        # Embedded document extraction stays false.  A model must return one
        # JSON document, not prose with a convenient JSON-shaped substring.
        return ExtractionPolicy(
            markdown_fence=self.allow_json_fence,
            reasoning_tags=self.allow_leading_think_block,
            embedded_json=False,
        )


class StageMaxOutputTokens(_ProfileModel):
    story_bible: int = Field(ge=1)
    story_graph: int = Field(ge=1)
    scene_beats: int = Field(ge=1)
    storyboard: int = Field(ge=1)

    def for_stage(self, stage: str) -> int:
        try:
            return getattr(self, stage)
        except AttributeError as error:
            raise ValueError(f"unknown canonical stage: {stage!r}") from error


class PresetId(str, Enum):
    COMPATIBLE_V1 = "compatible_v1"
    QUALITY_REASONING_V1 = "quality_reasoning_v1"
    FINAL_ONLY_V1 = "final_only_v1"
    CUSTOM = "custom"


class ExecutionPreset(_ProfileModel):
    preset_id: PresetId
    preset_version: str = PRESET_VERSION_V1
    request_extension: RequestExtension
    reasoning_mode: ReasoningMode
    text_context_window_tokens: int = Field(ge=1)
    text_max_output_tokens: int = Field(ge=1)
    stage_max_output_tokens: StageMaxOutputTokens
    text_attempt_timeout_seconds: float = Field(gt=0.0, le=3_600.0)
    max_semantic_corrections: int = Field(default=2, ge=0, le=2)


EXECUTION_PRESETS: dict[PresetId, ExecutionPreset] = {
    PresetId.COMPATIBLE_V1: ExecutionPreset(
        preset_id=PresetId.COMPATIBLE_V1,
        request_extension=RequestExtension.NONE,
        reasoning_mode=ReasoningMode.PROVIDER_DEFAULT,
        text_context_window_tokens=32_768,
        text_max_output_tokens=8_192,
        stage_max_output_tokens=StageMaxOutputTokens(
            story_bible=8_192, story_graph=8_192, scene_beats=4_096, storyboard=4_096
        ),
        text_attempt_timeout_seconds=300,
    ),
    PresetId.QUALITY_REASONING_V1: ExecutionPreset(
        preset_id=PresetId.QUALITY_REASONING_V1,
        request_extension=RequestExtension.CHAT_TEMPLATE_KWARGS,
        reasoning_mode=ReasoningMode.ENABLED,
        text_context_window_tokens=131_072,
        text_max_output_tokens=32_768,
        stage_max_output_tokens=StageMaxOutputTokens(
            story_bible=32_768, story_graph=32_768, scene_beats=32_768, storyboard=32_768
        ),
        text_attempt_timeout_seconds=900,
    ),
    PresetId.FINAL_ONLY_V1: ExecutionPreset(
        preset_id=PresetId.FINAL_ONLY_V1,
        request_extension=RequestExtension.CHAT_TEMPLATE_KWARGS,
        reasoning_mode=ReasoningMode.DISABLED,
        text_context_window_tokens=32_768,
        text_max_output_tokens=16_384,
        stage_max_output_tokens=StageMaxOutputTokens(
            story_bible=8_192, story_graph=8_192, scene_beats=8_192, storyboard=8_192
        ),
        text_attempt_timeout_seconds=600,
    ),
}


class TextProviderProfileSnapshot(_ProfileModel):
    """All secret-free fields frozen onto a V2 generation run."""

    profile_schema_version: Literal[2] = PROFILE_SCHEMA_VERSION_V2
    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    profile_version: int = Field(ge=0)
    text_provider: str = Field(min_length=1, max_length=200)
    text_base_url: str = Field(min_length=1, max_length=2_000)
    text_model: str = Field(min_length=1, max_length=200)
    text_auth_mode: Literal["none", "bearer"] = "bearer"
    text_capabilities: TextProviderCapabilities = Field(default_factory=TextProviderCapabilities)
    text_context_window_tokens: int = Field(ge=1)
    text_max_output_tokens: int = Field(ge=1)
    text_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    text_max_concurrency: int = Field(default=1, ge=1, le=32)
    text_connect_timeout_seconds: float = Field(default=10.0, gt=0.0, le=300.0)
    text_attempt_timeout_seconds: float = Field(gt=0.0, le=3_600.0)
    redirect_policy: Literal["no_follow"] = "no_follow"
    request_extension: RequestExtension = RequestExtension.NONE
    reasoning_mode: ReasoningMode = ReasoningMode.PROVIDER_DEFAULT
    extraction_policy: V2ExtractionPolicy = Field(default_factory=V2ExtractionPolicy)
    stage_max_output_tokens: StageMaxOutputTokens
    max_semantic_corrections: int = Field(default=2, ge=0, le=2)
    preset_id: PresetId = PresetId.CUSTOM
    preset_version: str = PRESET_VERSION_V1
    profile_hash: str = ""

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        if not _PROFILE_ID_RE.fullmatch(value):
            raise ValueError("profile_id must match [a-z][a-z0-9_]{0,62}")
        return value

    @field_validator("text_base_url")
    @classmethod
    def validate_text_base_url(cls, value: str) -> str:
        """Reject credential-bearing or request-shaped URLs before storage."""

        validated = validate_public_api_root(value)
        if validated is None:  # Field is non-null; this is a defensive guard.
            raise ValueError("text_base_url is required")
        return validated

    @model_validator(mode="after")
    def validate_execution_contract(self) -> "TextProviderProfileSnapshot":
        if self.text_max_output_tokens >= self.text_context_window_tokens:
            raise ValueError("text_max_output_tokens must be smaller than text_context_window_tokens")
        if self.request_extension == RequestExtension.NONE:
            if self.reasoning_mode != ReasoningMode.PROVIDER_DEFAULT:
                raise ValueError("reasoning_mode needs request_extension=chat_template_kwargs")
        elif self.request_extension == RequestExtension.CHAT_TEMPLATE_KWARGS:
            if not self.text_capabilities.chat_template_kwargs:
                raise ValueError("chat_template_kwargs must be an explicit provider capability")
            if self.reasoning_mode == ReasoningMode.PROVIDER_DEFAULT:
                raise ValueError("chat_template_kwargs requires enabled or disabled reasoning_mode")
        else:  # defensive for future enum extensions
            raise ValueError("unsupported request_extension")
        if self.preset_id != PresetId.CUSTOM:
            preset = execution_preset(self.preset_id)
            for field in (
                "preset_version",
                "request_extension",
                "reasoning_mode",
                "text_context_window_tokens",
                "text_max_output_tokens",
                "stage_max_output_tokens",
                "text_attempt_timeout_seconds",
                "max_semantic_corrections",
            ):
                if getattr(self, field) != getattr(preset, field):
                    raise ValueError(
                        f"{field} differs from preset {self.preset_id.value}; use preset_id=custom"
                    )
        expected_hash = v2_profile_hash(self)
        if self.profile_hash and self.profile_hash != expected_hash:
            raise ValueError("provider profile hash does not match its public fields")
        object.__setattr__(self, "profile_hash", expected_hash)
        return self

    def request_contract(self) -> tuple[RequestExtension, ReasoningMode, ExtractionPolicy]:
        return self.request_extension, self.reasoning_mode, self.extraction_policy.to_generation_policy()


class TextProviderProfile(_ProfileModel):
    """Mutable control-plane record; its ID is immutable after creation."""

    profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    display_name: str = Field(min_length=1, max_length=120)
    configuration: TextProviderProfileSnapshot
    revision: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def profile_and_configuration_must_match(self) -> "TextProviderProfile":
        if self.profile_id != self.configuration.profile_id:
            raise ValueError("profile_id must match configuration.profile_id")
        if self.revision != self.configuration.profile_version:
            raise ValueError("revision must match configuration.profile_version")
        return self


class ProviderProfileSelection(_ProfileModel):
    active_profile_id: str = Field(pattern=PROFILE_ID_PATTERN)
    revision: int = Field(ge=0)
    updated_at: datetime


def execution_preset(preset_id: PresetId | str) -> ExecutionPreset:
    """Return an immutable published preset, never a caller-owned mapping."""

    parsed = PresetId(preset_id)
    if parsed == PresetId.CUSTOM:
        raise ValueError("custom has no resolved preset values")
    return EXECUTION_PRESETS[parsed]


def preset_values(preset_id: PresetId | str) -> dict[str, Any]:
    """Convenience payload for a settings UI or profile-creation endpoint."""

    return execution_preset(preset_id).model_dump(mode="json", by_alias=True)


def v2_profile_hash(snapshot: TextProviderProfileSnapshot | Mapping[str, Any]) -> str:
    """Hash V2 fields only; V1 snapshots must use ``legacy_v1_profile_hash``."""

    if isinstance(snapshot, TextProviderProfileSnapshot):
        payload = snapshot.model_dump(mode="json", by_alias=False, exclude={"profile_hash"})
    else:
        data = dict(snapshot)
        if "profileSchemaVersion" in data:
            data.pop("profileHash", None)
        else:
            data.pop("profile_hash", None)
        payload = TextProviderProfileSnapshot.model_validate(data).model_dump(
            mode="json", by_alias=False, exclude={"profile_hash"}
        )
    return _canonical_hash(payload)


_V1_FIELD_ALIASES: dict[str, str] = {
    "profileId": "profile_id", "textProvider": "text_provider", "textBaseUrl": "text_base_url",
    "textModel": "text_model", "textAuthMode": "text_auth_mode",
    "textCapabilities": "text_capabilities", "textContextWindowTokens": "text_context_window_tokens",
    "textMaxOutputTokens": "text_max_output_tokens", "textTemperature": "text_temperature",
    "textMaxConcurrency": "text_max_concurrency", "textConnectTimeoutSeconds": "text_connect_timeout_seconds",
    "textAttemptTimeoutSeconds": "text_attempt_timeout_seconds", "redirectPolicy": "redirect_policy",
    "imageProvider": "image_provider", "imageBaseUrl": "image_base_url", "imageModel": "image_model",
    "imageAuthMode": "image_auth_mode", "videoProvider": "video_provider", "videoBaseUrl": "video_base_url",
    "videoModel": "video_model", "videoAuthMode": "video_auth_mode", "profileVersion": "profile_version",
}
_V1_NESTED_ALIASES = {
    "chatCompletions": "chat_completions", "jsonObject": "json_object", "jsonSchema": "json_schema",
}
_V1_ALLOWED_FIELDS = frozenset(_V1_FIELD_ALIASES) | frozenset(_V1_FIELD_ALIASES.values()) | {"profileHash", "profile_hash"}


def is_v2_snapshot(value: Mapping[str, Any]) -> bool:
    return value.get("profileSchemaVersion") == PROFILE_SCHEMA_VERSION_V2 or value.get(
        "profile_schema_version"
    ) == PROFILE_SCHEMA_VERSION_V2


def legacy_v1_profile_hash(snapshot: Mapping[str, Any]) -> str:
    """Reproduce the original V1 hash without injecting V2 defaults or fields."""

    unknown = set(snapshot) - _V1_ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"not a V1 provider snapshot; unexpected fields: {sorted(unknown)!r}")
    normalized: dict[str, Any] = {}
    for key, value in snapshot.items():
        if key in {"profileHash", "profile_hash"}:
            continue
        target = _V1_FIELD_ALIASES.get(key, key)
        if target == "text_capabilities" and isinstance(value, Mapping):
            normalized[target] = {
                _V1_NESTED_ALIASES.get(nested_key, nested_key): nested_value
                for nested_key, nested_value in value.items()
            }
        else:
            normalized[target] = value
    return _canonical_hash(normalized)


def validate_frozen_text_snapshot(value: Mapping[str, Any]) -> TextProviderProfileSnapshot | dict[str, Any]:
    """Validate V2 or retain a historic V1 payload with its original contract.

    Returning the V1 mapping unchanged is intentional: callers must not amend
    historic durable JSON merely by reading it through a newer model.
    """

    if is_v2_snapshot(value):
        return TextProviderProfileSnapshot.model_validate(value)
    expected = legacy_v1_profile_hash(value)
    supplied = value.get("profileHash", value.get("profile_hash", ""))
    if supplied and supplied != expected:
        raise ValueError("provider profile hash does not match its V1 public fields")
    return dict(value)


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
