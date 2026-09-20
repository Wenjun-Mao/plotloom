#!/usr/bin/env python3
"""Run a vertical-first, blinded-ready H3 recipe qualification study on Spark.

This is an experiment operator tool, not a gateway client. It sends a bounded
serial matrix directly to loopback ComfyUI and never changes an admitted H3
profile, the gateway queue, or Plotloom prompt persistence.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

from h3_prompt_robustness_study import Recipe, prompt_sha256, render_workflow, wait_for_completion


WIDTH = 608
HEIGHT = 1088
FRAME_COUNT = 124
SEEDS = (130117, 41398272, 20260919, 9048391, 27501834, 77261003)
RECIPES = (
    Recipe(
        identifier="turbo4_v1_0_res_multistep_6_3",
        lora_file="minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
        inference_steps=4,
        video_sigma_shift=6.0,
        audio_sigma_shift=3.0,
        sampler="res_multistep",
        scheduler="simple",
        denoise=1.0,
    ),
    Recipe(
        identifier="turbo4_v1_2_euler_6_3",
        lora_file="minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors",
        inference_steps=4,
        video_sigma_shift=6.0,
        audio_sigma_shift=3.0,
        sampler="euler",
        scheduler="simple",
        denoise=1.0,
    ),
    Recipe(
        identifier="turbo8_v1_0_euler_6_3_readme",
        lora_file="minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors",
        inference_steps=8,
        video_sigma_shift=6.0,
        audio_sigma_shift=3.0,
        sampler="euler",
        scheduler="simple",
        denoise=1.0,
    ),
)
SCENES = {
    "dialogue_portrait_v1": {
        "prompt": (
            "Visual: cinematic realism. A weary female astronaut stands in a spacecraft "
            "corridor, with Earth visible through a narrow window. She slowly looks from "
            "Earth toward the camera and exhales. Stable portrait camera, natural breathing "
            "and subtle body movement. The frame contains no written language, captions, "
            "subtitles, titles, lower thirds, signage, interface text, or typography.\n"
            "Audio: the astronaut says the following line aloud in Mandarin: “我们回家吧。” "
            "The dialogue exists only in the audio track; do not render the words visually.\n"
            "Sound: gentle spacecraft room tone."
        ),
    },
    "motion_portrait_v1": {
        "prompt": (
            "Visual: cinematic realism. A female astronaut walks slowly and naturally through "
            "an orbital spacecraft corridor, then briefly looks toward the Earthlit window. "
            "Stable vertical camera with restrained forward motion, coherent limbs, natural "
            "walking rhythm and intact facial features. The frame contains no written language, "
            "captions, subtitles, titles, lower thirds, signage, interface text, or typography.\n"
            "Audio: no spoken dialogue.\n"
            "Sound: soft footsteps, gentle spacecraft room tone and distant ventilation."
        ),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dialogue-input-name", required=True)
    parser.add_argument("--motion-input-name", required=True)
    parser.add_argument("--output-subfolder", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout-seconds", type=float, default=1200)
    parser.add_argument("--poll-seconds", type=float, default=2)
    parser.add_argument(
        "--recipe-id", action="append", default=[],
        help="Run only this declared recipe ID; repeat only for an explicit subset.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout_seconds <= 0 or args.poll_seconds <= 0:
        raise ValueError("timeout and poll intervals must be positive")
    document = json.loads(args.template.read_text(encoding="utf-8"))
    template = document.get("prompt") if isinstance(document, dict) else None
    if not isinstance(template, dict):
        raise ValueError("template must contain a prompt graph")
    selected_recipe_ids = set(args.recipe_id)
    selected_recipes = tuple(
        recipe for recipe in RECIPES
        if not selected_recipe_ids or recipe.identifier in selected_recipe_ids
    )
    if not selected_recipes or selected_recipe_ids.difference(recipe.identifier for recipe in selected_recipes):
        raise ValueError("recipe-id must name one or more declared recipes")
    input_names = {
        "dialogue_portrait_v1": args.dialogue_input_name,
        "motion_portrait_v1": args.motion_input_name,
    }
    cases = [
        (recipe, scene_id, str(scene["prompt"]), seed, input_names[scene_id])
        for recipe in selected_recipes
        for scene_id, scene in SCENES.items()
        for seed in SEEDS
    ]
    if args.dry_run:
        print(json.dumps({
            "caseCount": len(cases), "geometry": {"width": WIDTH, "height": HEIGHT, "frameCount": FRAME_COUNT},
            "cases": [
                {"recipeId": recipe.identifier, "sceneId": scene_id, "promptSha256": prompt_sha256(prompt), "seed": seed}
            for recipe, scene_id, prompt, seed, _ in cases
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    session = requests.Session()
    queue = session.get(f"{args.comfy_url}/queue", timeout=10).json()
    if not isinstance(queue, dict) or queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not empty; refuse to interleave this controlled study")
    results: list[dict[str, Any]] = []
    for index, (recipe, scene_id, prompt, seed, input_name) in enumerate(cases, start=1):
        started = time.monotonic()
        graph = render_workflow(
            template, recipe=recipe, prompt=prompt, seed=seed, input_name=input_name,
            output_prefix=f"{args.output_subfolder}/{recipe.identifier}_{scene_id}_seed-{seed}",
            width=WIDTH, height=HEIGHT, frame_count=FRAME_COUNT,
        )
        response = session.post(
            f"{args.comfy_url}/prompt",
            json={"prompt": graph, "client_id": "plotloom-h3-vertical-recipe-qualification"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        prompt_id = payload.get("prompt_id") if isinstance(payload, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            raise RuntimeError(f"ComfyUI returned an invalid prompt response for study case {index}")
        output = wait_for_completion(
            session, comfy_url=args.comfy_url, prompt_id=prompt_id,
            timeout_seconds=args.timeout_seconds, poll_seconds=args.poll_seconds,
        )
        result = {
            "recipeId": recipe.identifier, "sceneId": scene_id,
            "promptSha256": prompt_sha256(prompt), "seed": seed,
            "comfyPromptId": prompt_id, "output": output,
            "generationElapsedMs": round((time.monotonic() - started) * 1000),
        }
        results.append(result)
        print(
            f"[{index}/{len(cases)}] {recipe.identifier} {scene_id} seed={seed} -> "
            f"{output['subfolder']}/{output['filename']}",
            flush=True,
        )
    receipt = {
        "manifestVersion": 1,
        "kind": "minimax_h3_vertical_recipe_qualification",
        "geometry": {"width": WIDTH, "height": HEIGHT, "frameCount": FRAME_COUNT, "fps": 24},
        "recipes": [
            {
                "id": recipe.identifier, "loraFile": recipe.lora_file,
                "inferenceSteps": recipe.inference_steps,
                "videoSigmaShift": recipe.video_sigma_shift,
                "audioSigmaShift": recipe.audio_sigma_shift,
                "sampler": recipe.sampler, "scheduler": recipe.scheduler,
                "denoise": recipe.denoise,
            }
            for recipe in selected_recipes
        ],
        "results": results,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Receipt: {args.receipt}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, requests.RequestException, RuntimeError, TimeoutError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
