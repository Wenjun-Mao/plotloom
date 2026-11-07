"""Frozen native reference-image contract and complete graph construction."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .reference_contracts import CreateReferenceJobRequest, reference_frame, reference_frame_count
from .vae_policy import ADOPTED_VAE_POLICY, bind_vae_policy
from .voice_reference import VOICE_MODEL, VOICE_MODEL_SHA256

REFERENCE_CONTRACT_VERSION = 1
REFERENCE_RENDERER_VERSION = 1


class ReferenceImage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: StrictInt = Field(ge=1, le=9)
    atMs: StrictInt = Field(ge=0, lt=15_000)
    frameIndex: StrictInt = Field(ge=0, le=361)
    imageName: str = Field(min_length=1)
    sourceSha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    preparedSha256: str = Field(pattern=r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class ReferenceExecution:
    resolution: str
    duration_ms: int
    seed: int
    prompt_sha256: str
    images: tuple[ReferenceImage, ...]

    @property
    def frame_count(self) -> int:
        return reference_frame_count(self.duration_ms)

    def snapshot(self) -> dict[str, Any]:
        width, height = map(int, self.resolution.split("x"))
        return {
            "referenceContractVersion": REFERENCE_CONTRACT_VERSION,
            "workflowRendererVersion": REFERENCE_RENDERER_VERSION,
            "inputMode": "reference_images", "model": VOICE_MODEL,
            "modelSha256": VOICE_MODEL_SHA256,
            "recipe": {"steps": 20, "sampler": "res_multistep", "scheduler": "simple",
                       "denoise": 1.0, "lora": None, "sigmaShift": None, "refImageSize": "match"},
            "resolution": self.resolution, "width": width, "height": height,
            "requestedDurationMs": self.duration_ms, "fps": 24, "frameCount": self.frame_count,
            "seed": self.seed, "promptSha256": self.prompt_sha256,
            "references": [image.model_dump() for image in self.images],
            "vaePolicy": ADOPTED_VAE_POLICY.snapshot(),
        }

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))


def is_reference_job(job: dict[str, Any]) -> bool:
    if job.get("h3_contract") != "ref2va":
        return False
    try:
        return json.loads(job["execution_snapshot_json"]).get("inputMode") == "reference_images"
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def reference_execution_from_snapshot(value: str) -> ReferenceExecution:
    try:
        payload = json.loads(value)
        request = CreateReferenceJobRequest.model_validate({
            "prompt": "snapshot validation", "resolution": payload["resolution"],
            "aspectPolicy": "reject_mismatch", "durationMs": payload["requestedDurationMs"],
            "seed": payload["seed"],
            "references": [{"atMs": row["atMs"]} for row in payload["references"]],
        })
        images = tuple(ReferenceImage.model_validate(row) for row in payload["references"])
        if request.seed is None:
            raise ValueError
        if any(image.index != index or image.frameIndex != reference_frame(image.atMs)
               for index, image in enumerate(images, 1)):
            raise ValueError
        prompt_hash = payload["promptSha256"]
        if not isinstance(prompt_hash, str) or len(prompt_hash) != 64 or any(
            value not in "0123456789abcdef" for value in prompt_hash
        ):
            raise ValueError
        result = ReferenceExecution(request.resolution, request.duration_ms, request.seed,
                                    prompt_hash, images)
        if result.snapshot_json() != json.dumps(payload, sort_keys=True, separators=(",", ":")):
            raise ValueError
        return result
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid frozen reference-images execution snapshot") from None


def reference_response(job: dict[str, Any]) -> dict[str, Any]:
    try:
        execution = reference_execution_from_snapshot(job["execution_snapshot_json"])
    except ValueError:
        # Keep lifecycle status readable after integrity refusal; never project
        # unvalidated timing or hashes from a damaged execution snapshot.
        return {"inputMode": "reference_images", "referenceContractVersion": REFERENCE_CONTRACT_VERSION,
                "requestedDurationMs": None, "promptSha256": None, "references": None}
    return {
        "inputMode": "reference_images", "referenceContractVersion": REFERENCE_CONTRACT_VERSION,
        "requestedDurationMs": execution.duration_ms, "promptSha256": execution.prompt_sha256,
        "references": [{"index": row.index, "atMs": row.atMs, "frameIndex": row.frameIndex,
                        "effectiveTimeSeconds": row.frameIndex / 24,
                        "sourceSha256": row.sourceSha256, "preparedSha256": row.preparedSha256}
                       for row in execution.images],
    }


def render_reference_workflow(template: dict[str, Any], execution: ReferenceExecution, prompt: str) -> dict[str, Any]:
    if sha256(prompt.encode("utf-8")).hexdigest() != execution.prompt_sha256:
        raise ValueError("reference prompt differs from frozen snapshot")
    graph = copy.deepcopy(template)
    bind_vae_policy(graph, ADOPTED_VAE_POLICY)
    graph.pop("105:121", None)
    graph.pop("105:122", None)
    graph["105:6"]["inputs"] = {"unet_name": VOICE_MODEL, "weight_dtype": "default"}
    graph["105:9"]["inputs"] = {"scheduler": "simple", "steps": 20, "denoise": 1.0, "model": ["105:6", 0]}
    graph["105:17"]["inputs"] = {"sampler_name": "res_multistep"}
    graph["105:15"]["inputs"] = {"noise_seed": execution.seed}
    graph["105:107"]["inputs"] = {"value": execution.frame_count}
    width, height = map(int, execution.resolution.split("x"))
    graph["115"]["inputs"] = {"value": width}
    graph["116"]["inputs"] = {"value": height}
    inputs = {"clip": ["105:13", 0], "vae": ["105:11", 0], "prompt": prompt,
              "width": ["115", 0], "height": ["116", 0], "length": ["105:107", 0],
              "ref_image_size": "match"}
    positive = ["105:104", 0]
    for row in execution.images:
        image_node, guide_node = f"reference_image_{row.index}", f"reference_guide_{row.index}"
        graph[image_node] = {"class_type": "LoadImage", "inputs": {"image": row.imageName}}
        inputs[f"ref_images.ref_image_{row.index - 1}"] = [image_node, 0]
        graph[guide_node] = {"class_type": "MiniMaxH3AddGuide", "inputs": {
            "positive": positive, "latent": ["105:104", 1], "vae": ["105:11", 0],
            "image": [image_node, 0], "frame_idx": row.frameIndex,
        }}
        positive = [guide_node, 0]
    graph["105:104"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": inputs}
    graph["105:16"]["inputs"] = {"model": ["105:6", 0], "conditioning": positive}
    return graph
