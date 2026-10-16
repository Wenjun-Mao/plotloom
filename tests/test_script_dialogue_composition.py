"""Production-shaped 20-second F4→F5 fixture; no provider or native generation."""
import json
import subprocess
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from plotloom.codex_exec_resources import codex_exec_source_resources
from plotloom.codex_exec_validation import build_text_validation_plan, expand_validation_argv
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.script_contracts import ScriptAcceptRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.test_script_dialogue_compatibility import script_store, dialogue_script  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def publish_rendered_fixture(store, request, candidate, tmp_path, monkeypatch):
    """Execute the source-owned plan with its real checked runtime environment."""
    monkeypatch.syspath_prepend(str(ROOT / "services/creator_workbench"))
    from codex_exec_supervisor_environment import CodexExecSupervisorEnvironmentMixin
    from plotloom.codex_exec_profile import TEXT_VALIDATOR_RUNTIME_PROFILE
    pin = store.creative_handoff_execution_pin(request)
    exchange = store.creative_handoff_exchange()
    # Manual publication uses its own package contract. The separate native
    # sandbox probe owns v4 host publication; do not mix the two receivers.
    paths = exchange.write_package(request, pin)
    package, delivery = Path(paths["packagePath"]), Path(paths["deliveryPath"])
    payload = json.loads((package / "request.json").read_bytes())
    plan = build_text_validation_plan(request, execution_pin=pin, source_revision="a" * 40)
    resources = codex_exec_source_resources(ROOT, payload)
    private = tmp_path / request.stage
    private.mkdir()
    work = private / "validation"
    work.mkdir()
    delivery.mkdir()
    (delivery / plan.candidate_filename).write_bytes(canonical_json(candidate))
    before = sha256((delivery / plan.candidate_filename).read_bytes()).hexdigest()
    runner = CodexExecSupervisorEnvironmentMixin()
    runner.codex_home = private / "sandbox-home"
    runner.codex_home.mkdir()
    environment = runner._cli_environment(private, source_root=ROOT, domain="text", source_resources=resources,
        profile=SimpleNamespace(contract_version="plotloom.codex-exec.v8", text_validator_runtime_profile=TEXT_VALIDATOR_RUNTIME_PROFILE))
    for step in plan.steps:
        argv = expand_validation_argv(step, source_root=ROOT, submodule_root=ROOT / "third_party/shuohao-skills",
            job_root=package.parent, candidate_filename=plan.candidate_filename, tool_paths=dict(resources.tools))
        result = subprocess.run(argv, cwd=work, env=environment, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr.decode()
        if step.stdout_is_report:
            assert result.stdout.lower().startswith(b"<!doctype html>")
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


def test_twenty_second_opted_in_script_flows_through_real_f5_receiving(script_store, tmp_path, monkeypatch):
    candidate, request = script_store.prepare_script_candidate("ch_" + "6" * 32, planned_storyboard_max_cut_seconds=8)
    script = dialogue_script(request)
    ready = script_store.admit_script_delivery(publish_rendered_fixture(script_store, request, script, tmp_path, monkeypatch))
    accepted = script_store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0,
        binding=ready.binding)).accepted_script
    board, frozen = script_store.prepare_storyboard_review_candidate("ch_" + "7" * 32, max_cut_seconds=8)
    assert frozen.input_artifacts["script.json"] == accepted.script == script
    assert board.binding.target_playthrough_seconds == accepted.binding.target_playthrough_seconds == 20
    ready_board = script_store.admit_storyboard_review_delivery(
        publish_rendered_fixture(script_store, frozen, compatible_board(script), tmp_path, monkeypatch))
    review = script_store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=board.job_id,
        expected_review_revision=0, binding=ready_board.binding))
    assert review.status == "accepted" and review.stale_reasons == []
    assert script_store.script_state().accepted_script == accepted
