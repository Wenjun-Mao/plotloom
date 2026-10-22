"""Explicit creator deployment configuration, without credential environment mutation."""

import os
import stat
from pathlib import Path

from dotenv import dotenv_values

from plotloom.config import VideoProviderSettings
from plotloom.video_backends.minimax_h3.runtime import build_h3_backend


def read_h3_configuration(path: Path) -> VideoProviderSettings:
    """Read an existing protected file; do not export its values to subprocesses."""
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
        ):
            raise ValueError("unprotected configuration")
        values = dotenv_values(path, interpolate=False)
        credential = values.get("VIDEO_MODEL_API_KEY")
        endpoint = values.get("VIDEO_BASE_URL")
        if not credential or not credential.strip() or not endpoint:
            raise ValueError("missing configuration")
        settings = VideoProviderSettings(
            video_provider=values.get("VIDEO_PROVIDER") or "minimax_h3_gateway",
            video_model=values.get("VIDEO_MODEL") or "",
            video_base_url=endpoint,
            video_auth_mode=values.get("VIDEO_AUTH_MODE") or "bearer",
            video_api_key=credential.strip(),
        )
        if settings.video_auth_mode != "bearer":
            raise ValueError("unsupported authentication")
        # Validate the current catalog and private endpoint without contacting it.
        build_h3_backend(settings, enabled=True)
        return settings
    except (OSError, ValueError, RuntimeError):
        # Validation errors may contain input dictionaries; never log those.
        raise ValueError(
            "H3 configuration must be an owned, non-symlink, owner-only file "
            "with a private gateway root, bearer credential and current reviewed catalog"
        ) from None


def creator_h3_backend(environ: dict[str, str] | None = None):
    values = os.environ if environ is None else environ
    enabled = values.get("PLOTLOOM_CREATOR_ENABLE_H3", "false")
    if enabled == "false":
        return None, None
    if enabled != "true":
        raise ValueError("PLOTLOOM_CREATOR_ENABLE_H3 must be true or false")
    path = values.get("PLOTLOOM_CREATOR_H3_CONFIG_FILE")
    if not path:
        raise ValueError("Explicit H3 configuration file is required")
    return build_h3_backend(read_h3_configuration(Path(path)), enabled=True)
