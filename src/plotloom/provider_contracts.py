from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from plotloom.domain_base import CamelModel
from plotloom.public_values import (
    contains_secret_setting,
    contains_secret_value,
    validate_public_api_root,
)

DEFAULT_PROVIDER_PROFILE_ID = "default"


DEFAULT_TEXT_PROVIDER = "openai-compatible"


DEFAULT_TEXT_BASE_URL = "https://api.atlascloud.ai/v1"


DEFAULT_TEXT_MODEL = "deepseek-v3"


class ProviderAuthMode(str, Enum):
    """The only credential behavior a trusted local provider may declare."""

    NONE = "none"
    BEARER = "bearer"


class ProviderProfileCapabilities(CamelModel):
    """Declared OpenAI-compatible text-model capabilities, not probe results."""

    chat_completions: bool = True
    json_object: bool = False
    json_schema: bool = False


class PublicProviderConfiguration(CamelModel):
    """The public, persisted fields of the local trusted default profile.

    Plotloom currently has one locally saved profile rather than an arbitrary
    browser-selected profile registry.  The fixed ID makes that control-plane
    boundary explicit while keeping the established provider-settings API
    compatible.  Its revision and digest are attached only when the profile is
    materialized as a snapshot below.
    """

    profile_id: str = DEFAULT_PROVIDER_PROFILE_ID
    text_provider: str | None = None
    text_base_url: str | None = None
    text_model: str | None = None
    text_auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER
    text_capabilities: ProviderProfileCapabilities = Field(
        default_factory=ProviderProfileCapabilities
    )
    text_context_window_tokens: Annotated[int, Field(ge=1)] = 32_768
    text_max_output_tokens: Annotated[int, Field(ge=1)] = 8_192
    text_temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.2
    text_max_concurrency: Annotated[int, Field(ge=1, le=32)] = 1
    text_connect_timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)] = 10.0
    text_attempt_timeout_seconds: Annotated[float, Field(gt=0.0, le=3_600.0)] = 300.0
    redirect_policy: Literal["no_follow"] = "no_follow"
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

    @field_validator("profile_id")
    @classmethod
    def validate_local_profile_id(cls, value: str) -> str:
        if value != DEFAULT_PROVIDER_PROFILE_ID:
            raise ValueError(
                "only the trusted default provider profile may be selected"
            )
        return value

    @field_validator(
        "text_provider",
        "text_model",
        "image_provider",
        "image_model",
        "video_provider",
        "video_model",
    )
    @classmethod
    def normalize_public_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("text_base_url", "image_base_url", "video_base_url")
    @classmethod
    def validate_public_api_root(cls, value: str | None) -> str | None:
        return validate_public_api_root(value)

    @model_validator(mode="after")
    def validate_text_token_budget(self) -> PublicProviderConfiguration:
        if self.text_max_output_tokens >= self.text_context_window_tokens:
            raise ValueError(
                "textMaxOutputTokens must be smaller than textContextWindowTokens"
            )
        return self


class ProviderSnapshot(PublicProviderConfiguration):
    """Canonical, secret-free provider profile frozen into a generation run."""

    # PublicProviderConfiguration keeps these optional because an empty saved
    # settings row means "use environment defaults". A run snapshot has crossed
    # that boundary and must be fully resolved before it is hashed and queued.
    text_provider: str = DEFAULT_TEXT_PROVIDER
    text_base_url: str = DEFAULT_TEXT_BASE_URL
    text_model: str = DEFAULT_TEXT_MODEL
    profile_version: Annotated[int, Field(ge=0)] = 0
    profile_hash: str = ""

    @model_validator(mode="after")
    def require_resolved_text_profile(self) -> ProviderSnapshot:
        if not self.text_provider or not self.text_base_url or not self.text_model:
            raise ValueError(
                "provider snapshots require a resolved text provider, base URL, and model"
            )
        return self

    @model_validator(mode="after")
    def verify_profile_hash(self) -> ProviderSnapshot:
        payload = self.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields) - {"profile_hash"},
        )
        expected = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        if self.profile_hash and self.profile_hash != expected:
            raise ValueError("provider profile hash does not match its public fields")
        object.__setattr__(self, "profile_hash", expected)
        return self


PUBLIC_PROVIDER_SETTING_FIELDS: tuple[str, ...] = tuple(
    PublicProviderConfiguration.model_fields
)


class ProviderSettings(PublicProviderConfiguration):
    """Trusted default profile plus local availability and persistence metadata."""

    profile_version: Annotated[int, Field(ge=0)] = 0
    profile_hash: str = ""
    text_key_available: bool = False
    image_key_available: bool = False
    video_key_available: bool = False
    revision: Annotated[int, Field(ge=0)] = 0
    updated_at: datetime | None = None

    @field_validator("profile_id")
    @classmethod
    def validate_local_profile_id(cls, value: str) -> str:
        # The compatibility settings projection may expose whichever named
        # text profile is active. Frozen historical ProviderSnapshot retains
        # the original default-only validator above.
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
            raise ValueError("profileId must match [a-z][a-z0-9_]{0,62}")
        return value

    @model_validator(mode="after")
    def verify_profile_hash(self) -> ProviderSettings:
        # The compatibility endpoint may project a V2 named text profile. In
        # that case its already-validated V2 hash is carried through verbatim;
        # blank hashes retain the legacy singleton calculation below.
        if self.profile_hash:
            return self
        payload = self.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields) - {"profile_hash"},
        )
        expected = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "profile_hash", expected)
        return self
