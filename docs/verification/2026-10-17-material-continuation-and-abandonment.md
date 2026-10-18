# Material continuation and explicit project abandonment

Source candidate: isolated `b30f/plotloom`, baseline `d37a3f02`, uncommitted.
Implementation contract: ADR 0190. Source is not installed or activated. No live
project, runtime setting, credential, native generation or remote result changed.
Root owns independent review, full qualification, commit/push and activation.

## Implemented behavior

Explicit continuation creates a successor with fresh frozen future authority.
Adopted text, reference and frame evidence links exact original checkpoints;
original frame generation/selection decisions and receipts remain unchanged.
The real disposable partial-pack test changes future execution pins, produces
only missing images, completes the material pack and records a fixture human
handoff through the genuine review owner. This is a contract test, not live human
creative acceptance. Unresolved and delivered-but-unadopted original operations
remain explicit blockers, never implicit resend or automatic adoption authority.

Explicit abandonment requires a current server preview, revisions, exact title,
uncertainty acknowledgment, stopped automatic work and positively proven local
quiescence. Host revocation precedes erasure and preserves UNKNOWN evidence,
budgets and capacity. Ordinary deletion remains separate. The immediate-prior
layout can be abandoned directly without an unsafe UNKNOWN upgrade. A minimal
installation deletion intent exposes pending erasure after restart even when the
manifest is gone; observation never continues deletion. Workspace-exit wording
distinguishes exit from safe backend close.

## Executed focused verification

Commands below use `uv run --locked --no-sync python scripts/verify.py focused`
from the source checkout unless otherwise stated.

| Explicit selectors / command | Result |
| --- | --- |
| `--pytest tests/test_autopilot_authority.py --pytest tests/test_direct_project_deletion.py --pytest tests/test_autopilot_schema_upgrade.py` | 46 passed before the new preserving-layout case was added |
| `--pytest tests/test_autopilot_continuation.py --pytest tests/services/creator_workbench/test_project_abandonment.py --pytest tests/services/creator_workbench/test_codex_exec_supervisor_pool.py` | 34 passed; then 2 additional host-fence cases were added |
| `--pytest tests/test_project_abandonment.py --pytest tests/test_codex_exec_pool_migration.py --pytest tests/test_autopilot_schema_upgrade.py` | 22 passed, 2 test defects diagnosed below |
| `--pytest tests/test_project_abandonment.py --pytest tests/test_autopilot_schema_upgrade.py::test_immediate_prior_upgrade_preserves_cancelled_run_and_all_material_bytes` | 4 passed after the test corrections |
| `--pytest tests/services/creator_workbench/test_project_abandonment.py --pytest tests/services/creator_workbench/test_codex_exec_image_failure.py --pytest tests/services/creator_workbench/test_codex_exec_supervisor_validation_lifecycle.py --pytest tests/test_project_abandonment.py` | 22 passed |
| `--pytest tests/services/creator_workbench/test_project_abandonment.py` | Final 10 passed, including project-isolated admission and manifest write-vs-revocation fences |
| `--playwright e2e/autopilot-guidance.spec.ts --playwright e2e/project-direct-delete.spec.ts --playwright e2e/project-save-force-close.spec.ts` | 22 passed, 1 ambiguous pre-existing button selector corrected |
| `--playwright e2e/autopilot-guidance.spec.ts --playwright e2e/project-direct-delete.spec.ts --playwright e2e/project-lifecycle.spec.ts` | 16 passed, including corrected selector and all new consent/screenshot cases |
| `npm run test -- tests/autopilot-presentation.test.ts tests/project-directory-read-recovery.test.ts` in `frontend/` | 22 passed |
| `npm run typecheck` and `npm run typecheck:e2e` in `frontend/` | Passed |
| `npm run build:deterministic` in `frontend/` | Passed; checked static assets refreshed; existing chunk-size advisory |
| `uv run --locked --no-sync ruff check src/plotloom/api --select F401` | Passed, the repository's API lint gate |
| Full Ruff on all newly added Python files; `git diff --check` | Passed |
| `uv run --locked --no-sync python scripts/testing/check_module_ownership.py` | Native ownership union passed; no test bodies executed |

The 0029-to-0030 Alembic test passed and preserves the original run-column
projection. The project-folder preserving upgrade test retains a cancelled run,
all original policy/receipt/frame data and retained asset/package byte hashes.
The deletion tests exercise current and immediate-prior layouts, exact consent,
neighbor preservation and retry after manifest withdrawal/application reopen.

Diagnosed development failures: the UNKNOWN test initially expected zero image
calls despite its intentionally sent original job; it now compares unchanged
before/after calls. The preserving-layout test initially compared the new column
set instead of the original projection. The erasure-failure wrapper initially
omitted `rmtree.avoids_symlink_attacks`. A later permission-check assertion was
placed in the wrong test and corrected before final 10-case success. Browser
failure was an ambiguous substring selector after adding the distinct abandon
action; affected existing selectors now require exact button names. Broad Ruff
over pre-existing changed modules reports baseline style/re-export findings;
the established API lint and full lint on newly added Python modules pass.

## Desktop evidence and remaining gates

Disposable browser screenshots, under the isolated checkout only:

- `output/playwright/continuation-blocked.png`
- `output/playwright/continuation-consent.png`
- `output/playwright/abandonment-consent.png`
- `output/playwright/pending-deletion.png`

The abandonment consent screenshot was inspected locally. All screenshots are
fixture evidence, not live activation or creative acceptance. Full release
qualification, unfiltered hosted CI, installation/schema migration and live UI
acceptance were not run in this source assignment. No full gate was launched.

## Bounded independent-review corrections

The independent review identified four contract defects: retry erasure trusted
the directory identity checked before acquiring its lock; continuation consent
did not identify its predecessor; an unacknowledged deletion request permanently
latched its initial preview; and current-run/frame-origin selection depended on
wall-clock ordering. These are corrected at the erasure, admission, durable-intent
and lineage owners, respectively. ADR 0190 records the corrected contracts.

Retry erasure rechecks the approved directory inode and held lock after lease
acquisition, then performs recursive deletion relative to the approved directory
descriptor. Deterministic home/lock substitution regressions retain the deletion
intent and never erase the replacement. Continuation requires `expectedRunId`
and compares it transactionally, so old consent cannot act on a cancelled child
with coincident revisions. Unacknowledged consent can be refreshed only after a
new explicit preview for the original home/inode/manifest; acknowledged host
revocation stays immutable. Pending UI requests a new preview before renewed
consent when acknowledgment is absent. Run currentness and frame provenance now
follow exact lineage/decision identity, not timestamps.

| Explicit selector / command after corrections | Result |
| --- | --- |
| `--pytest tests/test_autopilot_continuation.py` | 13 passed; includes equal/backwards-clock chains, inherited review/handoff/video readiness, exact origin tampering and ancestor-consent replay |
| `--pytest tests/test_project_abandonment.py` | 7 passed; includes deterministic directory/lock substitution, revoke failure, lost acknowledgment and refreshed consent |
| `--pytest tests/test_autopilot_authority.py --pytest tests/test_autopilot_schema_upgrade.py` | 37 passed; affected authority and preserving-upgrade neighbors |
| `--playwright e2e/autopilot-guidance.spec.ts --playwright e2e/project-direct-delete.spec.ts` | 11 passed; predecessor payload and fresh pending-deletion preview asserted |
| `npm run typecheck` and `npm run typecheck:e2e` in `frontend/` | Passed |
| `npm run build:deterministic` in `frontend/` | Passed; checked assets refreshed; existing chunk-size advisory |
| Full Ruff on newly added Python files; API F401 lint; `git diff --check` | Passed |
| `uv run --locked --no-sync python scripts/testing/check_module_ownership.py` | Native discovery passed: 3187 pytest, 1401 Vitest, 325 Playwright cases; no test bodies executed |

One corrective test initially expected HTTP 409 for a simulated host failure.
The established `ImageJobError` handler returns HTTP 422; the regression now
asserts that status, the exact `project_abandonment_unconfirmed` error code and
the single attempted host operation. No handler or product error semantics were
changed to satisfy the test. New-file Ruff also diagnosed import order, a loop
lambda binding and a nested context manager; these were corrected before lint
success. The loaded pending-deletion screenshot now waits for an enabled retry
action. Continuation consent, blocked continuation and loaded pending deletion
screenshots were inspected locally; they remain disposable fixture evidence.

## First full qualification failure and acknowledged-deletion quarantine

The root-owned original full gate ran naturally to completion on committed
candidate `5cb08123`: exit 1, `VERIFY_SUMMARY` 1058.130 seconds. Worker 1 reported
11 failed / 1691 passed; worker 2 reported 35 failed / 1450 passed. Total Python:
46 failed / 3141 passed (3187 cases). The preserved root log is
`.local/material-recovery-20261017/full-5cb08123.log`. The 1401 frontend unit tests
and type checks passed; qualification stopped at Python, so downstream release
gates were not qualified. This corrective source materially invalidates that
candidate's release qualification; it is not a successful full gate.

Diagnosis distinguished product defects from stale fixtures. Receipt projection
strictness exposed a real unscoped inheritance query. The corrected geometry
query uses one project/run/operation-correlated exclusion while preserving the
original byte/hash/failure-order oracle unchanged. Current checkpoint validation
no longer probes for missing inheritance tables. Only exact frozen prior-layout
owners route to retained validation without continuation; bridge adoption follows
that same explicit boundary. Minimum SQLite fixtures now contain the current
inheritance/run fields and assert exact origin SQL while retaining decode counts,
failure priority, independent observations and read-only guarantees. View fixtures
explicitly name `predecessor_run_id`; lifetime counts derive once after the
existing typed policy/checkpoint validation. Serial-upgrade tests compare every
original column/value and separately assert the new NULL ancestry/empty links.

Independent fault reproduction also showed that successful host revocation plus
a failed initial manifest unlink left ordinary writes admitted; old consent could
then erase new work. ADR 0190 now defines acknowledged intent as irreversible
installation-scoped quarantine. Registry write/reopen/lifecycle admission checks
the existing ledger after acquiring the project lease. Create/resume preflight
before publishing a home and recheck under lease. Composed recovery copying and
publication, in-place upgrade and text startup obey the same boundary. Passive
inspection remains available, and explicit exact-consent erasure retry is separate.
No service, backup, long application transaction or global bytes revocation added.

Corrective commands use the same focused runner prefix as above:

| Explicit selectors / command | Result |
| --- | --- |
| `--pytest tests/test_autopilot_policy_decoding.py --pytest tests/test_autopilot_profile_bindings.py --pytest tests/test_autopilot_view_checkpoints.py --pytest tests/test_receipt_material_projections.py --pytest tests/test_material_closure_bytes.py --pytest tests/test_codex_exec_pool_project_upgrade.py` | 100 passed, including all original 46 failing cases |
| `--pytest tests/test_project_abandonment.py --pytest tests/test_project_deletion_quarantine.py --pytest tests/test_receipt_material_projections.py --pytest tests/test_autopilot_profile_bindings.py` | 53 passed after fixing the exact-prior bridge-adoption caller chain |
| `--pytest tests/test_project_abandonment.py --pytest tests/test_project_deletion_quarantine.py --pytest tests/test_autopilot_continuation.py --pytest tests/test_autopilot_schema_upgrade.py` | 46 passed; current/prior erasure, actual pre/post-manifest permission failures, restart, post-lease ACK, no publication on quarantined identity, genuine continuation and preserving migration |
| `--pytest tests/test_project_storage_recovery.py --pytest tests/test_direct_project_deletion.py` | 29 passed; portable CLI, held closed-folder leases, recovery-required behavior and ordinary deletion retained |
| `--pytest tests/test_project_deletion_quarantine.py` | Final 9 passed on the completed admission source, 12.476 seconds focused |
| Full Ruff on the new quarantine module/tests; F401 on changed Python files and API; `git diff --check` | Passed |
| `uv run --locked --no-sync python scripts/testing/check_module_ownership.py` | Native discovery passed: 3197 pytest, 1401 Vitest, 325 Playwright cases; no test bodies executed |

The first quarantine run passed all nine new cases but failed the immediate-prior
abandonment case because bridge-adoption validation still called current-only
inheritance lookup. That explicit caller chain was corrected, not tolerated via
table absence. A neighboring focused invocation was refused before any test body
because an operational-state filename did not exist; the corrected exact recovery
and deletion selectors passed above. Frontend inputs/assets are unchanged by this
correction, so their prior evidence is retained rather than rerun. No corrected
full gate, commit, push, installation, native generation or live acceptance was
performed by this source writer.
