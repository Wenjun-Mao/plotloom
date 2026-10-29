"""Primary/receiver/resource agreement and passive evidence preservation."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from plotloom.content_language_classifier import classify_candidate, original_sources, string_leaves
from plotloom.content_language_contract import CHECK_INPUT, bind_language_result
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.creative_handoff_identity import canonical_json
from plotloom.language_policy import freeze_request_language
from tests.content_language_fixtures import checking_request, original_request, result_for
from tests.test_content_language_contract import CANDIDATES
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION

ROOT = Path(__file__).resolve().parents[1]

_EXPECTED = {
    "outline": {"$.lang": "stable_identity", "$.source": "exact_source", "$.adaptation.core": "authored_prose"},
    "branches": {"$.lang": "stable_identity", "$.nodes[0].id": "stable_identity", "$.nodes[0].title": "authored_prose", "$.nodes[0].summary": "authored_prose"},
    "characters": {"$.lang": "stable_identity", "$.characters[0].id": "stable_identity", "$.characters[0].name": "authored_prose",
        "$.characters[0].oneLiner": "authored_prose", "$.characters[0].image.description": "authored_prose", "$.characters[0].image.prompt": "provider_technical",
        "$.characters[0].reviewNotes.sourceNotes": "authored_prose", "$.characters[0].reviewNotes.performanceGuidance": "authored_prose"},
    "art": {"$.lang": "stable_identity", "$.scenes[0].id": "stable_identity", "$.scenes[0].summary": "authored_prose",
        "$.scenes[0].image.description": "authored_prose", "$.scenes[0].image.prompt": "provider_technical"},
    "script": {"$.lang": "stable_identity", "$.episodes[0].scenes[0].flow[0].speaker": "stable_identity", "$.episodes[0].scenes[0].flow[0].line": "authored_prose"},
    "storyboard": {"$.lang": "stable_identity", "$.episodes[0].segments[0].id": "stable_identity", "$.episodes[0].segments[0].cuts[0].composition": "authored_prose",
        "$.episodes[0].segments[0].cuts[0].frame": "provider_technical", "$.episodes[0].segments[0].cuts[0].size": "stable_identity", "$.episodes[0].segments[0].cuts[0].camera": "stable_identity"},
    "bridge-intent": {"$.lang": "stable_identity", "$.entries[0].id": "stable_identity", "$.entries[0].suggestedText": "authored_prose"},
    "bridge-presentation": {"$.lang": "stable_identity", "$.entries[0].id": "stable_identity", "$.entries[0].spans[0].role": "stable_identity",
        "$.entries[0].spans[0].rendering": "authored_prose", "$.entries[0].spans[0].reason": "authored_prose"},
}


@pytest.mark.parametrize("stage", tuple(_EXPECTED))
def test_complete_representative_role_inventory_for_each_stage(stage):
    original, candidate = original_request(stage), CANDIDATES[stage]
    inventory = classify_candidate(stage, candidate, original_sources(original), original=original)
    assert {item["path"]: item["role"] for item in inventory} == _EXPECTED[stage]
    assert len(inventory) == len(dict(string_leaves(candidate)))


@pytest.mark.parametrize("saved", [True, False])
@pytest.mark.parametrize("subject,array", [("scenes", "lighting"), ("scenes", "states"), ("props", "lighting"), ("props", "states")])
def test_art_schema_primary_and_language_binder_require_state_descriptions(tmp_path, saved, subject, array):
    from tests.art_structure_fixtures import art_case, run_art
    from plotloom.art_structure import art_structure_issues
    request, candidate = art_case(tmp_path, saved=saved)
    if subject == "props" and not candidate.get("props"):
        candidate["props"] = [deepcopy(candidate["scenes"][0])]
        candidate["props"][0].update(id="P01", scale="handheld", states=deepcopy(candidate["scenes"][0]["lighting"]))
    candidate[subject][0][array] = [{"state": "夜色", "prompt": "cold night light"}]
    path = f"$.{subject}[0].{array}[0].description"
    assert any(path in item for item in art_structure_issues(candidate, preset=not saved))
    assert run_art(tmp_path, request, candidate).returncode == 42
    with pytest.raises(ValueError, match="description"):
        checking_request(request, candidate)
    schema = request.input_artifacts["art-structure-schema.json"]["schema"]
    assert "description" in schema["$defs"]["_State"]["required"]
    candidate[subject][0][array][0]["description"] = " "
    assert any(path in item for item in art_structure_issues(candidate, preset=not saved))


def test_marked_cast_primary_plan_resources_and_valid_native_renderer_agree(tmp_path):
    from tests.test_codex_exec_stage_routing import _saved_brief_example
    from plotloom.codex_exec_validation import validation_plan_from_package
    from plotloom.codex_exec_resources import codex_exec_source_resources
    request, candidate, _ = _saved_brief_example("characters")
    request.content_validation_contract = "plotloom.typed-content-result.v1"
    freeze_request_language(request, "zh-CN"); candidate["lang"] = "zh"
    exchange = CreativeHandoffExchange(tmp_path / "exchange"); pin = exchange.current_execution_pin("characters")
    paths = exchange.write_package(request, pin, executor_backend="codex_exec", plotloom_code_revision=SOURCE_REVISION)
    packet = json.loads((Path(paths["packagePath"])/"request.json").read_bytes())
    plan = validation_plan_from_package(packet)
    assert plan.steps[0].program == "uv" and plan.steps[0].argv[-2:] == ("--node", "{tool:node}")
    assert plan.steps[1].program == "node"
    resources = codex_exec_source_resources(ROOT, packet)
    assert {"uv", "python", "node"} <= dict(resources.tools).keys()
    assert ROOT / "scripts/creative_field_validation.py" in resources.read_paths
    candidate_path = tmp_path/"cast.json"; candidate_path.write_bytes(canonical_json(candidate))
    completed = subprocess.run([sys.executable, str(ROOT/"scripts/creative_field_validation.py"), str(candidate_path),
        "--request", str(Path(paths["packagePath"])/"request.json"), "--node", str(dict(resources.tools)["node"])], capture_output=True)
    assert completed.returncode == 0, completed.stderr + completed.stdout
    check = checking_request(request, candidate)
    assert bind_language_result(check, result_for(check)).verdict == "pass"


def test_final_receiver_refuses_text_locator_even_with_matching_report_and_manifest(tmp_path):
    from tests.creative_field_fixtures import cast_case
    request, candidate = cast_case()
    exchange = CreativeHandoffExchange(tmp_path/"exchange")
    paths = exchange.write_package(request, PIN)
    package, delivery = Path(paths["packagePath"]), Path(paths["deliveryPath"])
    delivery.mkdir(); candidate["characters"][0]["sheetImage"] = "https://example.com/unowned.png"
    raw, report = canonical_json(candidate), b"<!doctype html><title>Retained report bytes</title>"
    (delivery/"cast.json").write_bytes(raw); (delivery/"report.html").write_bytes(report)
    manifest = json.loads((package/"completion-manifest.example.json").read_bytes())
    manifest["deliveryId"] = "ownership-receiver-test"
    manifest["executorProvenance"]["codeRevision"] = SOURCE_REVISION
    manifest["candidate"]["sha256"], manifest["report"]["sha256"] = sha256(raw).hexdigest(), sha256(report).hexdigest()
    (delivery/"completion.json").write_bytes(canonical_json(manifest))
    with pytest.raises(ValueError, match="sheetImage"):
        exchange.read_delivery(request, PIN)
    assert (delivery/"report.html").read_bytes() == report


def test_old_semantic_rejection_is_readable_without_reclassifying_or_new_authority():
    from plotloom.content_language_contract import identity
    from tests.creative_field_fixtures import cast_case
    original, candidate = cast_case()
    check = checking_request(original, candidate)
    frozen = check.input_artifacts[CHECK_INPUT]
    frozen["classifierVersion"] = "plotloom.content-language-classifier.v3"
    frozen["sources"] = original_sources(original, ownership=False)
    from plotloom.provider_literal_discovery import DISCOVERY, discovery_inventory
    frozen[DISCOVERY] = discovery_inventory(frozen["sources"])
    frozen["bindingHash"] = identity({key:value for key,value in frozen.items() if key != "bindingHash"})
    check.source["bindingHash"] = frozen["bindingHash"]
    result = result_for(check, uncertain_path="$.notes")
    assert bind_language_result(check, result, require_current=False).verdict == "uncertain"
    with pytest.raises(ValueError): bind_language_result(check, result)
