"""Attended P3 lifecycle, dispatch and immutable output-association regressions."""
from contextlib import closing
import json
import pytest
from plotloom.autopilot_contracts import CheckpointEvidence, RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.image_commands import image_context
from plotloom.persistence.project.autopilot_bindings import assert_checkpoint_binding
from tests.autopilot_image_fixtures import deliver_image, image_environment
from tests.test_autopilot_images import current, sent_reference


def legacy_image_environment(tmp_path, monkeypatch):
    def historical_image_pin(code_revision):
        return {
            "version": "p1.5-pin.v1",
            "skillVersion": "plotloom-image-specialist.v3",
            "executionContract": "codex_specialist.v2",
            "codeRevision": code_revision,
            "skillHash": "c" * 64,
        }

    monkeypatch.setattr("plotloom.autopilot_launch.image_execution_pin", historical_image_pin)
    return image_environment(tmp_path, monkeypatch, auto_deliver=False)


def file_bytes(root):
    return {item.relative_to(root): item.read_bytes() for item in root.rglob("*") if item.is_file()}


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


@pytest.mark.parametrize(
    ("action", "restart"),
    [("cancel", False), ("cancel", True), ("takeover", False), ("takeover", True)],
)
def test_legacy_schema2_image_receipt_is_retained_after_cancel_or_takeover(
    tmp_path, monkeypatch, action, restart
):
    storage, registry, service, view, calls, _text = legacy_image_environment(tmp_path, monkeypatch)
    resumed = None
    try:
        retained, checkpoint = sent_reference(storage, service, view)
        job_id = checkpoint["evidence"]["jobId"]
        frozen_task_id = retained.policy.specialist_bindings["image"]
        policy_before = retained.policy.model_dump(mode="json", by_alias=True)
        with closing(storage.projects.open(view.project_id)) as store:
            before_context = image_context(store, "character-reference", job_id)
            request_hash = before_context["requestHash"]
            request_before = json.dumps(before_context["request"], sort_keys=True)
            package_path = store.image_exchange_for(before_context)._root() / "jobs" / job_id / "package"
            package_before = file_bytes(package_path)
            assert before_context["request"]["specialistPreflight"] == policy_before["executionPins"]["image"]
            assert json.loads((package_path / "request.json").read_text())["packageVersion"] == 4

        stopped = service.control(view.project_id, RunControlRequest(
            expected_revision=retained.revision, action=action
        ))
        assert stopped.state == {"cancel": "cancelled", "takeover": "taken_over"}[action]
        with closing(storage.projects.open(view.project_id)) as store:
            deliver_image(store, retained, checkpoint, manifest_schema_version=2)
            delivery_path = package_path.parent / "delivery"
            manifest = json.loads((delivery_path / "completion.json").read_text())
            pin = json.loads((delivery_path / "executor-pin.json").read_text())
            assert manifest["schemaVersion"] == 2
            assert manifest["toolEvidence"]["taskId"] == frozen_task_id
            assert pin["executionContract"] == "codex_specialist.v2"
            assert pin["skillVersion"] == "plotloom-image-specialist.v3"
            assert "nativeTaskId" not in pin
            published_before = file_bytes(delivery_path)

        active = service
        if restart:
            service.close()
            resumed = AutopilotService(storage, registry)
            assert resumed.acquire_controller()
            active = resumed
        active.step(view.project_id)

        result = current(storage, view)
        late_checkpoint = next(item for item in result.checkpoints if item["id"] == checkpoint["id"])
        assert result.state == {"cancel": "cancelled", "takeover": "taken_over"}[action]
        assert result.policy.model_dump(mode="json", by_alias=True) == policy_before
        assert late_checkpoint["state"] == "delivered"
        assert late_checkpoint["evidence"]["jobId"] == job_id
        assert late_checkpoint["evidence"]["requestHash"] == request_hash
        assert late_checkpoint["evidence"]["result"]["deliveryState"] == "inapplicable"
        assert late_checkpoint["evidence"]["result"]["candidateAssetIds"] == []
        assert calls == [job_id]
        assert registry.status(job_id) == {"state": "completed", "taskId": frozen_task_id}
        assert not registry.view()["busy"]

        with closing(storage.projects.open(view.project_id)) as store:
            after_context = image_context(store, "character-reference", job_id)
            assert after_context["requestHash"] == request_hash
            assert json.dumps(after_context["request"], sort_keys=True) == request_before
            assert file_bytes(package_path) == package_before
            assert file_bytes(delivery_path) == published_before
            with store.repository.engine.connect() as connection:
                assert_checkpoint_binding(
                    connection.connection.driver_connection,
                    view.project_id,
                    "delivered",
                    CheckpointEvidence.model_validate(late_checkpoint["evidence"]),
                    run_id=result.id,
                )
                delivery_state = connection.exec_driver_sql(
                    "SELECT state, diagnostic_code FROM v2_character_reference_proposal_deliveries WHERE proposal_id=?",
                    (job_id,),
                ).one()
                candidate_count = connection.exec_driver_sql(
                    "SELECT count(*) FROM v2_character_reference_proposal_candidates WHERE proposal_id=?",
                    (job_id,),
                ).scalar()
                assert delivery_state == ("inapplicable", "late_or_stale_delivery")
                assert candidate_count == 0
            assert not store.media.list_character_reference_decisions(view.project_id)["decisions"]
    finally:
        service.close()
        if resumed:
            resumed.close()


@pytest.mark.parametrize("action", ["cancel", "takeover"])
@pytest.mark.parametrize("wrong_task_id", ["6d1218af-044c-426a-99d2-18b76c5c6331", "exec-foreign-image-output"])
def test_wrong_legacy_task_id_keeps_late_image_reservation(tmp_path, monkeypatch, action, wrong_task_id):
    storage, registry, service, view, calls, _text = legacy_image_environment(tmp_path, monkeypatch)
    try:
        retained, checkpoint = sent_reference(storage, service, view)
        job_id = checkpoint["evidence"]["jobId"]
        frozen_task_id = retained.policy.specialist_bindings["image"]
        policy_before = retained.policy.model_dump(mode="json", by_alias=True)
        service.control(view.project_id, RunControlRequest(
            expected_revision=retained.revision, action=action
        ))
        with closing(storage.projects.open(view.project_id)) as store:
            deliver_image(store, retained, checkpoint, manifest_schema_version=2)
            context = image_context(store, "character-reference", job_id)
            delivery_path = store.image_exchange_for(context)._root() / "jobs" / job_id / "delivery"
            completion_path = delivery_path / "completion.json"
            manifest = json.loads(completion_path.read_text())
            manifest["toolEvidence"]["taskId"] = wrong_task_id
            completion_path.write_text(json.dumps(manifest))
            wrong_receipt = completion_path.read_bytes()
            package_path = delivery_path.parent / "package"
            package_before = file_bytes(package_path)

        service.step(view.project_id)

        result = current(storage, view)
        retained_checkpoint = next(item for item in result.checkpoints if item["id"] == checkpoint["id"])
        assert retained_checkpoint["state"] == "sent"
        assert retained_checkpoint["evidence"].get("deliveryHash") is None
        assert retained_checkpoint["evidence"]["result"].get("candidateAssetIds") is None
        assert result.state == {"cancel": "cancelled", "takeover": "taken_over"}[action]
        assert result.policy.model_dump(mode="json", by_alias=True) == policy_before
        assert calls == [job_id]
        assert registry.status(job_id) == {"state": "queued", "taskId": frozen_task_id}
        assert registry.view()["busy"]
        with closing(storage.projects.open(view.project_id)) as store:
            assert file_bytes(package_path) == package_before
            assert (delivery_path / "completion.json").read_bytes() == wrong_receipt
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql(
                    "SELECT count(*) FROM v2_character_reference_proposal_deliveries WHERE proposal_id=?",
                    (job_id,),
                ).scalar() == 0
                assert connection.exec_driver_sql(
                    "SELECT count(*) FROM v2_character_reference_proposal_candidates WHERE proposal_id=?",
                    (job_id,),
                ).scalar() == 0
            assert not store.media.list_character_reference_decisions(view.project_id)["decisions"]
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
