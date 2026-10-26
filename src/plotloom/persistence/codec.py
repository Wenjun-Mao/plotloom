from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..contract_hash import stable_hash
from plotloom.public_values import is_secret_setting_name

def _json_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=False)
    return value

def _contains_unredacted_secret_setting(value: Any) -> bool:
    """Allow explicit redaction markers while rejecting secret-shaped fields."""
    if isinstance(value, dict):
        for key, child in value.items():
            if is_secret_setting_name(key) and child != "[redacted]":
                return True
            if _contains_unredacted_secret_setting(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_unredacted_secret_setting(child) for child in value)
    return False

def _stored_utc(value: datetime) -> datetime:
    """Restore SQLite's offset-less UTC storage to the public datetime contract."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
