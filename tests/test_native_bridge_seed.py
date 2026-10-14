"""Copied pending projects keep advice and reservations local to each case."""
from contextlib import closing

import pytest

from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import ProjectAccessLease
from tests.autopilot_seed_fixtures import seed_files
from tests.native_bridge_runtime_fixtures import create_native_intent_runtime, create_native_presentation_runtime
from tests.native_bridge_seed_fixtures import assert_pending_bridge, pending_bridge_project
from tests.specialist_reconciliation_support import snapshot_database
from tests.test_native_bridge_intent import deliver as deliver_intent
from tests.test_native_bridge_presentation import deliver as deliver_presentation


@pytest.mark.parametrize("kind", ["intent", "presentation"])
def test_copy_admits_native_advice_without_seed_and_preserves_sibling_reservation(
    tmp_path, pending_native_bridge_seed, kind,
):
    seed = pending_native_bridge_seed.project
    factory = create_native_intent_runtime if kind == "intent" else create_native_presentation_runtime
    deliver = deliver_intent if kind == "intent" else deliver_presentation
    homes = []
    with pytest.MonkeyPatch.context() as first_patch:
        left = factory(tmp_path / "left", first_patch, pending_native_bridge_seed)
        storage, project = left[:2]
        service, job, calls = left[-3:]
        service.send(project, job)
        request, output = deliver(left)
        with closing(storage.projects.open(project)) as store:
            homes.append(store.home)
            assert output.is_relative_to(store.home)
            assert request.job_id == job
            before = store.production_bridge_state().proposal
        with pytest.MonkeyPatch.context() as second_patch:
            right = factory(tmp_path / "right", second_patch, pending_native_bridge_seed)
            sibling_storage, sibling_project = right[:2]
            sibling_service, sibling_job, sibling_calls = right[-3:]
            sibling_service.send(sibling_project, sibling_job)
            settings = service.registry.view()
            sibling_settings = sibling_service.registry.view()
            assert settings["text"]["taskId"] != sibling_settings["text"]["taskId"]
            assert settings["image"]["taskId"] != sibling_settings["image"]["taskId"]
            assert job != sibling_job and calls is not sibling_calls
            lease = next(sibling_service.registry.root.rglob("inflight.json"))
            assert lease.is_relative_to(sibling_storage.application.root)
            lease_bytes = lease.read_bytes()
            with closing(sibling_storage.projects.open(sibling_project)) as store:
                homes.append(store.home)
                sibling_database = snapshot_database(store)
                sibling_proposal = store.production_bridge_state().proposal
            unavailable = seed.home.with_name(seed.home.name + "-unavailable")
            seed.home.rename(unavailable)
            try:
                assert service.check(project, job)["candidateStatus"] == "ready"
                assert not service.registry.view()["busy"] and sibling_service.registry.view()["busy"]
                assert lease.read_bytes() == lease_bytes
                assert len(calls) == len(sibling_calls) == 1
                assert service.report(project, job) == (output / "report.html").read_bytes()
                with closing(storage.projects.open(project)) as store:
                    state = store.production_bridge_state()
                    assert state.installation is None and not state.proposal.installable
                    if kind == "intent":
                        assert state.proposal.intent_package.review_state == "model_suggested"
                        assert state.proposal.revision == before.revision + 1
                    else:
                        assert state.proposal == before
                        assert state.presentation_candidate.job_id == job
                with closing(sibling_storage.projects.open(sibling_project)) as store:
                    assert store.production_bridge_state().proposal == sibling_proposal
                    assert snapshot_database(store) == sibling_database
            finally:
                unavailable.rename(seed.home)
    for relative, _digest in seed.files:
        paths = [home / relative for home in (seed.home, *homes)]
        assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 3
    assert seed_files(seed.home) == seed.files


def test_copy_locks_packages_and_pending_state_are_independent(
    tmp_path, pending_native_bridge_seed, accepted_script_reconciliation_seed,
):
    seed = pending_native_bridge_seed.project
    copies = [pending_bridge_project(tmp_path / name, pending_native_bridge_seed) for name in ("left", "right")]
    homes = []
    for storage, project, revision, digest in copies:
        with closing(storage.projects.open(project)) as store:
            homes.append(store.home)
            proposal = assert_pending_bridge(store)
            assert (proposal.revision, proposal.content_hash) == (revision, digest)
    left_lease = ProjectAccessLease.acquire(homes[0], mode="exclusive")
    try:
        right_lease = ProjectAccessLease.acquire(homes[1], mode="exclusive")
        right_lease.close()
    finally:
        left_lease.close()
    active = ProjectAccessLease.acquire(seed.home, mode="shared")
    try:
        with pytest.raises(ValueError, match="active resources"):
            pending_bridge_project(tmp_path / "refused", pending_native_bridge_seed)
    finally:
        active.close()
    relative = next(path for path, _digest in seed.files if path.endswith("/delivery/storyboard.json"))
    retained = (homes[1] / relative).read_bytes()
    (homes[0] / relative).write_text("copied package mutation")
    assert (homes[1] / relative).read_bytes() == retained
    assert seed_files(seed.home) == seed.files
    # A valid Script-only seed has neither the accepted Storyboard nor pending Bridge.
    storage = ProjectFolderStorage(outputs_root=accepted_script_reconciliation_seed.home.parent,
        application_data_root=tmp_path / "wrong-state-application")
    with closing(storage.projects.open(accepted_script_reconciliation_seed.project_id)) as store:
        with pytest.raises(AssertionError):
            assert_pending_bridge(store)
