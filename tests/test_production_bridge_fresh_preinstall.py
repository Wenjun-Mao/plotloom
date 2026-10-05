"""Fresh proposal preparation preserves first-install and execution ownership."""
from contextlib import closing
from uuid import uuid4

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import InvalidTransitionError
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.project_storage import ProjectFolderStorage
from tests.test_production_bridge import _prepare_installable_bridge, _source_shaped_review_board
from tests.test_project_storage_art import _deliver_stage
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.test_production_bridge_intent import FakeAdapter, FakeResolver, _pending_project, _profile, _wait_for_job
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from plotloom.pipeline import RunSecretBroker


def test_stale_preinstall_preparation_retains_history_and_resets_whole_review(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"}))) as store:
        old = _prepare_installable_bridge(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + uuid4().hex)
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", _source_shaped_review_board(), "renewed-source-fixture"))
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=1, binding=ready.binding))
        assert store.production_bridge_state().status == "stale"
        assert not store.production_bridge_state().has_installation
        with pytest.raises(InvalidTransitionError, match="stale"):
            store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=old.revision, expected_content_hash=old.content_hash))
        fresh = store.prepare_production_bridge().proposal
        assert fresh.revision == old.revision + 1
        assert not fresh.installable
        assert fresh.intent_package.review_state == "pending"
        assert all(not entry.text for entry in fresh.intent_package.entries)
        assert not fresh.presentation.reviewed
        with store.repository.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT content_hash FROM v2_production_bridge_revisions WHERE project_id = ? AND revision = ?", (store.manifest.project_id, old.revision)).scalar_one() == old.content_hash



def test_first_install_history_refuses_fresh_proposals_even_after_currentness_changes(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"}))) as store:
        old = _prepare_installable_bridge(store)
        store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=old.revision, expected_content_hash=old.content_hash))
        original = store.project()
        store.update_brief(original.brief.model_copy(update={"genre": "changed after install"}), expected_revision=original.revision)
        state = store.production_bridge_state()
        assert state.status == "stale" and state.has_installation
        with pytest.raises(InvalidTransitionError, match="before first installation"):
            store.prepare_production_bridge()


@pytest.mark.parametrize("unknown", [False, True])
def test_unresolved_intent_execution_refuses_preparation_without_resend(tmp_path, unknown):
    storage, project_id, revision, digest = _pending_project(tmp_path)
    adapter = FakeAdapter("unknown" if unknown else "success", held=True)
    service = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        job = service.create(project_id, expected_revision=revision, expected_hash=digest, profile_snapshot=_profile())
        assert adapter.started.wait(8)
        if unknown:
            _wait_for_job(service, adapter, job)
        with closing(storage.projects.open(project_id)) as store:
            with pytest.raises(InvalidTransitionError, match="unresolved"):
                store.prepare_production_bridge()
            assert store.production_bridge_state().proposal.revision == revision
        assert adapter.calls == 1
    finally:
        adapter.release.set()
        service.close()
