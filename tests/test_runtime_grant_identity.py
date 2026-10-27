"""Durable local authority, non-mutating discovery and portable refusal."""

import errno
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage import database_identity as identities
from plotloom.project_storage.application_store import ApplicationStore
from plotloom.project_storage.delegated_qa_grants import (
    browser_qa_context,
    require_runtime_grant,
)
from plotloom.project_storage.video_batch_grants import VideoBatchGrants
from tests.delegated_qa_fixtures import qa_environment


def grant_fixture(tmp_path):
    home = tmp_path / "original"
    home.mkdir()
    path = home / "project.sqlite3"
    path.write_bytes(b"disposable file identity fixture")
    application_root = tmp_path / "application"
    application_root.mkdir()
    application = ApplicationStore(application_root)
    store = SimpleNamespace(home=home, database_path=path,
                            manifest=SimpleNamespace(project_id="fixture-project"))
    return store, application, VideoBatchGrants(application)


def test_reads_never_initialize_identity_or_grants(tmp_path):
    store, application, _ = grant_fixture(tmp_path)
    before = store.database_path.read_bytes()
    with pytest.raises(InvalidTransitionError):
        identities.database_identity(store.database_path)
    with pytest.raises(InvalidTransitionError):
        VideoBatchGrants(application, initialize=False).require(store, "unbound", "hash")
    assert store.database_path.read_bytes() == before
    with application._read() as connection:
        assert connection.execute("SELECT count(*) FROM runtime_execution_grants").fetchone()[0] == 0
    with pytest.raises(InvalidTransitionError):
        identities.database_identity(store.database_path)


def test_concurrent_create_publishes_one_immutable_identity(tmp_path):
    path = tmp_path / "database"
    path.touch()
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: identities.database_identity(path, create=True), range(24)))
    assert len(set(values)) == 1
    assert identities.database_identity(path) == values[0]


def test_identity_survives_new_handles_and_changed_guest_stat(tmp_path, monkeypatch):
    store, application, grants = grant_fixture(tmp_path)
    grants.authorize(store, "batch", "hash")
    original_fstat, original_stat = os.fstat, Path.stat

    def remapped(info):
        return SimpleNamespace(st_dev=info.st_dev + 71, st_ino=info.st_ino + 100000,
                               st_mode=info.st_mode, st_nlink=info.st_nlink)

    monkeypatch.setattr(os, "fstat", lambda fd: remapped(original_fstat(fd)))
    monkeypatch.setattr(Path, "stat", lambda path, **kwargs: remapped(original_stat(path, **kwargs)))
    VideoBatchGrants(application, initialize=False).require(store, "batch", "hash")
    with pytest.raises(InvalidTransitionError):
        grants.require(store, "batch", "changed-hash")


def test_replaced_database_at_same_path_cannot_inherit_authority(tmp_path):
    store, _application, grants = grant_fixture(tmp_path)
    grants.authorize(store, "batch", "hash")
    old = identities.database_identity(store.database_path)
    replacement = tmp_path / "replacement"
    replacement.write_bytes(store.database_path.read_bytes())
    replacement.replace(store.database_path)
    with pytest.raises(InvalidTransitionError, match="no execution grant"):
        grants.require(store, "batch", "hash")
    # A new trusted binding cannot overwrite an existing batch's old incarnation.
    with pytest.raises(InvalidTransitionError, match="different store incarnation"):
        grants.authorize(store, "batch", "hash")
    assert identities.database_identity(store.database_path) != old


@pytest.mark.parametrize("entry", ["symlink", "hardlink", "malformed", "unsupported"])
def test_unsafe_or_unavailable_identity_fails_closed(tmp_path, monkeypatch, entry):
    store, application, grants = grant_fixture(tmp_path)
    if entry == "symlink":
        original = tmp_path / "real"
        store.database_path.rename(original)
        store.database_path.symlink_to(original)
    elif entry == "hardlink":
        os.link(store.database_path, tmp_path / "linked")
    elif entry == "malformed":
        descriptor = os.open(store.database_path, os.O_RDONLY)
        try:
            identities._create(descriptor, b"malformed-existing-identity")
        finally:
            os.close(descriptor)
    else:
        def unsupported(_descriptor):
            raise OSError(errno.ENOTSUP, "fixture filesystem lacks metadata")
        monkeypatch.setattr(identities, "_read", unsupported)
    with pytest.raises(InvalidTransitionError):
        grants.authorize(store, "batch", "hash")
    with application._read() as connection:
        assert connection.execute("SELECT count(*) FROM runtime_execution_grants").fetchone()[0] == 0


@pytest.mark.parametrize("restore_kind", ["snapshot", "closed-folder"])
def test_restored_original_path_retains_truth_without_qa_authority(tmp_path, monkeypatch, restore_kind):
    storage, _client, _service, provider, project, _view, actor = qa_environment(tmp_path, monkeypatch)
    with closing(storage.projects.open(project)) as store:
        original_home = store.home
        identity = identities.database_identity(store.database_path)
    if restore_kind == "snapshot":
        source = Path(storage.recovery.create_snapshot(project).location)
        with pytest.raises(InvalidTransitionError):
            identities.database_identity(source / "project.sqlite3")
    else:
        storage.projects.close_project(project)
    relocated = tmp_path / "retired-original"
    original_home.rename(relocated)
    if restore_kind == "closed-folder":
        source = relocated
    restored = storage.recovery.restore(source)
    assert restored == original_home
    if restore_kind == "closed-folder":
        storage.projects.reopen_project(project)
    with closing(storage.projects.open(project)) as store:
        assert store.media.list_current_reviewed_keyframes(project)[0]["attribution"]["kind"] == "agent_operated_qa"
        with pytest.raises(InvalidTransitionError, match="no execution grant"):
            require_runtime_grant(store, storage.application, actor)
        assert browser_qa_context(store, storage.application)["eligible"] is False
        with pytest.raises(InvalidTransitionError):
            identities.database_identity(store.database_path)
    assert identities.database_identity(relocated / "project.sqlite3") == identity
    assert not provider.submits


def test_copy_with_preserved_metadata_still_requires_original_home(tmp_path):
    store, _application, grants = grant_fixture(tmp_path)
    grants.authorize(store, "batch", "hash")
    copied = tmp_path / "copy"
    shutil.copytree(store.home, copied)
    copied_store = SimpleNamespace(home=copied, database_path=copied / "project.sqlite3", manifest=store.manifest)
    # Make the test explicit on platforms whose copy utility omits xattrs.
    descriptor = os.open(copied_store.database_path, os.O_RDONLY)
    try:
        try:
            identities._create(descriptor, identities.database_identity(store.database_path).encode("ascii"))
        except OSError as error:
            assert error.errno == errno.EEXIST
    finally:
        os.close(descriptor)
    assert identities.database_identity(copied_store.database_path) == identities.database_identity(store.database_path)
    with pytest.raises(InvalidTransitionError, match="no execution grant"):
        grants.require(copied_store, "batch", "hash")
