# Bridge read and controller-claim optimization

Status: owner-approved and independently design-reviewed; implementation starts
after the CLI runtime worker's explicit October 14 source/check handoff.
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
