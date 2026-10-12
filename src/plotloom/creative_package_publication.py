"""Atomic frozen package publication with confined disposable staging bytes."""
from pathlib import Path
import os
import fcntl
import stat
import re
import shutil
from uuid import uuid4

from .creative_handoff_contracts import CreativeHandoffError


def _assert_partial_owned(path, files):
    """A crashed publisher's exact static subset is disposable; extras are not."""
    def visit(directory, prefix=""):
        if directory.is_symlink() or not directory.is_dir():
            raise CreativeHandoffError("package_conflict", "partial package directory is unsafe")
        for entry in directory.iterdir():
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            if entry.is_symlink():
                raise CreativeHandoffError("package_conflict", "partial package path is unsafe")
            if entry.is_dir():
                if relative != "inputs":
                    raise CreativeHandoffError("package_conflict", "partial package has foreign directories")
                visit(entry, relative)
            elif (relative not in files or not entry.is_file() or entry.stat().st_nlink != 1
                    or entry.stat().st_size != len(files[relative])
                    or entry.read_bytes() != files[relative]):
                raise CreativeHandoffError("package_conflict", "partial package contains unknown or changed bytes")
    visit(path)


def _publish_locked(package: Path, *, digest, files, write_once):
    job = package.parent
    job.mkdir(parents=True, exist_ok=True)
    prefix = f".package-{digest}-"
    for prior in job.iterdir():
        if prior.name.startswith(prefix):
            if not re.fullmatch(re.escape(prefix) + r"[a-f0-9]{32}", prior.name):
                raise CreativeHandoffError("package_conflict", "partial publisher identity is invalid")
            _assert_partial_owned(prior, files)
            # Only identified unpublished static request-derived subsets are
            # removed. Frozen packages and specialist deliveries are never here.
            shutil.rmtree(prior)
    staging = job / f"{prefix}{uuid4().hex}"
    staging.mkdir(mode=0o700)
    try:
        (staging / "inputs").mkdir(mode=0o700)
        for relative, contents in files.items():
            write_once(staging / relative, contents)
        for directory in (staging / "inputs", staging):
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        os.rename(staging, package)
        descriptor = os.open(job, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if staging.exists():
            _assert_partial_owned(staging, files)
            shutil.rmtree(staging)


PUBLICATION_LOCK = ".package-publication.lock"


def publish_package(package: Path, *, digest, files, write_once):
    package.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(package.parent / PUBLICATION_LOCK,
        os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size != 0:
            raise CreativeHandoffError("package_conflict", "package publication lock is unsafe")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if package.exists():
            # Another publisher may have installed the identical original
            # while this caller waited. The exchange verifies its bytes.
            return
        _publish_locked(package, digest=digest, files=files, write_once=write_once)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
