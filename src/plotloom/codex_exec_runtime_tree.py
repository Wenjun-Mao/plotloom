"""Stable, confined inventories for source and validator runtime resources."""
from __future__ import annotations

import json
import os
import stat
import unicodedata
from hashlib import sha256
from pathlib import Path


class CodexExecRuntimeTreeError(ValueError):
    """A source/runtime tree is unsafe or changed while its identity was read."""


def physical_directory(path: Path) -> Path:
    absolute = path.expanduser().absolute()
    if absolute.resolve(strict=True) != absolute or not absolute.is_dir():
        raise CodexExecRuntimeTreeError("validator directory must be physical and alias-free")
    return absolute


def _file_digest(descriptor: int, metadata, *, reject_hardlinks: bool) -> tuple[str, int]:
    before = os.fstat(descriptor)
    if (not stat.S_ISREG(before.st_mode)
            or (before.st_dev, before.st_ino) != (metadata.st_dev, metadata.st_ino)
            or (reject_hardlinks and before.st_nlink != 1)):
        raise CodexExecRuntimeTreeError("validator file must be a distinct regular file")
    digest = sha256()
    size = 0
    while block := os.read(descriptor, 1024 * 1024):
        size += len(block)
        if size > 500_000_000:
            raise CodexExecRuntimeTreeError("validator file exceeds its identity bound")
        digest.update(block)
    after = os.fstat(descriptor)
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_mode)
    if identity(before) != identity(after) or size != before.st_size:
        raise CodexExecRuntimeTreeError("validator file changed while hashing")
    return digest.hexdigest(), size


def stable_file_hash(path: Path) -> str:
    if path.absolute().resolve(strict=True) != path.absolute():
        raise CodexExecRuntimeTreeError("validator file cannot traverse an alias")
    metadata = path.lstat()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        digest, _size = _file_digest(descriptor, metadata, reject_hardlinks=True)
        if (path.lstat().st_dev, path.lstat().st_ino) != (metadata.st_dev, metadata.st_ino):
            raise CodexExecRuntimeTreeError("validator file changed during inspection")
        return digest
    finally:
        os.close(descriptor)


def runtime_tree_hash(
    root: Path, *, internal_links: bool = False, ignore_bytecode: bool = False,
) -> str:
    root = physical_directory(root)
    entries = []
    total_bytes = 0
    file_count = 0

    def visit(descriptor: int, prefix: tuple[str, ...]) -> None:
        nonlocal total_bytes, file_count
        before = os.fstat(descriptor)
        names = sorted(os.listdir(descriptor))
        keys = [unicodedata.normalize("NFC", name).casefold() for name in names]
        if len(keys) != len(set(keys)):
            raise CodexExecRuntimeTreeError("validator tree contains colliding names")
        for name in names:
            if name in {".", ".."} or "/" in name or "\\" in name:
                raise CodexExecRuntimeTreeError("validator tree contains an unsafe name")
            parts = (*prefix, name)
            relative = "/".join(parts)
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            ignored = ignore_bytecode and "__pycache__" in parts
            if stat.S_ISLNK(metadata.st_mode):
                target = os.readlink(name, dir_fd=descriptor)
                lexical_target = Path(os.path.normpath(str((root / relative).parent / target)))
                if (not internal_links or not lexical_target.is_relative_to(root)
                        or not (root / relative).resolve(strict=True).is_relative_to(root)):
                    raise CodexExecRuntimeTreeError("validator tree contains a symlink escape or alias")
                entries.append((relative, "link", target))
            elif stat.S_ISDIR(metadata.st_mode):
                if ignored and name != "__pycache__":
                    raise CodexExecRuntimeTreeError("source bytecode directory contains unexpected content")
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    if (os.fstat(child).st_dev, os.fstat(child).st_ino) != (metadata.st_dev, metadata.st_ino):
                        raise CodexExecRuntimeTreeError("validator directory changed during open")
                    visit(child, parts)
                finally:
                    os.close(child)
                if not ignored:
                    entries.append((relative, "directory"))
            elif stat.S_ISREG(metadata.st_mode):
                if ignored and not name.endswith(".pyc"):
                    raise CodexExecRuntimeTreeError("source bytecode directory contains unexpected content")
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    digest, size = _file_digest(child, metadata, reject_hardlinks=not internal_links)
                finally:
                    os.close(child)
                current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
                    raise CodexExecRuntimeTreeError("validator file changed during inspection")
                total_bytes += size
                file_count += 1
                if total_bytes > 2_000_000_000 or file_count > 100_000:
                    raise CodexExecRuntimeTreeError("validator tree exceeds its identity bounds")
                if not ignored:
                    entries.append((relative, "file", stat.S_IMODE(metadata.st_mode), digest, size))
            else:
                raise CodexExecRuntimeTreeError("validator tree contains a special file")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mtime_ns):
            raise CodexExecRuntimeTreeError("validator directory changed during inspection")
        if names != sorted(os.listdir(descriptor)):
            raise CodexExecRuntimeTreeError("validator directory inventory changed")

    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        visit(descriptor, ())
        current_root = root.lstat()
        opened_root = os.fstat(descriptor)
        if (not stat.S_ISDIR(current_root.st_mode)
                or (current_root.st_dev, current_root.st_ino) != (opened_root.st_dev, opened_root.st_ino)
                or physical_directory(root) != root):
            raise CodexExecRuntimeTreeError("validator confinement root changed during inspection")
    finally:
        os.close(descriptor)
    return sha256(json.dumps(sorted(entries), separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def python_source_identity(source_root: Path) -> tuple[Path, str]:
    """The sole admitted import parent contains the real Plotloom tree only."""
    parent = physical_directory(source_root / "src")
    if sorted(path.name for path in parent.iterdir()) != ["plotloom"]:
        raise CodexExecRuntimeTreeError("Python source parent contains unexpected siblings")
    physical_directory(parent / "plotloom")
    return parent, runtime_tree_hash(parent, ignore_bytecode=True)
