"""Seed reuse must preserve real admission, independent bytes and OS ownership."""
from contextlib import closing
import fcntl
import os
import sqlite3

import pytest

from plotloom.project_storage import ProjectStorageCorruptionError, ProjectStorageConfinementError
from plotloom.project_storage.operational_state import ProjectAccessLease
from tests.autopilot_geometry_fixtures import copy_geometry_frame_seed
from tests.autopilot_seed_fixtures import seed_files


def _attempts(storage, project):
    with closing(storage.projects.open(project)) as store:
        with store.repository.engine.connect() as connection:
            return connection.exec_driver_sql(
                "SELECT id,snapshot,receipt FROM v2_autopilot_exec_attempts ORDER BY id"
            ).all()


def test_copies_keep_exact_attempts_and_read_assets_without_original_seed(
    tmp_path, geometry_frame_seed,
):
    seed = geometry_frame_seed
    left, view = copy_geometry_frame_seed(seed, tmp_path / "left")
    right, other = copy_geometry_frame_seed(seed, tmp_path / "right")
    assert view.model_dump() == other.model_dump()
    assert _attempts(left, view.project_id) == _attempts(right, view.project_id)
    assert all(receipt is not None for _identifier, _snapshot, receipt in _attempts(left, view.project_id))
    for relative, _digest in seed.files:
        paths = [root / relative for root in (seed.root, tmp_path / "left", tmp_path / "right")]
        assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 3
    unavailable = seed.root.with_name(seed.root.name + "-unavailable")
    seed.root.rename(unavailable)
    try:
        with closing(left.projects.open(view.project_id)) as store:
            from plotloom.persistence.schema import ManagedAssetRow
            record = view.frames[0].geometry_preparation
            with store.repository._read() as session:
                for identifier in (record.source.asset.asset_id, record.output.asset_id):
                    asset = session.get(ManagedAssetRow, identifier)
                    assert store.artifacts.get(asset.original_uri)
    finally:
        unavailable.rename(seed.root)
    assert seed_files(seed.root) == seed.files


def test_database_asset_application_and_lock_mutations_cannot_bleed_between_copies(
    tmp_path, geometry_frame_seed,
):
    seed = geometry_frame_seed
    roots = [tmp_path / str(index) for index in range(3)]
    copies = [copy_geometry_frame_seed(seed, root) for root in roots]
    first, view = copies[0]
    second, _ = copies[1]
    untouched, _ = copies[2]
    project = view.project_id
    with closing(first.projects.open(project)) as store:
        database = store.database_path
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE v2_autopilot_runs SET policy_hash=?", ("0" * 64,))
    with closing(second.projects.open(project)) as store:
        from plotloom.persistence.schema import ManagedAssetRow
        with store.repository._read() as session:
            asset = session.get(ManagedAssetRow, view.frames[0].asset_id)
            (store.home / asset.original_uri.removeprefix("project-file:")).unlink()
    with first.application._write() as connection:
        connection.execute(
            "INSERT INTO global_accounting (dispatch_identity,resource,reserved_units,status,created_at) "
            "VALUES ('isolated-fixture','images',1,'consumed','2026-10-14')"
        )
    with untouched.application._read() as connection:
        assert connection.execute("SELECT count(*) FROM global_accounting").fetchone()[0] == 0
    for storage in (first, second):
        with pytest.raises((ProjectStorageCorruptionError, ProjectStorageConfinementError)):
            with closing(storage.projects.open(project)):
                pytest.fail("corrupted geometry copy was admitted")
    with closing(untouched.projects.open(project)) as store:
        assert store.repository.autopilot.current(project).frames == view.frames
    # Both existing ownership mechanisms must admit separate physical locks.
    first_lease = ProjectAccessLease.acquire(roots[0] / "outputs" / seed.home_name, mode="exclusive")
    try:
        other_lease = ProjectAccessLease.acquire(roots[2] / "outputs" / seed.home_name, mode="exclusive")
        other_lease.close()
    finally:
        first_lease.close()
    with (roots[0] / "application/.autopilot-controller.lock").open("rb") as first_lock:
        fcntl.flock(first_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (roots[2] / "application/.autopilot-controller.lock").open("rb") as other_lock:
            fcntl.flock(other_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert seed_files(seed.root) == seed.files


@pytest.mark.parametrize("owner", ["project", "controller"])
def test_active_seed_resources_are_refused(tmp_path, geometry_frame_seed, owner):
    seed = geometry_frame_seed
    if owner == "project":
        lease = ProjectAccessLease.acquire(seed.root / "outputs" / seed.home_name, mode="shared")
        try:
            with pytest.raises(ValueError, match="active resources"):
                copy_geometry_frame_seed(seed, tmp_path / "refused")
        finally:
            lease.close()
    else:
        with (seed.root / "application/.autopilot-controller.lock").open("rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with pytest.raises(ValueError, match="active resources"):
                copy_geometry_frame_seed(seed, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()
    assert seed_files(seed.root) == seed.files


@pytest.mark.parametrize("defect", ["sidecar", "symlink", "hardlink", "fifo", "changed"])
def test_nonquiescent_or_changed_seed_bytes_are_refused(tmp_path, geometry_frame_seed, defect):
    seed = geometry_frame_seed
    injected = seed.root / ("project.sqlite3-wal" if defect == "sidecar" else "unexpected")
    try:
        if defect == "symlink":
            injected.symlink_to(tmp_path)
        elif defect == "hardlink":
            os.link(seed.root / seed.files[0][0], injected)
        elif defect == "fifo":
            os.mkfifo(injected)
        else:
            injected.write_text("injected seed change")
        with pytest.raises(ValueError):
            copy_geometry_frame_seed(seed, tmp_path / "refused")
    finally:
        injected.unlink()
    assert not (tmp_path / "refused").exists()
    assert seed_files(seed.root) == seed.files
