"""Truthful independent checking and exact creative/provider boundaries."""
from contextlib import closing
from copy import deepcopy
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.exceptions import InvalidTransitionError
from plotloom.production_brief import assert_adaptable, production_brief
from plotloom.video_batch_basis import assert_new_dispatch_authority
from plotloom.video_batch_contracts import BatchControl, BatchSetup, BatchStart
from plotloom.video_directions_contract import bind_fidelity, render_report
from tests.autopilot_controller_fixtures import PIN
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.codex_exec_fixtures import install_profile
from tests.video_batch_fixtures import (
    batch_environment,
    draft_for,
    ready_batch,
    start_batch,
)
from tests.video_fidelity_fixtures import fidelity_for


def request_for(view):
    return CreativeHandoffRequest(job_id="ch_" + "a" * 32, project_id=view["projectId"], section_id=view["id"],
        stage="video-directions", expected_stage_revision=view["revision"], source={"operation": "fidelity-check"},
        input_artifacts={"video-targets.json": {"targets": view["manifest"]["targets"]},
            "language-contract.json": view["manifest"]["languageContract"]}, creative_brief="Check exact candidate.")


def test_native_drafter_and_checker_are_distinct_retained_invocations(tmp_path):
    storage, _client, service, provider, project, view = batch_environment(tmp_path)
    install_profile(service.registry)
    host = FakeCodexExecHost(storage, service.registry, candidate_factory=lambda _store, request:
        fidelity_for(request) if request.source.get("operation") == "fidelity-check"
        else draft_for(view).model_dump(mode="json", by_alias=True))
    service.registry.codex_exec_admit, service.registry.codex_exec_status = host.admit, host.status
    with patch.object(CreativeHandoffExchange, "current_execution_pin", return_value=PIN):
        service.draft(project, view["revision"])
        for _ in range(6):
            service.step(project)
        ready = service.current(project)
    assert ready["state"] == "ready", ready["execution"].get("error")
    draft, check = ready["execution"]["draft"], ready["execution"]["fidelity"]
    assert len(host.calls) == 2
    assert draft["attempt"]["attemptId"] != check["attempt"]["attemptId"]
    assert check["request"]["source"]["draftAttemptId"] == draft["attempt"]["attemptId"]
    assert check["request"]["inputArtifacts"]["language-contract.json"] == ready["manifest"]["languageContract"]
    assert draft["receipt"] and check["receipt"] and not provider.submits
    assert not ready["execution"].get("authorizedManifestHash")
    with closing(storage.projects.open(project)) as store:
        from plotloom.project_storage.video_batch_evidence import retained_batch_drafts
        with store.repository._read() as session:
            retained = retained_batch_drafts(session.connection().connection.driver_connection)
        assert len(retained) == 2


@pytest.mark.parametrize("code", ["omission", "negation", "extra_speech", "invented_decision", "sound_role", "visible_text"])
def test_rejected_semantic_candidate_cannot_authorize_or_dispatch(tmp_path, code):
    _storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    host = service.registry._video_fidelity_test_host
    def rejected(_store, request):
        result = fidelity_for(request, reject=True)
        result["targets"][0]["findings"][0]["code"] = code
        return result
    host.candidate_factory = rejected
    edited = draft_for(ready)
    edited.targets[0].fields[0].english += " A changed candidate."
    with patch.object(CreativeHandoffExchange, "current_execution_pin", return_value=PIN):
        service.edit_directions(project, ready["revision"], edited)
        for _ in range(3): service.step(project)
        rejected_view = service.current(project)
    assert rejected_view["state"] == "translation_rejected"
    assert not provider.submits
    assert len(rejected_view["execution"]["fidelityHistory"]) == 1
    assert rejected_view["manifest"]["targets"][0]["fidelity"]["findings"][0]["code"] == code
    with pytest.raises(InvalidTransitionError): start_batch(service, project, rejected_view)
    # The unchanged rejected candidate retains its actual check; no retry loop.
    before = len(host.calls)
    assert service.edit_directions(project, rejected_view["revision"], edited)["revision"] == rejected_view["revision"]
    assert len(host.calls) == before


def test_candidate_edit_invalidates_check_and_correction_gets_new_exact_attempt(tmp_path):
    storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    original = deepcopy(ready["execution"]["fidelity"])
    unchanged = service.edit_directions(project, ready["revision"], draft_for(ready))
    assert unchanged["revision"] == ready["revision"]
    edited = draft_for(ready)
    edited.targets[0].fields[0].english += " Corrected physical direction."
    with patch.object(CreativeHandoffExchange, "current_execution_pin", return_value=PIN):
        checking = service.edit_directions(project, ready["revision"], edited)
        assert checking["state"] == "checking"
        assert "fidelityCheck" not in checking["manifest"]["targets"][0]["directions"]
        with pytest.raises(InvalidTransitionError): start_batch(service, project, checking)
        for _ in range(3): service.step(project)
    current = service.current(project)
    assert current["state"] == "ready"
    assert current["execution"]["fidelity"]["attempt"]["attemptId"] != original["attempt"]["attemptId"]
    assert current["execution"]["fidelityHistory"] == [original]
    assert not provider.submits
    with closing(storage.projects.open(project)) as store:
        assert store.repository.video_batches.receipt(current["id"]) is None


@pytest.mark.parametrize("mutation", ["missing_target", "missing_path", "dimension", "source", "candidate", "prompt", "invented_actor"])
def test_checker_json_cannot_self_certify_incomplete_or_different_inputs(tmp_path, mutation):
    _storage, _client, service, _provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    request = request_for(ready)
    result = fidelity_for(request)
    target = result["targets"][0]
    if mutation == "missing_target": result["targets"].pop()
    elif mutation == "missing_path": target["checkedPaths"].pop()
    elif mutation == "dimension": target["checkedDimensions"][0] = "uninspected"
    elif mutation == "source": target["sourceHash"] = "0" * 64
    elif mutation == "candidate": target["candidateHash"] = "0" * 64
    elif mutation == "prompt": target["compiledPromptSha256"] = "0" * 64
    else: target["creatorAuthorized"] = True
    with pytest.raises(ValueError): bind_fidelity(request, result)


def test_projection_is_complete_derived_and_settings_bound(tmp_path):
    _storage, _client, _service, _provider, _project, view = batch_environment(tmp_path)
    snapshot = deepcopy(view["manifest"]["targets"][0]["snapshot"])
    original = deepcopy(snapshot)
    brief = production_brief(snapshot)
    assert {item["id"] for item in brief["sections"]} == {"shot", "context", "presentation", "references", "timing", "settings"}
    assert next(item for item in brief["sections"] if item["id"] == "shot")["content"] == snapshot["shot"]
    assert snapshot == original
    brief["sections"][0]["content"]["action"] = "A display edit cannot change canon."
    assert snapshot == original
    snapshot["request"]["seed"] += 1
    assert production_brief(snapshot)["briefHash"] != production_brief(original)["briefHash"]
    snapshot["resolvedContext"]["dialogueCues"] = [{"text": "bonjour", "language": "unsupported"}]
    with pytest.raises(ValueError, match="language"): assert_adaptable(snapshot)


def test_new_start_and_prepare_refuse_old_english_claim_without_manufacturing_checks(tmp_path):
    _storage, client, _service, _provider, project, view = batch_environment(tmp_path)
    with pytest.raises(ValidationError):
        BatchStart(expectedRevision=1, manifestHash=view["manifestHash"], basis="whole-batch-english.v1")
    with pytest.raises(InvalidTransitionError):
        assert_new_dispatch_authority({"provider": {"adapterId": "minimax_h3_gateway"}, "reviewedDirections": {"reviewedEnglish": True}})
    response = client.post(f"/api/v2/projects/{project}/video-jobs", json={
        "approvalId": "a", "shotId": "s", "storyboardRevision": 1, "expectedSelectionRevision": 1,
        "idempotencyKey": "old-contract", "reviewedDirections": {"sourceHash": "a"*64, "fields": [], "reviewedEnglish": True}})
    assert response.status_code == 422


def test_project_language_report_is_deterministic_from_frozen_inputs(tmp_path):
    _storage, _client, service, _provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    request = request_for(ready)
    result = fidelity_for(request)
    chinese = render_report(request, result)
    assert b'lang="zh"' in chinese
    payload = request.model_dump(mode="json", by_alias=True)
    import json
    reordered = CreativeHandoffRequest.model_validate_json(json.dumps(payload, sort_keys=True))
    assert render_report(reordered, result) == chinese
    english_payload = deepcopy(payload)
    english_payload["inputArtifacts"]["language-contract.json"] = {**payload["inputArtifacts"]["language-contract.json"], "contentLocale": "en-US", "reportLocale": "en"}
    for target in english_payload["inputArtifacts"]["video-targets.json"]["targets"]:
        target["snapshot"]["languageContract"] = english_payload["inputArtifacts"]["language-contract.json"]
        # Source edits always invalidate the previous candidate and check.
    english = CreativeHandoffRequest.model_validate(english_payload)
    with pytest.raises(ValueError): render_report(english, result)


def test_scoped_single_request_preserves_exact_seed_duration_and_visible_settings(tmp_path):
    storage, client, service, provider, project, old = batch_environment(tmp_path)
    service.control(project, BatchControl(batchId=old["id"], expectedControlRevision=old["controlRevision"], action="cancel"))
    target = old["manifest"]["targets"][0]
    args = target["args"]
    body = {"approvalId": args["approval_id"], "shotId": args["shot_id"], "storyboardRevision": args["storyboard_revision"],
        "expectedSelectionRevision": args["expected_selection_revision"], "idempotencyKey": "single-source", "seed": 177,
        "requestedDurationSeconds": 8, "aspectPolicy": "reject_mismatch", "playbackIntent": "segment_required"}
    view = service.setup(project, BatchSetup(profileId=old["manifest"]["setup"]["profileId"], shotIds=[args["shot_id"]], singleRequest=body))
    assert not view["manifest"]["blockers"], view["manifest"]["blockers"]
    frozen, = view["manifest"]["targets"]
    assert frozen["snapshot"]["request"]["seed"] == 177
    assert frozen["snapshot"]["request"]["durationSeconds"] == 8
    assert frozen["snapshot"]["playbackIntent"] == "segment_required"
    assert len(view["manifest"]["scopeShotIds"]) == 1 and not provider.submits
    ready = ready_batch(service, project, view)
    start_batch(service, project, ready)
    package = service.current(project)["authorizedDirections"][body["shotId"]]
    endpoint = f"/api/v2/projects/{project}/video-jobs"
    wrong = client.post(endpoint, json=body | {"idempotencyKey": "extra-unapproved-job", "reviewedDirections": package})
    assert wrong.status_code == 409
    prepared = client.post(endpoint, json=body | {"reviewedDirections": package})
    assert prepared.status_code == 201, prepared.text
    repeated = client.post(endpoint, json=body | {"reviewedDirections": package})
    assert repeated.status_code == 201 and repeated.json()["id"] == prepared.json()["id"]
    assert service.current(project)["execution"]["jobs"][body["shotId"]] == prepared.json()["id"]
    service.step(project)
    assert len(provider.submits) == 1, service.current(project)["execution"].get("error")
    with closing(storage.projects.open(project)) as store:
        assert len(service.video.jobs(store)) == 1


def test_project_language_edit_invalidates_checked_source_without_rewriting_evidence(tmp_path):
    storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    check = deepcopy(ready["execution"]["fidelity"])
    with closing(storage.projects.open(project)) as store:
        current = store.project()
        store.update_brief(current.brief.model_copy(update={"language": "en-US"}), expected_revision=current.revision)
    with pytest.raises(InvalidTransitionError):
        start_batch(service, project, ready)
    assert service.current(project)["execution"]["fidelity"] == check
    assert not provider.submits


def test_short_english_dialogue_is_not_a_lexical_ban_on_physical_direction():
    from plotloom.language_policy import language_contract
    from plotloom.video_backends.minimax_h3.prompt import compile_i2va_prompt
    from tests.test_h3_i2va_prompt import _review, _snapshot
    snapshot = _snapshot()
    snapshot["languageContract"] = language_contract("en-US")
    snapshot["shot"]["audioPlan"]["events"][0].update({"startOffsetUnits": 0, "durationUnits": 5000})
    snapshot["resolvedContext"]["dialogueCues"][0].update({"text": "I", "language": "en-US"})
    prompt = compile_i2va_prompt(snapshot, _review(snapshot), draft=True)
    assert "Push In" in prompt and prompt.count("<d>[English] I</d>") == 1
    # Structural compilation never grants semantic fidelity or generation consent.
    assert "fidelityCheck" not in _review(snapshot)
