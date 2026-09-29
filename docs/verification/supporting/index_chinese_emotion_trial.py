"""Two-take Chinese emo_text trial with the unchanged original MOSS D voice.

Run inspect first, then generate in the pinned IndexTTS2 Spark environment.
The generation phase uses the actual use_emo_text route, not a substituted vector.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch


REFERENCE_SHA256 = "da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae"
SOURCE_REVISION = "ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c"
MODEL_REVISION = "740dcaff396282ffb241903d150ac011cd4b1ede"
DIRECTION = "情况紧迫，果断地制止对方。语气坚定，立即行动，不恐慌、不害怕。"
TEXT = "等等，别打开那扇门！控制台还在报警，先把电源切断！"
SEEDS = (20260930, 20261001)
EMOTIONS = ("happy", "angry", "sad", "afraid", "disgusted", "melancholic", "surprised", "calm")
ALPHA = 1.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".partial.json")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def checked_emotions(value: dict) -> dict:
    if tuple(value) != EMOTIONS:
        raise ValueError("Classifier emotion keys/order differ from the pinned contract")
    if any(not np.isfinite(score) or not 0 <= score <= 1.2 for score in value.values()):
        raise ValueError("Invalid classifier scores")
    return dict(value)


def specification(args) -> dict:
    revision = subprocess.check_output(
        ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True,
    ).strip()
    if revision != SOURCE_REVISION or sha256(args.reference_audio) != REFERENCE_SHA256:
        raise ValueError("Pinned source or original MOSS D reference changed")
    reference, rate = sf.read(args.reference_audio)
    if rate != 24000 or reference.ndim != 1 or not reference.size or not np.isfinite(reference).all():
        raise ValueError("Expected finite mono 24-kHz reference")
    return {
        "purpose": "Chinese emotion interpretation and urgency listening trial; not voice publication",
        "sourceRevision": revision,
        "sourceFileSha256": sha256(args.source_dir / "indextts/infer_v2.py"),
        "modelRevision": MODEL_REVISION,
        "emotionModelSha256": sha256(args.model_dir / "qwen0.6bemo4-merge/model.safetensors"),
        "referenceSha256": REFERENCE_SHA256,
        "direction": DIRECTION,
        "text": TEXT,
        "seeds": list(SEEDS),
        "emotionOrder": list(EMOTIONS),
        "emoAlpha": ALPHA,
        "useEmoText": True,
        "useRandom": False,
        "normalizer": "native Linux WeTextProcessing",
    }


def inspect(args, spec: dict) -> None:
    from indextts.infer_v2 import QwenEmotion

    path = args.output_dir / "interpretation.json"
    if path.exists():
        raise ValueError("Retained interpretation already exists; do not overwrite")
    seed_all(SEEDS[0])
    helper = QwenEmotion(str(args.model_dir / "qwen0.6bemo4-merge"))
    started = time.monotonic()
    scores = checked_emotions(helper.inference(DIRECTION))
    evidence = {"specification": spec, "emotions": scores, "classifierSeconds": round(time.monotonic() - started, 2)}
    write_json(path, evidence)
    print(json.dumps(evidence, ensure_ascii=False), flush=True)


def generate(args, spec: dict) -> None:
    from indextts.infer_v2 import IndexTTS2

    inspection = json.loads((args.output_dir / "interpretation.json").read_text(encoding="utf-8"))
    if inspection["specification"] != spec:
        raise ValueError("Inspection belongs to a different trial specification")
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists() or list(args.output_dir.glob("*.wav")):
        raise ValueError("Outputs already exist; inspect evidence before any further generation")
    manifest = {"specification": spec, "inspection": inspection, "cases": []}
    write_json(manifest_path, manifest)
    model = IndexTTS2(
        cfg_path=str(args.model_dir / "config.yaml"), model_dir=str(args.model_dir),
        use_fp16=False, use_cuda_kernel=False, use_deepspeed=False, use_qwen_emo=True,
    )
    classify = model.qwen_emo.inference
    observed = []

    def record_classification(description: str):
        # Observe the real helper result without changing its values or RNG behavior.
        scores = checked_emotions(classify(description))
        observed.append(scores)
        print(json.dumps({"classifierEmotions": scores}, ensure_ascii=False), flush=True)
        return scores

    model.qwen_emo.inference = record_classification
    for seed in SEEDS:
        seed_all(seed)
        observed.clear()
        name = f"moss_d_index_chinese_direction_seed-{seed}.wav"
        output = args.output_dir / name
        temporary = output.with_suffix(".partial.wav")
        started = time.monotonic()
        model.infer(
            spk_audio_prompt=str(args.reference_audio), text=TEXT,
            output_path=str(temporary), use_emo_text=True, emo_text=DIRECTION,
            emo_alpha=ALPHA, use_random=False, verbose=False,
        )
        waveform, rate = sf.read(temporary)
        if waveform.ndim != 1 or not waveform.size or not np.isfinite(waveform).all() or len(observed) != 1:
            raise ValueError("Invalid waveform or unexpected emotion-classifier invocation count")
        os.replace(temporary, output)
        entry = {
            "seed": seed, "file": name, "emotions": observed[0],
            "matchesPreviewInterpretation": observed[0] == inspection["emotions"],
            "sampleRate": rate, "durationSeconds": round(len(waveform) / rate, 3),
            "peakAmplitude": round(float(np.abs(waveform).max()), 4),
            "elapsedSeconds": round(time.monotonic() - started, 2), "sha256": sha256(output),
        }
        manifest["cases"].append(entry)
        write_json(manifest_path, manifest)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    print(f"peakTorchAllocatedGiB={torch.cuda.max_memory_allocated() / 1024**3:.2f}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("inspect", "generate"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    spec = specification(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.phase == "inspect":
        inspect(args, spec)
    else:
        generate(args, spec)


if __name__ == "__main__":
    main()
