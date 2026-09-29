"""Compare two pinned reuse engines with the unchanged MOSS D reference.

This is an isolated Spark experiment, not a Voice Lab provider or Voice ID.
Run each engine in its own existing trial environment and output directory.
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


REFERENCE_TEXT = "雨还没有停。主灯，或者码头，我们只能先保住一边。"
REFERENCE_SHA256 = "da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae"
QWEN_REVISION = "fd4b254389122332181a7c3db7f27e918eec64e3"
INDEX_SOURCE_REVISION = "ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c"
INDEX_MODEL_REVISION = "740dcaff396282ffb241903d150ac011cd4b1ede"
EMOTION_URGENT = [0, 0, 0, 0.6, 0, 0, 0.3, 0]
LINES = (
    ("neutral", "灯塔的备用电源已经接通。我们还有十分钟检查航道。"),
    ("urgent", "等等，别打开那扇门！控制台还在报警，先把电源切断！"),
    ("gentle", "我知道你害怕。先跟着我的声音，慢慢呼吸，我们一起出去。"),
)
SEEDS = (20260930, 20261001)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def planned_cases(engine: str) -> list[tuple[str, str, int, list[int] | None]]:
    cases = [(label, text, seed, None) for label, text in LINES for seed in SEEDS]
    if engine == "index":
        urgent_text = next(text for label, text in LINES if label == "urgent")
        cases.extend(("urgent_controlled", urgent_text, seed, EMOTION_URGENT) for seed in SEEDS)
    return cases


def name_for(engine: str, label: str, seed: int) -> str:
    return f"moss_d_{engine}_{label}_seed-{seed}.wav"


def load_qwen(model_dir: Path, reference_audio: Path):
    from qwen_tts import Qwen3TTSModel

    model = Qwen3TTSModel.from_pretrained(
        str(model_dir), device_map="cuda:0", dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    prompt = model.create_voice_clone_prompt(
        ref_audio=str(reference_audio), ref_text=REFERENCE_TEXT,
        x_vector_only_mode=False,
    )
    return model, prompt


def load_index(model_dir: Path):
    from indextts.infer_v2 import IndexTTS2

    return IndexTTS2(
        cfg_path=str(model_dir / "config.yaml"), model_dir=str(model_dir),
        use_fp16=False, use_cuda_kernel=False, use_deepspeed=False,
        use_qwen_emo=False,
    )


def generate_qwen(model, prompt, text: str, output: Path) -> tuple[np.ndarray, int]:
    waveforms, sample_rate = model.generate_voice_clone(
        text=text, language="Chinese", voice_clone_prompt=prompt,
        do_sample=True,
    )
    if len(waveforms) != 1:
        raise ValueError("Qwen returned more than one waveform")
    waveform = np.asarray(waveforms[0], dtype=np.float32).reshape(-1)
    if not waveform.size or not np.isfinite(waveform).all():
        raise ValueError("Invalid Qwen waveform")
    # Retain unclipped float evidence; browser listening copies are separate.
    sf.write(output, waveform, sample_rate, subtype="FLOAT")
    return waveform, sample_rate


def generate_index(
    model, reference_audio: Path, text: str, emotion: list[int] | None,
    output: Path,
) -> tuple[np.ndarray, int]:
    temporary = output.with_suffix(".partial.wav")
    if temporary.exists():
        raise ValueError(f"Incomplete prior attempt needs inspection: {temporary}")
    model.infer(
        spk_audio_prompt=str(reference_audio), text=text,
        output_path=str(temporary), emo_vector=emotion,
        use_random=False, verbose=False,
    )
    waveform, sample_rate = sf.read(temporary)
    if waveform.ndim != 1 or not waveform.size or not np.isfinite(waveform).all():
        raise ValueError(f"Invalid Index waveform: {temporary}")
    os.replace(temporary, output)
    return waveform, sample_rate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("qwen", "index"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    reference_hash = sha256(args.reference_audio)
    if reference_hash != REFERENCE_SHA256:
        raise ValueError("Reference differs from owner-preferred original MOSS D")
    reference, reference_rate = sf.read(args.reference_audio)
    if reference.ndim != 1 or reference_rate != 24000 or not np.isfinite(reference).all():
        raise ValueError("Expected finite, mono, 24-kHz MOSS D reference")
    if args.engine == "index":
        if args.source_dir is None:
            parser.error("--source-dir is required for IndexTTS2")
        revision = subprocess.check_output(
            ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True,
        ).strip()
        if revision != INDEX_SOURCE_REVISION:
            raise ValueError("IndexTTS2 source revision changed")

    all_cases = planned_cases(args.engine)
    if args.limit is not None and not 1 <= args.limit <= len(all_cases):
        parser.error(f"--limit must be 1..{len(all_cases)}")
    cases = all_cases[: args.limit]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    metadata = {
        "purpose": "MOSS D Stage-2 reuse comparison; not voice publication",
        "engine": args.engine,
        "modelRevision": QWEN_REVISION if args.engine == "qwen" else INDEX_MODEL_REVISION,
        "sourceRevision": INDEX_SOURCE_REVISION if args.engine == "index" else None,
        "referenceAudioSha256": reference_hash,
        "referenceText": REFERENCE_TEXT,
        "normalizer": "native Linux WeTextProcessing" if args.engine == "index" else None,
        "cases": [],
    }
    manifest = metadata
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(manifest.get(key) != value for key, value in metadata.items() if key != "cases"):
            raise ValueError("Existing manifest belongs to another experiment")
    recorded = {entry["file"]: entry for entry in manifest["cases"]}
    if len(recorded) != len(manifest["cases"]):
        raise ValueError("Duplicate manifest entries")
    allowed_names = {name_for(args.engine, label, seed) for label, _, seed, _ in all_cases}
    if not set(recorded) <= allowed_names:
        raise ValueError("Manifest contains an unknown output")
    for name, entry in recorded.items():
        path = args.output_dir / name
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise ValueError(f"Recorded output changed: {name}")
    for label, _, seed, _ in cases:
        name = name_for(args.engine, label, seed)
        if name not in recorded and (args.output_dir / name).exists():
            raise ValueError(f"Unrecorded output exists: {name}")
    if all(name_for(args.engine, label, seed) in recorded for label, _, seed, _ in cases):
        return

    if args.engine == "qwen":
        model, prompt = load_qwen(args.model_dir, args.reference_audio)
    else:
        model = load_index(args.model_dir)
        prompt = None
    for label, text, seed, emotion in cases:
        name = name_for(args.engine, label, seed)
        if name in recorded:
            continue
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        output = args.output_dir / name
        started = time.monotonic()
        if args.engine == "qwen":
            waveform, sample_rate = generate_qwen(model, prompt, text, output)
        else:
            waveform, sample_rate = generate_index(
                model, args.reference_audio, text, emotion, output,
            )
        entry = {
            "case": label,
            "text": text,
            "seed": seed,
            "emotionVector": emotion,
            "file": name,
            "sampleRate": sample_rate,
            "durationSeconds": round(len(waveform) / sample_rate, 3),
            "peakAmplitude": round(float(np.max(np.abs(waveform))), 4),
            "generationSeconds": round(time.monotonic() - started, 2),
            "sha256": sha256(output),
        }
        manifest["cases"].append(entry)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    print(f"peakTorchAllocatedGiB={torch.cuda.max_memory_allocated() / 1024**3:.2f}", flush=True)


if __name__ == "__main__":
    main()
