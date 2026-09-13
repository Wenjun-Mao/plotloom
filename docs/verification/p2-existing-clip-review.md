# P2 existing-clip review

Captured 2026-09-13 by **Codex** from the retained local P2 pilot artifact.
This is a review receipt, not a persisted `VideoReview`, an explicit selection,
or an Approval. It makes no provider request and does not mutate the pilot
database, its ledger, the historical unknown job, or any candidate state.

## Scope and result

**Result: not yet usable for the adjoining-shot experiment.** The available
evidence supports a limited visual pass, but the required genuine audio review
and normal-speed temporal review have not occurred. Per the approved P2
checkpoint, an AAC track or transcription is not evidence of the spoken cue,
voice, sound quality, or synchronisation. Do not generate an adjoining clip or
select this candidate from this receipt.

The exact next action is a human or otherwise genuinely audio-capable reviewer
playing the retained managed clip at normal speed, including its ending, and
recording the cue/language/speaker, intelligibility, lip sync, ambience, and
absence of music. That review must also check continuous visual motion for
artefacts. If it passes, it can create the normal explicit review/selection
record; if it fails, it should name the concrete defect before any correction
slot is considered.

## Frozen lineage and integrity

| Item | Verified value | Result |
| --- | --- | --- |
| Ingested candidate | SHA-256 `b8f27b9e689020ba0186f044a2428f56ff73e97e8fb3e58d014b56fa416d65ae` | Pass — local artifact hash matches the prior ingestion receipt. |
| Frozen snapshot | SHA-256 `f3441a86c3c03999029222cb142e12d1223ba9b8f622d1659159520231079308` | Pass — retained job is the admitted five-second Wan snapshot. |
| Frozen keyframe | SHA-256 `c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd`, 1371 × 1148 RGB PNG | Pass — copied unchanged to the review pack. |
| Approved identity reference | SHA-256 `4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1`, 1370 × 1148 RGB PNG | Pass — copied unchanged to the review pack. |
| Frozen intent | Mara, a tired focused archivist with short dark wavy hair, thin round glasses and charcoal coat; tight head-and-shoulders framing; hands and reel outside frame; one restrained inhale and fractional upward gaze; no cut. | Assessed below against decoded video samples. |
| Frozen audio intent | Mara says “I can keep it safe.” once in measured English, low and controlled, over quiet archive ventilation and distant paper rustle; no music. | Unassessed — no genuine listening capability was available. |
| Historical unknown job | `vj_22de3a4aac36446aa33597240963524a` remains `outcome_unknown` with no output hash. | Pass — read-only inspection only; no replay, polling, reconciliation, or ledger change. |

The review pack contains the original input/reference images and two derived
contact sheets. Its hashes are listed in [supporting manifest](supporting/p2-existing-clip-review/SHA256SUMS).

## Measured media and resolution boundary

`ffprobe` measured a 1048 × 878 H.264 video stream, 150 frames at 30 fps and
5.000000 seconds, with a stereo 44.1 kHz AAC stream of 5.038005 seconds. The
container duration is therefore 5.038005 seconds. This confirms a 38.005 ms
audio tail beyond the final video frame; whether that is perceptible or harms
the final hold is unassessed without listening.

The frozen source keyframe aspect is `1371 / 1148 = 1.194251`; the delivered
video aspect is `1048 / 878 = 1.193622`, a -0.0527% relative difference. Thus
the delivered raster broadly preserves the source aspect, but **1048 × 878 is
not treated as an exact “720p” preset outcome**. The request recorded `720p`;
no authoritative preset-to-raster guarantee was inspected or inferred. This
receipt does not crop, stretch, transcode, or qualify a resolution contract.

## Attributed findings

Visual observations below are Codex's inspection of the decoded frame sequence:
six evenly spaced frames at 0.000, 1.000, 2.000, 3.000, 4.000 and about 4.967
seconds, plus 20 frames at 0.25-second spacing from 0.000 through 4.750
seconds. They are strong evidence about the sampled instants only. This agent
did not have model-visible, normal-speed moving-image playback, so continuous
motion, blink/face warping between samples, and full normal-speed performance
remain explicitly unassessed.

| Dimension | Decision | Time-localized evidence and boundary |
| --- | --- | --- |
| Same-person identity | Pass in sampled frames | At 0.000–5.000 seconds, the subject retains the frozen keyframe/reference's short wavy dark hair, thin round glasses, facial proportions, tired focused expression, and charcoal coat. The close crop appropriately makes the glove and reel unobservable rather than contradictory. |
| Framing and setting | Pass in sampled frames | 0.000–5.000 seconds holds the same tight head-and-shoulders close-up, with no hands or reel entering frame. The cool dawn window and archive shelving remain coherent with the frozen keyframe. |
| Intended visible action | Pass in sampled frames | The gaze rises gradually from downward at 0.000–about 1.500 seconds to more forward by about 2.000–5.000 seconds. A restrained inhale cannot be established from still frames, so only the visible gaze component passes. |
| Face/anatomy stability | Pass in sampled frames; continuous result unassessed | Across all 20 quarter-second samples, glasses, eyes, nose, mouth, hairline, jaw, shoulders, and coat are stable; no sampled extra anatomy, frame cut, or gross deformation is visible. Artefacts between 0.25-second samples and normal-speed motion are unassessed. |
| Visible defects | No blocking defect observed in sampled frames; continuous result unassessed | At 0.000, 2.500, and 5.000 seconds the close-up is clean, consistently lit, and free of an evident sampled cut, hand/reel intrusion, or identity change. This is not a normal-speed temporal-artifact pass. |
| Spoken cue, language, speaker, intelligibility | Unassessed, 0.000–5.038005 seconds | AAC presence is a technical fact, not an audio review. No listening or transcription-based substitution was used. |
| Lip sync | Unassessed, especially about 2.000–4.500 seconds | Mouth articulation is visible there, but it cannot be compared with the required line without audible playback. |
| Ambience and unwanted music | Unassessed, 0.000–5.038005 seconds | The requested ventilation/paper-rustle bed and absence of music require listening; stream metadata and waveform inspection would not settle either. |
| Cross-shot continuity | Unassessed / not applicable | There is no adjoining candidate or cut to assess. The first clip cannot open that experiment until the unresolved audio and normal-speed review pass. |

## Review materials and reproducibility

- [Approved identity reference](supporting/p2-existing-clip-review/approved-identity-reference.png) — immutable copied source image.
- [Frozen keyframe](supporting/p2-existing-clip-review/frozen-keyframe.png) — immutable copied source image.
- [Six-frame contact sheet](supporting/p2-existing-clip-review/clip-contact-sheet.png) — 0.000, 1.000, 2.000, 3.000, 4.000 and about 4.967 seconds, left-to-right then top-to-bottom.
- [Quarter-second contact sheet](supporting/p2-existing-clip-review/clip-quarter-second-contact-sheet.png) — 20 samples from 0.000 through 4.750 seconds at 0.25-second spacing, left-to-right then top-to-bottom.
- [Midpoint frame](supporting/p2-existing-clip-review/clip-midpoint.png) — decoded at 2.500 seconds.

Read-only source checks: `sha256sum` on the retained media/input/reference;
`file` on the images and video; SQLite reads of the existing video job, managed
asset, review, selection and identity-lineage records; and `ffprobe` stream
measurement. `ffmpeg` decoded the review-only stills without modifying source
media. No provider endpoint, runtime service, or source-state command ran.

## Product disposition

No concrete Plotloom implementation defect is diagnosed by this receipt. The
38.005 ms audio/video duration difference is a concrete **media fact**, not yet
an application bug; final-frame behavior and any audible tail belong in the
next genuine playback review. The current blocker is an assessment-capability
gap, so this checkpoint deliberately stops instead of treating technical track
presence as creative acceptance.
