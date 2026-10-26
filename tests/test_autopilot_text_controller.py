"""Durable automatic text path and original dispatch identities, no real calls."""
from contextlib import closing
import json
import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.exceptions import InvalidTransitionError
from tests.autopilot_controller_fixtures import environment, run_text, deliver


def test_one_start_installs_complete_text_without_human_flags_or_video(tmp_path, monkeypatch):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch)
    try:
        completed = run_text(service, view)
        assert len(calls) == len(set(calls)) == 8
        assert len(completed.checkpoints) == 11
        assert completed.phase == "references" and completed.state == "running"
        with closing(storage.projects.open(view.project_id)) as store:
            bridge = store.production_bridge_state()
            assert bridge.installation.status == "current"
            assert bridge.proposal.intent_package.review_state == "ai_adopted"
            assert bridge.proposal.presentation.reviewed is False
            assert bridge.proposal.presentation.machine_adoption is not None
            assert store.source_outline_state().source.material.text == store.project().brief.synopsis
            run = store.repository.autopilot.current(view.project_id)
            outline_checkpoint = next(item for item in run.checkpoints if item["operationKey"] == "outline")
            assert outline_checkpoint["state"] == "adopted"
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, "outline")
            job_root = store.creative_handoff_exchange().root / "jobs" / attempt.job_id
            package_request = json.loads((job_root / "package" / "request.json").read_text(encoding="utf-8"))
            manifest = json.loads((job_root / "delivery" / "completion.json").read_text(encoding="utf-8"))
            assert attempt.plotloom_code_revision == run.policy.code_revision == "a" * 40
            assert receipt.plotloom_code_revision == run.policy.code_revision
            assert package_request["plotloomCodeRevision"] == run.policy.code_revision
            assert package_request["executionPin"]["upstreamRevision"] == "d" * 40
            assert manifest["executorProvenance"]["codeRevision"] == run.policy.code_revision
            assert manifest["executorProvenance"]["upstreamRevision"] == "d" * 40
            assert manifest["executorProvenance"]["codeRevision"] != manifest["executorProvenance"]["upstreamRevision"]
            with store.repository.engine.connect() as connection:
                for table in ("v2_approval_decisions", "v2_visual_intents", "v2_reviewed_shot_bindings", "v2_same_person_reviews", "v2_video_jobs"):
                    assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
        assert not registry.view()["busy"]
    finally:
        service.close()


def test_process_lease_precedes_controller_claim(tmp_path, monkeypatch):
    storage, registry, service, view, _calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    other = AutopilotService(storage, registry)
    try:
        assert service.acquire_controller()
        assert not other.acquire_controller()
        with pytest.raises(InvalidTransitionError, match="process lease"):
            other.step(view.project_id)
        service.close()
        assert other.acquire_controller()
        other.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.repository.autopilot.current(view.project_id).checkpoints[0]["operationKey"] == "source"
    finally:
        service.close()
        other.close()


def test_pause_retains_receipt_then_resume_adopts_original_outline_without_resend(tmp_path, monkeypatch):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            job = next(item["evidence"]["jobId"] for item in current.checkpoints if item["operationKey"] == "outline")
            request = store.outline_candidate_request(job)
        service.control(view.project_id, RunControlRequest(expected_revision=current.revision, action="pause"))
        with closing(storage.projects.open(view.project_id)) as store:
            deliver(store, request, host=registry._codex_exec_test_host)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            paused = store.repository.autopilot.current(view.project_id)
            assert paused.state == "paused" and store.source_outline_state().accepted_outline is None
        assert not registry.view()["busy"]
        service.control(view.project_id, RunControlRequest(expected_revision=paused.revision, action="resume"))
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.source_outline_state().accepted_outline is not None
        assert calls == [job]
    finally:
        service.close()


def test_unknown_ack_restart_checks_original_job_and_never_resends(tmp_path, monkeypatch):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    assert service.acquire_controller()
    for _ in range(3):
        service.step(view.project_id)
    with closing(storage.projects.open(view.project_id)) as store:
        current = store.repository.autopilot.current(view.project_id)
        checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
        request = store.outline_candidate_request(checkpoint["evidence"]["jobId"])
        attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
            current.id, "outline"
        )
    # Simulate the host losing its live process owner before the next poll.
    # Restart must inspect this exact attempt rather than sending a new one.
    registry._codex_exec_test_host.lose_attempt(attempt.attempt_id)
    service.close()
    resumed = AutopilotService(storage, registry)
    try:
        assert resumed.acquire_controller()
        for _ in range(4):
            resumed.step(view.project_id)
        assert calls == [request.job_id]
        with closing(storage.projects.open(view.project_id)) as store:
            unknown = store.repository.autopilot.current(view.project_id)
            checkpoint = next(item for item in unknown.checkpoints if item["operationKey"] == "outline")
            assert checkpoint["state"] == "outcome_unknown"
            assert checkpoint["evidence"]["result"]["dispatchOutcomeUnknown"] is True
            deliver(store, request, host=registry._codex_exec_test_host)
        resumed.step(view.project_id)
        resumed.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
            assert checkpoint["state"] == "adopted"
            assert checkpoint["evidence"]["result"]["dispatchOutcomeUnknown"] is True
        assert calls == [request.job_id]
        assert not registry.view()["busy"]
    finally:
        resumed.close()


@pytest.mark.parametrize("action", ["cancel", "takeover"])
def test_late_stopped_delivery_retains_proof_without_adoption(tmp_path, monkeypatch, action):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            job = next(item["evidence"]["jobId"] for item in current.checkpoints if item["operationKey"] == "outline")
            request = store.outline_candidate_request(job)
        service.control(view.project_id, RunControlRequest(expected_revision=current.revision, action=action))
        with closing(storage.projects.open(view.project_id)) as store:
            deliver(store, request, host=registry._codex_exec_test_host)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            stopped = store.repository.autopilot.current(view.project_id)
            assert stopped.state == ("cancelled" if action == "cancel" else "taken_over")
            checkpoint = next(item for item in stopped.checkpoints if item["operationKey"] == "outline")
            assert checkpoint["state"] == "delivered"
            assert store.source_outline_state().accepted_outline is None
            assert store.source_outline_state().candidate is None or store.source_outline_state().candidate.status == "cancelled"
        assert calls == [job] and not registry.view()["busy"]
    finally:
        service.close()


def test_occupied_native_role_waits_then_dispatches_same_prepared_job(tmp_path, monkeypatch):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    from plotloom.image_job_contracts import ImageJobError
    original = registry.codex_exec_admit
    occupied = [True]
    def admission(attempt):
        if occupied[0]:
            raise ImageJobError("codex_exec_outcome_unknown", "fixture Mac process slot is occupied")
        return original(attempt)
    monkeypatch.setattr(registry, "codex_exec_admit", admission)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            waiting = store.repository.autopilot.current(view.project_id)
            prepared = next(item for item in waiting.checkpoints if item["operationKey"] == "outline")
            assert waiting.state == "waiting" and prepared["state"] == "sent"
            attempt_before, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                waiting.id, "outline"
            )
        assert not calls
        occupied[0] = False
        service.step(view.project_id)
        assert calls == [prepared["evidence"]["jobId"]]
        with closing(storage.projects.open(view.project_id)) as store:
            attempt_after, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                view.id, "outline"
            )
        assert attempt_after.attempt_id == attempt_before.attempt_id
    finally:
        service.close()


@pytest.mark.parametrize("drift", ["profile", "pin"])
def test_frozen_configuration_drift_blocks_before_sending(tmp_path, monkeypatch, drift):
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from tests.autopilot_controller_fixtures import PIN
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        assert service.acquire_controller()
        service.step(view.project_id)
        service.step(view.project_id)
        if drift == "profile":
            original_profile = registry.codex_exec_profile()
            monkeypatch.setattr(
                registry,
                "codex_exec_profile",
                lambda: original_profile.model_copy(update={"model": "changed-profile"}),
            )
        else:
            monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: PIN | {"upstreamRevision": "d" * 40})
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            blocked = store.repository.autopilot.current(view.project_id)
            assert blocked.state == "blocked" and blocked.blocker["code"] == "contract_blocked"
            prepared = next(item for item in blocked.checkpoints if item["operationKey"] == "outline")
            assert prepared["state"] == "prepared"
        assert not calls and not registry.view()["busy"]
    finally:
        service.close()


def test_cli_rechecks_frozen_profile_after_reservation_before_spawn_intent(tmp_path, monkeypatch):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        assert service.acquire_controller()
        service.step(view.project_id)
        service.step(view.project_id)
        original_profile = registry.codex_exec_profile
        profile_reads = 0

        def drift_during_final_gate():
            nonlocal profile_reads
            profile_reads += 1
            profile = original_profile()
            if profile_reads == 3:
                return profile.model_copy(update={"model": "changed-after-reservation"})
            return profile

        monkeypatch.setattr(registry, "codex_exec_profile", drift_during_final_gate)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            blocked = store.repository.autopilot.current(view.project_id)
            checkpoint = next(item for item in blocked.checkpoints if item["operationKey"] == "outline")
            attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(
                blocked.id, "outline"
            )
            assert blocked.state == "blocked" and blocked.blocker["code"] == "contract_blocked"
            assert checkpoint["state"] == "prepared"
            assert attempt is None
        assert not calls and registry._codex_exec_test_host.admissions == 0
    finally:
        service.close()


def test_atomic_text_adoption_crash_keeps_delivery_but_rolls_back_heads_and_decision(tmp_path, monkeypatch):
    from plotloom.autopilot_contracts import CheckpointEvidence
    from plotloom.persistence.project.autopilot import AutopilotPersistence
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch)
    try:
        assert service.acquire_controller()
        for _ in range(4):
            service.step(view.project_id)
        original = AutopilotPersistence.checkpoint
        def crash(owner, key, **values):
            if key == "outline" and values["state"] == "adopted":
                assert isinstance(values["evidence"], CheckpointEvidence)
                raise RuntimeError("after owner adoption before checkpoint")
            return original(owner, key, **values)
        monkeypatch.setattr(AutopilotPersistence, "checkpoint", crash)
        with pytest.raises(RuntimeError, match="before checkpoint"):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
            assert checkpoint["state"] == "delivered"
            assert store.source_outline_state().accepted_outline is None
        monkeypatch.setattr(AutopilotPersistence, "checkpoint", original)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.source_outline_state().accepted_outline is not None
        assert len(calls) == 1
    finally:
        service.close()


def test_interrupted_export_reuses_original_prepared_job_without_partial_package(tmp_path, monkeypatch):
    import plotloom.creative_handoff_package_exchange as exchange_owner
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch)
    try:
        assert service.acquire_controller()
        service.step(view.project_id)
        original = exchange_owner._write_once
        def interrupted(path, contents):
            original(path, contents)
            raise RuntimeError("interrupted static package publication")
        monkeypatch.setattr(exchange_owner, "_write_once", interrupted)
        with pytest.raises(RuntimeError, match="static package"):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
            assert checkpoint["state"] == "prepared"
            job = checkpoint["evidence"]["jobId"]
            assert not (store.home / "outputs/creative-handoff/jobs" / job / "package").exists()
        assert not calls
        monkeypatch.setattr(exchange_owner, "_write_once", original)
        service.step(view.project_id)
        service.step(view.project_id)
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.source_outline_state().accepted_outline is not None
            assert next(item for item in store.repository.autopilot.current(view.project_id).checkpoints if item["operationKey"] == "outline")["evidence"]["jobId"] == job
        assert calls == [job]
    finally:
        service.close()


def test_general_routes_install_all_66_intent_targets_in_one_bounded_native_job(tmp_path, monkeypatch):
    from plotloom.story_workloads import FIXED_CHINESE_BRIEF
    from plotloom.source_structures import complete_routes
    from plotloom.stage_contracts import StageName
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch,
        brief=FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 180}))
    try:
        completed = run_text(service, view)
        assert len(calls) == len(set(calls)) == 8
        with closing(storage.projects.open(view.project_id)) as store:
            bridge = store.production_bridge_state()
            assert len(bridge.proposal.intent_package.entries) == 66
            graph = store.authoring.get_stage_payload(view.project_id, StageName.STORY_GRAPH)
            routes = complete_routes(graph)
            assert len(routes) == 6 and len({route[-1] for route in routes}) == 3
            assert len(bridge.installation.cuts) == 54
        assert completed.phase == "references"
    finally:
        service.close()


def test_intent_bound_does_not_drop_or_split_over_ceiling_targets():
    from plotloom.production_bridge_intent_contract import intent_response_schema, bind_intent_suggestions
    ids = [f"target-{index}" for index in range(128)]
    schema = intent_response_schema(ids)
    assert schema["properties"]["entries"]["minItems"] == schema["properties"]["entries"]["maxItems"] == 128
    result = {"entries": [{"id": key, "suggestedText": "An irreversible decision."} for key in ids]}
    assert len(bind_intent_suggestions(result, ids)) == 128
    with pytest.raises(ValueError, match="bounded"):
        intent_response_schema([*ids, "target-extra"])
    with pytest.raises(ValueError):
        bind_intent_suggestions({"entries": result["entries"][:-1]}, ids)
    for replacement in ("target-0", "foreign-target"):
        with pytest.raises(ValueError, match="exactly once"):
            bind_intent_suggestions({"entries": [*result["entries"][:-1], {"id": replacement, "suggestedText": "A decision."}]}, ids)


def test_start_api_retains_one_policy_and_refuses_browser_authority_fields(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from plotloom.api import create_project_folder_authoring_app
    storage, _registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        client = TestClient(create_project_folder_authoring_app(storage))
        body = {"expectedBriefRevision": 1, "renderStyle": "realistic", "artRenderStyle": "realistic"}
        first = client.post(f"/api/v2/projects/{view.project_id}/autopilot/start", json=body)
        second = client.post(f"/api/v2/projects/{view.project_id}/autopilot/start", json=body | {"maxImages": 1})
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] == second.json()["id"] == view.id
        assert first.json()["policy"] == second.json()["policy"]
        assert client.post(f"/api/v2/projects/{view.project_id}/autopilot/start", json=body | {"claim": "forged"}).status_code == 422
        assert client.get(f"/api/v2/projects/{view.project_id}/autopilot").json()["id"] == view.id
        assert not calls
    finally:
        service.close()
