"""Unknown Codex Exec outcomes retain late proof without bypassing stage owners."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import ProductionBridgeIntentJobRow
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
def test_uncertain_bridge_late_receipt_settles_without_proposal_or_human_edits(
    tmp_path, monkeypatch, stage, state
):
    storage, registry, service, view, _calls = environment(tmp_path, monkeypatch)
    host = registry._codex_exec_test_host
    try:
        _current, checkpoint = prepared(storage, service, view, stage)
        host.auto_deliver = False
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                current.id, stage
            )
            original = store.production_bridge_state().proposal.content_hash
            assert attempt is not None and attempt.state == "running"
            assert receipt is None

        host.lose_attempt(attempt.attempt_id)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            retained = next(item for item in current.checkpoints if item["operationKey"] == stage)
            unknown, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                current.id, stage
            )
            assert retained["state"] == "outcome_unknown"
            assert retained["evidence"]["result"]["dispatchOutcomeUnknown"] is True
            assert unknown.state == "outcome_unknown" and receipt is None
            assert store.production_bridge_state().proposal.content_hash == original

        stop(storage, service, current, state)
        with closing(storage.projects.open(view.project_id)) as store:
            request = host.request(store, unknown)
            host.complete(store, request, unknown)
            host.pending.discard(str(unknown.attempt_id))
        service.step(view.project_id)

        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            retained = next(item for item in current.checkpoints if item["operationKey"] == stage)
            settled, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                current.id, stage
            )
            assert retained["state"] == "delivered"
            assert retained["evidence"]["result"]["dispatchOutcomeUnknown"] is True
            assert settled.state == "completed" and receipt is not None
            assert store.production_bridge_state().proposal.content_hash == original
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_approval_decisions").scalar() == 0
            with store.repository._read() as session:
                retained_job = session.get(ProductionBridgeIntentJobRow, request.job_id)
                assert retained_job.candidate is None
                retained_evidence = deepcopy(retained_job.response_evidence)
                retained_hash = retained_job.response_hash
            delivery = service.controller.validated_delivery(store, current, stage, request)
            owner = store.repository.production_bridge_intent
            # Refuse every mismatch even when this receipt has no candidate yet.
            for field, value in (("response_hash", "0" * 64),
                                 ("response_evidence", {**retained_evidence, "extra": "foreign"}),
                                 ("candidate", {"foreign": True}),
                                 ("transport", "text_api"),
                                 ("native_request", request.model_copy(update={"job_id": "ch_000000000000000000000001"}).model_dump(mode="json", by_alias=True))):
                row = SimpleNamespace(native_request=request.model_dump(mode="json", by_alias=True),
                    transport="codex_native", response_evidence=retained_evidence,
                    response_hash=retained_hash, candidate=None)
                setattr(row, field, value)
                with patch.object(owner, "_job", return_value=row):
                    with pytest.raises(InvalidTransitionError):
                        owner.retain_native_candidate(current.project_id, delivery)
                assert getattr(row, field) == value
        assert not registry.view()["busy"]

        original_calls = list(host.calls)
        service.control(
            view.project_id,
            RunControlRequest(expected_revision=current.revision, action="resume"),
        )
        host.auto_deliver = True
        for index in range(8):
            service.step(view.project_id)
            with closing(storage.projects.open(view.project_id)) as store:
                current = store.repository.autopilot.current(view.project_id)
                if index == 0:
                    assert store.production_bridge_state().proposal.content_hash == original
                    with store.repository._read() as session:
                        retained_job = session.get(ProductionBridgeIntentJobRow, request.job_id)
                        assert retained_job.candidate == delivery.candidate
                        assert retained_job.response_evidence == retained_evidence
                        assert retained_job.response_hash == retained_hash
            if next(item for item in current.checkpoints if item["operationKey"] == stage)["state"] == "adopted":
                break
        else:
            raise AssertionError("Late bridge candidate did not complete independent checking")
        assert host.calls[:len(original_calls)] == original_calls
        assert host.calls.count(request.job_id) == 1
        assert len(host.calls) == len(set(host.calls)) == len(original_calls) + 1
    finally:
        service.close()


def test_foreign_codex_manifest_cannot_gain_text_adoption_authority(tmp_path, monkeypatch):
    storage, registry, service, view, _calls = environment(
        tmp_path, monkeypatch, auto_deliver=False
    )
    host = registry._codex_exec_test_host
    try:
        _current, checkpoint = prepared(storage, service, view, "outline")
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            request = store.outline_candidate_request(checkpoint["evidence"]["jobId"])
            attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                current.id, "outline"
            )
            assert attempt is not None and attempt.state == "running"
            host.complete(store, request, attempt)
            delivery_path = (
                Path(store.creative_handoff_exchange().root)
                / "jobs"
                / attempt.job_id
                / "delivery"
                / "completion.json"
            )

        manifest = json.loads(delivery_path.read_text(encoding="utf-8"))
        manifest["executorProvenance"]["codeRevision"] = "d" * 40
        delivery_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        service.step(view.project_id)

        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            retained = next(item for item in current.checkpoints if item["operationKey"] == "outline")
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                current.id, "outline"
            )
            assert attempt.state == "completed" and receipt is not None
            assert store.source_outline_state().accepted_outline is None
            assert retained["state"] != "adopted"
            assert json.loads(delivery_path.read_text(encoding="utf-8"))["executorProvenance"]["codeRevision"] == "d" * 40
    finally:
        service.close()
