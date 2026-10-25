# Validated installation-only reader

Status: owner-approved implementation plan, 2026-10-25. The owner approved scoped
implementation, qualification, quiet activation/rollback and old proposal retirement
through Relay Direct. Source implementation passed independent review; final local qualification is
pending. Activation remains
with the manager after independent review and local qualification.

## Outcome and reason

Material inventory needs validated installed-production authority. It currently
calls store.production_bridge_state().installation, which also constructs
proposal/presentation models, preparation availability and job views. Expose a
small installation-only reader using the existing validation owner, and route
only initial_inventory() through it.

Success means the same installed authority is checked without unrelated review
projection. This is a separation of responsibilities with a current consumer;
no measured speedup, performance target or new benchmark is claimed.

Retained source R is /Users/wjmao/.codex/worktrees/b30f/plotloom, local main
c0d4630587e3d85d5aa9ec72d466c1f14de99b53 at implementation start. Installed checkout
P is /Users/wjmao/projects/HU/plotloom; its current identity is checked by the
manager before activation. Refresh identities/status at execution rather than
assuming those revisions or current host counts remain unchanged.

## Design and scope

1. Add get_installation(project_id) returning InstalledProduction or None to
   ProductionBridgeInstallation. Use the existing read lease, require the project
   and bridge head, then delegate to installation_in_session().
2. Add the typed ProjectStore.production_bridge_installation() facade in
   project_creative_stages.py.
3. Change only autopilot_materials.initial_inventory() to consume that facade.
   Missing/outdated installation still refuses before inventory proceeds; cast,
   art, topology, production-closure and workload checks retain their ownership.
4. Keep the full production-review reader and its current exception ordering,
   context reuse and UI response unchanged. Narrow/full equality is required for
   installation results on valid supported states, not unrelated review-UI
   failures. A current installation remains distinct from a newer pending rebuild.
5. Preserve installed admission/proposal evidence, exact canonical identities and
   upstream currentness checks. Use existing lease/snapshot semantics; introduce
   no cross-step/session cache, schema migration, fallback reader, compatibility
   adapter, new public endpoint or automatic write.

The existing validator in production_bridge_installation.py remains the
authority. Do not duplicate it or move inventory into a new orchestration layer.
The three product files are currently 128, 197 and 137 lines respectively; their
existing responsibilities fit the change. Add cohesive focused coverage instead
of substantially expanding the 493-line test_production_bridge.py. Apply the
repository's modularity rules without unrelated restructuring.

The old committed proposal 11b7ad65 on refs/heads/codex/python85-release
(76d6a916) is a reference for this narrow change, not an instruction to merge
that historical branch. Adapt to current main. Its old ADR 0164 is not an
accepted decision on current main; record the adopted decision through the
current ADR/index convention after implementation approval.

## Smallest local end-to-end proof

Before broad qualification, create one disposable source-shaped project outside
the installed data root using existing _store, _prepare_installable_bridge and
_accept fixture owners. Use real current schema, persistence, validators and
ordinary prepare/review/accept operations; authored test deliveries do not
establish native model/provider acceptance.

Exercise no installation -> accepted current installation -> inventory read ->
supported canonical or upstream edit -> outdated installation/inventory refusal.
Reopen the project and verify persisted identities and lack of read-side writes.
After installation setup, guard full review projection so a successful inventory
read proves it used the narrow path. A second read after a committed edit must
observe drift, including through a separately opened handle where applicable.

Also exercise the actual material-review API's readiness refusal using
test_autopilot_review_readiness.py and the existing disposable controller
environment. Its synthetic host is test plumbing: no real generation, new grant
or owner approval is needed. Keep the observable assertion scoped to this reader,
API readiness and persistent state, not provider E2E or complete media production.

The implementer owns fixture setup, readback and cleanup. Close handles/services
and remove temporary fixtures/helpers when their verification purpose is done;
retain concise results and actionable failures in this plan, not raw media,
a new evidence archive or a permanent QA installation.

## Acceptance and failure cases

| Case | Required result |
| --- | --- |
| Fresh project or prepared-but-unaccepted proposal | Reader returns None; inventory preserves the existing readiness refusal |
| Current accepted installation | Same InstalledProduction value as full reader, and same inventory identities/subjects |
| New pending replacement proposal | Current installation remains readable independently of proposal/preparation/job projection |
| Canonical head/revision/hash/status or upstream source drift | Existing outdated status/reasons remain visible; inventory refuses |
| Missing installed proposal, mismatched proposal hash/inputs or incomplete installed-stage identities | Existing hard failure is preserved; no fabrication, repair or fallback |
| Missing project or bridge head | Existing project/head admission failure is preserved |
| Unexpected validator/context failure | Propagates; never converted into current/absent installation |
| Successive reads across committed changes, reopen or rollback | Current lease/snapshot rules apply; no new stale cache or partial write |
| Read-only contract | Project/canonical/media/approval/run state is unchanged by reads |
| Projection separation | Inventory does not invoke get_state, proposal/presentation parsing, preparation/quiescence projection or job views |

Preserve full-reader regressions that intentionally check proposal-first failure
ordering. The new reader may avoid those unrelated projections, but it must
still reject corruption of the installation evidence it actually relies on.
No generation, approval, selection, dispatch or grant authority is introduced.

## Ordered implementation and verification

1. Refresh clean source/installed revisions, the exact retained proposal ref,
   dependency/validator readiness and existing fixture contracts. Resolve
   demonstrated local prerequisites before broad runs; do not recreate deleted
   historical QA workspaces or source copies.
2. Adapt the three small product changes and readiness-test stub. Add
   tests/test_production_bridge_installation_read.py, reusing current fixtures
   and the old proposal's useful cases after review. Exercise the small local
   journey above before expanding coverage.
3. Run focused affected contracts through the existing runner:

       uv run --locked --no-sync python scripts/verify.py focused

   Select the new installation-reader file, test_autopilot_review_readiness.py,
   test_bridge_operation_context.py, test_production_bridge.py,
   test_production_bridge_fresh_preinstall.py, and the production-rebuild,
   material-inventory/import and handoff cases affected by the actual diff.
   The implementer chooses exact cases/files and any additional lease/freshness
   regressions; these examples are not a fixed ceiling or substitute for review.
4. Register the new test file with the existing creative-production owner in
   scripts/testing/module-ownership.json. Review story-authoring/readiness
   ownership and shared consumers; avoid adding a verification framework.
   Use module expansion/show if helpful, without automatically running the whole
   module union before full qualification.
5. Have an independent read-only reviewer inspect the stable source/test diff
   and scoped evidence, especially authority, freshness, read-only behavior and
   separation from pending proposals. Address concrete findings in the same
   assignment; manager retests target changed inputs or remaining uncertainty.
6. Run one stable final local full gate:

       uv run --locked --no-sync python scripts/verify.py full

   This touches persistence authority across layers, so frontend-only
   qualification is insufficient. Follow AGENTS evidence-reuse/failure-repair
   policy: diagnose failures and rerun changed/failed downstream gates as needed;
   do not repeat unchanged broad qualification or waive real failures.
   Hosted CI is optional and unrequested, not a pending release blocker.
7. Record the adopted internal-read decision in a concise current ADR, add it to
   the appropriate ADR/spec index and production-identity engineering contract,
   and update this plan with actual results. Keep historical failures/limits
   truthful. Save one coherent qualified checkpoint on main; documentation-only
   follow-ups do not require another full run.
8. Carry out quiet installed activation and the rollback contract below, then
   retire the old proposal ref once the adaptation is incorporated and qualified
   on main. Recheck the exact ref value before removal; use compare-and-delete
   against its observed object ID. If it moved or contains newly unreviewed work,
   adjudicate that delta without discarding another writer's work or reopening
   the whole historical cleanup.
9. Replace temporary-hold wording in the cleanup plan/roadmap with the actual
   resolution. Delete stale historical launch/retention instructions, preserve
   current decisions, and remove temporary verification artifacts. Do not keep
   the branch merely as an audit record after resolution.

Implementation is serial on retained main with one tracked writer. Standing
approval for separate Codex tasks and model/reasoning selection remains valid;
use Relay Direct after implementation approval. Bounded read-only review can run
alongside independent verification, but reviewers do not become concurrent
writers or duplicate qualification owners. Keep native subagents attended through
their actual final, independent review, idle confirmation and archival.

## Activation, permission and rollback

Approval of this plan is intended to cover scoped implementation, local
verification, local main checkpoint, temporary-ref retirement and controlled
quiet backend activation at the existing P installation. It also covers planned
rollback and normal in-scope fixes without repeated milestone approvals.
That operational scope is now owner-approved through Relay Direct; activation
remains a manager-owned step after source handoff and qualification.

At activation, use existing deployment tooling and the same data root, providers,
profiles, settings and credentials. Backend Python imports require service
recreation. manage.py start rebuilds/recreates that container and installs the
owned Mac bridge, but may reuse its running process when the launchd definition
matches. That definition hashes host_bridge.py, not all imported product code.
Inspect the current lifecycle and relevant imports: explicitly restart the owned
bridge through its supported launchd lifecycle if needed to load changed code,
then verify its expected runtime/import identity. Reuse an unaffected bridge only
with evidence; command success alone does not prove reload. Coordinate both
components' quietness. Wait for real queued/active/validator work and admitted writes to
settle naturally; do not cancel, resend, clear holds or signal unrelated processes
to manufacture an idle checkpoint. A change in actual operational risk is a new
decision, not authority for a bypass.

Before touching P, record read-only comparison baselines for all current project
rows/media/drafts, application settings, host attempts/reservations/revocations,
protected credentials/configuration fingerprints, checked validators and runtime
identity. Preserve the actual current set, not hard-coded eight-project or
85-attempt totals if the owner has since worked. Never dump credential values.
Use temporary derived hashes/metadata; no bulk live-data copy or audit archive.

Reuse the final full gate's exact-wheel build and isolated installed-wheel smoke
where its inputs match; this already supplies disposable installed-package
proof. Resolve a concrete package-proof gap narrowly, without a duplicate broad
run or packaging framework. Then switch P through supported checkout/deployment
lifecycle, recreate the service at the quiet checkpoint and handle the owned
bridge's actual reload requirements above. The live deployment mounts source:
verify those qualified bytes and loaded-code identity separately from the wheel
proof. Verify qualified source/package
and static bytes, HTTPS/API health, current project/catalog/selected-media
readability, validator readiness and preservation comparison. Do not launch
new provider work to test this read-only change.

Keep the single existing functional recovery source/wheel package usable until
activation is verified. If startup or read-only acceptance fails, return P to the
previous qualified revision and restart through the same owned tooling; preserve
newer user data and report the failure rather than rewriting it to the baseline.
No schema/data migration is planned, so rollback is a code/runtime operation.
After success, refresh that one recovery package to qualified current code/docs,
verify it, and remove temporary candidates/helpers. No historical media or second
permanent recovery archive is justified.

## Completion and exclusions

Done means the narrow reader and inventory consumer are qualified on main,
independently reviewed, activated with preservation checks, documented through
current authority indexes, and the old proposal ref/temporary hold is retired.
Report source qualification and installation verification separately. No human
creative/audio acceptance or speedup is implied.

This scope changes no frontend, public API payload, persistence schema, provider,
prompt, generation budget, rights/creative attribution, existing UNKNOWN guard,
test runtime or dependency contract. No push, GitHub CI/Actions, media generation,
unrelated optimization or tracked-media cleanup is authorized by this plan.

Independent planning review (requested GPT-6.1 Sol / Medium; effective settings
unverified) found no unnecessary approval, budget, attempt or serialization gate.
Its bridge-reload finding is incorporated above; package qualification reuses
the final full gate rather than adding a duplicate broad run. No implementation,
activation, branch retirement or product test was performed during planning.

## Implementation checkpoint, 2026-10-25

Worker `01a173e0-83be-7912-8bb9-012c7e550a41` is the serial source writer in R.
The three product changes retain existing installation validation and read leases;
only initial inventory switches consumers. ADR 0219 records the internal reader.

Small local persistence/API journey passed before broader checks: the focused
runner selected
`tests/test_production_bridge_installation_read.py::test_persistent_inventory_journey_observes_upstream_drift`
and `tests/test_autopilot_review_readiness.py` (10 passed, 5.41s pytest; 7.980s runner).
The real disposable project used current fixture prepare/review/accept operations,
read back identical installed authority/inventory after reopen, then observed a
separate handle's committed Script reopen as outdated and refused inventory.
Logical persisted rows were unchanged by reads; the actual review/handoff API
refused incomplete material without mutation. This is local reader/API evidence,
not provider or media-production acceptance. No generation or grants were used.

Envelope: locked existing environment, CPython 3.12.13, macOS 27.0.1 arm64.
Focused affected-contract command:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_production_bridge_installation_read.py \
  --pytest tests/test_bridge_operation_context.py \
  --pytest tests/test_production_bridge.py \
  --pytest tests/test_production_bridge_fresh_preinstall.py \
  --pytest tests/test_production_rebuild.py \
  --pytest tests/test_production_rebuild_freshness.py \
  --pytest tests/test_production_rebuild_guards.py \
  --pytest tests/test_production_rebuild_dependencies.py \
  --pytest tests/test_autopilot_material_imports.py \
  --pytest tests/test_autopilot_handoff.py \
  --pytest tests/test_autopilot_review_readiness.py
```

First result: **99 passed, 1 failed**, 104.29s pytest / 114.978s runner.
The failed new canonical-status fixture injected `outdated`, outside supported
`StageStatus`/`CanonicalReplacementHead` vocabulary. The full review projection
correctly rejected that invalid fixture. Corrected it to `stale`; production code
was unchanged. Also strengthened inventory equality against the full-reader path
and added an ordinary supported canonical-edit regression. Reran only the changed
file with
`uv run --locked --no-sync python scripts/verify.py focused --pytest tests/test_production_bridge_installation_read.py`:
**15 passed**, 10.81s pytest / 12.449s runner. The **86 unchanged existing affected
cases** from the first run retain their passing evidence; this was not a second
broad run. The corrected file covers absent/prepared/current/pending installation,
upstream and canonical drift, reopen/separate-handle freshness, committed reversal,
corrupt evidence, admission failures, unexpected context errors, read-only logical
rows and projection separation. Existing full-reader exception-order/atomic
rollback regressions passed in the wider selection.

The existing module-plan command
`uv run --locked --no-sync python scripts/verify.py module --module creative-production --depth contract --show`
confirmed the new file in creative-production (43 pytest owner files); this is
expansion evidence, not module qualification. Readiness remains story-authoring.
Changed Python files passed `ruff check --select F401`; `git diff --check` passed.
The old proposal was inspected as reference; no branch merge/cherry-pick occurred.
Its ref still resolved to `76d6a916b4368e63dd8fe36479cd2f57e6f17c09` at this check.

Disposable pytest project roots from these runs were removed after readback or
had already been removed by pytest retention. No raw media/evidence archive or
historical QA root was created. Independent read-only review completed with no
findings; manager inspected the actual product/test diff and agreed. The manager
requested the missing exhaustive ADR catalogue entry, now added with a dated
amendment cue. No source correction was required. The stable full local gate is
next under the same sole qualification owner. No full/hosted gate, installation,
recovery refresh, live-state edit or proposal-ref deletion has yet been performed. Manager owns activation/recovery/ref
retirement. Known phase timings beyond the runner measurements are unavailable.

## Stable full qualification and scoped repair, 2026-10-25

Independent review and manager product/test diff inspection found no source issue.
The missing exhaustive ADR catalogue entry/datestamp was added before committing
candidate `b0ce2e66bd132700ce99759800618c1e847779fb` on retained main, clean at start.
The sole qualification owner ran exactly
`uv run --locked --no-sync python scripts/verify.py full` once.

Original full result: **failed**, 2098.419s, at the unfiltered browser gate:
**352 passed, 6 failed** (650.451s browser step; 10.8m Playwright). No automatic
retries were configured. Earlier passing gates retain their results:

- Locked dependencies; FFmpeg/FFprobe 9.0.2; API F401; archived prompt reader.
- Frontend: 172 files / **1538 tests passed** (6.358s step); frontend typecheck passed.
- Python: **4019 passed**, exact native inventory SHA-256
  `4fa34465cdd80bfb36cfc92a44105e4b1339e1d79031da008c8aa41d935e8c48`.
  Worker 1: 2113 passed / 1 warning, 1406.72s pytest, 1420.414s runner;
  worker 2: 1906 passed / 9 warnings, 806.56s pytest, 819.560s runner.
  Both complete-case fingerprints validated; Python full step 1433.595s.
- Deterministic frontend build passed (1.320s); checked static parity passed.
- Browser fixture typecheck passed; allocation verified 99 specs / 358 cases,
  shard sizes 101/69/80/108 with no overlap or omissions.

All six failures were strict locator ambiguity, rather than failed product state:
exact global text `归档只读` or `冻结只读` matched the toolbar badge plus six
workflow labels. Retained snapshots showed the correct banner/read-only controls.
Affected cases: directory archived-open access; lifecycle archive/restore/delete;
Source archived read-only at 1700x900, 1280x768 and 1280x460; storyboard batch
playback while Frozen. Five assertion sites in those four specs now scope the
same exact text to `page.getByRole("banner")`. All other assertions remain.
The manager independently reviewed the archived-status contexts and approved
this fixture correction. The Frozen case has the identical diagnosed cause.

Failure contexts were inspected in the existing `frontend/test-results` output;
no separate failure archive was created. The original failure remains recorded
here even after temporary outputs are removed. Product, static and dependency
inputs remain unchanged from b0ce2e66; only these test locators and documentation
change. Preserve the Python/frontend/unchanged-browser evidence above. Wheel
build/smoke were not reached in the original full run and will be run narrowly
with ordinary existing commands after affected-spec verification.
