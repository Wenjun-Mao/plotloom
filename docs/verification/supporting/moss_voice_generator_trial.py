"""Isolated MOSS VoiceGenerator audition against the earlier Qwen voice-design set.

Run on Spark only. This does not publish a Voice ID or modify the Voice Lab.
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
from transformers import AutoModel, AutoProcessor


AUDITION_TEXT = "雨还没有停。主灯，或者码头，我们只能先保住一边。"
URGENT_TEXT = "等等，别打开那扇门！控制台还在报警，先把电源切断！"
CASES = (
    ("a", 20260926, "三十岁左右的中国女性，中低音，冷静而坚定，略带沙哑，吐字自然，语速中等，不要播音腔。", AUDITION_TEXT),
    ("b", 20260927, "三十五岁左右的中国女性，温暖沉稳的女中音，带一点自然气声；冷静、可信赖，语速中等，不要播音腔。", AUDITION_TEXT),
    ("c", 20260928, "二十多岁的中国女性，清亮但不尖锐的中音，果断敏捷，语速稍快；自然口语，不要夸张表演。", AUDITION_TEXT),
    ("d", 20260929, "四十岁左右的中国女性，成熟、略有颗粒感的低音，克制而坚韧；停顿自然，语速偏慢，不要播音腔。", AUDITION_TEXT),
    ("a_urgent", 20260930, "三十岁左右的中国女性，中低音，冷静而坚定，略带沙哑，自然口语。此句紧急制止，语速和气息明显加快。", URGENT_TEXT),
)
MODEL_REVISION = "97521ec2b6f3ec5026ac1f5751f8fc302d82c2d4"
CODEC_REVISION = "3cd226ba2947efa357ef453bcad111b6eafba782"
DECODING = {
    "audio_temperature": 1.5,
    "audio_top_p": 0.6,
    "audio_top_k": 50,
    "audio_repetition_penalty": 1.1,
    "max_new_tokens": 4096,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--codec-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=len(CASES), choices=range(1, len(CASES) + 1))
    args = parser.parse_args()

    torch.backends.cuda.enable_cudnn_sdp(False)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = args.output_dir / "manifest.json"
    receipt = {
        "purpose": "MOSS vs Qwen VoiceDesign bounded audition; not product acceptance",
        "model": "OpenMOSS-Team/MOSS-VoiceGenerator",
        "modelRevision": MODEL_REVISION,
        "codecRevision": CODEC_REVISION,
        "decoding": DECODING,
        "audioSubtype": "FLOAT",
        "cases": [],
    }
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if any(existing.get(key) != receipt[key] for key in receipt if key != "cases"):
            raise ValueError("Existing manifest belongs to a different trial")
        receipt = existing
    completed = {entry["case"]: entry for entry in receipt["cases"]}
    for case, _, _, _ in CASES[: args.limit]:
        output = args.output_dir / f"moss_{case}.wav"
        if case in completed and (not output.exists() or sha256(output) != completed[case]["sha256"]):
            raise ValueError(f"Previously generated audio changed: {case}")
        if case not in completed and output.exists():
            raise ValueError(f"Unrecorded audio exists: {output}")
    if all(case in completed for case, _, _, _ in CASES[: args.limit]):
        return

    processor = AutoProcessor.from_pretrained(
        str(args.model_dir), codec_path=str(args.codec_dir), trust_remote_code=True,
        normalize_inputs=True,
    )
    processor.audio_tokenizer = processor.audio_tokenizer.to("cuda")
    model = AutoModel.from_pretrained(
        str(args.model_dir), trust_remote_code=True, local_files_only=True,
        attn_implementation="sdpa", dtype=torch.bfloat16,
    ).to("cuda")
    model.eval()
    sample_rate = int(processor.model_config.sampling_rate)

    for case, seed, instruction, text in CASES[: args.limit]:
        if case in completed:
            continue
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        conversation = [[processor.build_user_message(text=text, instruction=instruction)]]
        batch = processor(conversation, mode="generation")
        started = time.monotonic()
        with torch.inference_mode():
            outputs = model.generate(
                input_ids=batch["input_ids"].to("cuda"),
                attention_mask=batch["attention_mask"].to("cuda"),
                **DECODING,
            )
        messages = processor.decode(outputs)
        if len(messages) != 1 or not messages[0].audio_codes_list:
            raise ValueError(f"No decoded audio for {case}")
        audio = messages[0].audio_codes_list[0].detach().float().cpu().numpy().reshape(-1)
        if not audio.size or not np.isfinite(audio).all():
            raise ValueError(f"Empty or non-finite audio for {case}")
        output_path = args.output_dir / f"moss_{case}.wav"
        # Preserve raw model amplitudes; 16-bit PCM would clip samples above 1.0.
        sf.write(output_path, audio, sample_rate, subtype="FLOAT")
        entry = {
            "case": case,
            "seed": seed,
            "text": text,
            "instruction": instruction,
            "file": output_path.name,
            "sampleRate": sample_rate,
            "durationSeconds": round(audio.size / sample_rate, 3),
            "peakAmplitude": round(float(np.max(np.abs(audio))), 4),
            "elapsedSeconds": round(time.monotonic() - started, 2),
            "sha256": sha256(output_path),
        }
        receipt["cases"].append(entry)
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
