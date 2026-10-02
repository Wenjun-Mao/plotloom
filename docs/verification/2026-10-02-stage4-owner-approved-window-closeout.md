# Owner-approved production window: partial media, durable refresh fixes

This supplements the [resumed-media closeout](2026-10-02-stage4-resumed-media-closeout.md).
The owner approved C1–C4 visually and confirmed their sound, then authorized
another two hours. The recorded conservative window was 17:22:39–19:22:39 UTC
(13:22:39–15:22:39 Toronto), with new submissions stopping at 18:52:39 UTC.
The last new package, A2, was exported at **18:52:28.718209 UTC**. No new
generation was started after the submission cutoff; receiving, inspecting and
recording already-submitted work remained closeout actions.

The full twelve-cut, two-ending real-media walkthrough is **not complete**.
Four opening segments are selected; C5 and A1 await their own owner sound
verdicts. A2 has only a delivered, unbound still. B2's new take was explicitly
rejected. A3/B1/B4 remain unsent still preparations; B3's prior failed take is
preserved. Neither full route is playable, and no assembly acceptance is claimed.

## Three encountered failures, fixed at their owners

Implementations **`8427b13`** and **`ddb780c`** are committed, pushed to
`origin/main`, and deployed to the normal and isolated workbenches.

1. **Explicit retention was overwritten by an unchanged binding after refresh.**
   Keeping a replacement B2 still and saving its intent temporarily withdrew
   the media snapshot. Reconciliation treated absence and return of the old
   binding as a binding transition, silently retaining the old asset again.
   The next UI review consequently saved the old asset, changing its binding
   identity and correctly invalidating the replacement's frozen parent.
   [ADR 0103](../adr/0103-retained-candidate-read-reconciliation.md) separates
   creator retention from ready authoritative binding transitions, scoped to
   project/Shot. Unknown reads still disable owner actions. The accidentally
   invalidated job and binding history remain intact; no old job was revived
   or imported around admission. A fresh refinement was prepared against the
   actual current parent. In the deployed UI, its retention survived intent
   save, and the ensuing review bound the replacement asset as intended.
2. **Stable-name frontend assets lacked explicit cache revalidation.**
   During that verification, the server served the new JS while the browser
   still executed an older loaded bundle. [ADR 0104](../adr/0104-workbench-static-revalidation.md)
   makes the shared `/v2` static response owner send `Cache-Control: no-cache`
   on successful and conditional 304 responses. Existing validators remain;
   no security setting or caller-specific cache workaround was introduced.
   Both runtime owners were restarted for this Python change. Already running
   JS is not replaced automatically; the retained-candidate UI replay used
   the updated document and bundle.
3. **Unrelated media polling erased H3 seed and English work.**
   An image delivery refreshed the reader while A1's directions were being
   reviewed. Unknown binding/revision projections were incorrectly interpreted
   as changed source identity, clearing fields and randomizing the seed.
   [ADR 0105](../adr/0105-h3-review-media-read-recovery.md) separates availability
   from the last ready, Shot-owned identity. Loading/error preserves unverified
   seed/English buffers but withdraws consent, compiled preview and freeze,
   and cancels late callbacks. An explicit fresh source read preserves English
   only on exact source-hash equality. Genuine source/scope/settings changes
   still invalidate, and requests retain current project-wide CAS checks.
   The actual UI replay triggered an unrelated delivered-image refresh:
   all four fields and seed survived but were disabled, with no freeze;
   explicit matching-source revalidation restored editable buffers, not consent
   or compiled authorization. Shot navigation still cleared the old work.

Final checks executed on these source candidates:

- Manager full frontend **400 tests / 51 files passed**; app and E2E typechecks
  passed. Independent final source review also ran the full suite and both
  typechecks, with no actionable findings. Its 29 focused cases overlap the
  full total. Implementer negative controls failed with the old reconciliation
  and source-identity behavior; these were not independently repeated by root.
- The final production build passed; its existing large-chunk warning remains.
  Build/served-tree parity was checked. Current normal and copy HTTP JS bytes
  match the staged build and committed JS, with `Cache-Control: no-cache`.
- Final closeout reran `uv run pytest -q tests/test_static_asset_freshness.py`:
  **3 passed**. The existing Starlette/httpx deprecation warning remains.
- Real UI retention, source withdrawal/revalidation, single dispatch,
  ingestion, segment preparation and scoped rejection were exercised.
  Fixture tests do not establish media or assembly quality. CI was not
  dispatched in this window; no CI pass is claimed.

Current JS SHA-256:
`170543ba2f77206f09d5346e8649ae1ad890eb9af5488b2194976e03f1857a95`.
The final H3 frontend-only deployment required no further runtime restart.

## Real media and precise acceptance boundaries

### C1–C4: owner-approved individual clips

Root explicitly selected the four current `[0,60)` segments through the UI
and recorded the owner's visual/sound verdict with a named attribution.
Each is exactly 2.5 seconds. The replacement C2, not its rejected predecessor,
is selected. This records individual opening-clip approval, not an assembled
opening, route, geography or new-output sound verdict.

### C5: waiting take, unselected

The accepted C1 still's exact original bytes were independently imported as
C5 asset `1e9c54b5-d02e-4112-9c3d-83feac85eeaa`, with C5's own intent and
binding; C1's intent/selection was not overwritten. Root compared the still
with C01 manually. The imported asset did not expose the image-job same-person
review panel, so **no formal identity-review receipt is claimed** for C5.

Real job `vj_76a72a982acb44058115e67aa963d523` ingested once. Root and independent
review inspected all 60 proposed frames: a stable phone-held wait, with no
arrival, typing, send or departure observed. Segment
`4d75aa82-2929-4a09-9bfa-499c5da00413` is current/unselected, `[0,60)`.
Seed `733776270646588`; compiled-prompt SHA-256
`943ff6323350bdd544a6360c7b5f9f3ba908708023fc8ec2d40b64d7579e675e`.
Derivative SHA-256:
`0db1fe6a1f9b6c9ea8fcfff3fb584317d7dfd90a9e1f7488bf1573da8eb02f53`.
The clip was offered for owner sound review; no verdict has been received.
Cross-shot porch/strap/geography continuity remains an assembly question.

### A1: exterior approach, unselected

The delivered A1 still was explicitly retained, given its own intent, bound,
and visually reviewed against frozen C01 in the UI. Real job
`vj_177a64801d574581b42698d2308b19a6` used the authored **Tracking Shot**, not
a substituted static camera. Root and independent review inspected every
proposed frame plus native details: continuous rightward exterior approach
with a following camera, retained phone/person/bag and plausible evolving
window/street geometry. No stop, entry, typing, send or extra person was observed.
Feet are mostly cropped; framing tightens, and A2's starting frame needs cut review.

Segment `9c0561ab-f133-412b-8682-476a9c420f14` is current/unselected, `[0,60)`.
Seed `4215546708741480`; compiled-prompt SHA-256
`44919f82e323869501c6f6c85c98f5766dfd885c185d45e10f72810c1b457a21`.
Derivative SHA-256:
`9f7f78f30f41629a2ced9ba09b00f222f196eb2a47d657fd258dd9c17d2c038b`.
The owner answered **“尚未试听”** to this clip's sound-review question;
no audio acceptance or selection was inferred.

### B2: controlled first-frame trial, rejected

Fresh refinement asset `45d20edb-60bb-4703-940c-ca9bb4c95af4` enlarged the
unobstructed phone display and retained the exact complete unsent reply.
The earlier invalidated refinement remains history. Real job
`vj_72554372e78249fdb69228ab77c86ffe` kept the old job
`vj_b936af8b470a4f029468d4eb727c1ad4`'s **entire request controls, reviewed
English fields and compiled prompt identical**, including seed
`4387514445705463`. Prompt SHA-256:
`ec5c06fb8a54e82cb6446d16953a634b2472a8084ebcd1a2aea5b7cdce93e45c`.
The new first frame also changes framing and displays the retained incoming
message above the reply, so this does not isolate screen-size causality.

Root and independent review examined every first-60 frame, enlarged text
crops and native details. Both `今晚不去了，明天见。` and retained
`我还在老地方。` have softened/deformed glyphs, not reliable exact fidelity.
The thumb traverses the keyboard, but the composer expands and its arrow
relocates around frames 35–40. This is UI deformation, **not demonstrated
sending**. Tight hand/phone sway and near-static background do not convincingly
establish walking. Audio remains unreviewed.

The UI saved rejection `b03c639c-ddd9-4ffe-aa6f-472664950ea3` at 18:58:06 UTC.
Raw and segment are retained, unselected; the rejection banner disables selection.
Segment `0c1f8d03-565a-4822-bd4b-fdda421173fd`, `[0,60)`, SHA-256
`e36a0e9b485a8ddf851537b49e1ad5fec6427cb3b3e39d55ad1877a135fb037a`.
No post-cutoff retry or B3 follow-on was submitted. This larger-screen package
did not resolve this take's failure; C2's reading-only success does not qualify
typing/send fidelity. Reassess the input/action strategy before another trial.

All three new raw takes are H.264/AAC, 832×480, 24 fps, 124 measured frames /
5.167 seconds from requested five seconds, quality 8, native audio, center crop,
no end image. Their derivatives have exactly 60 frames / 2.5 seconds and 80,000
audio samples at 32 kHz. Hash/probe evidence is not listening evidence.

### A2: delivered still only, unbound

Job `ij_bfb865af05054969b94180ff08fa4c17` delivered asset
`9d41f250-581c-4640-b8b1-81c6ae88870e` under the exact ImageGen basename.
Root verified request/manifest/executor pin, skill/reference/output hashes;
technical receipt was accepted. Code pin `ddb780c`; only C01 was attached.
A1 geography was explicitly **text guidance, not image conditioning**.
Output SHA-256:
`eee39481ac88c8ad8e45505fe9dac6e651daeeda3ba3817aae2c7eee2946e441`.

Root and independent review find an individually compatible medium exterior
near-window frame, with C01-compatible visual anchors and retained phone/bag.
Dark mullions, wood base, bench, pale planter and wet pavement broadly carry
over. Pendant shades and window/interior/planter details differ; a changed
angle could explain some differences, but identical geometry is not established.
A1's ending profile versus A2's three-quarter pose/left-hand position also
needs cut review. Cropped legs do not prove active walking. It remains unbound,
with no formal same-person review or A2 H3 preparation/dispatch.

## Preservation and handoff

Fresh `manager-third-window-final-original.json` exactly equals
`manager-closeout-original.json`: **73 tables, 67 file hashes and seven API
projections unchanged**. Both `/healthz` endpoints are healthy and both
specialist registries have `busy: false`, `activeTasks: []`. All **10 real
originals are ingested**, with seven derivatives and four selected segments;
there is no pending/uncertain provider dispatch. Both full routes remain blocked
by missing current selected media, correctly shown in the actual UI.

Root was the sole browser/provider owner; source implementation and independent
reviews used explicit GPT-6.1 Sol / Medium. The retained image worker used
GPT-6 Luna / Max. Its A2 final was collected and independently reviewed, then
the idle chat was archived and its Relay route removed. The exact ImageGen
staging source was preserved after the required cleanup attempt refused its
non-private staging root; no forced chmod/deletion occurred. Other retained
cleanup refusals remain preserved. No measured provider-cost total is available.

The existing `creator-walkthrough-reporting-guard` heartbeat is confirmed
**PAUSED** by both tool and saved record. No service was stopped at closeout;
the normal workbench and labelled isolated review copy remain available.

Workflow-local evidence under `.local/unattended-2026-10-02/` includes:

- `stage4-live/c5-third-window-*` and `a1-third-window-*`: actual submitted UI,
  served review MP4s, all-frame/native sheets and A1 frozen snapshot.
- `stage4-live/b2-third-window-*`: served raw/segment, all-frame and independent
  text/detail sheets, submission and rejection-banner proof.
- `stage4-live/a2-third-window-exported.jpg`; the immutable A2 package and
  complete delivery under `final-installation/.../runs/20261002T184954065886Z__ij_bfb865af05054969b94180ff08fa4c17/`.
- `stage4-live/retained-candidate-verified-ui.jpg` and
  `h3-read-recovery-{withdrawn,revalidated}-ui.jpg`; `h3-recovery-static/`.
- `evidence/manager-third-window-final-original.json` and the retained baseline.

[Open A1 sound review](http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84&stage=storyboard&entity=shot%3Aending-a-s1-c1#video-segment-preview-vj_177a64801d574581b42698d2308b19a6).
[Open C5 sound review](http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84&stage=storyboard&entity=shot%3Aopening-s1-c5#video-segment-preview-vj_76a72a982acb44058115e67aa963d523).
Next owner action: listen to these two individual clips and provide their
verdicts. A further explicitly bounded production window is required for
remaining route media and reassessed phone action, followed by whole-route
audiovisual/continuity review. Do not select merely to unlock playback.
