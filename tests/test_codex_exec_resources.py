from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.codex_exec_python_environment import inspect_checked_python_environment
from plotloom.codex_exec_resources import (
    CodexExecResourceError,
    codex_exec_source_resources,
    codex_exec_source_read_paths,
    upstream_skill_path_for_stage,
)
from plotloom.storyboard_brief_style import freeze_storyboard_brief_style
from tests.codex_exec_runtime_fixtures import (
    codex_exec_test_source as _codex_exec_test_source,  # noqa: F401
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("planned", [False, True])
@pytest.mark.parametrize("typed", [False, True])
def test_opted_in_script_keeps_checked_python_and_pinned_node_together(planned, typed):
    from plotloom.script_dialogue_compatibility import freeze_planned_storyboard_dialogue
    artifacts = {}
    if planned:
        artifacts["script-admission.json"] = {"plannedStoryboardDialogue": freeze_planned_storyboard_dialogue(
            max_cut_seconds=8, language="zh-CN").model_dump(mode="json", by_alias=True)}
    request = dict(stage="script", upstreamSkillPath=upstream_skill_path_for_stage("script"),
        executionPin=_pin("script"), inputArtifacts=artifacts)
    if typed:
        request["contentValidationContract"] = "plotloom.typed-content-result.v1"
    resources = codex_exec_source_resources(ROOT, request)
    assert (ROOT / "scripts/script-content-validation.mjs" in resources.read_paths) is typed
    tools = dict(resources.tools)
    assert set(tools) == ({"uv", "python", "node"} if planned else {"node"})
    assert tools["node"].parent.parent.resolve() in resources.read_paths
    assert (ROOT / "src" in resources.read_paths) is planned
    assert (ROOT / "scripts/script_receiving.py" in resources.read_paths) is planned
    assert (resources.python_environment is not None) is planned


@pytest.fixture(autouse=True)
def test_owned_source(monkeypatch, codex_exec_test_source):
    monkeypatch.setattr(__import__(__name__, fromlist=["ROOT"]), "ROOT", codex_exec_test_source)


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
        (ROOT / "scripts/provider-literal-context.mjs").resolve(),
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
        (ROOT / "scripts/provider-literal-context.mjs").resolve(),
        node_executable.parent.parent,
    }
    if stage == "storyboard":
        expected.add((ROOT / "scripts/storyboard-dialogue-timing.mjs").resolve())
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


@pytest.mark.parametrize("marked", [False, True])
def test_outline_echo_wrapper_keeps_checked_python_and_renderer_node_together(marked):
    from plotloom.outline_echoes import ECHO_CONTRACT_FILENAME, outline_echo_contract
    artifacts = {ECHO_CONTRACT_FILENAME: outline_echo_contract()} if marked else {}
    request = dict(stage="outline", upstreamSkillPath=upstream_skill_path_for_stage("outline"),
        executionPin=_pin("outline"), inputArtifacts=artifacts,
        contentValidationContract="plotloom.typed-content-result.v1")
    resources = codex_exec_source_resources(ROOT, request)
    tools = dict(resources.tools)
    assert set(tools) == ({"uv", "python", "node"} if marked else {"node"})
    assert tools["node"].parent.parent.resolve() in resources.read_paths
    assert (ROOT / "scripts/outline_content_validation.py" in resources.read_paths) is marked
    assert (ROOT / "scripts/text-content-validation.mjs") in resources.read_paths
    assert (resources.python_environment is not None) is marked


@pytest.mark.parametrize("stage", ["outline", "characters", "art"])
def test_typed_text_validator_read_scope_contains_its_transitive_static_import(stage):
    request = dict(stage=stage, upstreamSkillPath=upstream_skill_path_for_stage(stage),
        executionPin=_pin(stage), inputArtifacts={},
        contentValidationContract="plotloom.typed-content-result.v1")
    resources = codex_exec_source_resources(ROOT, request)

    assert ROOT / "scripts/text-content-validation.mjs" in resources.read_paths
    assert ROOT / "scripts/provider-literal-context.mjs" in resources.read_paths
    assert ROOT not in resources.read_paths
    assert ROOT / "scripts" not in resources.read_paths


def test_outline_text_validator_import_succeeds_only_with_exact_sandbox_files():
    request = dict(stage="outline", upstreamSkillPath=upstream_skill_path_for_stage("outline"),
        executionPin=_pin("outline"), inputArtifacts={},
        contentValidationContract="plotloom.typed-content-result.v1")
    resources = codex_exec_source_resources(ROOT, request)
    validator = (ROOT / "scripts/text-content-validation.mjs").resolve()
    context = (ROOT / "scripts/provider-literal-context.mjs").resolve()
    assert validator in resources.read_paths and context in resources.read_paths
    node = dict(resources.tools)["node"]
    code = f"await import({json.dumps(validator.as_uri())})"

    def run(allowed_paths):
        command = [str(node), "--permission"]
        command.extend(f"--allow-fs-read={path}" for path in allowed_paths)
        command.extend(("--input-type=module", "--eval", code))
        return subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)

    allowed = run((validator, context))
    assert allowed.returncode == 0, allowed.stderr
    missing_dependency = run((validator,))
    assert missing_dependency.returncode != 0
    assert "ERR_ACCESS_DENIED" in missing_dependency.stderr
    assert str(context) in missing_dependency.stderr


@pytest.mark.parametrize("stage", ["outline", "branches", "characters", "art", "script", "storyboard",
    "bridge-intent", "bridge-presentation"])
def test_language_checker_scope_includes_all_policy_hash_inputs_and_denies_unrelated_resources(stage):
    request = dict(stage=stage, upstreamSkillPath=upstream_skill_path_for_stage(stage),
        executionPin=_pin(stage), source={"operation": "content-language-check"}, inputArtifacts={})
    resources = codex_exec_source_resources(ROOT, request)
    policy_files = tuple(ROOT / f"third_party/shuohao-skills/skills/{skill}/scripts/provider-literals.mjs"
        for skill in ("novel-art", "novel-characters", "novel-storyboard"))

    assert set(policy_files) <= set(resources.read_paths)
    assert ROOT / "scripts/content_language.py" in resources.read_paths
    assert ROOT not in resources.read_paths
    assert ROOT / "scripts" not in resources.read_paths
    assert ROOT / "third_party/shuohao-skills" not in resources.read_paths
    assert ROOT / "third_party/shuohao-skills/skills" not in resources.read_paths
    assert ROOT / "scripts/creative_field_validation.py" not in resources.read_paths
    assert ROOT / "scripts/art_content_validation.py" not in resources.read_paths
    upstream_path = upstream_skill_path_for_stage(stage)
    expected_stage_root = (ROOT / upstream_path).parent.resolve() if upstream_path.startswith(
        "third_party/shuohao-skills/"
    ) else None
    for skill in ("novel-outline", "novel-characters", "novel-art", "novel-script", "novel-storyboard"):
        stage_root = (ROOT / "third_party/shuohao-skills/skills" / skill).resolve()
        if stage_root != expected_stage_root:
            assert stage_root not in resources.read_paths


@pytest.mark.parametrize("stage", ["characters", "art", "storyboard"])
def test_primary_literal_binders_receive_all_policy_hash_inputs_only_when_run(stage):
    artifacts = {"provider-literal-contract.json": {}}
    if stage == "characters":
        from plotloom.creative_field_ownership import OWNERSHIP_FILENAME
        artifacts[OWNERSHIP_FILENAME] = {}
    elif stage == "art":
        from plotloom.art_structure import ART_STRUCTURE_FILENAME, art_structure_artifact
        artifacts["art-style-contract.json"] = {"style": "frozen-style"}
        artifacts[ART_STRUCTURE_FILENAME] = art_structure_artifact(preset=True)
    request = dict(stage=stage, upstreamSkillPath=upstream_skill_path_for_stage(stage),
        executionPin=_pin(stage), inputArtifacts=artifacts,
        contentValidationContract="plotloom.typed-content-result.v1")
    resources = codex_exec_source_resources(ROOT, request)
    policy_files = tuple(ROOT / f"third_party/shuohao-skills/skills/{skill}/scripts/provider-literals.mjs"
        for skill in ("novel-art", "novel-characters", "novel-storyboard"))

    assert set(policy_files) <= set(resources.read_paths)
    assert ROOT / ("scripts/art_content_validation.py" if stage == "art" else "scripts/creative_field_validation.py") in resources.read_paths
    assert ROOT not in resources.read_paths
    assert ROOT / "scripts" not in resources.read_paths
    assert ROOT / "third_party/shuohao-skills" not in resources.read_paths
    assert ROOT / "third_party/shuohao-skills/skills" not in resources.read_paths
    assert ROOT / "third_party/shuohao-skills/skills/novel-outline" not in resources.read_paths
    assert ROOT / "third_party/shuohao-skills/skills/novel-script" not in resources.read_paths
    upstream_root = (ROOT / upstream_skill_path_for_stage(stage)).parent.resolve()
    for skill in ("novel-outline", "novel-characters", "novel-art", "novel-script", "novel-storyboard"):
        stage_root = (ROOT / "third_party/shuohao-skills/skills" / skill).resolve()
        if stage_root != upstream_root:
            assert stage_root not in resources.read_paths
    unrelated_binder = "scripts/creative_field_validation.py" if stage == "art" else "scripts/art_content_validation.py"
    assert ROOT / unrelated_binder not in resources.read_paths


@pytest.mark.parametrize("stage", ["characters", "art"])
def test_primary_literal_binders_without_literal_context_do_not_grant_policy_hash_files(stage):
    artifacts = {}
    if stage == "characters":
        from plotloom.creative_field_ownership import OWNERSHIP_FILENAME
        artifacts[OWNERSHIP_FILENAME] = {}
    else:
        from plotloom.art_structure import ART_STRUCTURE_FILENAME, art_structure_artifact
        artifacts["art-style-contract.json"] = {"style": "frozen-style"}
        artifacts[ART_STRUCTURE_FILENAME] = art_structure_artifact(preset=True)
    request = dict(stage=stage, upstreamSkillPath=upstream_skill_path_for_stage(stage),
        executionPin=_pin(stage), inputArtifacts=artifacts,
        contentValidationContract="plotloom.typed-content-result.v1")
    resources = codex_exec_source_resources(ROOT, request)
    policy_files = tuple(ROOT / f"third_party/shuohao-skills/skills/{skill}/scripts/provider-literals.mjs"
        for skill in ("novel-art", "novel-characters", "novel-storyboard"))

    assert not set(policy_files) & set(resources.read_paths)
    binder = "scripts/art_content_validation.py" if stage == "art" else "scripts/creative_field_validation.py"
    assert ROOT / binder in resources.read_paths


@pytest.mark.parametrize('saved',[False,True])
def test_new_f5_literals_bind_checked_python_node_and_context_helper(saved):
    from tests.test_codex_exec_validation import _request, _saved_brief_artifacts
    artifacts=_saved_brief_artifacts('storyboard') if saved else {
        'script.json':{'episodes':[]},'outline.json':{'episodes':[]},
        'cast.json':{'characters':[]},'art.json':{'scenes':[]}}
    request=_request('storyboard',artifacts).model_dump(mode='json',by_alias=True)
    request.update(upstreamSkillPath=upstream_skill_path_for_stage('storyboard'),executionPin=_pin('storyboard'))
    resources=codex_exec_source_resources(ROOT,request)
    assert set(dict(resources.tools))=={'uv','python','node'}
    assert resources.python_environment is not None
    assert ROOT/'src' in resources.read_paths
    assert ROOT/'scripts/creative_field_validation.py' in resources.read_paths
    assert ROOT/'scripts/provider-literal-context.mjs' in resources.read_paths
    # The literal helper is inside the pinned stage directory, never another stage.
    assert ROOT/'third_party/shuohao-skills/skills/novel-storyboard' in resources.read_paths
