"""Retained wire proof stays readable; current execution never replays old contracts."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from plotloom.codex_exec_validation import build_text_validation_plan
from plotloom.creative_handoff_identity import canonical_json
from plotloom.script_dialogue_compatibility import PlannedStoryboardDialogue, assert_current_planned_dialogue, freeze_planned_storyboard_dialogue
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION, _request, _saved_brief_artifacts

ROOT = Path(__file__).resolve().parents[1]


def old_planned():
    profile = {"version": "dialogue.default.v1", "rules": [
        {"language": "zh-CN", "delivery": "natural", "unitsPerCharacter": 330},
        {"language": "*", "delivery": "natural", "unitsPerCharacter": 70}]}
    return {"version": "plotloom.planned-storyboard-dialogue.v1", "maxCutSeconds": 8, "language": "zh-CN",
        "profile": profile, "profileHash": sha256(canonical_json(profile)).hexdigest(),
        "normalizationVersion": "plotloom.f4-dialogue-normalization.v1"}


def test_retained_planned_profile_omission_and_binding_hash_are_unchanged():
    from plotloom.script_contracts import ScriptBinding
    from plotloom.authored_route_timing import route_budget_hash
    from plotloom.language_policy import language_contract
    raw = old_planned()
    parsed = PlannedStoryboardDialogue.model_validate_json(json.dumps(raw))
    assert parsed.model_dump(mode="json", by_alias=True) == raw
    sections = [{"sectionId": "opening", "episode": 1}]
    value = {"sourceRevision": 1, "sourceContentHash": "a"*64, "outlineRevision": 1, "outlineContentHash": "b"*64,
        "graphRevision": 1, "graphContentHash": "e"*64, "sectionMapRevision": 1, "sectionMapContentHash": "f"*64, "sectionIds": ["opening"], "castRevision": 1, "castContentHash": "c"*64,
        "artRevision": 1, "artContentHash": "d"*64, "targetPlaythroughSeconds": 10,
        "sectionBindings": sections, "completeRouteSectionIds": [["opening"]], "routeOnlySectionIds": [],
        "routeBudgetHash": route_budget_hash(target_seconds=10, section_bindings=sections, routes=[["opening"]], route_only_ids=[]),
        "plannedStoryboardDialogue": raw, "languageContract": language_contract("zh-CN")}
    binding = ScriptBinding.model_validate_json(json.dumps(value))
    assert binding.model_dump(mode="json", by_alias=True)["plannedStoryboardDialogue"] == raw
    with pytest.raises(ValueError, match="profile or normalization changed"):
        assert_current_planned_dialogue(parsed)
    current = freeze_planned_storyboard_dialogue(max_cut_seconds=8, language="zh-CN")
    assert_current_planned_dialogue(current)
    assert PlannedStoryboardDialogue.model_validate_json(current.model_dump_json(by_alias=True)) == current
    changed = deepcopy(raw); changed["profile"]["rules"][0]["unitsPerCharacter"] += 1
    with pytest.raises(ValueError, match="profile identity"):
        PlannedStoryboardDialogue.model_validate(changed)


def test_retained_script_plan_reads_old_frozen_profile_but_new_plan_refuses():
    from plotloom.codex_exec_retained_script import retained_script_package_projection
    from plotloom.persistence.project.autopilot_bindings import _retained_checkpoint_validation_plan
    from plotloom.project_storage.creative_evidence_inventory import _retained_codex_request_projection
    from tests.codex_exec_fixtures import PROFILE
    request = _request("script", {"script-admission.json": {"plannedStoryboardDialogue": old_planned()}})
    projected = retained_script_package_projection(request, PIN, source_revision=SOURCE_REVISION)
    plan = _retained_checkpoint_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    assert plan.model_dump(mode="json", by_alias=True) == projected["validationPlan"]
    assert _retained_codex_request_projection(request, PIN, PROFILE, ROOT, plotloom_code_revision=SOURCE_REVISION) == projected
    assert all(step["program"] == "uv" for step in projected["validationPlan"]["steps"])
    with pytest.raises(ValueError, match="profile or normalization changed"):
        build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)


@pytest.mark.parametrize("saved", [True, False])
def test_original_art_v1_shape_projection_is_passive_and_does_not_gain_new_schema(saved):
    from plotloom.art_structure import ART_STRUCTURE_FILENAME, art_structure_artifact
    from plotloom.art_style import freeze_art_style
    from plotloom.codex_exec_retained_visual import retained_visual_package_projection
    from plotloom.persistence.project.autopilot_bindings import _retained_checkpoint_validation_plan
    from plotloom.project_storage.creative_evidence_inventory import _retained_codex_request_projection
    from tests.codex_exec_fixtures import PROFILE
    route = "saved_brief" if saved else "preset_style"
    shape = json.loads((ROOT/"tests/fixtures/art-structure-v1.json").read_text())[route]
    style = _saved_brief_artifacts("art")["art-style-contract.json"] if saved else freeze_art_style("realistic", None)
    request = _request("art", {"cast.json": {"characters": []}, "art-style-contract.json": style,
        ART_STRUCTURE_FILENAME: art_structure_artifact(preset=not saved)})
    request.content_validation_contract = "plotloom.typed-content-result.v1"
    # Capture today's current wire plan, then restore the exact original inputs.
    current_plan = build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    request.input_artifacts[ART_STRUCTURE_FILENAME] = shape
    projected = retained_visual_package_projection(request, PIN, source_revision=SOURCE_REVISION)
    assert projected["inputArtifacts"][ART_STRUCTURE_FILENAME] == shape
    assert projected["validationPlan"]["steps"] == current_plan.model_dump(mode="json", by_alias=True)["steps"]
    assert _retained_checkpoint_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION).plan_hash == projected["validationPlanHash"]
    assert _retained_codex_request_projection(request, PIN, PROFILE, ROOT, plotloom_code_revision=SOURCE_REVISION) == projected
    with pytest.raises(ValueError, match="structural marker"):
        build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    request.input_artifacts[ART_STRUCTURE_FILENAME]["schema"]["extra"] = True
    with pytest.raises(ValueError, match="Art shape differs"):
        retained_visual_package_projection(request, PIN, source_revision=SOURCE_REVISION)


@pytest.mark.parametrize("stage", ["characters", "art"])
def test_retained_saved_brief_integrity_uses_recorded_hashes_while_new_execution_requires_current(stage):
    from plotloom.creative_field_ownership import OWNERSHIP_FILENAME
    from plotloom.codex_exec_retained_visual import retained_visual_package_projection
    from plotloom.persistence.project.autopilot_bindings import _retained_checkpoint_validation_plan
    request = _request(stage, _saved_brief_artifacts(stage))
    request.content_validation_contract = "plotloom.typed-content-result.v1"
    request.input_artifacts.pop(OWNERSHIP_FILENAME, None)  # Original pre-owner package representation.
    contract = request.input_artifacts[("cast" if stage == "characters" else "art") + "-style-contract.json"]
    current = build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    contract["validatorHashes"]["policy"] = "e"*64
    contract["contentHash"] = sha256(canonical_json({k:v for k,v in contract.items() if k != "contentHash"})).hexdigest()
    projected = retained_visual_package_projection(request, PIN, source_revision=SOURCE_REVISION)
    assert projected["validationPlan"]["steps"] == current.model_dump(mode="json", by_alias=True)["steps"]
    assert _retained_checkpoint_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION).plan_hash == projected["validationPlanHash"]
    with pytest.raises(ValueError, match="differs from its source contract"):
        build_text_validation_plan(request, execution_pin=PIN, source_revision=SOURCE_REVISION)
    contract["direction"] += " mutated"
    with pytest.raises(ValueError, match="integrity differs"):
        retained_visual_package_projection(request, PIN, source_revision=SOURCE_REVISION)
