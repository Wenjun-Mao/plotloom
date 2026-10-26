"""Canonical creative package identity and wire constants."""
from __future__ import annotations
import json
from hashlib import sha256
from typing import Any
from .creative_handoff_contracts import CreativeHandoffRequest

PACKAGE_VERSION = 1
COMPLETION_FILENAME = "completion.json"
TEMPLATE_FILENAME = "completion-manifest.example.json"
EXECUTION_PIN_KEYS = frozenset({"upstreamRevision", "upstreamSkillHash", "specialistSkillHash"})


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def request_hash(request: CreativeHandoffRequest) -> str:
    return sha256(canonical_json(request.model_dump(mode="json", by_alias=True))).hexdigest()
