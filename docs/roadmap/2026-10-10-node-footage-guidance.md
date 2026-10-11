# Node filming control clarification

Owner-approved on October 10, 2026. Baseline: `51cb408` on retained `main`.

## Outcome and root cause

The label `包含画面与剧本场景` made an existing production policy look like a
node-display setting. The shared `GraphNodeDetails` owns this control in both
graph views, so clarify it there rather than adding view-specific behavior.

Rename it to `此节点需要拍摄` and place an accessible description below it.
Explain screenplay scenes, storyboard and video requirements; footage time in
the complete route; decision footage before question/options; route-only nodes
without footage; and draft-only changes until confirmation/application, with
no automatic generation. Join nodes use continuation-specific playback wording.

The owner further requested explicit downstream rework and six-step ownership.
The help now names step 5/6 `制作与审阅` for possible timing redistribution and
revision/re-review of existing screenplay, storyboard and production content;
the target duration does not automatically increase. It names step 6/6 `播放`
for checking affected routes afterward. Step labels/order are shared with the
recommended workflow guide so this explanation cannot silently diverge from it.
After the adjacent readback failure was demonstrated, the owner explicitly
approved its repair with “go”. The expanded assignment includes both graph
writers' shared review handoff, as documented below and in ADR 0155.

## Scope and qualification boundary

This is presentation of the existing [ADR 0120](../adr/0120-explicit-node-footage-mode.md)
contract, not a new workflow or production rule. The existing checkbox handler,
`footageMode` values, author ownership, disable rules and request payloads remain
unchanged. Backend, API schemas/request bodies, persistence, admission rules,
authentication, providers/prompts, dependencies, build tooling and package
contracts remain unchanged against `51cb408`. The approved handoff does change
cross-component frontend runtime currentness: both graph views and the guide now
receive the authoritative write responses. It is therefore outside ADR 0156's
presentation/navigation-only exception. One stable, unfiltered local `full`
gate is required before push; unfiltered hosted CI remains separate.

All browser writes are limited to disposable fixture projects. Do not change
the owner's story, settings, jobs or draft, or restart normal8841.

## Verification and stopping condition

Focused component tests cover decision/join descriptions and both toggle
directions, exact mapping preservation, disabled controls and nonoptional node
roles. Existing browser toggle/production tests use the new accessible name.
A bounded browser case checks both views at all three supported desktop sizes
and verifies that accepted source/outline/graph state stays unchanged.

- Before the runtime handoff, focused `verify.py` selections
  `--vitest tests/graph-presentation.test.ts --vitest tests/recommended-workflow.test.ts`
  passed all 35 cases. `verify.py quick` passed 1,082 frontend tests in 133 files,
  both TypeScript checks, the lock check and API-scoped unused-import check.
- Three affected browser cases passed in 18.3 seconds: the new filming-help
  desktop case, existing node-role/toggle controls and installed-production
  draft protection. Selectors were `node filming help|creator node-role|creator
  Production shows` in `creator-workbench-operations.spec.ts` and
  `creator-workbench-production.spec.ts`.
- Both `recommended-workflow-guide.spec.ts` cases passed in 8.8 seconds,
  covering concrete next controls, the six-step guide and draft-navigation
  protection. Output is in `/tmp/plotloom-footage-step-guide-20261010/`.
- All six captured screenshots (both graph views at 1280×768, 1280×460 and
  1700×900) were directly inspected. The help remains readable without overflow,
  including the short desktop inspector. They are in
  `frontend/test-results/creator-workbench-operatio-8575a-views-on-supported-desktops/`.
- Independent GPT-6 Luna / Max read-only review found no functional or
  accessibility findings in the wording change. Its concrete-finding follow-up
  confirmed the pre-existing readback cause below and that its runtime repair
  required owner approval beyond the original presentation-only scope. The later
  step-reference refinement review also found no actionable findings. After
  explicit approval, the expanded readback review found no implementation issue;
  its one documentation finding (the stale scope/status note) is corrected here.

### Shared graph write readback — approved repair

The existing `production-rebuild.spec.ts` was updated only to use the new
checkbox name. Its run failed at line 111: Apply remains disabled after Confirm.
The preserved trace is
`/tmp/plotloom-filming-help-rebuild-20261010/production-rebuild-same-pr-d3291-s-subsequent-graph-revision/trace.zip`.

The trace records a successful section-map PUT returning accepted revision 2
with decision `choose` in `footage` mode. The workspace's last source-outline
read remains revision 1 with that decision in `route_only` mode; no fresh
source-outline read follows confirmation. `GraphWorkbenchProvider.confirmMapping`
ignored the mutation's returned source-review state and refreshed only the graph.
`CreatorWorkbench` consumes the shared workspace source-review owner, and
`creatorAdmission` correctly refuses to apply a draft that does not match that
stale accepted map. This was pre-existing against `51cb408`; the added
label/description did not cause it. The durable fix belongs in the shared
confirmation response handoff, not a relaxed admission check, reload workaround
or weaker test assertion.

Repairing confirmation exposed the same discarded response after application:
the install-graph POST succeeded and returned current graph revision 2, but the
UI still reported that it was waiting to apply. That intermediate failure is
preserved in `/tmp/plotloom-confirmation-repair-rebuild-20261010/`. Both failures
remain historical failures, not passes.

The provider now sends both successful, project/epoch-owned write receipts to
the existing shared workspace source-review owner before independent reads.
Failed writes and late responses after project changes publish nothing. Exact
map/currentness guards, CAS requests and separate save/confirm/apply operations
are retained; there is no local acceptance flag, reload workaround or weakened
test. Follow-up graph-read failures still block graph operations.

- Expanded focused command: `uv run --locked --no-sync python scripts/verify.py focused
  --vitest tests/graph-confirmation-read.test.ts --vitest tests/graph-workbench-provider.test.ts
  --vitest tests/graph-read-autosave.test.ts --vitest tests/project-directory-read-recovery.test.ts`.
  All 47 tests passed, including failed/late writes, write receipt before reads,
  graph-read failure and shared-owner held-read invalidation.
- `verify.py quick` passed all 1,087 frontend tests in 133 files, both type checks,
  locked dependencies and API unused imports (12.327 seconds).
- `npm --prefix frontend run test:e2e -- --workers=1
  --output=/tmp/plotloom-confirmation-valid-views-20261010
  --grep 'graph confirmation and application' e2e/creator-workbench-production.spec.ts`
  passed both real confirmation/application paths (9.9 seconds), without reload
  or generation dispatch. These use the existing contract-valid bridge fixture;
  the graph-edit-only fixture lacks accepted source/outline and is not used to
  bypass confirmation prerequisites.
- The unchanged production-rebuild assertions passed after both handoffs
  (15.4 seconds) in `/tmp/plotloom-confirmation-both-writers-20261010/`:
  installed production is preserved and explicitly becomes outdated after the
  footage revision; generation runs remain empty.

Two final `npm --prefix frontend run build:deterministic` builds produced the
same seven-file sorted path/SHA-256 JSON manifest, SHA-256
`bb2e57bc358f02a8ac2f1481223446183c6519986a11a993974e0653caaa8167`.
No-cache normal8841 GETs matched local `workbench.js`
`c8486efa665f7966aab5e8037a362bbbe593b67d1806f91a3bd387ef9c67088d`
and `workbench2.css`
`f4ff3dcfdd522b6dd7d2946e11673a4271a811c34397e495b036735822668ca3`.
The CSS/help layout is unchanged from the six inspected screenshots above.
The independent review's documentation finding was checked again and resolved.

Final full qualification, publication and hosted CI are pending. Product/creative
acceptance remains with the owner; no service restart or owner project operation
was performed. Preserve the executable candidate in a local commit before the
gate so the deterministic-asset Git parity check uses that exact candidate, not
the pre-change asset baseline; do not push until the full gate passes.
