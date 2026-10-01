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

Both jobs succeeded; no third job or new TTS call occurred. Spark's private evidence directory is
`/home/wjmao/services/plotloom-voice-lab/runtime-inventory/reference-strategy-pair-2026-09-30/`.
The CPU observer and runner hashes deployed there match their local copies.

| Reference strategy | Job | Backend elapsed | Minimum sampled available RAM |
|---|---|---:|---:|
| Original identity audition | `h3_26de75cecbf3456c9fcc21acee5034f5` | 741.712 s | 29.511 GiB |
| Existing line-specific performance | `h3_7acad2a427f840448de624f92f82d54a` | 738.944 s | 29.449 GiB |

Both outputs are 576×1024, 192 frames, exactly eight seconds, H.264 with
32-kHz AAC. Full video/audio decode and source/derived/output copy hashes passed.
Read-only SQLite comparison confirmed that frozen snapshots differ only in
`audioName`, `audioSha256`, `preparedAudioSha256` and per-job `imageName`.
The canonical sorted common-control hash, excluding only those four fields, is
`d03e19b041adfffb4d4f5839d55726359b4a604dcd06da0ce4da76198eb38a88`.
Model, recipe, prepared image, prompt and all generation settings match.

The trace contains **1,476 samples**, with a maximum actual gap of **1.017 s**
and no observer failure. In each observed case window, swap-out counter delta
was zero and memory PSI `some/full avg10` stayed zero. The Linux OOM-kill
counter did not increase. The matching kernel journal window
`2026-09-30 22:18:33–22:43:24 America/Toronto` contained no matching allocation
or OOM error. These observations do not measure CUDA free/peak capacity or
prove every future allocation safe. Existing swap occupied about 7.93 GiB;
it was not newly written by this pair and was not cleared.

Private Mac review package:
`/Users/wjmao/plotloom-canaries/2026-09-30-h3-reference-strategies/index.html`.
It keeps blind A/B labels until source reveal. Both video elements loaded with
the expected dimensions/duration, played and mutually paused in Playwright;
source reveal and JavaScript syntax checks passed. A 1440×900 capture is retained
inside that package. File navigation is blocked by the CLI browser, so this
check served only the package over a temporary loopback HTTP server; that
validation server and owned browser were stopped afterward. This is playback
verification, not a listening, identity or lip-sync verdict.

Private evidence hashes:

- Pair receipt: `5bffc4934edbfbe02a3047ef2330db351d906e97f76c8f1795c320b9ac01d48a`.
- Raw memory JSONL: `43a56f4d2d94fc5d7fea34aa62c55e0fb9b02d747919f6055fb795c8f1a278d7`.
- Identity-reference output: `b2515aceaf11d00bff28acc1366128eb48bf9a366cd3803c8ad12d8a8403fe34`.
- Performance-reference output: `8b4def902a741078d3918a25fe26516fb7de80fd76c6f690e147f8a587ecea8d`.
- Original failed receipt copy: `516b1354bcc65ddccef49ca17191f9adcd02b8c5c0c60767df19b017e486efdf`.
- Historical sysstat binary copy: `5f9013448105b706a728f8e9db5c00040827a2bbee9e96fe2e591d2bad0aede0`.

The raw sysstat copy is preserved privately before daily/monthly rotation can
remove the original readings. Historical receipt rows and published voices
were never rewritten. Final checks show Lab idle, H3/Qwen gateway fully ready
with zero queued/active dispatches, and Qwen Image healthy. No service was
stopped or restarted for this pair.

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

## Owner listening review

The owner reviewed the retained page and reported a large emotional difference.
The page's fixed mapping is **A = line-specific Index performance reference**
and **B = original MOSS D identity audition**, matching their retained output
hashes above. Neither label was reshuffled or inferred from playback order.

| Dimension | Owner verdict |
|---|---|
| Same-person identity | Both pass |
| Exact dialogue | Both pass |
| Firmness and decisiveness | Both pass |
| Time-critical urgency / emotional strength | A is much stronger than B |
| Lip-sync, extra speech and subtitles | Both good; no reported issue |

For this shot, the reviewed line-specific performance is the preferred strategy
when stronger urgency matters, without a reported identity, wording or lip-sync
penalty. This supports keeping the permanent identity anchor separate from
line-specific performance takes, then considering a reviewed take as H3's
reference for performance-sensitive dialogue. It does not establish general
superiority, prove isolated emotion transfer, guarantee soundtrack reuse, or
silently change the production H3 default. The two practical strategies also
differ in reference wording/duration, as described above.

The owner elected to treat the historical CUDA failure as an isolated incident
for current prioritization and **stop investigating unless it happens again**.
Its cause remains unresolved, not fixed or proven random. Preserve the original
failure, memory records and reusable observer; no new diagnosis, stress test,
monitoring automation or automatic OOM recovery is authorized. Existing serial
operating safeguards remain unchanged.

**Stop:** Technical comparison and this pair's owner listening review complete.
Further voice tuning and CUDA investigation are paused unless a concrete
reported defect/recurrence motivates new scope. No integration, director
message, merge or push is authorized. Usage/cost telemetry unavailable.
