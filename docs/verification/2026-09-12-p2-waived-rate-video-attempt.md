# P2 waived-rate five-second Wan attempt receipt

Captured 2026-09-13 from the retained checkpoint
`f6da5d88e3282fd1f7ada67aae3b2864c41f8e48`. This is an operational
transport, ingestion, and playback receipt. It is **not** audiovisual creative
acceptance and does not select a candidate.

## Explicit one-attempt waiver

The user expressly waived the otherwise required confirmation of the exact
current 720p dollar price for **one** new
`alibaba/wan-3.0/image-to-video` request. The exact dollar rate and actual
provider billing remain unknown; the shared requested-seconds ledger is not a
currency cap. This waiver did not change the model, five-second duration, 720p
resolution, native-audio request, frozen input, shared ledger, replay policy,
or secret-redaction rules.

## New admitted attempt

- New job: `vj_053f8298b8f9449ca68478c8a97e72b1`.
- Frozen snapshot SHA-256:
  `f3441a86c3c03999029222cb142e12d1223ba9b8f622d1659159520231079308`.
- Frozen keyframe SHA-256:
  `c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd`.
- Request: AtlasCloud `alibaba/wan-3.0/image-to-video`, 5 seconds, 720p,
  native audio. The current canonical Approval and selected-keyframe revision
  admitted the request without a new creative decision.
- A distinct durable idempotency identity was used. An external pre-send
  marker forbade replay after terminal loss.

The application created one new five-second reservation at
`2026-09-13T00:37:44.660662Z`, crossed its durable dispatch claim at
`2026-09-13T00:38:00.555572Z`, and made the sole permitted submit. The repaired
adapter returned a known provider prediction ID, which is retained only in the
private application state and is intentionally omitted here. There was no
retry, fallback, second upload, second generation request, or replay.

## Result and managed ingestion

Bounded reconciliation of that known ID produced one locally managed candidate:

| Field | Observed result |
| --- | --- |
| Final job state | `ingested` |
| Output SHA-256 | `b8f27b9e689020ba0186f044a2428f56ff73e97e8fb3e58d014b56fa416d65ae` |
| Measured duration | 5.038005 seconds |
| Dimensions | 1048 × 878 |
| Video codec | H.264 |
| Audio codec | AAC |

The temporary provider URL and raw provider bodies were kept in process only;
neither they nor credentials, request text, or billing data are stored in this
receipt.

## Local playback and review boundary

The isolated Plotloom runtime reopened the managed artifact in the video-pilot
panel. Browser playback reached `currentTime=0.570` seconds with
`paused=false`; metadata reported 5.038005 seconds at 1048 × 878. The captured
one-second frame is [the supporting local playback evidence](supporting/p2-waived-rate-video.png)
(SHA-256 `4b73b25ae5facf15dbcf74359ed9fb66f6703ccffc8e009270fd8d49e939e338`).
The frame shows the intended tight close-up with no hands or reel in view.

This environment verified an AAC track and actual browser playback, but could
not perform audible listening. It therefore does **not** establish the spoken
English cue, lip sync, voice identity, ambience quality, absence of music, or
full temporal/creative acceptance. No review or explicit candidate selection
was recorded.

## Shared-ledger and history preservation

The authoritative `wan-3.0-pilot-100-requested-seconds` ledger is now **10 / 100
requested seconds reserved** (90 remaining): the pre-existing unknown request
retains 5 seconds and this new known, ingested request retains its additional 5
seconds. This is conservative local accounting, not a provider billing receipt.

Historical `vj_22de3a4aac36446aa33597240963524a` remains immutable:
`outcome_unknown`, `dispatch_outcome_unknown`, no prediction ID, no output hash,
and no poll, reconciliation, replay, refund, or other mutation. Its original
events, plus the new job's `reserved` and `dispatch_claimed` events, are the
complete ledger history for this run.

## Verification and disposition

- Read-only SQLite inspection confirmed the frozen input hash, active lineage,
  new job state, output hash/observed media, shared ledger, and historical-job
  preservation.
- The in-app playback surface loaded metadata and played the locally served
  managed file; the supporting screenshot is a direct browser capture.
- `git diff --check` is the scoped source verification for this receipt-only
  change.

The owned runtime was stopped after capture. No production code, configuration,
or generated frontend asset changed. Tool usage/cost telemetry was unavailable;
the dollar rate and actual billing remain explicitly unresolved.
