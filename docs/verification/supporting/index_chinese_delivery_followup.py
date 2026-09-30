"""Six-take delivery follow-up, preserving the original Chinese trial evidence.

Copy this script and index_chinese_emotion_trial.py together. Inspect the three
directions first; generate exactly two seeds per new line in a fresh directory.
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
    ALPHA, SEEDS, checked_emotions, seed_all, sha256,
    specification as checked_setup, write_json,
)


CASES = (
    {
        "id": "decisive_urgency",
        "text": "先停下来，别碰那个开关！把人带到出口，我马上切断主电源。",
        "direction": "情况紧迫，果断地制止对方。语气坚定，立即行动，不恐慌、不害怕。",
    },
    {
        "id": "gentle_reassurance",
        "text": "别着急，我在这里。先慢慢呼吸，等你准备好了，我们再一起往前走。",
        "direction": "温柔地安慰对方，声音平稳、亲近、耐心。让对方感到安全，不哭泣、不夸张、不用哄小孩的语气。",
    },
    {
        "id": "restrained_frustration",
        "text": "这已经是第三次了。我不是责怪你，但我们不能再把同一个问题留到明天。",
        "direction": "感到不满和挫败，但克制地把问题说清楚。语气认真、有分寸，不大声斥责，不嘲讽，也不显得委屈或害怕。",
    },
)


def inspect(args, spec: dict) -> None:
    from indextts.infer_v2 import QwenEmotion

    target = args.output_dir / "interpretation.json"
    if target.exists():
        raise ValueError("Retained interpretation exists; do not overwrite")
    helper = QwenEmotion(str(args.model_dir / "qwen0.6bemo4-merge"))
    entries = []
    for case in CASES:
        seed_all(SEEDS[0])
        started = time.monotonic()
        scores = checked_emotions(helper.inference(case["direction"]))
        entry = {**case, "emotions": scores, "elapsedSeconds": round(time.monotonic() - started, 2)}
        entries.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    write_json(target, {"specification": spec, "cases": entries})


def generate(args, spec: dict) -> None:
    from indextts.infer_v2 import IndexTTS2

    inspection = json.loads((args.output_dir / "interpretation.json").read_text(encoding="utf-8"))
    if inspection["specification"] != spec:
        raise ValueError("Inspection specification differs")
    previews = {entry["id"]: entry["emotions"] for entry in inspection["cases"]}
    if set(previews) != {case["id"] for case in CASES}:
        raise ValueError("Inspection does not cover the exact three cases")
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists() or list(args.output_dir.glob("*.wav")):
        raise ValueError("Prior outputs exist; inspect before any further generation")
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
    for case in CASES:
        for seed in SEEDS:
            seed_all(seed)
            observed.clear()
            name = f"moss_d_index_{case['id']}_seed-{seed}.wav"
            output = args.output_dir / name
            temporary = output.with_suffix(".partial.wav")
            started = time.monotonic()
            model.infer(
                spk_audio_prompt=str(args.reference_audio), text=case["text"],
                output_path=str(temporary), use_emo_text=True, emo_text=case["direction"],
                emo_alpha=ALPHA, use_random=False, verbose=False,
            )
            waveform, rate = sf.read(temporary)
            if waveform.ndim != 1 or not waveform.size or not np.isfinite(waveform).all() or len(observed) != 1:
                raise ValueError("Invalid audio or unexpected classifier invocation count")
            os.replace(temporary, output)
            entry = {
                **case, "seed": seed, "file": name, "emotions": observed[0],
                "matchesPreviewInterpretation": observed[0] == previews[case["id"]],
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
    spec = {key: value for key, value in checked_setup(args).items() if key not in {"purpose", "direction", "text"}}
    spec.update({
        "purpose": "Three new Chinese delivery cases, two seeds each; not production integration",
        "cases": list(CASES),
        "runnerSha256": sha256(Path(__file__)),
        "sharedRunnerSha256": sha256(Path(__file__).with_name("index_chinese_emotion_trial.py")),
    })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (inspect if args.phase == "inspect" else generate)(args, spec)


if __name__ == "__main__":
    main()
