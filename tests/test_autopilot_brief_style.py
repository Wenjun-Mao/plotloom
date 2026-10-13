import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from plotloom.art_style import ArtPrepareRequest
from plotloom.autopilot_brief_style import (
    BRIEF_STAGE_INSTRUCTION_CONTRACT,
    BRIEF_STYLE_LABEL,
    EMPTY_DIRECTION,
    brief_stage_instructions,
    freeze_brief_style,
    image_style_guidance,
    validate_brief_style,
)
from plotloom.autopilot_contracts import LaunchPolicy, LaunchRequest
from plotloom.cast_style import CastPrepareRequest, validate_cast_style


def _policy(*, version="plotloom.pre-video.v3", authority="brief", direction=None):
    return LaunchPolicy.model_validate({
        "version": version, "styleAuthority": authority,
        "renderStyle": None if authority == "brief" else "ghibli",
        "artRenderStyle": None if authority == "brief" else "ghibli",
        "imageWidth": 1280, "imageHeight": 720, "maxImages": 80, "maxJobs": 96,
        "codeRevision": "a" * 40,
        "specialistBindings": {"text": "task-a", "image": "task-b"},
        "executionPins": {"existing": {"codeRevision": "frozen"}},
        "brief": {"visualStyle": direction},
    })


def test_brief_contract_preserves_source_direction_and_accepts_english_machine_fields():
    direction = "2D 动画；水彩；低饱和；保留纸张纹理细节"
    contract = freeze_brief_style(direction)
    payload = {"style": "saved-brief", "characters": [{"id": "hero", "image": {
        "style": BRIEF_STYLE_LABEL,
        "prompt": "2D animated character reference, watercolor wash, muted palette, preserve paper grain",
        "sheet": "English model sheet direction expressing the saved visual brief",
        "negativePrompt": "photorealistic rendering, harsh lighting",
    }}]}
    validate_brief_style(payload, contract, subjects=("hero",), stage="characters")
    assert contract["direction"] == direction
    assert EMPTY_DIRECTION not in payload["characters"][0]["image"]["prompt"]


def test_brief_contract_does_not_claim_to_validate_semantic_style_fidelity():
    direction = "2D 动画；水彩；低饱和"
    contract = freeze_brief_style(direction)
    payload = {"style": "saved-brief", "scenes": [{"id": "scene", "image": {
        "style": BRIEF_STYLE_LABEL,
        "prompt": "Watercolor animation with soft lighting",
        "sheet": "The English equivalent of the exact saved direction",
        "negativePrompt": "no photorealistic rendering; no harsh lighting",
    }}]}
    validate_brief_style(payload, contract, subjects=("scene",), stage="art")
    payload["scenes"][0]["image"]["style"] = "遵循项目简报"
    with pytest.raises(ValueError, match="English saved-Brief marker"):
        validate_brief_style(payload, contract, subjects=("scene",), stage="art")


def test_empty_brief_direction_is_explicit_and_does_not_inject_a_preset():
    contract = freeze_brief_style(None)
    payload = {"style": "saved-brief", "props": [{"id": "key", "image": {
        "style": BRIEF_STYLE_LABEL, "prompt": "Story-informed prop study with no preset style",
        "sheet": "English detail sheet for a prop with no preset style", "negativePrompt": "",
    }}]}
    validate_brief_style(payload, contract, subjects=("key",), stage="art")
    assert image_style_guidance(None, follows_brief=True) == EMPTY_DIRECTION
    assert image_style_guidance("2D；水彩；低饱和", follows_brief=True) == "2D；水彩；低饱和"
    assert image_style_guidance(None, follows_brief=False) == ""


@pytest.mark.parametrize(
    ("stage", "validate", "render"),
    [
        (
            "cast",
            'node scripts/brief-cast-style.mjs validate "$DELIVERY_ROOT/cast.json" --request "$PACKAGE_ROOT/request.json"',
            'node scripts/brief-cast-style.mjs render "$DELIVERY_ROOT/cast.json" --request "$PACKAGE_ROOT/request.json" > "$DELIVERY_ROOT/report.html"',
        ),
        (
            "art",
            'node scripts/brief-art-style.mjs validate "$DELIVERY_ROOT/art.json" --cast "$PACKAGE_ROOT/inputs/cast.json"',
            'node scripts/brief-art-style.mjs render "$DELIVERY_ROOT/art.json" --cast "$PACKAGE_ROOT/inputs/cast.json" > "$DELIVERY_ROOT/report.html"',
        ),
    ],
)
def test_saved_brief_instruction_contract_overrides_only_preset_routing(stage, validate, render):
    instructions = brief_stage_instructions(stage)
    assert "EXPLICIT SAVED-BRIEF RECEIVING-CONTRACT OVERRIDE" in instructions
    assert BRIEF_STAGE_INSTRUCTION_CONTRACT in instructions
    assert "take precedence over conflicting preset-specific requirements" in instructions
    assert "This override replaces only preset selection/defaults" in instructions
    assert "All other pinned skill instructions still apply" in instructions
    assert "upstream stage guidance, schema/structure, source/evidence, language" in instructions
    assert "do not add preset fields" in instructions
    assert "Resolve PACKAGE_ROOT as the absolute task-package directory" in instructions
    assert validate in instructions and render in instructions
    contract = freeze_brief_style("watercolor collage")
    assert contract["stageInstructionContract"] == BRIEF_STAGE_INSTRUCTION_CONTRACT


def test_brief_cast_keeps_upstream_source_and_structure_validation(tmp_path):
    contract = freeze_brief_style("2D animation")
    cast = {
        "style": "saved-brief", "summary": "A character summary", "lang": "zh",
        "characters": [{"id": "C01", "image": {
            "style": BRIEF_STYLE_LABEL, "prompt": "portrait, 2D animation",
            "sheet": "character sheet, 2D animation", "negativePrompt": "blurry",
            "tags": [],
        }}],
    }
    request = {"source": {"text": "A woman enters."}}
    with pytest.raises(ValueError, match="character Brief style/upstream validation failed") as error:
        validate_cast_style(cast, contract, request)
    assert "缺少 name" in str(error.value)


@pytest.mark.parametrize("direction", ["2D动画；拼贴；低饱和", "写实油画；硬光；高对比", None])
def test_real_upstream_cast_and_art_examples_validate_and_render_brief_reports(tmp_path, direction):
    from plotloom.art_style import validate_art_style
    from plotloom.autopilot_brief_style import BRIEF_STYLE, BRIEF_STYLE_LABEL

    examples = Path(__file__).parents[1] / "third_party/shuohao-skills/skills"
    cast = json.loads((examples / "novel-characters/examples/渡口-cast.json").read_text())
    art = json.loads((examples / "novel-art/examples/渡口-art.json").read_text())
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

    contract = freeze_brief_style(direction)
    request = {"source": {"text": "\n".join(source_quotes)}}
    validate_cast_style(cast, contract, request)
    with pytest.raises(ValueError, match="引文不是原文逐字片段"):
        validate_cast_style(cast, contract, {"source": {"text": "unrelated text"}})
    validate_art_style(art, cast, contract)

    cast_path, art_path, request_path = (tmp_path / name for name in ("cast.json", "art.json", "request.json"))
    cast_path.write_text(json.dumps(cast, ensure_ascii=False), encoding="utf-8")
    art_path.write_text(json.dumps(art, ensure_ascii=False), encoding="utf-8")
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    scripts = Path(__file__).parents[1] / "scripts"
    cast_report = subprocess.run(["node", str(scripts / "brief-cast-style.mjs"), "render", str(cast_path), "--request", str(request_path)], capture_output=True, text=True, check=True).stdout
    art_report = subprocess.run(["node", str(scripts / "brief-art-style.mjs"), "render", str(art_path), "--cast", str(cast_path)], capture_output=True, text=True, check=True).stdout
    assert "<html" in cast_report and "Saved Brief direction" in cast_report
    assert "<html" in art_report and "Saved Brief direction" in art_report


def test_new_launch_defaults_and_retained_v2_policy_keep_distinct_authorities():
    request = LaunchRequest(expectedBriefRevision=1, styleAuthority="brief")
    assert request.style_authority == "brief" and request.render_style is None
    raw_v2 = _policy(version="plotloom.pre-video.v2", authority="preset").model_dump(mode="json", by_alias=True)
    raw_v2.pop("styleAuthority")
    old = LaunchPolicy.model_validate(raw_v2)
    assert old.model_dump(mode="json", by_alias=True) == raw_v2
    assert old.effective_style_authority == "preset" and old.render_style == "ghibli"
    assert _policy().style_authority == "brief"
    with pytest.raises(ValidationError):
        _policy(version="plotloom.pre-video.v2", authority="brief")
    with pytest.raises(ValidationError):
        CastPrepareRequest(renderStyle="brief")
    with pytest.raises(ValidationError):
        ArtPrepareRequest(renderStyle="brief")
    assert {CastPrepareRequest(renderStyle=style).render_style for style in ("live-action", "realistic", "ghibli")} == {"live-action", "realistic", "ghibli"}
