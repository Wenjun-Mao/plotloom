"""Bounded creative exchange files and write-once publication primitive."""
import os
import stat
from pathlib import Path
from .creative_handoff_contracts import CreativeHandoffError, is_creative_job_id


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


def configured_exchange_root(root: Path) -> Path:
    configured = root.expanduser()
    if configured.is_symlink():
        raise CreativeHandoffError("package_conflict", "creative exchange root must not be a symlink")
    return configured.resolve()


def creative_job_root(root: Path, job_id: str) -> Path:
    if not is_creative_job_id(job_id):
        raise CreativeHandoffError("invalid_job_id", "creative handoff job identifier is invalid")
    job_root = root / "jobs" / job_id
    if (root / "jobs").is_symlink() or job_root.is_symlink():
        raise CreativeHandoffError("package_conflict", "creative job paths must not traverse symlinks")
    return job_root

def directory_names(directory: Path, *, package: bool = False) -> set[str]:
    if not directory.exists():
        return set()
    if directory.is_symlink() or not directory.is_dir():
        raise CreativeHandoffError("package_conflict" if package else "delivery_path_invalid", "handoff directory is unsafe")
    names = {entry.name for entry in directory.iterdir()}
    if any((directory / name).is_symlink() for name in names):
        raise CreativeHandoffError("delivery_symlink", "handoff paths must not traverse symlinks")
    return names
