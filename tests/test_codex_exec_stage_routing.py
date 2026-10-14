from __future__ import annotations

import json
import os
import shutil
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
from plotloom.codex_exec_resources import codex_exec_source_read_paths
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from tests.storyboard_brief_fixtures import real_example_request

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "third_party/shuohao-skills/skills"
BRIEF_DIRECTION = "2D animation; hand-cut paper collage; muted watercolor"


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


def _run_emitted_commands(tmp_path: Path, stage: str) -> str:
    request, candidate, candidate_filename = _saved_brief_example(stage)
    exchange = CreativeHandoffExchange(tmp_path / "creative-handoff")
    pin = exchange.current_execution_pin(stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec")
    package = Path(paths["packagePath"])
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    (delivery / candidate_filename).write_bytes(canonical_json(candidate))

    instructions = (package / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")
    marker = "From the delivery directory, run exactly:\n"
    assert instructions.count(marker) == 1
    commands = [
        line for line in instructions.split(marker, 1)[1].splitlines()
        if line.startswith('"$PLOTLOOM_NODE" ')
    ]
    assert len(commands) == 2
    assert " validate " in commands[0] and " render " in commands[1]

    node = shutil.which("node")
    assert node is not None
    environment = os.environ | {"PLOTLOOM_SOURCE_ROOT": str(ROOT), "PLOTLOOM_NODE": node}
    for command in commands:
        subprocess.run(
            ["bash", "-e", "-c", command], cwd=delivery, env=environment,
            capture_output=True, text=True, check=True,
        )
    report = (delivery / "report.html").read_text(encoding="utf-8")
    assert "<html" in report.lower()
    assert {path.name for path in delivery.iterdir()} == {candidate_filename, "report.html"}
    return report


@pytest.mark.parametrize("stage", ["characters", "art", "storyboard"])
def test_emitted_saved_brief_commands_validate_and_render_frozen_examples(tmp_path: Path, stage: str):
    report = _run_emitted_commands(tmp_path, stage)
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
    paths = exchange.write_package(request, exchange.current_execution_pin(stage), executor_backend="codex_exec")
    package = Path(paths["packagePath"])
    instructions = (package / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")
    package_request = json.loads((package / "request.json").read_text(encoding="utf-8"))
    resources = set(codex_exec_source_read_paths(ROOT, package_request))

    assert f'"$PLOTLOOM_SOURCE_ROOT/{adapter}"' in instructions
    assert neutral_adapter not in instructions
    assert (ROOT / adapter).resolve() in resources
    assert (ROOT / neutral_adapter).resolve() not in resources
