from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.codex_exec_validation import (
    CodexExecTextValidationPlan,
    build_text_validation_plan,
    expand_validation_argv,
    validation_plan_from_package,
)
from plotloom.creative_handoff_contracts import (
    CreativeHandoffRequest,
    creative_handoff_request_from_package,
)
from plotloom.production_dialogue_timing import (
    TIMING_FILENAME,
    freeze_f5_dialogue_timing,
)
from plotloom.storyboard_brief_style import freeze_storyboard_brief_style

PIN = {
    "upstreamRevision": "a" * 40,
    "upstreamSkillHash": "b" * 64,
    "specialistSkillHash": "c" * 64,
}
SOURCE_REVISION = "d" * 40


def _request(stage: str, artifacts: dict | None = None) -> CreativeHandoffRequest:
    if stage == "storyboard" and artifacts is not None and TIMING_FILENAME not in artifacts:
        artifacts = artifacts | {TIMING_FILENAME: freeze_f5_dialogue_timing(
            artifacts["script.json"], script_content_hash="a" * 64, language="zh-CN",
        ).model_dump(mode="json", by_alias=True)}
    return CreativeHandoffRequest.model_validate({
        "jobId": "ch_" + "a" * 20,
        "projectId": "project-demo",
        "sectionId": "section-opening",
        "stage": stage,
        "expectedStageRevision": 4,
        "source": {"kind": "synopsis", "text": "A ferryman faces one irreversible choice."},
        "inputArtifacts": artifacts or {},
        "creativeBrief": "Create one stage candidate. Preserve the frozen source facts.",
    })


def _saved_brief_artifacts(stage: str) -> dict:
    if stage == "characters":
        return {"cast-style-contract.json": freeze_brief_style("use restrained natural light")}
    if stage == "art":
        return {
            "art-style-contract.json": freeze_brief_style("use restrained natural light"),
            "cast.json": {"characters": []},
        }
    inherited = freeze_brief_style("use restrained natural light")
    return {
        "storyboard-style-contract.json": freeze_storyboard_brief_style(inherited),
        "script.json": {"episodes": []},
        "outline.json": {"episodes": []},
        "cast.json": {"characters": []},
        "art.json": {"scenes": []},
    }


@pytest.mark.parametrize(
    ("stage", "artifacts", "route", "candidate"),
    [
        ("outline", {}, "upstream", "outline.json"),
        ("branches", {}, "plotloom_native", "branches.json"),
        ("characters", {"cast-style-contract.json": {"style": "live-action"}}, "preset_style", "cast.json"),
        ("art", {"art-style-contract.json": {"style": "live-action"}, "cast.json": {"characters": []}}, "preset_style", "art.json"),
        ("script", {"outline.json": {"episodes": []}, "art.json": {"scenes": []}, "cast.json": {"characters": []}}, "upstream", "script.json"),
        ("storyboard", {"script.json": {"episodes": []}, "outline.json": {"episodes": []}, "cast.json": {"characters": []}, "art.json": {"scenes": []}}, "upstream", "storyboard.json"),
        ("bridge-intent", {}, "plotloom_native", "intent.json"),
        ("bridge-presentation", {}, "plotloom_native", "presentation.json"),
    ],
)
def test_plan_freezes_two_fixed_steps_for_each_fresh_text_stage(stage, artifacts, route, candidate):
    plan = build_text_validation_plan(_request(stage, artifacts), execution_pin=PIN, source_revision=SOURCE_REVISION)

    assert plan.stage == stage
    assert plan.route == route
    assert plan.candidate_filename == candidate
    assert tuple(step.step_id for step in plan.steps) == ("validate", "render")
    assert plan.steps[1].stdout_is_report
    assert not plan.steps[0].stdout_is_report
    assert all("sh" not in step.program for step in plan.steps)


@pytest.mark.parametrize("stage", ["characters", "art", "storyboard"])
def test_saved_brief_routes_expand_to_exact_single_node_command(stage, tmp_path):
    request = _request(stage, _saved_brief_artifacts(stage))
    plan = build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    source = tmp_path / "source"
    job = tmp_path / "job"
    tools = {"node": tmp_path / "node", "uv": tmp_path / "uv"}

    argv = expand_validation_argv(
        plan.steps[0], source_root=source, submodule_root=source / "third_party/shuohao-skills",
        job_root=job, candidate_filename=plan.candidate_filename, tool_paths=tools,
    )

    assert argv[0] == str(tools["node"])
    expected_adapter = {
        "characters": "brief-cast-style.mjs",
        "art": "brief-art-style.mjs",
        "storyboard": "brief-storyboard-style.mjs",
    }[stage]
    assert argv[1] == str(source / "scripts" / expected_adapter)
    assert argv[2:4] == ("validate", str(job / "delivery" / plan.candidate_filename))
    assert not any(arg.startswith("node") and arg != str(tools["node"]) for arg in argv)


def test_plan_package_mismatch_is_rejected_before_any_command_can_be_expanded():
    request = _request("branches")
    plan = build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    package = request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4,
        "executorBackend": "codex_exec",
        "plotloomCodeRevision": SOURCE_REVISION,
        "executionPin": PIN,
        "validationPlan": plan.model_dump(mode="json", by_alias=True),
        "validationPlanHash": plan.plan_hash,
    }

    assert validation_plan_from_package(package) == plan
    package["validationPlan"]["steps"][1]["argv"] = ["python", "-c", "print('fake')"]
    with pytest.raises(ValueError, match="source-owned stage policy"):
        validation_plan_from_package(package)


@pytest.mark.parametrize(
    ("stage", "tool_name"),
    [("outline", "node"), ("branches", "uv")],
)
def test_command_expansion_needs_only_the_stage_pinned_runtime(stage, tool_name, tmp_path):
    plan = build_text_validation_plan(_request(stage), execution_pin=PIN, source_revision=SOURCE_REVISION)
    tool = tmp_path / tool_name
    step = plan.steps[0]

    argv = expand_validation_argv(
        step,
        source_root=tmp_path / "source",
        submodule_root=tmp_path / "source" / "third_party" / "shuohao-skills",
        job_root=tmp_path / "job",
        candidate_filename=plan.candidate_filename,
        tool_paths={tool_name: tool},
    )

    assert argv[0] == str(tool)


def test_command_expansion_reports_a_missing_step_runtime_as_a_contract_error(tmp_path):
    plan = build_text_validation_plan(_request("outline"), execution_pin=PIN, source_revision=SOURCE_REVISION)
    with pytest.raises(ValueError, match="frozen validator runtime is unavailable: node"):
        expand_validation_argv(
            plan.steps[0], source_root=tmp_path / "source",
            submodule_root=tmp_path / "source" / "third_party" / "shuohao-skills",
            job_root=tmp_path / "job", candidate_filename=plan.candidate_filename,
            tool_paths={},
        )


def test_package_request_projection_tracks_the_request_model_fields():
    request = _request("outline")
    plan = build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    package = request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4,
        "executorBackend": "codex_exec",
        "plotloomCodeRevision": SOURCE_REVISION,
        "executionPin": PIN,
        "validationPlan": plan.model_dump(mode="json", by_alias=True),
        "validationPlanHash": plan.plan_hash,
    }

    assert creative_handoff_request_from_package(package) == request
    with pytest.raises(ValidationError):
        CreativeHandoffRequest.model_validate(package)


def test_plan_contract_rejects_missing_render_or_reordered_step():
    plan = build_text_validation_plan(_request("outline"), execution_pin=PIN, source_revision=SOURCE_REVISION)
    value = plan.model_dump(mode="json", by_alias=True)

    with pytest.raises(ValidationError):
        CodexExecTextValidationPlan.model_validate(value | {"steps": value["steps"][:1]})
    with pytest.raises(ValidationError, match="ordered validate and render"):
        CodexExecTextValidationPlan.model_validate(value | {"steps": list(reversed(value["steps"]))})
