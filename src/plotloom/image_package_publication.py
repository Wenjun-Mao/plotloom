"""Descriptor-confined atomic image package publication before native dispatch."""
import fcntl
import os
import re
import stat
from uuid import uuid4
from .image_exchange_files import _open_directory, _open_child_directory, _read_regular_at, _directory_names
from .image_job_contracts import ImageJobError
from .package_publication_lock import open_publication_lock


def _remove_owned( job_fd, name, files):
    directory = _open_child_directory(job_fd, name, package=True)
    try:
        allowed = {key.split("/")[0] for key in files}
        entries = _directory_names(directory, package=True)
        for entry in entries:
            if entry not in allowed:
                raise ImageJobError("package_conflict", "unpublished image package contains unknown entries")
            subset = {key.split("/", 1)[1]: value for key, value in files.items() if key.startswith(entry + "/")}
            if subset:
                nested = _open_child_directory(directory, entry, package=True)
                try:
                    _verify_subset( nested, subset)
                finally:
                    os.close(nested)
            else:
                _verify_subset( directory, {entry: files[entry]}, names={entry})
        # Validate the entire unpublished recipe before removing any member.
        for entry in entries:
            if any(key.startswith(entry + "/") for key in files):
                nested = _open_child_directory(directory, entry, package=True)
                try:
                    for filename in _directory_names(nested, package=True):
                        os.unlink(filename, dir_fd=nested)
                finally:
                    os.close(nested)
                os.rmdir(entry, dir_fd=directory)
            else:
                os.unlink(entry, dir_fd=directory)
    finally:
        os.close(directory)
    os.rmdir(name, dir_fd=job_fd)


def _verify_subset( directory, files, *, names=None):
    for name in names if names is not None else _directory_names(directory, package=True):
        if name not in files:
            raise ImageJobError("package_conflict", "unpublished image package contains unknown files")
        details = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or details.st_size > len(files[name]):
            raise ImageJobError("package_conflict", "unpublished image package contains unsafe files")
        content = _read_regular_at(directory, name, max_bytes=len(files[name]), package=True)
        if not files[name].startswith(content):
            raise ImageJobError("package_conflict", "unpublished image package contains changed bytes")


def publish_image_package( root, job_id, digest, files):
    job = _open_directory(root, ("jobs", job_id), create=True, package=True)
    descriptor = None
    staging = None
    try:
        descriptor = open_publication_lock(".package-publication.lock", dir_fd=job)
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or details.st_size != 0:
            raise ImageJobError("package_conflict", "image package publication lock is unsafe")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if "package" in _directory_names(job, package=True):
            return
        prefix = f".package-{digest}-"
        for name in _directory_names(job, package=True):
            if name.startswith(prefix):
                if not re.fullmatch(re.escape(prefix) + r"[a-f0-9]{32}", name):
                    raise ImageJobError("package_conflict", "unpublished image publisher identity is invalid")
                _remove_owned( job, name, files)
        staging = prefix + uuid4().hex
        os.mkdir(staging, mode=0o700, dir_fd=job)
        directory = _open_child_directory(job, staging, package=True)
        try:
            for path, content in files.items():
                parent, separator, name = path.partition("/")
                target = _open_child_directory(directory, parent, create=True, package=True) if separator else directory
                try:
                    output = os.open(name if separator else parent, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=target)
                    try:
                        data = memoryview(content)
                        while data:
                            data = data[os.write(output, data):]
                        os.fsync(output)
                    finally:
                        os.close(output)
                    os.fsync(target)
                finally:
                    if separator:
                        os.close(target)
            os.fsync(directory)
        finally:
            os.close(directory)
        os.rename(staging, "package", src_dir_fd=job, dst_dir_fd=job)
        staging = None
        os.fsync(job)
    finally:
        if staging is not None:
            _remove_owned( job, staging, files)
        if descriptor is not None:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
        os.close(job)
