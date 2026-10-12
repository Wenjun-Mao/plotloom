"""Canonical JSON identity without importing persistence or runtime composition."""
from hashlib import sha256
import json
from typing import Any


def stable_hash(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", by_alias=False)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()
