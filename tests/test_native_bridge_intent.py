"""Software contract checks use fake native sends, never a real specialist."""
import json
import subprocess
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from plotloom.exceptions import InvalidTransitionError
from plotloom.image_job_contracts import ImageJobError
from plotloom.native_bridge_intent_contract import render_native_intent_report
from plotloom.native_bridge_intent_service import NativeBridgeIntentService
from plotloom.pipeline import RunSecretBroker
from plotloom.production_bridge_contracts import ProductionBridgeIntentUpdateRequest
from plotloom.production_bridge_intent_service import ProductionBridgeIntentService
from tests.production_bridge_intent_fixtures import (
    FakeAdapter,
    FakeResolver,
    _pending_project,
)
from tests.test_specialist_settings import configured


@pytest.fixture
def native(tmp_path, monkeypatch):
    storage, project_id, revision, digest = _pending_project(tmp_path)
    registry, _settings = configured(storage.application.root)
    service = NativeBridgeIntentService(storage, registry)
    checkout = Path(__file__).resolve().parents[1]
    pin = {
        "upstreamRevision": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "upstreamSkillHash": sha256((checkout / "docs/creative-workflow/native-bridge-intent.md").read_bytes()).hexdigest(),
        "specialistSkillHash": sha256((checkout / ".agents/skills/plotloom-intent-specialist/SKILL.md").read_bytes()).hexdigest(),
    }
    # Tests are authored before the checkpoint commit. This explicit fake pin
    # seam qualifies state/binding mechanics, not real native source execution.
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, stage: pin if stage == "bridge-intent" else pytest.fail("unexpected stage"))
    calls = []
    real_run = subprocess.run

    def send(command, **kwargs):
        if len(command) > 1 and command[1] == "queue":
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "queued")
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", send)
    job = service.create(project_id, expected_revision=revision, expected_hash=digest)
    return storage, project_id, revision, digest, service, job, calls


def deliver(native, *, candidate=None, mutation=None, partial=False):
    storage, project, _revision, _digest, service, job, _calls = native
    with closing(storage.projects.open(project)) as store:
        request, _data = service._request(store, project, job)
        paths = store.creative_handoff_exchange().verified_package_paths(request, store.creative_handoff_execution_pin(request))
    output = Path(paths["deliveryPath"])
    output.mkdir()
    targets = request.input_artifacts["targets.json"]["entries"]
    value = candidate or {"entries": [{"id": entry["id"], "suggestedText": f"推动角色直面本场矛盾，建立第 {index + 1} 项选择的压力。"} for index, entry in enumerate(targets)]}
    candidate_bytes = canonical_json(value)
    report = render_native_intent_report(request, value) if candidate is None else b"<!doctype html><html>invalid candidate fixture</html>"
    (output / "intent.json").write_bytes(candidate_bytes)
    if partial:
        return request, output
    (output / "report.html").write_bytes(report)
    manifest = json.loads((Path(paths["packagePath"]) / "completion-manifest.example.json").read_text())
    manifest["deliveryId"] = "fake-software-delivery"
    manifest["candidate"]["sha256"] = sha256(candidate_bytes).hexdigest()
    manifest["report"]["sha256"] = sha256(report).hexdigest()
    manifest["executorProvenance"]["codeRevision"] = manifest["executorProvenance"]["upstreamRevision"]
    if mutation:
        mutation(manifest)
    (output / "completion.json").write_bytes(canonical_json(manifest))
    return request, output


def test_prepare_send_validated_delivery_requires_explicit_whole_package_review(native):
    storage, project, revision, digest, service, job, calls = native
    assert calls == []
    with closing(storage.projects.open(project)) as store:
        before = store.production_bridge_state()
        request, _ = service._request(store, project, job)
        assert request.source["proposal"]["contentHash"] == digest
        assert request.source["proposal"]["replacementTarget"] == before.proposal.replacement_target.model_dump(mode="json", by_alias=True)
        assert before.intent_job.transport == "codex_native" and before.intent_job.profile_id is None
        assert before.proposal.revision == revision
    service.send(project, job)
    assert len(calls) == 1 and "exact execution checkout" in calls[0][-1]
    assert service.registry.view()["busy"]
    with pytest.raises(InvalidTransitionError):
        service.send(project, job)
    request, output = deliver(native)
    checkout = Path(__file__).resolve().parents[1]
    request_path = output.parent / "package" / "request.json"
    validated = subprocess.run(["uv", "run", "--locked", "python", "scripts/native_bridge_intent.py", "validate", str(output / "intent.json"), "--request", str(request_path)], cwd=checkout, capture_output=True, check=True)
    assert b"validated" in validated.stdout
    rendered = subprocess.run(["uv", "run", "--locked", "python", "scripts/native_bridge_intent.py", "render", str(output / "intent.json"), "--request", str(request_path)], cwd=checkout, capture_output=True, check=True)
    assert rendered.stdout == (output / "report.html").read_bytes()
    assert service.check(project, job)["candidateStatus"] == "ready"
    assert not service.registry.view()["busy"]
    with closing(storage.projects.open(project)) as store:
        state = store.production_bridge_state()
        proposal = state.proposal
        assert proposal.revision == revision + 1
        assert proposal.intent_package.suggestion_origin == "codex_native.v1"
        assert proposal.intent_package.review_state == "model_suggested"
        assert not proposal.installable and state.installation is None
        assert proposal.inputs == request.source["proposal"]["inputs"]
        assert "profileId" not in proposal.intent_package.provenance
        saved = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
            expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
            entries=[{"id": entry.id, "text": entry.text} for entry in proposal.intent_package.entries],
        ))
        assert saved.proposal.intent_package.review_state == "author_saved"
        saved_revision = saved.proposal.revision
    service.check(project, job)
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().proposal.revision == saved_revision
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["cancel", "proposal", "source", "target"])
def test_cancelled_or_changed_authority_contains_late_delivery(native, change):
    storage, project, revision, digest, service, job, _calls = native
    service.send(project, job)
    if change == "cancel":
        service.cancel(project, job)
        assert service.registry.view()["busy"]
        with pytest.raises(InvalidTransitionError):
            service.create(project, expected_revision=revision, expected_hash=digest)
        with closing(storage.projects.open(project)) as store:
            assert store.production_bridge_state().preparation.status == "unavailable"
    else:
        with closing(storage.projects.open(project)) as store:
            if change == "proposal":
                proposal = store.production_bridge_state().proposal
                store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
                    expected_proposal_revision=revision, expected_content_hash=digest,
                    entries=[{"id": entry.id, "text": "作者自己的意图"} for entry in proposal.intent_package.entries],
                ))
            elif change == "source":
                state = store.project()
                store.update_brief(state.brief.model_copy(update={"target_playthrough_seconds": state.brief.target_playthrough_seconds + 1}), expected_revision=state.revision)
            else:
                # A changed canonical replacement target is distinct from source.
                from sqlalchemy import select

                from plotloom.domain import StageName
                from plotloom.persistence.schema import StageHeadRow
                with store.repository._write() as session:
                    head = session.scalar(select(StageHeadRow).where(StageHeadRow.project_id == project, StageHeadRow.stage == StageName.STORY_GRAPH.value))
                    head.revision += 1
            before = store.production_bridge_state().proposal
            revision, digest = before.revision, before.content_hash
    deliver(native)
    outcome = service.check(project, job)
    assert outcome["candidateStatus"] == ("cancelled" if change == "cancel" else "stale")
    assert not service.registry.view()["busy"]
    with closing(storage.projects.open(project)) as store:
        state = store.production_bridge_state()
        assert state.proposal.revision == revision and state.proposal.content_hash == digest
        assert state.installation is None
    assert "Codex" in service.report(project, job).decode()


@pytest.mark.parametrize("field", ["jobId", "requestHash", "stage", "execution", "hash"])
def test_wrong_delivery_identity_or_pin_preserves_reservation(native, field):
    _storage, project, _revision, _digest, service, job, _calls = native
    service.send(project, job)

    def mutation(manifest):
        if field == "execution":
            manifest["executorProvenance"]["codeRevision"] = "a" * 40
        elif field == "hash":
            manifest["candidate"]["sha256"] = "0" * 64
        else:
            manifest[field] = {"jobId": "ch_" + "z" * 32, "requestHash": "0" * 64, "stage": "script"}[field]
    deliver(native, mutation=mutation)
    with pytest.raises(CreativeHandoffError):
        service.check(project, job)
    assert service.registry.view()["busy"]


def test_partial_delivery_and_extra_suggestion_cannot_admit(native):
    storage, project, revision, _digest, service, job, _calls = native
    service.send(project, job)
    _request, output = deliver(native, partial=True)
    assert service.check(project, job)["candidateStatus"] == "dispatched"
    assert service.registry.view()["busy"]
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().proposal.revision == revision


def test_unknown_send_reopens_same_job_without_resending_or_api_reconciliation(native, monkeypatch):
    storage, project, revision, _digest, service, job, calls = native
    prior_run = subprocess.run
    def lost_send(command, **kwargs):
        if len(command) > 1 and command[1] == "queue":
            calls.append(command)
            return subprocess.CompletedProcess(command, 1, "lost acknowledgment")
        return prior_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", lost_send)
    with pytest.raises(ImageJobError):
        service.send(project, job)
    restarted = NativeBridgeIntentService(storage, service.registry)
    assert restarted.status(project, job)["state"] == "outcome_unknown"
    assert restarted.check(project, job)["candidateStatus"] == "outcome_unknown"
    with pytest.raises(InvalidTransitionError):
        restarted.send(project, job)
    adapter = FakeAdapter()
    api = ProductionBridgeIntentService(storage, resolver=FakeResolver(adapter), secrets=RunSecretBroker())
    try:
        api.inspect(project)
        with pytest.raises(InvalidTransitionError):
            api.submit(project, job)
        with closing(storage.projects.open(project)) as store:
            assert store.production_bridge_state().intent_job.status == "outcome_unknown"
            assert store.production_bridge_state().proposal.revision == revision
    finally:
        api.close()
    deliver(native)
    assert restarted.check(project, job)["candidateStatus"] == "ready"
    assert restarted.report(project, job) == service.report(project, job)
    assert len(calls) == 1 and adapter.calls == 0


def test_suggestions_only_complete_binder_and_deterministic_report(native):
    from plotloom.native_bridge_intent_contract import native_intent_suggestions
    storage, project, _revision, _digest, service, job, _calls = native
    with closing(storage.projects.open(project)) as store:
        request, _data = service._request(store, project, job)
    targets = request.input_artifacts["targets.json"]["entries"]
    complete = {"entries": [{"id": entry["id"], "suggestedText": "推进角色争取信任"} for entry in targets]}
    for candidate in (
        {"entries": complete["entries"][:-1]},
        {"entries": [complete["entries"][0], *complete["entries"]]},
        {"entries": [*complete["entries"], {"id": "unknown", "suggestedText": "非法目标"}]},
        {"entries": [{**entry, "sourceContentHash": "0" * 64} for entry in complete["entries"]]},
        {"entries": [{**entry, "suggestedText": " "} for entry in complete["entries"]]},
        {"entries": [{"id": entry["id"], "suggestedText": entry["sourceExcerpt"]} for entry in targets]},
    ):
        with pytest.raises(ValueError):
            native_intent_suggestions(request, candidate)
    assert len(native_intent_suggestions(request, complete)) == len(targets)
    service.send(project, job)
    _request, output = deliver(native)
    report = b"<!doctype html><html>different report</html>"
    (output / "report.html").write_bytes(report)
    manifest = json.loads((output / "completion.json").read_text())
    manifest["report"]["sha256"] = sha256(report).hexdigest()
    (output / "completion.json").write_bytes(canonical_json(manifest))
    with pytest.raises(CreativeHandoffError, match="deterministic"):
        service.check(project, job)
    assert service.registry.view()["busy"]


def test_native_execution_pin_refuses_uncommitted_source(monkeypatch):
    calls = []
    def dirty(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, " M src/plotloom/native_bridge_intent_contract.py\n")
    monkeypatch.setattr(subprocess, "run", dirty)
    with pytest.raises(CreativeHandoffError, match="committed"):
        CreativeHandoffExchange._pinned_execution("bridge-intent")
    assert len(calls) == 1 and "--porcelain" in calls[0]
    assert "scripts/native_bridge_intent.py" in calls[0]


@pytest.mark.parametrize("change", ["upstreamRevision", "upstreamSkillHash", "specialistSkillHash", "dirty"])
def test_send_rechecks_clean_frozen_execution_before_any_dispatch(native, monkeypatch, change):
    storage, project, _revision, _digest, service, job, calls = native
    with closing(storage.projects.open(project)) as store:
        request, frozen_job = service._request(store, project, job)
        frozen_pin = store.creative_handoff_execution_pin(request)
        paths = store.creative_handoff_exchange().verified_package_paths(request, frozen_pin)
    package = Path(paths["packagePath"])
    frozen_package = {path.relative_to(package): path.read_bytes() for path in package.rglob("*") if path.is_file()}
    frozen_registry = service.registry.path.read_bytes()
    if change == "dirty":
        prior_run = subprocess.run

        def dirty(command, **kwargs):
            if "--porcelain" in command:
                return subprocess.CompletedProcess(command, 0, " M scripts/native_bridge_intent.py\n")
            return prior_run(command, **kwargs)

        monkeypatch.setattr(subprocess, "run", dirty)
        monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin",
            lambda _self, stage: CreativeHandoffExchange._pinned_execution(stage))
    else:
        changed_pin = frozen_pin | {change: "0" * len(frozen_pin[change])}
        monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: changed_pin)
    with pytest.raises(CreativeHandoffError) as refused:
        service.send(project, job)
    assert refused.value.code == ("execution_pin_missing" if change == "dirty" else "execution_pin_mismatch")
    assert calls == []
    assert service.registry.path.read_bytes() == frozen_registry
    assert not service.registry.view()["busy"]
    assert service.registry.status(job) == {"state": "prepared"}
    assert not (service.registry.root / "dispatch").exists()
    assert not Path(paths["deliveryPath"]).exists()
    assert {path.relative_to(package): path.read_bytes() for path in package.rglob("*") if path.is_file()} == frozen_package
    with closing(storage.projects.open(project)) as store:
        assert service._request(store, project, job)[1] == frozen_job
        assert store.creative_handoff_execution_pin(request) == frozen_pin
        assert store.production_bridge_state().intent_job.status == "queued"
    # Restoring the original clean authority permits this exact request once;
    # refusal did not refresh its pin or manufacture a dispatch attempt.
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: frozen_pin)
    service.send(project, job)
    assert len(calls) == 1 and service.registry.view()["busy"]
    with pytest.raises(InvalidTransitionError):
        service.send(project, job)
    assert len(calls) == 1


def test_bounded_context_refuses_before_any_new_job(native, monkeypatch):
    storage, project, revision, digest, service, job, calls = native
    service.cancel(project, job)
    monkeypatch.setattr("plotloom.native_bridge_intent_service.MAX_INTENT_CONTEXT_CHARACTERS", 1)
    with pytest.raises(InvalidTransitionError, match="bounded"):
        service.create(project, expected_revision=revision, expected_hash=digest)
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().intent_job.id == job
    assert calls == []


def test_runtime_routes_configure_native_independently_and_reopen_inert_report(native):
    storage, project, revision, digest, service, job, calls = native
    app = create_project_folder_authoring_app(storage)
    with TestClient(app) as client:
        base = f"/api/v2/projects/{project}/production-bridge"
        state = client.get(base).json()
        assert state["intentGeneration"]["status"] == "unavailable"
        assert state["nativeIntentGeneration"]["status"] == "available"
        assert state["intentJob"]["profileId"] is None
        assert client.post(f"{base}/native-intent-jobs/{job}/send").status_code == 200
        deliver(native)
        checked = client.post(f"{base}/native-intent-jobs/{job}/check")
        assert checked.status_code == 200, checked.text
        assert checked.json()["intentJob"]["status"] == "ready"
        report = client.get(f"{base}/native-intent-jobs/{job}/report")
        assert report.status_code == 200 and report.content == service.report(project, job)
        assert "sandbox" in report.headers["content-security-policy"]
        assert report.headers["x-content-type-options"] == "nosniff"
        assert client.post(f"{base}/native-intent-jobs/{job}/send").status_code >= 400
    restarted = create_project_folder_authoring_app(storage)
    storage.projects.close_project(project)
    storage.projects.reopen_project(project)
    with TestClient(restarted) as client:
        assert client.get(base).json()["nativeIntentTask"]["reportAvailable"]
        assert client.get(f"{base}/native-intent-jobs/{job}/report").content == report.content
    assert len(calls) == 1


def test_unconfigured_runtime_never_calls_native_or_api(tmp_path):
    storage, project, revision, digest = _pending_project(tmp_path)
    app = create_project_folder_authoring_app(storage)
    with TestClient(app) as client:
        base = f"/api/v2/projects/{project}/production-bridge"
        assert client.get(base).json()["nativeIntentGeneration"] == {"status": "unavailable", "reason": "not_configured"}
        refused = client.post(base + "/native-intent-jobs", json={"expectedProposalRevision": revision, "expectedContentHash": digest})
        assert refused.status_code >= 400
        assert client.get(base).json()["intentJob"] is None
