# P2 Wan pilot attempt receipt

Captured 2026-09-12. This is a bounded operational receipt, not audiovisual
acceptance evidence.

- Isolated pilot data root:
  `/Users/wjmao/projects/HU/plotloom-p2-wan-pilot-FrZTHA`.
- Project: `448f7d1f-852e-4cae-975f-790f332c9b5f`.
- The first prepared request was deliberately cancelled before dispatch while
  its attributed exact-image comparison receipt was corrected. It released
  its five-second reservation and was never submitted.
- The one authorized application submit was replacement job
  `vj_22de3a4aac36446aa33597240963524a`, frozen snapshot
  `f3441a86c3c03999029222cb142e12d1223ba9b8f622d1659159520231079308`.
  It requested only five seconds, 720p, native audio.
- At `2026-09-12T07:17:00.738861Z`, the application crossed its durable local
  dispatch claim and recorded `outcome_unknown` with
  `dispatch_outcome_unknown`. It has no provider prediction ID, no output
  hash, no downloaded media, and no audiovisual review.
- There was no retry, poll, retrieve, fallback, second submit, or additional
  generation request. The local server was then stopped.

The current service deliberately sanitizes the exception at the post-claim
boundary. Therefore this receipt proves an application submit attempt, **not**
that Atlas upload or `generateVideo` was reached. Runtime preflight passed
(otherwise the request would have been cancelled before claim), but the exact
failure phase and provider HTTP status are unavailable from the persisted safe
evidence. A future controlled retry requires a separately approved request;
it must first add sanitized phase/status telemetry (for example keyframe read,
upload, submit, or response-parse) without retaining credentials, signed URLs,
or provider bodies.

The shared ledger remains conservatively `5 / 100` requested seconds reserved
(`95` remaining). It is accounting for the unknown dispatch outcome, not a
billing receipt or evidence that provider generation completed.

Frozen input evidence: the selected tight-close keyframe is SHA-256
`c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd`; its
attributed selection receipt records an explicit visual comparison to Mara's
approved identity reference SHA-256
`4ad5e12a307f2b3604b17ca7b2505f490cc8d71b91891f26f82e101a05c2b6a1`.
The canonical on-screen cue is “I can keep it safe.” in measured English, with
quiet archive ventilation and distant paper rustle, no music; hands and reel
remain outside the close frame.

## Offline implementation verification and disposition

Implementation through `98e310c`, including the recovery UI in `8f70f6c`:

- Full Python: **558 passed, 9 skipped** after imported-reference admission
  changes; subsequent changes were UI, tests and documentation only.
- Frontend unit: **126 passed**; typecheck and production build passed.
- Full real FastAPI/file-SQLite browser suite: **27 passed**. The first final
  run exposed a test synchronization race (26 passed, one failed); `98e310c`
  waits for the actual successful selection response before reading its asset.
  The focused test and then the full suite passed without sleeps or a waiver.
- Generated static freshness, wheel build and isolated installed-wheel smoke
  passed. Existing Vite bundle-size warning remains, not a new build failure.
- Director review corrected transport recovery classification, credential-free
  download handling, frozen identity lineage, selection applicability and
  retrieval/cancellation UI. Old-project successful responses/actions are
  prevented from replacing a newly selected project's video state.

This accepts the **offline implementation checkpoint only**, not P2 creative
or audiovisual completion. The isolated ledger and artifacts are retained;
owned live-pilot services were stopped. No Flow lifecycle changes or unrelated
worktree cleanup were needed. Root/subagent token and cost deltas were unavailable.

The remaining dispatch-diagnostic gap is explicit: no safe evidence identifies
whether upload, generation submission or response parsing failed. Preserve the
unknown attempt, seek provider-side reconciliation where possible, and add
allowlisted phase/status evidence before separately authorizing another attempt.
Do not infer that the existing provider request is safe to replay.
