"""Real opted-in CLI steps on test-owned inputs; no provider or native generation."""
import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.codex_exec_validation import build_text_validation_plan, validation_plan_from_package
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.script_dialogue_compatibility import freeze_planned_storyboard_dialogue

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests/fixtures/script-dialogue"
PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}


def make_case(tmp_path, maximum=15):
    package, delivery, private = (tmp_path / name for name in ("package", "delivery", "private-validation"))
    for p in (package, delivery, private):
        p.mkdir()
    (package / "inputs").mkdir()
    artifacts = {name: json.loads((DATA / f"retained-{name.removesuffix('.json')}.json").read_bytes())
        for name in ("outline.json", "art.json", "cast.json")}
    admission = json.loads((DATA / "retained-admission.json").read_bytes())
    admission["plannedStoryboardDialogue"] = freeze_planned_storyboard_dialogue(
        max_cut_seconds=maximum, language="zh-CN").model_dump(mode="json", by_alias=True)
    artifacts["script-admission.json"] = admission
    request = CreativeHandoffRequest(job_id="ch_" + "a" * 32, project_id="synthetic-script",
        section_id="pilot-script", stage="script", expected_stage_revision=0,
        source={"kind": "test-owned retained inputs"}, input_artifacts=artifacts, creative_brief="provider-free receiver fixture")
    plan = build_text_validation_plan(request, execution_pin=PIN, source_revision="d" * 40)
    payload = request.model_dump(mode="json", by_alias=True) | dict(packageVersion=4, executorBackend="codex_exec",
        plotloomCodeRevision="d" * 40, executionPin=PIN, validationPlan=plan.model_dump(mode="json", by_alias=True), validationPlanHash=plan.plan_hash)
    (package / "request.json").write_text(json.dumps(payload, ensure_ascii=False))
    for name, value in artifacts.items():
        (package / "inputs" / name).write_text(json.dumps(value, ensure_ascii=False))
    (delivery / "script.json").write_bytes((DATA / "retained-overlong-vo.json").read_bytes())
    return package, delivery, private, payload, plan


def receive(case, command, *, pinned_node=True):
    package, delivery, private, _payload, _plan = case
    environment = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    environment.pop("PLOTLOOM_NODE", None)
    if pinned_node:
        environment["PLOTLOOM_NODE"] = str(Path(shutil.which("node")).resolve())
    return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/script_receiving.py"), command,
        str(delivery / "script.json"), "--request", str(package / "request.json")],
        cwd=private, env=environment, capture_output=True, timeout=20)


@pytest.mark.parametrize("maximum,success", [(8, False), (15, True)])
@pytest.mark.parametrize("command", ["validate", "render"])
def test_real_native_receiving_steps_enforce_same_planned_bounds(tmp_path, maximum, success, command):
    case = make_case(tmp_path, maximum)
    package, delivery, _private, _payload, plan = case
    before = {p: sha256(p.read_bytes()).hexdigest() for p in (package / "request.json", delivery / "script.json")}
    assert plan.route == "plotloom_native" and [s.program for s in plan.steps] == ["uv", "uv"]
    assert [s.step_id for s in plan.steps] == ["validate", "render"]
    result = receive(case, command)
    assert (result.returncode == 0) is success, result.stderr.decode()
    if not success:
        assert b"planned storyboard maximum" in result.stderr and result.stdout == b""
    elif command == "render":
        assert result.stdout.lower().startswith(b"<!doctype html>")
        assert not result.stdout.startswith("✓".encode())
    else:
        assert "全部通过校验" in result.stdout.decode()
    assert all(sha256(p.read_bytes()).hexdigest() == expected for p, expected in before.items())


def test_native_receiver_never_falls_back_to_ambient_node(tmp_path):
    result = receive(make_case(tmp_path), "render", pinned_node=False)
    assert result.returncode != 0 and b"explicitly pinned PLOTLOOM_NODE" in result.stderr
    assert result.stdout == b""


@pytest.mark.parametrize("mutation", ["missing", "drifted"])
def test_missing_or_drifted_requirement_refuses_before_report(tmp_path, mutation):
    case = make_case(tmp_path)
    package, _delivery, _private, payload, _plan = case
    admission = payload["inputArtifacts"]["script-admission.json"]
    if mutation == "missing":
        admission.pop("plannedStoryboardDialogue")
    else:
        admission["plannedStoryboardDialogue"]["normalizationVersion"] = "changed-normalization"
    (package / "inputs/script-admission.json").write_text(json.dumps(admission, ensure_ascii=False))
    (package / "request.json").write_text(json.dumps(payload, ensure_ascii=False))
    with pytest.raises(ValueError):
        validation_plan_from_package(payload)
    result = receive(case, "render")
    assert result.returncode != 0 and result.stdout == b""
