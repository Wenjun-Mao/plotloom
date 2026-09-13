# P2 reviewed two-shot checkpoint receipt

Captured 2026-09-13 from the retained authoritative P2 SQLite database and
artifact root. This receipt records the approved bounded continuation after the
first clip's user review. It is not a universal voice/identity qualification,
P3 readiness, or a claim that the second clip received creative approval.

## Bounded execution and preserved history

The retained first candidate `vj_053f8298b8f9449ca68478c8a97e72b1` kept its
existing frozen snapshot `f3441a86c3c03999029222cb142e12d1223ba9b8f622d1659159520231079308`,
output SHA-256 `b8f27b9e689020ba0186f044a2428f56ff73e97e8fb3e58d014b56fa416d65ae`,
and known provider prediction identity. Before normal review/selection, the
runtime rechecked that retained job, current approval/keyframe/reference lineage,
and the shared ledger. The historical job
`vj_22de3a4aac36446aa33597240963524a` remains `outcome_unknown` with no
provider prediction ID or output; it was not replayed, polled, reconciled,
modified, or refunded.

The user reviewed the first clip on AtlasCloud and confirmed the exact cue
“I can keep it safe.”, believable lip-sync and motion, and no distracting audio
or visual defects. The normal immutable `VideoReview` is attributable to
`User (AtlasCloud review)` and explicitly says it does **not** claim local-file
viewing, timecodes, or stronger audio findings. That review selects only the
first candidate; no prior selection was transferred to the second clip.

The shared `wan-3.0-pilot-100-requested-seconds` ledger moved from **10/100**
to **15/100** requested seconds: exactly one additional 5-second reservation
and one dispatch claim. The adjoining attempt used the approved waiver only for
one AtlasCloud `alibaba/wan-3.0/image-to-video` request with five seconds,
720p, and native audio. There was one upload and one submit, no POST retry,
fallback, replay, or second generation request. Exact dollar price and actual
billing remain unverified.

## Frozen adjoining input

No retained image was suitable for the required adjoining composition: the
approved identity reference was front/three-quarter, while `shot_profile`
requires a full left side-profile at the desk. The normal P1.5 handoff created
one original ImageGen package, pinned at source revision
`3562969acee036da6af010db598ef8ef6c7c7c84`, from the frozen
`character_identity:char_mara` reference only. Its accepted delivery produced
the managed source image SHA-256
`0d007e461b0524cb8682ebfb3dd52f7e8073964c1b1a53dca60c9ad24d8e8c84`.

The package's attributable Codex visual assessment recorded a pass for the
approved Mara identity, full profile composition, dark-gloved hand, one fragile
spool, and oak desk. It is clearly labelled as a Codex assessment, not a human
approval or video review. The current reviewed-keyframe binding and its required
identity-aware review were both created through the normal API before video
admission. The frozen video snapshot is
`42610155e160b6de70419476c8bf0ac7f25c6dd4ee5fae9cf32e3add96a038e0`.

## New output and separate review dimensions

| Dimension | First clip | Adjoining clip |
| --- | --- | --- |
| Durable state | ingested and explicitly selected | ingested, deliberately unselected |
| Output SHA-256 | `b8f27b9e…416d65ae` | `b778ffc096417821573211ff20ad2bfb01647e9778c3088c7017cb4c23a7494b` |
| Technical media | H.264/AAC; 5.038005 s; 1048 × 878 | H.264/AAC; 5.038005 s; 1048 × 878 |
| Creative/audiovisual review | user AtlasCloud review passed within the exact stated evidence | **Pending**: no genuine audio or continuous temporal review was available in this execution environment |
| Cross-shot continuity | not independently qualified | **Pending** until both cuts receive genuine normal-speed, muted, and audio-only review |
| Resolution contract | requested 720p; actual raster reported separately, no preset-to-raster claim | same boundary; no cropping, stretching, or preset conformity claim |

The second native file and its contact sheet are retained locally at
`/Users/wjmao/projects/HU/plotloom-p2-wan-pilot-FrZTHA/review-packs/p2-adjoining-profile-2026-09-13/`.
The pack's named MP4 hash is the adjoining output hash above; its contact-sheet
SHA-256 is `1c891a7fffbf9fd4dcf660aeb003c1c0bbae7270d4c864c04b7cec6cee50d2da`.
The safe supporting still is [the adjoining contact sheet](supporting/p2-adjoining-profile-contact-sheet.png).
It is a frame-sampling aid, not a substitute for temporal or audio review.

## Product and verification disposition

The diagnosed product defect was narrow: the pilot exposed an individual video
job but could not play accepted adjoining jobs together. The frontend now derives
only current, explicitly selected, locally ingested candidates for the current
scene; it orders them by frozen storyboard order, supports explicit playback,
restart, and shot navigation, and keeps the final frame on completion. Pending,
stale, rejected, or unselected candidates cannot enter that sequence.

Focused validation before final candidate review:

- `npm --prefix frontend run test -- --run tests/video-pilot.test.ts` — 3 passed.
- `npm --prefix frontend run typecheck` — passed.

One independent Terra review found that the selector regression test had omitted
the central current/ingested/same-scene but **unselected** case. The candidate
implementation already filtered it; the test now supplies that case and asserts
its exclusion. No other blocking finding was raised.

The new second clip remains intentionally unselected, so the ordered two-clip
player cannot represent it as an accepted result. The outstanding gate is only
the genuine audiovisual/temporal assessment of that retained local MP4, followed
by normal review/selection if it passes; no additional generation is authorized
or needed for that review.
