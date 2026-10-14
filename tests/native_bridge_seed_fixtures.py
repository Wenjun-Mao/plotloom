"""Closed pending Bridge project copies, with all native work created afresh."""
from contextlib import closing
from dataclasses import dataclass

from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import close_blockers
from tests.production_bridge_intent_fixtures import _pending_project
from tests.specialist_reconciliation_seed import (
    AcceptedScriptSeed, freeze_accepted_script_project, open_accepted_script_copy,
)


@dataclass(frozen=True)
class PendingBridgeSeed:
    project: AcceptedScriptSeed


def assert_pending_bridge(store):
    source = store.source_outline_state()
    assert source.source and source.accepted_outline and source.accepted_section_map
    assert source.graph_admission.status == "current" and not source.graph_admission.stale_reasons
    assert not source.section_map_stale_reasons
    for state in (store.cast_state(), store.art_state(), store.script_state(), store.storyboard_review_state()):
        assert state.accepted_review_state.status == "current" and not state.stale_reasons
    state = store.production_bridge_state()
    assert state.status == "ready" and not state.stale_reasons
    assert state.preparation.status == "available"
    assert state.installation is state.intent_job is state.presentation_job is state.presentation_candidate is None
    proposal = state.proposal
    assert proposal and not proposal.installable and proposal.presentation.reviewed
    assert proposal.intent_package.review_state == "pending"
    assert all(not entry.text for entry in proposal.intent_package.entries)
    assert not close_blockers(store)
    with store.repository.engine.connect() as connection:
        for model in set(CANDIDATE_ROWS.values()):
            table = model.__table__.name
            assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}" WHERE status != \'accepted\'').scalar() == 0
        for table in (
            "v2_autopilot_runs", "v2_autopilot_exec_attempts", "v2_generation_runs",
            "v2_media_tasks", "v2_video_jobs", "v2_image_jobs",
            "v2_character_reference_proposals", "v2_art_reference_proposals",
            "v2_production_bridge_intent_jobs",
        ):
            assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
    return proposal


def build_pending_bridge_seed(root):
    # This is the original 9/9-shot builder, not the reconciliation 1/4 seed.
    storage, project, _revision, _digest = _pending_project(root)
    with closing(storage.projects.open(project)) as store:
        assert_pending_bridge(store)
        home = store.home
    assert not (storage.application.root / "specialists").exists()
    return PendingBridgeSeed(freeze_accepted_script_project(home, project))


def pending_bridge_project(root, seed=None):
    if seed is None:
        return _pending_project(root)
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    with closing(open_accepted_script_copy(storage, seed.project)) as store:
        proposal = assert_pending_bridge(store)
        return storage, store.manifest.project_id, proposal.revision, proposal.content_hash
