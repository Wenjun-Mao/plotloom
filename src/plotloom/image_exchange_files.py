"""Descriptor-relative, no-follow filesystem boundary for image exchanges."""
import errno
import os
import stat
from pathlib import Path
from .image_job_contracts import ImageJobError


def _no_follow_flags(*, directory: bool = False) -> int:
    """Return an OS-enforced no-follow open mode for untrusted delivery paths."""

    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise ImageJobError("image_exchange_invalid", "image exchange requires no-follow filesystem support")
    return os.O_RDONLY | no_follow | (getattr(os, "O_DIRECTORY", 0) if directory else 0)

def _path_open_error(error: OSError, *, package: bool = False) -> ImageJobError:
    if error.errno == errno.ELOOP:
        return ImageJobError("delivery_symlink", "image-job paths must not traverse symlinks")
    if package:
        return ImageJobError("package_conflict", "existing package paths are not safe regular entries")
    if error.errno == errno.ENOENT:
        return ImageJobError("delivery_incomplete", "delivery file is not present")
    return ImageJobError("delivery_path_invalid", "delivery entries must be regular non-symlink files")

def _open_directory(
    root: Path, parts: tuple[str, ...], *, create: bool = False, package: bool = False
) -> int:
    """Open a descendant directory one no-follow component at a time."""

    try:
        directory_fd = os.open(root, _no_follow_flags(directory=True))
    except OSError as error:
        raise _path_open_error(error, package=package) from error
    try:
        for part in parts:
            try:
                child_fd = os.open(part, _no_follow_flags(directory=True), dir_fd=directory_fd)
            except FileNotFoundError:
                if not create:
                    if package:
                        raise ImageJobError("package_conflict", "existing package directory is incomplete")
                    raise ImageJobError("delivery_incomplete", "delivery directory is not present")
                try:
                    try:
                        os.mkdir(part, dir_fd=directory_fd)
                    except FileExistsError:
                        # A cooperating publisher may create this ancestor
                        # before our per-job lock. Reopen with no-follow.
                        pass
                    child_fd = os.open(part, _no_follow_flags(directory=True), dir_fd=directory_fd)
                except OSError as error:
                    raise _path_open_error(error, package=package) from error
            except OSError as error:
                raise _path_open_error(error, package=package) from error
            os.close(directory_fd)
            directory_fd = child_fd
        return directory_fd
    except BaseException:
        os.close(directory_fd)
        raise

def _open_child_directory(
    parent_fd: int, name: str, *, create: bool = False, package: bool = False
) -> int:
    """Open one child from an already pinned parent descriptor."""

    try:
        return os.open(name, _no_follow_flags(directory=True), dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            if package:
                raise ImageJobError("package_conflict", "existing package directory is incomplete")
            raise ImageJobError("delivery_incomplete", "delivery directory is not present")
        try:
            try:
                os.mkdir(name, dir_fd=parent_fd)
            except FileExistsError:
                pass
            return os.open(name, _no_follow_flags(directory=True), dir_fd=parent_fd)
        except OSError as error:
            raise _path_open_error(error, package=package) from error
    except OSError as error:
        raise _path_open_error(error, package=package) from error

def _read_regular_at(
    directory_fd: int, filename: str, *, max_bytes: int, package: bool = False
) -> bytes:
    try:
        file_fd = os.open(filename, _no_follow_flags(), dir_fd=directory_fd)
    except OSError as error:
        raise _path_open_error(error, package=package) from error
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            code = "package_conflict" if package else "delivery_path_invalid"
            raise ImageJobError(code, "image-job entries must be regular files")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(file_fd, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > max_bytes:
            code = "package_conflict" if package else "delivery_file_too_large"
            raise ImageJobError(code, "delivery file exceeds the configured size limit")
        return content
    finally:
        os.close(file_fd)

def _directory_names(
    directory_fd: int,
    *,
    package: bool = False,
    allow_disappearing: frozenset[str] = frozenset(),
) -> set[str]:
    try:
        names = set(os.listdir(directory_fd))
        for name in tuple(names):
            try:
                mode = os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_mode
            except FileNotFoundError:
                # Directory listings are not snapshots. The publisher
                # unlinks this known staging file after linking the final
                # completion marker, so omit it if it vanishes mid-scan.
                if name not in allow_disappearing:
                    raise
                names.discard(name)
                continue
            if stat.S_ISLNK(mode):
                raise ImageJobError("delivery_symlink", "image-job paths must not traverse symlinks")
    except ImageJobError:
        raise
    except OSError as error:
        raise _path_open_error(error, package=package) from error
    return names
