# IndexTTS2 Linux text-normalizer qualification on Spark

**Status:** The native Linux normalizer and the prior ARM64 trial fallback produced
identical normalized strings in 30 fixed cases. One pinned full-inference Linux
smoke produced a byte-identical WAV to the prior fallback run. This resolves the
specific text-front-end comparison for these inputs; it does **not** select
IndexTTS2 as Voice Lab's reuse engine or establish general audio quality.

## Why this comparison was needed

The [earlier IndexTTS2 reuse trial](2026-09-29-indextts2-reuse-trial.md) used
upstream's `wetext` backend on Spark because PyPI did not offer a Pynini ARM64
wheel and a source build failed. Upstream's Linux path instead imports
`tn.chinese` and `tn.english` from WeTextProcessing. That difference could have
changed what the model heard, especially for numbers, English, punctuation,
interjections, or 儿化. This experiment tested the boundary rather than assuming
the two paths were equivalent.

## Isolated setup

- IndexTTS2 source remains pinned at
  `ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c`, with a clean checkout.
- A separate micromamba prefix at
  `/home/wjmao/services/index-tts2-trial/linux-normalizer` supplies conda-forge
  `pynini==2.1.7` for Linux ARM64 and PyPI `WeTextProcessing==1.2.0`.
  The inference process continued using the trial's Python 3.12.3 and
  PyTorch `2.14.0+cu130` environment; only that process's `PYTHONPATH` and
  `LD_LIBRARY_PATH` pointed at the isolated normalizer prefix. The previous
  inference environment and live Voice Lab were not modified.
- The fallback used the trial's `wetext==0.1.8` and the same
  `TextNormalizer` class, with only its `load()` backend choice overridden.
- Reproduction entrypoint:
  [index_tts2_normalizer_compare.py](supporting/index_tts2_normalizer_compare.py).
  It checks the source commit before normalizing.
- Generated JSON evidence on Spark:
  `/home/wjmao/services/index-tts2-trial/experiments/2026-09-29-normalizer-qualification/`.
  SHA-256: `wetext-v2.json` = `85c680d226984fb0a46ff7de39fbc9f06b09d47d9cf1b444ed2d731c2952e896`;
  `linux-v2.json` = `c5d5adf2653a5d2cd1b077da028d4b4addf416792c88b8e92b0160381132c4f0`.

To repeat the comparison from the trial directory, run the script once with
`--backend wetext` using `PYTHONPATH=<source>` and the trial `.venv/bin/python`.
Run it again with `--backend linux`, additionally prepending the isolated
normalizer's `lib/python3.12/site-packages` to `PYTHONPATH` and its `lib` to
`LD_LIBRARY_PATH`. Pass the pinned `--source-dir` and distinct `--output`
paths both times. Compare `cases[].normalized` by case ID, not whole JSON
files. This uses upstream's unchanged Linux `TextNormalizer.load()` path.

The 30 cases include the previous neutral/urgent/gentle lines, quantities and
digits, time/date, temperature, distance, codes, currency, names, acronyms,
mixed language, pronunciation annotation, punctuation, four interjections,
two 儿化 cases, repeated fillers, rapid instructions, and English. All 30
normalized strings matched exactly. The JSON file hashes differ because each
records its backend name, not because its normalized text differs. This is a
bounded fixture result, not proof of universal equivalence; neither backend
was judged correct for every pronunciation (for example, both render the
currency fixture awkwardly).

## Full-inference smoke

The [reuse trial runner](supporting/index_tts2_reuse_trial.py) gained an
explicit `--normalizer-backend=linux|wetext` choice, with the original fallback
as its unchanged default. With the same Candidate A reference WAV (SHA-256
`97f1d02937cc70b1dc7a1972333234afbfc7afddeac513b277fd961e9d171dfe`),
neutral line, seed `20260930`, and pinned Index checkpoint, the native Linux
backend generated a valid 22,050 Hz WAV of 4.493 seconds. Its SHA-256 was
`8eb0ab5a9b61cdcd3d57495167ea4f5f5990264339b602b10dc06965036fc36f`,
**identical** to the retained fallback WAV. Linux smoke output and manifest are
under `/home/wjmao/services/index-tts2-trial/experiments/2026-09-29-linux-normalizer-smoke/`.
The process-reported peak PyTorch allocation was 7.55 GiB; that is not total
system or GPU peak. No additional listening clips were generated because the
normalized text did not differ.

ComfyUI's queue was empty before and after. Qwen Image was temporarily stopped
to free memory, then restarted; its `/v1/models` endpoint subsequently returned
`Qwen/Qwen-Image-2.1`. Voice Lab stayed active and ComfyUI was not stopped.

## Consequences and remaining gates

For a future IndexTTS2 engine, prefer the native Linux WeTextProcessing path
now that Pynini is installable from conda-forge on this ARM64 host. Do not carry
the trial-only `TextNormalizer.load()` monkeypatch into Voice Lab. Before product
integration, package and lock the mixed ARM64 Python/PyTorch/native-library
environment reproducibly, repeat an installed-runtime smoke, review Index's
nonstandard model license, and complete human A/B evaluation of wording,
speaker identity, naturalness, and urgency. Stage-1 candidate design and the
Plotloom director handoff remain separate and on hold.
