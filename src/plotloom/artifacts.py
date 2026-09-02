from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Protocol, runtime_checkable
from urllib.parse import unquote, urlparse


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, content: bytes, *, expected_hash: str | None = None) -> str: ...

    def get(self, uri: str) -> bytes: ...


def _content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class LocalArtifactStore:
    """Content-addressed store with atomic publication and natural deduplication."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for_hash(self, digest: str) -> Path:
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("artifact digest must be a lowercase SHA-256 hex string")
        return self.root / digest[:2] / digest

    def put(self, content: bytes, *, expected_hash: str | None = None) -> str:
        digest = _content_hash(content)
        if expected_hash is not None and expected_hash != digest:
            raise ValueError("artifact content does not match expected SHA-256")
        path = self._path_for_hash(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return path.as_uri()
        temporary_name: str | None = None
        try:
            with NamedTemporaryFile(prefix=f".{digest}.", suffix=".partial", dir=path.parent, delete=False) as handle:
                temporary_name = handle.name
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
        return path.as_uri()

    def get(self, uri: str) -> bytes:
        parsed = urlparse(uri)
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            raise ValueError("local artifact URI must use file://")
        path = Path(unquote(parsed.path)).resolve()
        if self.root not in path.parents:
            raise ValueError("artifact URI is outside configured root")
        content = path.read_bytes()
        if path.name != _content_hash(content):
            raise ValueError("artifact content hash does not match its address")
        return content


class MemoryArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, bytes] = {}
        self._lock = RLock()

    def put(self, content: bytes, *, expected_hash: str | None = None) -> str:
        digest = _content_hash(content)
        if expected_hash is not None and expected_hash != digest:
            raise ValueError("artifact content does not match expected SHA-256")
        with self._lock:
            self._items.setdefault(digest, bytes(content))
        return f"memory://{digest}"

    def get(self, uri: str) -> bytes:
        digest = uri.removeprefix("memory://")
        with self._lock:
            content = self._items[digest]
        if digest != _content_hash(content):
            raise ValueError("artifact content hash does not match its address")
        return content
