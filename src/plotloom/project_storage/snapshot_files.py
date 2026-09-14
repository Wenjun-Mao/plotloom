"""Fail-closed filesystem primitives for portable snapshot payloads."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

from ..domain import contains_secret_setting, contains_secret_value
from .format import (
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    _relative_owned_path,
)
from .snapshot_contract import _Payload


def _sha256_path(path: Path) -> tuple[str, int]:
    _safe_regular(path, label=f"recovery file {path.name}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    digest = sha256()
    size = 0
    try:
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ProjectStorageConfinementError("recovery file changed into an unsafe entry")
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return digest.hexdigest(), size


def _safe_regular(path: Path, *, label: str) -> os.stat_result:
    if path.is_symlink():
        raise ProjectStorageConfinementError(f"{label} must not be a symlink")
    try:
        metadata = path.stat()
    except OSError as error:
        raise ProjectStorageCorruptionError(f"{label} is unavailable") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ProjectStorageConfinementError(f"{label} must be a regular file")
    if metadata.st_nlink != 1:
        raise ProjectStorageConfinementError(f"{label} must not be hard linked")
    return metadata


def _safe_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ProjectStorageConfinementError(f"{label} must be a real directory")
    return path.resolve()


def _source_file(root: Path, relative_path: PurePosixPath) -> Path:
    relative = _relative_owned_path(relative_path.as_posix())
    candidate = root.joinpath(*relative.parts)
    parent = candidate.parent
    if parent.is_symlink() or any(part.is_symlink() for part in parent.parents if part != root):
        raise ProjectStorageConfinementError("recovery path traverses a symlink")
    if root != parent.resolve() and root not in parent.resolve().parents:
        raise ProjectStorageConfinementError("recovery path escapes its project folder")
    _safe_regular(candidate, label=f"recovery file {relative.as_posix()}")
    return candidate


def _copy_regular(source: Path, destination: Path) -> _Payload:
    metadata = _safe_regular(source, label=f"recovery source {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.parent.is_symlink():
        raise ProjectStorageConfinementError("recovery destination traverses a symlink")
    source_descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except BaseException:
        os.close(source_descriptor)
        raise
    digest = sha256()
    total = 0
    try:
        with os.fdopen(source_descriptor, "rb") as reader, os.fdopen(descriptor, "wb") as writer:
            source_descriptor = -1
            descriptor = -1
            opened = os.fstat(reader.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise ProjectStorageConfinementError("recovery source changed into an unsafe entry")
            while chunk := reader.read(1024 * 1024):
                digest.update(chunk)
                total += len(chunk)
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
    except BaseException:
        if source_descriptor >= 0:
            os.close(source_descriptor)
        if descriptor >= 0:
            os.close(descriptor)
        destination.unlink(missing_ok=True)
        raise
    if total != metadata.st_size:
        destination.unlink(missing_ok=True)
        raise ProjectStorageCorruptionError("recovery source changed while it was copied")
    return _Payload(PurePosixPath(destination.name), digest.hexdigest(), total)


def _copy_payload(root: Path, destination_root: Path, relative_path: PurePosixPath) -> _Payload:
    source = _source_file(root, relative_path)
    if relative_path.parts[:1] == ("runs",):
        _assert_exchange_file_is_secret_free(source)
    target = destination_root.joinpath(*relative_path.parts)
    copied = _copy_regular(source, target)
    return _Payload(relative_path, copied.content_hash, copied.size_bytes)


def _assert_exchange_file_is_secret_free(path: Path) -> None:
    """Reject credential material in published human-readable exchange evidence."""

    if path.suffix not in {".json", ".txt"}:
        return
    raw = path.read_text(encoding="utf-8")
    try:
        value: Any = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    if contains_secret_setting(value) or contains_secret_value(value):
        raise ProjectStorageCorruptionError("published exchange contains forbidden secret material")


def _is_excluded(name: str) -> bool:
    return name.startswith(".") or name.endswith((".partial", ".tmp", "-wal", "-shm", "-journal", ".lock"))


def _published_files(root: Path, run_name: str) -> list[PurePosixPath]:
    run_root = root / "runs" / run_name
    if not run_root.exists():
        raise ProjectStorageCorruptionError("published exchange evidence is unavailable")
    _safe_directory(run_root, label="published exchange directory")
    results: list[PurePosixPath] = []

    def visit(directory: Path, relative: PurePosixPath) -> None:
        with os.scandir(directory) as entries:
            for entry in entries:
                if _is_excluded(entry.name):
                    continue
                child = directory / entry.name
                child_relative = relative / entry.name
                if entry.is_symlink():
                    raise ProjectStorageConfinementError("published exchange contains a symlink")
                if entry.is_dir(follow_symlinks=False):
                    visit(child, child_relative)
                elif entry.is_file(follow_symlinks=False):
                    _safe_regular(child, label="published exchange file")
                    results.append(child_relative)
                else:
                    raise ProjectStorageConfinementError("published exchange contains a non-regular entry")

    visit(run_root, PurePosixPath("runs") / run_name)
    return results
