"""Frozen Ref2VA contract, canonical WAV intake, and reviewed graph rendering."""
from __future__ import annotations

import copy
import json
import wave
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Any

from .contracts import GatewayError
from .profile_catalog import (
    FRAMES_PER_SECOND,
    H3Resolution,
    frame_count_for_duration_seconds,
)

VOICE_CONTRACT_VERSION = 1
VOICE_RENDERER_VERSION = 1
VOICE_MODEL = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
VOICE_MODEL_SHA256 = "9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779"
VOICE_RESOLUTIONS = {
    "960x544": H3Resolution("960x544", 960, 544),
    "576x1024": H3Resolution("576x1024", 576, 1024),
}
MAX_VOICE_BYTES = 2 * 1024 * 1024
MIN_VOICE_DURATION_MS = 1_000
MAX_VOICE_DURATION_MS = 10_000
VOICE_SAMPLE_RATE = 32_000


@dataclass(frozen=True)
class CanonicalVoice:
    source_sha256: str
    prepared_sha256: str
    source_bytes: bytes
    prepared_bytes: bytes
    duration_ms: int


@dataclass(frozen=True)
class VoiceExecution:
    resolution: H3Resolution
    requested_duration_seconds: int
    frame_count: int
    seed: int
    prompt_sha256: str
    image_name: str
    audio_name: str
    image_sha256: str
    prepared_image_sha256: str
    audio_sha256: str
    prepared_audio_sha256: str

    def snapshot_json(self) -> str:
        payload = {
            "voiceContractVersion": VOICE_CONTRACT_VERSION,
            "workflowRendererVersion": VOICE_RENDERER_VERSION,
            "inputMode": "image_voice",
            "model": VOICE_MODEL,
            "modelSha256": VOICE_MODEL_SHA256,
            "recipe": {"steps": 20, "sampler": "res_multistep", "scheduler": "simple",
                       "denoise": 1.0, "lora": None, "sigmaShift": None, "refImageSize": "match"},
            "resolution": self.resolution.value,
            "width": self.resolution.width,
            "height": self.resolution.height,
            "fps": FRAMES_PER_SECOND,
            "requestedDurationSeconds": self.requested_duration_seconds,
            "frameCount": self.frame_count,
            "seed": self.seed,
            "promptSha256": self.prompt_sha256,
            "imageName": self.image_name,
            "audioName": self.audio_name,
            "imageSha256": self.image_sha256,
            "preparedImageSha256": self.prepared_image_sha256,
            "audioSha256": self.audio_sha256,
            "preparedAudioSha256": self.prepared_audio_sha256,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def admitted_voice_resolution(resolution: str, duration_seconds: int) -> H3Resolution:
    selected = VOICE_RESOLUTIONS.get(resolution)
    if selected is None:
        raise GatewayError("voice_resolution_not_supported", 422)
    if duration_seconds < 5 or duration_seconds > 8:
        raise GatewayError("voice_duration_not_supported", 422)
    return selected


def canonical_voice(content: bytes) -> CanonicalVoice:
    """Accept only the trialed PCM form; rewrite its container header, never trim."""

    if not content or len(content) > MAX_VOICE_BYTES:
        raise GatewayError("voice_size_invalid", 413)
    try:
        with wave.open(BytesIO(content), "rb") as source:
            if (source.getcomptype(), source.getnchannels(), source.getsampwidth(), source.getframerate()) != (
                "NONE", 1, 2, VOICE_SAMPLE_RATE
            ):
                raise GatewayError("voice_format_not_supported", 422)
            frames = source.getnframes()
            duration_ms = frames * 1000 // VOICE_SAMPLE_RATE
            if not MIN_VOICE_DURATION_MS <= duration_ms <= MAX_VOICE_DURATION_MS:
                raise GatewayError("voice_duration_invalid", 422)
            samples = source.readframes(frames)
            if len(samples) != frames * 2:
                raise GatewayError("voice_decode_invalid", 422)
    except (wave.Error, EOFError, OSError) as error:
        raise GatewayError("voice_decode_invalid", 422) from error
    buffer = BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(VOICE_SAMPLE_RATE)
        target.writeframes(samples)
    prepared = buffer.getvalue()
    return CanonicalVoice(
        source_sha256=sha256(content).hexdigest(), prepared_sha256=sha256(prepared).hexdigest(),
        source_bytes=content, prepared_bytes=prepared, duration_ms=duration_ms,
    )


def voice_execution_from_snapshot(value: str) -> VoiceExecution:
    try:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise TypeError
        width = int(payload["width"])
        height = int(payload["height"])
        resolution = H3Resolution(str(payload["resolution"]), width, height)
        if resolution.value != f"{width}x{height}" or width <= 0 or height <= 0:
            raise ValueError
        if payload != json.loads(VoiceExecution(
            resolution=resolution,
            requested_duration_seconds=int(payload["requestedDurationSeconds"]),
            frame_count=int(payload["frameCount"]), seed=int(payload["seed"]),
            prompt_sha256=str(payload["promptSha256"]), image_name=str(payload["imageName"]),
            audio_name=str(payload["audioName"]), image_sha256=str(payload["imageSha256"]),
            prepared_image_sha256=str(payload["preparedImageSha256"]),
            audio_sha256=str(payload["audioSha256"]),
            prepared_audio_sha256=str(payload["preparedAudioSha256"]),
        ).snapshot_json()):
            raise ValueError
        if not all(len(payload[name]) == 64 for name in (
            "promptSha256", "imageSha256", "preparedImageSha256", "audioSha256", "preparedAudioSha256"
        )):
            raise ValueError
        if not 5 <= payload["requestedDurationSeconds"] <= 8 or payload["frameCount"] != frame_count_for_duration_seconds(
            payload["requestedDurationSeconds"]
        ):
            raise ValueError
        return VoiceExecution(
            resolution, int(payload["requestedDurationSeconds"]), int(payload["frameCount"]), int(payload["seed"]),
            str(payload["promptSha256"]), str(payload["imageName"]), str(payload["audioName"]),
            str(payload["imageSha256"]), str(payload["preparedImageSha256"]),
            str(payload["audioSha256"]), str(payload["preparedAudioSha256"]),
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid frozen Ref2VA execution snapshot") from None


def render_voice_workflow(template: dict[str, Any], *, execution: VoiceExecution, prompt: str) -> dict[str, Any]:
    """Reproduce the accepted first-frame-guide + standalone-audio Ref2VA graph."""

    if sha256(prompt.encode("utf-8")).hexdigest() != execution.prompt_sha256:
        raise ValueError("voice prompt differs from frozen snapshot")
    graph = copy.deepcopy(template)
    graph.pop("105:121")
    graph.pop("105:122")
    graph["105:6"]["inputs"] = {"unet_name": VOICE_MODEL, "weight_dtype": "default"}
    graph["105:9"]["inputs"] = {"scheduler": "simple", "steps": 20, "denoise": 1.0, "model": ["105:6", 0]}
    graph["105:16"]["inputs"] = {"model": ["105:6", 0], "conditioning": ["voice_first_frame_guide", 0]}
    graph["105:17"]["inputs"] = {"sampler_name": "res_multistep"}
    graph["105:15"]["inputs"] = {"noise_seed": execution.seed}
    graph["105:107"]["inputs"] = {"value": execution.frame_count}
    graph["115"]["inputs"] = {"value": execution.resolution.width}
    graph["116"]["inputs"] = {"value": execution.resolution.height}
    graph["voice_first_frame_image"] = {"class_type": "LoadImage", "inputs": {"image": execution.image_name}}
    graph["voice_reference_audio"] = {"class_type": "LoadAudio", "inputs": {"audio": execution.audio_name}}
    graph["105:104"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
        "clip": ["105:13", 0], "vae": ["105:11", 0], "audio_vae": ["105:24", 0],
        "prompt": prompt, "width": ["115", 0], "height": ["116", 0],
        "length": ["105:107", 0], "ref_image_size": "match",
        "ref_images.ref_image_0": ["voice_first_frame_image", 0],
        "ref_audios.ref_audio_0": ["voice_reference_audio", 0],
    }}
    graph["voice_first_frame_guide"] = {"class_type": "MiniMaxH3AddGuide", "inputs": {
        "positive": ["105:104", 0], "latent": ["105:104", 1],
        "vae": ["105:11", 0], "image": ["voice_first_frame_image", 0], "frame_idx": 0,
    }}
    return graph
