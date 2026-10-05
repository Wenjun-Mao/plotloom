# Six current-contract repairs

Status: implemented, independently reviewed, fully locally qualified and published.
Full remote CI is queued; normal-runtime activation remains a manager checkpoint.
Delivery authority: [approved assignment](../roadmap/2026-10-04-current-contract-repairs.md).
Baseline: `fa8e80c9122fc20189a1f30dd1f12ea040db5070`, retained `main`.
Runtime activation and creator acceptance are separate manager checkpoints.

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
| Remote CI | [Run 37248436763](https://github.com/Wenjun-Mao/plotloom/actions/runs/37248436763), queued on exact runtime candidate at `2026-10-05T00:40:39Z` (October 4 Toronto), full `browser_grep=.*` |
| Whitespace and remote divergence | Passed; remote had no divergent commits before normal push |

## Activation and acceptance boundary

Implementation and fixture verification do not establish normal-runtime
activation or creator usability/creative/media acceptance. Normal 8841 was not
restarted; the manager must coordinate activation against the normal installation
and preservation evidence. The retained 8851 copy, specialist bindings,
credentials, owner projects/media, H3, Narrative Forge V1 and Chinese manual were
not changed. Disposable fixture directories provide the execution evidence;
there were no generation/provider calls or new paid-provider fallbacks.
Existing records provide no task-level usage/cost delta, so none is claimed.
