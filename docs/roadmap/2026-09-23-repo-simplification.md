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

- [x] Reconcile and implement the approved Batch B slice against its then-current `main` baseline (`f4e4e47`): the static mount, shared E2E fixture, two API F401 findings, their module-local callers, and the current wheel prompt inventory were checked before changing their narrow verification contracts. Focused browser, API, lint, build and installed-wheel checks are recorded below.
- [ ] Before any Batch C removal, repeat the same current-source consumer, contract-owner, behavior, regression and shipped-artifact checks for each individual symbol. The original `f867eb0` spot checks remain preliminary for C.

The [finding/disposition register](2026-09-23-simplification-dispositions.md)
records the current-main documentation reconciliation and preserves amended or
withdrawn findings. It does **not** complete the per-symbol B/C implementation
gate above; those tracks still require their own current-source checks.

## Approved small tracks

| Track | Preliminary finding disposition | Primary dependency and owner | Next bounded action / stop |
| --- | --- | --- | --- |
| **A — documentation authority** | **Completed locally at `cb6fa27`.** The [ADR entrypoint](../adr/README.md), scoped 0004/0014/0042 and H3 notes, `0040` full-slug links, live H3 operator guidance, and [disposition register](2026-09-23-simplification-dispositions.md) reconcile the bounded claims while retaining history. | Documentation owner; independent read-only review and link/diff checks passed. | No schema, ID, persistence, or runtime change. Further ADR claims remain individual `Park`/`Test` leads, not an open Batch A rewrite. |
| **B — narrow verification tooling** | **Implemented and locally verified.** See the [source-backed assessment](2026-09-23-simplification-b-assessment.md), [ADR 0081](../adr/0081-narrow-source-static-and-api-lint-checks.md), and [developer verification commands](../development.md#checked-static-bundle-browser-smoke). The opt-in Playwright fixture serves checked static assets through FastAPI with no Vite; the positive save/reload and missing-JS/CSS counterfactuals pass. Ruff 0.16.8 is pinned, the two confirmed unused API imports are removed, and the API-only F401 check passes. The installed-wheel smoke also passes after its expected prompt inventory was aligned with the already-shipped `production_bridge_intent` template. | Engineering completed the narrow implementation; the director still owns any automatic CI trigger change. | CI remains `workflow_dispatch` only. No push/PR triggers, whole-source lint, autofix, formatter, ESLint, build-system change or Batch C work is included. The source-static browser check does not claim installed-wheel browser execution; the existing wheel smoke remains packaging/startup evidence. |
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
