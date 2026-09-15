"""Public gateway contracts and deployment settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .profile_catalog import LEGACY_PROFILE_ID

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
MANAGED_OUTPUT_RETENTION_HOURS = 72
GATEWAY_JOB_RECORD_RETENTION_DAYS = 30
GATEWAY_KEYFRAME_RETENTION_DAYS = 30
AspectPolicy = Literal["cover_center_crop", "contain_pad", "reject_mismatch"]


class GatewayError(RuntimeError):
    """A stable gateway failure that is safe to expose to a trusted caller."""

    def __init__(self, code: str, status_code: int = 502):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True)
class GatewaySettings:
    """Deployment configuration. Secrets are never persisted in SQLite."""

    api_key: str
    data_dir: Path
    comfy_input_dir: Path
    comfy_output_dir: Path = Path("/comfy/output")
    comfy_url: str = "http://127.0.0.1:8188"
    request_timeout_seconds: float = 30.0
    source_fetch_connect_timeout_seconds: float = 5.0
    source_fetch_read_timeout_seconds: float = 20.0
    source_fetch_max_redirects: int = 3
    worker_poll_seconds: float = 0.5
    dispatch_worker_enabled: bool = True

    @classmethod
    def from_environment(cls) -> "GatewaySettings":
        key = os.environ.get("H3_API_KEY", "").strip()
        if not key:
            raise RuntimeError("H3_API_KEY is required")
        return cls(
            api_key=key,
            data_dir=Path(os.environ.get("H3_GATEWAY_DATA_DIR", "/var/lib/plotloom-h3-gateway")),
            comfy_input_dir=Path(os.environ.get("H3_COMFY_INPUT_DIR", "/comfy/input")),
            comfy_output_dir=Path(os.environ.get("H3_COMFY_OUTPUT_DIR", "/comfy/output")),
            comfy_url=os.environ.get("H3_COMFY_URL", "http://127.0.0.1:8188").rstrip("/"),
            source_fetch_connect_timeout_seconds=float(
                os.environ.get("H3_SOURCE_FETCH_CONNECT_TIMEOUT_SECONDS", "5")
            ),
            source_fetch_read_timeout_seconds=float(
                os.environ.get("H3_SOURCE_FETCH_READ_TIMEOUT_SECONDS", "20")
            ),
            source_fetch_max_redirects=int(os.environ.get("H3_SOURCE_FETCH_MAX_REDIRECTS", "3")),
            worker_poll_seconds=float(os.environ.get("H3_WORKER_POLL_SECONDS", "0.5")),
            dispatch_worker_enabled=os.environ.get("H3_DISPATCH_WORKER_ENABLED", "true").strip().lower()
            not in {"0", "false", "no", "off"},
        )


class _JobParameters(BaseModel):
    """Frozen generation choices shared by both job-admission routes."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=8_000)
    aspect_policy: AspectPolicy = Field(alias="aspectPolicy")
    profile_id: str = Field(
        default=LEGACY_PROFILE_ID,
        alias="profileId",
        min_length=3,
        max_length=63,
        pattern=r"^[a-z][a-z0-9_]{0,62}$",
    )
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)


class CreateJobRequest(_JobParameters):
    """The durable two-step job-creation contract."""

    asset_id: str = Field(alias="assetId", min_length=3, max_length=80)
    idempotency_key: str | None = Field(
        default=None, alias="idempotencyKey", min_length=8, max_length=255
    )


class CreateJobFromImageRequest(_JobParameters):
    """One-step job choices, intentionally without retry-deduplication state."""

    def to_create_job_request(self, asset_id: str) -> CreateJobRequest:
        return CreateJobRequest.model_validate({
            "assetId": asset_id,
            "prompt": self.prompt,
            "aspectPolicy": self.aspect_policy,
            "profileId": self.profile_id,
            "seed": self.seed,
        })


class SourceUrlAssetRequest(BaseModel):
    """A private-network image source that is fetched only during admission."""

    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(alias="sourceUrl", min_length=1, max_length=2_048)

    @field_validator("source_url")
    @classmethod
    def require_http_source_url(cls, value: str) -> str:
        if any(character.isspace() for character in value):
            raise ValueError("sourceUrl must not contain whitespace")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("sourceUrl must be an absolute http(s) URL")
        return value


class CreateJobFromSourceUrlRequest(CreateJobFromImageRequest, SourceUrlAssetRequest):
    """The JSON convenience form: a remote image plus frozen job choices."""
