"""Correction schema result and fail-closed projection error."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class CorrectionResponseSchemaError(ValueError):
    """Typed repair authority cannot be represented without ambiguity."""


@dataclass(frozen=True)
class CorrectionResponseSchema:
    """One immutable overlay result bound into correction provenance."""

    version: str
    schema: dict[str, Any]
    schema_hash: str
    applied_fact_codes: tuple[str, ...]
