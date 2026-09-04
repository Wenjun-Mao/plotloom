from __future__ import annotations

import json

import pytest

from plotloom.domain import Shot, ShotSize
from plotloom.generation.exceptions import PromptRenderError
from plotloom.generation.prompts import PromptRenderer, PromptRepository


def test_repository_contains_all_versioned_stage_and_media_prompts() -> None:
    repository = PromptRepository()
    assert repository.list_ids() == (
        "media_image",
        "media_video",
        "repair_json",
        "scene_beats",
        "scene_beats_fragment",
        "story_bible",
        "story_graph",
        "story_graph_content_fill",
        "storyboard",
        "storyboard_fragment",
        "work_unit_correction",
    )
    for prompt_id in repository.list_ids():
        spec, spec_hash, source = repository.load(prompt_id)
        expected_major = "3." if prompt_id in {
            "story_bible",
            "story_graph",
            "scene_beats",
            "scene_beats_fragment",
            "storyboard",
            "storyboard_fragment",
        } else "2."
        assert spec.version.startswith(expected_major)
        assert len(spec_hash) == 64
        assert source.parent.name == "prompt_templates"


def test_prompt_rendering_is_strict_and_hashes_are_reproducible() -> None:
    renderer = PromptRenderer()
    variables = {"project_input": {"synopsis": "失忆领航员醒来"}}
    first = renderer.render("story_bible", {**variables, "json_schema": {"type": "object"}})
    second = renderer.render("story_bible", {**variables, "json_schema": {"type": "object"}})

    assert first.trace.spec_hash == second.trace.spec_hash
    assert first.trace.input_hash == second.trace.input_hash
    assert first.trace.rendered_hash == second.trace.rendered_hash
    assert first.trace.source == "plotloom/prompt_templates/story_bible.yaml"
    assert first.trace.variable_names == (
        "creative_constraints",
        "json_schema",
        "project_input",
    )
    assert "失忆领航员醒来" not in first.trace.model_dump_json()

    with pytest.raises(PromptRenderError, match="missing required variables"):
        renderer.render("story_bible", {"project_input": variables["project_input"]})
    with pytest.raises(PromptRenderError, match="undeclared variables"):
        renderer.render(
            "story_bible",
            {**variables, "json_schema": {}, "unexpected": True},
        )


def test_structured_generation_prompts_require_explicit_field_presence() -> None:
    repository = PromptRepository()
    for prompt_id in (
        "story_bible",
        "story_graph_content_fill",
        "scene_beats_fragment",
        "storyboard_fragment",
        "work_unit_correction",
    ):
        spec, _spec_hash, _source = repository.load(prompt_id)
        assert "presence-strict" in spec.system
        assert "required" in spec.system
        assert "不得依赖应用默认值" in spec.system

    scene_spec, _spec_hash, _source = repository.load("scene_beats_fragment")
    assert "entityStates" in scene_spec.user
    assert "不能省略任何一项" in scene_spec.user
    scene_full_spec, _spec_hash, _source = repository.load("scene_beats")
    assert "连续 order" in scene_full_spec.user
    assert "durationBudgetUnits" in scene_full_spec.user
    for field in (
        "facts",
        "entityStates",
        "screenDirection",
        "lighting",
        "sound",
        "notes",
        "voiceOver",
    ):
        assert field in scene_full_spec.user
    bible_spec, _spec_hash, _source = repository.load("story_bible")
    for field in (
        "id",
        "name",
        "description",
        "visualAnchors",
        "soundAnchors",
        "allowedStates",
        "continuityRules",
        "role",
        "goal",
        "traits",
        "voiceAnchors",
    ):
        assert field in bible_spec.user
    assert "visualIdentity" not in bible_spec.user
    correction_spec, _spec_hash, _source = repository.load("work_unit_correction")
    assert "对每条 schema.missing" in correction_spec.user
    assert "对每条 schema.extra_forbidden" in correction_spec.user
    assert "minimumDurationUnits" in correction_spec.user
    assert "minimumFitsSceneBudget" in correction_spec.user
    assert "timing_repair_facts" in correction_spec.variables
    assert "dialogue_timing_policy" in scene_spec.variables
    assert "language=\"*\"" in scene_spec.user
    assert "× measured 420" not in scene_spec.user


def test_storyboard_schema_and_media_prompts_are_separate() -> None:
    renderer = PromptRenderer()
    storyboard_schema = {
        "type": "object",
        "properties": {
            "shots": {
                "items": {
                    "properties": {
                        "audioPlan": {},
                        "cueIds": {},
                        "requiredEntityStates": {},
                        "transition": {},
                        "visualIntent": {},
                        "motionIntent": {},
                    }
                }
            }
        },
    }
    storyboard = renderer.render(
        "storyboard",
        {
            "story_bible": {},
            "story_graph": {},
            "scene_beats": {},
            "storyboard_constraints": {},
            "json_schema": storyboard_schema,
        },
    )
    assert storyboard.output.format == "json"
    assert storyboard.output.structured_output_mode == "prefer"
    assert "不生成供应商专用的图片或视频提示词" in storyboard.messages[1].content
    for field in ("audioPlan", "cueIds", "requiredEntityStates", "transition", "visualIntent", "motionIntent"):
        assert field in storyboard.messages[1].content

    shot = Shot(
        id="shot-1",
        scene_id="scene-1",
        order=1,
        title="苏醒",
        shot_size=ShotSize.CLOSE_UP,
        duration_seconds=4,
        visual_intent="身份迷失",
        motion_intent="缓慢睁眼",
    )
    image = renderer.render(
        "media_image",
        {
            "story_bible": {"logline": "测试"},
            "storyboard_shot": shot,
            "continuity_context": {},
            "media_constraints": {"aspectRatio": "16:9"},
        },
    )
    assert image.output.format == "text"
    assert image.trace.stage == "media_image"
    assert '"visualIntent":"身份迷失"' in image.messages[1].content
    assert "visual_intent" not in image.messages[1].content
    assert json.loads(json.dumps(image.trace.model_dump(mode="json"), default=str))
