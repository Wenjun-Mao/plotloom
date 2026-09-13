from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from plotloom.artifacts import LocalArtifactStore


def test_local_artifacts_are_content_addressed_atomic_and_deduplicated(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    content = b"canonical trace"
    digest = hashlib.sha256(content).hexdigest()
    first = store.put(content)
    second = store.put(content, expected_hash=digest)
    assert first == second
    assert first.endswith(f"/{digest[:2]}/{digest}")
    assert store.get(first) == content
    assert not list((tmp_path / "artifacts").rglob("*.partial"))


def test_artifact_hash_and_traversal_are_rejected(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    with pytest.raises(ValueError):
        store.put(b"content", expected_hash="0" * 64)
    outside = (tmp_path / "outside").resolve()
    outside.write_bytes(b"data")
    with pytest.raises(ValueError):
        store.get(outside.as_uri())


def test_local_artifacts_map_only_an_explicit_legacy_root(tmp_path: Path) -> None:
    old_root = tmp_path / "old-artifacts"
    current_root = tmp_path / "current-artifacts"
    content = b"retained media"
    digest = hashlib.sha256(content).hexdigest()
    old_uri = old_root / digest[:2] / digest
    current_path = current_root / digest[:2] / digest
    current_path.parent.mkdir(parents=True)
    current_path.write_bytes(content)
    store = LocalArtifactStore(current_root, legacy_roots=[old_root])

    assert store.get(old_uri.as_uri()) == content
    with pytest.raises(ValueError):
        store.get((tmp_path / "unlisted-artifacts" / digest[:2] / digest).as_uri())
