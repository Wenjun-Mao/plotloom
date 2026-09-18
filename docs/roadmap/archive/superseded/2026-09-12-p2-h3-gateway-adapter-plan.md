# P2-H3: local MiniMax-H3 adapter

> **Archive status (2026-09-18):** Superseded historical plan; unresolved items remain unresolved and this file is not an active delivery plan. See [the current tracker](../../2026-09-17-playable-mvp-milestones.md) and [roadmap entrypoint](../../README.md).


Status: prepared from the evidenced private gateway baseline.  This is an
implementation plan, not a claim that H3 candidates have passed creative
review.

## Goal

Let an approved, identity-reviewed Plotloom keyframe create one recoverable
MiniMax-H3 candidate through Spark's authenticated gateway, preserving the
same immutable production and selection boundaries as P2 Wan.

## Non-goals

- No arbitrary ComfyUI workflow, model, dimension, duration, or endpoint UI.
- No changes to canonical story data, character-reference policy, or approval
  requirements.
- No automatic candidate selection, speech acceptance, voice-lock claim, or
  multi-shot production.
- No changes to historical Wan snapshots, recovery records, or its paid
  100-second pilot ledger.

## Work slices

1. **Adapter contract and immutable preparation**
   - Extract the existing Atlas compiler/parser into an explicit
     `atlas_wan.v1` adapter without changing its persisted V1 snapshot shape.
   - Add `minimax_h3_gateway.v1`, whose capability record is exactly the
     `minimax_h3_fp8_turbo4_480p` gateway profile.
   - Change new-job preparation to freeze adapter ID/version, normalised
     request values, request seed, and the mandatory aspect policy.  Reject a
     configured-but-untrusted backend before reserving or dispatching.
   - Retain V1 Wan preparation as an exact compatibility path.

2. **Trusted H3 transport**
   - Add a narrow bearer-authenticated transport for `/v1/assets`,
     `/v1/video-jobs`, known-job status, and known-job output.
   - Accept only the gateway's documented response fields and safe IDs.
     Never persist an authorization header, endpoint query, raw response, or
     arbitrary ComfyUI output path.
   - Preflight the fixed gateway profile and queue availability before the
     durable dispatch claim.  Treat uncertainty after the claim as
     `outcome_unknown`; never POST again.
   - Retrieve MP4 bytes only by a validated known H3 job ID through the
     configured gateway base URL, then retain the existing local decode,
     hash, artifact, review, and range-playback checks.

3. **Runtime configuration and workbench**
   - Add an explicit H3 runtime gate plus server-only gateway bearer key.
     Keep the gateway's Tailnet HTTP base URL public-but-server-owned and
     never browser-settable.
   - Display the active trusted capability in the P2 workbench.  For H3,
     show 864x480 / approximately 5.17 seconds / native audio and require a
     visible aspect-policy choice.  Preserve Wan's 5-second/720p wording for
     historical Wan jobs.
   - Keep the P2 Wan allowance screen limited to paid Wan records; H3 shows
     gateway capacity rather than inventing a cost total.

4. **Verification**
   - Unit-test each strict request/response parser, no-replay semantics,
     H3 aspect-policy propagation, secret exclusion, and V1 snapshot/hash
     preservation.
   - Use a FastAPI/file-SQLite browser journey with an H3-gateway fixture to
     prove preparation, submission, polling, output ingestion, restart
     recovery, stale identity rejection, explicit candidate selection, and
     ranged playback.
   - Run a single real, no-selection H3 end-to-end probe from the local
     Plotloom runtime after static tests pass.  Preserve a secret-free receipt
     with profile, hashes, status, codecs, dimensions, and duration only.

## Acceptance

The adapter is ready for the next creative checkpoint only when Plotloom can
prepare, submit once, reconcile a known H3 job, ingest its MP4, and display it
as an unselected current candidate; all V1 Wan checks still pass unchanged;
and the browser visibly distinguishes the H3 profile and aspect policy.  A
human then reviews dialogue intelligibility, audiovisual continuity, and the
character across at least the intended adjacent shots before any broader video
production claim.
