"""Finite fake native packages; every source gate remains the real owner."""
import json
from contextlib import closing
from copy import deepcopy
from pathlib import Path

from plotloom.autopilot_contracts import POLICY_VERSION, LaunchRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.project_storage import ProjectFolderStorage
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.cast_style_fixtures import style_fixture
from tests.creative_delivery_fixtures import _pilot_script
from tests.production_bridge_fixtures import _source_shaped_review_board
from tests.test_creator_branch_suggestions import proposal
from tests.test_native_bridge_presentation import candidate_for
from tests.test_specialist_settings import configured

FIXTURES = Path(__file__).resolve().parents[1] / "frontend/e2e/fixtures/f5a"
PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
UPSTREAM_PIN = {"upstreamRevision": "d" * 40, "upstreamSkillHash": "e" * 64, "specialistSkillHash": "f" * 64}


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


def deliver(store, request, value=None, *, host=None):
    value = value if value is not None else candidate(store, request)
    run = store.repository.autopilot.current(request.project_id)
    if run.policy.version != POLICY_VERSION:
        raise AssertionError("fresh autopilot fixtures require the current Codex Exec launch policy")
    if host is None:
        raise AssertionError("Codex Exec delivery fixture requires its exact fake host")
    attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, request.stage)
    if attempt is None:
        raise AssertionError("Codex Exec delivery fixture requires its persisted project attempt")
    return host.complete(store, request, attempt, value=value)






def default_brief():
    return FIXED_CHINESE_BRIEF.model_copy(update={
        "decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0})


def runtime(storage, monkeypatch, *, auto_deliver=True):
    registry, _settings = configured(storage.application.root)
    from tests.codex_exec_fixtures import install_profile
    install_profile(registry)
    monkeypatch.setattr(
        CreativeHandoffExchange,
        "current_execution_pin",
        lambda _self, stage: PIN if stage in {"bridge-intent", "bridge-presentation", "video-directions"} else UPSTREAM_PIN,
    )
    host = FakeCodexExecHost(storage, registry, candidate_factory=lambda store, request: candidate(store, request), auto_deliver=auto_deliver)
    registry.codex_exec_admit = host.admit
    registry.codex_exec_status = host.status
    registry.codex_exec_cancel = host.cancel
    registry.codex_exec_suspend = host.suspend
    registry._codex_exec_test_host = host
    service = AutopilotService(storage, registry)
    return registry, service, host


def environment(tmp_path, monkeypatch, *, auto_deliver=True, brief=None, limits=None, early_references=False):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    selected = brief or default_brief()
    with closing(storage.projects.create(selected)) as store:
        project_id = store.manifest.project_id
    registry, service, host = runtime(storage, monkeypatch, auto_deliver=auto_deliver)
    request = LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic", **(limits or {}))
    # Existing focused owner tests freeze zero exploratory permission so their
    # exact image/late-delivery boundary remains isolated. Scheduler tests opt
    # into the actual production launch policy (four), including full packs.
    if early_references:
        view = service.launch(project_id, request)
    else:
        from plotloom import autopilot_service
        freeze = autopilot_service.freeze_launch_policy
        with monkeypatch.context() as launch:
            launch.setattr(autopilot_service, "freeze_launch_policy", lambda *args: freeze(*args).model_copy(update={"early_reference_limit": 0}))
            view = service.launch(project_id, request)
    return storage, registry, service, view, host.calls


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
