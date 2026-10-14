"""Copied accepted projects retain real terminal proof and fresh dispatch leases."""
from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from plotloom.project_storage import ProjectFolderStorage, ProjectStorageCorruptionError
from plotloom.project_storage.operational_state import ProjectAccessLease
from tests.autopilot_seed_fixtures import seed_files
from tests.specialist_reconciliation_seed import open_accepted_script_copy
from tests.specialist_reconciliation_support import (
    ReconciliationRuntime, cancel, delivery, prepare, snapshot_database, snapshot_files,
)


def test_fresh_copy_dispatch_and_terminal_proof_release_only_its_own_reservation(
    tmp_path, accepted_script_reconciliation_seed,
):
    seed = accepted_script_reconciliation_seed
    left = right = None
    try:
        with pytest.MonkeyPatch.context() as first_patch:
            left = ReconciliationRuntime(tmp_path / "left", first_patch, accepted_script_seed=seed)
            _candidate, request = prepare(left.store, "branches")
            paths = left.store.creative_handoff_exchange().verified_package_paths(
                request, left.store.creative_handoff_execution_pin(request),
            )
            assert all(Path(paths[key]).is_relative_to(left.store.home) for key in ("packagePath", "deliveryPath"))
            with left.client() as client:
                assert client.post(left.url("branches", request.job_id) + "/send").status_code == 200
            delivery(left.store, request)
            cancel(left.store, "branches", request.job_id)
            before = snapshot_database(left.store)
            package = left.store.home / "outputs/creative-handoff/jobs" / request.job_id
            frozen = snapshot_files(package)
            with pytest.MonkeyPatch.context() as second_patch:
                right = ReconciliationRuntime(tmp_path / "right", second_patch, accepted_script_seed=seed)
                _candidate, other = prepare(right.store, "script")
                with right.client() as client:
                    assert client.post(right.url("script", other.job_id) + "/send").status_code == 200
                assert request.job_id != other.job_id
                assert left.settings.text.task_id != right.settings.text.task_id
                assert left.settings.image.task_id != right.settings.image.task_id
                assert left.calls is not right.calls and len(left.calls) == len(right.calls) == 1
                assert left.settings.text.task_id in left.calls[0]
                assert right.settings.text.task_id in right.calls[0]
                for runtime in (left, right):
                    assert runtime.dispatch_root().is_relative_to(runtime.registry_root)
                lease = (right.dispatch_root() / "inflight.json").read_bytes()
                unavailable = seed.home.with_name(seed.home.name + "-unavailable")
                seed.home.rename(unavailable)
                try:
                    with left.client() as client:
                        result = client.post(left.url("branches", request.job_id) + "/check")
                        assert result.status_code == 200, result.text
                        assert result.json() == {"state": "completed", "candidateStatus": "discarded"}
                    assert not left.registry.view()["busy"] and right.registry.view()["busy"]
                    assert (right.dispatch_root() / "inflight.json").read_bytes() == lease
                    assert snapshot_database(left.store) == before
                    assert snapshot_files(package) == frozen
                    assert len(left.calls) == len(right.calls) == 1
                finally:
                    unavailable.rename(seed.home)
                for relative, _digest in seed.files:
                    paths = [root / relative for root in (seed.home, left.store.home, right.store.home)]
                    assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 3
    finally:
        for runtime in (left, right):
            if runtime is not None:
                runtime.store.close()
    assert seed_files(seed.home) == seed.files


def test_project_locks_database_and_package_changes_are_isolated_from_seed_and_sibling(
    tmp_path, accepted_script_reconciliation_seed,
):
    seed = accepted_script_reconciliation_seed
    stores = []
    try:
        for name in ("left", "right"):
            storage = ProjectFolderStorage(outputs_root=tmp_path / name / "outputs", application_data_root=tmp_path / name / "application")
            stores.append(open_accepted_script_copy(storage, seed))
        homes = [store.home for store in stores]
        databases = [store.database_path for store in stores]
        sibling_before = snapshot_database(stores[1])
    finally:
        for store in stores:
            store.close()
    first_lease = ProjectAccessLease.acquire(homes[0], mode="exclusive")
    try:
        sibling_lease = ProjectAccessLease.acquire(homes[1], mode="exclusive")
        sibling_lease.close()
    finally:
        first_lease.close()
    active = ProjectAccessLease.acquire(seed.home, mode="shared")
    try:
        storage = ProjectFolderStorage(outputs_root=tmp_path / "refused/outputs", application_data_root=tmp_path / "refused/application")
        with pytest.raises(ValueError, match="active resources"):
            open_accepted_script_copy(storage, seed)
    finally:
        active.close()
    relative = next(path for path, _digest in seed.files if path.endswith("/delivery/script.json"))
    retained = (homes[1] / relative).read_bytes()
    (homes[0] / relative).write_text("tampered copied package")
    with sqlite3.connect(databases[0]) as connection:
        connection.execute("UPDATE v2_script_revisions SET binding='{}'")
    left_storage = ProjectFolderStorage(outputs_root=homes[0].parent, application_data_root=tmp_path / "left/application")
    with pytest.raises(ProjectStorageCorruptionError):
        with closing(left_storage.projects.open(seed.project_id)):
            pytest.fail("corrupted copied project was admitted")
    right_storage = ProjectFolderStorage(outputs_root=homes[1].parent, application_data_root=tmp_path / "right/application")
    with closing(right_storage.projects.open(seed.project_id)) as store:
        assert store.script_state().accepted_review_state.status == "current"
        assert snapshot_database(store) == sibling_before
    assert (homes[1] / relative).read_bytes() == retained
    assert seed_files(seed.home) == seed.files
