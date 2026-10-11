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

The one unfiltered full run on clean candidate `e923b58` finished with exit 1
(876.785 seconds). Frontend units/type checks, all 1,492 Python cases and
deterministic asset/Git parity passed. The browser run passed 277 cases and
failed six: Brief structural-help short-viewport placement, Creator inspector
pointer resizing at 1280×460, three Source dirty-refresh retention cases and
the accepted-outline locator in `source-outline-section-map.spec.ts`. The last
is a strict-mode collision between guide status and the accepted-outline panel;
do not weaken it to an arbitrary first match. The log is
`/tmp/plotloom-node-footage-full-e923b58.log`; original failed traces remain in
`frontend/test-results/`. Wheel/package gates after the browser step did not run.
These are recorded failures, not full qualification or publication. All six
precede the adjacent-caption changes below. Product/creative acceptance remains
with the owner; no service restart or owner project operation was performed.

## Adjacent graph-action explanations — approved follow-up

The owner asked for short explanations beside Save, Confirm and Apply in both
graph views. The existing state contract is correct, but button names alone
do not explain the distinction at the point of use. A shared presentation
component now pairs each existing control with its caption: save preserves a
draft, confirm records approval without applying routes, and apply activates
the confirmed story routes. A common visible notice, also in every button's
accessible description, states that none of the three generates videos.

This is a presentation-only refinement against `e923b58`: each view retains
its exact disabled predicates, variants and callbacks. The provider, request
payloads, source-review ownership, API schemas, persistence, admission, auth,
provider/prompts, dependencies, build tooling and package contracts are
unchanged. It qualifies for ADR 0156's risk-scoped frontend checks; passed
Python evidence does not need to be repeated for these captions.

Component checks cover captions, unique accessible references, unchanged
handler delegation and disabled controls. Browser checks cover both views at
1280×768, 1280×460 and 1700×900, preserving inspector body space and accepted
source state, plus the existing native confirmation/application regressions.
Executed checks for this presentation follow-up:

- Focused `verify.py` selected `tests/graph-workflow-actions.test.ts` and
  `tests/graph-confirmation-read.test.ts`: all 13 passed. An initial selector
  included nonexistent `creator-admission.test.ts`; the runner refused it
  before execution, then the corrected explicit selection passed.
- `verify.py quick`: all 1,092 frontend cases in 134 files and both TypeScript
  checks passed (13.784 seconds); locked dependencies/API import check passed.
- The new desktop caption case and both existing real confirm/apply cases
  passed (17.4 seconds). Output:
  `/tmp/plotloom-graph-action-guidance-20261010/`. All six caption screenshots
  were inspected: descriptions are adjacent and readable, without horizontal
  overflow, and the short Creator inspector retains scrollable body space.
- The checked-static delivery/control cases passed at all three desktop sizes;
  Creator layout passed at 1280×768 and 1700×900. The existing 1280×460 pointer
  resize failure reproduced unchanged at line 62 (width stays 300px), as it did
  on `e923b58` before captions. This run is six passes and one failure, not an
  all-pass qualification. Its retained trace is in
  `/tmp/plotloom-graph-action-layout-20261010/`.
- Browser manifest collection verified 85 specs and 284 exact cases across
  existing shards, with zero overlap or omissions; no suite/tooling changes.
- Two deterministic builds matched the seven-file sorted path/SHA-256 JSON
  manifest `40ec79dbfe8519feecacb34c3f7c9620d1d9d1742f96c74659e1e9b114e1b789`.
  No-cache normal8841 reads matched `workbench.js`
  `5cfa7b4ecc943dca3f32fd3308a8a5cdba370b0550e9fba650e63be89c39a905`
  and `workbench2.css`
  `7799bba0df8ff3b4c32cc8e6273a0a01350c5b982155daca15ee0e6e5a6d4d15`.

Independent GPT-6 Luna / Max read-only review found no actionable caption,
accessibility or behavior findings: exact callbacks, disabled predicates and
variants are unchanged. It also classified the six earlier browser failures
as separate from the captions and graph write-readback repair. The short
Creator resize screenshot shows pointer text selection on the sticky guide,
not a successful divider drag. The source outline failure occurs before graph
map confirmation; the dirty-refresh cases concern the Source editor, which
these graph-action changes do not modify. No assertions were weakened.

The captions are served locally, but the prior full-gate failures and repeated
short-inspector failure still block release qualification and push. No hosted
CI for either unpushed candidate is claimed. Repairing those separate guide,
geometry and Source-editor blockers is not folded into this caption request.

## Whole-graph action placement — approved follow-up

The owner noticed that the Creator inspector footer visually associated Save,
Confirm and Apply with the selected node. The actions already have whole-graph
semantics; the root cause is their presentation within the node-detail boundary.
The owner approved moving them above the canvas into a full-width region labeled
`整张剧情图 · 保存与应用`, with the scope note `作用于全部节点和连接，不仅是当前选中的节点。`.
Both views share this presentation. The Creator graph-currentness reason moves
with these controls; the inspector now contains node editing/production only.

Against trusted candidate `9f655e8`, this changes markup, accessible descriptions
and layout only. Exact per-view callbacks, disabled predicates and variants are
preserved. The provider, payloads, APIs, persistence, admission, auth, generation,
prompts, dependencies, build tooling and package contracts are unchanged. Use
ADR 0156's frontend qualification; do not repeat unaffected Python evidence.
The earlier failed full/browser gates remain recorded and block publication.

The first placement kept too many separate rows (about 170px), pushing the
opening card below the initial viewport and triggering automatic scrolling.
The checked-bundle regression retained its `scrollY === 0` assertion and caught
this. Compact the same information into a wrapping heading/scope row, action
row and notice/status row; do not change selection scrolling or weaken the
initial-position contract. A second layout check read the inspector's previous
height immediately after node selection; the screenshot showed its subsequently
settled body. It now waits for the same >70px body-space assertion to settle.
The failed intermediate run and traces remain in
`/tmp/plotloom-whole-graph-action-layout-20261010/` (five passes, two failures).

Executed checks on the final compact presentation:

- `uv run --locked --no-sync python scripts/verify.py focused --vitest
  tests/graph-workflow-actions.test.ts --vitest tests/graph-confirmation-read.test.ts`:
  all 14 passed, including unique scope/help references and unchanged dispatch.
- `uv run --locked --no-sync python scripts/verify.py quick`: all 1,093 frontend
  tests in 134 files, both TypeScript checks and locked-dependency/API import
  checks passed (12.498 seconds). No Python integration rerun was needed.
- `npm --prefix frontend run test:e2e -- --workers=1
  --output=/tmp/plotloom-whole-graph-actions-final-20261010
  --grep '^(?!.*creator desktop rows and tall inspector 1280x460).*'
  e2e/creator-workbench-operations.spec.ts e2e/creator-workbench-production.spec.ts
  e2e/production-rebuild.spec.ts e2e/creator-workbench-layout.spec.ts
  e2e/creator-workbench-delivery.spec.ts`: all 17 selected cases passed (1.5m).
  This is explicitly focused feedback, not a full release gate. The known
  1280×460 divider-pointer failure was not repaired or blindly retried; its
  retained earlier failure still blocks publication. No release test was removed.
  Selected cases include native confirm/apply in both views, node editing and
  reload, installed-production preservation/rebuild, zero-dispatch clean entry,
  normal/tall layout and production-control reachability at all three sizes.
- Inspected all six final whole-graph bar screenshots at 1280×768, 1280×460 and
  1700×900, plus the clean-entry screenshot: labels and captions are readable,
  outside the inspector, without horizontal overflow. The bar test explicitly
  positions the whole region below the sticky guide, changes node selection,
  and keeps its accepted source review unchanged. Clean entry again has no
  automatic page or horizontal scrolling.
- Browser manifest collection retained all 85 specs and 284 exact cases across
  the existing 124/160 shards, with no missing or overlapping cases.
- Two final deterministic builds matched the seven-file sorted path/SHA-256
  JSON manifest `f0bf5dfe3eb876e7f4fa43b0e8dce69a75c724f35b315ef1ae7337f568aa4a96`.
  No-cache `/v2/` normal8841 reads matched `workbench.js`
  `64aab147b8a11114ea489e96d74abebfc0cf01e5b4ce8e82bc587517c8f9ad64`
  and `workbench2.css`
  `f5ab4497cd68f32fae9550b47aa8f0279f04494e8c4aba83b87302d82d8306cf`.

Independent GPT-6 Luna / Max read-only review checked the stable diff, then
rechecked the compact layout adjustment; no actionable findings. It confirmed
unchanged action predicates/callbacks/variants and preserved scope, captions,
generation notice and currentness status. It did not run tests or inspect pixels;
the source owner performed the above checks. The presentation is served locally,
without restart or owner project mutation, but remains unpushed with the earlier
unqualified runtime candidate. No new full-gate or hosted-CI success is claimed.

## Compact scope text and distinct workflow guide — approved follow-up

The owner requested consolidating the graph bar's scope, no-generation notice
and currentness reason, and differentiating the persistent workflow guide from
ordinary page rows. The graph bar had separate header/footer presentation;
the guide used an edge-to-edge row treatment. Both are presentation-layer issues.

The graph bar now uses one supporting paragraph beside its whole-graph heading,
with the existing conditional currentness reason rather than a hardcoded
confirmation prerequisite. Per-action captions remain adjacent; each button's
accessible description still includes its scope, own caption and no-video notice
once. The workflow guide is an inset rounded card with a warm tint, compass mark
and stage pill. The compass is decorative, not an additional assistant/control.
The guide retains its sticky position, six steps and existing navigation.

Diff review against `c1b24f7` confirms presentation and test changes only:
per-view handlers, disabled predicates, variants, workflow model and navigation
guards are unchanged. No API/schema/request payload, persistence, admission,
auth, provider, prompt, dependency, build-tooling or package contract changes.
ADR 0156 permits proportional frontend checks without repeating unaffected
Python integration evidence. Earlier release blockers remain in force.

Independent GPT-6 Luna / Max read-only review found no actionable findings in
the stable source/test diff, including scope, conditional status, accessible
descriptions and unchanged behavior. The reviewer did not run tests or inspect
pixels; those checks belong to the source owner below.

Executed verification on this presentation candidate:

- `uv run --locked --no-sync python scripts/verify.py focused --vitest
  tests/graph-workflow-actions.test.ts --vitest tests/graph-confirmation-read.test.ts
  --vitest tests/recommended-workflow.test.ts`: 42 passed (0.911 seconds).
- `uv run --locked --no-sync python scripts/verify.py quick`: 1,095 frontend
  tests in 134 files, both TypeScript checks, locked dependencies and API import
  check passed (12.648 seconds).
- `npm --prefix frontend run test:e2e -- --workers=1
  --output=/tmp/plotloom-guide-card-20261010 e2e/recommended-workflow-guide.spec.ts
  e2e/creator-workbench-operations.spec.ts e2e/creator-workbench-production.spec.ts
  e2e/production-rebuild.spec.ts e2e/creator-workbench-layout.spec.ts
  e2e/creator-workbench-delivery.spec.ts`: 19 passed, one failed (2.0m).
  The two guide cases and global-action case passed, including exact next
  controls, draft guards, shared-view 4/6 state, merged accessible text,
  collapsed/expanded visibility and no horizontal overflow. Native confirm/apply,
  production preservation/rebuild, clean-entry `scrollY === 0`, and production
  reachability at all three sizes passed. The existing 1280×460 divider pointer
  failure at line 62 repeats (expected width >300px, received 300px); its failure
  screenshot again shows guide text selected by the attempted drag. This run
  is not an all-pass or release qualification, and no assertion was weakened.
- Inspected the six graph-bar screenshots (both views at 1280×768, 1280×460
  and 1700×900), six collapsed/expanded guide screenshots, short-window Source
  next-import screenshot and clean-entry screenshot. The compact guide card is
  distinct, texts/controls are readable, and graph actions remain outside node
  details. Expanded status and source/navigation behavior are unchanged.
- Browser manifest collection retains 85 specs and 284 cases across the
  existing 124/160 shards, with zero missing/overlapping cases.
- Two deterministic builds match the sorted seven-file path/SHA-256 JSON
  manifest `f5e366bb2395f694fa739e0f9ad621bbafc6271752a6ed3ddd45bab12f172e46`.
  No-cache normal8841 reads match `workbench.js`
  `41444b675a3ea55c5991cfe926402b861d67edce5bf40a14b400a5a00bb8769f`
  and `workbench2.css`
  `5cb19a6b462b8c1b9350139f4885b6bf33f8e4ccec346ec10a2e9faf4e9979c1`.

The UI refinement is served locally without a service restart or owner project
mutation. It remains unpushed with the earlier failed runtime/release candidate;
neither a new full-gate pass nor hosted-CI success is claimed. Preserve the
owner's pending graph edits before refreshing the walkthrough tab. Separate
geometry/Source-editor repairs and test-suite modularization are not part of
this presentation follow-up.
