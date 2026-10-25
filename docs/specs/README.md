# Current specification map

Baseline: `8d3b259a`, 2026-10-22. Organization approved by the owner;
[ADR 0217](../adr/0217-feature-oriented-specification-authority.md) records why.

Start here to find agreed requirements by feature. This is not a capability
completion matrix. The first consolidated baseline covers Creator/Professional;
other rows point to existing domain owners, not newly rewritten specifications.
The [complete ADR catalogue](adr-catalogue.md) includes every numbered record,
including unindexed, proposed, candidate and historical records. A catalogue
entry is not an assertion of agreement, implementation, activation or acceptance.
The [chat reconciliation](conflicts.md#chat-decision-reconciliation) adds direct
approval provenance and records the limits of this history review.

## Three views, separate evidence

| View | Owns | Does not establish |
| --- | --- | --- |
| Product / UX | Author-visible behavior, interactions, states, supported surfaces | Implementation or creative acceptance |
| Engineering | API/schema, identity, validation, state/concurrency/persistence contracts | Permission to change agreed UX |
| Architecture | Responsibility boundaries, dependencies and data flow | A fresh code map merely because a diagram exists |
| Decision records | Context, choice, alternatives, consequences and supersession | One complete current specification or executed acceptance |
| Roadmap / verification / manual | Approved work / actual evidence / usage guidance | New requirement authority merely by copying old text |

## Feature and workflow map

Links in the product and engineering columns point to the currently relevant
owner chain. Follow exact amendments/status; broad domain rows are discovery,
not an instruction to execute their workflows.

| Feature / workflow | Product and UX owner | Engineering / architecture owner | Scope and evidence |
| --- | --- | --- | --- |
| Creator and Professional | [Consolidated product baseline](workbenches-product.md) | [Engineering baseline](workbenches-engineering.md), [architecture view](workbenches-architecture.md) | [Conflicts](conflicts.md), [audit](../verification/2026-10-22-workbench-spec-audit.md), [C/P/E playbook](../creative-workflow/graph-workbench-acceptance.md) |
| Brief → Source → Outline → branch suggestions | [Creator guide](../creator/graph-workbench.zh-CN.md), [0112](../adr/0112-original-source-direction-and-outline-settings.md), [0117](../adr/0117-creator-directions-and-branch-suggestions.md) | [0058](../adr/0058-f1a-source-outline-review-contract.md), [0118](../adr/0118-brief-owned-source-topology.md) → [0121](../adr/0121-current-source-graph-authoring.md), [0148](../adr/0148-workspace-owned-branch-mutations.md) | [Roadmap](../roadmap/README.md); no renewed generation authority |
| Cast, appearance and identity references | [Creator manual](../creator/manual.zh-CN.md), [0090](../adr/0090-cast-description-and-notes.md), [0091](../adr/0091-minimum-character-design.md), [0141](../adr/0141-character-render-direction.md) | [0060](../adr/0060-f2a-source-bound-cast-review.md), [0061](../adr/0061-f2b-cast-linked-identity-context.md), [0075](../adr/0075-creator-appearance-selection-metadata.md)–[0077](../adr/0077-character-owned-imported-appearance-assets.md), [0149](../adr/0149-independent-accepted-review-state.md) | Retained accepted evidence and new candidates have separate authority |
| Art design and subject references | [0078](../adr/0078-art-subject-reference-decisions.md), [0094](../adr/0094-author-selected-art-render-style.md), [0097](../adr/0097-art-reference-additional-candidates.md) | [0062](../adr/0062-f3a-source-bound-art-review.md), [0063](../adr/0063-f3b-art-reference-studies.md), [0189](../adr/0189-cross-shot-image-use.md) | Image bytes/reference selection are not identity or rights clearance |
| Script, storyboard and original reports | [0132](../adr/0132-creator-ui-reading-boundaries.md), [creator manual](../creator/manual.zh-CN.md) | [0064](../adr/0064-f4-section-bound-upstream-script.md), [0065](../adr/0065-f5a-source-bound-storyboard-review.md), [0126](../adr/0126-static-script-report-presentation.md), [0147](../adr/0147-owned-pinned-report-renderers.md), [0172](../adr/0172-f4-voice-over-projection.md), [0173](../adr/0173-f5-canonical-dialogue-timing-admission.md) | Original reports remain immutable; edited accepted content is distinct |
| Production bridge and story revision | [Native intent](../creative-workflow/native-bridge-intent.md), [presentation](../creative-workflow/native-bridge-presentation.md), [0123](../adr/0123-node-context-story-production-workflows.md) | [0079](../adr/0079-f5-production-canonical-bridge.md), [0100](../adr/0100-reviewed-production-presentation.md), [0107](../adr/0107-shot-production-presentation.md), [0138](../adr/0138-one-current-story-explicit-rebuild.md), [0150](../adr/0150-review-bound-production-bridge-acknowledgement.md) | First-install-only clauses narrowly superseded by explicit rebuild |
| Shot media, review, video and batch completion | [Native video directions](../creative-workflow/native-video-directions.md), [batch plan](../roadmap/2026-10-18-batch-video-production.md) | [0052](../adr/0052-shot-scoped-video-candidate-selection-and-disposal.md), [0108](../adr/0108-explicit-h3-rejected-take-reconsideration.md), [0135](../adr/0135-end-frame-read-qualification.md), [0191](../adr/0191-whole-pack-human-material-confirmation.md)–[0193](../adr/0193-batch-video-authority.md), [0204](../adr/0204-explicit-rejected-batch-take-replacement.md) | Review, dispatch, ingestion, selection and perceptual acceptance stay separate |
| Read story / play story | [0067](../adr/0067-story-branch-reader-prototype.md), [0132](../adr/0132-creator-ui-reading-boundaries.md) | [0051](../adr/0051-selected-path-preview-and-terminal-publication.md), [0082](../adr/0082-proposed-production-playback-timing.md), [0137](../adr/0137-retained-video-evidence-admission.md), [0138](../adr/0138-one-current-story-explicit-rebuild.md) | Missing, stale, unknown and transport failure remain distinct |
| Project directory, autosave, Freeze, recovery and deletion | [0218 autosave / optional Freeze](../adr/0218-working-input-autosave-and-optional-freeze.md), [retained implementation plan](../roadmap/2026-10-24-autosave-and-project-freeze.md); historical lifecycle: [0113](../adr/0113-project-save-close-and-force-exit.md)–[0116](../adr/0116-current-contract-recovery-and-copy-scope.md), [0201](../adr/0201-unified-project-deletion-preparation.md) | [0040 project storage](../adr/0040-project-folder-storage-boundary.md), [0043](../adr/0043-project-folder-close-quiescence.md), [0044](../adr/0044-portable-project-folder-recovery.md), [0046](../adr/0046-production-project-folder-runtime.md), [0110](../adr/0110-known-project-identity-before-admission.md), [0151](../adr/0151-local-project-command-admission.md) | Current autosave/no-Close contract; qualification and installed activation are evidenced separately in the retained plan/receipt. Exact target/consent/quiescence still applies. |
| Native specialists and pre-video automation | [F0 handoff](../creative-workflow/f0-shuohao-handoff.md), [pre-video contract](../creative-workflow/pre-video-autopilot-contract.md), [approved creator-completion plan](../roadmap/2026-10-22-creator-completion-loop.md) | [0074](../adr/0074-native-codex-image-specialist-dispatch.md), [0088](../adr/0088-frozen-creative-execution-identity.md), [0093](../adr/0093-configurable-specialist-handoffs.md), [0131](../adr/0131-routine-specialist-continuation-authority.md), [0162](../adr/0162-pre-video-autopilot-authority.md), [0174](../adr/0174-bounded-fair-codex-exec-pool.md), [0200](../adr/0200-optional-aggregate-provider-budgets.md), [0202](../adr/0202-bounded-text-content-correction.md), [0203](../adr/0203-explicit-text-correction-and-diagnostics.md) | Frozen jobs/grants retain exact authority; [bounded native UI completion evidence](../verification/2026-10-22-creator-completion-loop.md) is separate from creative acceptance |
| H3, Qwen, Voice Lab and gateway dashboard | [Operations index](../operations/README.md), [service boundary plan](../roadmap/2026-10-22-media-service-boundaries.md) | [0035](../adr/0035-backend-owned-video-modules.md), [0072](../adr/0072-shared-qwen-image-and-h3-generation-lane.md), [0205](../adr/0205-h3-ref2va-per-job-voice-reference.md)–[0216](../adr/0216-media-services-monorepo-boundaries.md) | Service-owned packages/runbooks remain local; integration and runtime adoption are separate |
| Core architecture, generation and field ownership | [Product direction](../adr/0026-story-to-playable-product-direction.md) | [0004](../adr/0004-canonical-generation-contract.md), [0010](../adr/0010-plotloom-clean-repository.md), [0013](../adr/0013-model-neutral-reliable-generation.md), [0018](../adr/0018-trusted-story-timing-allocation.md), [0019](../adr/0019-exact-fragment-and-join-state-contracts.md), [0041](../adr/0041-api-route-module-ownership.md), [0048](../adr/0048-retire-shared-repository-runtime.md) | [Existing architecture readers](../architecture/README.md) are frozen provenance, not current topology |
| Development, qualification and agent-operated QA | [AGENTS](../../AGENTS.md), [development](../development.md), [acceptance playbook](../creative-workflow/graph-workbench-acceptance.md) | [0023](../adr/0023-bounded-delivery-and-evidence.md), [0156](../adr/0156-risk-scoped-local-qualification.md), [0157](../adr/0157-native-test-module-ownership.md), [0198](../adr/0198-delegated-disposable-qa-authority.md), [0199](../adr/0199-local-release-qualification.md), [0217](../adr/0217-feature-oriented-specification-authority.md) | Hosted CI off unless directly requested; evidence levels are not interchangeable |

The [October 22 creator-completion milestone](../roadmap/2026-10-22-creator-completion-loop.md)
was explicitly approved for implementation, real UI E2E and activation. Its
[verification record](../verification/2026-10-22-creator-completion-loop.md)
records bounded completion and composite local qualification, retaining original
failed runs and audio/crop/creative limits. Representative character/branching
quality and an uncoached colleague pilot remain later milestones, not completed
acceptance or new implementation authority.

## Authority and maintenance

Shared vocabulary is maintained in the [creator UI wording guide](../operations/creator-ui-wording.md).
Provider/runbook details remain in [operations](../operations/README.md),
[media service ownership](../operations/media-services.md) and the service-local
[workbench runtime guide](../../services/creator_workbench/README.md).

1. An explicit owner decision governs its exact scope. Do not infer agreement
   from a sketch click, file location, record number, passing test or current code.
2. Use consolidated workbench clauses plus their cited source chain. Exact later
   amendments can supersede one clause without replacing the whole older record.
3. [Conflicts](conflicts.md) separate resolved supersessions from unresolved intent.
   A disputed requirement remains blocked for that conclusion; audit clear clauses
   independently. Missing evidence is UNVERIFIED, not an invented deviation.
   Sidebar height, Professional wheel ownership and Pro visual-state lifetime
   are explicitly agreed; no intent question remains in this bounded reconciliation.
   Agreement does not establish implementation or authorize the reported repairs.
4. Preserve original prototypes/records as provenance, not runtime dependencies.
   The approved v9 reference is pinned in the original workbench plan; subsequent
   source decisions govern exact admitted behavior. No new sketch approval occurs here.
5. New approved changes update the owning spec and affected C/P/E mapping, then
   link rationale and evidence. Do not copy requirement ownership into a run ledger.
   For chat-origin decisions, retain the direct human decision and relevant
   proposal context; reconcile later approval/status before updating an index.

This consolidation does not certify all product domains or authorize fixes.
The workbench audit reports code/evidence deviations before application changes.
The [workbench alignment implementation plan](../roadmap/2026-10-23-workbench-spec-alignment.md)
is the proposed delivery scope for the four findings and adopted C56/C57 behavior;
it awaits implementation approval rather than changing requirement authority.
