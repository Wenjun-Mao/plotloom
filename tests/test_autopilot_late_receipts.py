"""Unknown bridge settlement and identical frozen execution gates in all states."""
from contextlib import closing
import json
import subprocess
from pathlib import Path
import pytest
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService
from tests.autopilot_controller_fixtures import environment


def prepared(storage, service, view, stage):
    assert service.acquire_controller()
    for _ in range(40):
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
        checkpoint = next((item for item in current.checkpoints if item["operationKey"] == stage), None)
        if checkpoint is not None:
            assert checkpoint["state"] == "prepared"
            return current, checkpoint
    raise AssertionError("fixture stage preparation not reached")


def stop(storage, service, current, state):
    if state == "paused":
        service.control(current.project_id, RunControlRequest(expected_revision=current.revision, action="pause"))
    elif state == "blocked":
        with closing(storage.projects.open(current.project_id)) as store:
            store.repository.autopilot.blocker(current.project_id, code="test_hold", message="fixture hold")


@pytest.mark.parametrize("stage", ["bridge-intent", "bridge-presentation"])
@pytest.mark.parametrize("state", ["paused", "blocked"])
def test_uncertain_bridge_late_receipt_settles_without_proposal_or_human_edits(tmp_path, monkeypatch, stage, state):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch)
    try:
        _current, checkpoint = prepared(storage, service, view, stage)
        queue = subprocess.run
        def lost_ack(command, **kwargs):
            result = queue(command, **kwargs)
            return subprocess.CompletedProcess(command, 1, "") if len(command) > 1 and command[1] == "queue" else result
        monkeypatch.setattr(subprocess, "run", lost_ack)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            original = store.production_bridge_state().proposal.content_hash
            assert store.repository.production_bridge_intent.load_job(view.project_id, checkpoint["evidence"]["jobId"])["status"] == "outcome_unknown"
        stop(storage, service, current, state)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            retained = next(item for item in current.checkpoints if item["operationKey"] == stage)
            assert retained["state"] == "delivered"
            assert store.production_bridge_state().proposal.content_hash == original
            assert store.repository.production_bridge_intent.load_job(view.project_id, checkpoint["evidence"]["jobId"])["status"] == "outcome_unknown"
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_approval_decisions").scalar() == 0
        assert not registry.view()["busy"]
        original_calls = list(calls)
        service.control(view.project_id, RunControlRequest(expected_revision=current.revision, action="resume"))
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            assert next(item for item in store.repository.autopilot.current(view.project_id).checkpoints if item["operationKey"] == stage)["state"] == "adopted"
        assert calls == original_calls
    finally:
        service.close()


@pytest.mark.parametrize("state", ["running", "paused", "blocked", "retained-then-restart"])
def test_foreign_text_execution_never_gains_receipt_or_adoption_authority(tmp_path, monkeypatch, state):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch)
    resumed = None
    try:
        _current, checkpoint = prepared(storage, service, view, "outline")
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            request = store.outline_candidate_request(checkpoint["evidence"]["jobId"])
            path = Path(store.creative_handoff_exchange().write_package(request, store.creative_handoff_execution_pin(request))["deliveryPath"]) / "completion.json"
        stop(storage, service, current, "paused" if state == "retained-then-restart" else state)
        if state == "retained-then-restart":
            service.step(view.project_id)
        manifest = json.loads(path.read_text())
        manifest["executorProvenance"]["codeRevision"] = "d" * 40
        path.write_text(json.dumps(manifest, ensure_ascii=False))
        if state == "retained-then-restart":
            with closing(storage.projects.open(view.project_id)) as store:
                current = store.repository.autopilot.current(view.project_id)
            service.close()
            resumed = AutopilotService(storage, registry)
            assert resumed.acquire_controller()
            resumed.control(view.project_id, RunControlRequest(expected_revision=current.revision, action="resume"))
        active = resumed or service
        original_calls = list(calls)
        active.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            assert store.source_outline_state().accepted_outline is None
            assert next(item for item in current.checkpoints if item["operationKey"] == "outline")["state"] != "adopted"
        assert calls == original_calls
        assert json.loads(path.read_text())["executorProvenance"]["codeRevision"] == "d" * 40
    finally:
        service.close()
        if resumed:
            resumed.close()
