# Bridge read and controller-claim optimization

> Local QA artifact references below are historical; the [2026-10-25 cleanup](2026-10-25-top-five-cleanup.md)
> retires their storage, replay/launch/cutback instructions and preservation holds.
> Recorded outcomes and limits remain; current ADR/API contracts still apply.

Status: owner-approved and independently design-reviewed; implementation and
focused guards are complete after the CLI runtime worker's explicit October 14
source/check handoff. Stable code review and matched focused measurement passed;
complete release qualification remains open.
This continues the [Python speed track](2026-10-14-python-context-and-workers.md),
whose fixed-resource 85-percent target remains open.

## Ownership and selected design

The manager is the sole source/check owner in retained main checkout
`autopilot-ux-release`, initially clean at `dab20f6f`. Its executable inputs are
the previously qualified Python candidate. The CLI worker is idle at
`dda660dc`; its runtime source `e24cb80e` passed the allocated eleven native
validate/render pairs and controls (29 commands). The manager audited that
native evidence and the six-file test-only follow-up `7685a868`, including
fresh-checkout log hashes: 109 focused and 49 service checks passed. These are
bounded CLI results, not generation, concurrency, full-release or live proof.

CLI source remains unmerged and frozen during this Python slice. Do not replay
its native gate, resume an old run or infer qualification of combined source.
Before later integration/full qualification, reconcile actual executable,
dependency, test and configuration inputs rather than carrying an old timing
manifest or native proof across changed inputs implicitly.

The attended independent design review (requested GPT-6.1 Sol / High, effective
settings unverified) recommended both minimal optimizations and was collected
before implementation. [ADR 0170](../adr/0170-operation-local-bridge-and-controller-claim.md)
records their root cause, boundaries, rejected alternatives and guardrails.
Keep the claim return and following service read; do not expand into isolation,
ordinary-open validation, broader caching or default-concurrency changes.

## Current parallel ownership — October 14

The separately requested Python coordinator now owns the retained
`autopilot-ux-release` writer; the manager is read-only there and owns final
integration/publication. This supersedes the earlier serial window above.
The [Python plan](2026-10-14-python-context-and-workers.md#separately-requested-python-coordinator--october-14)
records task identity, resource allocation and exclusions. CLI work has priority;
no broad qualification or benchmark starts without a manager-allocated quiet
window. Existing Bridge/claim evidence stays scoped and unchanged.

## Matched measurement selected before code changes

Run the existing `verify.py focused` command with exactly these selectors before
and after, using a fresh temporary root for each quiet run:

- `tests/test_production_bridge.py`
- `tests/test_production_bridge_fresh_preinstall.py`
- `tests/test_autopilot_authority.py`
- `tests/test_autopilot_text_controller.py`
- `tests/test_storyboard_review_timing.py`
- `tests/test_specialist_settings.py` (unaffected control)
- `tests/test_autopilot_images.py::test_complete_pack_selects_all_subjects_and_unique_route_frames_without_human_facts`

Verify the actual collected inventory and unchanged selected tests/fixtures;
the design review estimated 73 cases, not yet executed qualification. Capture
external command wall time, pytest time, logs and source/dependency/host inputs.
New regression files run separately and do not enter the matched union. One
pair is scoped evidence, not a repeated-median or whole-suite speed claim.

## Implementation and verification

1. Record this design and baseline before production changes. Implement the
   private Storyboard resolved context and lazy Bridge-local projections, with
   ordered fresh lists and unchanged independent installation behavior.
2. Inject the dedicated controller-claim transaction lease. Retain lifecycle
   transaction primitives and existing claim/return behavior verbatim.
3. Add focused regressions for ADR 0170, including actual same/new-claim
   metadata, refused states, malformed returned evidence rollback, joined
   manual/autopilot commands, two-connection SQLite contention and non-SQLite
   delegation. Retain production-source and final-handoff safety coverage.
4. Run new guards, the unchanged matched union and affected Storyboard,
   autopilot safety/recovery/late-delivery/geometry/handoff checks. Review the
   stable candidate independently; reopen for concrete findings only.
5. Reserve full local qualification for the stable release candidate, reconcile
   exact inputs and current timing weights, then publish under repository
   policy. Hosted CI, CLI pool work and any future-launch activation are
   separate gates. Report actual complete-suite timing without claiming 85
   percent from selected tests or estimates.

Stop only for a material scope/authority change or an unresolved concrete
failure. The owner has already approved this bounded implementation; routine
progress does not require another permission question.

## Baseline and focused checkpoint

Before production edits, clean `37756cfd` passed the exact 73-case union above.
External command time was **71.41s**; pytest reported **64.63s**. Both exited
zero. The input fingerprint remained
`ba57bfa2c56d911e1652eeb3e283440c1294285ec89f0bcd17df8a588810c20f`
before/after; host fingerprint was
`e157fcd2c8db7127845d443a20785aff48490f424fcbfe1eb56ec31bb040db92`.
Submodule revision remained `4f9b2128c82adf623f594ba714c97d0afcfc16a2`.
No CLI/native activity or other test job ran during the measurement.

Retained root: `.local/remaining-cost/bridge-claim-before.2oqItH/`.
`focused.log` SHA-256:
`31af3814f3040bb6ab06ceb6e0ff7356b38afc4f4cd6400fba5bb26aa4d817da`.
The ordered, 73-line collected inventory (`cases.txt`) has SHA-256
`599c2c85f8228f6eb6e1c0e425e38be0bad7f065c86dc10a67a7699a82c3bde6`.
The matched after-run is recorded below.

The two new regression files contain 47 cases. Together with the unchanged
12 Storyboard-operation guards, all **59 passed**. Seven module-ownership
guards, scoped Ruff F401 and `git diff --check` also passed. The first run's
one failure was in the newly injected malformed-frame query substitute: it
assumed Core column queries expose ORM `entity` metadata. Narrowing that test
substitute to its exact ORM entity repaired the test; production code did not
change. The failed log, four-case return-validation rerun and stable 59-case
rerun are retained under `.local/remaining-cost/bridge-claim-*.log`.

Selected timing tests and their existing helpers are unchanged. This focused
checkpoint does not establish whole-suite success, publication or the
85-percent target.

## Matched after-run and independent code review

Clean `d09322cb911986c0592c39435af44c3d69e04c6a` passed the same **73 cases**,
with byte-identical collected inventory and unchanged existing test/helper files.
External command time was **65.21s**, versus **71.41s** before: one pair observed
**8.68% less wall time**. Pytest reported 57.19s versus 64.63s. Both commands
exited zero, used fresh temporary roots and ran without competing test/native
jobs. This is scoped single-pair evidence, not a repeated median or whole-suite
speed claim.

The after input fingerprint remained
`6a88498ac86cbddb5fa804dfd3a8ef79efbe6050bcad68f5d1770b03cc2561df`
before/after the run. Host, lockfile, project dependency declaration and Python
version file matched the baseline. Retained root:
`.local/remaining-cost/bridge-claim-after.bSdrjL/`; `focused.log` SHA-256
`8353efa439bcaa1d56cbc5ae1f4bb652c70582dcdc4c95829e516b02b947db88`.
`cases.txt` has the same `599c2c85...` SHA-256 recorded above.

An attended independent read-only code review of `37756cfd..d09322cb`
(requested GPT-6.1 Sol / High; effective provider settings unverified) found no
concrete correctness, security or regression findings. It confirmed preserved
diagnostics/installation failures, independent video-source currentness,
lifecycle transaction semantics, joined-command authority and the service's
fresh post-claim read. The reviewer ran no checks. Non-SQLite coverage remains
a transaction-delegation stub, not live backend qualification.

The complete Python inventory and release gate are still pending. The old
duration manifest binds the earlier 1,911-case executable inputs and cannot
silently qualify this changed candidate. Reconcile current scheduling inputs
before interpreting complete-suite timing. CLI integration, provider proof,
hosted CI and live activation remain separate.
