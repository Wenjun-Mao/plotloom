# ADR 0091: Spark Voice Lab owns specialist candidates, not product Voice IDs

**Status:** Accepted for the bounded specialist MVP, 2026-09-26.

## Context

The accepted prototype is static. Qwen3-TTS VoiceDesign produced four useful
synthetic candidates; Base-cloning candidate A across six new lines/seeds kept
recognizable identity in owner review, but both urgent lines lacked urgency.
H3's Ref2VA gateway consumes one frozen WAV per job and intentionally has no
voice library. The owner has withheld Plotloom director integration.

## Decision

- Run one private, same-origin Voice Lab UI/API on Spark, in its own service
  module. Model weights stay under `/home/wjmao/models/qwen3-tts`. Keep
  generation serial and load model weights on demand; never stop other services
  to make a Voice Lab request succeed.
- Admit this module beside the MiniMax H3 gateway as an explicit `services/`
  source-root exception. The repository guard still rejects every other
  service directory and untracked source/configuration within either module;
  local virtual environments, caches and package builds are excluded.
- A casting round freezes one audition line, each candidate's independently
  editable direction and resolved seed, and model/version. Candidate IDs and
  original audio are immutable. The 32-kHz H3-ready derivative has separate
  preparation provenance and hash. A failed derivative never replaces its
  original; an out-of-contract WAV is explicitly ineligible for H3.
- An explicit, reversible lab selection points to one immutable candidate and
  enables Base-model new-line trials. It is not a Plotloom character Voice ID,
  production approval, speaker-consistency guarantee, or acting approval.
- Candidate audio persists until an explicit later deletion policy is agreed;
  gateway output expiry does not apply. Interrupted generation is visible and
  never silently replayed after restart.

## Alternatives and consequences

Adding candidate management to the H3 gateway would conflate durable creative
assets with expiring video-job transport. Adding it to Plotloom now would
prematurely settle product ownership during the handoff hold. A Mac UI calling
Spark across origins would add a fragile split deployment. The independent
service therefore leaves a later explicit handoff/mapping step. It also means
the Lab's one-worker rule does not serialize H3 or Qwen Image workloads; busy
Spark conditions must fail visibly rather than preempt them.
