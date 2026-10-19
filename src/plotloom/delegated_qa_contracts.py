"""Explicit agent decisions under a separately retained, bounded owner grant."""
from typing import Literal

from pydantic import Field, field_validator

from .domain_base import CamelModel


class AgentQaAttribution(CamelModel):
    kind: Literal["agent_operated_qa"] = "agent_operated_qa"
    scope_id: str = Field(min_length=1, max_length=100)


class QaAvInspection(CamelModel):
    """An operator's actual observations, never inferred from authorization."""

    clips: Literal[True]
    native_audio: Literal[True]
    intent: Literal[True]
    windows: Literal[True]
    visual_observation: str = Field(min_length=1, max_length=2000)
    audio_observation: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(min_length=1, max_length=16)

    @field_validator("visual_observation", "audio_observation")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("QA inspection requires actual observations")
        return value

    @field_validator("evidence_refs")
    @classmethod
    def bounded_refs(cls, values):
        if any(not value.strip() or len(value) > 2000 for value in values):
            raise ValueError("QA inspection evidence references must be nonblank and bounded")
        return values
