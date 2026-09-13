# P2 repaired-adapter video attempt: rate preflight blocker

Captured 2026-09-12 from retained checkpoint `1ea3f18ca39bf23b07f1d7f1a37861c0f6d50b26`.
This is an operational receipt for the separately approved one-attempt request,
not audiovisual acceptance evidence.

## Outcome

**No new video job was admitted and no provider request was made.** The approved
runbook requires an exact current 720p price for
`alibaba/wan-3.0/image-to-video` before a paid submission, and treats rate
ambiguity as a live-work stopping condition. That precondition could not be
established without guessing:

- Atlas's current model listing describes this exact model as starting at
  `$0.04/s`, but does not state a 720p tier.
- Atlas's current `generateVideo` reference confirms that `720p`, five seconds,
  and native audio are supported for this model, but has no price table.
- Atlas's current pricing search material publishes a 720p rate for the distinct
  **Wan-3.0-Prime image-to-video** model, not the selected non-Prime model.

The prior rate receipt likewise recorded that the `$0.04/s` listing had no
resolution distinction. Inferring a 720p cost from either that generic starting
price or the Prime model would violate the P2 rate gate. The exact current 720p
rate therefore remains unavailable/ambiguous and is the precise preflight
blocker. No new admission, reservation, upload, `generateVideo` call, poll,
download, ingestion, browser playback, or creative review was attempted.

## Read-only preservation evidence

- The isolated live data root remained
  `/Users/wjmao/projects/HU/plotloom-p2-wan-pilot-FrZTHA`; no replacement ledger
  or database was created.
- The approved keyframe still hashes to
  `c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd`.
- Shared ledger `wan-3.0-pilot-100-requested-seconds` remains at **5 / 100
  requested seconds reserved** (95 remaining).
- Its immutable event history is unchanged: reservation and pre-dispatch release
  for cancelled `vj_d406106d11ac4c7e95a9b480acac50c2`, then reservation and
  dispatch claim for historical
  `vj_22de3a4aac36446aa33597240963524a`.
- Historical job `vj_22de3a4aac36446aa33597240963524a` remains
  `outcome_unknown`, with no provider prediction ID or output hash. It was not
  polled, replayed, or otherwise changed.

No process-only P2 opt-in was launched and no owned services were started, so
there are no live processes to stop. The optional supporting screenshot is
intentionally absent: a visual artifact would misrepresent a request that was
blocked before the application or provider was opened.

## Evidence sources and next action

- AtlasCloud, [Wan 3.0 image-to-video model listing](https://www.atlascloud.ai/models/alibaba/wan-3.0/image-to-video), checked 2026-09-12: generic `$0.04/s` starting price only.
- AtlasCloud, [Wan 3.0 `generateVideo` reference](https://www.atlascloud.ai/docs/more-models/alibaba/wan-3.0-image-to-video/generateVideo), checked 2026-09-12: model/request capability evidence, including 720p, duration, and audio, but no rate.
- AtlasCloud, [pricing material](https://www.atlascloud.ai/pricing/models), checked 2026-09-12: 720p pricing found for the different Wan-3.0-Prime image-to-video model, not adopted as evidence for this request.

Any renewed live attempt needs an operator-verified exact 720p rate for the
selected non-Prime model. It must use a new durable idempotency identity and a
new five-second shared-ledger reservation; it must not replay the historical
unknown job.

## Verification boundary

Read-only SQLite inspection and SHA-256 verification were run against the
retained pilot state. No code changed, so no test/build/browser gate was run.
The receipt is the sole source change; the worktree was otherwise clean at the
recorded checkpoint. Tool usage/cost telemetry was unavailable.
