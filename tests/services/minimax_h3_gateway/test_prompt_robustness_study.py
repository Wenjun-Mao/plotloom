"""Offline guardrails for the bounded H3 prompt-robustness operator tool."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _study_module():
    tools_path = Path(__file__).parents[3] / "services/minimax_h3_gateway/tools"
    path = tools_path / "h3_prompt_robustness_study.py"
    if str(tools_path) not in sys.path:
        sys.path.insert(0, str(tools_path))
    spec = importlib.util.spec_from_file_location("h3_prompt_robustness_study", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_study_matrix_is_bounded_and_keeps_the_recipes_complete() -> None:
    study = _study_module()

    assert len(study.RECIPES) == 2
    assert len(study.PROMPTS) == 2
    assert len(study.SEEDS) == 3
    assert all(recipe.lora_file.endswith(".safetensors") for recipe in study.RECIPES)
    assert all(recipe.sampler in {"res_multistep", "euler"} for recipe in study.RECIPES)


def test_study_renderer_has_exactly_one_start_frame_and_no_end_frame() -> None:
    study = _study_module()
    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    import json

    graph = study.render_workflow(
        json.loads(template_path.read_text(encoding="utf-8"))["prompt"],
        recipe=study.RECIPES[0], prompt=study.PROMPTS["audio_only_visual_no_text_v1"],
        seed=study.SEEDS[0], input_name="fixed.png", output_prefix="experiments/study/case",
    )

    assert graph["105:104"]["inputs"]["first_frame"] == ["h3_prompt_study_start_frame", 0]
    assert "last_frame" not in graph["105:104"]["inputs"]
    assert graph["h3_prompt_study_start_frame"]["inputs"]["image"] == "fixed.png"
    assert graph["105:122"]["inputs"] == {
        "model": ["105:121", 0], "shift_video": 6.0, "shift_audio": 3.0,
    }
    assert graph["105:9"]["inputs"]["steps"] == 4
    assert graph["92"]["inputs"]["filename_prefix"] == "experiments/study/case"


def test_study_renderer_accepts_explicit_native_portrait_geometry() -> None:
    study = _study_module()
    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    import json

    graph = study.render_workflow(
        json.loads(template_path.read_text(encoding="utf-8"))["prompt"],
        recipe=study.RECIPES[0], prompt="x", seed=1, input_name="portrait.png",
        output_prefix="experiments/study/portrait", width=608, height=1088,
        frame_count=124,
    )

    assert graph["115"]["inputs"]["value"] == 608
    assert graph["116"]["inputs"]["value"] == 1088
    assert graph["105:107"]["inputs"]["value"] == 124


def test_vertical_qualification_matrix_has_stronger_repeated_portrait_coverage() -> None:
    import h3_vertical_recipe_qualification as study

    assert (study.WIDTH, study.HEIGHT, study.FRAME_COUNT) == (608, 1088, 124)
    assert len(study.RECIPES) == 3
    assert len(study.SCENES) == 2
    assert len(study.SEEDS) == 6
    assert len(study.RECIPES) * len(study.SCENES) * len(study.SEEDS) == 36
    assert study.RECIPES[-1].identifier == "turbo8_v1_0_euler_6_3_readme"
