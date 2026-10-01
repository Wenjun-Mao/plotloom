# H3 reference strategies and Spark memory evidence

**Scope:** Owner-authorized two-clip comparison, followed by a pause on voice
tuning unless a concrete defect is reported. No new TTS calls, seed search,
model change, service stop, cache flush, API change, director contact, merge or
push. Existing Voice IDs and original failed evidence remain untouched.

## Recovered evidence: the old allocation failure

Index trial `vt_d2688889bdb845149eae046172a7785a` ran at
`2026-09-30T04:47:41Z–04:47:59Z`. Its original qualification receipt retains
a **62.373 GiB minimum sampled MemAvailable** during the loading window.
This is a per-trial sampled extreme, not a synchronized reading of CUDA free
memory at the failed allocation. The sampler retained extrema, not a time series.

Spark's retained `/var/log/sysstat/sa30` corroborates substantial Linux memory
headroom on either side of that window:

| UTC sample | MemAvailable (KiB) | Available (GiB) | Swap used (KiB) |
|---|---:|---:|---:|
| 2026-09-30 04:40:00 | 73,057,868 | 69.673 | 7,594,304 |
| 2026-09-30 04:50:14 | 73,054,944 | 69.671 | 7,594,248 |
| 2026-09-30 05:00:15 | 34,300,380 | 32.711 | 7,640,836 |
| 2026-09-30 05:10:00 | 34,642,144 | 33.037 | 8,177,400 |

These coarse samples are about ten minutes apart, not instantaneous peaks.
Accumulated swap use is not evidence of active thrashing: the swap-out rate in
the interval ending 04:50:14 was 0.00 pages/s. The later reduction to about
33 GiB must not be presented as the original failure's host-memory reading.
`sadf` filters here use UTC; the interactive `sar` display uses Spark's local
America/Toronto timezone. The failure was 00:47:58 local, **04:47:58 UTC**.

The exact kernel window still shows `NV_ERR_NO_MEMORY` in
`_memdescAllocInternal`, `kgrctxAllocMainCtxBuffer` and CUDA graphics-context
buffer allocation. Thus the failing layer is established, but an exact
allocator/cache/driver cause is not. Available Linux RAM does not guarantee
the next CUDA context allocation; the evidence argues against the simpler
claim that the whole host had merely exhausted its RAM.

The [earlier diagnosis](2026-09-30-voice-lab-cuda-neutral-retest.md) also measured
roughly 33 GiB host availability and much lower CUDA-reported free capacity
**later during diagnosis**, not contemporaneously with the failed trial.
Do not silently align those observations. No synchronized original CUDA trace
or failed-process Torch peak exists; these cannot be reconstructed now.

Read-only extraction commands, on Spark:

```sh
sadf -d -s 04:30:00 -e 05:10:00 /var/log/sysstat/sa30 -- -r ALL
sadf -d -s 04:30:00 -e 05:10:00 /var/log/sysstat/sa30 -- -S
sadf -d -s 04:30:00 -e 05:10:00 /var/log/sysstat/sa30 -- -W
journalctl -k --since '2026-09-30 00:45:00' \
  --until '2026-09-30 00:50:00' -o short-iso --no-pager
```

## Forward measurement, not another OOM reproduction

[memory_trace.py](../../services/qwen3_tts_voice_lab/tools/memory_trace.py)
is a standalone **CPU-only operator observer**, not a production endpoint or
a capacity guarantee. It writes private, exclusive JSONL with UTC and monotonic
timestamps, phase/job binding, MemAvailable/free/cache/reclaimable/anonymous
memory, swap, pressure stalls, swap/page-fault/OOM counters, and labelled
ComfyUI/Qwen-Image/voice-engine/embedding-process RSS. It never records process
arguments, environment variables, audio or prompt contents.

Sampling runs independently of HTTP polling at one-second intervals. The
receipt includes actual sample count and maximum observed gap: subsecond
transients may still be missed. Process exit between reads is ordinary, not a
fabricated zero measurement. Process RSS peaks are per-process observations,
not the sum of a service's memory. Host use, RSS and Torch/CUDA allocation are
overlapping views of Spark UMA and must never be added together.

Spark's `nvidia-smi` reports memory total/used/free as `N/A`. The observer
therefore records CUDA memory as **not measured** rather than starting an extra
CUDA context or guessing from host counters. Future diagnosis of another real
allocation failure should correlate its exact process/kernel timestamps with
this trace and existing engine Torch metrics; it may still require a separately
scoped driver investigation. Successful runs alone do not close that cause.

For a future authorized voice window, start this observer first, then run the
ordinary job separately. This command does not create a generation:

```sh
/home/wjmao/services/plotloom-voice-lab/.venv/bin/python \
  /home/wjmao/services/plotloom-voice-lab/runtime-inventory/closeout-tools/memory_trace.py \
  --output /home/wjmao/services/plotloom-voice-lab/runtime-inventory/NEW-memory.jsonl \
  --duration-seconds 300
```

## Matched comparison

[compare_h3_references.py](../../services/qwen3_tts_voice_lab/tools/compare_h3_references.py)
admits at most two serial, unreplayed Ref2VA requests under an exclusive receipt.
It uses the same image, prompt, seed `20260923`, resolution `576x1024`, Base-20
Ref2VA runtime and requested **eight seconds** in both cases. The longer clip
allows the existing 5.283-second performance take to finish without making
clipping the experiment's confound.

- Identity reference: unchanged original raw MOSS D audition, SHA-256
  `da061210b3e8360c20be8546089d42382f36a8ada64d953b0c151c64fd6088ae`.
- Performance reference: existing Index Chinese-description take at seed
  `20260930`, SHA-256
  `80ba844e1294cbf0d9587327d98a730891cd0558fc5ffaee153a70e6f8cb8bfb`.
  Its delivery passed the [owner's urgency review](2026-09-29-index-chinese-emotion-description-trial.md).
  It is not a newly synthesized or newly published identity.
- Target dialogue in both prompts: `等等，别打开那扇门！控制台还在报警，先把电源切断！`.
- Both references undergo the same CPU-only mono PCM16 / 32-kHz conversion;
  source hashes and derived hashes stay separate. No trimming, loudness
  normalization, or per-case prompt adaptation.

This compares **two practical reference strategies**, not emotion causality:
reference words, duration and performance necessarily differ. Same numeric seed
does not guarantee identical model random draws after conditioning changes.
H3 still generates a new soundtrack; neither strategy promises exact reuse of
the input speech waveform or audio-driven lip-sync.

Stop after this pair. Listening should separately judge identity, exact words,
decisive urgency, lip-sync, extra speech and subtitles. One pair cannot establish
general superiority or automatically change the default H3 input.

## Execution and acceptance

The first job was accepted as `h3_26de75cecbf3456c9fcc21acee5034f5`; the
comparison remains in progress. Spark's private evidence directory is
`/home/wjmao/services/plotloom-voice-lab/runtime-inventory/reference-strategy-pair-2026-09-30/`.
The CPU observer and runner hashes deployed there match their local copies.

Focused verification: 64 locked Voice Lab tests, 13 root extraction checks,
scoped Ruff, relative documentation links and patch checks passed. The existing
Starlette/httpx deprecation warning remains. No package runtime/frontend source
changed, so prior wheel/UI gates were not rerun or presented as new evidence.

Independent Luna review (Terra unavailable in the built-in selector) requested
strict redirect rejection and preservation of both job and observer failure.
Both were addressed; regression tests prove all five redirect statuses produce
one request, uncertain first dispatch never reaches the second, and final
sample failure cannot hide a job error. Re-review found no remaining material
findings in those areas.

Final technical evidence and listening acceptance remain pending. No old
failure is relabelled as fixed by this work.
