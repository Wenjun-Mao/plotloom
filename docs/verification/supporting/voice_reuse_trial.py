"""Bounded Candidate A VoiceDesign-to-Base reuse experiment on Spark.

This is an experiment runner, not a Plotloom or gateway production component.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


REFERENCE_TEXT = "雨还没有停。主灯，或者码头，我们只能先保住一边。"
REFERENCE_SHA256 = "97f1d02937cc70b1dc7a1972333234afbfc7afddeac513b277fd961e9d171dfe"
BASE_REVISION = "fd4b254389122332181a7c3db7f27e918eec64e3"
CASES = (
    ("neutral", "灯塔的备用电源已经接通。我们还有十分钟检查航道。"),
    ("urgent", "等等，别打开那扇门！控制台还在报警，先把电源切断！"),
    ("gentle", "我知道你害怕。先跟着我的声音，慢慢呼吸，我们一起出去。"),
)
SEEDS = (20260930, 20261001)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=6, choices=range(1, 7))
    args = parser.parse_args()

    reference_hash = sha256(args.reference_audio)
    if reference_hash != REFERENCE_SHA256:
        raise ValueError("Candidate A reference hash does not match the reviewed original")
    reference_audio, reference_sr = sf.read(args.reference_audio)
    if reference_sr != 24000 or reference_audio.ndim != 1:
        raise ValueError("Expected mono 24 kHz Candidate A original")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest = {
        "purpose": "Candidate A speaker reuse; exploratory, not a canonical Voice ID",
        "model": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "modelRevision": BASE_REVISION,
        "referenceAudioSha256": reference_hash,
        "referenceText": REFERENCE_TEXT,
        "mode": "in-context voice clone; x_vector_only_mode=False",
        "cases": [],
    }
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(existing.get(key) != manifest[key] for key in manifest if key != "cases"):
            raise ValueError("Existing manifest belongs to a different experiment")
        manifest = existing

    planned = [
        (label, text, seed)
        for label, text in CASES
        for seed in SEEDS
    ][: args.limit]
    completed = {entry["file"]: entry for entry in manifest["cases"]}
    for label, _, seed in planned:
        name = f"candidate_a_clone_{label}_seed-{seed}.wav"
        if name in completed and sha256(args.output_dir / name) != completed[name]["sha256"]:
            raise ValueError(f"Previously generated audio changed: {name}")
        if name not in completed and (args.output_dir / name).exists():
            raise ValueError(f"Unrecorded audio exists; inspect before retrying: {name}")
    if all(f"candidate_a_clone_{label}_seed-{seed}.wav" in completed for label, _, seed in planned):
        return

    model = Qwen3TTSModel.from_pretrained(
        str(args.model_dir),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    prompt = model.create_voice_clone_prompt(
        ref_audio=str(args.reference_audio),
        ref_text=REFERENCE_TEXT,
        x_vector_only_mode=False,
    )

    for label, text, seed in planned:
        name = f"candidate_a_clone_{label}_seed-{seed}.wav"
        if name in completed:
            continue
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        started = time.monotonic()
        waveforms, sample_rate = model.generate_voice_clone(
            text=text,
            language="Chinese",
            voice_clone_prompt=prompt,
            do_sample=True,
        )
        if len(waveforms) != 1:
            raise ValueError("Expected one waveform per generation")
        waveform = np.asarray(waveforms[0], dtype=np.float32).reshape(-1)
        if not waveform.size or not np.all(np.isfinite(waveform)):
            raise ValueError("Empty or non-finite generated waveform")
        output_path = args.output_dir / name
        sf.write(output_path, waveform, sample_rate, subtype="PCM_16")
        entry = {
            "case": label,
            "text": text,
            "seed": seed,
            "file": name,
            "sampleRate": sample_rate,
            "durationSeconds": round(len(waveform) / sample_rate, 3),
            "peakAmplitude": round(float(np.max(np.abs(waveform))), 4),
            "elapsedSeconds": round(time.monotonic() - started, 2),
            "sha256": sha256(output_path),
        }
        manifest["cases"].append(entry)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
