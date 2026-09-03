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
        "storyboard",
        "storyboard_fragment",
    )
    for prompt_id in repository.list_ids():
        spec, spec_hash, source = repository.load(prompt_id)
        assert spec.version.startswith("2.")
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


def test_storyboard_schema_and_media_prompts_are_separate() -> None:
    renderer = PromptRenderer()
    storyboard_schema = {
        "type": "object",
        "properties": {
            "shots": {
                "items": {
                    "properties": {
                        "audio": {},
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
    for field in ("audio", "transition", "visualIntent", "motionIntent"):
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
