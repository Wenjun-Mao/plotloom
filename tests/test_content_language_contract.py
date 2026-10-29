"""Semantic result trust and complete eight-stage language ownership regression."""
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.content_language_classifier import (
    STAGES,
    string_leaves,
)
from plotloom.content_language_contract import (
    CHECK_INPUT,
    bind_language_result,
    freeze_language_candidate,
    render_language_report,
)
from plotloom.creative_package_projection import project_creative_package
from plotloom.language_policy import freeze_request_language
from plotloom.text_correction_contracts import TextContentIssue
from tests.content_language_fixtures import (
    checking_request,
    original_request,
    result_for,
)
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION

CANDIDATES = {
    "outline": {"lang": "zh", "source": "The Ferry", "adaptation": {"core": "Wrong ordinary English prose."}},
    "branches": {"lang": "zh", "nodes": [{"id": "start", "title": "Ordinary English title", "summary": "Wrong prose."}]},
    "characters": {"lang": "zh", "characters": [{"id": "C01", "name": "Mara", "oneLiner": "Wrong prose.",
        "image": {"description": "身着旧雨衣的年轻守灯人。", "prompt": "A young lighthouse keeper."},
        "reviewNotes": {"sourceNotes": "Wrong note.", "performanceGuidance": ""}}]},
    "art": {"lang": "zh", "scenes": [{"id": "S01", "summary": "Wrong prose.",
        "image": {"description": "空旷的灯塔。", "prompt": "A deserted lighthouse at dawn."}}]},
    "script": {"lang": "zh", "episodes": [{"scenes": [{"flow": [{"speaker": "C01", "line": "Wrong ordinary English."}]}]}]},
    "storyboard": {"lang": "zh", "episodes": [{"segments": [{"id": "E01-01", "cuts": [{"composition": "Wrong prose.",
        "frame": "Wide shot of a deserted lighthouse.", "size": "wide", "camera": "Static Shot"}]}]}]},
    "bridge-intent": {"lang": "zh", "entries": [{"id": "scene:opening", "suggestedText": "Wrong prose."}]},
    "bridge-presentation": {"lang": "zh", "entries": [{"id": "action:opening", "spans": [{"start": 0, "end": 3,
        "role": "physical", "rendering": "Wrong prose.", "reason": "Wrong explanation."}]}]},
}


@pytest.mark.parametrize("stage", STAGES)
def test_correct_lang_metadata_cannot_replace_semantic_review(stage):
    original = original_request(stage)
    candidate = CANDIDATES[stage]
    request = checking_request(original, candidate)
    inventory = request.input_artifacts[CHECK_INPUT]["inventory"]
    path = next(item["path"] for item in inventory if item["role"] == "authored_prose")
    result = result_for(request, rejected_path=path)
    assert bind_language_result(request, result).verdict == "reject"
    assert bind_language_result(request, result).coverage[0].path == inventory[0]["path"]
    assert "助手语义检查" in render_language_report(request, result).decode()


@pytest.mark.parametrize("stage", STAGES)
def test_checker_plan_and_package_use_original_stage_but_deterministic_checker_only(stage, tmp_path):
    original = original_request(stage)
    request = checking_request(original, CANDIDATES[stage])
    plan = build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    assert plan.stage == stage and plan.route == "plotloom_native"
    assert all("{source}/scripts/content_language.py" in step.argv for step in plan.steps)
    assert all(step.program == "uv" for step in plan.steps)
    package, instructions, _template, _members = project_creative_package(tmp_path, request, PIN,
        executor_backend="codex_exec", plotloom_code_revision=SOURCE_REVISION)
    assert package["stage"] == original.stage
    assert package["source"]["operation"] == "content-language-check"
    assert "primary-stage" in instructions.decode()
    assert request.text_correction is None and request.content_validation_contract is None


@pytest.mark.parametrize("tamper", ["omit", "duplicate", "order", "hash", "role", "span", "flag"])
def test_incomplete_or_forged_semantic_results_fail_closed(tamper):
    request = checking_request(original_request(), CANDIDATES["outline"])
    result = result_for(request, rejected_path="$.adaptation.core")
    if tamper == "omit": result["coverage"].pop()
    elif tamper == "duplicate": result["coverage"][-1] = deepcopy(result["coverage"][0])
    elif tamper == "order": result["coverage"].reverse()
    elif tamper == "hash": result["coverage"][0]["sha256"] = "0" * 64
    elif tamper == "role": result["coverage"][0]["role"] = "provider_technical"
    elif tamper == "span": result["findings"][0]["span"]["text"] = "forged"
    else: result["checked"] = True
    with pytest.raises(ValueError): bind_language_result(request, result)


@pytest.mark.parametrize("stage", STAGES)
def test_unknown_nonempty_field_is_never_silently_exempt(stage):
    candidate = deepcopy(CANDIDATES[stage]) | {"plausibleEnglishMetadata": "But this is actually creative prose."}
    original = original_request(stage)
    if stage == "bridge-presentation":
        from plotloom.content_language_classifier import (
            classify_candidate,
            original_sources,
        )
        field = next(item for item in classify_candidate(stage, candidate, original_sources(original), original=original)
                     if item["path"] == "$.plausibleEnglishMetadata")
        assert field["role"] == "authored_prose"
        # The current closed presentation schema refuses this field before
        # deriving any source-slice witness; it never receives an exemption.
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            checking_request(original, candidate)
        return
    request = checking_request(original, candidate)
    field = next(item for item in request.input_artifacts[CHECK_INPUT]["inventory"]
                 if item["path"] == "$.plausibleEnglishMetadata")
    assert field["role"] == "authored_prose"
    assert bind_language_result(request, result_for(request, rejected_path=field["path"])).verdict == "reject"
    forged = result_for(request)
    next(item for item in forged["coverage"] if item["path"] == field["path"])["verdict"] = "not_applicable"
    with pytest.raises(ValueError, match="semantic language review"):
        bind_language_result(request, forged)


def test_source_name_quote_and_technical_english_have_explicit_separate_owners():
    original = original_request("characters")
    candidate = {"lang": "zh", "source": "The Ferry", "characters": [{"name": "Mara",
        "persona": {"evidence": ['Keep the light on.']}, "oneLiner": "Mara守着灯塔。",
        "image": {"prompt": "A close portrait of a lighthouse keeper.", "description": "穿雨衣的守灯人。"}}]}
    request = checking_request(original, candidate)
    roles = {item["path"]: item["role"] for item in request.input_artifacts[CHECK_INPUT]["inventory"]}
    assert roles["$.characters[0].name"] == "authored_prose"
    assert roles["$.characters[0].persona.evidence[0]"] == "exact_source"
    assert roles["$.characters[0].image.prompt"] == "provider_technical"
    result = result_for(request)
    field = next(item for item in result["coverage"] if item["path"] == "$.characters[0].oneLiner")
    field["exceptions"] = [{"kind": "proper_name", "candidateSpan": {"path": field["path"], "start": 0, "end": 4, "text": "Mara"},
        "sourceSpan": {"path": "$.source.text", "start": 0, "end": 4, "text": "Mara"}}]
    name = next(item for item in result["coverage"] if item["path"] == "$.characters[0].name")
    name["exceptions"] = [{"kind": "proper_name", "candidateSpan": {"path": name["path"], "start": 0, "end": 4, "text": "Mara"},
        "sourceSpan": {"path": "$.source.text", "start": 0, "end": 4, "text": "Mara"}}]
    assert bind_language_result(request, result).verdict == "pass"
    field["exceptions"][0]["sourceSpan"]["text"] = "invented"
    with pytest.raises(ValueError, match="exact Unicode"):
        bind_language_result(request, result)


def test_accidental_source_substring_cannot_exempt_an_english_scene_name():
    original = original_request()
    original.source["text"] = "Mara enters the room."
    request = checking_request(original, {"lang": "zh", "scenes": [{"id": "S01", "name": "room"}]})
    field = next(item for item in request.input_artifacts[CHECK_INPUT]["inventory"] if item["path"].endswith(".name"))
    assert field["role"] == "authored_prose" and "sourceSpan" not in field
    assert bind_language_result(request, result_for(request, rejected_path=field["path"])).verdict == "reject"


def test_any_source_candidate_locale_or_generation_setting_change_invalidates_but_ui_is_absent():
    original = original_request()
    candidate = CANDIDATES["outline"]
    first = freeze_language_candidate(original, candidate)
    assert first == freeze_language_candidate(original, deepcopy(candidate))
    changed = original.model_copy(deep=True)
    changed.source["text"] += " A new source fact."
    assert freeze_language_candidate(changed, candidate)["bindingHash"] != first["bindingHash"]
    changed = original.model_copy(deep=True)
    changed.input_artifacts["settings.json"] = {"variation": "restrained"}
    assert freeze_language_candidate(changed, candidate)["bindingHash"] != first["bindingHash"]
    changed = original.model_copy(deep=True)
    freeze_request_language(changed, "en-US")
    assert freeze_language_candidate(changed, candidate | {"lang": "en"})["bindingHash"] != first["bindingHash"]
    assert "applicationLocale" not in json.dumps(first)


def test_language_repair_facts_have_no_model_authored_instructions():
    issue = TextContentIssue(code="content_language_mismatch", field_paths=("$.entries[0].suggestedText",),
                             repair_facts={"contentLocale": "en-US"})
    assert issue.repair_facts == {"contentLocale": "en-US"}
    with pytest.raises(ValueError):
        TextContentIssue(code="content_language_mismatch", field_paths=issue.field_paths,
                         repair_facts={"contentLocale": "en-US", "instruction": "trust the writer"})


@pytest.mark.parametrize("operation", ["draft", "fidelity-check"])
def test_video_technical_results_do_not_require_creative_candidate_lang(operation, tmp_path):
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from plotloom.creative_handoff_identity import canonical_json
    request = original_request("video-directions")
    request.source = {"operation": operation}
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    paths = exchange.write_package(request, PIN)
    package, delivery = Path(paths["packagePath"]), Path(paths["deliveryPath"])
    delivery.mkdir()
    raw, report = canonical_json({"targets": []}), b"<!doctype html><title>technical fixture</title>"
    (delivery / "directions.json").write_bytes(raw)
    (delivery / "report.html").write_bytes(report)
    manifest = json.loads((package / "completion-manifest.example.json").read_bytes())
    manifest["deliveryId"] = "technical-result-fixture"
    manifest["candidate"]["sha256"], manifest["report"]["sha256"] = sha256(raw).hexdigest(), sha256(report).hexdigest()
    manifest["executorProvenance"]["codeRevision"] = PIN["upstreamRevision"]
    (delivery / "completion.json").write_bytes(canonical_json(manifest))
    result = exchange.read_delivery(request, PIN)
    assert result.candidate == {"targets": []}
    assert request.input_artifacts["language-contract.json"]["reportLocale"] == "zh"


def test_unowned_nested_prose_stays_semantically_reviewed():
    candidate = CANDIDATES["outline"] | {
        "additionalNotes": {"description": "Wrong ordinary English route description.",
                            "routes": [{"name": "留在桌上"}]},
    }
    request = checking_request(original_request(), candidate)
    inventory = request.input_artifacts[CHECK_INPUT]["inventory"]
    assert len(inventory) == len(dict(string_leaves(candidate)))
    assert all(item["role"] == "authored_prose" for item in inventory
               if item["path"].startswith("$.additionalNotes."))
    assert bind_language_result(request, result_for(request,
        rejected_path="$.additionalNotes.description")).verdict == "reject"
