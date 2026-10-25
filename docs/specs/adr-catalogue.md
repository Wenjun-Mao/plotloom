# Complete ADR discovery catalogue

Snapshot: 2026-10-22, source baseline `8d3b259a` plus documentation-only ADR 0217.
Amended 2026-10-24 to include ADR 0218's owner-approved autosave/optional Freeze decision.
Amended 2026-10-25 to include ADR 0219's owner-approved validated installation-only reader. Earlier opening status cues remain historical excerpts, not new qualification claims.
Each numbered Markdown file is linked once below; `docs/adr/README.md` remains
a selected decision-chain guide, not this exhaustive inventory. The feature map
is [README](README.md); this catalogue preserves full slugs and historical IDs.

The opening status cue is a literal excerpt, not a resolved current-status badge.
It may describe an old adoption boundary or need later amendments/receipts.
No marker does not mean accepted or rejected. Proposed/candidate/implemented/
qualified/activated/human-accepted states are different. Do not infer precedence
from numeric order alone. Two distinct `0040` slugs remain; no `0164` is invented.
Cohorts below are discovery aids, not exclusive roles or approval classifications.

## Foundations, extraction and canonical generation

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0003-v2-strangler-architecture](../adr/0003-v2-strangler-architecture.md) | See source; no uniform opening status marker |
| [0004-canonical-generation-contract](../adr/0004-canonical-generation-contract.md) | See source; no uniform opening status marker |
| [0005-generation-runs-and-quarantine](../adr/0005-generation-runs-and-quarantine.md) | See source; no uniform opening status marker |
| [0006-media-adapter-boundary](../adr/0006-media-adapter-boundary.md) | See source; no uniform opening status marker |
| [0007-archify-architecture-documentation](../adr/0007-archify-architecture-documentation.md) | See source; no uniform opening status marker |
| [0008-capability-based-adoption-tracking](../adr/0008-capability-based-adoption-tracking.md) | See source; no uniform opening status marker |
| [0009-atomic-project-bootstrap](../adr/0009-atomic-project-bootstrap.md) | See source; no uniform opening status marker |
| [0010-plotloom-clean-repository](../adr/0010-plotloom-clean-repository.md) | See source; no uniform opening status marker |
| [0011-provider-profiles-and-generation-work-units](../adr/0011-provider-profiles-and-generation-work-units.md) | See source; no uniform opening status marker |
| [0012-approved-storyboards-and-production-units](../adr/0012-approved-storyboards-and-production-units.md) | See source; no uniform opening status marker |
| [0013-model-neutral-reliable-generation](../adr/0013-model-neutral-reliable-generation.md) | Accepted. |
| [0014-project-lifecycle-and-workbench](../adr/0014-project-lifecycle-and-workbench.md) | Accepted and implemented for M1-B0 and M1-B1. The complete local checkpoint |
| [0015-exact-work-unit-repair](../adr/0015-exact-work-unit-repair.md) | Accepted for M1-R. |
| [0016-versioned-authoring-quality-gates-and-approval](../adr/0016-versioned-authoring-quality-gates-and-approval.md) | Accepted. |
| [0017-alpha-validation-and-correction-boundaries](../adr/0017-alpha-validation-and-correction-boundaries.md) | Accepted. |
| [0018-trusted-story-timing-allocation](../adr/0018-trusted-story-timing-allocation.md) | Accepted. |
| [0019-exact-fragment-and-join-state-contracts](../adr/0019-exact-fragment-and-join-state-contracts.md) | Accepted. |
| [0020-alpha-public-score-sheet-drafts](../adr/0020-alpha-public-score-sheet-drafts.md) | Accepted. |
| [0021-alpha-source-provenance](../adr/0021-alpha-source-provenance.md) | Accepted. |
| [0022-executable-correction-contracts](../adr/0022-executable-correction-contracts.md) | Accepted. |
| [0023-bounded-delivery-and-evidence](../adr/0023-bounded-delivery-and-evidence.md) | Accepted for development workflow. Generation field ownership remains governed |
| [0024-pluggable-text-backends-and-independent-qualification](../adr/0024-pluggable-text-backends-and-independent-qualification.md) | Accepted by the user on 2026-09-07; implementation pending. This amends the |
| [0025-provider-readiness-and-versioned-admission](../adr/0025-provider-readiness-and-versioned-admission.md) | Accepted 2026-09-10. This is a focused implementation amendment to ADR 0024. |

## Product, assets, provider and persistence boundaries

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0026-story-to-playable-product-direction](../adr/0026-story-to-playable-product-direction.md) | Accepted direction and P0 architecture amendment, 2026-09-11, following the two |
| [0027-managed-imported-still-preview-contract](../adr/0027-managed-imported-still-preview-contract.md) | Accepted and implemented for the approved P0 slice, 2026-09-11. This is the |
| [0028-agent-operated-image-jobs](../adr/0028-agent-operated-image-jobs.md) | Accepted and integrated, including brief/usability corrections, on pushed 'main' |
| [0029-manual-image-handoff-usability-and-identity-references](../adr/0029-manual-image-handoff-usability-and-identity-references.md) | Accepted for the P1 usability checkpoint, 2026-09-11. |
| [0030-character-reference-decisions-and-cross-shot-review](../adr/0030-character-reference-decisions-and-cross-shot-review.md) | Accepted for P1.5 implementation, 2026-09-12. Visual qualification remains a |
| [0031-bounded-wan-video-production](../adr/0031-bounded-wan-video-production.md) | Status: approved implementation contract, 2026-09-12. Provider/model and the |
| [0032-project-local-active-storage-and-imagegen-cleanup](../adr/0032-project-local-active-storage-and-imagegen-cleanup.md) | Accepted, 2026-09-13. This is an operational storage contract for active local |
| [0033-private-minimax-h3-gateway](../adr/0033-private-minimax-h3-gateway.md) | See source; no uniform opening status marker |
| [0034-provider-neutral-video-adapters-and-local-h3](../adr/0034-provider-neutral-video-adapters-and-local-h3.md) | See source; no uniform opening status marker |
| [0035-backend-owned-video-modules](../adr/0035-backend-owned-video-modules.md) | See source; no uniform opening status marker |
| [0036-minimax-h3-profile-catalog](../adr/0036-minimax-h3-profile-catalog.md) | See source; no uniform opening status marker |
| [0037-reviewed-keyframe-aspect-preparation](../adr/0037-reviewed-keyframe-aspect-preparation.md) | See source; no uniform opening status marker |
| [0038-h3-gateway-durable-fifo-dispatch](../adr/0038-h3-gateway-durable-fifo-dispatch.md) | See source; no uniform opening status marker |
| [0039-h3-gateway-managed-output-retention](../adr/0039-h3-gateway-managed-output-retention.md) | See source; no uniform opening status marker |
| [0040-private-h3-image-ingestion](../adr/0040-private-h3-image-ingestion.md) | See source; no uniform opening status marker |
| [0040-project-folder-storage-boundary](../adr/0040-project-folder-storage-boundary.md) | Accepted, 2026-09-13. Checkpoint 2A replaces the rejected '460ff56' |
| [0041-api-route-module-ownership](../adr/0041-api-route-module-ownership.md) | Accepted for the API modularization checkpoint. |
| [0042-persistence-capability-composition](../adr/0042-persistence-capability-composition.md) | See source; no uniform opening status marker |
| [0043-project-folder-close-quiescence](../adr/0043-project-folder-close-quiescence.md) | Accepted, 2026-09-14. This continues the unwired project-folder composition |
| [0044-portable-project-folder-recovery](../adr/0044-portable-project-folder-recovery.md) | Accepted, 2026-09-14. This advances the direct, format-6 project-folder |
| [0045-project-video-dispatch-ownership](../adr/0045-project-video-dispatch-ownership.md) | Accepted, 2026-09-14. This advances the direct format-7 project-folder |
| [0046-production-project-folder-runtime](../adr/0046-production-project-folder-runtime.md) | Accepted, 2026-09-14. |
| [0047-production-browser-parity-and-project-lifecycle](../adr/0047-production-browser-parity-and-project-lifecycle.md) | Accepted, 2026-09-14. |
| [0048-retire-shared-repository-runtime](../adr/0048-retire-shared-repository-runtime.md) | Accepted, 2026-09-14. |
| [0049-h3-catalog-clean-cutover](../adr/0049-h3-catalog-clean-cutover.md) | See source; no uniform opening status marker |
| [0050-unified-h3-generation-contract](../adr/0050-unified-h3-generation-contract.md) | See source; no uniform opening status marker |

## Source/review/playback and H3/Qwen contracts

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0051-selected-path-preview-and-terminal-publication](../adr/0051-selected-path-preview-and-terminal-publication.md) | See source; no uniform opening status marker |
| [0052-shot-scoped-video-candidate-selection-and-disposal](../adr/0052-shot-scoped-video-candidate-selection-and-disposal.md) | See source; no uniform opening status marker |
| [0053-synopsis-proposal-review-boundary](../adr/0053-synopsis-proposal-review-boundary.md) | See source; no uniform opening status marker |
| [0054-editable-storyboard-continuation-currentness](../adr/0054-editable-storyboard-continuation-currentness.md) | See source; no uniform opening status marker |
| [0055-storyboard-required-entity-presence-correction](../adr/0055-storyboard-required-entity-presence-correction.md) | See source; no uniform opening status marker |
| [0056-graph-typed-edge-entry-state-boundary](../adr/0056-graph-typed-edge-entry-state-boundary.md) | See source; no uniform opening status marker |
| [0057-shuohao-first-creative-workflow](../adr/0057-shuohao-first-creative-workflow.md) | Status: Accepted direction, 2026-09-17; F0 foundation implemented, F1–F10 pending. |
| [0058-f1a-source-outline-review-contract](../adr/0058-f1a-source-outline-review-contract.md) | Status: Accepted, 2026-09-17. |
| [0059-f1b-source-bound-section-map](../adr/0059-f1b-source-bound-section-map.md) | Status: Accepted, 2026-09-18. |
| [0060-f2a-source-bound-cast-review](../adr/0060-f2a-source-bound-cast-review.md) | Status: Accepted, 2026-09-18. |
| [0061-f2b-cast-linked-identity-context](../adr/0061-f2b-cast-linked-identity-context.md) | Status: Accepted, 2026-09-18. |
| [0062-f3a-source-bound-art-review](../adr/0062-f3a-source-bound-art-review.md) | Status: Accepted, 2026-09-18. |
| [0063-f3b-art-reference-studies](../adr/0063-f3b-art-reference-studies.md) | Status: Accepted, 2026-09-18. |
| [0064-f4-section-bound-upstream-script](../adr/0064-f4-section-bound-upstream-script.md) | Status: Accepted, 2026-09-18. |
| [0065-f5a-source-bound-storyboard-review](../adr/0065-f5a-source-bound-storyboard-review.md) | Status: Accepted, 2026-09-18. |
| [0066-h3-qualified-job-duration-contract](../adr/0066-h3-qualified-job-duration-contract.md) | See source; no uniform opening status marker |
| [0067-story-branch-reader-prototype](../adr/0067-story-branch-reader-prototype.md) | Status: Accepted, 2026-09-18. |
| [0068-h3-reproducibility-and-qualified-recipes](../adr/0068-h3-reproducibility-and-qualified-recipes.md) | See source; no uniform opening status marker |
| [0069-h3-explicit-sampling-recipes-and-profile-cutover](../adr/0069-h3-explicit-sampling-recipes-and-profile-cutover.md) | See source; no uniform opening status marker |
| [0070-h3-quality-resolution-contract](../adr/0070-h3-quality-resolution-contract.md) | See source; no uniform opening status marker |
| [0071-read-only-character-reference-gallery](../adr/0071-read-only-character-reference-gallery.md) | Status: Accepted, 2026-09-20. |
| [0072-shared-qwen-image-and-h3-generation-lane](../adr/0072-shared-qwen-image-and-h3-generation-lane.md) | See source; no uniform opening status marker |
| [0073-qwen-image-reviewed-canvas-contract](../adr/0073-qwen-image-reviewed-canvas-contract.md) | See source; no uniform opening status marker |
| [0074-native-codex-image-specialist-dispatch](../adr/0074-native-codex-image-specialist-dispatch.md) | See source; no uniform opening status marker |
| [0075-creator-appearance-selection-metadata](../adr/0075-creator-appearance-selection-metadata.md) | See source; no uniform opening status marker |
| [0076-cast-reopen-cancellation-and-bounded-comparison](../adr/0076-cast-reopen-cancellation-and-bounded-comparison.md) | See source; no uniform opening status marker |
| [0077-character-owned-imported-appearance-assets](../adr/0077-character-owned-imported-appearance-assets.md) | See source; no uniform opening status marker |
| [0078-art-subject-reference-decisions](../adr/0078-art-subject-reference-decisions.md) | Status: Accepted, 2026-09-22. |
| [0079-f5-production-canonical-bridge](../adr/0079-f5-production-canonical-bridge.md) | Status: Accepted for scoped implementation, 2026-09-22. Product and creative |
| [0080-advisory-shot-count-policy](../adr/0080-advisory-shot-count-policy.md) | Status: Accepted for bounded implementation, 2026-09-22. Creative and production acceptance remain separate. |
| [0081-narrow-source-static-and-api-lint-checks](../adr/0081-narrow-source-static-and-api-lint-checks.md) | Status: Accepted for bounded verification, 2026-09-22. |
| [0082-proposed-production-playback-timing](../adr/0082-proposed-production-playback-timing.md) | See source; no uniform opening status marker |
| [0083-h3-single-image-prompt-contract](../adr/0083-h3-single-image-prompt-contract.md) | Status: the 2026-09-23 v2 decision below is historical; the 2026-09-24 |
| [0084-h3-v1-vocal-control-comparison](../adr/0084-h3-v1-vocal-control-comparison.md) | Status: historical one-treatment experiment. New preparation through this |

## Brief-to-production UX, lifecycle and workbench

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0085-brief-to-source-entry-and-optional-declarations](../adr/0085-brief-to-source-entry-and-optional-declarations.md) | Status: Accepted for the bounded creator walkthrough fix, 2026-09-25. |
| [0086-trusted-outline-candidate-reader](../adr/0086-trusted-outline-candidate-reader.md) | Status: Superseded within this ADR by the creator-approved revision below, 2026-09-26. |
| [0087-branch-save-apply-continue](../adr/0087-branch-save-apply-continue.md) | Status: accepted for the bounded creator-walkthrough improvement, 2026-09-26. |
| [0088-frozen-creative-execution-identity](../adr/0088-frozen-creative-execution-identity.md) | Status: Accepted — 2026-09-26 |
| [0089-cast-review-text-presentation](../adr/0089-cast-review-text-presentation.md) | Status: accepted for bounded creator walkthrough, 2026-09-26. |
| [0090-cast-description-and-notes](../adr/0090-cast-description-and-notes.md) | Status: accepted, 2026-09-26 |
| [0091-minimum-character-design](../adr/0091-minimum-character-design.md) | Status: accepted, 2026-09-26 |
| [0092-selection-controls-versus-actions](../adr/0092-selection-controls-versus-actions.md) | Status: Accepted |
| [0093-configurable-specialist-handoffs](../adr/0093-configurable-specialist-handoffs.md) | See source; no uniform opening status marker |
| [0094-author-selected-art-render-style](../adr/0094-author-selected-art-render-style.md) | Status: accepted, 2026-09-29. Supersedes the deferred painterly/live-action |
| [0095-persistent-creator-workbench](../adr/0095-persistent-creator-workbench.md) | Status: accepted, 2026-10-01. |
| [0096-native-specialist-deep-link-wake](../adr/0096-native-specialist-deep-link-wake.md) | Status: accepted, 2026-10-02. |
| [0097-art-reference-additional-candidates](../adr/0097-art-reference-additional-candidates.md) | Status: accepted, 2026-10-02. |
| [0098-isolated-workbench-native-transport](../adr/0098-isolated-workbench-native-transport.md) | Status: accepted for the bounded test-installation launcher, 2026-10-02. |
| [0099-source-review-activation-currentness](../adr/0099-source-review-activation-currentness.md) | accepted r1 bound to Script r2 after navigation and a same-project server |
| [0100-reviewed-production-presentation](../adr/0100-reviewed-production-presentation.md) | Status: accepted for the bounded unattended Stage 4 source gate, 2026-10-02. |
| [0101-accessible-creator-confirmations](../adr/0101-accessible-creator-confirmations.md) | Status: accepted for the owner-authorized Stage 4 correction, 2026-10-02. |
| [0102-explicit-h3-review-seed](../adr/0102-explicit-h3-review-seed.md) | Status: Accepted |
| [0103-retained-candidate-read-reconciliation](../adr/0103-retained-candidate-read-reconciliation.md) | Status: Accepted |
| [0104-workbench-static-revalidation](../adr/0104-workbench-static-revalidation.md) | Status: Accepted |
| [0105-h3-review-media-read-recovery](../adr/0105-h3-review-media-read-recovery.md) | Status: Accepted |
| [0106-reviewed-pre-generation-image-terminal-outcome](../adr/0106-reviewed-pre-generation-image-terminal-outcome.md) | See source; no uniform opening status marker |
| [0107-shot-production-presentation](../adr/0107-shot-production-presentation.md) | Status: accepted for the 2026-10-03 E2E-first continuation. |
| [0108-explicit-h3-rejected-take-reconsideration](../adr/0108-explicit-h3-rejected-take-reconsideration.md) | Status: Accepted |
| [0109-bounded-browser-ci-evidence](../adr/0109-bounded-browser-ci-evidence.md) | Status: Accepted, 2026-10-03. |
| [0110-known-project-identity-before-admission](../adr/0110-known-project-identity-before-admission.md) | Status: accepted for the bounded E2E runtime repair, 2026-10-04. |
| [0111-journey-first-creator-presentation](../adr/0111-journey-first-creator-presentation.md) | Status: accepted for the owner-approved October 4, 2026 UI polish pass. |
| [0112-original-source-direction-and-outline-settings](../adr/0112-original-source-direction-and-outline-settings.md) | Status: Accepted, 2026-10-04. |
| [0113-project-save-close-and-force-exit](../adr/0113-project-save-close-and-force-exit.md) | Status: Accepted, 2026-10-04. |
| [0114-direct-project-deletion](../adr/0114-direct-project-deletion.md) | Status: Accepted, 2026-10-04. |
| [0115-workspace-home-navigation](../adr/0115-workspace-home-navigation.md) | Status: Accepted, 2026-10-04. |
| [0116-current-contract-recovery-and-copy-scope](../adr/0116-current-contract-recovery-and-copy-scope.md) | Status: Owner approved, 2026-10-04. See the six-repair roadmap assignment. |
| [0117-creator-directions-and-branch-suggestions](../adr/0117-creator-directions-and-branch-suggestions.md) | Accepted 2026-10-04 for the approved creator UI batch. The topology portion is superseded before release by ADR 0118 after the owner approved Brief-driven br… |
| [0118-brief-owned-source-topology](../adr/0118-brief-owned-source-topology.md) | Accepted October 4, 2026 after the owner expanded the creator UI batch. |
| [0119-current-workbench-visual-roles](../adr/0119-current-workbench-visual-roles.md) | Accepted October 4, 2026 under the approved sketch-led visual assignment. |
| [0218-working-input-autosave-and-optional-freeze](../adr/0218-working-input-autosave-and-optional-freeze.md) | Status: accepted for implementation, 2026-10-24. Implements the owner-approved |

## Graph authoring, node workflows and read authority

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0120-explicit-node-footage-mode](../adr/0120-explicit-node-footage-mode.md) | Accepted for bounded G0 implementation, 2026-10-06. The manager approved this |
| [0121-current-source-graph-authoring](../adr/0121-current-source-graph-authoring.md) | Status: accepted under the owner-approved G0–G1 workbench scope, 2026-10-06. |
| [0122-creator-workspace-presentation](../adr/0122-creator-workspace-presentation.md) | Status: accepted within owner-approved G2 scope, 2026-10-06. |
| [0123-node-context-story-production-workflows](../adr/0123-node-context-story-production-workflows.md) | Status: accepted within owner-approved G3/G4 scope, 2026-10-06. |
| [0124-requesting-client-project-read-quiescence](../adr/0124-requesting-client-project-read-quiescence.md) | Status: accepted within G5 demonstrated-blocker scope, 2026-10-06. |
| [0125-complete-candidate-asset-projections](../adr/0125-complete-candidate-asset-projections.md) | Status: Accepted, 2026-10-07. |
| [0126-static-script-report-presentation](../adr/0126-static-script-report-presentation.md) | Status: Accepted, 2026-10-07. |
| [0127-reusable-creator-lifecycle-acceptance](../adr/0127-reusable-creator-lifecycle-acceptance.md) | Status: Accepted workflow decision, 2026-10-07. Product capabilities and each run's |
| [0128-graph-edit-safety-diagnostics](../adr/0128-graph-edit-safety-diagnostics.md) | Accepted 2026-10-07. |
| [0129-read-only-access-versus-save-progress](../adr/0129-read-only-access-versus-save-progress.md) | Accepted 2026-10-07. |
| [0130-media-selection-read-after-write-authority](../adr/0130-media-selection-read-after-write-authority.md) | Accepted 2026-10-07. |
| [0131-routine-specialist-continuation-authority](../adr/0131-routine-specialist-continuation-authority.md) | Accepted 2026-10-08 UTC; owner clarification during the creator E2E run. |
| [0132-creator-ui-reading-boundaries](../adr/0132-creator-ui-reading-boundaries.md) | Status: Accepted, 2026-10-08. |
| [0133-owned-project-read-acknowledgement](../adr/0133-owned-project-read-acknowledgement.md) | Status: Accepted, 2026-10-08. |
| [0134-typed-review-context-diagnostics](../adr/0134-typed-review-context-diagnostics.md) | Status: Accepted, 2026-10-08; extended to Script/Storyboard 2026-10-09. |
| [0135-end-frame-read-qualification](../adr/0135-end-frame-read-qualification.md) | Status: Accepted, 2026-10-08. |
| [0136-project-load-availability](../adr/0136-project-load-availability.md) | Status: Accepted, 2026-10-08. |
| [0137-retained-video-evidence-admission](../adr/0137-retained-video-evidence-admission.md) | Status: Accepted for the demonstrated E21/E22 repair, 2026-10-08. |
| [0138-one-current-story-explicit-rebuild](../adr/0138-one-current-story-explicit-rebuild.md) | Status: owner-approved contract, 2026-10-08; implemented in the isolated candidate, |
| [0139-profile-owned-text-credentials](../adr/0139-profile-owned-text-credentials.md) | Status: adopted under the owner's current-only configuration requirement, |
| [0140-native-bridge-intent-candidates](../adr/0140-native-bridge-intent-candidates.md) | Status: implemented candidate; software qualification and native acceptance are separate. |
| [0141-character-render-direction](../adr/0141-character-render-direction.md) | Status: accepted, 2026-10-09 |
| [0142-shot-display-identity](../adr/0142-shot-display-identity.md) | Status: accepted |
| [0143-identity-review-refusal-guidance](../adr/0143-identity-review-refusal-guidance.md) | Status: Accepted, 2026-10-09. |
| [0144-runtime-owned-workspace-capabilities](../adr/0144-runtime-owned-workspace-capabilities.md) | Status: implemented candidate; qualification is recorded in the E22 receipt. |
| [0145-current-read-authority-for-graph-and-directory](../adr/0145-current-read-authority-for-graph-and-directory.md) | Status: implemented candidate; qualification and limits are recorded in the |
| [0146-explicit-unassessable-identity-review](../adr/0146-explicit-unassessable-identity-review.md) | Status: accepted by the owner, 2026-10-09; implemented and independently source/ |
| [0147-owned-pinned-report-renderers](../adr/0147-owned-pinned-report-renderers.md) | Status: accepted by the owner, 2026-10-09; fork implemented, independently reviewed |
| [0148-workspace-owned-branch-mutations](../adr/0148-workspace-owned-branch-mutations.md) | Status: implemented and independently reviewed; scoped frontend/browser |
| [0149-independent-accepted-review-state](../adr/0149-independent-accepted-review-state.md) | Status: implementation in progress, 2026-10-09. |
| [0150-review-bound-production-bridge-acknowledgement](../adr/0150-review-bound-production-bridge-acknowledgement.md) | Status: implemented and independently reviewed, 2026-10-09. Focused qualification |
| [0151-local-project-command-admission](../adr/0151-local-project-command-admission.md) | Status: implemented; focused qualification and independent source review passed, |

## Qualification, workers, bridge and automation

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0152-owned-browser-fixture-listeners](../adr/0152-owned-browser-fixture-listeners.md) | Status: adopted for the E2E fixture, 2026-10-09; final focused checks, independent |
| [0153-duration-balanced-browser-files](../adr/0153-duration-balanced-browser-files.md) | Status: adopted in CI configuration, 2026-10-10; exact hosted qualification is |
| [0154-process-local-style-contract-derivation](../adr/0154-process-local-style-contract-derivation.md) | Status: accepted for bounded implementation probe, 2026-10-10. |
| [0155-recommended-creative-workflow-guide](../adr/0155-recommended-creative-workflow-guide.md) | Status: accepted, 2026-10-10. |
| [0156-risk-scoped-local-qualification](../adr/0156-risk-scoped-local-qualification.md) | Status: accepted, 2026-10-10. |
| [0157-native-test-module-ownership](../adr/0157-native-test-module-ownership.md) | Status: accepted, 2026-10-11. |
| [0158-accepted-source-seed-for-graph-command-tests](../adr/0158-accepted-source-seed-for-graph-command-tests.md) | Status: accepted, 2026-10-11. |
| [0159-four-duration-balanced-hosted-browser-shards](../adr/0159-four-duration-balanced-hosted-browser-shards.md) | Status: accepted, 2026-10-11. |
| [0160-two-process-python-full-gate](../adr/0160-two-process-python-full-gate.md) | Status: accepted. The exact-runner integrated local full gate passed on |
| [0161-specialist-presentation-candidates](../adr/0161-specialist-presentation-candidates.md) | Status: accepted |
| [0162-pre-video-autopilot-authority](../adr/0162-pre-video-autopilot-authority.md) | Status: accepted for implementation, 2026-10-12; source implementation present, release gates pending. The owner selected automatic |
| [0163-autopilot-brief-style-authority](../adr/0163-autopilot-brief-style-authority.md) | Status: accepted for implementation, 2026-10-12. Extends the |
| [0165-serial-codex-exec-autopilot](../adr/0165-serial-codex-exec-autopilot.md) | Status: accepted for the owner-approved serial executor checkpoint, 2026-10-13. |
| [0166-receipt-scoped-authority-snapshots](../adr/0166-receipt-scoped-authority-snapshots.md) | Status: accepted and locally qualified. The owner approved this narrow |
| [0167-operation-local-storyboard-context](../adr/0167-operation-local-storyboard-context.md) | Status: accepted by the owner on October 14, 2026; implemented with focused |
| [0168-exact-python-worker-completion](../adr/0168-exact-python-worker-completion.md) | Status: accepted for the owner-approved bounded worker experiment on October |
| [0169-isolated-codex-python-validator-runtime](../adr/0169-isolated-codex-python-validator-runtime.md) | See source; no uniform opening status marker |
| [0170-operation-local-bridge-and-controller-claim](../adr/0170-operation-local-bridge-and-controller-claim.md) | Status: owner-approved October 14, 2026; independently design-reviewed; |
| [0171-historical-python-scheduling-predictions](../adr/0171-historical-python-scheduling-predictions.md) | Status: accepted for the owner's October 14 scheduling preapproval, after an |
| [0172-f4-voice-over-projection](../adr/0172-f4-voice-over-projection.md) | Status: accepted for the bounded serial-executor repair, 2026-10-14. |
| [0173-f5-canonical-dialogue-timing-admission](../adr/0173-f5-canonical-dialogue-timing-admission.md) | Status: accepted for the bounded serial-executor repair, 2026-10-14. |
| [0174-bounded-fair-codex-exec-pool](../adr/0174-bounded-fair-codex-exec-pool.md) | Status: accepted for the approved bounded implementation, 2026-10-14. |
| [0175-dependency-ready-autopilot-materials](../adr/0175-dependency-ready-autopilot-materials.md) | Status: accepted for the approved bounded implementation, 2026-10-14. |
| [0176-receipt-command-local-material-projections](../adr/0176-receipt-command-local-material-projections.md) | Status: owner-authorized October 14, 2026; independently design-reviewed and |
| [0177-invocation-local-autopilot-profile-construction](../adr/0177-invocation-local-autopilot-profile-construction.md) | Status: owner-authorized October 14, 2026; implementation committed at |
| [0178-capsule-plan-handoff-authority](../adr/0178-capsule-plan-handoff-authority.md) | See source; no uniform opening status marker |
| [0179-planned-script-dialogue-compatibility](../adr/0179-planned-script-dialogue-compatibility.md) | See source; no uniform opening status marker |
| [0180-outline-report-metadata-receiving](../adr/0180-outline-report-metadata-receiving.md) | Status: Implemented candidate, 2026-10-16; independent/Root source review pending. |
| [0181-historical-qualification-preservation](../adr/0181-historical-qualification-preservation.md) | Status: Human-approved decision, implemented candidate, 2026-10-16; |
| [0182-failed-imagegen-event-metadata](../adr/0182-failed-imagegen-event-metadata.md) | Status: Root-approved bounded decision; implementation candidate, 2026-10-16. |
| [0183-closure-local-canonical-row-bytes](../adr/0183-closure-local-canonical-row-bytes.md) | Status: bounded trial statically accepted by Root, October 17, 2026. Current-source |
| [0184-validation-local-profile-construction](../adr/0184-validation-local-profile-construction.md) | Status: Root-authorized bounded current-source implementation, October 17, 2026. |
| [0185-installed-text-test-prefix](../adr/0185-installed-text-test-prefix.md) | Status: Accepted for bounded local retention, October 17, 2026, after Root and |
| [0186-run-view-local-checkpoint-evidence](../adr/0186-run-view-local-checkpoint-evidence.md) | Status: owner-authorized October 15, 2026; implementation, 99 focused checks and |
| [0187-frozen-worker-instruction-discovery](../adr/0187-frozen-worker-instruction-discovery.md) | Status: Accepted, 2026-10-17 |
| [0188-native-bridge-request-budget](../adr/0188-native-bridge-request-budget.md) | Status: Accepted, 2026-10-17 |

## Material/batch authority, lifecycle and corrections

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0189-cross-shot-image-use](../adr/0189-cross-shot-image-use.md) | Implemented in '901e6270', with browser-fixture correction 'cf689db9', and locally |
| [0190-explicit-material-continuation-and-abandonment](../adr/0190-explicit-material-continuation-and-abandonment.md) | Status: accepted; implementation 'dd3033d6' locally qualified, 2026-10-18. |
| [0191-whole-pack-human-material-confirmation](../adr/0191-whole-pack-human-material-confirmation.md) | Status: accepted for implementation, 2026-10-17, under the approved |
| [0192-inspection-and-authority-admission](../adr/0192-inspection-and-authority-admission.md) | Status: implementation decision, 2026-10-18 |
| [0193-batch-video-authority](../adr/0193-batch-video-authority.md) | Status: implementation decision, 2026-10-18 |
| [0194-provider-free-host-platform-resources](../adr/0194-provider-free-host-platform-resources.md) | Status: accepted; scoped module/Linux verification passed, 2026-10-18. |
| [0195-command-identity-display-width](../adr/0195-command-identity-display-width.md) | Status: accepted; scoped module/Linux verification passed, 2026-10-18. |
| [0196-owned-copied-hosted-test-interpreter](../adr/0196-owned-copied-hosted-test-interpreter.md) | Status: manager-approved; scoped verification only. See the |
| [0197-codex-exec-image-instruction-access](../adr/0197-codex-exec-image-instruction-access.md) | Status: accepted for implementation; activation and provider E2E remain separate. |
| [0198-delegated-disposable-qa-authority](../adr/0198-delegated-disposable-qa-authority.md) | Status: accepted implementation decision, 2026-10-19 |
| [0199-local-release-qualification](../adr/0199-local-release-qualification.md) | Status: accepted owner-directed workflow decision, 2026-10-19 |
| [0200-optional-aggregate-provider-budgets](../adr/0200-optional-aggregate-provider-budgets.md) | Status: accepted implementation decision, 2026-10-19 |
| [0201-unified-project-deletion-preparation](../adr/0201-unified-project-deletion-preparation.md) | Status: accepted for implementation, 2026-10-19; source qualification is separate. |
| [0202-bounded-text-content-correction](../adr/0202-bounded-text-content-correction.md) | Status: accepted for source implementation, 2026-10-21. |
| [0203-explicit-text-correction-and-diagnostics](../adr/0203-explicit-text-correction-and-diagnostics.md) | Status: owner-approved source implementation, 2026-10-22. |
| [0204-explicit-rejected-batch-take-replacement](../adr/0204-explicit-rejected-batch-take-replacement.md) | Status: accepted implementation decision, 2026-10-22 |

## Integrated media services and dashboard

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0205-h3-ref2va-per-job-voice-reference](../adr/0205-h3-ref2va-per-job-voice-reference.md) | See source; no uniform opening status marker |
| [0206-spark-voice-lab-candidate-boundary](../adr/0206-spark-voice-lab-candidate-boundary.md) | See source; no uniform opening status marker |
| [0207-voice-lab-projects-and-published-voice-identity](../adr/0207-voice-lab-projects-and-published-voice-identity.md) | See source; no uniform opening status marker |
| [0208-voice-lab-observed-job-progress](../adr/0208-voice-lab-observed-job-progress.md) | See source; no uniform opening status marker |
| [0209-voice-lab-independent-engines-and-delivery](../adr/0209-voice-lab-independent-engines-and-delivery.md) | See source; no uniform opening status marker |
| [0210-h3-runtime-qualification-and-catalog-isolation](../adr/0210-h3-runtime-qualification-and-catalog-isolation.md) | See source; no uniform opening status marker |
| [0211-voice-lab-shared-host-operating-boundary](../adr/0211-voice-lab-shared-host-operating-boundary.md) | See source; no uniform opening status marker |
| [0212-published-voice-performance-takes-and-shared-admission](../adr/0212-published-voice-performance-takes-and-shared-admission.md) | See source; no uniform opening status marker |
| [0213-h3-video-only-vae-precision](../adr/0213-h3-video-only-vae-precision.md) | Status: accepted by owner on 2026-10-06; deployment requires its separate receipt. |
| [0214-read-only-gateway-dashboard](../adr/0214-read-only-gateway-dashboard.md) | Status: accepted for the owner-approved dashboard slice, 2026-10-20. |
| [0215-h3-dashboard-submission-boundary](../adr/0215-h3-dashboard-submission-boundary.md) | Status: accepted by owner, 2026-10-21. Extends ADR 0214's read-only surface. |
| [0216-media-services-monorepo-boundaries](../adr/0216-media-services-monorepo-boundaries.md) | Status: repository direction and implementation approved by the owner on 2026-10-22. |

## Validated installed-production reads

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0219-validated-installation-only-reader](../adr/0219-validated-installation-only-reader.md) | Status: implemented and locally qualified, 2026-10-25; installed activation is |

## Specification organization

| Record (full slug) | Opening status cue — inspect source for exact scope |
| --- | --- |
| [0217-feature-oriented-specification-authority](../adr/0217-feature-oriented-specification-authority.md) | Status: documentation organization approved by the owner, 2026-10-22. |
