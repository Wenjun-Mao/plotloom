# State-aware project directory actions · 2026-10-24

Status: implemented, independently reviewed, locally frontend-qualified and
activated with preservation-checked live Safari inspection. Qualified executable
and clean installed revision: `4c6db5ffe94ee0e37008945c5d9b2170f2763c98`.
Retained R baseline `87d949de6678699a0334609571fc6b4530a797e9`.
Agent QA does not establish owner personal acceptance. The
[approved plan](../roadmap/2026-10-24-project-directory-actions.md) owns scope.

## Root cause and boundary

The directory projected current-workspace actions onto every active row because
only closed/archive state influenced action selection. Current identity was only
a label. The repair is an explicit row projection plus a lifecycle-owner guard
against noncurrent force exit. Safe noncurrent Close and all existing server
admission, draft/read ownership, confirmations and deletion contracts remain.

The unchanged directory summary supplies positive nonterminal pipeline facts,
not complete native-media occupancy. Queued/running/cancel-requested ordinary
Close/archive are disabled with a short reason; null/terminal summaries do not
claim idle. Copy, Open, current Exit and deletion preview retain their supported
paths. Missing folder state is visibly unconfirmed. Backend-open state says
“未关闭”, distinct from current workspace identity.

Actual-diff boundary for reduced final qualification: frontend row projection,
accessible in-flow disclosure, one current-identity lifecycle guard, CSS, frontend
tests, existing local test ownership manifests and docs. API clients/request
payloads, backend/API schemas, persistence/admission/auth, provider/prompt behavior,
dependencies/locks, build tooling and package contracts are unchanged. Final generated
assets are bound by the refreshed checked-static manifest below. Existing test manifests register the new
permanent regression; no CI/workflow preparation or hosted execution occurs.

## Executed development evidence

Evidence root: `.local/project-directory-actions-20261024/` in retained R.

- `early-ui.log`: 3 real isolated two-project Close→Reopen/Open journeys pass at
  1280×768, 1280×460 and 1700×900. More Enter/Escape/focus return/outside dismissal,
  current-only save/exit, noncurrent exact Close and continued current identity.
  `early-pixels/` retains all three screenshots; worker and root inspected actual
  short/large pixels. This is Vite development evidence, not final static proof.
- `focused-safety.log`: 4 passes, archive/restore refusal+retry, unchanged exact
  typed deletion and safe noncurrent busy-Close refusal preserving current work.
- `focused-expanded.log`: units 29 pass; UI 3 pass/1 fails because the added
  combination fixture used an incorrect welcome button label. Retained failure
  trace/pixels: `first-combination-failure/`. Corrected the test entry to the
  actual “打开项目目录”; no product workaround.
- `focused-ui-corrected.log`: combined archived+closed real Restore→Reopen and
  current+archived read-only title pass; three new post-command focus assertions
  fail. `first-focus-failure/` retains traces/pixels. Browser disables the focused
  More trigger before the effect can record its owner; root cause is disclosure
  focus ownership. Capture intent before admission; after settlement restore only
  within the same project/current identity, and never steal an active dialog input.
- `focus-failed-success.log`: 2 exact causal browser cases pass: 1280×768 full
  journey now checks post-command focus; archive refusal/retry checks returned
  More focus. `focus-fix.log` separately retains the initial one-case repair pass.
- `focused-freeze.log`: all 40 cases in the four affected unit files pass,
  including app-state navigation, directory projection/read recovery and command
  ownership. Tests cover every nonterminal/terminal summary, unknown folder state,
  closed+archived ordering, no explicit-close capability, current+archived, changed
  row facts/read withdrawal and no focus theft across confirmation/workspace.
  `freeze-typecheck.log`: frontend typecheck passes. Browser invocation also passes
  its native E2E typecheck. `git diff --check` passes.

The repository quick development tier was mistakenly invoked before stable review;
it includes unfiltered frontend units. Preserve `quick.log` as **failed**: 1,504
pass/1 fails on the old always-visible Archive selector. The affected app-state
unit now opens More before invoking the same draft-guard action; its focused
regression passes above. Quick stopped before its typechecks. This run is not
final qualification and is not relabelled green.

All browser data roots/processes are fixture-owned and isolated. The new journey
checks zero dispatch requests and the offline provider's zero request counter.
No live project/settings/accounting/UNKNOWN state is touched. Combined-state API
operations target only its fresh disposable project. Native-media occupancy is
not fully enumerated and no idle/capability authority is invented.

## Initial qualification plan (historical checkpoint)

At the initial checkpoint work stopped for root's stable source review. After
concrete findings closed, the sole
worker will run unfiltered frontend units, both typechecks, two deterministic
isolated builds with exact SHA-256 tree equality, formal checked-static refresh,
affected whole-file browser journeys and direct pixels. Reuse unchanged backend
evidence after reviewed boundary confirmation. Do not rerun broad/full backend,
real providers, installed-service restart, push or GitHub CI. Root owns final independent
review, live Safari, preservation-checked frontend-only activation and cleanup.

Product outcome at that initial checkpoint: actual isolated directory Close/Reopen/Open and
combined lifecycle states; final static qualification and activation remain
pending. Product/infrastructure/coordination timing breakdown was not measured;
logs retain individual check elapsed times rather than invented percentages.

## Stable review repairs (before final qualification)

Independent/root review identified three concrete P2 gaps. Repair ownership stays
in the frontend layer:

1. A painted project snapshot can remain A while the route already owns B.
   Force exit now captures route project/epoch/stage before confirmation, carries
   that exact operation into execution, rechecks before admission/disposition and
   preserves the existing post-await checks. It cannot discard A or blank B from
   stale consent. `review-repairs-units.log` covers before-confirmation/pending-
   confirmation invalidation and valid A exit; `review-causal-corrected.log`
   proves actual same-document browser history with B's GET held and A's pending
   confirmation, zero Close/discard requests and successful B readback.
2. Archived+closed title navigation could call Open before Restore. Disable that
   title with Restore-first guidance; archived+open title retains read-only
   navigation. Both capability states are covered; after Restore, Reopen remains
   capability-gated. No navigation/backend behavior is expanded.
3. Existing unique-deletion assertion now expands More first and counts exactly
   one deletion command in its accessible management group. A More accessible
   label can contain the project's title (including 删除), so counting labels
   across the whole row was a test-selector mismatch. Capability=false browser
   regression now asserts disabled Reopen/title plus the same prior-error and
   zero-Open requirements rather than trying an impossible click.

Focused repaired freeze evidence:

- `repaired-freeze-units.log`: 45 cases across all four affected unit files pass.
- `review-causal-browser.log`: two pass/two fail; preserved trace shows the
  chained fixture's post-Reopen direct archive got 409 `another local writer is
  active`. The deletion count also matched the More label's project title.
- `review-causal-corrected.log`: held-B/exit, unavailable-capability/error and
  exact-one idle deletion pass; combined fixture's follow-up fails because it
  awaited Brief even though Reopen correctly routes Creator. After these two
  fixture failures the method was reassessed: split current-archived state into
  a separate fresh pre-archived fixture rather than chaining timing/route
  assumptions. No product retry/tolerance or backend guard change.
- `review-combination-split.log`: exact combined Restore→Reopen and separate
  current-archived read-only title cases pass (2).
- `review-no-capability.log`: archived+closed Restore then disabled Reopen/title,
  clear capability explanation and zero Open requests pass (1).

The new directory spec now uses existing `checkedStaticTest`. Focused review
proof used explicit isolated Vite output `review-static-current/` through
`PLOTLOOM_STATIC_DIR`; normal checked assets and installed P remain untouched.
Its build log is `review-static-current-build.log`. This is focused development
proof, not final two-build determinism or final static qualification. Tests for
held B continue to use their existing Vite fixture. Source is refrozen for root
review; final qualification has not started.

## First final frontend qualification, retained before keyboard follow-up

Root and independent review closed the three P2 findings before these runs.
All checks passed on that stable pre-focus-follow-up candidate:

| Check | Result / evidence under `.local/project-directory-actions-20261024/` |
| --- | --- |
| Unfiltered frontend units | 1,511 cases / 170 files pass; `final-units.log` |
| Frontend / E2E typechecks | Pass; `final-typecheck.log`, `final-e2e-typecheck.log` |
| Two isolated complete builds | Identical 7-file trees; `final-build-a.log`, `final-build-b.log`, `final-build-a.sha256`, `final-build-b.sha256` |
| Formal checked-static refresh | Standard `build:deterministic`; exact match to both isolated trees, `final-checked-refresh.log`, `final-checked.sha256`, `final-build-comparison.log` |
| Local test ownership manifest contract | 7 pass; `final-manifest-contract.log` |
| Explicit 11 whole-file browser selection | 79 pass in 5.8m; `final-browser.log`, artifacts in `final-browser/` |

The browser command was `npm --prefix frontend run test:e2e -- --workers=1
--output=../.local/project-directory-actions-20261024/final-browser` followed by
exact whole `e2e/*.spec.ts` files: `project-directory-actions`, `project-lifecycle`,
`project-lifecycle-errors`, `project-folder-close`, `project-save-force-close`,
`project-direct-delete`, `project-unified-delete`, `project-read-close`,
`project-folder-snapshot-restore`, `art-review`, `sketch-visual-system`.
No test-name/line filters were used. The new directory file's six cases use
checked static; existing files retain their established fixtures.

Two isolated build commands used the standard Vite build/config with explicit
`--outDir ../.local/project-directory-actions-20261024/final-build-a` and `-b`.
The normal checked tree was verified unchanged before the formal refresh.
Full relative-path SHA manifests include every file; all seven paths agree,
not just the two changed assets. Worker and root directly inspected the final
1280×768, 1280×460 and 1700×900 captures in `final-browser/project-directory-actions--*/directory-more-*.png`:
primary/current hierarchy, management text, focus ring and reachability are
clear with no material clipping/overlap. These original passing logs/bytes are
retained rather than overwritten by follow-up qualification.

## Keyboard ownership follow-up and focused red-to-green proof

Before commit the worker identified a concrete missing keyboard path: outside
pointer dismissal alone permits Tab out of A's disclosure and Enter into B's
while A remains open. A's earlier capture-Escape handler can then steal B's
Escape/focus. Root confirmed this is an in-scope owning-layer contract defect,
allowed the unchanged 79-case run to finish, and authorized a causal repair.

`keyboard-red-unit.log` and `keyboard-red-browser.log` retain the expected failed
new assertions: after outside focus/actual Tab into B, A remains expanded. The
browser trace/pixels are in `keyboard-red-browser/`. The small repair adds
`focusin` to the same bounded outside-event owner, preserving Tab within the
management group and removing competing stale Escape owners when focus leaves.
No central menu abstraction or command/admission change.

`keyboard-green-units.log`: all 18 directory projection cases pass.
`keyboard-green-browser.log`: the new exact two-row case passes on the isolated
`keyboard-green-static/` build (explicit `--outDir`, `keyboard-green-build.log`).
It checks Enter into A, Tab within A, actual Tab into B closing A, opening B,
then Escape closing only B and returning B's focus. Original normal static assets
are still the preceding qualified bytes at this review checkpoint. The new
source/test/ADR/playbook amendment is refrozen for root review before refreshed
final qualification.


## Final refreshed qualification and idle handoff

Root accepted the narrow owning-layer keyboard repair after reading its actual
source and red/green evidence. No remaining review finding. Final qualification
keeps the actual frontend-only boundary above: backend code/schemas/API payloads,
admission/auth/persistence, provider/prompts, dependencies, build tooling and
package contracts are unchanged against trusted `87d949de`. Only generated
`workbench.js` / `workbench2.css` product bytes differ. Existing backend evidence
is reused; no full backend, hosted CI, live-provider or installed-service run is
claimed. This is bounded local frontend qualification, not full release or owner
creative acceptance.

| Refreshed check | Result / exact evidence root `.local/project-directory-actions-20261024/` |
| --- | --- |
| Unfiltered units | **1,512 pass / 170 files**; `refreshed-units.log` |
| Both typechecks | Pass; `refreshed-typecheck.log`, `refreshed-e2e-typecheck.log` |
| Two isolated complete builds | All **7 paths/SHA-256s identical**; `refreshed-build-a.log`, `refreshed-build-b.log`, matching `.sha256` files |
| Formal deterministic static refresh | Exactly matches both isolated trees; `refreshed-checked-refresh.log`, `refreshed-build-comparison.log`, `refreshed-checked.sha256` |
| Four whole-file browser owners | **25 pass in 1.6m**; `refreshed-browser.log` |
| Three exact force-consent cases | **3 pass in 9.6s**; `refreshed-force-consent.log` |
| Pixel inspection | Worker directly viewed final **1280×768 / 1280×460 / 1700×900** captures in `refreshed-browser/project-directory-actions--*/directory-more-*.png`; labels, focus ring and all More commands remain reachable without clipping/overlap |
| Diff integrity | `git diff --check` passes; scoped source/docs/tests/generated checkpoint on `main` |

The two standard Vite/config build invocations use explicit isolated outputs
`--outDir ../.local/project-directory-actions-20261024/refreshed-build-a` and `-b`.
The preceding checked manifest remained unchanged until the standard
`npm --prefix frontend run build:deterministic` formal refresh. Sorted complete
relative-path manifests include every file. Final manifest file SHA-256:
`55141bb48c77d46bf54e442e7db510d3ada146579f607d1a384a02431e904ee8`.
Final `workbench.js`:
`75312bec7d0280b165d9a8975e40fafdde6192a85b6c8a92e40d4a95fd21ef86`;
`workbench2.css`:
`5d694081b283fbc901de0edcad9f2ad7e79621d1994d43dc71cc45cb99e5c19a`.

The 25-case command is the existing `npm --prefix frontend run test:e2e --
--workers=1 --output=../.local/project-directory-actions-20261024/refreshed-browser`
with whole files `e2e/project-directory-actions.spec.ts` (7 checked-static cases),
`e2e/project-lifecycle-errors.spec.ts`, `e2e/project-lifecycle.spec.ts`, and
`e2e/project-unified-delete.spec.ts`. The separate existing save/force-close file
uses exact grep `failed draft save retains input; force consent|force exits while
a prepared job|pending A exit`, one worker, and output `refreshed-force-consent`.
This is intentionally 28 refreshed cases, not another automatic 79-case run.

Explicit evidence reuse: retain **52 distinct unchanged cases** from the prior
79-case pass: art review (9), direct deletion (11), folder Close (8), snapshot/
restore (5), owned read/Close (3), desktop visual system (5), and the other eleven
save/force-close cases. Only outside-focus dismissal changed after that run;
request/lifecycle/backend inputs, consent/disposition semantics and those cases'
asserted owning behavior remain unchanged. Their concrete confirmation/refusal/
deletion consumers were refreshed above. The result covers **80 distinct browser
cases compositionally (28 refreshed + 52 retained)**, not a single 80-case
invocation. Original failed quick/development/red results remain failed history.
The local manifest contract's unchanged 7 passes are also retained.

Root owns live Safari, a fresh eight-project/settings/accounting/UNKNOWN2 baseline,
any preservation-checked frontend-only activation, and task/Relay cleanup. Worker
made no installed-P edits, live project mutations, real-provider calls, push or
GitHub Actions/workflow changes. Normal generated assets in retained R now match
the final qualified manifest. Worker stops after the coherent scoped `main`
commit; no additional edits or runs follow handoff. Activation and human/creative
acceptance remain separate and unperformed by this worker.

## Independent manager review and activation

Root collected the actual worker final and verified the worker idle, clean `main`
checkpoint, changed source and retained logs/manifests. The independent Luna/Max
reviewer found the route-owned confirmation race, archived+closed title bypass
and stale test interactions; its second read-only final resolved all three P2s.
Root separately reviewed the subsequent three-line outside-focus repair and its
actual red/green evidence, and viewed all three refreshed desktop captures.
Requested model/effort settings remain unverified by the host.

At 2026-10-24T22:31:18Z the fresh immediate-before snapshot matched the first
successful current capture exactly except observation time. All eight projects,
including the completed one-minute example, are protected without any historical
row exclusions or controller-claim normalization. The initial preservation helper
had incorrectly required DELETE header mode based on an immutable connection's
PRAGMA response. The first root capture failed before producing JSON. All eight
actual headers retain WAL mode without sidecars. The corrected diagnostic reads
under each existing exclusive OS lease, refuses sidecars and requires unchanged
database bytes through inspection; it changes no journal mode or application
data. The failed capture and correction are retained in the private root evidence.

Root confirmed both checkouts clean and compared the qualified candidate against
installed `ac27bad98bb453fe39c1a16fdc6815b4795f6c54`: the backend tree differs only
in the two generated frontend assets; dependency, package and build inputs are
identical. The host installed checkout was switched, detached and clean, to
`4c6db5ff`. No service or bridge restart was needed. All seven static paths in R,
installed P, the running container, local HTTP and the HTTPS entrypoint match the
qualified manifest exactly. Both HTTP paths return `Cache-Control: no-cache`;
health remains OK. Container ID/start time/PID and bridge PID 66847 are unchanged.

Native Safari inspection used one fresh temporary tab with the completed example
as current project. Actual AX and pixels show all eight rows: current-only
Save-and-close/Exit, Open/More on the other seven, and the truthful summary limit.
Expanded noncurrent More exposes Copy/Archive/Close/Delete; Escape collapses it,
returns focus to its own trigger and retains the directory. Outside focus also
dismisses it. The full two-row Tab/Escape sequence is established by the retained
isolated Chromium regression; no browser keyboard preferences were changed.
No live lifecycle or content command was invoked. Root closed only its temporary
tab, refreshed the original idle directory to the new build, retained all eighteen
original tabs, and restored the previously selected tab.

After activation and again after Safari (2026-10-24T22:35:38Z), the complete current
snapshots equal immediate-before except observation time: every project database
file byte, full table fingerprint and persistent file; every application/host
table; settings, credential fingerprints and permissions; queue/validator/slot
state; and both exact UNKNOWN holds. There are zero active attempts, enabled queue
entries, validators or slots. Native runtime identities are unchanged. This is
agent-operated UI verification, with destructive/live lifecycle paths established
only on disposable fixtures. No provider dispatch, push or hosted CI occurred.

Private manager evidence: `.local/project-directory-actions-20261024-root/`:
`preservation-before-activation-v2.json`, `preservation-immediate-before.json`,
`preservation-after-activation.json`, `preservation-after-safari.json`,
`static-activation.json`, `native-safari.json`, and
`preservation-probe-correction.md`. All three native assignments were attended;
actual finals, source and relevant evidence were collected before cleanup.
