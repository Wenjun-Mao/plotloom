"""Fresh fake API jobs admit advice from copies without reading their seed."""
from contextlib import closing

from plotloom.pipeline import RunSecretBroker
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from tests.autopilot_seed_fixtures import seed_files
from tests.native_bridge_seed_fixtures import pending_bridge_project
from tests.production_bridge_intent_fixtures import FakeAdapter, FakeResolver, _profile, _wait_for_job
from tests.specialist_reconciliation_support import snapshot_database


def test_copied_pending_project_admits_fresh_api_job_without_seed_or_sibling_edits(
    tmp_path, pending_native_bridge_seed,
):
    seed = pending_native_bridge_seed.project
    storage, project, revision, digest = pending_bridge_project(tmp_path / "left", pending_native_bridge_seed)
    sibling, sibling_project, _revision, _digest = pending_bridge_project(tmp_path / "right", pending_native_bridge_seed)
    with closing(sibling.projects.open(sibling_project)) as store:
        sibling_database = snapshot_database(store)
        sibling_proposal = store.production_bridge_state().proposal
    adapter = FakeAdapter(held=True)
    service = None
    unavailable = seed.home.with_name(seed.home.name + "-unavailable")
    seed.home.rename(unavailable)
    try:
        service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
        job = service.create(project, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        assert adapter.started.wait(8)
        with closing(storage.projects.open(project)) as store:
            state = store.production_bridge_state()
            assert state.intent_job.id == job and state.intent_job.transport == "text_api"
            assert state.intent_job.profile_id == "fake" and state.intent_job.status == "dispatched"
            assert state.proposal.revision == revision and state.proposal.content_hash == digest
        _wait_for_job(service, adapter, job)
        assert adapter.calls == 1 and not seed.home.exists()
        with closing(storage.projects.open(project)) as store:
            state = store.production_bridge_state()
            assert state.intent_job.id == job and state.intent_job.status == "ready"
            assert state.proposal.revision == revision + 1
            assert state.proposal.intent_package.review_state == "model_suggested"
            assert state.proposal.intent_package.suggestion_origin == "model_inference.v1"
            assert state.proposal.intent_package.provenance["jobId"] == job
            assert state.installation is None and not state.proposal.installable
        with closing(sibling.projects.open(sibling_project)) as store:
            state = store.production_bridge_state()
            assert state.intent_job is None and state.proposal == sibling_proposal
            assert snapshot_database(store) == sibling_database
    finally:
        # Release a held fake worker before executor shutdown, including failures.
        adapter.release.set()
        try:
            if service is not None:
                service.close()
        finally:
            unavailable.rename(seed.home)
    assert seed_files(seed.home) == seed.files
