# Codebase modularization: persistence-first structure proposal

**Status:** all four modularization steps are complete: the responsibility map,
project/application persistence and storage extraction, corrected frontend
workspace extraction, and the justified-only assessment of the remaining large
modules. The original frontend receipt extracted media and draft autosave while
retaining mixed workspace ownership; the accepted correction is recorded below
and in its amended verification receipt. This document remains a historical
map and records change triggers rather than an aesthetic refactor backlog.
It follows the accepted API modularization checkpoint at
`f9487508239bf14f5f8de8b255456c97a3e3b933` and the already-approved breaking
project-folder storage destination.  It does not reopen the cutover decision,
add a selectable storage mode, or schedule frontend work concurrently.

## Delivery checklist

- [x] Responsibility map accepted.
- [x] Project-folder storage package conversion completed.
- [x] Persistence package conversion complete (schema/codec/database/transaction,
  authoring, generation, project media, and application control have explicit
  capability owners; the retained runtime surface is compatibility composition).
- [x] Frontend modularization correction: the original Step 3 receipt did not
  complete workspace ownership. The accepted correction gives route,
  project-session, authoring, run, profile, and directory state explicit
  owners and passed an attended source-ownership review.
- [x] Justified assessment of other large modules completed; line count alone
  is not implementation authority. See the [Step 4 assessment](#step-4-justified-only-assessment-of-the-remaining-large-modules).

### Persistence checkpoint seams

This checkpoint deletes `persistence.py` and preserves the public
`plotloom.persistence` façade. Mapped rows now have schema owners; canonical
value conversion and `stable_hash` live in `codec.py`; engine/session setup is
in `database.py`; and the five named read/write/bootstrap/lifecycle/claim leases
are in `transactions.py`. `legacy_repository.py` intentionally retains the
public `SQLiteRepository` and `ProjectSQLiteRepository` facade while callers
still depend on it. The second slice moved project catalog/lifecycle and
authoring draft/canonical-stage/gate/approval bodies into named
`persistence/project` collaborators (about 8,012 lines remain). The third
slice moves the public generation lifecycle bodies into ten named collaborators:
frozen snapshots/run bootstrap, StagePlan creation, work-unit attempt evidence,
fragment reuse, aggregate seals, progress, exact repair scope, startup recovery,
atomic canonical output installation, and artifact/trace evidence. They use
only explicit repository session/query/codec helpers; the facade preserves
public signatures and project-bound admission checks. No service locator,
dynamic forwarding, or separate generation monolith was introduced.

`legacy_repository.py` remains a compatibility composition boundary. The
original generation-extraction receipt overstated its completion: repair,
recovery, immutable evidence, and atomic install policy still lived in the
facade. The ownership correction recorded in
`docs/verification/2026-09-13-persistence-generation-ownership-correction.md`
moves that policy into the named generation owners and adds a no-bounce-back
regression. The final media/control correction replaces the former policy
monoliths with focused `project/media_*.py` owners for managed assets,
intent/admission, selection/preview, reference decisions/proposals, same-person
review, image preparation/delivery, video currentness/lifecycle, and legacy
media tasks. `application/profile_*.py` likewise separates value conversion,
bootstrap, catalog, admission, and the atomic settings projection; the Wan
pilot ledger remains in `application/accounting.py`. `project/media.py` is the
72-line typed construction root for fixed media owners, and
`application/profiles.py` is a 179-line explicit compatibility composition
layer. `legacy_repository.py` remains the one documented retained runtime
facade and delegates directly to those typed owners.
ADR 0042 records the director-accepted correction. No schema,
public API, migration, runtime cutover, storage ownership, provider spend, or
frontend decision changes in this persistence-complete phase.

## Audit checkpoint

- **Verified baseline:** clean `f948750` worktree before this audit.
- **Observable outcome:** an implementable ownership map and a bounded first
  persistence/storage extraction that makes the project-folder destination
  easier to finish without changing behavior.
- **Scope:** first-party runtime and frontend inventory, with targeted reading
  of `persistence.py`, `project_storage.py`, their callers, storage tests, the
  storage plan, and ADRs 0040/0041.  No source, test, configuration, provider,
  data, frontend, or generated-asset files were changed.
- **Stopping condition:** commit this proposal and stop for director review.
  The first source slice must receive a new bounded assignment; it must not be
  combined with a cutover, snapshot/restore, video/draft feature work, or a
  frontend rewrite.

The line-count guideline is a signal about cohesion, not permission to fragment
dense code mechanically.  Targets below are roughly 400 lines where practical;
an expected module over 500 lines must be justified by one cohesive contract or
split before it grows further.

## What the audit found

`src/plotloom/persistence.py` is 10,120 lines.  It currently combines four
distinct layers:

| Current range | Current responsibility | Why the boundary matters |
| --- | --- | --- |
| 180-1,021 | SQLAlchemy `Base`, 47 mapped rows, table-set selection, and small value conversion | Mapping/schema ownership is mixed with behavior and with two physical database destinations. |
| 1,110-2,054 | engine/session setup; SQLite lock/transaction policies; project create/list/archive/duplicate/delete | The writer leases are correctness contracts, while project catalog/lifecycle is not application-control storage. |
| 2,055-4,365 | managed stills, visual intent/selection, video, character references, image-job and review persistence | These are portable project facts, but video pilot ledger/accounting is installation-owned. |
| 4,371-9,863 | authoring drafts, canonical heads/revisions/gates/approvals, snapshots, runs/attempts/work units/repair/recovery/artifacts, media tasks, profiles/settings | This interleaves authoring and generation transactions with installation-wide provider selection and settings. |
| 10,010-10,120 | `ProjectSQLiteRepository`, a subclass that filters schema tables and rejects or rebinding checks for application behavior | It proves the desired ownership split, but inheritance leaves the project repository coupled to the full repository's surface and schema file. |

The boundary is already explicit in the table set.  `PROJECT_TEXT_PIPELINE_TABLE_NAMES`
identifies portable project tables: canonical project/revisions/heads/drafts,
gate and approval records, run/attempt/plan/work-unit/repair/topology evidence,
artifacts and media tasks, and still/image/review/manual-handoff facts.
Provider settings, text provider profiles and selection, plus the video-pilot
ledger/events, stay application-owned.  The approved storage plan adds global
accounting and dispatch leases to that application side.  A future split must
make that distinction structural, not reimplement it in an ever-growing
allowlist.

`src/plotloom/project_storage.py` is 822 lines and has four cohesive concerns
that happen to share a file:

| Current area | Responsibility that should own it | Evidence in the current implementation |
| --- | --- | --- |
| format, errors, JSON/path helpers, manifest and owned-artifact values | project-folder format and confinement contract | immutable format-5 `project.json`, normalized relative paths, secret rejection and SHA-256 identity |
| `ApplicationStore` | installation control data only | public reusable profiles/selection and global accounting in `application.sqlite3` |
| `_OwnedArtifactStore`/`ProjectArtifactStore` | project-owned immutable byte addressing | confined `assets/<prefix>/<hash>`, no symlinks/hard links, hash and size verification |
| `ProjectStore`, registry and `ProjectFolderStorage` | manifest discovery, bound project handle, and explicit composition | one `project.sqlite3` per folder, handle close, project-ID binding, non-overlapping roots |

That file is therefore a strong first extraction candidate.  In contrast,
`project_generation_storage.py` is only 97 lines and is a focused direct
pipeline composition; it should remain intact while the storage interfaces
under it are clarified.

The retained runtime still constructs `SQLiteRepository` in `runtime.py`; API,
pipeline, jobs, media/video services, conformance, and tests import that type
directly.  This is why a first move cannot silently replace it with a broad
`Repository` service locator or change the runtime's recovery ownership.

## Final responsibility-oriented package shape

This is the desired destination after independently accepted slices, not a
request for one large move.  `persistence.py` would be replaced by the
`persistence/` package only when the source file can be deleted in the same
slice; a module and package of that name must never coexist.

```text
src/plotloom/
├── persistence/
│   ├── __init__.py                 # deliberate public imports only
│   ├── codec.py                    # canonical JSON/value conversion; stable_hash
│   ├── database.py                 # engine/session construction and close
│   ├── transactions.py             # named read/write/bootstrap/lifecycle/claim leases
│   ├── schema/
│   │   ├── base.py                 # Base and metadata registration
│   │   ├── project_authoring.py    # project, revisions, heads, drafts, gates, approvals
│   │   ├── project_generation.py   # runs, attempts, plans, units, seals, repair, topology
│   │   ├── project_media.py        # artifacts, media, still/image/review/handoff tables
│   │   └── application_control.py  # profiles, selection, pilot ledger/accounting
│   ├── project/
│   │   ├── authoring.py            # brief/stage/draft/gate/approval operations
│   │   ├── generation.py           # snapshots, runs, work units, repair, recovery facts
│   │   ├── media.py                # managed still/image/video project facts
│   │   ├── workflow.py             # named cross-capability transactions only
│   │   └── repository.py           # project-bound composition and admission boundary
│   ├── application/
│   │   ├── profiles.py             # reusable public profiles and selection
│   │   └── accounting.py           # pilot ledger, dispatch/accounting reservations
│   └── legacy_repository.py        # temporary retained-runtime composition; delete on cutover
├── project_storage/
│   ├── __init__.py                 # intentional public storage exports
│   ├── format.py                   # manifest, format errors and confinement primitives
│   ├── artifacts.py                # project-owned immutable byte store
│   ├── application_store.py        # small sqlite application-control store
│   ├── project_handle.py           # bound project repository and project-local adapters
│   ├── registry.py                 # manifest-derived directory registry
│   └── composition.py              # ProjectFolderStorage; named collaborators only
└── project_generation_storage.py   # retained focused pipeline composition
```

The listed modules are targets, not a mandate to create empty wrapper files.
For example, `project/workflow.py` exists only for operations that demonstrably
need authoring and generation changes in one SQL transaction; it is not a
catch-all orchestration layer.  Similarly, `persistence/__init__.py` remains a
small public boundary, not a forwarding copy of every internal class.

### Dependency directions

```text
domain / validation / generation contracts
                 ↑
persistence/schema <- persistence/{codec,database,transactions}
                 ↑
persistence/project/{authoring,generation,media} <- project/workflow
                 ↑                                      ↑
project_storage/{format,artifacts,project_handle,registry} <- project_storage/composition
                 ↑                                      ↑
        runtime/API/jobs/pipeline (named repository or opened ProjectStore)

persistence/application/* -> application-store control data
    (never imports project folders or canonical project content)
```

Schema modules may depend on `domain` value types only for explicitly mapped
columns.  Repository capabilities may depend on their own mapped rows,
transactions, pure codec, domain and validation contracts; they must not import
API routers, runtime composition, browser code, provider credentials, or
filesystem paths.  `project_storage` may construct a project-bound repository
and own paths/handles, but must not become a second canonical business-service
layer.  `runtime`, API registrars and runners receive the exact capability they
need rather than an untyped bag.

## Durable contracts that the split must preserve

### Public import, schema and compatibility surface

- Preserve `plotloom.SQLiteRepository` and `plotloom.persistence.SQLiteRepository`
  while the retained runtime exists.  Preserve `Base`, `stable_hash`, and the
  currently imported ORM row types at their current import paths during the
  mechanical package conversion; tests may later stop reaching into row types,
  but that is a separate test-ownership change.
- Preserve `ProjectSQLiteRepository`, `ProjectFolderStorage`, `ProjectStore`,
  `ProjectDirectoryRegistry`, project-storage errors, format-5 manifest fields,
  and `ProjectArtifactStore` imports until a specific caller migration removes
  each one.  Keep the API factories and their direct-storage limits from ADR
  0041 unchanged.
- Keep every existing table name, column, constraint, foreign key, index,
  SQLAlchemy `Base` metadata registration, full-vs-project table selection, and
  Alembic environment import stable during behavior-preserving extraction.
  No migration, format bump, project-folder importer, data rewrite, or legacy
  compatibility mode belongs in it.
- Keep `stable_hash` canonical JSON behavior and all persisted content hashes,
  frozen profile/version/adapter snapshots, run/attempt/artifact identities,
  idempotency fingerprints and repair-scope hashes byte-for-byte compatible.

### Transaction, locking, recovery and secret ownership

- Move the existing named transaction contracts intact: ordinary write,
  bootstrap `BEGIN IMMEDIATE` lease for idempotency bindings, lifecycle
  `BEGIN IMMEDIATE` lease for lifecycle/project-owned writes, and work-unit
  claim `BEGIN IMMEDIATE` lease.  Their distinct contention translations and
  busy-timeout behavior are observable correctness semantics, not helpers to
  flatten into one context manager.
- A capability never opens a second transaction while another capability's
  operation is active.  The public operation that spans capabilities owns one
  named transaction in `project/workflow.py`, passes its private session only
  to the participating capability internals, and commits/rolls back once.
  Examples are canonical draft consumption plus stage/brief mutation, run
  output installation plus head updates, and a lifecycle transition plus its
  busy guard.  API and runner code never receives a session.
- Project-folder discovery remains manifest-validated, folder-name-independent,
  and bound to exactly one project ID.  Each route opens and closes the exact
  handle; run evidence cannot cross a project home.  Outputs and application
  roots remain real, non-overlapping directories.
- Relative owned bytes retain SHA-256 path identity, regular-file/no-symlink/no-
  hard-link checks, project-local deduplication only, size/hash verification,
  and no absolute `file://` persistence.  Runs and manual exchange packages
  remain below their owning project folder.
- Provider profiles/selection, paid accounting, dispatch leases and credentials
  remain installation/session/server-owned.  Project databases freeze only
  public operation snapshots.  No secret may enter manifests, project rows,
  artifacts, snapshots, profile settings, errors, traces or logs.
- Existing startup recovery remains owned by retained runtime composition until
  the cutover has an explicit replacement.  Project restore/open must not replay
  a provider request; missing credentials or unknown remote submission remains
  explicit recovery state.  Do not use a persistence split to smuggle in
  snapshot/restore, close/quiescence, or video behavior.

## Bounded first code refactor: storage format and project-bound repository seam

**Start only after director approval.**  This slice is deliberately narrower
than the full package tree but materially separates the two ownership roots.

| Slice item | Exact work | Explicit non-goal |
| --- | --- | --- |
| Split folder storage | Replace `project_storage.py` with `project_storage/format.py`, `artifacts.py`, `application_store.py`, `project_handle.py`, `registry.py`, `composition.py`, and a small intentional export module.  Move code as-is by the four audited concerns. | No behavior/schema/format change; no snapshot, restore, close, draft, image, video, provider or UI feature. |
| Defer project-bound persistence | Keep `PROJECT_TEXT_PIPELINE_TABLE_NAMES` and `ProjectSQLiteRepository` in `persistence.py`.  Moving the subclass separately from its base would require cyclic or forwarding scaffolding. | Do not replace the retained `SQLiteRepository`, reclassify table ownership, or turn it into mixins. |
| Name physical ownership | Make `ProjectStore` import only the project-bound repository; make application control storage a named collaborator of `ProjectFolderStorage`.  Preserve existing `ProjectFolderStorage` public construction and behavior. | Do not wire project folders into `build_runtime_app` or introduce old/new selection. |
| Delete moved sources | Delete `project_storage.py`; leave `persistence.py` unchanged in this slice.  The package export file can re-export documented public symbols only. | Do not delete legacy project paths, runtime data, or database tables. |

Expected size targets for this first slice are format 120-180, artifacts
150-220, application store 180-260, projects 250-360, composition 80-140, and
project-bound repository 130-190 lines.  If the focused `projects.py` exceeds
500 lines after the move, split its registry from its bound handle before
continuing.  The unchanged 10k-line `persistence.py` is not declared healthy by
this slice; it has only lost the folder-specific responsibility that belongs at
the storage boundary.

This is a behavior-preserving extraction, not the already-approved project-folder
runtime cutover.  The latter still must replace callers deliberately, remove
obsolete project persistence paths as each caller changes, stop writers, archive
the old working sets, and avoid a legacy importer or dual-write/selection mode
as stated in the storage plan and ADR 0040.

### Characterization before and after the first slice

Before moving code, record baseline comparisons for the following rather than
assuming an import-only change is safe:

1. Manifest creation/discovery/open rejects symlinks, traversal, duplicate IDs,
   missing/invalid manifests, foreign project IDs, corrupt databases and
   overlapping roots; project folders reopen after process restart.
2. Project byte persistence retains the same relative URI, content hash/size,
   no-link confinement and cross-project isolation; application profile data
   rejects secret-shaped configuration and does not appear in a project DB.
3. Direct text execution retains successful, failed, cancelled, quarantined and
   outcome-unknown evidence without partial canonical heads; exact repair and
   admitted public profile snapshots retain their current behavior.
4. Existing direct-storage authoring and still/image browser contract tests keep
   project handle close discipline, draft CAS receipt/error mapping, image
   package confinement and API import/factory behavior.
5. A focused import matrix covers `plotloom`, `plotloom.persistence`,
   `plotloom.project_storage`, `plotloom.api`, Alembic metadata import, retained
   runtime import, and installed-package imports after a wheel is built.

Run focused `tests/test_project_storage.py`,
`tests/test_project_storage_image_workflow.py`, and
`tests/backend_core/test_api_modularization_contract.py` while extracting, plus
the nearest repository/pipeline tests touched by an import change.  On a stable
candidate, run the required locked Python suite, frontend test/typecheck/build,
static freshness check, wheel build plus installed-wheel smoke, and the existing
browser evidence for normal workbench and the already-exercised direct-storage
path.  A first slice without frontend edits must leave
`src/plotloom/static/` unchanged; frontend compilation is a release gate, not a
reason to regenerate assets.  Preserve a failing import or lock result as
evidence—do not retain duplicate code or add broad exception handling to force
the move through.

## Subsequent backend slices and stopping point

After the first slice stabilizes, take one capability at a time, with exact
caller migration and deletion in each assignment:

1. **Schema/database/transactions extraction.**  Move mapping rows, pure codec
   and transaction infrastructure into their final files without changing table
   names or lease behavior.  Keep the legacy full repository as the one
   retained-runtime composition while callers are still on it.
2. **Project authoring capability.**  Extract project lifecycle, canonical
   authoring, draft, gate and approval operations, retaining their named
   cross-capability transactions.  Do not change client/API schemas.
3. **Project generation capability.**  Extract snapshots, plans, attempts,
   work-unit/repair/seal/commit and recovery facts as one lifecycle contract;
   do not split correction semantics before the relevant generation ownership
   ADR review.
4. **Project media and application control separately.**  Move still/image/
   review facts independently from provider profiles/settings and pilot/global
   accounting.  Video dispatch and accounting require an explicit cross-store
   reservation/reconciliation contract at cutover, not a fictional distributed
   transaction.
5. **Cutover readiness stop.**  Stop modularization once project and
   application capability boundaries, transactions and tests make the
   project-folder runtime replacement a direct, bounded delivery.  Shift to
   completing the approved project-folder workflow, portable recovery and
   cutover; do not keep extracting merely to reach an aesthetic line count.

Each slice needs a concise ADR amendment only if it changes public imports,
schema/persistence, transaction semantics, runtime/recovery, or the approved
storage destination.  A pure file move with preserved contracts needs a focused
receipt, not a new architecture process.

## Frontend modularization correction (Step 3)

The separately authorized frontend phase established the media and durable
authoring-draft roots without a wire-contract, transport-policy, server-action,
or visual redesign. Its original claim that `WorkspaceApp.tsx` was an
intentional remaining composition root was rejected: the same file retained
route/epoch/AbortController navigation, project loading, directory lifecycle,
profile session keys, canonical saves, and run polling.

The correction starts from the preserved `932cb09` baseline and makes the
compatibility entrypoint small while giving already-extracted boundaries named
owners under `app/workspace/`: protocol and route facts in `contracts.ts`,
profile catalog/session-key state in `useTextProviderProfiles.ts`, directory
cursor lifetime in `useProjectDirectory.ts`, run poll/trace currentness in
`useRunSession.ts`, and inspector/dialog views in `WorkspaceViews.tsx`.
The correction now assigns substantial project-session work to typed owners:
`useWorkspaceProjectLoader.ts` owns abortable aggregate loading,
`useProjectAuthoringPersistence.ts` owns canonical create/save and draft CAS,
`useWorkspaceNavigation.ts` owns URL/history and dirty-draft routing,
`useAuthoringDraftRecovery.ts` owns recovery/discard prompts, and
`useProjectLifecycle.ts` owns directory lifecycle actions. The accepted final
correction adds `useWorkspaceSession.ts` as the single canonical snapshot and
route-epoch owner, moves blank/demo initialization to
`useProjectInitialization.ts`, and completes trace navigation plus draft
conflict/recovery ownership in their dedicated hooks. `WorkspaceController.tsx`
is now a 248-line composition/view root. One attended Terra review found and
closed the explicit, implicit, and abandoned trace-selection races; the full
frontend, locked Python, static, browser, and wheel gates then passed.

`api.ts` and `types.ts` remain intentionally stable shared wire boundaries in
this phase: no backend capability required a transport-shape move, so creating
parallel type copies would have added compatibility risk without clarifying an
owner. The full module tree and verification receipt are recorded in
`docs/verification/2026-09-14-frontend-workbench-modularization.md`.

## Frontend phase: original planning record

No frontend code belongs in the first backend slice.  The audited seams are
clear enough to plan next: `App.tsx` (1,633 lines) owns application shell,
routing/query state, project loading, drafts, profiles, directory actions and
pipeline polling; `managed-media.tsx` (2,209 lines) owns workbench fetching,
still/image/reference/proposal/review mutations, local form state and preview
playback.  `api.ts` (573) is transport/client admission, while `types.ts`
(1,099) is a public client contract mixed with feature families.

The completed, separately approved frontend phase established:

```text
frontend/src/
├── app/                 # route parsing, workspace shell and project session state
├── features/authoring/  # page-local editor state and draft integration
├── features/media/      # workbench shell
│   ├── assets/          # imports, visual intent, selection and preview
│   ├── image-jobs/      # package/export/refresh/candidate lifecycle
│   └── references/      # character/reference/proposal/review forms
├── api/                 # transport grouped by backend capability
└── contracts/           # feature-owned client types; shared protocol types only
```

Start with the managed-media workbench because it has the clearest internal
feature seams, keep its API methods and browser behavior stable, and extract
page-local components/hooks rather than one global state container.  Route and
workspace ownership in `App.tsx` is a separate slice.  Do not split `types.ts`
by alphabetical shape; move a type with its owning feature and retain a small
shared wire-contract module.  Any frontend change rebuilds and verifies
`src/plotloom/static/`; it must not be coupled to the persistence move.

## Step 4: justified-only assessment of the remaining large modules

Completed against `6acada8`, with the current source line counts below. This is
not a claim that every file is small or permanently final. It answers whether a
further extraction is necessary to complete the approved storage milestone or
to repair a demonstrated ownership conflict. It is not: no source change is
authorized by this assessment. The detailed evidence and historical-receipt
supersession pointers are in
[`docs/verification/2026-09-14-modularization-step-4-assessment.md`](../verification/2026-09-14-modularization-step-4-assessment.md).

| Candidate (current lines) | Actual responsibility and dependency boundary | Decision and precise future trigger |
| --- | --- | --- |
| `generation/work_units.py` (4,772) | Pure, provider/repository/pipeline-free model-response contract: it compiles a frozen `GenerationWorkUnit`, binds untrusted fragments to trusted IDs, and owns versioned schema, semantic-repair facts, and their postconditions. It depends on domain/validation plus focused generation contracts, planning, prompt, timing, topology, and schema modules; `work_unit_pipeline.py` consumes its public boundary. | **Leave intact now.** Its apparent subtopics are one author/model/trusted-code contract; splitting only for size risks severing the invariant that model output never owns plan hashes, unit IDs, or input hashes. Reassess only when a versioned prompt/schema/correction policy deliberately changes ownership and can be moved with an explicit compatibility/import contract and targeted contract regressions. |
| `work_unit_pipeline.py` (1,719) | `DurableWorkUnitRunner` is the one runtime orchestration owner for attempts, correction admission, provider execution, sealed aggregates, cancellation, and exact repair. It couples frozen generation plans and work-unit contracts to repository lifecycle transactions and secret leases. | **Leave intact now.** Its ordering is a correctness boundary, not a generic helper collection, and it is not an obstacle to folder storage. Reassess only when the project-handle cutover changes the runner/repository transaction contract, or a new lifecycle proves a separable operation while preserving one durable attempt/seal ordering. |
| `domain.py` (1,550) and `validation.py` (1,484) | `domain.py` is the imported canonical Pydantic/value vocabulary for authoring, runs, profiles, traces, secrecy and stage order. `validation.py` applies graph, coverage, stage-payload, continuity and gate rules over that shared vocabulary, including timing/topology helpers. They are used across API, persistence, generation, runners and tests. | **Leave intact now.** Moving by noun would widen public import and schema compatibility risk and can create domain/validator cycles. Reassess only for an approved versioned public-schema boundary or a demonstrated validator dependency cycle; first specify exports, serialization compatibility, and migration/regression coverage. |
| `alpha_acceptance.py` (1,351) and `conformance.py` (655) | These are separate secret-free qualification runners. Conformance runs disposable profile samples through the production pipeline and emits narrow receipts; Alpha additionally pins checkout provenance, copies a stable source DB pair, builds blinded review packs, and gates external-review receipts. Both deliberately construct isolated repositories and close their resources. | **Leave intact now.** Similar setup does not establish shared ownership: Alpha's provenance/blinding rules are not Conformance's repeatable release gate. Reassess only if a proven shared disposable-run lifecycle diverges in cleanup, admission, or receipt secrecy; extract that single tested primitive without merging qualification policy or review-pack publication. |
| `generation/planning.py` (1,063) and `generation/story_graph_topology.py` (1,110) | These are focused generation contracts: planning freezes work units/dependencies; topology produces the bounded graph/content-fill contract consumed by `work_units.py`, pipeline and conformance receipts. | **Leave intact now.** No storage caller owns their policy, and no mixed side effect was found. Reassess only when a new generation stage or topology version needs independently versioned public contract data; preserve plan/topology hashes and existing consumers. |
| `media.py` (665), `image_job_exchange.py` (714), and `pipeline.py` (738) | `media.py` owns typed image/video adapter specifications, gateway secret boundary, normalized status and prompt compilation. `image_job_exchange.py` owns confined same-host package/delivery validation and has no browser-path authority. `pipeline.py` owns text provider/secret resolution and the production `PipelineEngine` composition. | **Leave intact now.** Each has a recognizable transport/exchange/runtime boundary, and none blocks close, snapshot, restore, accounting, or cutover. Reassess only when adding a provider, exchange protocol, or runtime engine causes a concrete conflict between its adapter/transport and contract owner; extract that exact side-effect-free or protocol seam with its safety tests. |
| Frontend `api.ts` (573), `types.ts` (1,099), and authoring pages (`SceneBeatsPage.tsx` 1,276; `StoryBiblePage.tsx` 1,032) | `api.ts` is the single typed `/api/v2` transport and session-key boundary; `types.ts` is the shared server-wire vocabulary imported by workspace, pages and feature packages. The two large pages compose editor-local cards, focus/deletion/migration disclosure, and their page-specific form state over helpers already extracted to `scene-beats-editor.ts` and related UI modules. | **Leave intact now.** Splitting shared types by alphabetical shape or endpoint methods without a backend/wire ownership move would create parallel contracts; splitting page components merely for line count risks breaking local focus and structural-confirmation behavior. Reassess only with an endpoint schema change that gives a feature exclusive transport/types, or a demonstrated page-state race/accessibility defect with a bounded component-owner remedy. |

The retained compatibility facade in `persistence/legacy_repository.py` remains
the one real modularization exception. Its purpose and deletion trigger are
already explicit: retained-runtime callers still import `SQLiteRepository`, so
it remains direct typed composition until the separately approved runtime
cutover. Step 4 does not reopen the accepted persistence ownership correction
or frontend session/cutover decisions.

### Project repository retirement prerequisite correction

The project-folder repository now has its own project-only composition and does
not import, subclass, instantiate, or eagerly initialize the retained facade.
Project-folder authoring, generation, image, and direct-video callers use their
named project owners. This is the prerequisite for runtime cutover, not the
deletion of the retained 1.5k-line facade: retained runtime/API callers still
own that compatibility surface and must be replaced deliberately before it can
be removed.

### Completion boundary and next product priority

This completes **modularization only**. It does not complete the project-folder
storage feature, runtime cutover, portable recovery, or production-video work.
The next product delivery remains the existing approved storage plan, in order:
finish close/quiescence and snapshot/restore, preserve video dispatch and
installation-owned accounting through their explicit recovery/reconciliation
contract, then perform the one-way runtime cutover and closeout. No new
architecture is proposed here.

## Compact working lessons

- Compare an observable baseline before moving a module: import topology,
  schema/table set, transaction result and browser path are better evidence
  than a clean diff alone.
- Give every resulting module a named domain owner.  If its name cannot state
  its transaction and data authority, it is probably a new monolith in a
  directory.
- Keep audit-first as a gate for cross-cutting moves.  It prevents a large
  refactor from quietly changing the already-set project-folder destination or
  displacing the work needed to finish it.

## Audit verification and handoff

This documentation-only audit runs no suites, builds or browser jobs.  Before
commit, verify document links/references and `git diff --check`.  The director
reviews this proposal before authorizing any implementation, acceptance, merge
or push.
