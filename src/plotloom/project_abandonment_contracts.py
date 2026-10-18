"""Exact deletion consent is separate from remote attempt settlement."""
from typing import Literal

from pydantic import Field

from .codex_exec_contracts import CodexExecAttempt
from .domain import CamelModel


class AbandonmentPacket(CamelModel):
    project_id: str
    project_home: str
    attempts: list[CodexExecAttempt]
    expected_preview_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class AbandonmentPreview(CamelModel):
    project_id: str
    preview_hash: str
    eligible: bool
    revoked: bool = False
    blockers: list[str]
    unknown_attempt_ids: list[str]
    remote_outcomes: Literal["preserved"] = "preserved"
