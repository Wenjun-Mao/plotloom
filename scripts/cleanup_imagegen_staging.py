"""Copy a completed ImageGen delivery from Codex staging, then safely clean it.

This utility deliberately owns only the exact staging paths named by a
specialist after a successful built-in ImageGen call.  It is not a general
generated-images cleanup command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from plotloom.image_job_contracts import ImageDeliveryManifest


class CleanupError(ValueError):
    """A safe staging-cleanup refusal with an actionable non-secret reason."""


@dataclass(frozen=True)
class CleanupResult:
    copied: tuple[Path, ...]
    already_present: tuple[Path, ...]
    removed: tuple[Path, ...]
    already_removed: tuple[Path, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path, *, label: str, missing_ok: bool = False) -> os.stat_result | None:
    try:
        details = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        raise CleanupError(f"{label} is missing: {path}") from None
    if stat.S_ISLNK(details.st_mode):
        raise CleanupError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISREG(details.st_mode):
        raise CleanupError(f"{label} must be a regular file: {path}")
    return details


def _directory(path: Path, *, label: str) -> Path:
    details = path.lstat()
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
        raise CleanupError(f"{label} must be a real directory: {path}")
    return path.resolve(strict=True)


def _confined_direct_child(path: Path, root: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise CleanupError(f"{label} must be an absolute path: {path}")
    # `absolute()` is lexical and therefore preserves a symlink for `_regular`
    # to reject instead of silently resolving it outside the declared root.
    candidate = path.absolute()
    if candidate.parent != root or candidate.name.startswith("."):
        raise CleanupError(f"{label} must be a non-hidden direct child of {root}: {path}")
    return candidate


def _task_staging_root() -> Path:
    """Return the one Codex staging directory attributable to this task."""

    task_id = (os.environ.get("CODEX_THREAD_ID") or "").strip()
    if not task_id:
        raise CleanupError("CODEX_THREAD_ID is required to prove task-owned staging")
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    return (codex_home / "generated_images" / task_id).resolve(strict=False)


def _copy_new(source: Path, destination: Path) -> None:
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.partial")
    try:
        with source.open("rb") as input_file, temporary.open("xb") as output_file:
            shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        temporary.unlink(missing_ok=True)


def _open_directory_fd(path: Path, *, label: str) -> int:
    """Bind a directory before operating on its untrusted children."""

    _directory(path, label=label)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        return os.open(path, flags)
    except OSError as error:
        raise CleanupError(f"{label} could not be opened without following a symlink: {path}") from error


def _open_regular_at(directory_fd: int, filename: str, *, label: str, missing_ok: bool = False) -> tuple[int, os.stat_result] | None:
    try:
        fd = os.open(filename, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise CleanupError(f"{label} is missing: {filename}") from None
    except OSError as error:
        raise CleanupError(f"{label} could not be opened without following a symlink: {filename}") from error
    details = os.fstat(fd)
    if not stat.S_ISREG(details.st_mode):
        os.close(fd)
        raise CleanupError(f"{label} must be a regular file: {filename}")
    return fd, details


def _hash_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while chunk := os.read(fd, 1024 * 1024):
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return digest.hexdigest()


def _copy_new_at(source_fd: int, destination_fd: int, filename: str) -> None:
    temporary = f".{filename}.{os.getpid()}.partial"
    output_fd: int | None = None
    try:
        output_fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=destination_fd,
        )
        os.lseek(source_fd, 0, os.SEEK_SET)
        while chunk := os.read(source_fd, 1024 * 1024):
            os.write(output_fd, chunk)
        os.fsync(output_fd)
        os.close(output_fd)
        output_fd = None
        os.replace(temporary, filename, src_dir_fd=destination_fd, dst_dir_fd=destination_fd)
        os.fsync(destination_fd)
    finally:
        if output_fd is not None:
            os.close(output_fd)
        try:
            os.unlink(temporary, dir_fd=destination_fd)
        except FileNotFoundError:
            pass


def cleanup_staging(*, package: Path, staging_root: Path, staged_paths: list[Path]) -> CleanupResult:
    """Copy named staged outputs, verify the complete delivery, then unlink them.

    Missing staged files are idempotent only after their already-present delivery
    output validates.  Any malformed manifest, foreign path, symlink, extra
    output, or mismatched bytes stops before deleting a staging file.
    """

    package = _directory(package, label="package")
    if package.name != "package" or package.parent.name.startswith("."):
        raise CleanupError("package must be the exact exchange package directory")
    expected_staging_root = _task_staging_root()
    if staging_root.resolve(strict=False) != expected_staging_root:
        raise CleanupError("staging root does not match this task's Codex ImageGen directory")
    staging_root = _directory(staging_root, label="staging root")
    request_path = package / "request.json"
    delivery_root = _directory(package.parent / "delivery", label="delivery")
    completion_path = delivery_root / "completion.json"
    outputs_root = delivery_root / "outputs"
    _regular(request_path, label="package request")
    _regular(completion_path, label="completion manifest")
    outputs_root = _directory(outputs_root, label="delivery outputs")

    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        manifest = ImageDeliveryManifest.model_validate_json(completion_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as error:
        raise CleanupError("completion manifest or frozen request is invalid") from error
    if manifest.job_id != request.get("jobId") or manifest.request_hash != request.get("requestHash"):
        raise CleanupError("completion manifest does not match the frozen package identity")

    declared = {item.filename: item.sha256 for item in manifest.outputs}
    candidates = [_confined_direct_child(path, staging_root, label="staged output") for path in staged_paths]
    names = [path.name for path in candidates]
    if len(names) != len(set(names)) or set(names) != set(declared):
        raise CleanupError("exact staged paths must cover every manifest output once")

    staging_fd = _open_directory_fd(staging_root, label="staging root")
    outputs_fd = _open_directory_fd(outputs_root, label="delivery outputs")
    try:
        copied: list[Path] = []
        already_present: list[Path] = []
        source_details: dict[Path, os.stat_result | None] = {}
        for source in candidates:
            destination = outputs_root / source.name
            source_entry = _open_regular_at(staging_fd, source.name, label="staged output", missing_ok=True)
            source_details[source] = source_entry[1] if source_entry else None
            destination_entry = _open_regular_at(outputs_fd, source.name, label="delivery output", missing_ok=True)
            expected_hash = declared[source.name]
            try:
                if source_entry is not None and _hash_fd(source_entry[0]) != expected_hash:
                    raise CleanupError(f"staged output does not match its completion manifest: {source}")
                if destination_entry is not None:
                    if _hash_fd(destination_entry[0]) != expected_hash:
                        raise CleanupError(f"existing delivery output would be overwritten incompatibly: {destination}")
                    already_present.append(destination)
                elif source_entry is None:
                    raise CleanupError(f"staged output is missing before a durable delivery exists: {source}")
                else:
                    _copy_new_at(source_entry[0], outputs_fd, source.name)
                    copied_entry = _open_regular_at(outputs_fd, source.name, label="delivery output")
                    assert copied_entry is not None
                    try:
                        if _hash_fd(copied_entry[0]) != expected_hash:
                            raise CleanupError(f"copied delivery output does not match its completion manifest: {destination}")
                    finally:
                        os.close(copied_entry[0])
                    copied.append(destination)
            finally:
                if source_entry is not None:
                    os.close(source_entry[0])
                if destination_entry is not None:
                    os.close(destination_entry[0])

        if set(os.listdir(outputs_fd)) != set(declared):
            raise CleanupError("delivery output set is not exactly the completion manifest")
        for filename, expected_hash in declared.items():
            output_entry = _open_regular_at(outputs_fd, filename, label="delivery output")
            assert output_entry is not None
            try:
                if _hash_fd(output_entry[0]) != expected_hash:
                    raise CleanupError(f"delivery output no longer matches its completion manifest: {filename}")
            finally:
                os.close(output_entry[0])

        removed: list[Path] = []
        already_removed: list[Path] = []
        for source in candidates:
            original = source_details[source]
            if original is None:
                already_removed.append(source)
                continue
            current_entry = _open_regular_at(staging_fd, source.name, label="staged output")
            assert current_entry is not None
            try:
                current = current_entry[1]
                if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino) or _hash_fd(current_entry[0]) != declared[source.name]:
                    raise CleanupError(f"staged output changed while preparing cleanup: {source}")
                os.unlink(source.name, dir_fd=staging_fd)
            finally:
                os.close(current_entry[0])
            removed.append(source)
    finally:
        os.close(outputs_fd)
        os.close(staging_fd)
    return CleanupResult(tuple(copied), tuple(already_present), tuple(removed), tuple(already_removed))


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely copy verified ImageGen staging outputs into one Plotloom delivery.")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--staged", type=Path, action="append", required=True)
    args = parser.parse_args()
    try:
        result = cleanup_staging(package=args.package, staging_root=args.staging_root, staged_paths=args.staged)
    except CleanupError as error:
        print(f"cleanup refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "copied": [str(path) for path in result.copied],
        "alreadyPresent": [str(path) for path in result.already_present],
        "removed": [str(path) for path in result.removed],
        "alreadyRemoved": [str(path) for path in result.already_removed],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
