"""Explicit erasure of permanently revoked, absent project host history."""
from uuid import UUID

from pydantic import Field

from .domain import CamelModel


class ProjectGarbageCollectionRequest(CamelModel):
    project_id: UUID
    expected_preview_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class ProjectGarbageCollectionPreview(CamelModel):
    project_id: UUID
    preview_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    eligible: bool
    blockers: list[str]
    attempt_ids: list[UUID]
    private_file_count: int = Field(ge=0)
    private_symlink_count: int = Field(default=0, ge=0)
    applied: bool = False
