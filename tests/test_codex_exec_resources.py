from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.codex_exec_python_environment import inspect_checked_python_environment
from plotloom.codex_exec_resources import (
    CodexExecResourceError,
    codex_exec_source_read_paths,
    upstream_skill_path_for_stage,
)
from plotloom.storyboard_brief_style import freeze_storyboard_brief_style

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin(stage: str) -> dict[str, str]:
    upstream_path = upstream_skill_path_for_stage(stage)
    upstream_revision_root = (
        ROOT / "third_party" / "shuohao-skills"
        if not stage.startswith("bridge-")
        else ROOT
    )
    revision = subprocess.run(
        ["git", "-C", str(upstream_revision_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    specialist_path = (
        ".agents/skills/plotloom-intent-specialist/SKILL.md"
        if stage == "bridge-intent"
        else ".agents/skills/plotloom-presentation-specialist/SKILL.md"
        if stage == "bridge-presentation"
        else ".agents/skills/plotloom-shuohao-specialist/SKILL.md"
    )
    return {
        "upstreamRevision": revision,
        "upstreamSkillHash": _sha256(ROOT / upstream_path),
        "specialistSkillHash": _sha256(ROOT / specialist_path),
    }


def test_shuohao_source_allowlist_is_stage_bound_and_pinned():
    request = {
        "stage": "branches",
        "upstreamSkillPath": upstream_skill_path_for_stage("branches"),
        "executionPin": _pin("branches"),
    }

    paths = set(codex_exec_source_read_paths(ROOT, request))
    python_environment = inspect_checked_python_environment(ROOT)
    uv_runtime = Path(shutil.which("uv")).resolve(strict=True)

    assert paths == {
        (ROOT / "third_party/shuohao-skills/skills/novel-outline").resolve(),
        (ROOT / "scripts/branch_suggestion.py").resolve(),
        (ROOT / "src").resolve(),
        (ROOT / "pyproject.toml").resolve(),
        (ROOT / "uv.lock").resolve(),
        python_environment.root,
        uv_runtime,
        python_environment.runtime_root,
    }
    assert ROOT not in paths
    assert (ROOT / "third_party/shuohao-skills/skills/novel-storyboard").resolve() not in paths


def test_native_source_allowlist_uses_exact_document_and_validator():
    request = {
        "stage": "bridge-intent",
        "upstreamSkillPath": upstream_skill_path_for_stage("bridge-intent"),
        "executionPin": _pin("bridge-intent"),
    }

    paths = set(codex_exec_source_read_paths(ROOT, request))
    python_environment = inspect_checked_python_environment(ROOT)
    uv_runtime = Path(shutil.which("uv")).resolve(strict=True)

    assert paths == {
        (ROOT / "docs/creative-workflow/native-bridge-intent.md").resolve(),
        (ROOT / "scripts/native_bridge_intent.py").resolve(),
        (ROOT / "src").resolve(),
        (ROOT / "pyproject.toml").resolve(),
        (ROOT / "uv.lock").resolve(),
        python_environment.root,
        uv_runtime,
        python_environment.runtime_root,
    }


def test_node_stage_allowlist_pins_only_its_skill_adapter_and_runtime(tmp_path):
    request = {
        "stage": "characters",
        "upstreamSkillPath": upstream_skill_path_for_stage("characters"),
        "executionPin": _pin("characters"),
    }

    paths = set(codex_exec_source_read_paths(ROOT, request))
    node_executable = Path(shutil.which("node")).resolve(strict=True)

    assert paths == {
        (ROOT / "third_party/shuohao-skills/skills/novel-characters").resolve(),
        (ROOT / "scripts/cast-style.mjs").resolve(),
        node_executable.parent.parent,
    }
    assert (ROOT / ".venv").resolve() not in paths


@pytest.mark.parametrize(
    ("stage", "contract_filename", "contract", "adapter", "policy"),
    [
        (
            "characters",
            "cast-style-contract.json",
            freeze_brief_style("hand-cut paper collage"),
            "scripts/brief-cast-style.mjs",
            "src/plotloom/autopilot_brief_style.py",
        ),
        (
            "art",
            "art-style-contract.json",
            freeze_brief_style("hand-cut paper collage"),
            "scripts/brief-art-style.mjs",
            "src/plotloom/autopilot_brief_style.py",
        ),
        (
            "storyboard",
            "storyboard-style-contract.json",
            freeze_storyboard_brief_style(freeze_brief_style("hand-cut paper collage")),
            "scripts/brief-storyboard-style.mjs",
            "src/plotloom/storyboard_brief_style.py",
        ),
    ],
)
def test_saved_brief_source_allowlist_selects_neutral_adapter_and_exact_policy(
    stage: str, contract_filename: str, contract: dict, adapter: str, policy: str,
):
    request = {
        "stage": stage,
        "upstreamSkillPath": upstream_skill_path_for_stage(stage),
        "executionPin": _pin(stage),
        "inputArtifacts": {contract_filename: contract},
    }

    paths = set(codex_exec_source_read_paths(ROOT, request))
    node_executable = Path(shutil.which("node")).resolve(strict=True)
    expected = {
        (ROOT / f"third_party/shuohao-skills/skills/novel-{stage}").resolve(),
        (ROOT / adapter).resolve(),
        (ROOT / policy).resolve(),
        node_executable.parent.parent,
    }
    assert paths == expected
    if stage == "characters":
        assert (ROOT / "scripts/cast-style.mjs").resolve() not in paths
    elif stage == "art":
        assert (ROOT / "scripts/art-style.mjs").resolve() not in paths


def test_saved_brief_resource_route_fails_closed_for_mutated_contract():
    contract = freeze_brief_style("hand-cut paper collage") | {"direction": "new direction"}
    request = {
        "stage": "characters",
        "upstreamSkillPath": upstream_skill_path_for_stage("characters"),
        "executionPin": _pin("characters"),
        "inputArtifacts": {"cast-style-contract.json": contract},
    }

    with pytest.raises(CodexExecResourceError, match="saved-Brief contract"):
        codex_exec_source_read_paths(ROOT, request)


def test_source_allowlist_rejects_a_forged_stage_path_or_pin():
    request = {
        "stage": "branches",
        "upstreamSkillPath": "third_party/other/SKILL.md",
        "executionPin": _pin("branches"),
    }
    with pytest.raises(CodexExecResourceError, match="path does not match"):
        codex_exec_source_read_paths(ROOT, request)

    request["upstreamSkillPath"] = upstream_skill_path_for_stage("branches")
    request["executionPin"] = request["executionPin"] | {"upstreamSkillHash": "0" * 64}
    with pytest.raises(CodexExecResourceError, match="bytes no longer match"):
        codex_exec_source_read_paths(ROOT, request)
