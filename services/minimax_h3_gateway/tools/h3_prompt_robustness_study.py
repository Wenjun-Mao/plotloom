#!/usr/bin/env python3
"""Run a bounded, serial H3 dialogue-visual-text robustness study on Spark.

This operator tool talks directly to loopback-only ComfyUI.  It is deliberately
outside the gateway's public API and cannot alter its catalog, queue, or
production profile selection.  It renders two fully declared four-step
LightX2V recipes and two prompt contracts over the same input, geometry,
duration, and seed set.

Run it on Spark (where ComfyUI and the chosen input are mounted) rather than
from a client machine.  The resulting receipt contains prompt hashes, not
prompt text, so it can be retained beside the generated experiment media.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


WIDTH = 832
HEIGHT = 480
FRAME_COUNT = 124
VIDEO_SHIFT = 6.0
AUDIO_SHIFT = 3.0
SCHEDULER = "simple"
DENOISE = 1.0
SEEDS = (130117, 41398272, 20260919)


@dataclass(frozen=True)
class Recipe:
    identifier: str
    lora_file: str
    sampler: str


RECIPES = (
    Recipe(
        identifier="turbo4_v1_0_res_multistep_6_3",
        lora_file="minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
        sampler="res_multistep",
    ),
    Recipe(
        identifier="turbo4_v1_2_euler_6_3",
        lora_file="minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors",
        sampler="euler",
    ),
)


PROMPTS = {
    # This mirrors Plotloom's current frozen dialogue projection: it gives the
    # model one undifferentiated prompt containing visual, dialogue and sound.
    "inline_dialogue_v1": (
        "Cinematic realism. A weary female astronaut stands in a spacecraft "
        "corridor, with Earth visible through the window. "
        "Action: she slowly looks from Earth toward the camera and exhales. "
        "Motion: stable cinematic camera, natural breathing and subtle body movement.\n"
        "Dialogue (zh-CN; speaker=astronaut; delivery=soft; performance=relieved): 我们回家吧。\n"
        "Sound (ambience): gentle spacecraft room tone."
    ),
    # The proposed H3-native contract deliberately describes the visible
    # frame and the audible spoken line as separate semantic channels.
    "audio_only_visual_no_text_v1": (
        "Visual: cinematic realism. A weary female astronaut stands in a "
        "spacecraft corridor, with Earth visible through the window. She slowly "
        "looks from Earth toward the camera and exhales. Stable cinematic camera, "
        "natural breathing and subtle body movement. The frame contains no written "
        "language, captions, subtitles, titles, lower thirds, signage, interface "
        "text, or typography.\n"
        "Audio: the astronaut says the following line aloud in Mandarin: “我们回家吧。” "
        "The dialogue exists only in the audio track; do not render the words visually.\n"
        "Sound: gentle spacecraft room tone."
    ),
}


def _replace(value: Any, replacements: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _replace(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace(child, replacements) for child in value]
    return replacements.get(value, value)


def render_workflow(
    template: dict[str, Any], *, recipe: Recipe, prompt: str, seed: int,
    input_name: str, output_prefix: str, width: int = WIDTH, height: int = HEIGHT,
    frame_count: int = FRAME_COUNT,
) -> dict[str, Any]:
    """Render a one-frame H3 graph with an explicit, complete recipe."""

    if width <= 0 or height <= 0 or frame_count <= 0:
        raise ValueError("geometry and frame count must be positive")

    graph = _replace(
        copy.deepcopy(template),
        {
            "__PROMPT__": prompt,
            "__SEED__": seed,
            "__WIDTH__": width,
            "__HEIGHT__": height,
            "__FRAME_COUNT__": frame_count,
            "__LORA_FILE__": recipe.lora_file,
            "__LORA_STRENGTH__": 1.0,
            "__INFERENCE_STEPS__": 4,
            "__VIDEO_SIGMA_SHIFT__": VIDEO_SHIFT,
            "__AUDIO_SIGMA_SHIFT__": AUDIO_SHIFT,
            "__SAMPLER__": recipe.sampler,
            "__SCHEDULER__": SCHEDULER,
            "__DENOISE__": DENOISE,
        },
    )
    graph["h3_prompt_study_start_frame"] = {
        "class_type": "LoadImage", "inputs": {"image": input_name},
    }
    graph["105:104"]["inputs"]["first_frame"] = ["h3_prompt_study_start_frame", 0]
    graph["105:104"]["inputs"].pop("last_frame", None)
    graph["92"]["inputs"]["filename_prefix"] = output_prefix
    return graph


def _history_output(record: object) -> dict[str, str] | None:
    if not isinstance(record, dict):
        return None
    outputs = record.get("outputs")
    if not isinstance(outputs, dict):
        return None
    matches: list[dict[str, str]] = []
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for item in node.get("images", []):
            if not isinstance(item, dict):
                continue
            filename, subfolder, output_type = item.get("filename"), item.get("subfolder"), item.get("type")
            if all(isinstance(value, str) for value in (filename, subfolder, output_type)) and filename.endswith(".mp4"):
                matches.append({"filename": filename, "subfolder": subfolder, "type": output_type})
    return matches[0] if len(matches) == 1 else None


def wait_for_completion(
    session: requests.Session, *, comfy_url: str, prompt_id: str, timeout_seconds: float, poll_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = session.get(f"{comfy_url}/history/{prompt_id}", timeout=10)
        response.raise_for_status()
        history = response.json()
        record = history.get(prompt_id) if isinstance(history, dict) else None
        status = record.get("status") if isinstance(record, dict) and isinstance(record.get("status"), dict) else {}
        if status.get("completed"):
            if status.get("status_str") not in {"success", "completed"}:
                raise RuntimeError(f"ComfyUI execution failed for {prompt_id}: {status.get('status_str')}")
            output = _history_output(record)
            if output is None:
                raise RuntimeError(f"ComfyUI returned no single MP4 for {prompt_id}")
            return output
        time.sleep(poll_seconds)
    raise TimeoutError(f"ComfyUI did not complete {prompt_id} within {timeout_seconds:g}s")


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True, help="Path to minimax_h3_template_v2.json")
    parser.add_argument("--input-name", required=True, help="Existing ComfyUI input filename, not a host path")
    parser.add_argument("--output-subfolder", required=True, help="ComfyUI output subfolder below data/output")
    parser.add_argument("--receipt", type=Path, required=True, help="Where to write the JSON receipt")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--poll-seconds", type=float, default=2)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout_seconds <= 0 or args.poll_seconds <= 0:
        raise ValueError("timeout and poll intervals must be positive")
    template_document = json.loads(args.template.read_text(encoding="utf-8"))
    template = template_document.get("prompt") if isinstance(template_document, dict) else None
    if not isinstance(template, dict):
        raise ValueError("template must contain a prompt graph")
    cases = [
        (recipe, prompt_id, prompt, seed)
        for recipe in RECIPES
        for prompt_id, prompt in PROMPTS.items()
        for seed in SEEDS
    ]
    rendered = [
        {
            "recipeId": recipe.identifier,
            "promptContractId": prompt_id,
            "promptSha256": prompt_sha256(prompt),
            "seed": seed,
            "workflow": render_workflow(
                template, recipe=recipe, prompt=prompt, seed=seed, input_name=args.input_name,
                output_prefix=f"{args.output_subfolder}/{recipe.identifier}_{prompt_id}_seed-{seed}",
            ),
        }
        for recipe, prompt_id, prompt, seed in cases
    ]
    if args.dry_run:
        print(json.dumps({"caseCount": len(rendered), "cases": [{key: value for key, value in item.items() if key != "workflow"} for item in rendered]}, ensure_ascii=False, indent=2))
        return 0

    session = requests.Session()
    queue = session.get(f"{args.comfy_url}/queue", timeout=10).json()
    if not isinstance(queue, dict) or queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("ComfyUI queue is not empty; refuse to interleave this controlled study")
    results: list[dict[str, Any]] = []
    for index, item in enumerate(rendered, start=1):
        started = time.monotonic()
        response = session.post(
            f"{args.comfy_url}/prompt", json={"prompt": item["workflow"], "client_id": "plotloom-h3-prompt-robustness-study"}, timeout=30,
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
        result = {key: value for key, value in item.items() if key != "workflow"}
        result.update({"comfyPromptId": prompt_id, "output": output, "generationElapsedMs": round((time.monotonic() - started) * 1000)})
        results.append(result)
        print(f"[{index}/{len(rendered)}] {result['recipeId']} {result['promptContractId']} seed={result['seed']} -> {output['subfolder']}/{output['filename']}", flush=True)

    receipt = {
        "manifestVersion": 1,
        "kind": "minimax_h3_prompt_robustness_study",
        "inputName": args.input_name,
        "geometry": {"width": WIDTH, "height": HEIGHT, "frameCount": FRAME_COUNT, "fps": 24},
        "sampling": {"videoSigmaShift": VIDEO_SHIFT, "audioSigmaShift": AUDIO_SHIFT, "steps": 4, "scheduler": SCHEDULER, "denoise": DENOISE},
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
