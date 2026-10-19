# Explicit storyboard confirmation without naming paperwork

The owner directly requested removing the storyboard approval box's mandatory
reviewer label. This source checkpoint is based on `3f56d297`; the implementation
commit containing this record defines the exact candidate. No live creator
decision is performed by this implementation or its tests.

## Outcome and root cause

The smallest observable journey is a persisted current board → one explicit
approve click → real API/SQLite readback labelled `创作者确认（未署名）` → explicit
revoke. A controlled browser fixture supplies the board and human action facts;
there is no provider call or invented live approval. The source owner executes
qualification; the manager owns activation, the independent imported-frame/H3
journey, actual human reviews and settlement.

The UI and API incorrectly required a reviewer string, while shared attribution
encoding and project validation assumed every unnamed approval came from an
autopilot handoff. [ADR 0016](../adr/0016-versioned-authoring-quality-gates-and-approval.md)
now names the current contract: the public action requires explicit typed
`attribution: {kind: "unnamed_creator"}` alongside the unchanged exact revision,
content hash, decision and gate-set version. Retired reviewer/note fields are
rejected; there is no name/notes form, replacement audit-name default, extra
confirmation prompt or automatic approval.

The storyboard decision owner admits the existing unnamed type for manual
actions and existing human handoff scope, while refusing machine scopes. The
shared identity-review attribution owner remains handoff-only. Manual unnamed
storyboard decisions need no fabricated autopilot receipt; linked handoff proofs
still validate their exact approvals, identity reviews and material closure.
Retained names and notes remain unchanged and truthfully readable. No schema
reset, migration, historical rewrite or compatibility write adapter was added.

`StoryboardApprovalControls` extracts the cohesive status/history/action UI from
the formerly 503-line page (now 499 lines). Submission locks synchronously,
shows progress/errors, blocks unsaved approval, and requires the exact current
server bindings. No frame selection, production or dispatch is authorized by a
mere valid board or by removing the naming form.

## Executed scoped evidence

- `focused --pytest` with `tests/test_storyboard_creator_confirmation.py`,
  `tests/test_project_storage_authoring_control_contracts.py` and
  `tests/test_autopilot_creator_confirmation.py`: **39 passed**, 37.47s
  (runner 42.177s). Covers unnamed approve/revoke/reopen, duplicate refusal,
  stale revision/hash/gates, retired fields, machine scopes, named history and
  unchanged whole-pack handoff/identity semantics.
- Downstream `focused --pytest` with `tests/test_project_storage_image_workflow.py`,
  `tests/test_project_storage_image_identity_contracts.py`,
  `tests/test_project_storage_image_delivery_contracts.py` and
  `tests/test_video_batch.py`: **15 passed**, 16.35s (runner 22.163s).
- Initial native Vitest selection `tests/storyboard-creator-confirmation.test.ts`
  plus `tests/storyboard-shot-route.test.ts`: **18 passed**. Its first run failed
  because the new fixture omitted `GateResult.entityPath`; the fixture was
  corrected without making the renderer tolerant of malformed server data.
- `quick`: **1,422 frontend cases**, frontend/browser type checks, lock and API
  import checks passed in 13.091s. Existing jsdom `window.scrollBy` diagnostics
  appeared while tests passed. This preceded the final async review correction.
- Independent read-only review found one P2: keyed page unmount did not invalidate
  a delayed approval response, allowing an old project to update the workspace's
  review. Effect cleanup now invalidates the response fence. A regression starts
  deferred A approval, mounts keyed B, resolves A, and proves B receives no old
  review. Final `focused --vitest tests/storyboard-creator-confirmation.test.ts`:
  **8 passed**, runner 0.885s. Frontend types passed again. The reviewer confirmed
  the finding resolved with no introduced defect; no tests were run by them.
- `focused --playwright` with `e2e/m1b1-workbench.spec.ts`,
  `e2e/navigation-shell.spec.ts` and `e2e/imported-still-preview.spec.ts`:
  **8 passed**, 35.3s (runner 37.626s). After the async correction, the exact
  `m1b1-workbench.spec.ts` journey passed again: **1 passed**, 10.1s
  (runner 12.186s). It asserts absence of both form fields and exercises
  approve/revoke/reapprove, persistence/readback and upstream staleness.
- Final deterministic build ran twice with matching SHA-256 trees, seven files.
  Evidence: `.local/batch-video/storyboard-confirmation-assets.json`.
  Checked `src/plotloom/static/workbench.js` SHA-256:
  `484a7e55e6886c8a38f75a2f1bbaf5c6fa43c5a239d4300f79e35dcef2c4ecca`.
  Desktop pixel inspection passed on the final browser screenshot:
  `frontend/test-results/m1b1-workbench-M1-B1-canon-79f92-pproves-a-canonical-project/unnamed-storyboard-confirmation.png`.
  It shows compact unnamed attribution and revoke with no naming/notes form.
- Targeted Ruff on the new backend owner/test and `git diff --check` passed.
  A wider modified-old-test lint inspection also reported two pre-existing nested
  context style warnings; unrelated test structure was preserved.

The independent reviewer retained requested GPT-6.1 Sol / High, effective
settings unverified. Existing tests/callers were updated to the new public write
contract; unrelated reviewer fields in other workflows retain their contracts.

## Remaining boundary

This is scoped source/UI/API qualification, not a new full release or provider
E2E. The prior full gate remains bound to `081d56d4`. The manager's real
imported-frame/H3 slice and actual combined material/final AV decisions are
separate; final cross-layer full qualification follows a stable integrated
candidate. No new full, wheel sweep, provider call, live import/approval/control,
recovery/capacity change, activation, push or CI was performed here. Both UNKNOWN
reservations and the paused owner story remain outside this source assignment.
Product/infrastructure/coordination totals and cost deltas are unavailable;
executed gate durations above are the available measurements.
