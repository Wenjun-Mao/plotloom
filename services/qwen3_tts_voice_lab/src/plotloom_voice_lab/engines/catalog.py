"""Versioned public execution identities; filesystem configuration stays private."""

from __future__ import annotations

import copy

from ..identity import BASE_MODEL, BASE_REVISION, DESIGN_MODEL, DESIGN_REVISION


EMOTIONS = ("happy", "angry", "sad", "afraid", "disgusted", "melancholic", "surprised", "calm")
ADAPTER_VERSION = "voice_lab_process.v1"
CATALOG = {
    "qwen_design": {
        "stage": "creation", "label": "Qwen VoiceDesign", "modelId": DESIGN_MODEL,
        "modelRevision": DESIGN_REVISION, "sampleRate": 24000,
        "settings": {"dtype": "bfloat16", "attention": "sdpa", "language": "Chinese", "doSample": True},
    },
    "moss_design": {
        "stage": "creation", "label": "MOSS VoiceGenerator",
        "modelId": "OpenMOSS-Team/MOSS-VoiceGenerator",
        "modelRevision": "97521ec2b6f3ec5026ac1f5751f8fc302d82c2d4", "sampleRate": 24000,
        "sourceRevision": "934d6826b084c46a0d033402174d5f8ac4ed2519",
        "codecRevision": "3cd226ba2947efa357ef453bcad111b6eafba782",
        "settings": {"dtype": "bfloat16", "attention": "sdpa", "audio_temperature": 1.5,
                     "audio_top_p": 0.6, "audio_top_k": 50, "audio_repetition_penalty": 1.1,
                     "max_new_tokens": 4096},
    },
    "qwen_base": {
        "stage": "reuse", "label": "Qwen Base", "modelId": BASE_MODEL,
        "modelRevision": BASE_REVISION, "sampleRate": 24000,
        "settings": {"dtype": "bfloat16", "attention": "sdpa", "language": "Chinese",
                     "doSample": True, "xVectorOnly": False},
    },
    "index_base": {
        "stage": "reuse", "label": "IndexTTS2", "modelId": "IndexTeam/IndexTTS-2",
        "modelRevision": "740dcaff396282ffb241903d150ac011cd4b1ede", "sampleRate": 22050,
        "sourceRevision": "ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c",
        "classifierSha256": "11293257a8df593c154a8ecd5fc039f3076de35411e35f06d41b471e136f6641",
        "settings": {"dtype": "float32", "useCudaKernel": False, "useDeepspeed": False,
                     "useRandom": False, "emoAlpha": 1.0, "normalizer": "linux_WeTextProcessing"},
    },
}


def snapshot(engine_id: str, stage: str) -> dict:
    spec = CATALOG.get(engine_id)
    if spec is None or spec["stage"] != stage:
        raise ValueError("engine.stage_invalid")
    from .process import runtime_config, runtime_fingerprint
    runtime = runtime_config().get(engine_id)
    return {"schemaVersion": 1, "engineId": engine_id, "adapterVersion": ADAPTER_VERSION,
            "runtimeFingerprint": runtime_fingerprint(runtime) if runtime else None, **copy.deepcopy(spec)}


def validate_snapshot(value: dict) -> None:
    if value != snapshot(value.get("engineId"), value.get("stage")):
        raise ValueError("engine.snapshot_unavailable")


def public_catalog() -> list[dict]:
    return [snapshot(key, value["stage"]) for key, value in CATALOG.items()]
