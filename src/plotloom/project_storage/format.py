"""Format constants, records, and filesystem primitives for project homes."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, field_validator

from ..domain import CamelModel

PROJECT_STORAGE_FORMAT_VERSION = 7
PROJECT_DATABASE_RELATIVE_PATH = "project.sqlite3"
PROJECT_MANIFEST_FILENAME = "project.json"


class ProjectStorageError(RuntimeError):
    """Base error for the isolated project-folder storage boundary."""


class ProjectStorageConflictError(ProjectStorageError):
    """Raised when a project edit is based on stale project state."""


class ProjectStorageConfinementError(ProjectStorageError):
    """Raised when a stored path could escape its owning project home."""


class ProjectStorageCorruptionError(ProjectStorageError):
    """Raised when a project manifest or database does not meet this format."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: bytes) -> str:
    return sha256(value).hexdigest()


def _utc_folder_timestamp(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S%fZ")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = json.loads(handle.read())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectStorageCorruptionError(f"invalid JSON file: {path}") from error
    if not isinstance(value, dict):
        raise ProjectStorageCorruptionError(f"JSON object required: {path}")
    return value


def _write_new_file(path: Path, contents: bytes) -> None:
    """Publish one new immutable file without replacing an existing path."""

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _require_real_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink():
        raise ProjectStorageConfinementError(f"{label} must not be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise ProjectStorageConfinementError(
            f"{label} must be a real directory: {path}"
        )
    return path.resolve()


def _relative_owned_path(value: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    if (
        not value
        or candidate.is_absolute()
        or ".." in candidate.parts
        or "." in candidate.parts
    ):
        raise ProjectStorageConfinementError(
            "owned artifact paths must be normalized relative paths"
        )
    return candidate


class ProjectManifest(CamelModel):
    """Immutable identity record stored at the root of every project home."""

    format_version: Literal[PROJECT_STORAGE_FORMAT_VERSION] = (
        PROJECT_STORAGE_FORMAT_VERSION
    )
    project_id: str = Field(min_length=1)
    created_at: datetime
    database_path: Literal[PROJECT_DATABASE_RELATIVE_PATH] = (
        PROJECT_DATABASE_RELATIVE_PATH
    )


class OwnedArtifact(CamelModel):
    """A hash-addressed project-owned file, never an absolute machine path."""

    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    relative_path: str
    media_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _relative_owned_path(value).as_posix()
