# Six current-contract repairs

Status: implemented, independently reviewed, fully locally qualified, published
and activated on normal 8841 after owner approval. Full remote CI is in progress;
creator usability and creative acceptance remain separate.
Delivery authority: [approved assignment](../roadmap/2026-10-04-current-contract-repairs.md).
Baseline: `fa8e80c9122fc20189a1f30dd1f12ea040db5070`, retained `main`.
The normal activation result is recorded below; fixture verification does not
establish creator acceptance.

## Root causes and delivered contracts

| Outcome | Root cause and owning-layer repair | Evidence |
| --- | --- | --- |
| Lifecycle and native ownership | Lifecycle admission inspected publication rows, while native execution lived in the installation registry. Cancelling publication did not stop queued/unknown execution. Composition now supplies project-specific execution admission; close, archive, delete and snapshot hold the project lease before reading registry/dispatch ownership. | `test_project_specialist_ownership.py`: all five text stages and all three image targets, cancelled queued/unknown attempts, restart, unrelated idle project, reservation/receipt crash windows and dispatch race. Existing exact-proof settlement suites remain authoritative for release. |
| First Outline reprepare | The view treated a retained cancelled candidate as permanently occupying first preparation. The explicit action now permits another preparation from confirmed Source with the existing currentness/read-only guards; sending and acceptance remain separate. | `outline-cancel-reprepare.test.ts`; real disposable browser store checks unchanged Source, different job, retained original package and no native send. |
| Stale pre-install bridge | Currentness and installation history were collapsed in the UI. `hasInstallation` exposes persistent admission independently of staleness; preparation refuses any prior installation or unresolved intent job. Fresh preparation preserves history and resets intent/presentation review; local edits require explicit abandonment. | `test_production_bridge_fresh_preinstall.py` and `production-bridge-panel.test.ts`: renewed F5, history, failed prepare, local edits, unresolved jobs and installed refusal. |
| Retained browser input | A generic aggregate-read error became a discard-only unavailable state. Temporary failure, project 404 and confirmed archival now expose read-only original project/scope/base JSON with copy/export/keep/retry. Restore rechecks active exact project/base; changed versions enter existing conflict processing and failed authority reads keep writes disabled. | `retained-author-draft-recovery.test.ts`/app-state: exact retry/restore, foreign authority, revision conflict/reload, archival/deletion, auxiliary 404 and Home retention; browser test verifies downloaded JSON and unchanged canonical title. |
| Duplicate explanation | The UI label omitted the existing contiguous ready canonical-prefix contract and ignored its receipt. Confirmation explains Brief/prefix/exclusions; completion presents actual `copiedThrough`/`omittedStages`. | `project-lifecycle.spec.ts` exercises real server duplicate confirmation and receipt with existing revision/idempotency/original-preservation behavior. |
| Choice read retry | Failure or mismatched ownership remained an indefinite null/loading state. An identity-owned read hook exposes failure/staleness and explicit retry; superseded responses cannot install. Exact edges, current storyboard and completed node still gate choices. | `bridge-choice-retry.test.ts`: failure recovery, edge/source mismatch, node completion and late response after project switch; existing preview browser contracts. |

Durable decisions: [ADR 0093](../adr/0093-configurable-specialist-handoffs.md),
[ADR 0114](../adr/0114-direct-project-deletion.md),
[ADR 0058](../adr/0058-f1a-source-outline-review-contract.md) and
[ADR 0116](../adr/0116-current-contract-recovery-and-copy-scope.md).
Author/model ownership of generation content did not change. Trusted code owns
native dispatch identity, lifecycle admission, source currentness and CAS; the
author retains explicit prepare/send/review/restore/copy/keep/discard decisions.
No correction machinery or older-contract replay layer was introduced.

## Independent review and corrections

Attended read-only GPT-6.1 Sol / High review covered the stable six-repair
candidate and ran 32 frontend and 26 Python checks. It found one P2: if authority
changed during the restore recheck, the old recovery dialog still allowed only
restore/discard and suppressed existing conflict processing. The fix captures
the original record/workspace and sends version changes to conflict processing;
temporary/missing/archived/foreign authority refusals expose retained inspection
and disable editor writes. The reviewer independently ran 51 related frontend
tests on the correction and reported no blocking follow-up findings.

The first full Python gate found three obsolete test assertions (1,121 passed):
two called the removed duplicate private publication scanner and one omitted
`hasInstallation`. Assertions now exercise the shared publication contract and
current response; no compatibility shim was added. A fresh-preinstall test first
changed upstream Brief authority rather than obtaining a fresh F5 revision, and
then reused a fixed job ID; it now renews current F5 with a distinct ID. These
fixture failures did not justify weaker source-currentness or identity guards.

An earlier full browser attempt was intentionally stopped for the concrete
restore correction: 45 passed, two interrupted, 119 not run. It is not a passed
gate. The final unfiltered run qualifies the corrected candidate separately.

## Executed verification

Runtime candidate: `0aff7dd49325f7424341d6007f083739bf96aadc`, pushed to
`origin/main`. The subsequent roadmap/receipt commit contains only delivery
documentation and is not relabelled as the executed runtime candidate.
Ignored local logs: `.local/relay/contract-repairs-2026-10-04/`.

| Check | Result |
| --- | --- |
| Frozen all-group Python sync and API F401 | Passed |
| Full Python suite | 1,124 passed in 440.34 seconds; existing Starlette/httpx warning |
| Frontend unit suite | 502 passed across 67 files |
| Frontend types / production build / checked static | Passed; rebuilding committed assets produced no diff; existing large-chunk warning |
| Archived prompt reader | Passed |
| Wheel build / installed-wheel smoke | Passed |
| Focused browser repairs and lifecycle | 8 passed |
| Full unfiltered browser gate | 166 passed in 8.9 minutes, two workers; no filter/skips/assertion weakening |
| Remote CI | [Run 37248436763](https://github.com/Wenjun-Mao/plotloom/actions/runs/37248436763), started on exact runtime candidate at `2026-10-05T00:40:39Z` (October 4 Toronto), full `browser_grep=.*`; still in progress at the activation checkpoint |
| Whitespace and remote divergence | Passed; remote had no divergent commits before normal push |

## Activation and acceptance boundary

The worker delivery did not restart normal 8841. The owner subsequently approved
activation while pausing the walkthrough; the manager activated it as recorded
below. Implementation, fixture verification and backend activation do not
establish creator usability/creative/media acceptance. The retained 8851 copy, specialist bindings,
credentials, owner projects/media, H3, Narrative Forge V1 and Chinese manual were
not changed. Disposable fixture directories provide the execution evidence;
there were no generation/provider calls or new paid-provider fallbacks.
Existing records provide no task-level usage/cost delta, so none is claimed.

## Owner approved normal activation

On October 4, 2026, the owner said to proceed with backend activation and could
wait. Before activation, the manager independently reviewed the scoped changes
and reran 121 Python and 33 frontend checks, all passing. The initial Python
collection invocation referenced a nonexistent filename and ran no tests;
corrected invocations used the existing native safety and image settlement
suites. The read-only handoff review is retained in
`.local/relay/contract-repairs-manager-2026-10-04/review.json`.

The existing native registry was idle (`busy: false`, `activeTasks: []`). The
supported `uv run --locked python services/creator_workbench/manage.py start
--data-root .local/creator-walkthrough` completed successfully, recreated the
normal container and verified the native bridge. No service launcher, deployment
shape, schema, project data or provider configuration was changed. The deployment
checkout was `53631ce76e22cf301c2057c7db90af923f66c15d`; its executable source is
the qualified `0aff7dd` candidate, with only delivery documentation intervening.

- Container: `0f819ea546c4ed55760b8a219cc95422117f937a2250da432df199d1fb8c28a5`.
- Image: `sha256:cbad1d8b9e6bea8dc280acbc94d0236dc361280c600ea91427c128122613b876`.
- Start: `2026-10-05T00:56:47.467999574Z` (October 4, 20:56 Toronto).
- Container health and `/healthz`: healthy / `status: ok`.
- OpenAPI exposes the new boolean `ProductionBridgeState.hasInstallation`,
  confirming the restarted API loaded the repaired response contract.
- Served `/v2/workbench.js` matches checked SHA-256
  `94479fdd2f219a17241181bc9e5d8616f16a07102f53416cc2216ec5759c6c11`.

The existing read-only capture helper produced byte-identical preservation
records under `.local/source-entry-2026-10-04/`:
`before-current-contract-activation.json` and
`after-current-contract-activation.json`. `cmp` passed; both SHA-256 values are
`a35a717f3cb2b79840c28a978453641f056a85ec971d240951068c92141134c8`.
These cover both normal projects, all 74 table projections per project, seven API
projections per project, all captured project-home file hashes (13 for
风里的纸飞机 and 67 for 雨停以后), and specialist settings. Deployment configuration
and the existing bridge credential hash also remain unchanged. This is captured
row/projection/file equality, not whole-SQLite-file byte equality.

风里的纸飞机 remains at source r1 and retained outline r1 with
`outlineStatus: reopened`; candidate `ch_fe401cbcb93c43208035a42d8e9ce51d` remains `prepared` and
unsent. 雨停以后 retains accepted outline r1. The native registry remains idle;
the video budget remains unconfigured with no attempts. No send, cancel,
acceptance, lifecycle mutation, reset, copy, deletion or H3 activation was used.
The creator's browser tab was not refreshed or operated; unsaved browser input
and the deferred Chinese manual were left untouched. Backend checks do not
claim fresh live browser or creator usability acceptance.
