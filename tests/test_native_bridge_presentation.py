"""Fake sends and disposable projects qualify advice, never creative acceptance."""
import json
import subprocess
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.creative_handoff_identity import canonical_json
from plotloom.exceptions import InvalidTransitionError
from plotloom.image_job_contracts import ImageJobError
from plotloom.native_bridge_intent_service import NativeBridgeIntentService
from plotloom.native_bridge_presentation_contract import native_presentation_suggestions, render_native_presentation_report
from plotloom.native_bridge_presentation_service import NativeBridgePresentationService
from plotloom.production_bridge_contracts import ProductionBridgeIntentUpdateRequest
from tests.native_bridge_runtime_fixtures import create_native_presentation_runtime


@pytest.fixture
def presentation(tmp_path, monkeypatch):
    return create_native_presentation_runtime(tmp_path, monkeypatch)


@pytest.fixture
def seeded_presentation(tmp_path, monkeypatch, pending_native_bridge_seed):
    return create_native_presentation_runtime(tmp_path, monkeypatch, pending_native_bridge_seed)


def candidate_for(request):
    return {"entries": [{"id": source["id"], "spans": [{"start": 0, "end": len(source["sourceText"]),
        "role": "dialogue" if source["kind"] == "dialogue" else "physical",
        "rendering": "" if source["kind"] == "dialogue" else source["sourceText"], "reason": ""}]}
        for source in request.input_artifacts["presentation-source.json"]["sources"]]}


def deliver(fixture, *, mutate_candidate=None, mutate_manifest=None, different_report=False, partial=False):
    storage, project, _proposal, service, job, _calls = fixture
    with closing(storage.projects.open(project)) as store:
        request, _ = service._request(store, project, job)
        paths = store.creative_handoff_exchange().verified_package_paths(request, store.creative_handoff_execution_pin(request))
    value = candidate_for(request)
    report = render_native_presentation_report(request, value)
    if mutate_candidate:
        mutate_candidate(value)
    if different_report:
        report = b"<!doctype html><html>not the derived report</html>"
    output = Path(paths["deliveryPath"]); output.mkdir()
    encoded = canonical_json(value)
    (output / "presentation.json").write_bytes(encoded)
    if partial:
        return request, output
    (output / "report.html").write_bytes(report)
    manifest = json.loads((Path(paths["packagePath"]) / "completion-manifest.example.json").read_text())
    manifest["deliveryId"] = "fake-presentation-delivery"
    manifest["candidate"]["sha256"], manifest["report"]["sha256"] = sha256(encoded).hexdigest(), sha256(report).hexdigest()
    manifest["executorProvenance"]["codeRevision"] = manifest["executorProvenance"]["upstreamRevision"]
    if mutate_manifest:
        mutate_manifest(manifest)
    (output / "completion.json").write_bytes(canonical_json(manifest))
    return request, output


def test_delivery_prefills_advice_without_changing_proposal_then_explicit_save(presentation):
    storage, project, before, service, job, calls = presentation
    assert calls == []
    service.send(project, job)
    with pytest.raises(InvalidTransitionError):
        service.send(project, job)
    request, output = deliver(presentation)
    assert service.check(project, job)["candidateStatus"] == "ready"
    assert not service.registry.view()["busy"]
    with closing(storage.projects.open(project)) as store:
        state = store.production_bridge_state()
        assert state.proposal == before and state.intent_job is None
        assert state.presentation_job.id == job and state.presentation_candidate.job_id == job
        assert state.presentation_candidate.source_hash == before.presentation.source_hash
        assert not state.proposal.presentation.reviewed and not state.proposal.installable
        assert state.presentation_candidate.entries[0].spans[0].rendering == before.presentation.sources[0].source_text
    app = create_project_folder_authoring_app(storage)
    with TestClient(app) as client:
        base = f"/api/v2/projects/{project}/production-bridge"
        state = client.get(base).json()
        assert state["nativePresentationGeneration"]["status"] == "available"
        report = client.get(f"{base}/native-presentation-jobs/{job}/report")
        assert report.content == service.report(project, job)
        assert "sandbox" in report.headers["content-security-policy"]
        assert client.post(base + "/accept", json={"expectedProposalRevision": before.revision, "expectedContentHash": before.content_hash}).status_code >= 400
        saved = client.put(base + "/proposals/presentation", json={"expectedProposalRevision": before.revision,
            "expectedContentHash": before.content_hash, "sourceHash": before.presentation.source_hash,
            "reviewedComplete": True, "entries": state["presentationCandidate"]["entries"]})
        assert saved.status_code == 200, saved.text
        current = saved.json()
        assert current["proposal"]["revision"] == before.revision + 1
        assert current["proposal"]["presentation"]["reviewed"]
        assert current["proposal"]["intentPackage"] == before.intent_package.model_dump(mode="json", by_alias=True)
        assert current["installation"] is None and current["presentationCandidate"] is None
        assert current["presentationJob"]["status"] == "stale"
        assert client.get(f"{base}/native-presentation-jobs/{job}/report").content == report.content
    with closing(storage.projects.open(project)) as reopened:
        persisted = reopened.production_bridge_state()
        assert persisted.proposal.presentation.model_dump(mode="json", by_alias=True) == current["proposal"]["presentation"]
        assert persisted.proposal.presentation.reviewed and persisted.presentation_candidate is None
        assert persisted.installation is None
    validated = subprocess.run(["uv", "run", "--locked", "python", "scripts/native_bridge_presentation.py", "validate",
        str(output / "presentation.json"), "--request", str(output.parent / "package" / "request.json")], capture_output=True, check=True)
    assert b"validated" in validated.stdout
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["cancel", "proposal", "source", "target"])
def test_late_delivery_preserves_saved_content_and_report(presentation, change):
    storage, project, before, service, job, _calls = presentation
    service.send(project, job)
    if change == "cancel":
        service.cancel(project, job)
        assert service.registry.view()["busy"]
        with pytest.raises(InvalidTransitionError):
            NativeBridgeIntentService(storage, service.registry).create(project, expected_revision=before.revision, expected_hash=before.content_hash)
    else:
        with closing(storage.projects.open(project)) as store:
            if change == "proposal":
                store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
                    expected_proposal_revision=before.revision, expected_content_hash=before.content_hash,
                    entries=[{"id": entry.id, "text": "更新后的作者意图"} for entry in before.intent_package.entries]))
            elif change == "source":
                current = store.project()
                store.update_brief(current.brief.model_copy(update={"target_playthrough_seconds": current.brief.target_playthrough_seconds + 1}), expected_revision=current.revision)
            else:
                from sqlalchemy import select
                from plotloom.stage_contracts import StageName
                from plotloom.persistence.schema import StageHeadRow
                with store.repository._write() as session:
                    head = session.scalar(select(StageHeadRow).where(StageHeadRow.project_id == project, StageHeadRow.stage == StageName.STORY_GRAPH.value))
                    head.revision += 1
            before = store.production_bridge_state().proposal
    deliver(presentation)
    assert service.check(project, job)["candidateStatus"] == ("cancelled" if change == "cancel" else "stale")
    with closing(storage.projects.open(project)) as store:
        state = store.production_bridge_state()
        assert state.proposal == before and state.presentation_candidate is None and state.installation is None
    assert not service.registry.view()["busy"]
    assert "待作者确认" in service.report(project, job).decode()


@pytest.mark.parametrize("invalid", ["omitted", "duplicate", "gap", "unassigned", "extra", "rewrite", "rendering", "reason"])
def test_complete_span_binder_rejects_invalid_candidate(seeded_presentation, invalid):
    presentation = seeded_presentation
    storage, project, before, service, job, _ = presentation
    with closing(storage.projects.open(project)) as store:
        request, _ = service._request(store, project, job)
    value = candidate_for(request)
    if invalid == "omitted": value["entries"].pop()
    elif invalid == "duplicate": value["entries"].append(deepcopy(value["entries"][0]))
    elif invalid == "extra": value["entries"][0]["sourceText"] = "rewrite"
    else:
        span = value["entries"][0]["spans"][0]
        if invalid == "gap": span["start"] = 1
        elif invalid == "unassigned": span["role"] = "unassigned"
        elif invalid == "rewrite": span["role"] = "visible_text"
        elif invalid == "rendering": span["rendering"] = " "
        else: span.update(role="review_only", rendering="", reason="")
    with pytest.raises(ValueError): native_presentation_suggestions(request, value)
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().proposal == before


@pytest.mark.parametrize("invalid", ["partial", "candidate", "report", "pin", "hash"])
def test_invalid_delivery_cannot_release_reservation(seeded_presentation, invalid):
    presentation = seeded_presentation
    _storage, project, _before, service, job, _ = presentation
    service.send(project, job)
    deliver(presentation, partial=invalid == "partial", different_report=invalid == "report",
        mutate_candidate=(lambda value: value["entries"].pop()) if invalid == "candidate" else None,
        mutate_manifest=(lambda manifest: manifest["executorProvenance"].update(codeRevision="0" * 40)) if invalid == "pin"
            else (lambda manifest: manifest["candidate"].update(sha256="0" * 64)) if invalid == "hash" else None)
    if invalid == "partial": assert service.check(project, job)["candidateStatus"] == "dispatched"
    else:
        with pytest.raises(CreativeHandoffError): service.check(project, job)
    assert service.registry.view()["busy"]


def test_unknown_send_and_reopen_never_resends(presentation, monkeypatch):
    storage, project, before, service, job, calls = presentation
    real_run = subprocess.run
    def lost(command, **kwargs):
        if len(command) > 1 and command[1] == "queue":
            calls.append(command)
            return subprocess.CompletedProcess(command, 1, "lost acknowledgment")
        return real_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", lost)
    with pytest.raises(ImageJobError): service.send(project, job)
    reopened = NativeBridgePresentationService(storage, service.registry)
    assert reopened.check(project, job)["candidateStatus"] == "outcome_unknown"
    with pytest.raises(InvalidTransitionError): reopened.send(project, job)
    deliver(presentation)
    assert reopened.check(project, job)["candidateStatus"] == "ready"
    assert len(calls) == 1
    with closing(storage.projects.open(project)) as store:
        assert store.production_bridge_state().proposal == before


def test_send_pin_mismatch_preserves_frozen_job(presentation, monkeypatch):
    storage, project, before, service, job, calls = presentation
    with closing(storage.projects.open(project)) as store:
        request, data = service._request(store, project, job)
        pin = store.creative_handoff_execution_pin(request)
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: pin | {"upstreamRevision": "0" * 40})
    with pytest.raises(CreativeHandoffError, match="冻结任务"): service.send(project, job)
    assert calls == [] and not service.registry.view()["busy"]
    with closing(storage.projects.open(project)) as store:
        assert service._request(store, project, job)[1] == data
        assert store.production_bridge_state().proposal == before


def test_mixed_roles_preserve_literal_text_choices_and_unicode_without_approval():
    from plotloom.creative_handoff_contracts import CreativeHandoffRequest
    from plotloom.production_presentation import prepare_presentation
    from tests.production_presentation_fixtures import _package, _updates
    evidence = _package().frozen_evidence
    evidence["script"]["episodes"][0]["scenes"][0]["flow"][0]["action"] = "停🙂步。抬眼。"
    package = prepare_presentation(inputs=evidence["inputs"], script=evidence["script"],
        storyboard=evidence["storyboard"], mapping=evidence["sectionMap"])
    request = CreativeHandoffRequest(job_id="ch_" + "p" * 32, project_id="project", section_id="production-bridge",
        stage="bridge-presentation", expected_stage_revision=3, source={"proposal": {"revision": 3, "contentHash": "a" * 64}},
        input_artifacts={"presentation-source.json": package.model_dump(mode="json", by_alias=True)}, creative_brief="Frozen mixed source")
    entries = _updates(package)
    for entry in entries:
        entry["spans"] = [{"rendering": "", "reason": "", **span} for span in entry["spans"]]
    advice = native_presentation_suggestions(request, {"entries": entries})
    assert {span.role for entry in advice.entries for span in entry.spans} == {"physical", "visible_text", "runtime_choice", "review_only", "dialogue"}
    literal = package.sources[2]
    visible = advice.entries[2].spans[1]
    assert literal.source_text[visible.start:visible.end] == "今晚不去了，明天见。"
    assert advice.entries[0].spans[0].end == len("停🙂步。抬眼。")
    assert not package.reviewed and all(not source.spans for source in package.sources)
    assert package.runtime_choice["choices"][0]["prompt"] == "怎么办？"


def test_frozen_presentation_state_and_report_are_pure_reads(presentation):
    from tests.working_input_preservation import preservation_inventory
    storage, project, before, service, job, calls = presentation
    service.send(project, job)
    deliver(presentation)
    service.check(project, job)
    storage.projects.close_project(project)
    before_rows = preservation_inventory(storage.projects.outputs_root)
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        before_app = preservation_inventory(storage.application.root)
        base = f"/api/v2/projects/{project}/production-bridge"
        state = client.get(base)
        assert state.status_code == 200, state.text
        assert state.json()["presentationJob"]["status"] == "ready"
        assert client.get(f"{base}/native-presentation-jobs/{job}/report").content == service.report(project, job)
        assert client.post(f"{base}/native-presentation-jobs/{job}/check").status_code == 409
        assert preservation_inventory(storage.application.root) == before_app
    assert preservation_inventory(storage.projects.outputs_root) == before_rows
    assert len(calls) == 1
