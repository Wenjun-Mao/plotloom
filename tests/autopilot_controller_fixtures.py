"""Finite fake native packages; every source gate remains the real owner."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from plotloom.autopilot_contracts import LaunchRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_commands import CREATIVE_METHODS
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json, request_hash
from plotloom.native_bridge_intent_contract import render_native_intent_report
from plotloom.native_bridge_presentation_contract import render_native_presentation_report
from plotloom.project_storage import ProjectFolderStorage
from tests.cast_style_fixtures import style_fixture
from tests.creative_delivery_fixtures import _pilot_script
from tests.production_bridge_fixtures import _source_shaped_review_board
from tests.test_creator_branch_suggestions import proposal
from tests.test_native_bridge_presentation import candidate_for
from tests.test_specialist_settings import configured

FIXTURES = Path(__file__).resolve().parents[1] / "frontend/e2e/fixtures/f5a"
PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}


def candidate(store, request):
    stage = request.stage
    if stage == "outline":
        return {"source": request.source["title"], "params": {"episodes": 1}, "episodes": []}
    if stage == "branches":
        return proposal(request.source["topology"])
    if stage == "characters":
        return style_fixture(json.loads((FIXTURES / "cast.json").read_text()), request.input_artifacts["cast-style-contract.json"])
    if stage == "art":
        value = json.loads((FIXTURES / "art.json").read_text())
        value["sectionUsage"] = [{"sectionId": item["sectionId"], "sceneIds": ["S01"], "propIds": []}
            for item in request.input_artifacts["section-map.json"]["sections"]]
        return value
    if stage == "script":
        binding = store.script_state().candidate.binding
        value = _pilot_script()
        value["sectionBindings"] = [item.model_dump(mode="json", by_alias=True) for item in binding.section_bindings]
        template = value["episodes"][0]
        template["scenes"][0]["characters"] = ["keeper"]
        value["episodes"] = [dict(deepcopy(template), ep=item.episode) for item in binding.section_bindings]
        return value
    if stage == "storyboard":
        binding = store.storyboard_review_state().candidate.binding
        value = _source_shaped_review_board(episodes=[item.episode for item in binding.section_bindings])
        for episode in value["episodes"]:
            for segment in episode["segments"]:
                for cut in segment["cuts"]:
                    cut["characters"] = ["keeper"]
        return value
    if stage == "bridge-intent":
        return {"entries": [{"id": entry["id"], "suggestedText": "让角色面对不可撤回的选择，并使这一行动改变他人的下一步。"}
            for entry in request.input_artifacts["targets.json"]["entries"]]}
    return candidate_for(request)


def deliver(store, request, value=None):
    value = value if value is not None else candidate(store, request)
    pin = store.creative_handoff_execution_pin(request)
    paths = store.creative_handoff_exchange().write_package(request, pin)
    root = Path(paths["deliveryPath"])
    root.mkdir()
    filename = CreativeHandoffExchange._candidate_filename(request.stage)
    content = canonical_json(value)
    report = (render_native_intent_report(request, value) if request.stage == "bridge-intent" else
        render_native_presentation_report(request, value) if request.stage == "bridge-presentation" else
        b"<!doctype html><html><body>Deterministic fake native evidence; no human creative acceptance.</body></html>")
    (root / filename).write_bytes(content)
    (root / "report.html").write_bytes(report)
    manifest = {"schemaVersion": 1, "jobId": request.job_id, "requestHash": request_hash(request),
        "deliveryId": "autopilot-fixture-" + request.stage, "stage": request.stage,
        "candidate": {"filename": filename, "sha256": sha256(content).hexdigest()},
        "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()},
        "executorProvenance": {"codeRevision": PIN["upstreamRevision"],
            "skillVersion": f"plotloom-{request.stage.removeprefix('bridge-')}-specialist.v1" if request.stage.startswith("bridge-") else "fixture",
            "skillHash": pin["specialistSkillHash"], "upstreamRevision": pin["upstreamRevision"],
            "upstreamSkillHash": pin["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"},
        "limitations": ["Deterministic fake delivery, not real generation or product acceptance."]}
    (root / "completion.json").write_bytes(canonical_json(manifest))


def environment(tmp_path, monkeypatch, *, auto_deliver=True, brief=None):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    selected = brief or FIXED_CHINESE_BRIEF.model_copy(update={
        "decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0})
    with closing(storage.projects.create(selected)) as store:
        project_id = store.manifest.project_id
    registry, _settings = configured(storage.application.root)
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: PIN)
    calls, original_run = [], subprocess.run
    def queue(command, **kwargs):
        if len(command) > 1 and command[1] == "queue":
            job = re.search(r"ch_[a-z0-9]{32}", command[-1]).group()
            calls.append(job)
            if auto_deliver:
                with closing(storage.projects.open(project_id)) as store:
                    checkpoint = next(item for item in store.repository.autopilot.current(project_id).checkpoints if item["evidence"]["jobId"] == job)
                    stage = checkpoint["evidence"]["owner"]
                    request = (service.controller.bridge_services[stage]._request(store, project_id, job)[0]
                        if stage in service.controller.bridge_services else getattr(store, CREATIVE_METHODS[stage][1])(job))
                    deliver(store, request)
            return subprocess.CompletedProcess(command, 0, "queued")
        return original_run(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", queue)
    service = AutopilotService(storage, registry)
    request = LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic")
    view = service.launch(project_id, request)
    return storage, registry, service, view, calls


def run_text(service, view, *, steps=40):
    assert service.acquire_controller()
    for _ in range(steps):
        service.step(view.project_id)
        with closing(service.storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
        if any(item["operationKey"] == "installation" for item in current.checkpoints):
            return current
        assert current.state in {"running", "waiting"}, current.blocker
    raise AssertionError("bounded fake text path did not reach installation")
