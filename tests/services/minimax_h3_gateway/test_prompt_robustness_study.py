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
    assert all(recipe.inference_steps == 4 for recipe in study.RECIPES)
    assert all((recipe.video_sigma_shift, recipe.audio_sigma_shift) == (6.0, 3.0) for recipe in study.RECIPES)


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
    assert study.SUPPORTED_PORTRAIT_GEOMETRIES == {
        (576, 1024), (608, 1088), (704, 1280),
    }
    assert len(study.RECIPES) == 3
    assert len(study.SCENES) == 2
    assert len(study.SEEDS) == 6
    assert len(study.RECIPES) * len(study.SCENES) * len(study.SEEDS) == 36
    assert study.RECIPES[-1].identifier == "turbo8_v1_0_euler_6_3_readme"
    assert study.EXPLICIT_BASE_RECIPE.identifier == "base20_res_multistep_native_12_3"
    assert study.EXPLICIT_BASE_RECIPE.lora_file is None
    assert study.EXPLICIT_BASE_RECIPE.video_sigma_shift is None


def test_eight_step_qualification_recipe_renders_eight_steps_not_four() -> None:
    import h3_vertical_recipe_qualification as study
    import h3_prompt_robustness_study as renderer
    import json

    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    eight_step = study.RECIPES[-1]
    graph = renderer.render_workflow(
        json.loads(template_path.read_text(encoding="utf-8"))["prompt"],
        recipe=eight_step, prompt="x", seed=1, input_name="portrait.png",
        output_prefix="experiments/study/eight-step", width=608, height=1088,
        frame_count=124,
    )

    assert eight_step.inference_steps == 8
    assert graph["105:9"]["inputs"]["steps"] == 8
    assert graph["105:122"]["inputs"] == {
        "model": ["105:121", 0], "shift_video": 6.0, "shift_audio": 3.0,
    }
    assert graph["105:17"]["inputs"]["sampler_name"] == "euler"


def test_base_qualification_recipe_removes_turbo_nodes_and_uses_native_defaults() -> None:
    import h3_vertical_recipe_qualification as study
    import h3_prompt_robustness_study as renderer
    import json

    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    base = study.EXPLICIT_BASE_RECIPE
    graph = renderer.render_workflow(
        json.loads(template_path.read_text(encoding="utf-8"))["prompt"],
        recipe=base, prompt="x", seed=1, input_name="portrait.png",
        output_prefix="experiments/study/base20", width=608, height=1088,
        frame_count=124,
    )

    assert "105:121" not in graph
    assert "105:122" not in graph
    assert graph["105:9"]["inputs"]["steps"] == 20
    assert graph["105:9"]["inputs"]["model"] == ["105:6", 0]
    assert graph["105:16"]["inputs"]["model"] == ["105:6", 0]
    assert graph["105:17"]["inputs"]["sampler_name"] == "res_multistep"
    assert base.public_descriptor()["topology"] == "base_model_with_native_sigma_defaults"
    assert base.public_descriptor()["effectiveSigmaShifts"] == {"video": 12.0, "audio": 3.0}


def test_vertical_qualification_can_rerun_only_an_invalid_recipe(
    monkeypatch, capsys,
) -> None:
    import h3_vertical_recipe_qualification as study
    import json

    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    monkeypatch.setattr(
        study.sys,
        "argv",
        [
            "h3_vertical_recipe_qualification.py",
            "--template", str(template_path),
            "--dialogue-input-name", "dialogue.png",
            "--motion-input-name", "motion.png",
            "--output-subfolder", "experiments/study",
            "--receipt", "/tmp/receipt.json",
            "--recipe-id", "turbo8_v1_0_euler_6_3_readme",
            "--dry-run",
        ],
    )

    assert study.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["caseCount"] == 12
    assert {case["recipeId"] for case in payload["cases"]} == {
        "turbo8_v1_0_euler_6_3_readme"
    }


def test_vertical_qualification_requires_explicit_base_recipe_selection(
    monkeypatch, capsys,
) -> None:
    import h3_vertical_recipe_qualification as study
    import json

    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    monkeypatch.setattr(
        study.sys,
        "argv",
        [
            "h3_vertical_recipe_qualification.py",
            "--template", str(template_path),
            "--dialogue-input-name", "dialogue.png",
            "--motion-input-name", "motion.png",
            "--output-subfolder", "experiments/study",
            "--receipt", "/tmp/receipt.json",
            "--recipe-id", "base20_res_multistep_native_12_3",
            "--dry-run",
        ],
    )

    assert study.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["caseCount"] == 12
    assert {case["recipeId"] for case in payload["cases"]} == {
        "base20_res_multistep_native_12_3"
    }


def test_vertical_qualification_accepts_an_approved_alternate_geometry(
    monkeypatch, capsys,
) -> None:
    import h3_vertical_recipe_qualification as study
    import json

    template_path = (
        Path(__file__).parents[3]
        / "services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json"
    )
    monkeypatch.setattr(
        study.sys,
        "argv",
        [
            "h3_vertical_recipe_qualification.py",
            "--template", str(template_path),
            "--dialogue-input-name", "dialogue.png",
            "--motion-input-name", "motion.png",
            "--output-subfolder", "experiments/study",
            "--receipt", "/tmp/receipt.json",
            "--width", "704", "--height", "1280",
            "--recipe-id", "turbo4_v1_2_euler_6_3",
            "--dry-run",
        ],
    )

    assert study.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["caseCount"] == 12
    assert payload["geometry"] == {"width": 704, "height": 1280, "frameCount": 124}


def test_vertical_qualification_rejects_unapproved_geometry(monkeypatch) -> None:
    import h3_vertical_recipe_qualification as study

    monkeypatch.setattr(
        study.sys,
        "argv",
        [
            "h3_vertical_recipe_qualification.py",
            "--template", "template.json",
            "--dialogue-input-name", "dialogue.png",
            "--motion-input-name", "motion.png",
            "--output-subfolder", "experiments/study",
            "--receipt", "/tmp/receipt.json",
            "--width", "832", "--height", "480",
            "--dry-run",
        ],
    )

    import pytest

    with pytest.raises(ValueError, match="approved portrait geometry"):
        study.main()
