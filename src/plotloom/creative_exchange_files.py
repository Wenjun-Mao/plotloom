"""Bounded creative exchange files and write-once publication primitive."""
import os
import stat
from pathlib import Path
from .creative_handoff_contracts import CreativeHandoffError


def _read_regular(path: Path, *, max_bytes: int, package: bool = False) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise CreativeHandoffError("delivery_incomplete", "required handoff file is not present") from error
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise CreativeHandoffError("package_conflict" if package else "delivery_path_invalid", "handoff entries must be regular files")
    with path.open("rb") as handle:
        content = handle.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise CreativeHandoffError("package_conflict" if package else "delivery_file_too_large", "handoff file exceeds its size limit")
    return content


def _write_once(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
