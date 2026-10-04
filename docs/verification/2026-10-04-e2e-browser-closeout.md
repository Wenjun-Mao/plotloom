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
snapshot: two GETs start00:29:27.825Z, the last finishes28.007Z; snapshot POST
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
- Enumeration:133 supported cases in42 files, including both new API cases.
- The actual read-only Sol/Medium final finds no concrete blocker: exact
  assertions, same-file regression ordering, route-drain dependency and the
  snapshot's finite network quiescence remain sound. It confirms the retained
  45-second fixture budget covers setup/teardown together; it did not execute
  tests or certify CI runtime. The actual Sol/High diagnostic final is also
  collected. Root remains the sole source writer.
- Source publication and a new unfiltered CI run remain required. The failed
  candidate is never promoted retroactively; per-test startup cost is measured
  by the next full run rather than assumed to fit its bounds.

## Release result

Pending. No full-browser acceptance or completed implementation claim yet.
No further provider jobs, media changes, owner sound acceptance, normal backend
restart or original schema upgrade are implied by this test repair.
