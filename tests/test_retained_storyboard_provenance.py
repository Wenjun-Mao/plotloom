"""Passive frozen proof must not acquire today's execution authority."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from plotloom.codex_exec_retained_storyboard import retained_storyboard_package_projection
from plotloom.codex_exec_validation import build_text_validation_plan, validation_plan_from_package
from plotloom.creative_execution_pin import execution_pin_for_request
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_handoff_identity import canonical_json
from plotloom.creative_package_projection import project_creative_package
from plotloom.persistence.project.autopilot_bindings import (
    _current_checkpoint_validation_plan, _retained_checkpoint_validation_plan,
)
from plotloom.project_storage.creative_evidence_inventory import _retained_codex_request_projection
from plotloom.production_dialogue_timing import TIMING_FILENAME
from tests.codex_exec_fixtures import PROFILE
from tests.retained_storyboard_fixtures import PIN, REVISION, STYLE, replace_style, seal, storyboard_request


@pytest.mark.parametrize("typed", [False, True])
def test_current_frozen_storyboard_projection_preserves_exact_plan_and_package(tmp_path, typed):
    request = storyboard_request(typed=typed)
    expected, *_ = project_creative_package(tmp_path / request.job_id, request, PIN,
        executor_backend="codex_exec", plotloom_code_revision=REVISION)
    actual = retained_storyboard_package_projection(request, PIN, source_revision=REVISION)
    assert actual == expected
    assert validation_plan_from_package(actual).plan_hash == actual["validationPlanHash"]
    assert _retained_checkpoint_validation_plan(request, execution_pin=PIN,
        source_revision=REVISION) == build_text_validation_plan(request, execution_pin=PIN, source_revision=REVISION)


@pytest.mark.parametrize("typed", [False, True])
def test_historical_hashes_remain_literal_and_never_grant_fresh_execution(tmp_path, typed):
    request = storyboard_request(typed=typed, historical=True)
    before = canonical_json(request.model_dump(mode="json", by_alias=True))
    projected = retained_storyboard_package_projection(request, PIN, source_revision=REVISION)
    assert canonical_json(request.model_dump(mode="json", by_alias=True)) == before
    assert projected["inputArtifacts"] == request.input_artifacts
    steps = projected["validationPlan"]["steps"]
    assert steps[1]["argv"] == ["{source}/scripts/brief-storyboard-style.mjs", "render",
        "{candidate}", "--request", "{package}/request.json"]
    assert steps[0]["argv"] == (["{source}/scripts/storyboard-content-validation.mjs",
        "{candidate}", "{package}/request.json"] if typed else [
        "{source}/scripts/brief-storyboard-style.mjs", "validate", "{candidate}",
        "--request", "{package}/request.json"])
    assert ("contentValidationContract" in projected) is typed
    assert _retained_checkpoint_validation_plan(request, execution_pin=PIN,
        source_revision=REVISION).plan_hash == projected["validationPlanHash"]
    assert _retained_codex_request_projection(request, PIN, PROFILE, tmp_path / "absent",
        plotloom_code_revision=REVISION) == projected
    for fresh in (build_text_validation_plan, _current_checkpoint_validation_plan):
        with pytest.raises(ValueError, match="visual authority differs"):
            fresh(request, execution_pin=PIN, source_revision=REVISION)
    with pytest.raises(ValueError, match="visual authority differs"):
        validation_plan_from_package(projected)


def test_retained_projection_needs_no_package_checkout_or_filesystem_reads(tmp_path):
    request = storyboard_request(historical=True)
    def forbidden(*args, **kwargs):
        raise AssertionError("retained projection must be filesystem independent")
    with patch.object(Path, "read_bytes", forbidden), patch("subprocess.run", forbidden):
        projected = _retained_codex_request_projection(request, PIN, PROFILE, tmp_path / "missing",
            plotloom_code_revision=REVISION)
        assert projected["executionPin"] == execution_pin_for_request(request, PIN)
        assert projected["validationPlan"]["sourceRevision"] == REVISION


def corrupt(contract, mutation):
    if mutation == "missing":
        return None
    if mutation == "extra":
        contract["unowned"] = "no new authority"
    elif mutation in {"authority", "version", "stageInstructionContract", "contentHash"}:
        contract[mutation] = "unsupported"
    elif mutation == "missing_direction":
        contract.pop("direction")
    elif mutation == "direction":
        contract["direction"] = "rebound direction"
        seal(contract)
    elif mutation == "emptyRule":
        contract["emptyDirectionRule"] = "rebound rule"
        seal(contract)
    elif mutation.startswith("hash_"):
        hashes = contract["validatorHashes"]
        if mutation == "hash_missing":
            hashes.pop("adapter")
        elif mutation == "hash_extra":
            hashes["foreign"] = "a" * 64
        else:
            hashes["adapter"] = "not-a-hash"
        seal(contract)
    else:
        parent = contract["inheritedArtRenderContract"]
        if mutation == "parent_missing":
            contract.pop("inheritedArtRenderContract")
        elif mutation == "parent_extra":
            parent["unowned"] = "no new authority"
            seal(parent)
        elif mutation == "parent_direction":
            parent["direction"] = []
            seal(parent)
        elif mutation == "parent_hash":
            parent["contentHash"] = "a" * 64
        elif mutation == "parent_version":
            parent["version"] = True
            seal(parent)
        elif mutation == "parent_authority":
            parent["authority"] = "preset"
            seal(parent)
        elif mutation == "parent_inventory":
            parent["validatorHashes"].pop("castAdapter")
            seal(parent)
        seal(contract)
    return contract


@pytest.mark.parametrize("mutation", ["missing", "extra", "authority", "version", "stageInstructionContract",
    "contentHash", "missing_direction", "direction", "emptyRule", "hash_missing", "hash_extra", "hash_invalid",
    "parent_missing", "parent_extra", "parent_direction", "parent_hash", "parent_version", "parent_authority",
    "parent_inventory"])
def test_passive_style_tampering_is_refused_without_normalization(mutation):
    request = storyboard_request(historical=True)
    value = corrupt(deepcopy(request.input_artifacts[STYLE]), mutation)
    changed = replace_style(request, value)
    with pytest.raises((TypeError, ValueError), match="retained Storyboard"):
        retained_storyboard_package_projection(changed, PIN, source_revision=REVISION)


@pytest.mark.parametrize("typed", [False, True])
def test_resealed_historical_hash_change_changes_bound_request_and_plan(typed):
    request = storyboard_request(typed=typed, historical=True)
    original = retained_storyboard_package_projection(request, PIN, source_revision=REVISION)
    style = deepcopy(request.input_artifacts[STYLE])
    style["validatorHashes"]["adapter"] = "a" * 64
    seal(style)
    changed = retained_storyboard_package_projection(replace_style(request, style), PIN, source_revision=REVISION)
    assert changed["requestHash"] != original["requestHash"]
    assert changed["validationPlanHash"] != original["validationPlanHash"]


@pytest.mark.parametrize("revision", [None, "current", "A" * 40, "a" * 65])
def test_retained_plan_refuses_invalid_source_revision(revision):
    with pytest.raises(ValueError, match="frozen source revision"):
        retained_storyboard_package_projection(storyboard_request(), PIN, source_revision=revision)


def test_retained_plan_refuses_wrong_stage_pin_and_content_contract():
    request = storyboard_request()
    with pytest.raises(ValueError, match="Storyboard request"):
        retained_storyboard_package_projection(request.model_copy(update={"stage": "art"}), PIN,
            source_revision=REVISION)
    with pytest.raises(CreativeHandoffError):
        retained_storyboard_package_projection(request, PIN | {"extra": "no"}, source_revision=REVISION)
    with pytest.raises(ValueError, match="content boundary"):
        retained_storyboard_package_projection(request.model_copy(update={"content_validation_contract": "unknown"}),
            PIN, source_revision=REVISION)


@pytest.mark.parametrize("value", [None, {}, {"contentHash": "a" * 64}])
def test_retained_plan_keeps_frozen_timing_shape_and_hash_guards(value):
    request = storyboard_request()
    artifacts = deepcopy(request.input_artifacts)
    if value is None:
        artifacts.pop(TIMING_FILENAME)
    else:
        artifacts[TIMING_FILENAME] = value
    with pytest.raises(ValueError):
        retained_storyboard_package_projection(request.model_copy(update={"input_artifacts": artifacts}),
            PIN, source_revision=REVISION)
