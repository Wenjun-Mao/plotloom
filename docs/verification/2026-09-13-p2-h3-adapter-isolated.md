# P2-H3 adapter: isolated verification record

Date: 2026-09-13
Scope: adapter implementation on `codex/h3-plotloom-adapter`; no merge or
push from this record.

## Outcome

Plotloom can now use one server-selected private MiniMax-H3 gateway adapter
without changing historical Atlas Wan job snapshots or its paid-pilot ledger.
The browser must make an explicit no-stretch policy decision, and the adapter
freezes its profile/version/request/seed before a one-time submission.

One contract correction was made during this work.  The first adapter draft
only required a decodable H.264/AAC download, although it advertised a fixed
864x480 / 24-fps / 124-frame profile.  That could admit a playable but
misconfigured result.  The adapter now probes the received bytes and sends a
mismatching output to `retrieve_needed` with
`h3_output_profile_mismatch`; it cannot be selected.

## Checks

| Check | Result |
| --- | --- |
| H3 transport, job, configuration, and gateway tests | 27 passed |
| Browser H3 fixture: required aspect choice → prepare → submit → reconcile → explicit select → FastAPI/file-SQLite restart | passed |
| Full browser suite | 28 passed |
| Frontend typecheck and unit suite | passed; 130 unit tests |
| Production frontend build | passed (standard bundle-size warning only) |
| Wheel build and isolated installed-wheel smoke | passed |
| `git diff --check` | passed before packaging |

The branch was then rebased onto the shared-main storage-cleanup and narrow
`services/minimax_h3_gateway` admission fixes.  Its first combined E2E run
revealed a real compatibility regression: browser fixtures still attested
`plotloom-image-specialist.v2` after the package contract advanced to v3.
The product correctly rejected those deliveries.  The fixtures now write v3;
the two affected P1/P1.5 journeys and the entire 28-journey browser suite
pass.  The rebased unfiltered Python suite passes with **632 passed, 9
skipped**.  No test is deselected or waived.

## Local probe correlation

The already-generated Mandarin dialogue probe was re-read through the new
probe implementation, producing H.264/AAC, 864x480, 24 fps, 124 frames, and
5.167 seconds.  Its creative observation remains bounded in
[the dialogue probe record](2026-09-13-h3-mandarin-dialogue-probe.md): one
reviewed line was intelligible and lip-synced under one prompt/keyframe.  No
additional live gateway submission, candidate selection, voice-lock claim, or
cross-shot acceptance was made before the dedicated adapter probe below.

## Live Plotloom-to-gateway probe

After the rebased static gates passed, one temporary FastAPI/SQLite/artifact
runtime exercised the actual private gateway through the adapter.  It used a
tracked still as an approved keyframe, `cover_center_crop`, and a server-made
seed.  It did not select, retain, or attach the result to a user project.

- Frozen snapshot hash:
  `1e8e333cd46c87c7ebf68aab0c5b61decab1f76a9bc3b9bac1c6d1220bc5b72b`.
- Temporary Plotloom job ID: `vj_373e999ec8dd4d459e42f242c90e9c67`.
- Result SHA-256:
  `b2fa6f323f358241e097ca69f19e9519950897dc034c944250bc94a48d2e47b8`.
- Observed output: H.264/AAC, 864x480, 24 fps, 124 frames, 5.167 seconds.
- Final state: `ingested`, `selected: false`; no resubmission occurred.

The private endpoint, bearer key, raw prompt, source project ID, and video
bytes were intentionally not retained in this receipt.  The isolated runtime
and its temporary database/artifact directories were removed after the check.

## Integration status and next boundary

The branch was rebased onto the corrected shared baseline, passed the
unfiltered suite, and was fast-forwarded to `main` before this live receipt
was added.  The private gateway remains a trusted server setting; no browser,
project, or artifact stores its endpoint credentials.

The next product boundary is creative review of a deliberately retained,
human-selected candidate across adjoining shots.  This adapter probe does not
claim that result, character continuity, or voice continuity.
