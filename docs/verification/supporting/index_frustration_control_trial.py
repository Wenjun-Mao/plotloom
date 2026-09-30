"""Four-take, fixed-line comparison of positive Chinese text and explicit anger.

Copy beside index_chinese_emotion_trial.py. Inspect once, then generate in a
fresh directory. This is an isolated trial, not a Voice Lab provider change.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from index_chinese_emotion_trial import (
    ALPHA, EMOTIONS, SEEDS, checked_emotions, seed_all, sha256,
    specification as checked_setup, write_json,
)


TEXT = "这已经是第三次了。我不是责怪你，但我们不能再把同一个问题留到明天。"
DIRECTION = "对问题反复出现感到不满和挫败，带一点恼火把要求说清楚。语气严肃、坚定，情绪力度适中，表达克制而有分量。"
ANGER_VECTOR = [0, 0.25, 0, 0, 0, 0, 0, 0]
ARMS = ("positive_text", "explicit_anger")


def inspect(args, spec: dict) -> None:
    from indextts.infer_v2 import QwenEmotion

    target = args.output_dir / "interpretation.json"
    if target.exists():
        raise ValueError("Retained interpretation exists; do not overwrite")
    seed_all(SEEDS[0])
    helper = QwenEmotion(str(args.model_dir / "qwen0.6bemo4-merge"))
    started = time.monotonic()
    scores = checked_emotions(helper.inference(DIRECTION))
    result = {
        "specification": spec, "textModeEmotions": scores,
        "vectorModeEmotions": dict(zip(EMOTIONS, ANGER_VECTOR)),
        "classifierSeconds": round(time.monotonic() - started, 2),
    }
    write_json(target, result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def generate(args, spec: dict) -> None:
    from indextts.infer_v2 import IndexTTS2

    inspection = json.loads((args.output_dir / "interpretation.json").read_text(encoding="utf-8"))
    if inspection["specification"] != spec:
        raise ValueError("Inspection specification differs")
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists() or list(args.output_dir.glob("*.wav")):
        raise ValueError("Prior outputs exist; inspect before another generation")
    manifest = {"specification": spec, "inspection": inspection, "cases": []}
    write_json(manifest_path, manifest)
    model = IndexTTS2(
        cfg_path=str(args.model_dir / "config.yaml"), model_dir=str(args.model_dir),
        use_fp16=False, use_cuda_kernel=False, use_deepspeed=False, use_qwen_emo=True,
    )
    classify = model.qwen_emo.inference
    observed = []

    def record_classification(description: str):
        scores = checked_emotions(classify(description))
        observed.append(scores)
        return scores

    model.qwen_emo.inference = record_classification
    for arm in ARMS:
        for seed in SEEDS:
            seed_all(seed)
            observed.clear()
            output = args.output_dir / f"moss_d_index_frustration_{arm}_seed-{seed}.wav"
            temporary = output.with_suffix(".partial.wav")
            controls = (
                {"use_emo_text": True, "emo_text": DIRECTION}
                if arm == "positive_text" else
                {"use_emo_text": False, "emo_vector": list(ANGER_VECTOR)}
            )
            started = time.monotonic()
            model.infer(
                spk_audio_prompt=str(args.reference_audio), text=TEXT,
                output_path=str(temporary), emo_alpha=ALPHA,
                use_random=False, verbose=False, **controls,
            )
            expected_calls = 1 if arm == "positive_text" else 0
            if len(observed) != expected_calls:
                raise ValueError("Unexpected emotion-classifier invocation count")
            waveform, rate = sf.read(temporary)
            if waveform.ndim != 1 or not waveform.size or not np.isfinite(waveform).all():
                raise ValueError("Invalid waveform")
            os.replace(temporary, output)
            scores = observed[0] if observed else dict(zip(EMOTIONS, ANGER_VECTOR))
            entry = {
                "arm": arm, "seed": seed, "file": output.name,
                "emotions": scores, "classifierCalls": len(observed),
                "matchesPreviewInterpretation": (
                    scores == inspection["textModeEmotions"] if observed else None
                ),
                "sampleRate": rate, "durationSeconds": round(len(waveform) / rate, 3),
                "peakAmplitude": round(float(np.abs(waveform).max()), 4),
                "fullScaleSamples": int(np.count_nonzero((waveform <= -1.0) | (waveform >= 32767 / 32768))),
                "sampleCount": len(waveform), "subtype": sf.info(output).subtype,
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
    spec = {key: value for key, value in checked_setup(args).items() if key not in {"purpose", "direction", "text", "useEmoText"}}
    spec.update({
        "purpose": "Four-take frustration text/vector comparison; not production integration",
        "text": TEXT, "direction": DIRECTION, "explicitVector": ANGER_VECTOR,
        "arms": list(ARMS), "runnerSha256": sha256(Path(__file__)),
        "sharedRunnerSha256": sha256(Path(__file__).with_name("index_chinese_emotion_trial.py")),
    })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (inspect if args.phase == "inspect" else generate)(args, spec)


if __name__ == "__main__":
    main()
