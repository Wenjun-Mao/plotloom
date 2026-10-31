"""Optional machine copies preserve their actual source identities before review."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from plotloom.brief_contracts import ProjectBrief
from plotloom.content_language_contract import CHECK_INPUT, bind_language_result
from plotloom.outline_echoes import ECHO_CONTRACT_FILENAME, OutlineEchoError, outline_echo_contract, outline_echo_roles
from plotloom.outline_settings import outline_settings
from plotloom.source_structures import planned_structure
from tests.content_language_fixtures import checking_request, original_request, result_for

ROOT = Path(__file__).resolve().parents[1]


def echo_fixture():
    request = original_request()
    request.source |= {"kind": "synopsis", "briefOrigin": {"kind": "saved_brief", "revision": 1,
                                                         "contentHash": "a" * 64}}
    brief = ProjectBrief(title="小灯", synopsis="她把灯留在桌上或带到窗边。", language="zh-CN",
                         nodeBudget=4, endingCount=2, decisionPointsPerPath=1, desiredJoinCount=0)
    settings = outline_settings(brief)
    topology = planned_structure(request.project_id, brief).model_dump(mode="json", by_alias=True)
    request.input_artifacts |= {ECHO_CONTRACT_FILENAME: outline_echo_contract(), "outline-settings.json": settings, "story-topology.json": topology}
    candidate = json.loads((ROOT / "third_party/shuohao-skills/skills/novel-outline/examples/current-zh.json").read_text())
    candidate["params"] |= {key: settings[key] for key in
                           ("language", "aspectRatio", "shotCountPolicy", "genreSelections", "visualStyleSelections")}
    candidate["sourceMetadata"] = deepcopy(request.source)
    candidate["sourceMetadata"].pop("text")
    candidate["storyTopology"] = deepcopy(topology)
    return request, candidate


def test_exact_echoes_exempt_only_their_bound_machine_or_source_leaves():
    original, candidate = echo_fixture()
    request = checking_request(original, candidate)
    roles = {item["path"]: item["role"] for item in request.input_artifacts[CHECK_INPUT]["inventory"]}
    assert roles["$.params.shotCountPolicy"] == "stable_identity"
    assert roles["$.storyTopology.nodes[0].kind"] == "stable_identity"
    assert roles["$.sourceMetadata.title"] == "exact_source"
    assert bind_language_result(request, result_for(request)).verdict == "pass"
    # Matching a frozen value at an unregistered location grants nothing.
    candidate["inventedSetting"] = original.input_artifacts["outline-settings.json"]["language"]
    request = checking_request(original, candidate)
    assert next(x for x in request.input_artifacts[CHECK_INPUT]["inventory"]
                if x["path"] == "$.inventedSetting")["role"] == "authored_prose"


@pytest.mark.parametrize("change,path", [
    ("enum", "$.params.shotCountPolicy"), ("hash", "$.storyTopology"),
    ("extra", "$.storyTopology"), ("metadata", "$.sourceMetadata.kind"),
    ("route_plan", "$.routePlan"),
])
def test_machine_mutations_reject_before_semantic_check_with_typed_primary_feedback(tmp_path, change, path):
    original, candidate = echo_fixture()
    if change == "enum": candidate["params"]["shotCountPolicy"] = "严格"
    elif change == "hash": candidate["storyTopology"]["topologyHash"] = "b" * 64
    elif change == "extra": candidate["storyTopology"]["readableEnglish"] = "unreviewed prose"
    elif change == "metadata": candidate["sourceMetadata"]["kind"] = "故事梗概"
    else: candidate["routePlan"] = {"decision": {"nodeId": "opaque-id"}, "sections": [], "routes": [{"edgeIds": ["opaque-edge"]}]}
    with pytest.raises(OutlineEchoError) as error:
        outline_echo_roles(candidate, original)
    assert error.value.path == path
    raw = json.dumps(candidate, ensure_ascii=False).encode()
    candidate_file, request_file = tmp_path / "candidate.json", tmp_path / "request.json"
    candidate_file.write_bytes(raw)
    request_file.write_text(original.model_dump_json(by_alias=True))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/outline_content_validation.py"),
        str(candidate_file), "--request", str(request_file), "--node", shutil.which("node")],
        capture_output=True, check=False)
    assert result.returncode == 42, result.stderr
    packet = json.loads(result.stdout)
    from plotloom.text_correction_contracts import TextContentIssue
    issues = [TextContentIssue.model_validate(issue) for issue in packet["issues"]]
    assert len(issues) == 1 and issues[0].code == "candidate_content_invalid"
    assert issues[0].field_paths == ("$",) and path in packet["displayDiagnostics"][0]


def test_current_outline_constraints_preserve_authored_content_and_structural_gate(tmp_path):
    original, candidate = echo_fixture()
    before = deepcopy(candidate)
    assert outline_echo_contract() == {"version": "plotloom.outline-input-echoes.v2",
        "candidateConstraints": {"forbiddenTopLevelFields": ["routePlan"]}}
    assert "routePlan" not in candidate
    outline_echo_roles(candidate, original)
    candidate_file, request_file = tmp_path / "outline.json", tmp_path / "request.json"
    candidate_file.write_text(json.dumps(candidate, ensure_ascii=False))
    request_file.write_text(original.model_dump_json(by_alias=True))
    result = subprocess.run([sys.executable, str(ROOT / "scripts/outline_content_validation.py"),
        str(candidate_file), "--request", str(request_file), "--node", shutil.which("node")],
        capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert candidate == before


def test_prepared_outline_prompt_and_schema_share_current_candidate_constraint():
    from types import SimpleNamespace
    from plotloom.outline_preparation import outline_request
    from plotloom.source_outline_contracts import SourceMaterial
    original, _ = echo_fixture()
    brief = ProjectBrief(title="小灯", synopsis="她把灯留下。", language="zh-CN")
    store = SimpleNamespace(
        manifest=SimpleNamespace(project_id=original.project_id),
        source_outline_state=lambda: SimpleNamespace(accepted_outline=None,
            source=SimpleNamespace(material=SourceMaterial(kind="synopsis", title=brief.title, text=brief.synopsis))),
        project=lambda: SimpleNamespace(require_brief=lambda: brief))
    request = outline_request(store)
    assert request.input_artifacts[ECHO_CONTRACT_FILENAME] == outline_echo_contract()
    assert request.input_artifacts["outline-report-metadata-schema.json"]["not"] == {"required": ["routePlan"]}
    assert "Omit routePlan entirely" in request.creative_brief
    assert "existing Outline fields" in request.creative_brief
    assert "Route-plan prose" not in request.creative_brief
