"""Shared managed-blob owner publishes complete single-linked identities only."""

import multiprocessing
import os
import signal
import stat
from hashlib import sha256

import pytest

import plotloom.project_storage.artifact_publication as publication
from plotloom.project_storage.artifacts import ProjectArtifactStore, _OwnedArtifactStore
from plotloom.project_storage.format import (
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
)
from tests.artifact_publication_fixtures import child_process, kill_at_publication

CONTENT = b"bounded-interrupted-publication" * 1000
DIGEST = sha256(CONTENT).hexdigest()


def owned(tmp_path):
    home = tmp_path / "project"
    home.mkdir()
    return home, _OwnedArtifactStore(home)


def canonical(home):
    return home / "assets" / DIGEST[:2] / DIGEST


@pytest.mark.parametrize(
    "boundary", ["partial_write", "before_promotion", "after_promotion"]
)
def test_sigkill_leaves_absent_or_complete_canonical_and_retry_preserves_stage(
    tmp_path, boundary
):
    home, store = owned(tmp_path)

    def interrupted():
        kill_at_publication(boundary)
        store.put(CONTENT, media_type="application/octet-stream")

    assert child_process(interrupted) == -signal.SIGKILL
    path = canonical(home)
    if boundary == "after_promotion":
        assert path.read_bytes() == CONTENT and path.stat().st_nlink == 1
    else:
        assert not path.exists()
    stages = list(tmp_path.glob(".artifact-publish-*"))
    assert len(stages) == 1 and not list(home.rglob(".artifact-publish-*"))
    stage = stages[0]
    assert stat.S_IMODE(stage.stat().st_mode) == 0o700
    retained = {
        file.name: (file.stat().st_ino, file.read_bytes()) for file in stage.iterdir()
    }
    if boundary == "partial_write":
        assert retained["blob"][1] == CONTENT[:17]
    if boundary == "before_promotion":
        assert retained["blob"][1] == CONTENT
    if boundary == "after_promotion":
        assert not retained
    recorded = []
    address = ProjectArtifactStore(store, record=recorded.append).put(
        CONTENT, expected_hash=DIGEST
    )
    assert home / address == path
    assert path.read_bytes() == CONTENT and path.stat().st_nlink == 1
    assert len(recorded) == 1 and len(list(tmp_path.glob(".artifact-publish-*"))) == 1
    assert retained == {
        file.name: (file.stat().st_ino, file.read_bytes()) for file in stage.iterdir()
    }


def test_concurrent_same_hash_native_exclusive_winner_is_single_linked(tmp_path):
    home, store = owned(tmp_path)
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(2)

    def publish():
        original = publication.rename_exclusive

        def raced(*args):
            barrier.wait(timeout=10)
            original(*args)

        publication.rename_exclusive = raced
        store.put(CONTENT, media_type="application/octet-stream")

    processes = [context.Process(target=publish) for _ in range(2)]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            process.close()
    assert (
        canonical(home).read_bytes() == CONTENT and canonical(home).stat().st_nlink == 1
    )
    assert not list(tmp_path.glob(".artifact-publish-*"))


def test_existing_valid_identity_is_unchanged_and_fsynced_before_metadata(
    tmp_path, monkeypatch
):
    home, store = owned(tmp_path)
    artifact = store.put(CONTENT, media_type="application/octet-stream")
    before = canonical(home).stat()
    synced = []
    native_sync = publication.os.fsync

    def sync(descriptor):
        metadata = os.fstat(descriptor)
        synced.append((metadata.st_ino, stat.S_ISDIR(metadata.st_mode)))
        native_sync(descriptor)

    monkeypatch.setattr(publication.os, "fsync", sync)

    def record(value):
        assert value == artifact
        assert (before.st_ino, False) in synced
        for directory in [canonical(home).parent, home / "assets", home, tmp_path]:
            assert (directory.stat().st_ino, True) in synced

    ProjectArtifactStore(store, record=record).put(CONTENT)
    after = canonical(home).stat()
    assert (before.st_ino, before.st_mtime_ns, before.st_size) == (
        after.st_ino,
        after.st_mtime_ns,
        after.st_size,
    )
    assert not list(tmp_path.glob(".artifact-publish-*"))


@pytest.mark.parametrize(
    "kind",
    ["wrong_bytes", "directory", "hardlink", "symlink", "dangling_symlink", "fifo"],
)
def test_preexisting_corrupt_or_foreign_canonical_is_refused_unchanged(tmp_path, kind):
    home, store = owned(tmp_path)
    path = canonical(home)
    path.parent.mkdir()
    foreign = tmp_path / "foreign"
    foreign.write_bytes(CONTENT)
    if kind == "wrong_bytes":
        path.write_bytes(b"partial")
    elif kind == "directory":
        path.mkdir()
    elif kind == "hardlink":
        os.link(foreign, path)
    elif kind == "symlink":
        path.symlink_to(foreign)
    elif kind == "dangling_symlink":
        path.symlink_to(tmp_path / "absent")
    else:
        os.mkfifo(path)
    before = path.lstat()
    with pytest.raises((ProjectStorageConfinementError, ProjectStorageCorruptionError)):
        store.put(CONTENT, media_type="application/octet-stream")
    after = path.lstat()
    assert (before.st_ino, before.st_mtime_ns, before.st_mode, before.st_nlink) == (
        after.st_ino,
        after.st_mtime_ns,
        after.st_mode,
        after.st_nlink,
    )
    assert foreign.read_bytes() == CONTENT
    if kind == "wrong_bytes":
        assert path.read_bytes() == b"partial"
    assert not list(tmp_path.glob(".artifact-publish-*"))


@pytest.mark.parametrize("parent_kind", ["assets", "prefix"])
def test_symlink_parent_is_refused_without_foreign_write(tmp_path, parent_kind):
    home, store = owned(tmp_path)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    if parent_kind == "assets":
        (home / "assets").rmdir()
        (home / "assets").symlink_to(foreign)
    else:
        canonical(home).parent.symlink_to(foreign)
    with pytest.raises(ProjectStorageConfinementError):
        store.put(CONTENT, media_type="application/octet-stream")
    assert list(foreign.iterdir()) == []
    assert not list(tmp_path.glob(".artifact-publish-*"))


@pytest.mark.parametrize("code", [18, 22, 95, 13])
def test_native_capability_cross_mount_and_permission_failure_never_fall_back(
    tmp_path, monkeypatch, code
):
    home, store = owned(tmp_path)

    def refuse(*args):
        raise OSError(code, "native exclusive rename refused")

    monkeypatch.setattr(publication, "rename_exclusive", refuse)
    with pytest.raises(OSError):
        store.put(CONTENT, media_type="application/octet-stream")
    assert not canonical(home).exists() and not list(
        tmp_path.glob(".artifact-publish-*")
    )


@pytest.mark.parametrize("failure", ["write", "target_fsync"])
def test_catchable_failure_cleans_only_own_stage_and_never_records(
    tmp_path, monkeypatch, failure
):
    home, store = owned(tmp_path)
    native = publication.os.fsync

    def fail(descriptor):
        metadata = os.fstat(descriptor)
        should_fail = (
            not stat.S_ISDIR(metadata.st_mode)
            if failure == "write"
            else metadata.st_ino == canonical(home).parent.stat().st_ino
        )
        if should_fail:
            raise OSError("injected durability failure")
        native(descriptor)

    monkeypatch.setattr(publication.os, "fsync", fail)
    recorded = []
    with pytest.raises(OSError):
        ProjectArtifactStore(store, record=recorded.append).put(CONTENT)
    assert recorded == [] and not list(tmp_path.glob(".artifact-publish-*"))
    if failure == "write":
        assert not canonical(home).exists()
    else:
        assert (
            canonical(home).read_bytes() == CONTENT
            and canonical(home).stat().st_nlink == 1
        )


@pytest.mark.parametrize(
    "alteration", ["symlink", "hardlink", "foreign_file", "extra_file"]
)
def test_cleanup_preserves_altered_stage_and_foreign_entries(
    tmp_path, monkeypatch, alteration
):
    home, store = owned(tmp_path)
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"foreign-preserved")

    def alter(source, name, target, digest):
        stage = next(tmp_path.glob(".artifact-publish-*"))
        blob = stage / name
        if alteration == "extra_file":
            (stage / "foreign").write_bytes(b"unknown")
        elif alteration == "hardlink":
            os.link(blob, tmp_path / "linked-stage")
        else:
            blob.unlink()
            if alteration == "symlink":
                blob.symlink_to(foreign)
            else:
                blob.write_bytes(b"other-inode")
        raise OSError("injected changed stage")

    monkeypatch.setattr(publication, "rename_exclusive", alter)
    with pytest.raises((OSError, ProjectStorageConfinementError)):
        store.put(CONTENT, media_type="application/octet-stream")
    assert foreign.read_bytes() == b"foreign-preserved" and not canonical(home).exists()
    stage = next(tmp_path.glob(".artifact-publish-*"))
    if alteration == "extra_file":
        assert (stage / "foreign").read_bytes() == b"unknown"
    elif alteration == "hardlink":
        assert (stage / "blob").read_bytes() == CONTENT and (
            tmp_path / "linked-stage"
        ).read_bytes() == CONTENT
    elif alteration == "symlink":
        assert (stage / "blob").is_symlink()
    else:
        assert (stage / "blob").read_bytes() == b"other-inode"


def test_readonly_and_wrong_expected_hash_create_no_stage_or_blob(tmp_path):
    home, store = owned(tmp_path)
    with pytest.raises(ProjectStorageCorruptionError):
        ProjectArtifactStore(store, writable=False).put(CONTENT)
    with pytest.raises(ValueError):
        ProjectArtifactStore(store).put(CONTENT, expected_hash="f" * 64)
    assert not canonical(home).exists() and not list(
        tmp_path.glob(".artifact-publish-*")
    )


def test_validation_failure_closes_the_open_blob_descriptor(tmp_path, monkeypatch):
    home, store = owned(tmp_path)
    store.put(CONTENT, media_type="application/octet-stream")
    parent = os.open(canonical(home).parent, os.O_RDONLY | os.O_DIRECTORY)
    captured = []

    def lose_entry(directory, name, descriptor):
        captured.append(descriptor)
        os.unlink(name, dir_fd=directory)  # Test-owned external disappearance.
        os.stat(name, dir_fd=directory, follow_symlinks=False)

    monkeypatch.setattr(publication, "_entry_matches", lose_entry)
    try:
        with pytest.raises(FileNotFoundError):
            publication._validate_blob(parent, DIGEST, CONTENT)
        assert len(captured) == 1
        with pytest.raises(OSError):
            os.fstat(captured[0])
    finally:
        os.close(parent)
