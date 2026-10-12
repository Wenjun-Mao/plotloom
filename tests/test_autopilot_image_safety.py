"""Attended P3 lifecycle, dispatch and immutable output-association regressions."""
from contextlib import closing
import pytest
from plotloom.autopilot_contracts import CheckpointEvidence, RunControlRequest
from plotloom.image_commands import image_context
from plotloom.persistence.project.autopilot_bindings import assert_checkpoint_binding
from tests.autopilot_image_fixtures import image_environment
from tests.test_autopilot_images import current


def reach(storage, service, view, owner, state):
    for _ in range(24):
        service.step(view.project_id)
        result = current(storage, view)
        checkpoint = next((item for item in result.checkpoints if item["evidence"]["owner"] == owner), None)
        if checkpoint is not None and checkpoint["state"] == state:
            return result, checkpoint
        assert result.state in {"running", "waiting"}, result.blocker
    raise AssertionError("bounded native fixture boundary not reached")


@pytest.mark.parametrize("owner", ["character-reference", "art-reference"])
@pytest.mark.parametrize("action", ["cancel", "takeover"])
def test_stop_after_reference_ingestion_preserves_terminal_owner_and_prevents_selection(tmp_path, monkeypatch, owner, action):
    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        retained, checkpoint = reach(storage, service, view, owner, "delivered")
        stopped = service.control(view.project_id, RunControlRequest(expected_revision=retained.revision, action=action))
        assert stopped.state == {"cancel": "cancelled", "takeover": "taken_over"}[action]
        original_calls = list(calls)
        service.step(view.project_id)
        result = current(storage, view)
        assert next(item for item in result.checkpoints if item["id"] == checkpoint["id"])["state"] == "delivered"
        with closing(storage.projects.open(view.project_id)) as store:
            assert image_context(store, owner, checkpoint["evidence"]["jobId"])["state"] == "delivered"
        assert calls == original_calls and not registry.view()["busy"]
    finally:
        service.close()


@pytest.mark.parametrize("state", ["delivered", "adopted"])
def test_direct_shot_cancellation_withdraws_automatic_authority_before_bundle(tmp_path, monkeypatch, state):
    storage, _registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        _retained, checkpoint = reach(storage, service, view, "image", state)
        with closing(storage.projects.open(view.project_id)) as store:
            store.media.cancel_image_job(view.project_id, checkpoint["evidence"]["jobId"], "Manual cancellation fixture")
        withdrawn = current(storage, view)
        assert withdrawn.state == "taken_over"
        original_calls = list(calls)
        service.step(view.project_id)
        result = current(storage, view)
        assert result.bundle is None and calls == original_calls
        assert len(result.frames) == (1 if state == "adopted" else 0)
    finally:
        service.close()


@pytest.mark.parametrize("race", [False, True])
def test_partial_execution_publication_blocks_initial_or_final_native_send(tmp_path, monkeypatch, race):
    storage, registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        _retained, checkpoint = reach(storage, service, view, "character-reference", "prepared")
        with closing(storage.projects.open(view.project_id)) as store:
            context = image_context(store, "character-reference", checkpoint["evidence"]["jobId"])
            delivery = store.image_exchange_for(context)._root() / "jobs" / checkpoint["evidence"]["jobId"] / "delivery"
        def partial():
            delivery.mkdir()
            (delivery / "executor-pin.json").write_bytes(b"retained in-progress execution evidence")
        if race:
            original = registry.dispatch
            def dispatch(role, **kwargs):
                partial()
                return original(role, **kwargs)
            monkeypatch.setattr(registry, "dispatch", dispatch)
        else:
            partial()
        service.step(view.project_id)
        result = current(storage, view)
        assert result.state == "blocked" and result.blocker["code"] == "delivery_conflict"
        assert next(item for item in result.checkpoints if item["id"] == checkpoint["id"])["state"] == "prepared"
        assert (delivery / "executor-pin.json").read_bytes() == b"retained in-progress execution evidence"
        assert not calls and not registry.view()["busy"]
    finally:
        service.close()


@pytest.mark.parametrize("field,value", [("output_filename", "foreign.png"), ("output_hash", "d" * 64), ("role", "refinement")])
def test_retained_candidate_must_match_exact_manifest_output(tmp_path, monkeypatch, field, value):
    storage, _registry, service, view, _calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        _retained, checkpoint = reach(storage, service, view, "character-reference", "delivered")
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository.engine.begin() as connection:
                connection.exec_driver_sql(f'UPDATE v2_character_reference_proposal_candidates SET "{field}"=? WHERE proposal_id=?', (value, checkpoint["evidence"]["jobId"]))
                with pytest.raises(ValueError, match="exact manifest outputs"):
                    assert_checkpoint_binding(connection.connection.driver_connection, view.project_id, "delivered",
                        CheckpointEvidence.model_validate(checkpoint["evidence"]), run_id=view.id)
    finally:
        service.close()
