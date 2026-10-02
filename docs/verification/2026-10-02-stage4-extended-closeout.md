# Extended creator walkthrough: deployed fixes, media acceptance open

The final implementation is `fe656c06456b1024ab6ddecc40d206399906d160`,
pushed to `origin/main` and deployed to both local workbenches. This closes the
owner's current-run native-popup correction, not the full real-media journey.
The final owner extension at 15:31 UTC allowed verification/deployment/handoff
until 13:00 Toronto / 17:00 UTC, with no new media generation. Real generation
stopped at 15:04:18 UTC. Earlier frozen requests, revisions and receipts retain
their historical pins; they were not rewritten to claim this newer source.

This supplements the [earlier live checkpoint](2026-10-02-stage4-live-checkpoint.md),
[source gate](2026-10-02-stage4-source-gate.md) and
[completed reference/script/storyboard loop](2026-10-02-stage23-live-completion.md).
All creative approvals and reference/keyframe choices are provisional decisions
in the isolated copy, never the owner's creative acceptance.

## Popup root cause and durable correction

The B2/B3 review actions invoked ordinary browser-native confirmations. In the
actual Codex in-app browser, the supported JS-dialog accessor returned no
actionable dialog; even a non-awaited click left the prompt waiting for the
owner. Native app access was denied and an alternate CDP initialization stalled.
No security bypass was used. The earlier locked-host incident is separate, as
is the lack of actual audio audition; neither is repaired by changing a dialog.

[ADR 0101](../adr/0101-accessible-creator-confirmations.md) replaces all four
native confirmations with one in-page HTML modal: original rejection, single
and bulk video-candidate deletion, and ShotBeatLink removal. It preserves the
explicit decision, target and consequences; Cancel is the default focus.
Project/target/revision/currentness changes invalidate pending consent. The
confirmed callback freezes its exact payload, a synchronous guard prevents
double dispatch, and reload does not replay consent. Backend CAS, provider
authority and evidence-retention rules are unchanged.

The restore regression exposed an older UI mismatch: it offered deletion of an
unselected original with retained segment proposals. The server correctly
returned 409 under ADR 0082. Single/bulk controls now exclude and explain these
protected originals. Proposal IDs also invalidate pending consent when a new
proposal arrives without a selection-revision change. The regression deletes
only a separately created segment-free synthetic candidate, not protected media.

The [overnight preflight](2026-10-02-overnight-ui-preflight.md) now requires
actual confirm/cancel/reload and host-access checks on the intended browser,
plus a separately established way to hear and review audio. This is not a
promise that sign-in, security prompts or host locking can be handled unattended.

## Executed verification and deployment

- Full frontend: **377 tests / 49 files passed**; app and E2E TypeScript checks
  passed. Independent GPT-6.1 Sol / Medium review found no remaining actionable
  findings and independently passed 37 focused tests.
- Browser: **2 passed**. The four-action synthetic confirmation fixture checks
  exact writes, cancel/Escape/focus return, keyboard navigation, reload and no
  native dialogs. The restored-video test uses the **shipped static build**,
  reviewed H3 directions and six-second playback segments from eight-second
  fake takes. It checks authored duration before/after restore, unchanged
  selected playback bytes, preservation until explicit replacement, incomplete
  route refusal, protected originals, and cancel-then-confirm deletion.
- Three backend disposal regressions passed: exact named/shared-byte targets,
  exclusion of candidates arriving after bulk confirmation, and interrupted
  disposal recovery. No backend implementation changed in this final slice.
- Production build and whitespace checks passed. Existing large-chunk and
  Starlette/httpx deprecation warnings remain; no CI result is claimed. The
  repository CI is manual `workflow_dispatch`; this push did not launch it.
- Actual in-app-browser fixture proof verified one explicit synthetic rejection
  write and cancel/reload recovery. After deployment, the manager independently
  opened the real C1 rejection dialog, verified HTML `:modal` and default Cancel,
  cancelled, tested Escape/focus return and reloaded pending consent. No actual
  rejection, deletion, selection or generation was performed in that check.

The old restore test first failed before the changed confirmation action because
it assumed expanded preparation/keyframe panels and retired direct H3 selection.
It was migrated to the supported workflow rather than hiding the failure. An
independent review added a duration assertion to prevent an eight-second raw take
from satisfying a six-second segment test. The later 409 led to the retention UI
correction above. Final Vite and shipped-static runs both passed; counts are not
summed across overlapping reruns.

Only generated `workbench.js` and `workbench.css` changed. They were promoted at
an independently verified idle specialist checkpoint; both complete static trees
match the staged build. HTTP bytes on ports 8841 and 8851 match:

- JS: `81ace50c0e34663c5c0252ef70c2447d4ffec24a97027d11409532591d1efbcb`
- CSS: `ce7f8cb9c9ff9c66fa283f452f07f5f9001ddfe078a0c62098f6e588de3f1b39`

No service restart was needed for this frontend correction. Both health endpoints
return OK. Normal H3 remains disabled; the isolated copy retains its existing
explicit H3 configuration, without additional calls.

## Retained real-media state

The installed proposal r3, current F5 r2, twelve 2500-ms cuts and Storyboard
Approval are unchanged. Authored routes remain 20 and 22.5 seconds, not a claim
of achieved 30-second playback. Stage 4 now has eight delivered keyframe image
jobs and six prepared, unsent image drafts. The four additional still deliveries
cover corrected C3 geography, B2's unsent reply, C4's lowered gaze and a larger
C2 phone display. The C2 refinement is unselected and has no H3 trial.

| Real original | Visual disposition | Playback evidence |
| --- | --- | --- |
| Opening C1 | Retained for review | Unselected 60-frame / 2.5-second derivative |
| Opening C2 | Rejected: generated message text was not reliably exact/readable | No selected segment |
| Opening C3 | Bounded settling action visible; wider continuity unconfirmed | Unselected 60-frame / 2.5-second derivative |
| Home B2 | Rejected: glyph deformation/new marks and premature send | No selected segment |
| Home B3 | Send action visible, but rejected for text deformation/new UI shapes | No selected segment |
| Opening C4 | Downward-to-upward gaze lift and brief hold visible; moving background remains | No derivative or selected segment |

All six real originals are ingested and unselected. The two derivatives have
verified managed/served hashes and exact 60-frame video plus 2.5-second native
audio coverage. Technical audio presence is **not** evidence of listening.
Neither real ending route is playable. The failed phone-text experiments do not
prove a universal model limitation; pixel scale versus generated reconstruction
has not been isolated. Exact still text does not establish exact video text.

Complete IDs, hashes, review notes and limitations are retained under
`.local/unattended-2026-10-02/stage4-live/extended-closeout-receipt.json` and
`extension-handoff.md`. Their original 15:34 deadline records are historical;
the owner's later extension is recorded here and in the active plan. The C2/C4
image receipts have unknown model/effort metadata; intended worker settings are
not substituted for actual receipt values. Staging cleanup refusals and earlier
invalid receipt observations remain preserved, not bypassed or erased.

## Preservation and handoff

Original 雨停以后: all **73 database tables and 67 file hashes** still equal the
launch baseline. All seven current API projections equal the earlier
post-provenance-deployment capture. The historical nullable-provenance projection
change is explained in the earlier checkpoint and is not a data mutation.
After the deployed browser checks, all six copy video outputs, reviews,
selections and segment records also exactly match the pre-check receipt.

Evidence in `.local/unattended-2026-10-02/` includes:

- `evidence/manager-confirmation-predeployment-original.json`
- `evidence/manager-confirmation-after-promote-original.json`
- `evidence/manager-confirmation-after-iab-original.json`
- `stage4-live/accessible-confirmation-iab.jpg` — synthetic fixture proof
- `stage4-live/manager-deployed-confirmation-iab.png` — deployed real dialog,
  subsequently cancelled without a review write

The fixture server is stopped. Finished image and implementation chats were
reviewed, confirmed idle, archived in child-before-parent order, and their exact
Relay routes removed. The unrelated quarantined route and unknown-dispatch
evidence are preserved. The owned isolated server remains available on 8851/8852;
normal services are unchanged. The temporary continuation heartbeat is stopped
at this closeout; it is not permission to resume generation later.

Review copy: [isolated storyboard](http://127.0.0.1:8851/v2/?project=ee271b49-f384-414c-9711-452ee6333b84&stage=storyboard).
Normal workbench: [localhost:8841](http://127.0.0.1:8841/v2/).
The copy is local to this Mac; remote access was not needed or newly configured.

Next acceptance requires genuine original/final audio review, identity/location
sequence review, a newly authorized bounded experiment for phone-text/typing
fidelity, and missing route media. The six unsent image drafts are not automatic
continuation instructions. No measured provider-cost total is available. The
full walkthrough goal remains incomplete; passing implementation gates does not
change that acceptance boundary.
