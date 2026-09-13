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

`uv run --locked pytest -q` executed 606 passing tests and 9 skips.  Its one
failure is intentionally not waived here: the shared-main extraction contract
does not yet declare the independently-added top-level `services/` gateway
root.  A separate shared-main owner is correcting that repository-policy
baseline; this isolated branch must not duplicate the correction.

## Local probe correlation

The already-generated Mandarin dialogue probe was re-read through the new
probe implementation, producing H.264/AAC, 864x480, 24 fps, 124 frames, and
5.167 seconds.  Its creative observation remains bounded in
[the dialogue probe record](2026-09-13-h3-mandarin-dialogue-probe.md): one
reviewed line was intelligible and lip-synced under one prompt/keyframe.  No
new live gateway submission, candidate selection, voice-lock claim, or
cross-shot acceptance was made during adapter verification.

## Remaining integration condition

Before this branch can be proposed for `main`, rebase it onto the corrected
shared baseline, rerun the unfiltered Python suite, and then run the normal
merge/push review.  The private gateway remains a trusted server setting; no
browser, project, or artifact stores its endpoint credentials.
