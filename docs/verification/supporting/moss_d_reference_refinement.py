"""Bounded, isolated MOSS D refinement; never publishes a Voice ID.

Use the same spoken line, pinned model, and decoding as the first audition.
Paired seeds separate a direction change from stochastic variation.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel, AutoProcessor

from moss_voice_generator_trial import AUDITION_TEXT, CODEC_REVISION, DECODING, MODEL_REVISION, sha256


D_ORIGINAL = "四十岁左右的中国女性，成熟、略有颗粒感的低音，克制而坚韧；停顿自然，语速偏慢，不要播音腔。"
D_CONVERSATIONAL = "四十岁左右的中国女性，成熟、略有颗粒感的低音，克制而坚韧；像对身边的人说话，不是朗诵。语速自然，短暂停顿，不要播音腔。"
CASES = tuple(
    (f"d_{direction}_{seed}", seed, instruction)
    for direction, instruction in (("original", D_ORIGINAL), ("conversational", D_CONVERSATIONAL))
    for seed in (20261001, 20261002)
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--codec-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    # Refuse to overwrite any evidence from an earlier invocation.
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"Output directory is not empty: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    torch.backends.cuda.enable_cudnn_sdp(False)
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

    receipt = {
        "purpose": "MOSS D Stage-1 reference search; not product acceptance",
        "modelRevision": MODEL_REVISION,
        "codecRevision": CODEC_REVISION,
        "decoding": DECODING,
        "text": AUDITION_TEXT,
        "sampleRate": sample_rate,
        "audioSubtype": "FLOAT",
        "cases": [],
    }
    for case, seed, instruction in CASES:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        conversation = [[processor.build_user_message(text=AUDITION_TEXT, instruction=instruction)]]
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
        output = args.output_dir / f"{case}.wav"
        sf.write(output, audio, sample_rate, subtype="FLOAT")
        entry = {
            "case": case,
            "seed": seed,
            "instruction": instruction,
            "file": output.name,
            "durationSeconds": round(audio.size / sample_rate, 3),
            "peakAmplitude": round(float(np.max(np.abs(audio))), 4),
            "generationSeconds": round(time.monotonic() - started, 2),
            "sha256": sha256(output),
        }
        receipt["cases"].append(entry)
        # Persist completed entries even if a later candidate fails.
        (args.output_dir / "manifest.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(entry, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
