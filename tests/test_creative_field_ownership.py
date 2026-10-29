"""Every exemption has a request-aware owner; prose never inherits metadata trust."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from plotloom.content_language_classifier import classify_candidate, original_sources
from plotloom.content_language_contract import bind_language_result, freeze_language_candidate
from plotloom.creative_field_ownership import CreativeFieldError, creative_field_roles, ownership_artifact
from tests.content_language_fixtures import checking_request, original_request, result_for
from tests.creative_field_fixtures import cast_case

ROOT = Path(__file__).resolve().parents[1]


def roles(request, candidate):
    return {item["path"]: item["role"] for item in classify_candidate(request.stage, candidate, original_sources(request), original=request)}


@pytest.mark.parametrize("locale", ["zh-CN", "en-US"])
@pytest.mark.parametrize("saved", [True, False])
def test_cast_image_style_exact_mode_owner(locale, saved):
    request, candidate = cast_case(saved=saved, locale=locale)
    schema = ownership_artifact(request)["schema"]
    assert schema["properties"]["characters"]["items"]["properties"]["image"]["properties"]["style"] == {"const": candidate["characters"][0]["image"]["style"]}
    assert roles(request, candidate)["$.characters[0].image.style"] == "stable_identity"
    assert roles(request, candidate)["$.characters[0].sectionPresence[0].context"] == "authored_prose"
    for wrong in ("已保存的简报方向", "Saved Brief Direction", "ordinary creative style prose"):
        candidate["characters"][0]["image"]["style"] = wrong
        with pytest.raises(CreativeFieldError, match="image.style"):
            freeze_language_candidate(request, candidate)


@pytest.mark.parametrize("saved", [True, False])
def test_art_both_subject_styles_and_cross_array_roles(saved):
    from plotloom.art_style import freeze_art_style
    request = original_request("art")
    contract = freeze_art_style("brief" if saved else "realistic", None)
    request.input_artifacts["art-style-contract.json"] = contract
    state = {"state": "夜色", "description": "灯光照出一道裂纹。", "prompt": "cold light on a visible crack"}
    candidate = {"lang": "zh", "scenes": [{"image": {"style": "Saved Brief direction" if saved else "温和的画风"},
        "lighting": [deepcopy(state)], "states": [deepcopy(state)]}],
        "props": [{"image": {"style": "Saved Brief direction" if saved else "保留材质细节"},
            "lighting": [deepcopy(state)], "states": [deepcopy(state)]}]}
    inventory = roles(request, candidate)
    for key in ("scenes", "props"):
        assert inventory[f"$.{key}[0].image.style"] == ("stable_identity" if saved else "authored_prose")
        for array in ("lighting", "states"):
            for field in ("state", "description", "prompt"):
                assert inventory[f"$.{key}[0].{array}[0].{field}"] == ("provider_technical" if field == "prompt" else "authored_prose")
        if saved:
            altered = deepcopy(candidate); altered[key][0]["image"]["style"] = "已保存的简报方向"
            with pytest.raises(CreativeFieldError): creative_field_roles(altered, request)


@pytest.mark.parametrize("selector", ["measured", "natural", "brisk", "brisk but regretful", "Brisk", "缓慢而压抑"])
def test_script_delivery_uses_only_actual_timing_owner_vocabulary(selector):
    request = original_request("script")
    candidate = {"lang": "zh", "episodes": [{"scenes": [{"flow": [{"delivery": selector, "line": "灯还亮着。"}]}]}]}
    from plotloom.dialogue_timing_policy import DialogueDeliveryPace
    expected = "stable_identity" if selector in {item.value for item in DialogueDeliveryPace} else "authored_prose"
    assert roles(request, candidate)["$.episodes[0].scenes[0].flow[0].delivery"] == expected


@pytest.mark.parametrize("mutation", ["hash", "authority", "direction", "contract", "extra-authority", "section-id", "order", "mode", "bool", "route-presence", "extra-section"])
def test_optional_echoes_are_exact_and_closed(mutation):
    request, candidate = cast_case()
    if mutation == "hash": candidate["styleAuthority"]["contentHash"] = "b"*64
    elif mutation == "authority": candidate["styleAuthority"]["authority"] = "saved-brief"
    elif mutation == "direction": candidate["styleAuthority"]["direction"] += "Wrong English addition"
    elif mutation == "contract": candidate["styleAuthority"]["stageInstructionContract"] = "other"
    elif mutation == "extra-authority": candidate["styleAuthority"]["prose"] = "unreviewed English prose"
    else:
        items = candidate["characters"][0]["sectionPresence"]
        if mutation == "section-id": items[0]["sectionId"] = "new"
        elif mutation == "order": items.reverse()
        elif mutation == "mode": items[0]["footageMode"] = "route_only"
        elif mutation == "bool": items[0]["present"] = 1
        elif mutation == "route-presence": items[1]["present"] = True
        elif mutation == "extra-section": items[0]["notes"] = "unreviewed English prose"
    with pytest.raises(CreativeFieldError): creative_field_roles(candidate, request)


def test_metadata_source_exposes_author_direction_only_and_never_exempts_notes():
    request, candidate = cast_case()
    frozen = freeze_language_candidate(request, candidate)
    assert frozen["sources"]["authorDirection"] == request.input_artifacts["cast-style-contract.json"]["direction"]
    assert "cast-style-contract_json" not in frozen["sources"]["inputs"]
    inventory = {item["path"]: item for item in frozen["inventory"]}
    assert inventory["$.styleAuthority.direction"]["role"] == "exact_source"
    assert inventory["$.styleAuthority.direction"]["sourceSpan"]["path"] == "$.authorDirection"
    assert inventory["$.notes"]["role"] == "authored_prose"
    assert inventory["$.characters[0].sectionPresence[0].context"]["role"] == "authored_prose"
    candidate["arbitraryMetadata"] = {"contentHash": "a"*64, "style": "Saved Brief direction"}
    assert roles(request, candidate)["$.arbitraryMetadata.contentHash"] == "authored_prose"
    # Optional echoes may be omitted; unrelated creative prose stays checked.
    candidate.pop("styleAuthority"); candidate["characters"][0].pop("sectionPresence")
    checking = checking_request(request, candidate)
    assert bind_language_result(checking, result_for(checking, rejected_path="$.notes")).verdict == "reject"


@pytest.mark.parametrize("stage,key", [("characters", "characters"), ("art", "scenes"), ("art", "props")])
@pytest.mark.parametrize("nested", [False, True])
def test_text_only_candidates_refuse_resource_locators(stage, key, nested):
    request = original_request(stage)
    subject = {"image": {"sheetImage": "file:///private/value"}} if nested else {"sheetImage": "https://example.com/sheet.png"}
    with pytest.raises(CreativeFieldError, match="omit resource locators"):
        creative_field_roles({key: [subject]}, request)


def test_source_bound_embedded_id_exception_keeps_surrounding_note_semantic():
    original, candidate = cast_case()
    request = checking_request(original, candidate)
    reply = result_for(request)
    note = next(item for item in reply["coverage"] if item["path"] == "$.notes")
    note["exceptions"] = [{"kind": "source_quote", "candidateSpan": {"path": "$.notes", "start": 0, "end": 3, "text": "C01"},
        "sourceSpan": {"path": "$.inputs.outline_json.characters[0].id", "start": 0, "end": 3, "text": "C01"}}]
    assert bind_language_result(request, reply).verdict == "pass"
    invalid = deepcopy(reply); note = next(item for item in invalid["coverage"] if item["path"] == "$.notes")
    note["exceptions"][0]["candidateSpan"]["end"] = len(candidate["notes"])
    note["exceptions"][0]["candidateSpan"]["text"] = candidate["notes"]
    with pytest.raises(ValueError): bind_language_result(request, invalid)
    candidate["notes"] = "C01 遵照 Brief 操作。"
    request = checking_request(original, candidate)
    assert bind_language_result(request, result_for(request, rejected_path="$.notes")).verdict == "reject"


def test_primary_ownership_rejection_preserves_typed_raw_hash_and_generic_paths(tmp_path):
    request, candidate = cast_case()
    candidate["styleAuthority"]["contentHash"] = "d"*64
    raw = json.dumps(candidate, ensure_ascii=False).encode()
    (tmp_path/"cast.json").write_bytes(raw); (tmp_path/"request.json").write_text(request.model_dump_json(by_alias=True))
    result = subprocess.run([sys.executable, str(ROOT/"scripts/creative_field_validation.py"), str(tmp_path/"cast.json"),
        "--request", str(tmp_path/"request.json"), "--node", shutil.which("node")], capture_output=True)
    assert result.returncode == 42, result.stderr
    packet = json.loads(result.stdout)
    assert packet["candidateHash"] == sha256(raw).hexdigest()
    assert packet["issues"] == [{"code": "candidate_content_invalid", "fieldPaths": ["$"], "repairFacts": {}}]
    assert "$.styleAuthority.contentHash" in packet["displayDiagnostics"][0]
    from plotloom.text_correction_contracts import TextContentIssue
    assert TextContentIssue.model_validate(packet["issues"][0]).field_paths == ("$",)


def test_new_ownership_dependency_bytes_invalidate_checker_policy(monkeypatch):
    request, candidate = cast_case()
    first = freeze_language_candidate(request, candidate)
    read = Path.read_bytes
    def changed(path):
        value = read(path)
        return value + b"\n# changed owner" if path.name == "creative_field_ownership.py" else value
    monkeypatch.setattr(Path, "read_bytes", changed)
    second = freeze_language_candidate(request, candidate)
    assert first["checkerPolicyHash"] != second["checkerPolicyHash"]
    assert first["bindingHash"] != second["bindingHash"]
