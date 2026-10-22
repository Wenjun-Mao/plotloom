"""Pending replacement reviews cannot outlive their canonical target."""

from contextlib import closing

import pytest

from plotloom.domain import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.production_bridge_contracts import ProductionBridgeIntentUpdateRequest
from tests.production_bridge_fixtures import (
    _prepare_installable_bridge,
    _review_fixture_presentation,
)
from tests.production_bridge_intent_fixtures import _profile
from tests.production_rebuild_fixtures import _accept, _heads, _review, _store


def _edit_board(store):
    project_id = store.manifest.project_id
    head = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
    board = store.authoring.get_stage_payload(
        project_id, StageName.STORYBOARD
    ).model_dump(mode="json", by_alias=True)
    board["shots"][0]["title"] += " revised during proposal review"
    store.authoring.update_stage(project_id, StageName.STORYBOARD, head.revision, board)


def test_target_drift_is_visible_and_fresh_preparation_recovers_without_borrowing_reviews(
    tmp_path,
):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        proposal = _review(
            store,
            store.prepare_production_bridge(installed.preparation.request).proposal,
        )
        _edit_board(store)
        before = store.production_bridge_state()
        assert before.status == "stale"
        assert before.stale_reasons == ["production rebuild replacement target changed"]
        assert before.installation.status == "outdated"
        assert before.preparation.status == "available"
        heads = _heads(store)
        with pytest.raises(InvalidTransitionError, match="stale"):
            store.update_production_bridge_intent_package(
                ProductionBridgeIntentUpdateRequest(
                    expected_proposal_revision=proposal.revision,
                    expected_content_hash=proposal.content_hash,
                    entries=[
                        {"id": entry.id, "text": entry.text}
                        for entry in proposal.intent_package.entries
                    ],
                )
            )
        with pytest.raises(InvalidTransitionError, match="stale"):
            _review_fixture_presentation(store, proposal)
        with pytest.raises(InvalidTransitionError, match="changed before inference"):
            store.repository.production_bridge_intent.source_context(
                store.manifest.project_id,
                expected_revision=proposal.revision,
                expected_hash=proposal.content_hash,
            )
        assert store.production_bridge_state() == before
        assert _heads(store) == heads
        fresh = store.prepare_production_bridge(before.preparation.request)
        assert fresh.status == "ready"
        assert fresh.installation == before.installation
        assert fresh.proposal.intent_package.review_state == "pending"
        assert not fresh.proposal.presentation.reviewed
        accepted = _accept(store, _review(store, fresh.proposal))
        assert accepted.status == "accepted"
        assert accepted.installation.status == "current"
        assert accepted.stale_reasons == []


@pytest.mark.parametrize("phase", ["queued", "dispatched"])
def test_target_drift_blocks_model_dispatch_or_late_adoption(tmp_path, phase):
    _, store = _store(tmp_path)
    with closing(store):
        installed = _accept(store, _prepare_installable_bridge(store))
        proposal = store.prepare_production_bridge(
            installed.preparation.request
        ).proposal
        owner, project_id = (
            store.repository.production_bridge_intent,
            store.manifest.project_id,
        )
        job_id = owner.enqueue(
            project_id,
            expected_revision=proposal.revision,
            expected_hash=proposal.content_hash,
            profile_snapshot=_profile(),
            prompt_trace={"prompt_version": "1", "rendered_hash": "a" * 64},
            prompt_messages=[],
            response_schema={},
        )
        if phase == "dispatched":
            assert owner.mark_dispatched(project_id, job_id)
        _edit_board(store)
        heads = _heads(store)
        if phase == "queued":
            assert not owner.mark_dispatched(project_id, job_id)
        else:
            owner.finish_success(
                project_id,
                job_id,
                suggestions={
                    entry.id: "obsolete target suggestion"
                    for entry in proposal.intent_package.entries
                },
                response_evidence={"retained": "late response"},
                response_hash="b" * 64,
                provider_request_id="late-target",
                usage=None,
            )
        state = store.production_bridge_state()
        assert state.intent_job.status == "stale"
        assert state.proposal == proposal
        assert state.status == "stale"
        assert _heads(store) == heads
