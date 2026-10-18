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
