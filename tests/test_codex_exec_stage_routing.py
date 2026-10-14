from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from plotloom.art_style import freeze_art_style
from plotloom.autopilot_brief_style import (
    BRIEF_STYLE,
    BRIEF_STYLE_LABEL,
    brief_stage_instructions,
    freeze_brief_style,
)
from plotloom.cast_style import freeze_cast_style
from plotloom.codex_exec_resources import codex_exec_source_resources
from plotloom.codex_exec_validation import expand_validation_argv, validation_plan_from_package
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from tests.storyboard_brief_fixtures import real_example_request

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "third_party/shuohao-skills/skills"
BRIEF_DIRECTION = "2D animation; hand-cut paper collage; muted watercolor"
PLOTLOOM_CODE_REVISION = "f" * 40


def _saved_brief_cast_and_art() -> tuple[dict, dict, str]:
    cast = json.loads((EXAMPLES / "novel-characters/examples/渡口-cast.json").read_text())
    art = json.loads((EXAMPLES / "novel-art/examples/渡口-art.json").read_text())
    cast["style"] = art["style"] = BRIEF_STYLE
    source_quotes = []
    for index, character in enumerate(cast["characters"], 1):
        character["id"] = f"C{index:02d}"
        character["image"]["style"] = BRIEF_STYLE_LABEL
        source_quotes.extend(character.get("persona", {}).get("evidence", []))
    for collection in ("scenes", "props"):
        for subject in art.get(collection, []):
            if isinstance(subject.get("image"), dict):
                subject["image"]["style"] = BRIEF_STYLE_LABEL
    return cast, art, "\n".join(source_quotes)


def _saved_brief_example(stage: str) -> tuple[CreativeHandoffRequest, dict, str]:
    if stage in {"characters", "art"}:
        cast, art, source_text = _saved_brief_cast_and_art()
        contract = freeze_brief_style(BRIEF_DIRECTION)
        input_artifacts = (
            {"cast-style-contract.json": contract}
            if stage == "characters"
            else {"cast.json": cast, "art-style-contract.json": contract}
        )
        request = CreativeHandoffRequest.model_validate({
            "jobId": "ch_" + stage + "a" * 24,
            "projectId": "codex-exec-stage-routing",
            "sectionId": "section-example",
            "stage": stage,
            "expectedStageRevision": 1,
            "source": {"kind": "synopsis", "text": source_text},
            "inputArtifacts": input_artifacts,
            "creativeBrief": brief_stage_instructions("cast" if stage == "characters" else "art"),
        })
        return request, cast if stage == "characters" else art, "cast.json" if stage == "characters" else "art.json"

    request, board, _binding = real_example_request(BRIEF_DIRECTION)
    return request, board, "storyboard.json"


def _assert_candidate_only_assignment(instructions: str) -> None:
    assert "Write only the stage-shaped candidate JSON" in instructions
    assert "Do not create report.html, completion.json, or any other output" in instructions
    assert "do not run validators or renderers" in instructions
    assert "trusted Codex Exec host validates the candidate and creates the report" in instructions
    assert "From the delivery directory, run exactly:\n" not in instructions
    assert "$PLOTLOOM_NODE" not in instructions


def _run_frozen_plan(tmp_path: Path, stage: str) -> str:
    request, candidate, candidate_filename = _saved_brief_example(stage)
    exchange = CreativeHandoffExchange(tmp_path / "creative-handoff")
    pin = exchange.current_execution_pin(stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION)
    package = Path(paths["packagePath"])
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    candidate_bytes = canonical_json(candidate)
    (delivery / candidate_filename).write_bytes(candidate_bytes)

    instructions = (package / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")
    _assert_candidate_only_assignment(instructions)
    package_request = json.loads((package / "request.json").read_text(encoding="utf-8"))
    plan = validation_plan_from_package(package_request)
    resources = codex_exec_source_resources(ROOT, package_request)
    tools = dict(resources.tools)
    adapter = f"scripts/brief-{'cast' if stage == 'characters' else stage}-style.mjs"
    policy = "src/plotloom/storyboard_brief_style.py" if stage == "storyboard" else "src/plotloom/autopilot_brief_style.py"
    assert plan.route == "saved_brief" and plan.candidate_filename == candidate_filename
    assert plan.source_revision == PLOTLOOM_CODE_REVISION
    assert set(resources.read_paths) == {
        (EXAMPLES / f"novel-{stage}").resolve(), (ROOT / adapter).resolve(),
        (ROOT / policy).resolve(), tools["node"].parent.parent,
    }
    assert tuple(step.step_id for step in plan.steps) == ("validate", "render")
    assert tuple(step.stdout_is_report for step in plan.steps) == (False, True)
    assert {path.name for path in delivery.iterdir()} == {candidate_filename}
    report_path = delivery / plan.report_filename
    for step in plan.steps:
        argv = expand_validation_argv(
            step, source_root=ROOT, submodule_root=ROOT / "third_party/shuohao-skills",
            job_root=package.parent, candidate_filename=plan.candidate_filename, tool_paths=tools,
        )
        assert argv[:2] == (str(tools["node"]), str(ROOT / adapter))
        result = subprocess.run(argv, cwd=delivery, capture_output=True, check=True, timeout=30)
        if step.stdout_is_report:
            assert not report_path.exists()
            report_path.write_bytes(result.stdout)
            assert report_path.read_bytes() == result.stdout
        else:
            assert not report_path.exists()
        assert (delivery / candidate_filename).read_bytes() == candidate_bytes
    report = report_path.read_bytes().decode("utf-8")
    assert "<html" in report.lower()
    assert {path.name for path in delivery.iterdir()} == {candidate_filename, "report.html"}
    return report


@pytest.mark.parametrize("stage", ["characters", "art", "storyboard"])
def test_emitted_saved_brief_commands_validate_and_render_frozen_examples(tmp_path: Path, stage: str):
    report = _run_frozen_plan(tmp_path, stage)
    assert "saved" in report.lower() or "storyboard" in report.lower()


@pytest.mark.parametrize(
    ("stage", "contract_filename", "contract_factory", "adapter", "neutral_adapter"),
    [
        ("characters", "cast-style-contract.json", freeze_cast_style, "scripts/cast-style.mjs", "scripts/brief-cast-style.mjs"),
        ("art", "art-style-contract.json", freeze_art_style, "scripts/art-style.mjs", "scripts/brief-art-style.mjs"),
    ],
)
def test_preset_control_keeps_existing_adapter_and_allowlist(
    tmp_path: Path, stage: str, contract_filename: str, contract_factory, adapter: str, neutral_adapter: str,
):
    contract = contract_factory("ghibli", None)
    artifacts = {contract_filename: contract}
    if stage == "art":
        artifacts["cast.json"] = {}
    request = CreativeHandoffRequest.model_validate({
        "jobId": "ch_preset" + stage + "b" * 20,
        "projectId": "codex-exec-stage-routing",
        "sectionId": "section-example",
        "stage": stage,
        "expectedStageRevision": 1,
        "source": {"kind": "synopsis", "text": "A ferry crosses at dusk."},
        "inputArtifacts": artifacts,
        "creativeBrief": "Keep the frozen preset authority.",
    })
    exchange = CreativeHandoffExchange(tmp_path / "creative-handoff")
    paths = exchange.write_package(
        request, exchange.current_execution_pin(stage), executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION,
    )
    package = Path(paths["packagePath"])
    instructions = (package / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")
    package_request = json.loads((package / "request.json").read_text(encoding="utf-8"))
    _assert_candidate_only_assignment(instructions)
    plan = validation_plan_from_package(package_request)
    resources = codex_exec_source_resources(ROOT, package_request)
    tools = dict(resources.tools)

    assert plan.route == "preset_style"
    assert plan.source_revision == PLOTLOOM_CODE_REVISION
    assert all(step.program == "node" and step.argv[0] == f"{{source}}/{adapter}" for step in plan.steps)
    assert neutral_adapter not in instructions
    assert set(resources.read_paths) == {
        (EXAMPLES / f"novel-{stage}").resolve(), (ROOT / adapter).resolve(), tools["node"].parent.parent,
    }
    assert (ROOT / neutral_adapter).resolve() not in resources.read_paths
