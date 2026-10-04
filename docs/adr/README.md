# Architecture decision records

The [roadmap entrypoint](../roadmap/README.md) owns current delivery scope.
ADRs record decisions at their adoption boundary; a later scoped decision may
supersede one clause without erasing the earlier record. For a live instruction,
follow the latest applicable decision and its current source owner, not an old
literal in an otherwise useful historical ADR. The [simplification disposition
register](../roadmap/2026-09-23-simplification-dispositions.md) tracks audit
leads separately from approved work.

| Current question | Decision chain and source owner |
| --- | --- |
| Canonical entity identity, revisions, and authoring drafts | [0004](0004-canonical-generation-contract.md) defines the original stage model; `src/plotloom/canonical_schema.py` owns current `StableId`. [0014](0014-project-lifecycle-and-workbench.md) records explicit canonical Save; [0040, project-folder storage](0040-project-folder-storage-boundary.md) and [0043](0043-project-folder-close-quiescence.md) own durable draft receipts and close quiescence. Browser buffers are provisional. |
| Project-folder runtime and persistence | [0040, project-folder storage](0040-project-folder-storage-boundary.md) → [0046](0046-production-project-folder-runtime.md) → [0048](0048-retire-shared-repository-runtime.md). [0042](0042-persistence-capability-composition.md)'s shared `legacy_repository.py` exception is historical; `src/plotloom/persistence/project/repository.py` is the current composition owner. |
| Known project identity and admission failures | [0110](0110-known-project-identity-before-admission.md) separates manifest identity lookup from availability-filtered catalog discovery; target-home admission retains busy/corrupt/closed distinctions. |
| Project recovery | [0043](0043-project-folder-close-quiescence.md) and [0044](0044-portable-project-folder-recovery.md); the current manifest/schema admission code, not an old format number in prose, decides which folder opens. |
| Brief to Source entry and declaration ownership | [0058](0058-f1a-source-outline-review-contract.md) established F1A; [0085](0085-brief-to-source-entry-and-optional-declarations.md) makes Brief an editable Source draft seed and declarations optional while retaining historical values. |
| Outline candidate reading | [0086](0086-trusted-outline-candidate-reader.md) owns isolated interactive original reports, JSON fallback and upstream structural-label boundaries. |
| Branch editor next step | [0087](0087-branch-save-apply-continue.md) distinguishes save, apply and navigation to Characters using current saved-map and graph state. |
| Creative task execution identity | [0088](0088-frozen-creative-execution-identity.md) binds preparation-time skill identity in trusted project persistence; refresh does not substitute current checkout hashes. |
| Native specialist availability and wake | [0095](0095-persistent-creator-workbench.md) owns the persistent Mac/Docker deployment; [0096](0096-native-specialist-deep-link-wake.md) separates queue admission from a documented desktop-open request without transferring execution ownership. |
| Isolated native transport composition | [0098](0098-isolated-workbench-native-transport.md) derives the test server, bridge allowlist and outbound shim from one runtime owner; unknown dispatch reservations remain authoritative. |
| Art render-style authority | [0094](0094-author-selected-art-render-style.md) freezes author-selected style and Brief direction, retaining upstream gates through a shared art adapter. |
| Additional art-reference candidates | [0097](0097-art-reference-additional-candidates.md) separates a new requirements draft from a frozen delivered request, retaining existing images and reference choices. |
| Source-review currentness in the workbench | [0099](0099-source-review-activation-currentness.md) revalidates visible retained review state on navigation and same-project server refresh while preserving editor buffers. |
| Creator guidance and visual hierarchy | [0111](0111-journey-first-creator-presentation.md) supplies next-step explanations from existing owners, shared presentation roles and a Chinese Creator's Manual without duplicating readiness or relaxing authority. |
| Character-review presentation | [0089](0089-cast-review-text-presentation.md) separates exact inference suffixes losslessly and preserves label selection without removing normal field activation. |
| H3 creation and output | [0038](0038-h3-gateway-durable-fifo-dispatch.md) and [0039](0039-h3-gateway-managed-output-retention.md) established FIFO and retention. [0040, private H3 image ingestion](0040-private-h3-image-ingestion.md) is the other `0040`, a historical two-step input contract. [0050](0050-unified-h3-generation-contract.md) removed public asset/job creation routes; [0066](0066-h3-qualified-job-duration-contract.md), [0068](0068-h3-reproducibility-and-qualified-recipes.md), [0069](0069-h3-explicit-sampling-recipes-and-profile-cutover.md), and [0070](0070-h3-quality-resolution-contract.md) refine current admission. `src/plotloom/video_backends/minimax_h3/adapter.py` owns the catalog marker and qualified duration set. |
| Creator destructive/review confirmation | [0101](0101-accessible-creator-confirmations.md) owns DOM confirmation, frozen domain targets, cancellation and unattended UI preflight. |
| H3 reviewed seed control | [0102](0102-explicit-h3-review-seed.md) exposes exact browser-safe seeds and invalidates source review and idempotency when edited. |
| Retained candidate across media refresh | [0103](0103-retained-candidate-read-reconciliation.md) separates explicit retention from authoritative binding transitions while preserving read withdrawal. |
| Deployed frontend freshness | [0104](0104-workbench-static-revalidation.md) requires revalidation of the stable-name `/v2` frontend build, including conditional 304 responses. |
| H3 review across unknown media reads | [0105](0105-h3-review-media-read-recovery.md) preserves creator seed/English buffers while withdrawing authorization and requiring exact source revalidation. |
| Image specialist blocked before generation | [0106](0106-reviewed-pre-generation-image-terminal-outcome.md) admits explicit, pin/request/dispatch-bound no-output terminal proof without cancellation-only or idle-only release. |
| Reviewed production presentation | [0100](0100-reviewed-production-presentation.md) owns exhaustive source review, physical/visible/runtime separation, exact source timing, accepted F5 binding and explicit isolated H3 composition. |
| Post-install shot presentation changes | [0107](0107-shot-production-presentation.md) owns source-bound per-shot author amendments, trusted exact-text provenance, shared image/H3 projection and shot-scoped currentness without rewriting accepted source. |
| Rejected H3 take reconsideration | [0108](0108-explicit-h3-rejected-take-reconsideration.md) owns an explicit reasoned reopen event, selection-revision CAS, preserved history and active playback continuity. |
| Production playback timing | [0082](0082-proposed-production-playback-timing.md) distinguishes authored shot time, frozen request, measured take and a reviewed segment. The bounded synthetic-media implementation is approved; the H3 original-output contract remains intact. |
| Capability tracking and delivery | [0008](0008-capability-based-adoption-tracking.md)'s tracking method survives, but its named [matrix](../roadmap/archive/superseded/2026-09-02-capability-matrix.md) is archived. Use the [roadmap](../roadmap/README.md) for active work and acceptance. |
| Verification tooling | [0081](0081-narrow-source-static-and-api-lint-checks.md) separates checked source-bundle browser evidence from installed-wheel packaging evidence and keeps Ruff scoped to API F401 findings. [0109](0109-bounded-browser-ci-evidence.md) bounds independent browser shards, preserves failure evidence and distinguishes filtered diagnostics from the full release gate. |

Two files retain the historical number `0040`; cite each by its full slug and
link, never by number alone. This index is a navigation aid, not a declaration
that every unlisted ADR is obsolete or that a past evidence identity should be
rewritten to match current code. The full decision corpus is this directory.
