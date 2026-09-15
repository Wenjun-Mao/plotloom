"""Frozen ComfyUI workflow rendering and output-descriptor parsing."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .naming import is_safe_path_part
from .profile_catalog import GatewayProfile


def load_h3_template() -> dict[str, Any]:
    """Load the profile-neutral reviewed H3 graph template."""

    path = Path(__file__).with_name("profiles") / "minimax_h3_turbo4_template_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def render_workflow(
    template: dict[str, Any], *, profile: GatewayProfile, prompt: str,
    start_input_name: str | None, end_input_name: str | None, seed: int, frame_count: int,
) -> dict[str, Any]:
    """Render a reviewed H3 graph with zero, one, or two optional frame inputs."""

    workflow = copy.deepcopy(template)
    def replace(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: replace(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace(child) for child in value]
        return {
            "__PROMPT__": prompt,
            "__SEED__": seed,
            "__WIDTH__": profile.width,
            "__HEIGHT__": profile.height,
            "__FRAME_COUNT__": frame_count,
        }.get(value, value)

    workflow = replace(workflow)
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
