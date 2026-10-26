"""Production-shaped 20-second F4→F5 fixture; no provider or native generation."""
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from plotloom.codex_exec_validation import (
    build_text_validation_plan,
    expand_validation_argv,
)
from plotloom.creative_handoff_identity import canonical_json
from plotloom.script_contracts import ScriptAcceptRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.script_dialogue_runtime import manual_validation_runtime
from tests.test_script_dialogue_compatibility import (
    dialogue_script,
    script_store,  # noqa: F401 -- pytest registers this imported fixture by name
)

ROOT = Path(__file__).resolve().parents[1]


def publish_rendered_fixture(store, request, candidate, tmp_path):
    """Run the real plan in the locked test engine for the manual receiver."""
    pin = store.creative_handoff_execution_pin(request)
    exchange = store.creative_handoff_exchange()
    # Manual publication uses its own package contract. The separate native
    # sandbox probe owns v4 host publication; do not mix the two receivers.
    paths = exchange.write_package(request, pin)
    package, delivery = Path(paths["packagePath"]), Path(paths["deliveryPath"])
    payload = json.loads((package / "request.json").read_bytes())
    plan = build_text_validation_plan(request, execution_pin=pin, source_revision="a" * 40)
    private = tmp_path / request.stage
    private.mkdir()
    work = private / "validation"
    work.mkdir()
    delivery.mkdir()
    (delivery / plan.candidate_filename).write_bytes(canonical_json(candidate))
    before = sha256((delivery / plan.candidate_filename).read_bytes()).hexdigest()
    frozen = {path: sha256(path.read_bytes()).hexdigest() for path in package.rglob("*") if path.is_file()}
    with manual_validation_runtime(ROOT, private) as runtime:
        runtime.observations.update(candidateSha256=before,
            frozenPackageSha256={str(path.relative_to(package)): digest for path, digest in frozen.items()},
            results=[])
        for step in plan.steps:
            argv = expand_validation_argv(step, source_root=ROOT, submodule_root=ROOT / "third_party/shuohao-skills",
                job_root=package.parent, candidate_filename=plan.candidate_filename, tool_paths=runtime.tools)
            runtime.observations["validationArgv"].append(list(argv))
            result = subprocess.run(argv, cwd=work, env=runtime.environment, capture_output=True, timeout=30, check=False)
            assert result.returncode == 0, result.stderr.decode()
            runtime.observations["results"].append({"stepId": step.step_id,
                "exitCode": result.returncode, "stdoutSha256": sha256(result.stdout).hexdigest()})
            assert {path: sha256(path.read_bytes()).hexdigest() for path in package.rglob("*") if path.is_file()} == frozen
            assert sha256((delivery / plan.candidate_filename).read_bytes()).hexdigest() == before
            if step.stdout_is_report:
                assert result.stdout.lower().startswith(b"<!doctype html>")
                assert result.stdout.strip().lower().endswith(b"</html>")
                (delivery / plan.report_filename).write_bytes(result.stdout)
    assert sha256((delivery / plan.candidate_filename).read_bytes()).hexdigest() == before
    manifest = {"schemaVersion": 1, "jobId": request.job_id, "requestHash": payload["requestHash"],
        "stage": request.stage, "deliveryId": "provider-free-composition",
        "candidate": {"filename": plan.candidate_filename}, "report": {"filename": plan.report_filename},
        "executorProvenance": {"codeRevision": "a" * 40, "skillVersion": "fixture",
            "skillHash": pin["specialistSkillHash"], "upstreamRevision": pin["upstreamRevision"],
            "upstreamSkillHash": pin["upstreamSkillHash"], "model": "fixture", "reasoningEffort": "high"}}
    for kind, filename in (("candidate", plan.candidate_filename), ("report", plan.report_filename)):
        manifest[kind]["sha256"] = sha256((delivery / filename).read_bytes()).hexdigest()
    manifest["executorProvenance"]["codeRevision"] = "a" * 40
    manifest["limitations"] = ["provider-free fixture; direct command execution, not native sandbox generation"]
    (delivery / "completion.json").write_text(json.dumps(manifest))
    return exchange.read_delivery(request, pin)


def compatible_board(script):
    episodes = []
    for episode in script["episodes"]:
        line = episode["scenes"][0]["flow"][1]["line"]
        prompt = (
            "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
            "integrated_multimodal_description:\n[Shot 1] Cinematic, live-action, cool gray palette. "
            f"A static shot of the empty doorway in <Picture 1>. An off-screen narrator VO says <d>[Chinese] {line}</d>.\n\n"
            "overall_soundscape: Quiet wind.\n\nnon_diegetic_music: N/A"
        )
        cut = {"seconds": 4.5, "beats": [1, 2], "size": "medium", "camera": "Static Shot", "characters": [], "props": [],
            "frame": "medium shot of an empty doorway at dawn, cinematic film still, cool gray palette, 16:9"}
        episodes.append({"ep": episode["ep"], "segments": [{"id": f"E{episode['ep']:02}-01", "sceneIndex": 1,
            "cuts": [cut], "h3Prompt": prompt}]})
    return {"source": script["source"], "params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}, "episodes": episodes}


def test_twenty_second_opted_in_script_flows_through_real_f5_receiving(script_store, tmp_path, monkeypatch):  # noqa: F811
    from plotloom import codex_exec_python_environment
    def forbidden_operator_admission(*args, **kwargs):
        raise AssertionError("manual composition must not inspect an operator Codex environment")
    monkeypatch.setattr(codex_exec_python_environment, "inspect_checked_python_environment", forbidden_operator_admission)
    candidate, request = script_store.prepare_script_candidate("ch_" + "6" * 32, planned_storyboard_max_cut_seconds=8)
    script = dialogue_script(request)
    ready = script_store.admit_script_delivery(publish_rendered_fixture(script_store, request, script, tmp_path))
    accepted = script_store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0,
        binding=ready.binding)).accepted_script
    board, frozen = script_store.prepare_storyboard_review_candidate("ch_" + "7" * 32, max_cut_seconds=8)
    assert frozen.input_artifacts["script.json"] == accepted.script == script
    assert board.binding.target_playthrough_seconds == accepted.binding.target_playthrough_seconds == 20
    ready_board = script_store.admit_storyboard_review_delivery(
        publish_rendered_fixture(script_store, frozen, compatible_board(script), tmp_path))
    review = script_store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=board.job_id,
        expected_review_revision=0, binding=ready_board.binding))
    assert review.status == "accepted" and review.stale_reasons == []
    assert script_store.script_state().accepted_script == accepted
    for stage, program in (("script", "uv"), ("storyboard", "node")):
        facts = json.loads((tmp_path / stage / "runtime-observations.json").read_bytes())
        assert facts["python"]["executable"] == sys.executable
        assert facts["python"]["physicalExecutable"] == str(Path(sys.executable).resolve())
        assert facts["python"]["prefix"] == sys.prefix
        assert Path(facts["python"]["appImport"]) == ROOT / "src/plotloom/script_receiving.py"
        assert Path(facts["node"]["executable"]).is_absolute()
        assert facts["node"]["executable"] == facts["tools"]["node"]
        assert [item["stepId"] for item in facts["results"]] == ["validate", "render"]
        assert len(facts["validationArgv"]) == 2
        assert all(argv[0] == facts["tools"][program] for argv in facts["validationArgv"])
        assert facts["parentEnvironmentUnchanged"] and facts["sourceConfigurationUnchanged"]
        assert facts["operatorReceiptPresentBefore"] == facts["operatorReceiptPresentAfter"]
