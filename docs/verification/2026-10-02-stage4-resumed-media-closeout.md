# Resumed media window: controlled C2 improvement, acceptance still open

This supplements the [extended closeout](2026-10-02-stage4-extended-closeout.md).
The owner explicitly authorized another bounded generation window and agreed
to listen to the audio. The window was 16:08:45–17:08:45 UTC (12:08:45–13:08:45
Toronto), with new submissions stopping at 16:38:45 UTC. No listening verdict
has yet been received. Root owned all source, browser and provider mutations;
GPT-6.1 Sol / Medium reviewers performed independent read-only source and media
reviews. All project decisions below are provisional, isolated-copy decisions.

## Implemented and deployed: explicit H3 review seed

Implementation `a7e92b0` is pushed to `origin/main` and deployed to both
workbenches. The controlled trial exposed a creator-workflow gap: the backend
froze an explicit seed, but the UI only supplied a random one. Changing both
seed and first image would weaken the comparison; preparing through an API
would not complete the UI workflow. [ADR 0102](../adr/0102-explicit-h3-review-seed.md)
therefore makes the seed an explicit input to the shared source-review contract.

The decimal field accepts exactly representable nonnegative integers, including
zero, and rejects blank, signed, fractional, exponent or unsafe values.
Changing it invalidates source/directions/consent/compiled preview and rotates
request identity. Read, preview and freeze use the same value; dispatch remains
separate. The backend's wider integer contract was not changed.

Executed checks on this source:

- Full frontend: **387 tests / 49 files passed**; app and E2E typechecks passed.
- Seed-specific **12 tests** and **45 focused seed/video/timing tests** passed;
  these overlap the full suite and are not additional totals.
- The shipped-static restored-video browser regression passed (**1 test**).
  Its three fake candidates freeze the exact historical seed and assert both
  the preparation request and persisted snapshot, alongside existing duration,
  replacement, restore, protected-original and confirmation checks.
- Independent source review closed a test-helper CSS-selector collision by
  giving the seed its own field class; final review had no actionable findings.
- A fresh independent production rebuild byte-matches both complete served
  static trees. The existing large-chunk warning remains. No backend changed,
  no service restart was needed, and no CI result is claimed (manual dispatch).
- The actual in-app browser displayed the new field, froze the historical seed,
  submitted once and retrieved the new real original. An older tab retained
  its prior bundle after reload; a fresh same-browser tab loaded current bytes.
  No browser security setting or user draft was changed to force that reload.

HTTP-verified deployed JS SHA-256:
`72b94a1054355d61dabd403ef4abc9e85b142e1ad30446ed5a3bc40055a6da14`.
`workbench2.css` SHA-256:
`c0f56674ccdd4ff379fa43e409598556db2943de83ac0bf0ac7ad3c198d8848b`.
Only those two generated files changed in this slice.

## Real C2 comparison and bounded visual result

Old rejected original: `vj_20d20f212c9f4ba5a33b4d81befd98eb`.
New original: `vj_9d1efcc0a49349c4b2500b1b5cb05d91`, dispatched once at
16:27:15 UTC and subsequently ingested through the UI. Provider receipt:
`h3_e0b29dfc84cc488f8db52e7688721319`.

Both snapshots have identical request controls, provider binding and complete
compiled prompt, independently compared from retained records: quality 8,
832×480, requested 5 seconds / 124 frames at 24 fps, native audio, center crop,
seed `2325339575976657`, and no end image. Compiled-prompt SHA-256:
`eeead9e05a78f3f1daca0c389b27d7e5839dafb5841d9c724da7ae733098ba87`.
The first-frame package changed to reviewed asset
`0ed63e43-cf91-47e9-b8b7-67f41aaa7917`, original SHA-256
`61f5522411e809b6298f5d5fb7d8dc20c9abe193334d5fc699fefbd7af81633c`.
Its shot-specific intent, binding and same-person review were explicitly saved
in the UI. Side-profile compatibility is narrower than complete identity or
sequence acceptance. Retained old image/video evidence was not overwritten.

The new raw H.264/AAC original has 124 frames and measured duration 5.167 seconds.
Root and the independent media reviewer examined all first 60 frames as phone
text crops, a full-shot sample grid, and full-resolution frames 0/24/60/123.
Within `[0,60)`, the complete **“我还在老地方。”** is legible throughout,
including punctuation, without observed replacement/missing characters, added
words, new UI, typing or sending. Strokes remain somewhat softened by rendering
and perspective. This is a material local improvement over the old rejected
take, not a universal exact-text guarantee. Framing, background and text
presentation also changed: the experiment does **not** isolate pixel-size
causality or establish B2/B3 typing/send fidelity. Audio and sequence continuity
remain unaccepted.

New raw SHA-256:
`9d50e31f3724f7bf9c53b94b60984921e7ea04cc07a03047fcbe8313f0d47f40`.
The UI created, but did not select, C2 segment
`9f324db4-aa18-4e1a-adc0-bc5e08165e06`, `[0,60)`, exactly 2.5 seconds;
SHA-256 `52f9700ee22ba975ddf6de4246dff48cffee2986f97e9fa770f575c9f26be992`.

## Other media and unresolved acceptance

The UI also created unselected C4 segment
`8a7d7670-05f9-4bb5-8a11-f6f5918573ea`, `[0,60)`, exactly 2.5 seconds;
SHA-256 `ea184df49764ea3b76beb26fe71d348da49575cc6b09189b3ca74ba08175c1fe`.
Root inspected every frame in its contact sheet: downward gaze develops into
an upward glance and short hold. Background motion and broader continuity
remain separate review questions. Managed probes show 60 video frames and
80,000 audio samples at 32 kHz for both new derivatives. Served hashes equal
their managed hashes; decoder/stream evidence is not listening evidence.

C1/C3 and the new C2/C4 derivatives were offered to the owner for sound review.
No sound acceptance was inferred from generation authorization. All **seven
real originals and four derivatives remain unselected**; all video jobs are
terminal/ingested, with no uncertain or pending provider dispatch. The old
C2/B2/B3 rejections remain preserved. Neither ending route is playable.

C5 reuse was assessed without mutation or dispatch. The retained C1 still fits
the isolated medium stationary-phone action, but its pictured geography and
strap do not resolve C3/C4 sequence continuity. Also, intents are versioned per
asset/role: overwriting C1's intent for C5 would stale its binding. If faithful
reuse is later chosen, an explicit independent exact-byte import with its own
C5 intent and identity review is the supported isolation path, not an excuse
to accept that geography. C5/A1/A2/A3/B1/B4 remain unsent prepared still drafts;
B2/B3 need a separately reassessed text/action experiment. Nothing auto-sends.

## Preservation, evidence and handoff

The fresh original-project capture `manager-resumed-closeout-original.json`
exactly equals `manager-closeout-original.json`: all **73 tables, 67 file
hashes and seven API projections** are unchanged. Both workbenches return
healthy status and have no active specialist reservations. The existing
`creator-walkthrough-reporting-guard` heartbeat is confirmed **PAUSED** by the
tool and saved record. Finished read-only review results have been collected;
no native worker was reopened. The manager-owned isolated server remains
available; no service, security or original-project setting was altered.

Evidence is local under `.local/unattended-2026-10-02/`:

- `stage4-live/resumed-video-jobs.json`: complete retained video snapshots.
- `stage4-live/c2-fixed-seed-{raw,segment-0-60}.mp4`, detail/sample/text PNGs,
  and `c2-fixed-seed-{submitted,review}.jpg`: raw, derivative and review proof.
- `stage4-live/c4-h3-segment-0-60.mp4` and `c4-h3-segment-all60.png`.
- `evidence/manager-{media-resume,seed-deployed,resumed-closeout}-original.json`.
- `seed-control-static/` and `seed-control-independent-static/`: matching builds.

[Open the current C2 review](http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84&stage=storyboard&entity=shot%3Aopening-s1-c2).
The normal workbench remains [localhost:8841](http://127.0.0.1:8841/v2/).
Next: obtain actual original/final sound verdicts; reconcile scene/identity/prop
continuity; authorize a further bounded production window for missing/rejected
route media. Do not select solely to make playback run. No measured provider
cost total is available. The full real-media walkthrough remains incomplete.
