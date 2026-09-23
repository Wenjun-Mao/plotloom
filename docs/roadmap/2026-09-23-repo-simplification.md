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
| **A — documentation authority** | ADR-SIM-01/02 are scoped candidates; A1/A2/A4/A8 require current-authority triage, not wholesale ADR rewriting. `docs/adr/README.md` is still absent; ADR 0004 still says UUID-only, while ADR 0014 still has browser-provisional draft prose. | Reconciliation first; documentation owner with director deciding any contested live contract. | Annotate only live authority and scoped supersession: record IDs vs authored stable IDs; durable draft receipt vs provisional browser buffer; preserve explicit canonical Save and historical text. Stop before changing schema, IDs, or persistence. |
| **B — narrow verification tooling** | F1 remains true in one respect: CI is `workflow_dispatch` only. Existing CI already builds the bundle, runs Python/frontend/E2E, and smokes a wheel, so do not describe those gates as absent. F20/F21 are instrumentation/build-entrypoint leads, not cleanup authorization. Ruff/ESLint are still absent from checked manifests. | Reconciliation and a stable shipped-artifact browser baseline; engineering owns tooling, director owns any change to automatic CI triggers. | Propose a small lint gate and a recurring browser check of the actual shipped artifact, with bounded failure triage. Keep automatic push/PR CI triggers as a **separate explicit decision**. Stop before mass autofix, broad import deletion, or build-system replacement. |
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
