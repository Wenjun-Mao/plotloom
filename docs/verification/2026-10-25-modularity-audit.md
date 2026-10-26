# File size and modularity audit — 2026-10-25

## Outcome and authority

**Audit complete; the audit itself authorized no implementation.** The owner requested architectural review using ~400 lines as a target and 500 as a review threshold, then rejected “extract when next changed” as an adequate disposition. Every oversized candidate below has an explicit **EXTRACT**, **RETAIN** or **RETIRE** recommendation, reason and, where work is proposed, a named finite batch. These are proposed work items, not promises that an unspecified future edit will address them.


Implementation update: the owner approved G1/R1–R3 with Go on 2026-10-25.
Those source boundaries are now implemented, independently reviewed and locally
qualified by composite evidence and activated with preservation checks in the [delivery plan](../roadmap/2026-10-25-generation-contracts-and-retirements.md).
The census and line references below remain the audit baseline.
G3–G5 are now selected in the combined plan below; all other extraction batches
remain pending.

The owner approved the subsequent [G2 plan](../roadmap/2026-10-25-g2-work-unit-ownership.md)
with “Go ahead with Relay direct”. Its completed delivery owns canonical binding,
schema/presence, stage semantics/adapters and repair derivation/source assertions
outside the 489-line compiler. Exact extraction parity, early runtime and persisted snapshot/restore proofs,
independent stable/security review and composite full-local qualification pass.
The original full/browser failures and targeted corrections remain explicit;
manager activation, exact preservation/readback and single recovery refresh are
complete. The plan records the sole narrow continuity evidence persistence
false-positive correction and the 571-line cohesive timing-owner rationale.
The audit census below remains historical; no other batch is activated.

The owner subsequently requested planning and then implementing G3–G5 together.
Their [combined reviewed plan](../roadmap/2026-10-25-g3-g5-generation-ownership.md)
defines serial internal checkpoints and integrated review/qualification/activation,
preservation and recovery under one combined request. Their source candidate now
has actual planning/context/topology, registry/selection/schema-family and durable
runtime/evidence/exchange/compiler owners, with direct consumer imports. The small
native project and real-adapter loopback recovery proofs pass; integrated independent
review, final qualification and activation remain pending. The 589-line unit owner
retains one execution-local allocation/recovery/rejection/correction/candidate loop;
its already-separated provider/evidence/compiler/source boundaries make another
state-distributing split unwarranted. The plan records exact parity and failures.
G3–G5 are implemented at source, not yet delivered. All unrelated
batches remain unselected.

Baseline: clean retained `main` at `cfc55173df4418bc0d929ed93f2992daf99f03fb`, in `/Users/wjmao/.codex/worktrees/b30f/plotloom`. Three read-only reviews covered generation, backend/services and frontend; the manager independently reconciled the census, inspected material evidence and reviewed scripts, other tests and documentation code. This report and its roadmap pointer are the only intended changes.

**120 files exceed 400 lines; 42 reach the 500-line review threshold.** Recommendations: **52 EXTRACT, 65 RETAIN, 3 RETIRE**. An EXTRACT recommendation can move only a shared helper or a subset of responsibilities; it does not imply dividing every test case or meeting an exact resulting line count. RETIRE can remove one obsolete execution branch while retaining live neutral contracts.

The highest-value first implementation batch is **G1: leaf generation response/repair contracts**, because it removes an observed dependency cycle before moving compiler behavior. Decide R1–R3 as explicit retired-contract removals; they need not delay G1. Frontend F2 is a useful independent next track, with one source writer at a time.

## Method, coverage and limits

Tracked-file census used physical lines, including blanks/comments, for `.py, .ts, .tsx, .js, .jsx, .mjs, .cjs, .css, .html, .sh, .bash, .zsh`. “Above 400” means >400; review threshold means >=500. Standard-library Python AST inspection provided function spans and import/class structure without importing project code. Searches covered actual source callers, tests, entry points, current ADR promises and selected smaller coupled modules. This is a structural audit, not proof of runtime behavior or an exhaustive semantic reading of every file.

| Census group | Files | >400 | >=500 |
|---|---:|---:|---:|
| Core Python (`src/plotloom`) | 456 | 38 | 19 |
| Frontend source/config | 285 | 13 | 4 |
| Service source/config | 137 | 4 | 0 |
| Scripts | 74 | 5 | 0 |
| Tests and test support | 764 | 51 | 12 |
| Auxiliary documentation/prototype code | 34 | 9 | 7 |
| **Total** | **1,750** | **120** | **42** |

Test classification includes root/frontend test trees, service `tests/` trees and files named `test_*`. The auxiliary group includes authored documentation HTML; it is separated from executable runtime concerns. No models/schema exemption was applied: declarative contracts received individual review.

Excluded generated outputs: seven tracked files under `src/plotloom/static/`; the three architecture readers and their three visual contact sheets; and `docs/storyboard-handbook/index.html`. Generation ownership is explicit in [Vite configuration](../../frontend/vite.config.ts), [architecture guide](../architecture/README.md#supporting-files) and [handbook builder](../storyboard-handbook/build.mjs). Locks, JSON data, dependencies, ignored local artifacts and external submodule contents are not handwritten source in this census.

Every >400 file appears exactly once in the inventory. Selected smaller clusters were reviewed for cycles, hidden ownership and unnecessary forwarding; findings below include concrete sub-400 changes. Low line count does not certify cohesion. No tests/builds, live database/settings inspections, provider calls, activation, CI or pushes were performed for the audit.

## Prioritized architectural findings

### P1 — Compiler ownership creates a real repair-model dependency cycle

[work_units.py](../../src/plotloom/generation/work_units.py) is 4,772 lines: response models (:156), repair contracts (:243–1029), adapters (:1058/:1462), frozen prompt provenance (:1196), compilation (:1593), canonical binding (:2025), repair derivation/source validation (:2341–3964) and stage validation (:3967/:4239). These are independently meaningful authorities with different consumers.

The [correction-directive module](../../src/plotloom/generation/correction_directives.py) explicitly documents avoiding compiler model imports to prevent a cycle (:1–9), then checks concrete model names (:514/:739). Correction schema/postconditions import the compiler-owned facts. In the other direction, complete storyboard response DTOs live in [storyboard_presence_repair.py](../../src/plotloom/generation/storyboard_presence_repair.py):70–123, alongside one repair family.

**Suggestion: G1 then G2.** Establish leaf response/repair contracts and frozen prompt records, update actual consumers, then separate canonical binding, stage validators and repair families. Keep fact derivation and its source revalidation together. Retire the central compatibility-export role rather than hiding new modules behind the old compiler. This improves dependency direction and makes authority inspectable; smaller files are a consequence.

### P1 — Durable execution mixes independently testable responsibilities

[work_unit_pipeline.py](../../src/plotloom/work_unit_pipeline.py) combines stage sequencing (:177), unit execution (:367–920), correction packet compilation (:970–1399) and durable evidence IO (:1401–1594). The provider exchange (:539–740) has a critical single boundary: lease → persisted dispatch → provider call → delivery-certainty classification/redaction → persisted response.

**Suggestion: G5 after G1–G4.** Extract the correction compiler, evidence codec and complete provider exchange with explicit collaborators. Keep allocation/recovery/correction iteration under one unit owner, stage ordering/sealing under one stage owner, and `finally: release_run` (:331) visible. Do not add runner mixins or callback bags. The benefit is testable evidence/dispatch contracts without fragmenting no-replay safety.

### P1 — Shared domain and frontend contracts obscure actual ownership

[domain.py](../../src/plotloom/domain.py) combines stage/run, provider, public evidence and security/value validation. [provider_profiles.py](../../src/plotloom/provider_profiles.py):24 imports its URL validator, while `domain.py:1215` imports profile models locally to avoid a cycle. This is an observed dependency problem, not a hypothetical future growth concern.

[frontend types.ts](../../frontend/src/types.ts) combines story, media, projects/drafts, execution/review, providers and source review across 1,367 lines. [api.ts](../../frontend/src/api.ts) combines the corresponding endpoint groups in 822 lines.

**Suggestion: B1 and F4, followed by F5.** Give public validation and backend model families leaf owners; use seven frontend contract leaves and six domain endpoint clients. Update consumers directly. Keep a single [ApiTransport](../../frontend/src/api-transport.ts):10–50 instance so all clients share read admission, credential headers, fetch binding and errors. Do not introduce independent per-client read gates or a large forwarding facade. Keep consumed-draft header parsing with canonical/draft endpoints.

### P2 — Editor presentation and orchestration can be separated cleanly

[SceneBeatsPage.tsx](../../frontend/src/pages/SceneBeatsPage.tsx) has 1,267 lines and existing typed boundaries: continuity editor (:117), structural confirmations (:279/:363), dialogue/beat cards (:406/:571), page owner (:753) and scene inspector (:1000). [StoryboardPage](../../frontend/src/pages/StoryboardPage.tsx):452–484 packs a dense selected-shot form into orchestration. Playback and H3 production admission also share [video-pilot.tsx](../../frontend/src/video-pilot.tsx).

**Suggestion: F2/F3.** Extract complete typed presentation components, including playback identity/autoplay/stale-ended handling as one unit. Keep each page's aggregate draft, selection, route/issue focus, migration/deletion and confirmation owner intact. For Scene Beats, use continuity primitives, structural confirmations, BeatCard with private CueCard, and SceneInspector under `pages/scene-beats/`. No extra state-hook decomposition is warranted.

### P2 — Small files can still conceal a large implicit object

The [Codex Exec supervisor](../../services/creator_workbench/codex_exec_supervisor.py):35 has **15 direct mixin bases, 20 including inherited mixins**. Its process owner is only 476 lines, but `_execute` spans :43–435 and relies on shared implicit state. A line cap alone would miss this architecture.

**Suggestion: B6.** First extract terminal completion inspection (:304–363) and receipt/output values (:364–434) using immutable explicit inputs. Keep supervisor mutation/publication and the lock across final cancellation/auth checks, spawn and identity commit (:114–234). Do not add another mixin or rewrite the entire supervisor at once. Source identity is frozen by [codex_exec_profile.py](../../src/plotloom/codex_exec_profile.py):121–142/:253–255: changed implementation needs a new qualified profile identity, never a rewrite of old attempt evidence.

### P2 — Duplicate fixture and protocol ownership is already demonstrable

[Cast-reference E2E helpers](../../frontend/e2e/cast-reference-studies.spec.ts):577–733 duplicate [existing shared fixtures](../../frontend/e2e/fixtures/cast-reference.ts):38–168/:216–229. `copyProposalFromBrowser` (:663) repeats the shared send request/button interaction (:110).

Five protocols are duplicated in [api/models.py](../../src/plotloom/api/models.py):71–101 and [api/protocols.py](../../src/plotloom/api/protocols.py):16–46: RunScheduler, MediaScheduler, MediaPromptCompiler, TextProviderResolver and TextProfileSecretSource. Keep one owner for the three live text/run protocols; R2 removes both unused media copies.

Collected Python tests also serve as fixture libraries:
- Alpha review builders → `test_alpha_qualification_contracts.py:14`.
- Runtime settings/fake H3 → `test_runtime_capabilities.py:10` and `test_runtime_declared_text_preset.py:11`.
- Cast context/delivery → `test_review_seam_currentness.py:20–21`.
- Recovery raster → pool/schema upgrade tests (:69/:132).
- Image delivery helpers → `test_image_source_lineage.py:8`, although they already originate in `project_folder_image_delivery_fixtures.py`.

**Suggestion: F1, B2 and T1.** Consolidate actual shared owners, redirect existing helper imports where possible, and move only genuinely reused setup into non-collected support modules. Preserve fixture scope/lifetime, assertions and exact native case union; update module ownership with moved tests. No new fixture framework is needed.

### P3 — Documentation code has separate extraction opportunities

The offline Prompt Pipeline Lab controller (807 lines) mixes pure teaching-model construction with DOM behavior. Its CSS (1,984 lines) and handbook CSS (1,910 lines) mix page primitives, educational components and responsive/print rules.

**Suggestion: D1/D2 after runtime priorities.** Split by those real responsibilities, preserving cascade order and existing EPUB/mobile-PDF owners. The lab explicitly supports direct `file://` opening: use ordinary local scripts with an explicit shared model namespace, preserving frozen teaching outputs. Do not introduce a server, ESM-fetch dependency, build framework or reinterpret the frozen V1 research as current Plotloom behavior. The authored chapters receive individual RETAIN exceptions below.

## Retired execution contracts requiring owner review

These are **recommendations to remove current source contracts**, not permission inferred from “unused” code. Repository searches cannot establish unknown external Python users. I recommend accepting the intentional breaking removals under the repository's current-contract policy; no current internal execution consumer was found.

| Decision | Suggestion and reason | Exact limits |
|---|---|---|
| **R1: legacy stage-level text repair** | Remove the legacy `pipeline.py:434–764` bridge, exported `GenerationOrchestrator`/in-memory quarantine engine and their direct tests/prompt consumers; reject new scope-less stage repair. Current API, dispatcher, alpha and conformance use durable pipeline/exact-child execution instead. Supersede [ADR 0015](../adr/0015-exact-work-unit-repair.md):109's callable legacy promise. | Preserve current exact repair/reuse, historical trace decoding, schema-version refusal, interrupted-legacy recovery classification and all UNKNOWN/no-replay guards. Move live broker/provider resolution first or in the same bounded change. |
| **R2: generic raw-media execution** | Remove `src/plotloom/media.py` compiler/adapters and `tests/test_media.py`, unused `MediaTaskRequest` and both media protocol copies. Current source has only test imports; raw task execution was retired by [ADR 0048](../adr/0048-retire-shared-repository-runtime.md):39–44 and constrained by [ADR 0031](../adr/0031-bounded-wan-video-production.md)/[ADR 0012](../adr/0012-approved-storyboards-and-production-units.md). | Preserve current image/H3 production and any row codecs/recovery still read by supported project storage. Retire obsolete execution promises, not snapshot/restore or live managed media. |
| **R3: Atlas/Wan execution fallback** | Remove `atlas_wan_transport.py`, Atlas adapter/capability in `video_provider.py:309–319/:402–574` and the default in `video_jobs.py:44`; require an explicit adapter. Current runtime selects H3 and `config.py:188–201` rejects `PLOTLOOM_ENABLE_WAN_P2`. Supersede [ADR 0034](../adr/0034-provider-neutral-video-adapters-and-local-h3.md):34–37/:66–67's old execution/test-retention requirement. | Remove nine Atlas-specific test functions (33 statically expanded cases) from `tests/backend_core/test_atlas_wan_transport.py:19–226`; preserve/relocate its four diagnostic-allowlist cases (:229–240). Neutral `WanDispatchDiagnostic`/`WanDispatchError` are live H3 contracts despite their names. Preserve frozen Wan readback/integrity and dispatch accounting. Remove the obsolete toggle from the H3 manual (:254), where even the string `false` is rejected. |

No live project deletion, ledger release, provider dispatch or data rewrite belongs in R1–R3. Preserving still-consumed decoding/safety contracts has present functional value; this is not a proposal to keep audit-only history. Existing historical records need no new archive.

## Complete >400 inventory

Paths are relative to the repository; links point to the audited source. All recommendations are **proposed**. Batch identifiers below map to finite work in the next section. RETAIN is an affirmative architectural decision, not deferred extraction. A new responsibility or materially changed dependency surface invalidates its rationale.

### Generation runtime (10)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [src/plotloom/generation/work_units.py](../../src/plotloom/generation/work_units.py) | 4,772 | **EXTRACT** · G1/G2 | Leaf response/repair and frozen-prompt contracts; canonical binding; stage validators; repair-family derivation and source assertions. Compiler currently owns models used by its own dependencies. |
| [src/plotloom/work_unit_pipeline.py](../../src/plotloom/work_unit_pipeline.py) | 1,799 | **EXTRACT** · G5 | Correction compiler, durable provider exchange and evidence codec; retain stage/unit execution, cancellation, ordered sealing and run release as explicit owners. |
| [src/plotloom/generation/planning.py](../../src/plotloom/generation/planning.py) | 1,110 | **EXTRACT** · G3 | Immutable contracts/hashes, enqueue planning, stage planning and selector-scoped context; preserve sibling order and route-only filtering. |
| [src/plotloom/generation/story_graph_topology.py](../../src/plotloom/generation/story_graph_topology.py) | 1,096 | **EXTRACT** · G3 | Separate deterministic topology search from untrusted content-fill schema/binding; keep feasibility and materialization together. |
| [src/plotloom/generation/correction_directives.py](../../src/plotloom/generation/correction_directives.py) | 861 | **EXTRACT** · G4 | Versioned registry versus executable selection/evidence projection; consume G1 leaf fact types instead of concrete model-name checks. |
| [src/plotloom/pipeline.py](../../src/plotloom/pipeline.py) | 764 | **EXTRACT** · G5/R1 | Move live RunSecretBroker and provider resolution to their runtime owner; retire the unused stage-level engine bridge through R1. |
| [src/plotloom/generation/correction_schema.py](../../src/plotloom/generation/correction_schema.py) | 661 | **EXTRACT** · G4 | Graph/join, continuity and cue/timing overlay builders with deterministic assembly, conflict checks and base-schema nonmutation. |
| `src/plotloom/generation/orchestration.py` (retired; [ADR 0220](../adr/0220-generation-contract-leaves-and-retired-execution.md)) | 552 | **RETIRE** · R1 | No current internal production caller; retire its exported legacy engine contract explicitly. If the owner retains that API, its single attempt/quarantine lifecycle justifies 552 lines. |
| [src/plotloom/generation/storyboard_timing_repair.py](../../src/plotloom/generation/storyboard_timing_repair.py) | 527 | **RETAIN** | 527-line exception: replacement-plan validation/hash and deterministic construction prove the same timing authority; no second lifecycle owner. |
| [src/plotloom/generation/aggregation.py](../../src/plotloom/generation/aggregation.py) | 426 | **RETAIN** | Exact ordered manifest, merge, cross-unit references, size and canonical parity jointly determine one seal gate. |

### Other core runtime (28)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [src/plotloom/domain.py](../../src/plotloom/domain.py) | 1,228 | **EXTRACT** · B1 | Stage/run, provider/snapshot and public evidence projections have distinct consumers; move URL/security validation to a leaf to break provider_profiles' return dependency. |
| [src/plotloom/alpha_acceptance.py](../../src/plotloom/alpha_acceptance.py) | 1,195 | **EXTRACT** · B3 | Separate sample execution, blind artifact publication, receipt assembly and independent review/gates; share only deterministic metrics with conformance. |
| [src/plotloom/api/project_folder.py](../../src/plotloom/api/project_folder.py) | 830 | **EXTRACT** · B2 | Separate HTTP error mapping, lifecycle and canonical/draft routes; keep read-open proof scope and per-request lifetime together. |
| `src/plotloom/media.py` (retired; [ADR 0220](../adr/0220-generation-contract-leaves-and-retired-execution.md)) | 665 | **RETIRE** · R2 | Obsolete generic raw-media compiler/adapters have test-only imports and no production execution route; remove retired execution and its tests, retaining current row decoding/recovery. |
| [src/plotloom/conformance.py](../../src/plotloom/conformance.py) | 622 | **EXTRACT** · B3 | Use one pure metrics owner shared with alpha acceptance; retain separate profiles, receipts, thresholds and qualification lifecycles. |
| [src/plotloom/image_job_exchange.py](../../src/plotloom/image_job_exchange.py) | 588 | **EXTRACT** · B4 | Confined descriptor/filesystem operations and pure manifest assertions are separate from exchange orchestration; callers should consume the confined owner directly. |
| [src/plotloom/video_provider.py](../../src/plotloom/video_provider.py) | 574 | **RETIRE** · R3 | Retire Atlas adapter/capability and default selection; keep neutral live dispatch diagnostics/errors and frozen data interpretation. |
| [src/plotloom/project_storage/application_store.py](../../src/plotloom/project_storage/application_store.py) | 567 | **EXTRACT** · B5 | Run routing/frozen-profile ledger and table registration have a bounded store owner; profile deletion checks must remain in the same write transaction. |
| [src/plotloom/validation_storyboard.py](../../src/plotloom/validation_storyboard.py) | 540 | **EXTRACT** · B1 | Extract pure dialogue and continuity validators with explicit inputs; retain ordered gate aggregation, hashes and ID observation. |
| [src/plotloom/canonical_schema.py](../../src/plotloom/canonical_schema.py) | 505 | **RETAIN** | 505-line exception: strict composed canonical wire schema; Bible, graph, scene/beat and shot/timing references are one validation contract, not separate lifecycle owners. |
| [src/plotloom/video_backends/minimax_h3/adapter.py](../../src/plotloom/video_backends/minimax_h3/adapter.py) | 492 | **EXTRACT** · B5 | Catalogue declarations belong with the existing backend catalogue; retain request compilation and response validation in adapter. |
| [src/plotloom/persistence/project/cast.py](../../src/plotloom/persistence/project/cast.py) | 487 | **RETAIN** | Accepted identity preparation, admission, acceptance/reopen/cancel and consumer projections share the same source binding. |
| [src/plotloom/specialist_settings.py](../../src/plotloom/specialist_settings.py) | 483 | **EXTRACT** · B4 | Executable/environment/host client boundary is separate from registry locking, frozen dispatch identity and UNKNOWN settlement. |
| [src/plotloom/persistence/project/generation_recovery.py](../../src/plotloom/persistence/project/generation_recovery.py) | 471 | **RETAIN** | Ordered no-replay recovery classification runs under one write transaction; splitting branches would obscure conservative terminal treatment. |
| [src/plotloom/project_storage/registry.py](../../src/plotloom/project_storage/registry.py) | 470 | **RETAIN** | Create/open/duplicate/delete share confined project identity and lease lifetime. |
| [src/plotloom/api/project_folder_image_jobs.py](../../src/plotloom/api/project_folder_image_jobs.py) | 463 | **EXTRACT** · B2 | Character-reference endpoints and ordinary image-job endpoints have distinct package/admission owners; share stateless projections. |
| [src/plotloom/autopilot_text_controller.py](../../src/plotloom/autopilot_text_controller.py) | 461 | **RETAIN** | Stopped/active/late checkpoint reconciliation shares one controller lifetime; independent hooks would scatter response authority. |
| [src/plotloom/persistence/schema/project_media.py](../../src/plotloom/persistence/schema/project_media.py) | 453 | **EXTRACT** · B5 | Reference-specific tables/imported appearance form a cohesive schema owner; preserve exact SQL, foreign keys, indexes and registration order. |
| [src/plotloom/creative_handoff_exchange.py](../../src/plotloom/creative_handoff_exchange.py) | 448 | **EXTRACT** · B4 | Package publication versus frozen pin checks; remove package-mixin imports back into subclass helpers/constants via a leaf package owner. |
| [src/plotloom/persistence/project/generation_lifecycle.py](../../src/plotloom/persistence/project/generation_lifecycle.py) | 429 | **RETAIN** | Canonical install, cancellation and commit share one transaction/lifecycle authority. |
| [src/plotloom/api/contracts.py](../../src/plotloom/api/contracts.py) | 427 | **EXTRACT** · B1/B2/R2 | Move provider request contracts to their leaf owner, canonicalize duplicated live protocols, and remove unused raw-media request/protocol declarations with R2. |
| [src/plotloom/project_storage/project_handle.py](../../src/plotloom/project_storage/project_handle.py) | 419 | **RETAIN** | One bound project home, repository, artifacts and read/write lease lifetime including close/read-open. |
| [src/plotloom/api/text_admission.py](../../src/plotloom/api/text_admission.py) | 418 | **RETAIN** | Ephemeral readiness revision, secret lease and admission checks form one authoritative operation. |
| [src/plotloom/persistence/project/media_art_reference_proposals.py](../../src/plotloom/persistence/project/media_art_reference_proposals.py) | 417 | **RETAIN** | One exploratory subject-study proposal lifecycle with common source/currentness semantics. |
| [src/plotloom/project_storage/project_video.py](../../src/plotloom/project_storage/project_video.py) | 417 | **RETAIN** | Cross-database reservation, claim and claim-event ordering is one conservative dispatch boundary. |
| [src/plotloom/persistence/project/repository.py](../../src/plotloom/persistence/project/repository.py) | 415 | **RETAIN** | Explicit composition of repository capabilities and lease; extracting wiring would hide dependencies or introduce a service locator. |
| [src/plotloom/persistence/project/media_video_segments.py](../../src/plotloom/persistence/project/media_video_segments.py) | 407 | **RETAIN** | Revision reopening and selection rules jointly preserve the selected sibling; one selection authority. |
| [src/plotloom/provider_profiles.py](../../src/plotloom/provider_profiles.py) | 407 | **RETAIN** | One exact versioned frozen provider/hash contract; repair the domain dependency through B1 rather than split each schema version. |

### Frontend runtime (13)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [frontend/src/types.ts](../../frontend/src/types.ts) | 1,367 | **EXTRACT** · F4 | Seven contract leaves: story/stage, media/video, image jobs/references, projects/drafts, execution/review, providers and source review. Direct consumer imports; no central re-export barrel. |
| [frontend/src/pages/SceneBeatsPage.tsx](../../frontend/src/pages/SceneBeatsPage.tsx) | 1,267 | **EXTRACT** · F2 | Typed continuity editor, structural confirmations, BeatCard/private CueCard and SceneInspector; retain one plan, selection, draft and confirmation owner. |
| [frontend/src/api.ts](../../frontend/src/api.ts) | 822 | **EXTRACT** · F5 | Six domain endpoint clients sharing the same ApiTransport/read-admission instance; direct consumer and mock updates, no large delegating facade. |
| [frontend/src/features/media/ManagedMediaWorkbench.tsx](../../frontend/src/features/media/ManagedMediaWorkbench.tsx) | 507 | **RETAIN** | 507-line exception: composition of existing data/selection/assets/jobs/reference owners with common busy/error/readiness context. Further extraction forwards the same large wiring interface. |
| [frontend/src/pages/StoryboardPage.tsx](../../frontend/src/pages/StoryboardPage.tsx) | 499 | **EXTRACT** · F3 | Move selected-shot inspector form; retain aggregate changes, route/issue focus, migration/deletion and approval/confirmation ownership. |
| [frontend/src/video-pilot.tsx](../../frontend/src/video-pilot.tsx) | 492 | **EXTRACT** · F3 | Ordered playback with identity/autoplay/stale-ended state; pure route selection/projection separately. Retain H3 request/currentness admission. |
| [frontend/src/features/media/keyframes/KeyframeAndPreviewPanel.tsx](../../frontend/src/features/media/keyframes/KeyframeAndPreviewPanel.tsx) | 479 | **EXTRACT** · F3 | Complete StillPreviewPanel including subset/create/history/private player; intent drafts and compatibility review stay with their existing owner. |
| [frontend/src/scene-beats-editor.ts](../../frontend/src/scene-beats-editor.ts) | 474 | **RETAIN** | One pure scene→beat→cue edit algebra; parent migration, ordering, deletion disclosure and application must agree. |
| [frontend/src/app/workspace/useProjectAuthoringPersistence.ts](../../frontend/src/app/workspace/useProjectAuthoringPersistence.ts) | 467 | **RETAIN** | One save generation and exact acknowledgment/retirement authority across brief/stage writes, conflict recovery and receipt-required discard. |
| [frontend/src/storyboard-editor.ts](../../frontend/src/storyboard-editor.ts) | 460 | **RETAIN** | Shot/cue scheduling, beat coverage, audio and deletion/migration enforce shared storyboard relationships. |
| [frontend/src/pages/StoryBiblePage.tsx](../../frontend/src/pages/StoryBiblePage.tsx) | 445 | **RETAIN** | One Bible aggregate draft, selection, referential deletion and issue focus; specialized entity forms already have separate owners. |
| [frontend/src/app/workspace/useWorkspaceSession.ts](../../frontend/src/app/workspace/useWorkspaceSession.ts) | 422 | **RETAIN** | One route epoch/canonical snapshot owner for navigation invalidation, load acceptance and project creation transitions. |
| [frontend/src/app/workspace/WorkspaceController.tsx](../../frontend/src/app/workspace/WorkspaceController.tsx) | 416 | **RETAIN** | Composition binds single quiescence/journal/review/branch/session owners; another forwarding hook or shell hides these dependencies. |

### Service runtime (4)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [services/creator_workbench/codex_exec_supervisor_process.py](../../services/creator_workbench/codex_exec_supervisor_process.py) | 476 | **EXTRACT** · B6 | Terminal evidence inspection and receipt/output values become explicit collaborators; keep lock-protected cancellation/auth → spawn → identity commit under supervisor. |
| [services/minimax_h3_gateway/src/plotloom_h3_gateway/media.py](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/media.py) | 474 | **RETAIN** | Owned output paths, purge eligibility and integration-file lifetime form one filesystem authority. |
| [services/minimax_h3_gateway/src/plotloom_h3_gateway/gateway.py](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/gateway.py) | 425 | **EXTRACT** · B7 | Qwen request/dispatch coordination becomes an explicit collaborator; Gateway retains the single shared H3/Qwen lane claim. |
| [services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/static/dashboard.css](../../services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/static/dashboard.css) | 404 | **RETAIN** | One dashboard palette/layout/queue/detail view and responsive behavior; no separate product surface requiring another style owner. |

### Generation tests (11)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [tests/generation/test_m12a_contracts.py](../../tests/generation/test_m12a_contracts.py) | 804 | **EXTRACT** · G1/G2 | Replace milestone grouping with scene/dialogue, storyboard audio/ID repair and entity vocabulary/presence owners; share builders once. |
| [tests/generation/test_correction_schema.py](../../tests/generation/test_correction_schema.py) | 661 | **EXTRACT** · G4 | Align graph/join, continuity and cue/timing tests with their production overlay owners; non-collected shared fixtures. |
| [tests/generation/test_story_graph_topology.py](../../tests/generation/test_story_graph_topology.py) | 613 | **EXTRACT** · G2/G3 | Move repair provenance and compiler integration to their actual owners; retain planner/hash/binding assertions. |
| [tests/generation/test_planning_and_aggregation.py](../../tests/generation/test_planning_and_aggregation.py) | 580 | **EXTRACT** · G3 | Separate planning/context identity from manifest/merge/seal acceptance; shared canonical builders remain explicit. |
| [tests/generation/test_work_unit_scene_facts.py](../../tests/generation/test_work_unit_scene_facts.py) | 487 | **EXTRACT** · G2 | Scene Beats cue/budget authority differs from Storyboard timing-plan provenance and mutation rules. |
| [tests/generation/test_correction_directives.py](../../tests/generation/test_correction_directives.py) | 476 | **RETAIN** | One selection/projection policy: registry order, executable/deferred authority, prompt-local indexes and hashes interact across fact families. |
| [tests/generation/test_continuity_repair.py](../../tests/generation/test_continuity_repair.py) | 448 | **RETAIN** | One sequence/source-binding contract across stages; direction, canonical outer authority and tamper refusal share the same oracle. |
| [tests/generation/test_scene_fragment_contracts.py](../../tests/generation/test_scene_fragment_contracts.py) | 433 | **RETAIN** | One ingress contract joining closed response shape, local IDs, frozen join/direct-edge authority, schema and stale-plan refusal. |
| [tests/generation/test_correction_postconditions.py](../../tests/generation/test_correction_postconditions.py) | 418 | **RETAIN** | One provider-independent exact-authority acceptance API; small family cases already use bounded common fixtures. |
| [tests/generation/test_join_state_values.py](../../tests/generation/test_join_state_values.py) | 407 | **RETAIN** | One incoming-edge value contract from finite-JSON admission and hash through frozen Scene Beats planning. |
| [tests/generation/test_work_unit_prompts.py](../../tests/generation/test_work_unit_prompts.py) | 406 | **RETAIN** | One compiler provenance contract covering nulls, scoped secrecy, incoming facts, JSON identity and complete correction schedules. |

### Frontend tests and browser journeys (9)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [frontend/e2e/cast-reference-studies.spec.ts](../../frontend/e2e/cast-reference-studies.spec.ts) | 733 | **EXTRACT** · F1 | Consolidate duplicated builders/controls into existing cast-reference fixture; move held-session/read/import races to one session-ownership spec. |
| [frontend/e2e/image-jobs.spec.ts](../../frontend/e2e/image-jobs.spec.ts) | 548 | **EXTRACT** · F1 | Separate stale-intent and tampered-manifest failures from the 527-line journey using shared approved/reference-ready setup; retain original→refinement acceptance. |
| [frontend/tests/character-reference-gallery.test.ts](../../frontend/tests/character-reference-gallery.test.ts) | 531 | **RETAIN** | 531-line exception: one abort-ignoring deferred harness tests response/subject/pending-File ownership across session races; splitting duplicates private authority setup. |
| [frontend/tests/production-bridge-panel.test.ts](../../frontend/tests/production-bridge-panel.test.ts) | 491 | **RETAIN** | One proposal/canonical-handoff UI contract across acknowledged server state, unsaved intent, installation receipt and replacement target; fixtures already extracted. |
| [frontend/tests/graph-workbench-provider.test.ts](../../frontend/tests/graph-workbench-provider.test.ts) | 489 | **RETAIN** | One read/receipt/preview/Undo/live-selection authority with compact common harness; delayed responses exercise the same owner. |
| [frontend/e2e/art-review.spec.ts](../../frontend/e2e/art-review.spec.ts) | 453 | **EXTRACT** · F1 | Move F4 script acceptance/edit/restart journey to its script-review owner; retain art cases with existing art fixture. |
| [frontend/e2e/creator-workbench-operations.spec.ts](../../frontend/e2e/creator-workbench-operations.spec.ts) | 438 | **RETAIN** | Graph operations, Undo, capacity/reuse and unfinished selected input share one operation vocabulary and existing creator fixture. |
| [frontend/tests/recommended-workflow.test.ts](../../frontend/tests/recommended-workflow.test.ts) | 417 | **RETAIN** | One ordered recommendation policy across currentness, admission, drafts and media; stage guidance already has focused owners. |
| [frontend/e2e/creator-workbench-layout.spec.ts](../../frontend/e2e/creator-workbench-layout.spec.ts) | 414 | **EXTRACT** · F1 | Separate canonical read-only geometry from editable row/inspector layout; preserve distinct checked-static/native fixtures, viewport matrix and no-write assertions. |

### Service-local tests (4)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [services/creator_workbench/test_codex_exec_supervisor.py](../../services/creator_workbench/test_codex_exec_supervisor.py) | 642 | **EXTRACT** · B6 | Separate environment, terminal evidence and cancellation matrices with shared cleanup support; assertions and process-group lifetime remain intact. |
| [services/creator_workbench/test_bridge.py](../../services/creator_workbench/test_bridge.py) | 521 | **EXTRACT** · B6 | Exec-profile/readiness/control cases differ from queue/wake/auth cases; reuse existing service fixture support. |
| [services/creator_workbench/test_isolated.py](../../services/creator_workbench/test_isolated.py) | 469 | **RETAIN** | One isolated composition lifetime spanning private roots, shim/native identity, H3 startup and complete cleanup. |
| [services/qwen3_tts_voice_lab/tests/test_voice_lab.py](../../services/qwen3_tts_voice_lab/tests/test_voice_lab.py) | 449 | **EXTRACT** · B7 | Move reused fake engine/app/request setup out of a collected test; browser_server, multi_engine and take_dispatch tests currently import it. |

### Other Python tests and support (27)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [tests/test_v2_authoring_domain.py](../../tests/test_v2_authoring_domain.py) | 1,032 | **EXTRACT** · T2 | Split canonical schema/IDs/entity state, dialogue/timing gates, scene continuity, graph join/value and coverage owners; preserve cross-stage parity scenarios intact. |
| [tests/test_project_storage.py](../../tests/test_project_storage.py) | 861 | **EXTRACT** · T2 | Source/store isolation and recovery, draft CAS/receipt API, and operational lease/reopen tests have independent owners; retain process cleanup and transaction assertions. |
| [tests/test_production_project_folder_runtime.py](../../tests/test_production_project_folder_runtime.py) | 598 | **EXTRACT** · T1/T2 | Move runtime settings/fake-H3 support out of collected tests; separate lifecycle/admission integration from typed-H3 composition, preserving each complete journey. |
| [tests/test_production_bridge.py](../../tests/test_production_bridge.py) | 493 | **RETAIN** | One F5→canonical production projection/install authority covering exact source/CAS, atomic rollback, capacity and advisory policy; installable fixture already separate. |
| [tests/test_creator_branch_suggestions.py](../../tests/test_creator_branch_suggestions.py) | 491 | **RETAIN** | One branch propose/read/adopt/cancel/currentness contract with existing source and graph fixtures; stale/foreign/malformed cases exercise that same pipeline. |
| [tests/test_project_storage_exact_repair_regressions.py](../../tests/test_project_storage_exact_repair_regressions.py) | 487 | **RETAIN** | One exact-child source/sibling-binding lifecycle across stale/foreign/tamper/recovery/deletion order; shared setup is already local/support-owned. |
| [tests/test_project_storage_image_delivery_contracts.py](../../tests/test_project_storage_image_delivery_contracts.py) | 480 | **EXTRACT** · T1 | Retain delivery cases; redirect image-source-lineage imports to existing project_folder_image_delivery_fixtures instead of this collected test's reexports. |
| [tests/test_image_job_exchange_contracts.py](../../tests/test_image_job_exchange_contracts.py) | 475 | **RETAIN** | One immutable package/exchange contract across retained manifest hashes, frozen references, native task binding and host publication; shared fixtures are compact. |
| [tests/test_alpha_acceptance.py](../../tests/test_alpha_acceptance.py) | 473 | **EXTRACT** · B3/T1 | Execution/profile/provenance versus independent review manifests/gates; shared review builders currently imported by another collected test move to support. |
| [tests/test_codex_exec_contracts.py](../../tests/test_codex_exec_contracts.py) | 459 | **RETAIN** | Frozen profile and attempt snapshot binding are one execution contract; version/refusal/terminal-evidence matrices share that immutable identity. |
| [tests/test_codex_exec_delivery.py](../../tests/test_codex_exec_delivery.py) | 459 | **RETAIN** | One host-published delivery boundary with frozen assignment/profile, exact project receipt/inventory and source-path authority; receipt builder is local. |
| [tests/services/minimax_h3_gateway/test_app.py](../../tests/services/minimax_h3_gateway/test_app.py) | 451 | **RETAIN** | One public frozen-job integration contract: admitted request/catalogue → frozen workflow → FIFO/restart/output handling with shared controlled Comfy harness. |
| [tests/test_conformance.py](../../tests/test_conformance.py) | 447 | **EXTRACT** · B3 | Separate real four-stage runner/setup/failure contract from qualification receipt/shape/threshold/CLI contract, matching source owners. |
| [tests/test_project_storage_source_outline.py](../../tests/test_project_storage_source_outline.py) | 447 | **RETAIN** | One source/outline/section-map publication authority with stale, cancelled and foreign races; existing package/source fixtures are shared. |
| [tests/creative_delivery_fixtures.py](../../tests/creative_delivery_fixtures.py) | 446 | **RETAIN** | One reusable accepted source/cast/art/script chain with pinned context; stage wrappers share the same fixture lineage and actual consumers. |
| [tests/test_project_storage_image_identity_contracts.py](../../tests/test_project_storage_image_identity_contracts.py) | 444 | **RETAIN** | One 339-line temporal identity journey from authored subject through review to stale replacement; splitting steps would lose lineage oracle, helper setup already separate. |
| [tests/test_project_storage_recovery.py](../../tests/test_project_storage_recovery.py) | 441 | **EXTRACT** · T1 | Retain portable restore cases; move/reuse raster helper imported by schema/pool-upgrade tests through a non-collected fixture owner. |
| [tests/test_project_storage_art.py](../../tests/test_project_storage_art.py) | 436 | **RETAIN** | One art acceptance/reference/currentness lifecycle, including explicit CAS decisions and historical/stale observations; common creative fixtures already separate. |
| [tests/test_project_storage_video_disposal.py](../../tests/test_project_storage_video_disposal.py) | 433 | **RETAIN** | One owned blob disposal/refcount/selected-sibling/concurrent-candidate/restart authority; complete lifecycle cases are useful together. |
| [tests/test_project_storage_cast.py](../../tests/test_project_storage_cast.py) | 424 | **EXTRACT** · T1 | Retain cast cases together; move shared accepted context/delivery helpers imported by review-seam tests into a non-collected fixture owner. |
| [tests/test_project_storage_direct_generation_regressions.py](../../tests/test_project_storage_direct_generation_regressions.py) | 424 | **RETAIN** | Current direct durable pipeline dispatch/recovery boundary, including frozen provenance, atomic seal, restart and response reuse; not the retired stage engine. |
| [tests/test_production_bridge_intent.py](../../tests/test_production_bridge_intent.py) | 422 | **RETAIN** | One author/model intent contract across exact targets, save/reinfer, stale/late response, restart UNKNOWN and secret-free frozen evidence; shared fixtures already separate. |
| [tests/test_paid_outline_handoff.py](../../tests/test_paid_outline_handoff.py) | 415 | **RETAIN** | One finite capability/no-retry/acknowledgment-loss boundary; capsule setup is already separate, and current authority tests remain live. |
| [tests/test_extraction_contract.py](../../tests/test_extraction_contract.py) | 412 | **EXTRACT** · T2 | Installed wheel completeness/import-isolation probe versus static source-boundary/metadata hygiene; keep actual wheel builder with package probe. |
| [tests/test_project_storage_video_submission.py](../../tests/test_project_storage_video_submission.py) | 408 | **RETAIN** | Four complete frozen-H3 submission scenarios cover reviewed directions/restart, duration/geometry and explicit crop/currentness; shared protocol boundary. |
| [tests/test_project_storage_generation_contracts.py](../../tests/test_project_storage_generation_contracts.py) | 407 | **RETAIN** | One durable provider attempt/prompt/correction audit contract; frozen secret-free profiles, correction evidence and no-replay assertions agree. |
| [tests/test_codex_exec_telemetry.py](../../tests/test_codex_exec_telemetry.py) | 405 | **RETAIN** | One ordered event/reference/provenance parser boundary; shared raster and event harness tests literal tool-call evidence. |

### Scripts (5)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [scripts/testing/run_python_suite.py](../../scripts/testing/run_python_suite.py) | 440 | **RETAIN** | One child-process lifecycle including signals, completion proof and TERM/KILL cleanup; balancing/timing already separate. Long coordinator alone is not a split reason. |
| [scripts/testing/module_selection.py](../../scripts/testing/module_selection.py) | 428 | **RETAIN** | Validated exact module union, deterministic plan/commands and CLI adapter form one selection contract; moving command lists would obscure rather than isolate policy. |
| [scripts/verify.py](../../scripts/verify.py) | 423 | **RETAIN** | Verification tier/command policy is one composition owner; scheduling and module selection already have separate modules. |
| [scripts/testing/check_module_ownership.py](../../scripts/testing/check_module_ownership.py) | 413 | **RETAIN** | Manifest checks and three native collector parsers jointly prove one complete exact owner inventory; no separate parser product/owner. |
| [scripts/autopilot/handoff/node_helper.mjs](../../scripts/autopilot/handoff/node_helper.mjs) | 404 | **RETAIN** | One single-use handoff authority closes over physical roots, time, phase and process receipts; splitting closures broadens the hash/import surface. Actual current capsule/test consumers remain. |

### Authored auxiliary documentation code (9)

| File | Lines | Decision / batch | Reason or extraction boundary |
|---|---:|---|---|
| [docs/prompt-pipeline-lab/assets/lab.css](../../docs/prompt-pipeline-lab/assets/lab.css) | 1,984 | **EXTRACT** · D1 | Base/layout, pedagogical components and responsive/print styling; preserve cascade/import order and direct offline opening. |
| [docs/storyboard-handbook/assets/handbook.css](../../docs/storyboard-handbook/assets/handbook.css) | 1,910 | **EXTRACT** · D2 | Base typography/layout/TOC, reusable teaching components and responsive/print families; preserve cascade and existing separate EPUB/mobile-PDF owners. |
| [docs/prompt-pipeline-lab/assets/lab.js](../../docs/prompt-pipeline-lab/assets/lab.js) | 807 | **EXTRACT** · D1 | Pure frozen prompt/response/media teaching model versus DOM controls/rendering; ordinary local scripts with explicit namespace, no server/ESM requirement. |
| [docs/storyboard-handbook/src/chapters/02-moon-control-room.html](../../docs/storyboard-handbook/src/chapters/02-moon-control-room.html) | 799 | **RETAIN** | 799-line authored chapter exception: one worked control-room narrative; arbitrary fragments degrade reading and chapter navigation. |
| [docs/storyboard-handbook/src/chapters/04-narrative-forge-contracts.html](../../docs/storyboard-handbook/src/chapters/04-narrative-forge-contracts.html) | 708 | **RETAIN** | 708-line authored chapter exception: one frozen-source contract analysis with stable citations/anchors and chapter output identity. |
| [docs/storyboard-handbook/src/chapters/01-common-foundation.html](../../docs/storyboard-handbook/src/chapters/01-common-foundation.html) | 607 | **RETAIN** | 607-line authored chapter exception: one foundation narrative, anchors and publication unit; no inline executable controller. |
| [docs/storyboard-handbook/src/chapters/06-shuohao-storyboard.html](../../docs/storyboard-handbook/src/chapters/06-shuohao-storyboard.html) | 596 | **RETAIN** | 596-line authored chapter exception: one storyboard analysis, stable anchors and EPUB chapter identity; no second executable responsibility. |
| [docs/prompt-pipeline-lab/index.html](../../docs/prompt-pipeline-lab/index.html) | 485 | **RETAIN** | One semantic educational page; markup is content, controller/styles already separate. Splitting sections adds assembly machinery without an independent owner. |
| [docs/storyboard-handbook/src/chapters/05-shuohao-pipeline.html](../../docs/storyboard-handbook/src/chapters/05-shuohao-pipeline.html) | 413 | **RETAIN** | One pipeline-analysis chapter; source citations and sequential prose belong together rather than a new fragment build layer. |

## Proposed finite implementation batches

**G1/R1–R3 and G2 are complete, including independent review, composite local qualification and preservation-checked activation. All unselected batches are NOT STARTED and await implementation authorization.** The table is the actionable queue linked from the existing roadmap, not a new tracking system. Completing a batch requires its boundary, actual consumer updates and relevant assertion-preserving tests; merely creating new files does not complete it. Any rejection of an EXTRACT recommendation should be an explicit reviewed RETAIN decision with a reason, not “next time.”

### Recommended order and boundaries

G1/G2 are delivered. Next consider G3, then G4 before G5; B1 precedes backend contract consumers; F4 precedes F5. F1/F2 can be scheduled independently between generation batches. Lower-priority script/auxiliary work does not gate runtime progress. Use a single source writer; independent reviewers inspect stable checkpoints. Each row below is a bounded assignment, not permission to run all work concurrently.

| Batch | Deliverable and boundary | Proposed owner and relevant verification |
|---|---|---|
| **G1** | Leaf Scene Beats/Storyboard response DTOs, repair-fact contracts and frozen prompt records; remove compiler/model-name import workaround and relocate presence-repair DTOs. Direct imports, no central compatibility barrel. | Generation contracts. Correction directives/schema/postconditions, continuity, scene/storyboard models, authorized-null round trips, cold imports and schema/hash equality. |
| **G2** | Canonical fragment binder, stage validation and graph/join, continuity, dialogue, storyboard entity/audio repair-family owners; each derivation stays with source assertion. One stage/family per checkpoint. | Generation contracts. M12a successor suites, scene facts, fragments, exact source binding, ID/timing allocation and canonical aggregation parity. |
| **G3** | Planning contracts/hashes, enqueue/stage planning and scoped context; topology contracts/search versus content-fill binding. Keep bounded search/materialization together. | Shared-generation/graph with source-authoring consumer review. Route-only selection, sibling order, source option limits, deterministic topology/hash/IDs and seal parity. |
| **G4** | Versioned correction registry separated from authority selection/projection; graph/join, continuity and cue/timing schema builders with deterministic assembly. | Shared-generation. Registry ordering/uniqueness, conflict rejection, base nonmutation, nulls, executable-local indexes, deferred authority and stable projection hashes. |
| **G5** | Durable provider exchange, correction compiler and evidence codec with explicit inputs; stage/unit owners retain allocation, recovery, commit, seal and release. Extract live broker/provider resolver from pipeline. | Project lifecycle + generation/security review. Existing generation contracts, direct/exact repair, pending-sibling/recovery, secret/provider tests; durable response reuse, no duplicate call, known/unknown failure classification and ordered commits. |
| **B1** | Public URL/value validation leaf, provider/stage/run/public evidence model families; pure dialogue/continuity validators. Direct consumers, no domain barrel. | Backend contracts. Provider snapshots/hash versions, cold imports, public-value rejection and storyboard gate/issue order. |
| **B2** | HTTP lifecycle, error translation and canonical/draft route owners; character-reference versus ordinary image endpoints; one live protocol owner. | API/project lifecycle. Read-open proof/lifetime, HTTP status/errors, draft CAS/consumed receipts, image binding and before-send frozen authority. |
| **B3** | Acceptance execution, blind artifacts, external review and receipt owners; shared pure metrics with conformance, distinct gates. Pair corresponding test moves and shared review fixtures. | Qualification tooling. Alpha sample/profile/provenance, conformance loop/failure, independent review-gate, receipt shape/threshold and CLI contracts; secret-free evidence. |
| **B4** | Three independent cuts, serial checkpoints: confined image-exchange filesystem/manifest owner; creative package/pin boundary removing back-imports; specialist executable/environment host client. | Exchange/security. Path/no-follow/descriptor lifetimes, exact package inventory/publication, pin authority and host identity/settlement tests. Do not combine changes into a generic exchange framework. |
| **B5** | Three independent small cuts: application routing/profile ledger capability; media-reference schema owner; H3 catalogue ownership. Preserve exact persistence/runtime contracts. | Storage/H3 owners. Same-transaction profile deletion, SQL/FK/index/registration parity, frozen catalogue/request/response contract tests. No schema migration or reset implied. |
| **B6** | Supervisor terminal inspection and receipt/output collaborators, plus bridge/supervisor test ownership. No new mixin; keep spawn/identity under existing lock. | Creator-workbench host. Cancellation, terminal/process evidence, environment/readiness, source/profile identity, recovery/UNKNOWN and service isolation. Qualify a new profile identity if implementation changes. |
| **B7** | Separate bounded assignments: explicit Qwen coordinator retaining one shared lane; voice-lab non-collected engine/app/request fixture support. | Gateway and voice-lab respectively. H3/Qwen FIFO/interleaving/cancel/restart and frozen workflows; voice-lab engine/browser/take-dispatch fixture consumers. No provider request needed for static fixture moves. |
| **F1** | Consolidate cast helpers; session-race spec; independent stale/tamper image tests; script-stage journey; canonical read-only layout suite. | Frontend tests. Actual affected Playwright selectors, identical fixture outputs/assertions, serial journey prerequisites and native owner-union update. |
| **F2** | Four Scene Beats presentation modules with explicit typed props; one page authority. Also remove the two-line WorkspaceApp alias and use its actual controller import. | Frontend editors. Scene editor/helper, validation focus, confirmations/selection and affected browser journey; preserve focus keys and callback authority. |
| **F3** | Complete ordered playback owner and route projection; complete still-preview panel; selected-shot inspector. | Frontend media/storyboard. Playback/read-state/source identity/autoplay, retained candidate/currentness, shot confirmation/route/focus and affected browser journeys. |
| **F4** | Seven contract leaves, existing specialist contracts retained, all source/test/E2E imports updated, central type barrel removed. Stage/common leaf feeds execution; project may consume execution, not the reverse. | Frontend contracts. Both TS checks, contract consumers and schema/payload parity; no accidental runtime import cycle. |
| **F5** | Six typed endpoint clients sharing one transport/read gate; update actual consumers and spy targets. H3 request types with video owner, draft-header parsing with canonical/draft endpoints. | Frontend API. Transport/admission/credentials, API requests, authoring mutation receipts, reports, production bridge and affected domain tests. Broad API refactor warrants final full-local policy. |
| **T1** | Exact known test-to-test fixture edges listed above: move/reuse alpha, runtime, cast and raster support; redirect image-lineage helpers to their existing owner. Voice-lab equivalent is paired with B7. | Affected test owners. Compare native case union and fixture isolation, run both producer/consumer suites; no tests imported only for setup. Pair source-related moves with B3/T2. |
| **T2** | Split static extraction checks versus installed-wheel probe; storage isolation/recovery versus drafts versus leases; runtime lifecycle versus H3 composition; authoring schema/entity, timing, continuity, graph and coverage suites. | Packaging/project lifecycle/authoring respectively. Preserve each full temporal scenario and all assertions, update module ownership and compare complete native case union. Separate checkpoints for these independent owners. |
| **D1** | Lab pure teaching model versus DOM controller; style primitives/components/responsive-print owners, stable offline entrypoint. | Documentation UI. Existing lab verifier, frozen prompt/response output parity, direct-file browser interaction and responsive/print inspection. |
| **D2** | Handbook style primitives, components and responsive/print rules; retain chapter structure and dedicated EPUB/mobile-PDF styles. | Documentation publishing. Existing builders/verification, stable anchors/chapter ordering, desktop/mobile/print comparison and affected export checks. |
| **R1–R3** | Owner accepts each intentional breaking removal and supersedes named ADR execution promises; implement only that exact retired surface and its obsolete tests/docs. | Existing runtime owner; security/storage review confirms current readers, H3/managed media, snapshot/restore and no-replay behavior remain. R3 relocates neutral diagnostic tests and updates module allocation. |

Some table rows contain explicitly independent small cuts under a common owner; they are not a proposed multi-contract mega-change. No new dependency injection framework, generic graph toolkit, fixture framework, compatibility barrel or audit archive is recommended.

### Observable proof and final qualification

For an authorized implementation, place the smallest observable journey and its fixture/runtime identity in the existing batch brief **before edits**, following [AGENTS](../../AGENTS.md#small-real-e2e-first-required). For G1/G2/G5 this is the smallest authorized disposable project through the affected generation stage and persisted readback, using the supported native runtime; for F2/F3 it is the affected editor/player interaction with reload and currentness checks. Resolve schema/profile/readiness and dispatch identity early. Focused fake-provider tests prove failure safety; they do not establish real provider or creative acceptance. Existing standing generation authority applies within its actual scope; the audit creates no new generation assignment.

During work, run exact focused or reviewed module selections for changed contracts and their consumers. Test moves must preserve the native test union and update `scripts/testing/module-ownership.json`; do not reduce coverage or weaken assertions to accommodate new files. Changed frontend source requires fresh deterministic generated assets.

One execution owner performs final local qualification on a stable integrated candidate under the repository's existing policy. Broad/cross-layer refactors require the full-local gate; bounded presentation-only changes may qualify through the documented frontend policy only after dependency-surface review. Reuse unchanged evidence rather than repeating full qualification per extraction. Activation is a distinct authorized operation; hosted CI and pushes remain unrequested.

### Maintaining the decision

The existing roadmap points here as **audit complete / implementation pending**. After authorization, the selected batch gets an explicit outcome and stopping condition there; after delivery, update its status and evidence pointer. Leave unselected batches visibly pending rather than labeling them “when next changed.” No new tracking service or automatic line-count gate has been introduced.

The current user-supplied modularity rules apply to every implementation batch: inspect responsibilities before substantial >400 edits, prefer a separate owner for a new responsibility above 500, and justify any substantial change leaving a file above 500. The RETAIN reasons in this inventory are reviewed baseline exceptions, not permanent permission to grow a file. Reassess a changed responsibility/dependency, rather than mechanically invalidating every exception for a trivial edit.

## Verification of this audit

- Census: 1,750 tracked source-like files after explicit generated exclusions; 120 >400 inventory rows, no missing or duplicate candidates; 42 >=500 individually dispositioned.
- Source evidence: current caller/import searches, AST spans, public entry points and relevant ADR contracts; manager reconciliation includes smaller-file cycles, mixin ownership and fixture imports.
- Report validation: independent stable-draft review and local documentation consistency checks are recorded at closeout below.
- No application/test/generated code changes, runtime tests/builds, live data edits, provider work, service restart, deployment, GitHub CI or push are part of this audit.

## Closeout

Independent stable-draft review found no blocking corrections. It reproduced
1,764 tracked source-like files minus 14 generated outputs, the 1,750-file
census, all 120 unique inventory paths and exact line counts, 42 >=500 and the
52/65/3 dispositions. It checked complete frontend coverage and the stated
authority/preservation limits; backend retirement semantics additionally rely
on the backend review and the manager's current-source checks, not a second
independent full semantic audit.

Manager documentation checks passed: every inventory line count matches the
baseline source, no missing/duplicate oversized candidate, all local report and
roadmap link targets exist, and the staged documentation diff is whitespace
clean. All three audit workers returned actual finals, released access and were
archived; their reporting registrations were removed. No runtime qualification or implementation decision was implied by that audit
closeout. The later owner-approved G1/R1–R3 implementation is tracked in the
delivery plan; other batches remain proposed.
