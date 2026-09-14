"""Project-owned immutable artifact storage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path, PurePosixPath

from .format import (
    OwnedArtifact,
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    _relative_owned_path,
    _require_real_directory,
    _sha256,
    _write_new_file,
)


class _OwnedArtifactStore:
    """Project-relative immutable bytes with confinement and hard-link checks."""

    def __init__(self, project_home: Path, *, create: bool = True) -> None:
        self.project_home = project_home.resolve()
        assets_root = self.project_home / "assets"
        if create:
            self.assets_root = _require_real_directory(
                assets_root, label="project assets root"
            )
        else:
            if assets_root.is_symlink() or (
                assets_root.exists() and not assets_root.is_dir()
            ):
                raise ProjectStorageConfinementError(
                    "project assets root must be a real directory"
                )
            self.assets_root = assets_root

    def _path_for(
        self, relative_path: PurePosixPath, *, final_must_exist: bool
    ) -> Path:
        if relative_path.parts[:1] != ("assets",):
            raise ProjectStorageConfinementError(
                "owned artifacts must live below assets/"
            )
        if self.project_home.is_symlink() or not self.project_home.is_dir():
            raise ProjectStorageConfinementError(
                "project home must remain a real directory"
            )
        candidate = self.project_home.joinpath(*relative_path.parts)
        parent = candidate.parent
        if parent.is_symlink() or any(
            part.is_symlink() for part in parent.parents if part != self.project_home
        ):
            raise ProjectStorageConfinementError(
                "owned artifact path must not traverse a symlink"
            )
        resolved_parent = parent.resolve()
        if (
            self.project_home != resolved_parent
            and self.project_home not in resolved_parent.parents
        ):
            raise ProjectStorageConfinementError(
                "owned artifact path escapes the project home"
            )
        if final_must_exist:
            if candidate.is_symlink() or not candidate.is_file():
                raise ProjectStorageConfinementError(
                    "owned artifact is missing or not a regular file"
                )
            if candidate.stat().st_nlink != 1:
                raise ProjectStorageConfinementError(
                    "owned artifact must not be hard linked"
                )
        return candidate

    def put(self, contents: bytes, *, media_type: str) -> OwnedArtifact:
        content_hash = _sha256(contents)
        relative_path = PurePosixPath("assets") / content_hash[:2] / content_hash
        path = self._path_for(relative_path, final_must_exist=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = self._path_for(relative_path, final_must_exist=True)
            if _sha256(existing.read_bytes()) != content_hash:
                raise ProjectStorageCorruptionError(
                    "owned artifact hash path has different bytes"
                )
        else:
            _write_new_file(path, contents)
        return OwnedArtifact(
            content_hash=content_hash,
            relative_path=relative_path.as_posix(),
            media_type=media_type,
            size_bytes=len(contents),
        )

    def read(self, artifact: OwnedArtifact) -> bytes:
        relative_path = _relative_owned_path(artifact.relative_path)
        path = self._path_for(relative_path, final_must_exist=True)
        contents = path.read_bytes()
        if (
            len(contents) != artifact.size_bytes
            or _sha256(contents) != artifact.content_hash
        ):
            raise ProjectStorageCorruptionError(
                "owned artifact bytes do not match stored identity"
            )
        return contents


class ProjectArtifactStore:
    """``ArtifactStore`` adapter whose addresses are owned relative paths."""

    def __init__(
        self,
        owned: _OwnedArtifactStore,
        *,
        record: Callable[[OwnedArtifact], None] | None = None,
        writable: bool = True,
    ) -> None:
        self._owned = owned
        self._record = record
        self._writable = writable

    def put(self, content: bytes, *, expected_hash: str | None = None) -> str:
        if not self._writable:
            raise ProjectStorageCorruptionError(
                "a read-only project inspection cannot write artifacts"
            )
        digest = _sha256(content)
        if expected_hash is not None and expected_hash != digest:
            raise ValueError("artifact content does not match expected SHA-256")
        artifact = self._owned.put(
            content, media_type="application/octet-stream"
        )
        if self._record is not None:
            self._record(artifact)
        return artifact.relative_path

    def get(self, uri: str) -> bytes:
        relative = _relative_owned_path(uri)
        parts = relative.parts
        if (
            len(parts) != 3
            or parts[0] != "assets"
            or len(parts[1]) != 2
            or len(parts[2]) != 64
            or parts[2][:2] != parts[1]
            or any(character not in "0123456789abcdef" for character in parts[2])
        ):
            raise ValueError(
                "project artifact URI must name an owned content-addressed asset"
            )
        return self._owned.read(
            OwnedArtifact(
                content_hash=parts[2],
                relative_path=relative.as_posix(),
                media_type="application/octet-stream",
                size_bytes=self._owned._path_for(relative, final_must_exist=True)
                .stat()
                .st_size,
            )
        )


class ProjectRunArtifactStore(ProjectArtifactStore):
    """Run-bound adapter that records every opaque runtime byte in project storage."""

    def record_run_evidence(self, content: bytes) -> str:
        """Persist deterministic runner evidence through the normal artifact contract."""

        return self.put(content)
