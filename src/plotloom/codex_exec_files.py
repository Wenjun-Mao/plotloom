"""No-follow filesystem evidence for frozen Codex execution inputs/outputs."""
from __future__ import annotations

import os
import stat
import unicodedata
from hashlib import sha256
from pathlib import Path, PurePosixPath

from .codex_exec_contracts import CodexExecPackageFile, CodexExecOutputEvidence

MAX_FILES = 256
MAX_TREE_BYTES = 500_000_000
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)


class CodexExecFileError(ValueError):
    """A package or output tree is unsafe or changed during inspection."""


def _parts(path: str | PurePosixPath) -> tuple[str, ...]:
    value = str(path)
    if not value or "\\" in value or value.startswith("/"):
        raise CodexExecFileError("execution tree paths must be canonical relative POSIX paths")
    parts = tuple(value.split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        raise CodexExecFileError("execution tree paths cannot traverse directories")
    return parts


def _assert_no_case_or_unicode_collisions(names: list[str]) -> None:
    normalized_names: set[str] = set()
    for name in names:
        normalized_name = unicodedata.normalize("NFC", name)
        collision_key = normalized_name.casefold()
        if collision_key in normalized_names:
            raise CodexExecFileError("execution tree contains case or Unicode path collisions")
        normalized_names.add(collision_key)


def _open_directory(parent_fd: int, name: str) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise CodexExecFileError("execution evidence requires no-follow directory opens")
    try:
        descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError as error:
        raise CodexExecFileError("execution tree contains an unsafe directory") from error
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise CodexExecFileError("execution tree declarations must be directories")
    return descriptor


def _open_root(path: Path) -> int:
    absolute = path.expanduser().absolute()
    if absolute.is_symlink():
        raise CodexExecFileError("execution confinement root cannot be a symlink")
    try:
        resolved = absolute.resolve(strict=True)
        if resolved != absolute:
            raise CodexExecFileError("execution confinement root cannot traverse symlinks")
        descriptor = os.open(resolved, _DIRECTORY_FLAGS)
    except OSError as error:
        raise CodexExecFileError("execution confinement root is unavailable") from error
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise CodexExecFileError("execution confinement root must be a directory")
    return descriptor


def assert_empty_directory(confinement_root: Path, relative_directory: str) -> None:
    """Prove a no-follow, project-confined directory has no retained entries."""
    root_fd = _open_root(confinement_root)
    directory_fd = root_fd
    opened: list[int] = []
    try:
        for name in _parts(relative_directory):
            directory_fd = _open_directory(directory_fd, name)
            opened.append(directory_fd)
        before = os.fstat(directory_fd)
        try:
            names = os.listdir(directory_fd)
        except OSError as error:
            raise CodexExecFileError("execution directory cannot be read safely") from error
        if names:
            raise CodexExecFileError("execution directory must be empty before admission")
        after = os.fstat(directory_fd)
        if (
            (before.st_dev, before.st_ino, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_mtime_ns)
            or os.listdir(directory_fd)
        ):
            raise CodexExecFileError("execution directory changed during empty check")
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)
        os.close(root_fd)


def read_confined_regular_file(confinement_root: Path, relative_path: str, *, max_bytes: int) -> bytes:
    """Read one bounded file through no-follow directory descriptors."""
    if max_bytes < 1:
        raise ValueError("confined file limit must be positive")
    parts = _parts(relative_path)
    root_fd = _open_root(confinement_root)
    opened: list[int] = []
    try:
        parent_fd = root_fd
        for name in parts[:-1]:
            parent_fd = _open_directory(parent_fd, name)
            opened.append(parent_fd)
        name = parts[-1]
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise CodexExecFileError("confined file must be a regular file")
            descriptor = os.open(name, _FILE_FLAGS, dir_fd=parent_fd)
        except OSError as error:
            raise CodexExecFileError("confined file cannot be opened safely") from error
        try:
            initial = os.fstat(descriptor)
            if (not stat.S_ISREG(initial.st_mode)
                    or (initial.st_dev, initial.st_ino) != (metadata.st_dev, metadata.st_ino)):
                raise CodexExecFileError("confined file identity changed during open")
            chunks: list[bytes] = []
            size = 0
            while True:
                chunk = os.read(descriptor, min(1024 * 1024, max_bytes - size + 1))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > max_bytes:
                    raise CodexExecFileError("confined file exceeds its byte limit")
            final = os.fstat(descriptor)
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
                != (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                or (current.st_dev, current.st_ino) != (initial.st_dev, initial.st_ino)
                or size != initial.st_size
            ):
                raise CodexExecFileError("confined file changed during read")
            return b"".join(chunks)
        except OSError as error:
            raise CodexExecFileError("confined file could not be read") from error
        finally:
            os.close(descriptor)
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)
        os.close(root_fd)


def scan_regular_tree(
    confinement_root: Path,
    relative_directory: str,
    *,
    max_files: int = MAX_FILES,
    max_total_bytes: int = MAX_TREE_BYTES,
) -> tuple[CodexExecPackageFile, ...]:
    """Hash a confined tree through directory descriptors without following links."""
    if not 1 <= max_files <= MAX_FILES or not 1 <= max_total_bytes <= MAX_TREE_BYTES:
        raise ValueError("execution tree limits exceed the qualified profile bounds")
    root_fd = _open_root(confinement_root)
    directory_fd = root_fd
    opened: list[int] = []
    try:
        for name in _parts(relative_directory):
            directory_fd = _open_directory(directory_fd, name)
            opened.append(directory_fd)
        files: list[CodexExecPackageFile] = []
        file_identities: set[tuple[int, int]] = set()
        total_bytes = 0

        def visit(descriptor: int, prefix: tuple[str, ...]) -> None:
            nonlocal total_bytes
            before = os.fstat(descriptor)
            try:
                names = sorted(os.listdir(descriptor))
            except OSError as error:
                raise CodexExecFileError("execution tree directory cannot be read") from error
            _assert_no_case_or_unicode_collisions(names)
            canonical_paths: set[str] = set()
            for name in names:
                if not name or name in {".", ".."} or "/" in name or "\\" in name:
                    raise CodexExecFileError("execution tree contains a noncanonical filename")
                normalized_name = unicodedata.normalize("NFC", name)
                canonical_parts = (*prefix, normalized_name)
                canonical_path = "/".join(canonical_parts)
                if canonical_path.casefold() in canonical_paths:
                    raise CodexExecFileError("execution tree contains canonical path collisions")
                canonical_paths.add(canonical_path.casefold())
                try:
                    metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                except OSError as error:
                    raise CodexExecFileError("execution tree changed during inspection") from error
                if stat.S_ISLNK(metadata.st_mode):
                    raise CodexExecFileError("execution tree cannot contain symlinks")
                if stat.S_ISDIR(metadata.st_mode):
                    child = _open_directory(descriptor, name)
                    try:
                        visit(child, canonical_parts)
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise CodexExecFileError("execution tree contains a non-regular file")
                try:
                    file_fd = os.open(name, _FILE_FLAGS, dir_fd=descriptor)
                except OSError as error:
                    raise CodexExecFileError("execution tree file cannot be opened safely") from error
                try:
                    initial = os.fstat(file_fd)
                    if not stat.S_ISREG(initial.st_mode) or (initial.st_dev, initial.st_ino) != (metadata.st_dev, metadata.st_ino):
                        raise CodexExecFileError("execution tree file identity changed during inspection")
                    identity = (initial.st_dev, initial.st_ino)
                    if identity in file_identities:
                        raise CodexExecFileError("execution tree contains duplicate filesystem identities")
                    file_identities.add(identity)
                    digest = sha256()
                    size = 0
                    while True:
                        chunk = os.read(file_fd, min(1024 * 1024, max_total_bytes - total_bytes + 1))
                        if not chunk:
                            break
                        size += len(chunk)
                        total_bytes += len(chunk)
                        if total_bytes > max_total_bytes:
                            raise CodexExecFileError("execution tree exceeds its frozen byte limit")
                        digest.update(chunk)
                    final = os.fstat(file_fd)
                    current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                    if (
                        (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                        != (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
                        or (current.st_dev, current.st_ino) != identity
                        or size != initial.st_size
                    ):
                        raise CodexExecFileError("execution tree file changed during inspection")
                    files.append(CodexExecPackageFile(relativePath=canonical_path, sha256=digest.hexdigest(), sizeBytes=size))
                    if len(files) > max_files:
                        raise CodexExecFileError("execution tree exceeds its frozen file-count limit")
                except OSError as error:
                    raise CodexExecFileError("execution tree file could not be hashed") from error
                finally:
                    os.close(file_fd)
            after = os.fstat(descriptor)
            if (before.st_dev, before.st_ino, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mtime_ns):
                raise CodexExecFileError("execution tree directory changed during inspection")
            if sorted(os.listdir(descriptor)) != names:
                raise CodexExecFileError("execution tree entries changed during inspection")

        visit(directory_fd, ())
        if not files:
            raise CodexExecFileError("execution tree cannot be empty")
        return tuple(sorted(files, key=lambda item: item.relative_path))
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)
        os.close(root_fd)


def output_evidence_for_tree(
    confinement_root: Path,
    relative_directory: str,
    *,
    output_prefix: str,
    max_files: int = MAX_FILES,
    max_total_bytes: int = MAX_TREE_BYTES,
) -> tuple[CodexExecOutputEvidence, ...]:
    """Convert a safely scanned output tree into receipt-relative identities."""
    prefix = "/".join(_parts(output_prefix))
    files = scan_regular_tree(
        confinement_root,
        relative_directory,
        max_files=max_files,
        max_total_bytes=max_total_bytes,
    )
    return tuple(
        CodexExecOutputEvidence(
            outputHash=item.sha256,
            outputRelativePath=f"{prefix}/{item.relative_path}",
            sizeBytes=item.size_bytes,
        )
        for item in files
    )
