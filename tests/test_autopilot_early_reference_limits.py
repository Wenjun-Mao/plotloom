"""Frozen exploratory allowance, honest lower bounds and late complete inventory."""
import json
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from tests import autopilot_controller_fixtures
from tests.autopilot_controller_fixtures import environment


def current(storage, run):
    with closing(storage.projects.open(run.project_id)) as store:
        return store.repository.autopilot.current(run.project_id)


@pytest.mark.parametrize("limits", [{"max_images": 1}, {"max_jobs": 9}])
def test_known_impossible_lower_bound_refuses_early_images(tmp_path, monkeypatch, limits):
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, limits=limits, early_references=True)
    host = registry._codex_exec_test_host
    try:
        assert service.acquire_controller()
        for _ in range(40):
            service.step(run.project_id)
            view = current(storage, run)
            if view.state == "blocked":
                break
        else:
            raise AssertionError("known impossible scope did not stop")
        assert "已知必需参考" in view.blocker["message"]
        assert not host.image_calls
        assert not any(item["evidence"]["owner"] in {"image", "character-reference", "art-reference"} for item in view.checkpoints)
        assert view.bundle is None and view.handoff is None
    finally:
        service.close()


def test_late_complete_oversize_retains_early_candidates_and_stops_new_dispatch(tmp_path, monkeypatch):
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch,
        limits={"max_images": 12}, early_references=True)
    host = registry._codex_exec_test_host
    try:
        assert service.acquire_controller()
        for _ in range(80):
            service.step(run.project_id)
            view = current(storage, run)
            if view.state == "blocked":
                break
        else:
            raise AssertionError("complete inventory did not stop at its frozen ceiling")
        assert "完整素材包超过冻结" in view.blocker["message"]
        early = [item for item in view.checkpoints if item["evidence"]["result"].get("earlyReference")]
        assert early and all(item["state"] == "delivered" for item in early)
        assert 0 < len(host.image_calls) <= 4
        original_calls = list(host.image_calls)
        for _ in range(2):
            service.step(run.project_id)
        assert host.image_calls == original_calls
        with closing(storage.projects.open(run.project_id)) as store:
            for checkpoint in early:
                assert checkpoint["evidence"]["result"]["candidateAssetIds"]
            assert store.media.list_character_reference_decisions(run.project_id)["decisions"] == []
        assert view.bundle is None and view.handoff is None and not view.frames
    finally:
        service.close()


def test_two_initial_cast_subjects_reserve_early_opportunity_for_art_and_pause_keeps_identity(tmp_path, monkeypatch):
    candidate = autopilot_controller_fixtures.candidate
    prop = json.loads((Path(__file__).resolve().parents[1] / "third_party/shuohao-skills/skills/novel-art/examples/渡口-art.json").read_text())["props"][0]
    def richer_candidate(store, request):
        value = candidate(store, request)
        if request.stage == "characters":
            for index in range(1, 4):
                observer = deepcopy(value["characters"][0])
                observer.update(id=f"observer{index}", name=f"Observer {index}")
                value["characters"].append(observer)
        if request.stage == "art":
            value["props"] = [deepcopy(prop)]
            preset = request.input_artifacts["art-style-contract.json"]["preset"]["render"]
            value["props"][0]["image"]["prompt"] = preset + " " + value["props"][0]["image"]["prompt"]
        return value
    monkeypatch.setattr(autopilot_controller_fixtures, "candidate", richer_candidate)
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    host = registry._codex_exec_test_host
    try:
        assert service.acquire_controller()
        for _ in range(40):
            service.step(run.project_id)
            view = current(storage, run)
            early = [item for item in view.checkpoints if item["evidence"]["result"].get("earlyReference")]
            assert len(early) <= 4
            if len(early) == 4 and all(item["state"] == "delivered" for item in early):
                break
            assert view.state in {"running", "waiting"}, view.blocker
        else:
            raise AssertionError("bounded Cast/Art opportunity did not complete")
        assert not any(item["operationKey"] == "installation" for item in view.checkpoints)
        assert {item["operationKey"] for item in early} == {
            "character-reference:keeper", "character-reference:observer1",
            "art-reference:scene:S01", "art-reference:prop:P01",
        }
        identities = {item["operationKey"]: item["evidence"]["jobId"] for item in early}
        original_calls = list(host.image_calls)
        service.control(run.project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
        service.step(run.project_id)
        paused = current(storage, run)
        assert paused.state == "paused" and host.image_calls == original_calls
        assert {item["operationKey"]: item["evidence"]["jobId"] for item in paused.checkpoints
            if item["evidence"]["result"].get("earlyReference")} == identities
        assert all(item["state"] == "delivered" for item in paused.checkpoints if item["operationKey"] in identities)
        with closing(storage.projects.open(run.project_id)) as store:
            assert store.media.list_character_reference_decisions(run.project_id)["decisions"] == []
    finally:
        service.close()
