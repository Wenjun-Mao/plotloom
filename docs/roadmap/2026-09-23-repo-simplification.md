# Repository simplification: bounded tracking plan

Status: approved to track and reconcile, **not** blanket approval to delete code or redesign contracts. Initial spot-check baseline: local `main` at `f867eb0` (2026-09-23); documentation Batch A was reconciled against `b552039`. The roadmap [entrypoint](README.md) remains the delivery authority; this page does not change product priorities.

## Source manifest and first gate

The four untouched source files are in `/Users/wjmao/Downloads/plotloom simplifications/`:

| Source filename | Evidence baseline | Use |
| --- | --- | --- |
| `2026-09-18-codebase-simplification-audit.md` | `4676a9d` | F1–F27 and amended dispositions, not current-main facts |
| `2026-09-18-adr-review.md` | companion to `4676a9d` | A1–A16 and amended authority findings |
| `2026-09-19-plotloom-simplification-adr-independent-audit.md` | `72edb23c3a823eb0623bf71dc2d16fb515654f37` | SIM-01–04 and ADR-SIM-01/02, independently checked at that revision |
| `2026-09-19-plotloom-simplification-adr-insertions.md` | `72edb23c3a823eb0623bf71dc2d16fb515654f37` | Copy-ready wording for the same SIM/ADR-SIM additions; **not another independent set of findings** |

- [ ] Reconcile every proposed B/C slice against then-current `main` before implementation: exact surviving symbol/caller, current contract owner, behavior to preserve, tests and shipped-artifact check, and whether the finding was corrected or withdrawn by audit amendments. Keep unresolved items as investigate/defer. Recheck after any intervening main change. The original `f867eb0` spot checks are preliminary, not that completed per-symbol reconciliation.

The [finding/disposition register](2026-09-23-simplification-dispositions.md)
records the current-main documentation reconciliation and preserves amended or
withdrawn findings. It does **not** complete the per-symbol B/C implementation
gate above; those tracks still require their own current-source checks.

## Approved small tracks

| Track | Preliminary finding disposition | Primary dependency and owner | Next bounded action / stop |
| --- | --- | --- | --- |
| **A — documentation authority** | **Completed locally at `cb6fa27`.** The [ADR entrypoint](../adr/README.md), scoped 0004/0014/0042 and H3 notes, `0040` full-slug links, live H3 operator guidance, and [disposition register](2026-09-23-simplification-dispositions.md) reconcile the bounded claims while retaining history. | Documentation owner; independent read-only review and link/diff checks passed. | No schema, ID, persistence, or runtime change. Further ADR claims remain individual `Park`/`Test` leads, not an open Batch A rewrite. |
| **B — narrow verification tooling** | **Assessment only:** [source-backed proposal](2026-09-23-simplification-b-assessment.md). CI is still `workflow_dispatch` only; existing CI builds/checks the bundle and smokes the wheel, but shared Playwright serves Vite. Ruff/ESLint remain absent from checked manifests; isolated Ruff F401 diagnosis found two API unused imports. | Engineering owns a later bounded implementation; director owns any automatic CI trigger change. | If approved, add one built-static browser smoke and an API-only F401 gate with focused cleanup. Keep push/PR triggers separate. Stop before broad lint/autofix, import deletion, build-system replacement, or C. |
| **C — proven retirements** | SIM-01/02 remain plausible: `RunContext.providers` and empty `ProviderPorts()` callers still exist; `recover_runtime_jobs` still has only its two old helper tests as observed callers. Neither is yet proven safe to remove on current main. | Per-symbol consumer/export/packaging check; engineering owns each separate patch and its focused regressions. | First characterize the provider bag, then separately the startup helper; preserve real provider resolution, `GenerationEngine`, artifact context, active startup reconciliation, recovery/acknowledgment, and the third lifespan test. Stop if an active consumer or contract appears. |

## Investigate or defer; no implementation approval here

| Finding group | Preliminary disposition and next authority |
| --- | --- |
| SIM-03 / old-new storage capability switches | **Defer contract redesign.** False states still encode loading, failure, retry, and unsaved-project behavior; director must approve an initialization contract and test matrix before any branch removal. |
| SIM-04, F13–F15 / V3 profile, hashes, schema presence | **Investigate identity rules.** Only pure construction that preserves frozen profile versions, read-only loaders, credential admission, and distinct validation policies may be proposed later. |
| F3–F4, F17 / migration and historical readers | **Defer deletion.** Prove present write/read populations and restore obligations first; do not infer dead code from a static search or reset user-valued data. |
| F5–F7, F9–F12, F16–F19, F22–F27 / broad residuals and clones | **Inventory only.** Each symbol needs its own current consumer, safety, and product-boundary decision; no umbrella cleanup assignment. The optional F24 `projectIdFromLocation` candidate and duplicate draft-key helper remain small checks, not a new framework. |
| H3, security, platform, acceptance-tool relocation, old pipeline retirement | **Out of this track.** Keep their existing owners and gates; the source reports explicitly do not authorize bundling them here. |

Completion of this tracker means decisions are navigable and each approved small slice has its own evidence and checks. It does not mean the audit's suggested sequence has been implemented or that a shorter codebase is itself a product outcome.
