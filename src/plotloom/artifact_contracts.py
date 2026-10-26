from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from plotloom.contract_identity import new_id, utc_now
from plotloom.domain_base import CamelModel
from plotloom.stage_contracts import StageName


class ArtifactKind(str, Enum):
    PROMPT = "prompt"
    RESPONSE = "response"
    VALIDATION = "validation"
    CANDIDATE = "candidate"
    CANONICAL = "canonical"
    MEDIA = "media"


class Artifact(CamelModel):
    id: str = Field(default_factory=new_id)
    run_id: str
    attempt_id: str | None = None
    work_unit_id: str | None = None
    source_artifact_id: str | None = None
    stage: StageName | None = None
    kind: ArtifactKind
    media_type: str = "application/json"
    content: Any
    content_hash: str
    created_at: datetime = Field(default_factory=utc_now)
