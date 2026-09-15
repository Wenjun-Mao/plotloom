# H3 unified direct-generation live canaries

**Date:** 2026-09-15  
**Revision:** `cd6403d`  
**Scope:** Spark private gateway V4 only; this is not a Plotloom candidate
selection, a quality qualification, or a public-service test.

## Purpose

Verify the deployed direct-generation contract after retiring the public asset
and split job-creation routes. The tests used the gateway's protected internal
bearer through its host environment. No credential, URL query, prompt body, or
media bytes are retained in this receipt.

## Deployment and admission

The gateway was rebuilt from `cd6403d`. `GET /health` then reported:

- `profileContractVersion: 4`;
- the six reviewed H3 profiles;
- `inputModes: ["image", "text"]`;
- a zero-depth queue and `dispatchConcurrency: 1` before submission.

Two direct jobs were accepted with server-generated seeds. The text job became
`running` first; the image job remained `queued` and began only after the text
job completed. This is the expected persisted single-worker FIFO behavior.

| Canary | Gateway job | Result | Frozen request / observed result | Gateway elapsed |
| --- | --- | --- | --- | ---: |
| T2V exploration | `h3_4337e2bf1685494ea6aa710d4aefe0a9` | succeeded | 5 requested seconds → 124 frames / 5.1667 s; 832×480; H.264/AAC | 62,291 ms |
| Start/end I2V | `h3_7bd8116706fe4879af3e96072014a3db` | succeeded | 8 requested seconds → 192 frames / 8.0000 s; 832×480; H.264/AAC | 111,173 ms |

The resolved I2V seed was `148562251572570852`; the T2V seed was
`6647439385160164985`. The status responses supplied the expected
`generationSubmittedAt`, `generationCompletedAt`, and
`generationElapsedMs` fields. Those elapsed values exclude image preparation
and the managed-output transfer by contract.

## Output checks

The gateway output endpoint downloaded only its two known managed MP4s. Local
`ffprobe` confirmed H.264 video, AAC audio, 24 fps, the recorded dimensions,
and exact 124/192 frame counts. `volumedetect` found non-silent audio in both
outputs (T2V mean `-14.8 dB`; I2V mean `-33.2 dB`).

Visual endpoint review used local temporary contact sheets only:

- T2V held a coherent cinematic lunar-station interior across sampled frames.
  This verifies availability of native audio and T2V graph execution, not
  dialogue quality, story suitability, or a production authoring feature.
- I2V began with the supplied explorer/control-room composition and reached a
  close emergency-console framing consistent with the supplied end frame. The
  intermediate camera transition is plausible for a bounded integration
  canary, but remains unselected and is not a cross-shot continuity approval.

The two MP4s remain in gateway-managed storage under the existing 72-hour
output policy. Temporary local review copies were kept outside the repository
and are not release artifacts.

## Boundaries retained

- Plotloom still submits only its approved five-second I2V path; no text-mode
  authoring control was added.
- This smoke does not establish character consistency, narration quality,
  general end-frame adherence, or a new media-production acceptance gate.
- The retired `POST /v1/assets` and `POST /v1/video-jobs` routes were covered
  by the gateway regression suite as 404s; this live check used only
  `/from-image` and `/from-text`.
