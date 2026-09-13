"""Safe, inspectable names for gateway-owned files."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

_UTC_FILENAME_TIMESTAMP = "%Y-%m-%dT%H-%M-%SZ"
_TIMESTAMP_PREFIX = r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z"
H3_JOB_ID = re.compile(r"h3_[0-9a-f]{32}\Z")
ASSET_ID = re.compile(r"asset_[0-9a-f]{32}\Z")


def timestamped_storage_name(object_id: str, suffix: str) -> str:
    """Create a portable UTC filename while preserving its stable owner ID."""

    timestamp = datetime.now(timezone.utc).strftime(_UTC_FILENAME_TIMESTAMP)
    return f"{timestamp}_{object_id}{suffix}"


def is_owned_storage_name(name: object, *, object_id: str, suffixes: tuple[str, ...]) -> bool:
    """Validate a timestamped gateway filename for one stable object ID."""

    if not isinstance(name, str):
        return False
    return any(
        re.fullmatch(
            rf"{_TIMESTAMP_PREFIX}_{re.escape(object_id)}{re.escape(suffix)}", name
        )
        for suffix in suffixes
    )


def is_safe_path_part(value: str) -> bool:
    """Allow one relative output filename or subfolder, never traversal."""

    return not value.startswith(("/", "\\")) and ".." not in Path(value).parts and "\\" not in value
