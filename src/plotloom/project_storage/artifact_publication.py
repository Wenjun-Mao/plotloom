"""Durable confined publication of complete managed content-addressed bytes."""

import errno
import os
import stat
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

from .exclusive_rename import rename_exclusive
from .format import (
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    _sha256,
)

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _open_directory(name: str | Path, *, parent: int | None = None) -> int:
    try:
        return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ProjectStorageConfinementError(
                "artifact directories must not traverse symlinks or foreign files"
            ) from error
        raise


def _walk_directory(path: Path) -> int:
    descriptor = _open_directory(path.anchor)
    try:
        for part in path.parts[1:]:
            child = _open_directory(part, parent=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _entry_matches(parent: int, name: str, descriptor: int) -> bool:
    return _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == _identity(
        os.fstat(descriptor)
    )


def _validate_blob(
    parent: int, name: str, contents: bytes, *, expected_inode=None
) -> bool:
    try:
        descriptor = os.open(name, _READ_FLAGS, dir_fd=parent)
    except FileNotFoundError:
        return False
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ProjectStorageConfinementError(
                "owned artifact must not be a symlink"
            ) from error
        raise
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not _entry_matches(parent, name, descriptor)
            or (expected_inode is not None and _identity(metadata) != expected_inode)
        ):
            raise ProjectStorageConfinementError(
                "owned artifact must remain one identified regular file without hard links"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            if metadata.st_size != len(contents) or _sha256(handle.read()) != _sha256(
                contents
            ):
                raise ProjectStorageCorruptionError(
                    "owned artifact hash path has different bytes"
                )
            os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def _write_stage(descriptor: int, contents: bytes) -> None:
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            if handle.write(contents) != len(contents):
                raise OSError(errno.EIO, "incomplete artifact staging write")
            handle.flush()
            os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cleanup_stage(parent: int, name: str, stage: int, blob_inode) -> None:
    """No recursive cleanup; changed or foreign entries remain forensic evidence."""
    if not _entry_matches(parent, name, stage):
        raise ProjectStorageConfinementError(
            "artifact staging directory identity changed; preserved"
        )
    try:
        metadata = os.stat("blob", dir_fd=stage, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        if (
            blob_inode is None
            or _identity(metadata) != blob_inode
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
        ):
            raise ProjectStorageConfinementError(
                "artifact staging file identity changed; preserved"
            )
        os.unlink("blob", dir_fd=stage)
        os.fsync(stage)
    # rmdir refuses any unknown extra entries rather than deleting them.
    os.rmdir(name, dir_fd=parent)
    os.fsync(parent)


def publish_blob(project_home: Path, digest: str, contents: bytes) -> None:
    """Stage outside portable payload, fsync, then atomically publish or validate a winner."""
    with ExitStack() as stack:

        def keep(descriptor):
            stack.callback(os.close, descriptor)
            return descriptor

        parent = keep(_walk_directory(project_home.parent))
        project = keep(_open_directory(project_home.name, parent=parent))
        assets = keep(_open_directory("assets", parent=project))
        prefix = digest[:2]
        try:
            os.mkdir(prefix, mode=0o700, dir_fd=assets)
        except FileExistsError:
            pass
        target = keep(_open_directory(prefix, parent=assets))

        def finish():
            # Reopening the admitted root catches path replacement while retained FDs
            # keep every operation confined to the originally opened directories.
            with ExitStack() as verification:
                current = _walk_directory(project_home.parent)
                verification.callback(os.close, current)
                if (
                    _identity(os.fstat(current)) != _identity(os.fstat(parent))
                    or not _entry_matches(parent, project_home.name, project)
                    or not _entry_matches(project, "assets", assets)
                    or not _entry_matches(assets, prefix, target)
                ):
                    raise ProjectStorageConfinementError(
                        "artifact publication directory identity changed"
                    )
            os.fsync(target)
            os.fsync(assets)
            os.fsync(project)
            os.fsync(parent)

        if _validate_blob(target, digest, contents):
            finish()
            return
        stage_name = ".artifact-publish-" + uuid4().hex
        # A fresh directory under the admitted outputs parent, never another root.
        os.mkdir(stage_name, mode=0o700, dir_fd=parent)
        stage = keep(_open_directory(stage_name, parent=parent))
        blob_inode = None
        try:
            if os.fstat(stage).st_dev != os.fstat(target).st_dev:
                raise OSError(
                    errno.EXDEV, "artifact staging and project must share a filesystem"
                )
            descriptor = keep(
                os.open(
                    "blob",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=stage,
                )
            )
            blob_inode = _identity(os.fstat(descriptor))
            # Keep the inode allocated until cleanup; a foreign replacement cannot
            # reuse the old inode number after the writer closes its descriptor.
            _write_stage(os.dup(descriptor), contents)
            if not _validate_blob(stage, "blob", contents, expected_inode=blob_inode):
                raise ProjectStorageConfinementError(
                    "artifact staging file disappeared"
                )
            os.fsync(stage)
            os.fsync(parent)
            if not _entry_matches(parent, stage_name, stage):
                raise ProjectStorageConfinementError(
                    "artifact staging directory identity changed"
                )
            try:
                rename_exclusive(stage, "blob", target, digest)
            except FileExistsError:
                pass  # Another complete publication won; it receives identical checks.
            if not _validate_blob(target, digest, contents):
                raise ProjectStorageConfinementError("published artifact disappeared")
            finish()
        finally:
            _cleanup_stage(parent, stage_name, stage, blob_inode)
