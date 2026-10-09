# Branch mutation ownership — scoped qualification

Source: retained `codex/one-current-story-rebuild` candidate after18a5216.
Contract: [ADR0148](../adr/0148-workspace-owned-branch-mutations.md).
This closes the demonstrated remount/admission defects, not the full E2E run
or native specialist cancellation. Normal8841 remains unchanged.

## Root causes and repair

Actual Source→Brief→Source unmount discarded the panel's local pending ticket
while a cancellation POST continued. A remounted panel could expose precommit
task state and ignore completion. An independent read-only reviewer confirmed
the owning-layer diagnosis against the source and the browser interception
evidence; no backend mutation failure or observed duplicate POST was inferred.

A narrow workspace owner now retains sent flights, completion generation and
unknown/error status per project. Prepare/cancel share synchronous admission.
Task reads remain panel-local and refresh after completion. Lifecycle Close,
snapshot, force-close and deletion join the POST, not the subsequently suspended
GET. Unknown outcomes refuse lifecycle completion until a current successful
read; no automatic POST replay, global task cache or compatibility fallback.

Independent review reproduced a brief obsolete enabled task render before a
passive refresh. Value/error now carries exact owner/project/basis/version/retry
identity; render and retained mutation/adoption callbacks refuse obsolete
authority synchronously. Three layout-phase regressions failed before the fix.
A retained adoption callback gap was also closed and checked independently.

The manager found a notification-order race: a pending subscriber could start
Close before the joinable promise was assigned. Its new held-flight test failed
before repair. Assigning the flight before publication closes this root cause;
the independent reviewer reran the ordering and read/adoption tests cleanly.

## Executed verification

- Both TypeScript checks PASS; full frontend970 tests in118 files PASS.
  Frontend build and deterministic entrypoint PASS; current generated static
  was refreshed. Lock check, API/scripts unused-import lint and diff checks PASS.
- Four focused real-server browser journeys PASS in11.7s: actual remount with
  one held cancellation POST, Close drainage, snapshot drainage, and existing
  stale-task/read-error recovery. Source/graph projection equality is asserted.
- Owner tests cover per-project isolation, duplicate/readonly admission,
  unknown-result refusal, all four lifecycle dispositions and re-registration
  after force-close. Hook tests cover late precommit GET, A-B-A, dirty protection,
  retained errors, explicit read recovery, prepare ownership and retained
  project/basis adoption refusal.
- Independent review: original ownership contract, read-binding/adoption
  corrections and ordering delta closed. The reviewer independently ran25
  focused tests, then14 for the final ordering/read-binding delta; browser and
  native verification were explicitly outside that review.
- Coverage-inventory test PASS. Focused unused-import lint and diff checks PASS.
  A broad scripts lint found an unused outer `sys` import in the wheel smoke
  helper; removed only that import. Its embedded probe retains its own import.
  The next combined installed-wheel smoke must qualify the helper after cleanup.

All six final pending/cancelled captures were directly inspected at1700×900,
1280×768 and1280×460. Pending copy and cancellation control are readable; short
desktop content scrolls normally. Evidence is under
`/private/tmp/plotloom-branch-remount-browser-reviewed/` (real-server fixtures,
not native generation). The first browser attempt failed at test setup because
the new fixture used a nonexistent preparation endpoint. Correcting it to the
existing `/branch-suggestions` contract produced the passing replay; no product
endpoint or gate was relaxed.

## Limits and next boundary

Force-close/deletion ownership is unit/quiescence evidence, not an additional
native/browser journey. Combined full Python/browser/wheel gates and
idle-only isolated activation remain open. Existing specialist/media receipts
and protected projects were not modified by these fixture checks. The E22.6
playbook now retains these exact remount, acknowledgment and lifecycle cases.
