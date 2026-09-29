"""Isolated IndexTTS2 reuse comparison for the reviewed Candidate A voice.

Run only on Spark's trial environment. This does not alter Voice Lab or Plotloom.
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


SOURCE_REVISION = "ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c"
MODEL_REVISION = "740dcaff396282ffb241903d150ac011cd4b1ede"
REFERENCE_SHA256 = "97f1d02937cc70b1dc7a1972333234afbfc7afddeac513b277fd961e9d171dfe"
CASES = (
    ("neutral", "灯塔的备用电源已经接通。我们还有十分钟检查航道。", None),
    ("urgent", "等等，别打开那扇门！控制台还在报警，先把电源切断！", None),
    ("gentle", "我知道你害怕。先跟着我的声音，慢慢呼吸，我们一起出去。", None),
    # Test whether separate acting control improves the previously flat urgent line.
    ("urgent_controlled", "等等，别打开那扇门！控制台还在报警，先把电源切断！", [0, 0, 0, 0.6, 0, 0, 0.3, 0]),
)
SEEDS = (20260930, 20261001)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def use_wetext_normalizer() -> None:
    """Select upstream's alternative WeText backend for this ARM-only trial.

    The upstream Linux branch requires Pynini, which has no PyPI ARM64 wheel.
    This adapter is a trial constraint, not an approved production divergence.
    """
    from indextts.utils.front import TextNormalizer
    from wetext import Normalizer

    def load(self: TextNormalizer) -> None:
        if self.zh_normalizer is None or self.en_normalizer is None:
            self.zh_normalizer = Normalizer(remove_erhua=False, lang="zh", operator="tn")
            self.en_normalizer = Normalizer(lang="en", operator="tn")

    TextNormalizer.load = load


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=8, choices=range(1, 9))
    parser.add_argument("--normalizer-backend", choices=("wetext", "linux"), default="wetext")
    args = parser.parse_args()

    source_revision = subprocess.check_output(
        ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    if source_revision != SOURCE_REVISION:
        raise ValueError("IndexTTS2 source revision changed")
    if sha256(args.reference_audio) != REFERENCE_SHA256:
        raise ValueError("Reference is not the reviewed Candidate A recording")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    planned = [
        (label, text, emotion, seed)
        for label, text, emotion in CASES
        for seed in SEEDS
    ][: args.limit]
    manifest_path = args.output_dir / "manifest.json"
    manifest = {
        "purpose": "IndexTTS2 versus Qwen Base; exploratory speaker reuse",
        "sourceRevision": SOURCE_REVISION,
        "modelRevision": MODEL_REVISION,
        "referenceAudioSha256": REFERENCE_SHA256,
        "normalizer": (
            "upstream WeText backend selected on ARM64 (trial only)"
            if args.normalizer_backend == "wetext"
            else "upstream Linux WeTextProcessing backend (isolated ARM64 trial)"
        ),
        "precision": "fp32",
        "cases": [],
    }
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(existing.get(key) != value for key, value in manifest.items() if key != "cases"):
            raise ValueError("Existing manifest belongs to another experiment")
        manifest = existing
    recorded = {entry["file"]: entry for entry in manifest["cases"]}
    for label, _, _, seed in planned:
        name = f"candidate_a_indextts2_{label}_seed-{seed}.wav"
        path = args.output_dir / name
        if name in recorded and (not path.is_file() or sha256(path) != recorded[name]["sha256"]):
            raise ValueError(f"Recorded output changed: {name}")
        if name not in recorded and path.exists():
            raise ValueError(f"Unrecorded output exists: {name}")
    if len(recorded) >= args.limit:
        return

    if args.normalizer_backend == "wetext":
        use_wetext_normalizer()
    from indextts.infer_v2 import IndexTTS2

    model = IndexTTS2(
        cfg_path=str(args.model_dir / "config.yaml"),
        model_dir=str(args.model_dir),
        use_fp16=False,
        use_cuda_kernel=False,
        use_deepspeed=False,
        use_qwen_emo=False,
    )
    torch.cuda.reset_peak_memory_stats()
    for label, text, emotion, seed in planned:
        name = f"candidate_a_indextts2_{label}_seed-{seed}.wav"
        if name in recorded:
            continue
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        output = args.output_dir / name
        temporary = output.with_suffix(".partial.wav")
        if temporary.exists():
            raise ValueError(f"Incomplete prior attempt needs inspection: {temporary}")
        started = time.monotonic()
        model.infer(
            spk_audio_prompt=str(args.reference_audio),
            text=text,
            output_path=str(temporary),
            emo_vector=emotion,
            use_random=False,
            verbose=False,
        )
        audio, sample_rate = sf.read(temporary)
        if not audio.size or not np.isfinite(audio).all():
            raise ValueError(f"Invalid generated audio: {temporary}")
        os.replace(temporary, output)
        entry = {
            "case": label,
            "text": text,
            "emotionVector": emotion,
            "seed": seed,
            "file": name,
            "sampleRate": sample_rate,
            "durationSeconds": round(len(audio) / sample_rate, 3),
            "peakAmplitude": round(float(np.max(np.abs(audio))), 4),
            "elapsedSeconds": round(time.monotonic() - started, 2),
            "sha256": sha256(output),
        }
        manifest["cases"].append(entry)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    print(f"peakTorchAllocatedGiB={torch.cuda.max_memory_allocated() / 1024**3:.2f}", flush=True)


if __name__ == "__main__":
    main()
