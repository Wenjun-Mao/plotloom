"""Public gateway contracts and deployment settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
MANAGED_OUTPUT_RETENTION_HOURS = 72
GATEWAY_JOB_RECORD_RETENTION_DAYS = 30
GATEWAY_KEYFRAME_RETENTION_DAYS = 30
AspectPolicy = Literal["cover_center_crop", "contain_pad", "reject_mismatch"]
ImageBackgroundMode = Literal["opaque", "transparent"]
QWEN_IMAGE_STEPS = 40
QWEN_IMAGE_GUIDANCE_SCALE = 1.0


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
    qwen_image_url: str = "http://127.0.0.1:30010"
    qwen_image_model: str = "Qwen/Qwen-Image-2.1"
    qwen_image_request_timeout_seconds: float = 180.0
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
            qwen_image_url=os.environ.get("H3_QWEN_IMAGE_URL", "http://127.0.0.1:30010").rstrip("/"),
            qwen_image_model=os.environ.get("H3_QWEN_IMAGE_MODEL", "Qwen/Qwen-Image-2.1"),
            qwen_image_request_timeout_seconds=float(
                os.environ.get("H3_QWEN_IMAGE_REQUEST_TIMEOUT_SECONDS", "180")
            ),
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


class _GenerationParameters(BaseModel):
    """Frozen generation choices shared by both job-admission routes."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=8_000)
    quality: int = Field(default=1)
    resolution: str = Field(min_length=7, max_length=9, pattern=r"^[0-9]{3,4}x[0-9]{3,4}$")
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)
    duration_seconds: int = Field(default=5, alias="durationSeconds", ge=5, le=15)


class CreateImageJobRequest(_GenerationParameters):
    """Public image-to-video request choices.

    The image itself is either fetched from ``sourceUrl`` JSON fields or
    supplied through the matching multipart fields.  It is never a reusable
    public asset identifier.
    """

    aspect_policy: AspectPolicy = Field(alias="aspectPolicy")


class CreateTextJobRequest(_GenerationParameters):
    """Exploration-only text-to-video request choices."""


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


class CreateImageJobFromSourceUrlRequest(CreateImageJobRequest, SourceUrlAssetRequest):
    """The JSON image form with a required first-frame URL."""

    end_source_url: str | None = Field(default=None, alias="endSourceUrl", max_length=2_048)

    @field_validator("end_source_url")
    @classmethod
    def require_http_end_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return SourceUrlAssetRequest.model_validate({"sourceUrl": value}).source_url


class _QwenImageParameters(BaseModel):
    """The reviewed, exact-canvas Qwen-Image public contract."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=8_000)
    resolution: str = Field(min_length=7, max_length=9, pattern=r"^[0-9]{3,4}x[0-9]{3,4}$")
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)
    background_mode: ImageBackgroundMode = Field(default="opaque", alias="backgroundMode")


class CreateQwenTextImageJobRequest(_QwenImageParameters):
    """A Qwen text-to-image request, always producing one PNG."""


class CreateQwenEditImageJobRequest(_QwenImageParameters):
    """A one-reference Qwen image edit; multi-image editing is not admitted."""


class CreateQwenEditImageJobFromSourceUrlRequest(
    CreateQwenEditImageJobRequest, SourceUrlAssetRequest
):
    """The JSON image-edit form with exactly one source image URL."""
