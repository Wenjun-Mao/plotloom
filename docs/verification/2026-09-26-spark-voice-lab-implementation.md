# Spark Voice Lab implementation verification

**Scope:** Specialist-only Qwen3-TTS Voice Lab. No Plotloom or H3 gateway API
integration, director message, merge, or push. The retained lab data was not
deleted. Tested 2026-09-26 EDT / 2026-09-27 UTC on Spark.

## What was verified

- The private, same-origin UI and API run as the enabled Spark user service
  `plotloom-voice-lab.service` at `http://100.64.35.71:8897/`. `GET /health`
  returned `status=ok`, both model checkpoints available, and no active lab
  worker after the trial. The UI says *model files available*, not that GPU
  capacity or generation success is guaranteed.
- A real browser-created two-candidate Mandarin round
  `vr_0d8d0c8b18cf43d4b23280f617df0438` completed in about 41 seconds.
  Both candidates were playable, blind shuffle and two-item comparison worked,
  and each independently authored direction was retained with its seed and
  VoiceDesign checkpoint revision. Candidate `vc_ca9213d858a14f53b966cd08be7be1ec`
  had original SHA-256 `2d724c3984fb03e9b91685b3527ba56bc6751276e1f9c83922a3e9dfd28f9ec2`;
  candidate `vc_8e8fea0eacb74431a582bf78d3e20114` had original SHA-256
  `a1fee726c6da61b08746834c1e1899b919da033417eedb701b1524d559cf4c8b`.
  Their separate H3-ready WAVs were verified on Spark as 32-kHz, mono, 16-bit
  PCM and matched their recorded hashes. Original durations were 5.44 and
  5.68 seconds, within the gateway's technical reference bound.
- Browser selection `vs_ecc5c2268fe647db8eaca2f93cca05b3` points to the
  first immutable candidate. The new-line Base clone trial
  `vt_9662e045bb7b4edeaa78b5064c690eeb` completed in about 31 seconds,
  produced a playable 4.32-second 24-kHz WAV, and retained the source hash,
  resolved seed, Base revision and output SHA-256
  `19dc0766d535801f5a362b811d976c2969eaa79c3fffdda9dc9e78cc68cb6772`.
  Reinstalling the wheel and restarting the systemd service twice left the
  round, audio hashes, selection and clone trial readable in the browser.
- [Candidate/round capture](supporting/spark-voice-lab-candidates-1440x900.png)
  and [selection/reuse capture](supporting/spark-voice-lab-reuse-1440x900.png)
  were taken at 1440×900 from the real Spark origin after restart. No browser
  console error remained after adding the local favicon.

## Checks

- `uv run --locked --group test pytest -q` from the Voice Lab module:
  **10 passed** (one existing Starlette/httpx deprecation warning). The added
  regression proves a failed H3 derivative leaves the original WAV playable
  and the candidate selectable while marking the derivative unavailable.
- `uv run --locked pytest -q` from the repository root: **783 passed** (the
  same deprecation warning). The first run identified an outdated repository
  guard that allowed only the H3 service; its explicit admitted-service
  contract and regression fixture were updated, then the full suite passed.
- `uv run --locked pytest -q tests/test_extraction_contract.py`: **13 passed**.
- `node --check` for the Voice Lab browser script: passed. `uv build
  --project services/qwen3_tts_voice_lab`: wheel and source distribution built.
  Installed wheel SHA-256:
  `e4cb93a2d174ed9490f89d2a3b0d93e71af0d673ed042250466cc52f5ce5c56a`.
- Real browser journey: create round, wait for both candidates, blind shuffle,
  compare, select, create clone, wait for completion, service restart, refresh
  and inspect persistence. The 2/4/6/8 request counts and interruption/failure
  contracts are covered by fake-engine tests, not four real model runs.

## Boundaries and follow-up

The UI is private-network-only and unauthenticated; do not expose it publicly.
No creative judgment of the two new candidates or clone has been recorded, and
H3 video/lip-sync were not run for this slice. Earlier owner review found
identity reuse promising but urgent delivery weak; this implementation does
not resolve acting control. The service serializes its own worker only, not
other Spark generators. New candidates remain durable until a separate
retention decision. Plotloom product Voice IDs and director handoff remain on
hold by owner instruction.
