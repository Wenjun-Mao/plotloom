# E2E browser release closeout

Scope: finish the release gate for the owner's
[E2E-first continuation](../roadmap/2026-10-03-e2e-first-continuation.md).
The [real-media receipt](2026-10-03-e2e-first-real-media-closeout.md) owns the
twelve actual media selections, both real routes, original protection and
pending owner listening. This record does not substitute fixtures for that proof.

## Preserved failed candidate

Unfiltered [run37164168705](https://github.com/Wenjun-Mao/plotloom/actions/runs/37164168705)
targets `93002f4da53d2c8f0db067667998309edbb6e7a7` and ended in failure.

- Non-browser job111323579176 passed in13m16s:1062 backend tests,421 frontend
  tests/56 files, types, archived-reader, static-drift, wheel and installed-wheel
  smoke. One existing backend deprecation warning remains.
- Browser shard2/job111325613114 passed65 tests in7.9m, without failed, skipped
  or flaky cases. Reports/results11288938529/11289122626 were uploaded.
- Browser shard1/job111325613123 finished with3 persistent failures,3 flaky
  and60 passed in18.3m. Reports/results11289173476/11289078612 were uploaded.
  Local copies remain under `.local/unattended-2026-10-02/ci-37164168705/`.

These results are not a green release. Exact trace/error evidence, not merely
retry success or an agent's statement, determines the repair layer.

## Root causes and bounded repairs

### Three persistent test-contract failures

1. `image-jobs.spec.ts` expected packageVersion4; both attempts returned5.
   The canonical identity backend contract already explicitly tests5. Update
   the exact browser expectation to5, preserving schema/job/request/reference,
   provenance, stale-intent and tamper assertions. No compatibility tolerance.
2. `imported-still-preview.spec.ts` queried the correct current-Approval warning
   inside a collapsed keyframe disclosure after storyboard save. Reopen that
   disclosure through its normal labeled control before asserting visibility.
   Reapproval, selection refusal and retained-media assertions stay unchanged.
3. `interactive-segment-review.spec.ts` matched both the disclosure's own summary
   and a nested `原始动作与构图` summary. Target `:scope > summary`; retain both
   viewport overflow checks, draft preservation and reader assertions.

### Shared mutable fixture state behind two flaky cases

The prior art-review held-send test intentionally left a native dispatch
reservation without terminal delivery. A later unrelated cast delivery send
correctly received409 `image_dispatch_busy`. Production release rules are not
wrong and must not be weakened to satisfy the test.

The prior package-conflict test also left a successful backend restart override
at `outputs/after-package-conflict`. A later cast project was created there:
the00:30:36.561Z candidate response names that path. Its normal default restart
then restored the worker fixture's original root; at00:30:57.013Z project reads
returned404. The nested override container has no project manifest and is not
an immediate project home. This is test-owned root drift, not a further
production identity/admission bug. The read-only Sol/High actual final confirms
that exact transition without claiming a reproduction.

The shared whole workbench is now test-scoped: backend, provider, private data
roots and frontend. The page depends explicitly on the workbench so held routes
drain before backend teardown. Within-test restart persistence remains intact.
[ADR0109](../adr/0109-bounded-browser-ci-evidence.md) records the scope/budget
contract and rejects ad-hoc resets, production lease clearing and weaker
admission. Worker count, retries and test/assertion deadlines are unchanged.

Two sequential API-only regressions intentionally leave an alternate root in
the first case and require a new project to survive default restart in the
second. Both pass on one worker; no browser is instantiated. Their first seed
attempt failed422 because `brief.synopsis` was missing; the seeds now satisfy
the exact creation schema rather than bypassing validation.

### Snapshot test ordering

The snapshot trace shows draft rehydration reads overlapping the exclusive
snapshot: two GETs start00:43:27.825Z, the last finishes28.007Z; snapshot POST
starts27.937Z and returns409 `project_busy` at28.006Z. Local selection-button
readiness does not prove those read leases have finished.

Wait for this browser's network quiescence before taking the snapshot, then
assert the response succeeds before reading its location. No sleep, retry,
deadline extension or production read/exclusive lease bypass is introduced.
The existing full snapshot/restore journey retains all persistence assertions.

## Stable repair verification

- API-only runtime-isolation regression:2 passed in5.1s, one worker, no retries.
- Frontend unit suite:421 passed/56 files; app and E2E types passed.
- Production build passed with the existing large-chunk advisory. Checked static
  bytes are unchanged because only browser-test code/configuration changed.
- Enumeration:133 supported cases in42 files, including both new API cases;
  file-level shards enumerate67/25 files and66/17 files.
- The actual read-only Sol/Medium final finds no concrete blocker: exact
  assertions, same-file regression ordering, route-drain dependency and the
  snapshot's finite network quiescence remain sound. It confirms the retained
  45-second fixture budget covers setup/teardown together; it did not execute
  tests or certify CI runtime. The actual Sol/High diagnostic final is also
  collected. Root remains the sole source writer.
- Source publication and a new unfiltered CI run remain required. The failed
  candidate is never promoted retroactively; per-test startup cost is measured
  by the next full run rather than assumed to fit its bounds.

## First repair result (failed)

Stable repair `11a113ee625c75767a5e63eb3e70c87e80ded0ec` is committed and
pushed to `origin/main`; the source checkout was clean and aligned afterward.
Fresh unfiltered [run37166752916](https://github.com/Wenjun-Mao/plotloom/actions/runs/37166752916)
started at2026-10-04T01:01:45Z on that exact SHA and ended in failure.
Non-browser job111331132004 passed in12m49s; both browser shards started
at01:14:39Z. No browser result is inferred from that non-browser success.
Its log confirms1062 backend tests (one existing warning),421 frontend tests,
both build/static and wheel/installed-wheel smoke gates. Browser shard2,
job111333141214, passed all66 cases in9.7m with no failed/flaky/skipped cases;
the job completed in11m4s and uploaded results/report11290327176/11290232249.
Shard1/job111333141200 ended with2 persistent failures,1 flaky and64 passed
in23.2m; its job finished in24m26s. Results/report11290647744/11290277173 are
retained on GitHub, and the failed shard's results are copied under
`.local/unattended-2026-10-02/ci-37166752916/shard-1/`.
At that checkpoint there was no full-browser acceptance or completed
implementation claim.
No further provider jobs, media changes, owner sound acceptance, normal backend
restart or original schema upgrade are implied by this test repair.

## Handoff preservation audit · 01:05 UTC

Both8851 and normal8841 `/healthz` report OK. The read-only specialist view
reports `busy=false`, `activeTasks=[]`; all17 video jobs remain ingested, with
12 selected/current playback segments. Exact segment IDs match the real-media
receipt, and every segment retains inFrame0/outFrame60,24fps,2.5-second video
and audio endpoints,80,000 presented samples/32kHz and832×480 dimensions.

Cast/Art/Script/Storyboard source review remain accepted without candidates or
stale reasons. The bridge remains accepted/current, installed Bible/beats/
storyboard r1, with no simulation label; the current storyboard Approval remains
bound to that exact revision. The actual browser is left at opening1/5,
`尚未选择`, ready to play, and marked as a user-facing deliverable.

`evidence/manager-11a113e-handoff-original.json` compares byte-identically with
the window preflight:73 table facts,67 file hashes and7 API projections. No
normal backend restart/schema migration is inferred from the owner's test-copy
selection authority. The isolated backend/static remain the verified93002f4
runtime; this subsequent candidate changes tests/docs only and rebuilds to
identical shipped bytes, so no additional activation is necessary.

## Second terminal reassessment · 01:46 UTC

The earlier packageVersion5, summary locator, snapshot ordering and mutable
fixture isolation steps now pass; this does not turn the failed run green.
Later assertions expose two additional current-contract transitions:

- Image intent save succeeded: POST201 returns original asset57532aec and
  exact revision2/sourceRefs at01:26:14.350Z. The following ready workbench
  read has that intent and no reviewed bindings. ADR0103 deliberately clears
  retained selection on an authoritative binding removal; the r2 editor is
  therefore absent, not evidence that persistence failed. The test now asserts
  the exact save response and removed binding, explicitly retains the original
  again through its normal unpressed candidate control, then inspects r2. Late
  frozen-refinement inapplicability/no-publication checks remain unchanged.
- Imported-still retry queried the old open disclosure before its storyboard
  PATCH settled (trace804432.712 versus804487.862). The canonical revision key
  then remounted the page with collapsed disclosures. The first attempt did
  reopen keyframes, but later queried a preparation card without reopening its
  separate disclosure. Await exact successful storyboard PATCH/revision2 and
  the normal enabled Save control before opening the new keyframe disclosure;
  reapproval/missing-three checks stay, then reopen preparation before retaining
  the candidate. The source's `finishSave` occurs after canonical acceptance
  and awaited refreshed Approval, making that control a supported boundary.

The one flaky Close case also has an exact readiness race: Close200 at
01:35:56.379Z precedes a directory GET starting56.416Z, retained unfinished
with status−1 when the test restarts its server. Its row therefore remains
active without a Reopen button. All three Close→restart sequences in that file
now require the exact closed-row label and visible normal Reopen control before
stopping the backend. Restart, cache clearing and exact durable-draft recovery
assertions remain. No proxy-error cause or production persistence defect is
claimed from that interrupted read alone.

The actual Sol/High read-only final confirms both disclosure mechanisms and
the Close ordering; no execution or edits are attributed to it. Root owns all
repairs. These are test transitions, not authorization to retain a stale binding,
rewrite media, clear a lease, force a click, extend deadlines or skip a case.
The actual independent Sol/Medium final finds no concrete blocker in the three
specs: the unpressed candidate, post-`finishSave` control and refreshed closed
row establish the required boundaries without weakening behavior. Inspection
only, no execution. E2E types/build/static-drift/diff checks pass; production
and unit-test bytes are unchanged from the latest1062/421-test CI receipt.
A fresh unfiltered run remains required.

The reviewed follow-up is pushed as
`e835d0f3a2cd8daa52257503c8d1dd1b810d32e2` on clean aligned retained `main`.
Unfiltered [run37169099225](https://github.com/Wenjun-Mao/plotloom/actions/runs/37169099225)
started at01:48:01Z on that exact SHA; at launch its result was pending. No media or
production bytes changed, so the verified isolated runtime remains untouched.
Non-browser job111338210743 passed in13m58s:1062 backend tests (one existing
warning),421 frontend tests/56 files, types, archived reader, static-drift,
wheel and installed-wheel smoke. Browser shard2/job111340246772 completed
successfully at02:11:28Z in9m23s:66 passed in8.4m, with no failed/flaky/skipped
cases. Results/report11291096383/11291156255 are retained on GitHub. Shard1
remains running at this checkpoint; its result determines full closure.

## Final preservation audit · 02:11 UTC

`evidence/manager-e835d0f-final-original.json` compares byte-identically with
the window preflight:73 table facts,67 file hashes and7 API projections.
Both8841/8851 health checks report OK. The isolated specialist view is idle
(`busy=false`, no active tasks); all17 video jobs are ingested and the exact
12 selected segments remain current with the receipt's identities,0–60 frame
ranges,24fps,2.5-second endpoints,80,000 samples/32kHz and832×480 dimensions.
The bridge remains accepted/current with Bible/beats/storyboard r1 and no
stale reasons or simulation label. The actual browser remains ready at
opening1/5, `尚未选择`, normal `播放当前` control, and is marked as a deliverable.
No additional production/media/project write was made during this audit.

## Terminal release acceptance · 02:23 UTC

Unfiltered [run37169099225](https://github.com/Wenjun-Mao/plotloom/actions/runs/37169099225)
completed successfully at2026-10-04T02:23:16Z on exact source
`e835d0f3a2cd8daa52257503c8d1dd1b810d32e2`. Browser shard1/job111340246738
passed all67 cases in20.2m, completing its job in21m10s at02:23:15Z.
The repaired image-intent, imported-still and all Close cases pass on their
first attempt. Together with shard2's66 cases, all133 supported E2E cases in
42 files pass, including the two API-only isolation regressions; no failures,
flaky retries or skips. The required non-browser gates above also pass.
The unchanged one-worker/shard and fixture/test/global/step/job limits suffice;
the longer shard's per-test stack cost is measured here, not waived.

Shard1 results/report11291395951/11291475883 and shard2 results/report
11291096383/11291156255 remain on that run. Prior failed evidence is preserved
and is not rewritten as successful. The tested source is pushed on retained
`main`; the follow-up closeout commit contains only roadmap/verification prose
and does not change production, test or checked static bytes. No new full CI
result is claimed for that documentation-only tip.

The existing `creator-walkthrough-reporting-guard` heartbeat was paused through
the app at02:24 UTC; the tool returned `PAUSED` and the persisted state matches.
Its prompt, cadence, name and target chat were preserved. The real-media receipt
and completed roadmap own the usable copy and acceptance boundaries: both real
routes are covered, owner listening for A2/A3/B1–B4 remains pending, and no
normal backend restart/schema upgrade or final-film acceptance is implied.
Historical stall/click causes expressly marked unproven above remain unproven;
this green current-contract gate does not invent a diagnosis for them.
