"""Versioned public contract for verified project-folder snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator

from ..domain import CamelModel
from .format import ProjectManifest, _relative_owned_path


SNAPSHOT_FORMAT_VERSION = 1
SNAPSHOT_MANIFEST_FILENAME = "snapshot.json"


class SnapshotFile(CamelModel):
    """One immutable byte payload retained by a portable snapshot."""

    relative_path: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)

    @field_validator("relative_path")
    @classmethod
    def confined_path(cls, value: str) -> str:
        return _relative_owned_path(value).as_posix()


class ProjectSnapshotManifest(CamelModel):
    """Self-validating snapshot inventory and project identity."""

    snapshot_format_version: Literal[SNAPSHOT_FORMAT_VERSION] = SNAPSHOT_FORMAT_VERSION
    snapshot_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    created_at: datetime
    project_manifest: ProjectManifest
    database_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    files: list[SnapshotFile]


class ProjectSnapshotReceipt(CamelModel):
    """Completion response for a synchronous local snapshot operation."""

    operation_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: Literal["complete"] = "complete"
    location: str = Field(min_length=1)
    manifest: ProjectSnapshotManifest


@dataclass(frozen=True)
class _Payload:
    relative_path: PurePosixPath
    content_hash: str
    size_bytes: int
