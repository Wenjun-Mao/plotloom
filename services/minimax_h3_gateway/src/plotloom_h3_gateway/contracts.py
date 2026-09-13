"""Public gateway contracts and deployment settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .profile_catalog import LEGACY_PROFILE_ID

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
MANAGED_OUTPUT_RETENTION_HOURS = 72
EXPIRED_JOB_RECORD_RETENTION_DAYS = 30
ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
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
            worker_poll_seconds=float(os.environ.get("H3_WORKER_POLL_SECONDS", "0.5")),
            dispatch_worker_enabled=os.environ.get("H3_DISPATCH_WORKER_ENABLED", "true").strip().lower()
            not in {"0", "false", "no", "off"},
        )


class CreateJobRequest(BaseModel):
    """The intentionally small, versioned application contract."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(alias="assetId", min_length=3, max_length=80)
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
    idempotency_key: str | None = Field(
        default=None, alias="idempotencyKey", min_length=8, max_length=255
    )
