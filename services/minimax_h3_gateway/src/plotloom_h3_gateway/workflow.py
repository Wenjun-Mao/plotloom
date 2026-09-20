"""Frozen ComfyUI workflow rendering and output-descriptor parsing."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .naming import is_safe_path_part
from .profile_catalog import H3ExecutionProfile


def load_h3_template() -> dict[str, Any]:
    """Load the profile-rendered reviewed H3 graph template."""

    path = Path(__file__).with_name("profiles") / "minimax_h3_template_v2.json"
    return json.loads(path.read_text(encoding="utf-8"))


def render_workflow(
    template: dict[str, Any], *, execution: H3ExecutionProfile, prompt: str,
    start_input_name: str | None, end_input_name: str | None, seed: int, frame_count: int,
) -> dict[str, Any]:
    """Render a reviewed H3 graph with zero, one, or two optional frame inputs."""

    workflow = copy.deepcopy(template)
    def replace(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: replace(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace(child) for child in value]
        recipe = execution.recipe
        return {
            "__PROMPT__": prompt,
            "__SEED__": seed,
            "__WIDTH__": execution.width,
            "__HEIGHT__": execution.height,
            "__FRAME_COUNT__": frame_count,
            "__INFERENCE_STEPS__": recipe.inference_steps,
            "__SAMPLER__": recipe.sampler,
            "__SCHEDULER__": recipe.scheduler,
            "__DENOISE__": recipe.denoise,
        }.get(value, value)

    workflow = replace(workflow)
    if execution.recipe.topology == "turbo":
        _render_turbo_topology(workflow, execution)
    else:
        _render_base_topology(workflow)

    h3_inputs = workflow["105:104"]["inputs"]
    for socket, input_name, node_id in (
        ("first_frame", start_input_name, "h3_start_frame"),
        ("last_frame", end_input_name, "h3_end_frame"),
    ):
        if input_name is not None:
            workflow[node_id] = {"class_type": "LoadImage", "inputs": {"image": input_name}}
            h3_inputs[socket] = [node_id, 0]
        else:
            h3_inputs.pop(socket, None)
    return workflow


def _render_turbo_topology(workflow: dict[str, Any], execution: H3ExecutionProfile) -> None:
    """Render the reviewed Turbo path with explicit LoRA and 6/3 shifts."""

    recipe = execution.recipe
    if (
        recipe.lora_file is None or recipe.lora_strength is None
        or recipe.video_sigma_shift is None or recipe.audio_sigma_shift is None
    ):
        raise ValueError("turbo recipe is incomplete")
    workflow["105:121"]["inputs"] = {
        "lora_name": recipe.lora_file,
        "strength_model": recipe.lora_strength,
        "model": ["105:6", 0],
    }
    workflow["105:122"]["inputs"] = {
        "model": ["105:121", 0],
        "shift_video": recipe.video_sigma_shift,
        "shift_audio": recipe.audio_sigma_shift,
    }


def _render_base_topology(workflow: dict[str, Any]) -> None:
    """Use H3 native 12/3 defaults: no Turbo LoRA or shift override nodes."""

    workflow.pop("105:121", None)
    workflow.pop("105:122", None)
    for node_id in ("105:9", "105:16"):
        workflow[node_id]["inputs"]["model"] = ["105:6", 0]


def single_output_descriptor(outputs: object) -> dict[str, str] | None:
    """Accept precisely one safe MP4 descriptor from completed Comfy history."""

    if not isinstance(outputs, dict):
        return None
    matches: list[dict[str, str]] = []
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        for item in node_output.get("images", []):
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            subfolder = item.get("subfolder", "")
            output_type = item.get("type")
            if not all(isinstance(value, str) for value in (filename, subfolder, output_type)):
                continue
            if (
                output_type == "output"
                and filename.endswith(".mp4")
                and is_safe_path_part(filename)
                and is_safe_path_part(subfolder)
            ):
                matches.append({"filename": filename, "subfolder": subfolder, "type": output_type})
    return matches[0] if len(matches) == 1 else None
