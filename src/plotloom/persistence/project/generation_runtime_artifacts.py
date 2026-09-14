"""Typed inventory persistence for opaque bytes emitted by a project run."""

from __future__ import annotations

from pathlib import PurePosixPath

from sqlalchemy import select

from ...exceptions import InvalidTransitionError
from ...domain import utc_now
from ..schema import RunArtifactBlobRow
from .generation_access import GenerationPersistenceAccess


class ProjectGenerationRuntimeArtifactPersistence:
    """Bind project-folder runtime bytes to exactly one canonical run."""

    def __init__(self, access: GenerationPersistenceAccess) -> None:
        self._access = access

    def record(
        self,
        run_id: str,
        *,
        relative_path: str,
        content_hash: str,
        media_type: str,
        size_bytes: int,
    ) -> None:
        path = PurePosixPath(relative_path)
        if (
            not relative_path
            or path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 3
            or path.parts[0] != "assets"
            or len(path.parts[1]) != 2
            or len(path.parts[2]) != 64
            or path.parts[2] != content_hash
            or path.parts[2][:2] != path.parts[1]
            or any(character not in "0123456789abcdef" for character in content_hash)
        ):
            raise InvalidTransitionError(
                "runtime artifact must use its confined content-addressed path"
            )
        if not media_type or size_bytes < 0:
            raise ValueError("runtime artifact metadata is invalid")

        access = self._access
        with access.leases.write() as session:
            access.rows.run(session, run_id)
            existing = session.scalar(
                select(RunArtifactBlobRow).where(
                    RunArtifactBlobRow.run_id == run_id,
                    RunArtifactBlobRow.relative_path == path.as_posix(),
                )
            )
            if existing is not None:
                if (
                    existing.content_hash == content_hash
                    and existing.media_type == media_type
                    and existing.size_bytes == size_bytes
                ):
                    return
                raise InvalidTransitionError(
                    "runtime artifact path is already bound to different bytes"
                )
            session.add(
                RunArtifactBlobRow(
                    run_id=run_id,
                    relative_path=path.as_posix(),
                    content_hash=content_hash,
                    media_type=media_type,
                    size_bytes=size_bytes,
                    created_at=utc_now(),
                )
            )
