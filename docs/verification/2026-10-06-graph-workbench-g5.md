# G5 integrated creator workbench qualification

Status: locally qualified, published and activated on healthy normal8841 after
the exact owner-authorized native reconciliation and demo retirement below.
Remote browser CI and owner acceptance remain separate.
G0–G4 evidence remains historical at its
recorded fingerprints; it is not rewritten as evidence for the final candidate.

## Scope and current changes

The owner-approved G0–G5 outcome is one source-bound graph draft shared by creator
and professional modes, explicit node footage membership, exact structural
commands, node-context Story/Production and the existing production/media owners.
Desktop authoring starts at 1280px. Installed production remains first-install-only.
The permanent [C/P contract](../creative-workflow/graph-workbench-acceptance.md) and
[creator guide](../creator/graph-workbench.zh-CN.md) distinguish draft saving,
confirmation, installation, generation, approval and explicit media selection.

G5 exposed presentation and lifecycle gaps, corrected at their owners:

- The reader required an episode for route-only controls and discarded valid
  routes. It now requires exact explicit footage bindings, retains all route
  nodes and omits only route-only episodes. Invalid membership displays a
  binding mismatch instead of an indefinite loading indicator. ADR 0120 records
  the correction and preserves prior evidence boundaries.
- A delayed Undo/command receipt restored its old selection after a newer click.
  The shared receipt owner snapshots the presentation-selection generation and
  preserves a later selection only while that node still exists; otherwise it
  selects the receipt's safe node. Content/CAS/Undo authority is unchanged.
  ADR 0121 records the guard. Deferred receipt tests cover retained and removed
  nodes; the native operations journey holds an actual Undo receipt.
- Separate Tab/Escape tests exposed cancellation masked by the combined exercise.
  The gesture owner now cancels either key, divider blur and delivered window
  blur. Window blur starting with textarea focus reproduced a retained 469px
  tentative width before the fix. The corrected exercise preserves automatic
  or explicit preference, late-release idempotence, focus/caret/content/scroll
  and zero authored writes. Actual OS blur delivery remains unverified: headed
  tab activation did not deliver that event on this host. ADR 0122 records this
  evidence boundary.
- Save-and-close's own Script JSON/report reads could still hold shared leases
  after the draft was durably saved. ADR 0124 adds requesting-client read
  admission and full-body settlement at the transport/report owner, before
  exclusive Close/Delete/Snapshot. Queued reads resume on every exit; unknown,
  failed or timed-out settlement fails closed. Real JSON and original-CSP HTML
  response holds prove the ordering. No server lease bypass or automatic retry
  was added. Busy409 now gives occupation/retry guidance; revision-conflict409
  keeps conflict guidance. Raw image/video GETs and other clients remain server
  guarded and can correctly return project_busy.

Retired test expectations now use exact Art section membership, current creator
directory entry, shared Root close/recovery and an explicitly configured late
footage fault. No binary/V1 execution, old section-map buffer, shape fallback,
historical reader or automatic data upgrade was restored.

## Executed gates and retained diagnostics

All logs below are in ignored `.local/graph-workbench/`; a launched process is
not a passing gate. The final source/static/wheel identities are recorded below.

- `uv lock --check`, configured API F401 lint and full Python gate exited 0:
  **1182 passed**, 374.54s, one existing Starlette/httpx warning. Backend behavior
  has not changed since that run (`g5-lock.txt`, `g5-lint.txt`, `g5-python.txt`).
- Earlier frontend suite **531 passed / 74 files**, app types and deterministic
  static build exited 0 (`g5-final-frontend.txt`, `g5-final-types.txt`,
  `g5-final-build.txt`). E2E types run before each native invocation.
- Earlier rebuilt wheel and isolated installed smoke exited 0
  (`g5-final-wheel-build.txt`, `g5-final-wheel-smoke.txt`); superseded below.
- Current-contract native run: **70 passed / 2 failed**, exit1, 2.2m
  (`g5-current-contract-native.txt`). Both failures were the test's incorrect
  Brief link locator; captured UI proved the standalone button. Reassessed after
  two unsuccessful attempts. Corrected final viewport/Close run: **15 passed**,
  exit0, 42.5s (`g5-final-viewport.txt`).
- Initial full E2E diagnostic was deliberately interrupted after a runtime fix
  invalidated the unchanged candidate: **132 passed, 14 failed, 4 interrupted,
  36 not run**, exit130 (`g5-full-e2e.txt`). It is not qualification.
- `g5-qualified-full-e2e.txt`: **183 passed / 2 failed**, exit1, 5.6m.
  Operations read raced Undo's durable acknowledgement; the test now awaits the
  actual PUT response and writer readiness. Snapshot collided with initial media
  reads. Its isolated follow-up (**5 passed / 1 failed**, exit1) incorrectly
  expected automatic Brief recovery. After two attempts, trace/screenshot review
  established the exact server draft behind the explicit Restore dialog. The
  corrected journey chooses Restore and retains snapshot/media lineage checks.
- `g5-candidate-native.txt`: **13 passed**, exit0, 27.4s; frontend **531 / 74**,
  app types/static build exited0. Candidate wheel/installed smoke/compile exited0.
  These identities precede the window-blur/lifecycle delta and are historical.
- `g5-final-full-e2e.txt`: **185 passed / 1 failed**, exit1, 5.7m. Shared Root
  Save-and-close saved rev1 correctly but raced an owned Script GET holding a
  shared lease. Close returned project_busy safely. The requesting client's read
  admission/settlement contract and incorrect blanket409 revision-conflict copy
  were corrected at their owners under ADR 0124; server exclusive/unknown-dispatch
  safety remains required.
- `g5-window-event-after.txt`: **4 passed**, exit0, 18.3s; separate Tab/Escape at
  all three viewports and deterministic delivered-window-blur with native pointer
  and textarea focus. Both pre-fix diagnostics are retained (`g5-window-focus-before`
  event probe failed; `g5-window-event-before` reproduced width not restored).
- Current stable frontend **538 passed / 76 files**, app/E2E types and
  deterministic static build exited0 (`g5-read-stable-frontend.txt`,
  `g5-read-stable-types.txt`, `g5-read-stable-build.txt`). Focused native
  **37 passed**, exit0, 1.3m (`g5-read-stable-native.txt`), covers JSON/HTML read
  settlement, Close/save/force-close, late edits, snapshot lineage, Story,
  delivered blur and all three desktop viewports. Initial read-route teardown
  and ApiError fixture diagnostics remain retained; neither is qualification.
- Fresh wheel build, isolated installed-wheel smoke and compileall exited0
  (`g5-release-wheel-build.txt`, `g5-release-wheel-smoke.txt`,
  `g5-release-compile.txt`). The preceding smoke invocation supplied a file
  where the helper requires a directory; its argument-only exit1 is retained
  separately. Fresh lock, configured API lint and archived-reader verification
  exited0 (`g5-release-lock.txt`, `g5-release-lint.txt`,
  `g5-release-archived-reader.txt`).
- `g5-release-full-e2e.txt`: **189 passed / 1 failed**, exit1, 5.6m.
  The prepared-publication guard correctly refused permanent deletion with
  actual409/code project_busy; only the test's raw-code UI text expectation was
  obsolete. The bounded test-only correction verifies that response, human
  occupation/explicit retry guidance, no false version conflict, exact partial
  input and prepared-candidate retention and continued project existence.
  All six direct-delete cases passed, exit0, 22.7s
  (`g5-release-delete-e2e.txt`). No runtime/static/wheel changed.
  The complete unchanged candidate rerun, `g5-release-qualified-full-e2e.txt`,
  finished **190 passed**, exit0, **5.5m**. A subsequent deterministic rebuild
  exited0 and all801 manifest hashes remained identical
  (`g5-release-static-recheck.txt`).
  The staged diff subsequently found one trailing space in a newly added Python
  test, omitted by the earlier unstaged check. Formatting alone was corrected
  before publication; the focused module passed8, exit0, 1.35s. The final staged
  diff check passed. Browser/runtime/static/wheel bytes remain those of the
  passing full gate.

Existing nonblocking diagnostics: Starlette's TestClient/httpx deprecation;
Node's NO_COLOR/FORCE_COLOR runner warning; Vite's large bundle warning; the
pre-existing SettingsDialog number-field React key warning. No new unexplained
resource/page error is accepted. QA uses test-owned roots and fake transports:
zero live provider calls and no creative/media acceptance.

## Evidence key and direct visual observations

The test files below are under `frontend/e2e/` unless stated otherwise:

- **OPS**: `creator-workbench-operations.spec.ts`, exact 123 → 222 → 333,
  replacement inputs, safe bypass/only-delete, every node kind, Cancel/Undo,
  native connection click/drag, capacity/reuse, targets and directory entry.
- **LAY**: `creator-workbench-layout.spec.ts`, 24 nodes/six siblings, three
  desktop viewports, top/middle/bottom, horizontal pan and real separator
  drag/keyboard/cancel/double-click/clamp/persistence.
- **DEL**: `creator-workbench-delivery.spec.ts`, checked FastAPI static bundle,
  clean nine-node/nine-edge readback and exact production controls/Shot handoff
  at all three viewports and both OS colour preferences.
- **TEXT**: `creator-workbench-text.spec.ts`, checked-static blank placeholders,
  Chinese/spaces/literal HTML, unchanged topology, native row-add keyboard
  preview and Escape with zero Root writes.
- **STORY**: `creator-workbench-story.spec.ts`, all repeated scene occurrences,
  scoped dirty ownership, read retry, prepare/check/report/accept/cancel and
  automatic-result checking with no automatic send/accept.
- **PROD**: `creator-workbench-production.spec.ts`, repeated scene coordinates,
  every ordered cut/exact identity/duration, route-only zero footage, stale
  suspension, installed data preservation and first-install restriction.
- **BRIEF**: `creator-brief-structure.spec.ts`, current Brief return and frozen
  proposal rejection; OPS target preview; `source-entry-settings.spec.ts`.
- **CMD**: `tests/test_graph_commands.py`, exact transaction metadata, stale CAS,
  safety/capacity refusals, pending restoration/reuse/input replacement.
- **API**: `tests/test_graph_workbench_api.py`, public preview/apply/recovery;
  `tests/test_graph_authoring_production.py`, exact footage installation.
- **OWN**: existing Art/Cast/Script/source currentness, branch suggestion,
  storyboard, media, H3 fake, branch playback, close and snapshot/restore native
  journeys run in the full browser gate.
- **PURE**: frontend provider/layout/production/projection/model tests and the
  full Python gate. Tests prove contracts; they do not replace native or visual
  evidence or owner acceptance.

Directly inspected the earlier viewport set from `g5-final-viewport`: 12
top/middle/bottom/reopened views, nine panned parallel-row views, six Production
OS-preference views, three exact Shot-owner views and the clean example.
Also inspected five current OPS preview/insert/Undo/reopened views.
The six siblings stay on one row with separated labels and clear input/output
arrows; wide rows pan without wrapping. Short desktop keeps a readable side
inspector and reachable footer. Production shows exact 2.5s last cut and a
separate missing-approval state; the handoff selects `opening—s2—c5` in the
existing Shot owner. Both OS preferences preserve the existing dark theme.
Reopened 1280 views intentionally retain the user's horizontal pan and may clip
the selected card's left edge; a subsequent new selection reveals it. This is
not claimed as a fresh centred view. Full-page Story screenshots supplement
content evidence and do not establish sticky-toolbar geometry.

The stable read-admission candidate produced34 permanent screenshots under
`supporting/graph-workbench-g5/`, with per-image hashes/source paths in
`screenshots.json`. Twenty-seven were byte-identical to inspected predecessors;
all seven changed images were directly inspected, including literal text, all
Story occurrences and changed normal/short parallel-row views. The manager also
directly inspected six current desktop/Production captures. Direct raw-media
quiescence is not claimed: the snapshot journey deliberately leaves the Media
owner before its lifecycle operation. Actual OS delivery of window blur remains
unverified; the delivered-event regression is explicit above. Five final full-gate
OPS screenshots were also copied, hashed and directly inspected, bringing the
permanent G5 image set to39.

## All active C/P items

This is the complete evidence mapping, not a waiver list. All local engineering
gates and independent reviews are closed. Normal activation and exact preservation
readback are verified below; owner acceptance is separate.

| Item | Feature and concrete evidence |
|---|---|
| C01 | DEL checked JS/CSS response/page-error checks; deterministic static/wheel gates; diagnostics listed above. |
| C02 | DEL clean current opening/Story; API authored-opening regression; canonical source-less read-only in m1b1. |
| C03 | LAY selected top/middle/bottom inspector bounds; directly inspected three viewport sets. |
| C04 | LAY document vertical/chart horizontal-only checks; DEL internal scroll reaches last cut/footer. |
| C05 | LAY six same-y siblings and six distinct labels; panned row views directly inspected. |
| C06 | OPS insert/retarget/Undo screenshots; PURE skip-edge gutter and separated convergence labels. |
| C07 | LAY long Chinese and selected cards; DEL both OS preferences; TEXT blank/literal views directly inspected. |
| C08 | LAY keyboard separator and cancellation; DEL Enter Shot handoff; sketch visual/help/focus journey. |
| C09 | LAY every actual row add control; OPS row addition preserves unrelated structure. |
| C10 | OPS explicit detached/mixed row; PURE all-member parent defaults reject one detached member. |
| C11 | OPS visible merge default, explicit pending and changed successor; PURE shared-target requirement. |
| C12 | OPS explicit fresh decision scaffold and ending refusal; CMD decision capacity/retained options. |
| C13 | OPS retained-node reuse and existing-output refusal; CMD identity/body/output preservation. |
| C14 | OPS exact original edge insert and input replacement; CMD option/effect/target preservation. |
| C15 | OPS/LAY real-node counts, explicit edge labels/arrow directions and exact preview table. |
| C16 | TEXT literal Chinese/spaces/HTML creates no b/img elements or handler execution; exact saved prose/topology retained. |
| C17 | OPS Cancel and stale API preview; exact apply once/CAS; TEXT native Escape leaves Root unchanged with zero writes. |
| C18 | OPS independent native click and pointer drag; displaced targets retain nodes/body/downstream. |
| C19 | OPS cycle/self-link refusal; CMD all safety refusals atomic; PURE legal skip-level edge layout. |
| C20 | OPS 333 input chooses exact 222 output outside prior layer; CMD replacement inputs. |
| C21 | OPS original 222 input becomes pending; CMD preserves chosen/prior edge metadata/displaced target. |
| C22 | CMD no-op retarget refusal; OPS Brief cap6 prevents seventh option; exact identities retained. |
| C23 | OPS delete every non-start kind/detached node and protected opening; PROD retained canonical/media. |
| C24 | OPS explicit two deletion modes; CMD detached endpoint metadata/no cascades. |
| C25 | OPS safe bypass; CMD unique no-effect rule and merge/decision safety refusal. |
| C26 | OPS Cancel/Undo exact mapping; PURE late selection preserved or safe fallback if node removed. |
| C27 | STORY original opening episode dirty across nodes/tabs/modes/reload; scoped save only that episode. |
| C28 | OPS mode switch uses Root/readback; graph interaction professional/creator shared owner. |
| C29 | BRIEF/OPS complete target/help preview; settings tests use current integer/shot/branch contracts. |
| C30 | BRIEF stale frozen proposal; PURE target validation and unchanged graph; backend exact contract gates. |
| C31 | OPS target preview explicit confirmation; incomplete/capacity CMD/API refuse admission. |
| C32 | CMD pending/blank drafts and no-worse safety; Brief current128/6 limits; failure readbacks unchanged. |
| C33 | OPS multi-step exact Undo/metadata/selection; provider refuses content-loss Undo; no canon/media rollback. |
| C34 | API stale/recovery and OWN unknown-dispatch/error paths; visible production pause/retry reasons. |
| C35 | OPS reload, shared Root Save-and-close and source recovery; ACK leaves map/canon unconfirmed. |
| C36 | API stale/double submission; provider deferred receipt tests; OPS actual held Undo selection. |
| C37 | G0–G4 attended reviews retained; stable G5 Sol/Medium review and manager Sol/High review closed with no concrete blocker, all801 fingerprints independently verified. Manager separately cleared the precise one-test busy-copy delta and its six-case native result. |
| C38 | DEL clean isolated9/9, opening/Story, exact ACK, no accepted map/run/write, start scroll/closed checks. |
| C39 | Current801-file source manifest plus static/wheel hashes; exact one-native-receipt / five-DB-row retirement and unchanged postactivation evidence in the linked operation receipts. |
| C40 | STORY all repeated scenes/actions/dialogue; PROD exact repeated occurrence/cut order and shared node. |
| C41 | STORY/OWN explicit package prepare/check/cancel/accept/report; API explicit confirm/first installation. |
| C42 | PROD prose/footage/board drift pauses handoff while retaining records; BRIEF and Script currentness. |
| C43 | DEL/PROD exact Shot owner; OWN real approve/keyframe/video/select/play commands with fake transport. |
| C44 | OPS fresh route-only decision; PROD zero rows for route-only; API explicit footage subset/opt-in. |
| C45 | LAY24-node natural page growth, viewport-height clamp/no500cap; direct matrix and code review. |
| C46 | LAY default380/300, pointer/keyboard/Home/End/doubleclick, separate Tab/Escape with persisted width; delivered window blur cancels from textarea focus; resize clamp/reopen/body retained. |
| C47 | DEL visible1280 boundary; current guide; retired390 authoring tests removed, matrix starts1280. |
| P01 | BRIEF existing current project edits; PROD/OWN retained downstream stale evidence; no auto generation. |
| P02 | BRIEF/branch native frozen current settings; API/CMD exact current topology/footage/CAS targets. |
| P03 | STORY automatic check0send0accept; OWN completion/failure/cancel/reopen/poll-stop ownership. |
| P04 | STORY/OWN original report annotation after edit, accepted read-only, reopen/save/cancel/explicit apply. |
| P05 | Branch native suggestion → reviewable Root → explicit confirm/install; no planner equality workaround. |
| P06 | STORY occurrence IDs/reader full route; PROD/DEL exact Shot; OWN character/Art/video/playback IDs. |

## Publication, preservation and product acceptance

Working directly on retained `main`; initial base `e542f49`, initial remote 0/0.
The manager's pre-existing roadmap entry and owner-approved plan are preserved.
Implementation revision `c8f59b77222216f4e2923283606493658f28674f` is pushed to
`origin/main`, with a clean worktree and remote0/0 after publication. The final
staged diff/static check passed; no force push or unrelated work was used.
Full unfiltered [remote CI](https://github.com/Wenjun-Mao/plotloom/actions/runs/37495692517)
is running on that exact revision: verify succeeded and both browser shards are
in progress at16:44:07UTC. Remote CI is not claimed as passed. Docs-only publication
follow-up `892adaf` preserves the same source/static/wheel candidate. The existing
owner browser session was not refreshed or edited; zero provider dispatches.

The stable runtime review used source aggregate
`522ce076d04165149a553f8b76db9d9dae75a0039a355d2427fe72c2df77a6ce`.
Only the busy-delete test correction changes the release aggregate to
`56ee95527c88b8db9e58aaa52aa66ead07f0b688f00d43c49bfd79ecb4631f0d`;
all other800 entries were identical at the full browser gate. A later one-space
Python test formatting correction makes the publication aggregate
`28e9b376708a2601c1f48041ca38dc2f094c87564b4e3e19ef4ab473bbb9a466`;
runtime and test semantics are unchanged. The permanent source manifest and
`artifacts.json` record exact identities:

- JS `47c7d7073601043c83f2e567efef6319014d401b123de1e6e03f5615a1959dc6`.
- CSS `740bf83cf5643e916f98ae353cea8bcba9b7b58ee9625bd6b66443436381a7d1`.
- Wheel `3027bbd4de1f42154b6491d9a886f9bb4b1e2bfc06fe129add07916e46403b7d`.

Read-only normal preflight identifies two projects. Only 雨停以后
`ee271b49-f384-414c-9711-452ee6333b84` has an incompatible retained Graph and
binary accepted section map. The manager approved exact guarded retirement of that
map r1, Graph r1, matching source admission and only unavoidable Graph FK gate/
approval rows. Both heads become missing/r0; source/outline/Brief/drafts/Script/
media/settings and all other projects remain protected. Reset was held until
final qualification and quiescence, now established below;
no fallback, implicit rewrite or deletion of Script/media/assets is permitted.
风里的纸飞机 `2f52cf22-3f4a-4f05-8dc3-4f55e76687b9` remains unrelated/protected.
Specialist busy=false is insufficient alone: queued, running and unknown work,
exact target/revision and protected hashes must be verified before any mutation.

The guarded read-only preflight proved why that boundary matters. Exact retained
character-reference proposal `ij_627a0a680e784d30985054cde8bfd669` is delivered,
but its native task `01a0c506-84d5-7161-8ae0-2ae914e5d81a` still has an exact-identity
queued receipt, with no inflight marker. The specific specialist turn completed
and its delivered image/pin/manifest match stored accepted delivery
`527a476c-61bc-4926-b91a-627014a09768` / manifest hash
`edf322edd038a8e6b3e9db13fae9bba143734c4f33f92d8b6bac8592c7f75f78`.
These facts do not silently settle native ownership. Current package verification
finds only a retired deliveryInstruction mismatch; supported Refresh would reject
it, so no Refresh POST, package rewrite, cancellation or native receipt mutation
was performed during diagnosis. Exact Graph/map retirement authority did not
extend to that independent native record; reset/activation correctly stayed held
until the owner separately authorized the exact terminal receipt reconciliation.

Read-only receiving inspection and native guard checks retained full preservation:
two project DBs (74 tables each),84 project files, application DB/files and three
protected deployment/credential/settings files have aggregate
`237c63897f538817ee625d83320669310666ea07e2b0117d336e4e68364c5122`, identical
to the initial preflight. Credentials are represented only by fingerprints,
permissions and ownership; no secret values or automatic backups were copied.
The ignored one-off helper adds explicit guards that remain active under `-O`,
noncreating existing registry metadata/lock admission, project→registry locks,
reserved receipt destinations, exact full-row/schema/file precommit delta checks,
and protected postcommit readback. Its actual optimized read-only preflight
exits1 on the queued native outcome, before transaction admission. This is a
correct safety refusal, not normal reset qualification or permission to bypass it.
The existing-only helper's attended Sol/High review closed without a remaining
source blocker. Ten optimized synthetic guard checks passed, exit0; normal
quiescence remains blocked. A separate ignored exact terminal-completion helper
passes current delivery/pin/provenance/output/stored-manifest receiving checks
and read-only admission with unchanged preservation. Six isolated existing-method
checks initially passed6, then final10, exit0, including both project leases,
exact one-receipt transition, refusal on inflight/temporary/wrong identity/missing
lock and honest post-effect/evidence-write failure states. The owner separately
authorized only this exact completed-result reconciliation and the prior reset;
attended Sol/High and manager reviews cleared both final refinements before execution.

Actual optimized completion ran once, exit0: only the exact queued receipt became
completed. The original237c… capture remains retained; its sole approved file delta
produced fresh reset baseline
`396b8d3942a7c6225442f64d66fa39e3b1e40f071e4efa2bae6c9ba3786ca712`.
Supported stop exited0, with identical stopped fingerprints. Actual optimized
retirement ran once, exit0: exactly three reviewed PK rows removed and two existing
heads normalized; gate/approval rows0. In-transaction full-row/schema/file delta
and FK checks passed before commit; both project leases and registry lock remained
held for exact postcommit readback. No backup, old-contract adapter, replacement
Graph or automatic acceptance was created.

Supported start/recreate exited0; container healthy at16:42:23UTC and native bridge
health succeeded. Current typed Graph/Source/Cast/Art/Script/Bridge projections and
served JS/CSS passed read-only qualification for both projects. Rain retains exact
source/outline r1, Cast r2/Art r1 and four managed assets; Cast/Art expose computed
staleness without changing their stored rows. Both missing/r0 Graph heads expose
current initial draft payloads, with no Root draft written or production installed.
Wind's existing reopened outline is preserved. The entire postactivation capture
equals postreset aggregate
`2ad5913d7f35ace530add7649b308e891321d67f3fbdbdab48a235b16e1a2033`:
all other rows, schemas,84 project files, application files and three protected
deployment/credential/settings files are unchanged. The manager independently
reconstructed the one-file completion and exact five-row retirement boundaries,
then verified live health, both current Graph endpoints and exact served JS/CSS;
a fresh independent capture after those reads still equals2ad591… in full.
Permanent redacted evidence: [native completion](supporting/graph-workbench-g5/normal-native-completion.json),
[retirement](supporting/graph-workbench-g5/normal-retirement.json),
[activation/readback](supporting/graph-workbench-g5/normal-activation.json).

Engineering qualification, normal activation and owner usability acceptance are
separate. Final next action remains a fresh owner walkthrough of the qualified
real UI. Real creative quality, media choices and audiovisual acceptance are
not established by fake-provider checks or engineering screenshots.
