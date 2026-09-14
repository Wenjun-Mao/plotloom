# Modularization Step 4 assessment receipt

## Outcome

The fourth approved modularization step is complete as a docs-only,
justified-only assessment. At accepted frontend baseline `6acada8`, targeted
source/caller reading found no mixed-responsibility flaw that blocks the
approved project-folder storage milestones. No source, test, frontend/static,
configuration, provider, data, or plugin file changed; no new refactor is
proposed solely because a module is long.

This closes the four-step modularization effort, not the storage feature,
runtime cutover, portable recovery, or production-video delivery.

## Accepted history and real remaining exceptions

| Step | Accepted revision / outcome | Current status |
| --- | --- | --- |
| Responsibility map | `f9487508239bf14f5f8de8b255456c97a3e3b933` API-modularization checkpoint and the approved project-folder destination | retained historical map; no second inventory was created |
| Project/application persistence and storage | `187794c249af49a5bb7ab1bbc509c666d00c411d` persistence media/control completion, following the package and authoring/generation extractions | `persistence.py` and `project_storage.py` monoliths are retired; named capability owners are in place |
| Frontend workspace | `6acada83bd1ffc6ae267bf5d0c1e5d3224b3131f` corrected workspace-session ownership | `App.tsx` and `managed-media.tsx` are two-line compatibility entrypoints; `WorkspaceController.tsx` is the composition/view root |
| Other large modules | this receipt and the amended modularization roadmap | assessed only; no mechanical extraction justified |

The one material modularization exception is
`src/plotloom/persistence/legacy_repository.py`: it is the explicit typed
compatibility composition boundary for retained-runtime callers of
`SQLiteRepository`. It is not a reopened state-ownership decision. Its removal
belongs to the separately approved one-way runtime cutover, after callers have
moved; it must not be replaced by a service locator or forwarding monolith.

Historical receipts are preserved rather than rewritten. The roadmap's
frontend-correction section and
`2026-09-14-frontend-workbench-modularization.md` supersede the original broad
Step-3 workspace conclusion; the roadmap's persistence checkpoint and
`2026-09-13-persistence-generation-ownership-correction.md` supersede the
earlier generation-ownership overstatement.

## Targeted source assessment

| Candidate | Evidence read | Assessment and future trigger |
| --- | --- | --- |
| `src/plotloom/generation/work_units.py` (4,772 lines) | Module contract/imports; `compile_work_unit_request`, trusted binding, semantic-repair schema/fact/postcondition functions; callers in `src/plotloom/work_unit_pipeline.py` and generation contract tests | It is intentionally provider-, repository-, and pipeline-free: one frozen work-unit prompt/response ownership boundary. Prompt compilation, schema restriction, trusted ID binding and repair evidence must agree, so splitting by repair/topic is unjustified. Reassess only for an approved versioned prompt/schema/correction ownership change with explicit compatibility and contract regressions. |
| `src/plotloom/work_unit_pipeline.py` (1,719) | `DurableWorkUnitRunner.execute` and imports of repository, secrets, planning, correction, and work-unit contracts | It owns one durable lifecycle ordering from frozen plan through attempts, corrections, aggregates, cancellation and exact repair. A file split now would cross transaction and seal ordering without a demonstrated conflict. Reassess only if project-handle cutover changes that transaction contract, or a new lifecycle yields a tested separable operation. |
| `src/plotloom/domain.py` (1,550) and `src/plotloom/validation.py` (1,484) | Public models/enums/stage helpers, secret checks, graph/coverage/stage/continuity/gate validation and imports across API, persistence, generation and tests | The public canonical vocabulary and its cross-stage validation remain deliberately co-evolved, despite separate files. There is no cycle or storage obstacle. Reassess only for an approved versioned public schema or demonstrated dependency cycle, after naming exports and serialization compatibility. |
| `src/plotloom/alpha_acceptance.py` (1,351) and `src/plotloom/conformance.py` (655) | Disposable-repository execution, source/profile handling, secret-free receipt construction, Alpha review-pack/provenance code, and their tests | They are distinct qualification policies: Alpha owns checkout provenance and blinded external-review packs; Conformance owns repeatable profile qualification. Their shared use of the production pipeline is intentional, not duplicated policy. Reassess only if a demonstrated cleanup/admission/receipt-secrecy divergence warrants one narrow shared disposable-run primitive. |
| `src/plotloom/generation/planning.py` (1,063) and `src/plotloom/generation/story_graph_topology.py` (1,110) | Current sizes, direct consumers in work-unit compilation/pipeline/conformance and their named plan/topology contracts | Each owns one frozen generation-policy contract. No filesystem, runtime-cutover, or storage responsibility is mixed in. Reassess only when a new stage/topology version requires independently versioned public data; preserve plan/topology hashes. |
| `src/plotloom/media.py` (665), `src/plotloom/image_job_exchange.py` (714), `src/plotloom/pipeline.py` (738) | Adapter/gateway/compiler sections; exchange confinement/no-follow validation; text engine/provider/secret composition | The three modules respectively own media transport, same-host image exchange, and text-run runtime composition. No source evidence shows a conflict with close, snapshots/restore, video accounting, or cutover. Reassess only when a concrete provider/exchange/engine addition crosses one of those boundaries. |
| `frontend/src/api.ts` (573), `frontend/src/types.ts` (1,099), `frontend/src/pages/SceneBeatsPage.tsx` (1,276), `frontend/src/pages/StoryBiblePage.tsx` (1,032) | Shared typed API client/type imports throughout workspace/features/pages; page-local editor, focus, deletion/migration and inspector components | API and types are stable shared wire boundaries, while the large pages keep tightly coupled local editor/interaction behavior and already consume extracted helpers. Reassess only for an endpoint schema change giving a feature exclusive wire ownership, or a demonstrated page accessibility/state defect with a bounded owner change. |

## Preserved contracts

- Prompt/schema/repair ownership remains author → model → trusted binder as
  documented; model output still cannot own plan hashes, work-unit IDs, or input
  hashes.
- Durable attempt, correction, seal, cancellation, recovery and repository
  transaction ordering remain unchanged.
- Canonical domain/Pydantic serialization, validation, public frontend wire
  types, API client session-key handling, and retained `SQLiteRepository`
  import compatibility remain unchanged.
- The extraction boundary remains intact: production code does not import or
  read Narrative Forge V1 runtime paths or data.

## Verification for this docs-only change

- Read-only source/caller and current line-count checks covered the candidates
  listed above, including conformance and remaining large authoring pages.
- Path/reference validation confirmed each cited source file and the approved
  `docs/roadmap/project-folder-storage-plan.md` close, snapshot/restore, video,
  accounting and cutover sequence.
- `git diff --check` was run before commit.

No Python, frontend, static, wheel, or browser suite was rerun: this change
does not alter executable code or generated assets. The final reported product
gates remain those recorded for `6acada8` in
`2026-09-14-frontend-workbench-modularization.md` (frontend, locked Python,
static, browser, and wheel) and for the accepted persistence receipts; this
receipt does **not** represent a fresh full-suite result.

## Next product priority

Follow the existing project-folder storage plan without new architecture:
complete close/quiescence and snapshot/restore, preserve video dispatch plus
installation-owned accounting through their explicit recovery/reconciliation
contract, then perform the one-way runtime cutover and closeout. Modularization
does not authorize those product changes by itself.
