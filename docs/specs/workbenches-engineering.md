# Workbenches: agreed engineering contracts

Consolidated 2026-10-22; [product intent](workbenches-product.md) is independent of
current implementation. The source records below own detailed schema/algorithm
choices; their status is not a claim that native acceptance completed.

| Contract | Required guarantee | Decision chain / coverage |
| --- | --- | --- |
| Graph authority | Both modes use one typed `story_graph/root` draft, authenticated planner seed/author provenance and sole source-bound admission; canonical read-only never fabricates these | [0121](../adr/0121-current-source-graph-authoring.md), [0122 amendment](../adr/0122-creator-workspace-presentation.md#workspace-presentation-is-independent-of-write-authority-2026-10-22); C02/C28/P05 |
| Save / confirm / apply | Incomplete draft save is recoverability. Confirmation binds exact current source/outline/map; application checks draft/base/context/content and consumes it atomically. No generic competing graph writer | [0121](../adr/0121-current-source-graph-authoring.md), [0155 handoff](../adr/0155-recommended-creative-workflow-guide.md); C17/C31/C35/C53 |
| Commands and preview | Immutable acknowledged draft revision + typed command + result/impact; confirm recomputes under lease/CAS. Preserve IDs/effects/untouched targets. Explicit join/type deltas; stale/cancel/refusal zero partial write | [0121](../adr/0121-current-source-graph-authoring.md), [0128](../adr/0128-graph-edit-safety-diagnostics.md); C09–C26/C48–C50 |
| Current read authority | Explicit loading/ready/failed; only current successful editable graph read admits new edits/commands/timer/blur/drain writes. Retain buffer/receipt on failure; GET-only recovery; ready-stale explicit recovery distinct | [0145](../adr/0145-current-read-authority-for-graph-and-directory.md), [0133](../adr/0133-owned-project-read-acknowledgement.md); C34–C36/C51 |
| In-flight writes | Valid already-admitted ACK/outcome remains valid after read withdrawal; empty drains need no graph read. Acknowledgement basis cannot be guessed from a click or server observation | [0145](../adr/0145-current-read-authority-for-graph-and-directory.md), [0151](../adr/0151-local-project-command-admission.md); C35/C36/C51 |
| Session ownership | Project/epoch/read generation/latest ACK/CAS reject late work. Async flush cannot dispatch under obsolete owner; old completion cannot unlock a newer operation or overwrite newer selection | [0121 amendments](../adr/0121-current-source-graph-authoring.md), [0148](../adr/0148-workspace-owned-branch-mutations.md); C27/C36/C52 |
| Presentation storage | Versioned private project-scoped shared selection and Creator geometry outside draft/approval/production fingerprints; canonical selection restores only existing IDs, otherwise current opening; no author revision for viewing | [0122](../adr/0122-creator-workspace-presentation.md); C03/C28/C45/C46/C48 |
| Pro visual session | Supported node positions and pan/zoom survive mode unmount/remount within the active project session; project change/reload/close-reopen reset only that visual state. No durable layout storage, author write, new read-only dragging or shared-selection reset | [0122 lifetime](../adr/0122-creator-workspace-presentation.md#owner-approved-professional-visual-state-lifetime-2026-10-23); C57 implemented and locally exercised at `dd71f079`; [qualification and limits](../verification/2026-10-23-workbench-spec-alignment.md#final-local-frontend-qualification), activation/hardware/owner acceptance separate |
| Source read publication | One workspace source-review owner; successful owned confirm/apply publishes returned review before independent refresh; late/failed operations cannot publish. Failed follow-up does not erase successful write outcome | [0155](../adr/0155-recommended-creative-workflow-guide.md), [0145](../adr/0145-current-read-authority-for-graph-and-directory.md); C28/C35/C51/P06 |
| Story projection | Exact section→episode→ordered scene occurrence; preserve complete upstream JSON; revision/hash-bound replacement; immutable original reports separate from edited annotation | [0123](../adr/0123-node-context-story-production-workflows.md), [0126](../adr/0126-static-script-report-presentation.md), [0147](../adr/0147-owned-pinned-report-renderers.md); C27/C40/C54 |
| Review authority | Candidate freshness and retained accepted-content currentness are independent. Binding mismatch/read failure cannot authorize reopening, continuation or production | [0149](../adr/0149-independent-accepted-review-state.md), [0132](../adr/0132-creator-ui-reading-boundaries.md); C42/E18.1; 0149's implementation status remains historical, not promoted here |
| Footage | Explicit membership, default route-only for decision/join, schema/validation/frozen timing hashes agree. No inferred inclusion from prose; route-only cannot satisfy a footage-only state contract | [0120](../adr/0120-explicit-node-footage-mode.md), [0121](../adr/0121-current-source-graph-authoring.md); C44/E13 |
| Production identity | Exact accepted scene/cut coordinates and installed shot IDs, no location/index guessing; current installation separate from latest proposal; no handoff on missing/stale/unknown binding | [0123](../adr/0123-node-context-story-production-workflows.md), [0138](../adr/0138-one-current-story-explicit-rebuild.md), [0150](../adr/0150-review-bound-production-bridge-acknowledgement.md); C40–C43/E12.2 |
| Explicit rebuild | Freeze replacement heads/admission/hash + proposal CAS; atomic bundle install and source-owned graph/Bible rebind; fresh relevant approvals; retained assets not automatically eligible; no selective-video-reuse claim | [0138](../adr/0138-one-current-story-explicit-rebuild.md); E12.1–E12.4/E18 |
| Directory and working input | One typed project-draft CAS owner per scope/entity; raw incomplete input, exact lost-receipt reconciliation and atomic explicit adoption; verified per-document journals with addressable retained namespaces; all-owner preservation and reconnect; route-epoch fencing. Optional Freeze drains admitted writes and holds true read-only browse/play admission, without resume/reconcile. Restore retains Frozen; no Close/save-close/force-exit surface | [0218](../adr/0218-working-input-autosave-and-optional-freeze.md); C58; [retained inventory](../roadmap/2026-10-24-autosave-and-project-freeze.md#execution-inventory--source-review-checkpoint) |
| Lifecycle and dispatch | [0218](../adr/0218-working-input-autosave-and-optional-freeze.md) replaces routine Close with automatic working-input preservation and optional Freeze; existing owned flights/quiescence/consent/recovery apply; cannot clear unknown reservations, retry uncertain dispatch or infer native cancellation from task state | [0043](../adr/0043-project-folder-close-quiescence.md), [0113](../adr/0113-project-save-close-and-force-exit.md), [0132](../adr/0132-creator-ui-reading-boundaries.md), [0148](../adr/0148-workspace-owned-branch-mutations.md), [0201](../adr/0201-unified-project-deletion-preparation.md); P03/E19–E21 |
| Selective batch replacement | Review, predecessor cancellation and successor creation are separate persisted operations. Exact lineage/CAS/currentness retain rejected history and good siblings; lost acknowledgements reconcile retained state without replay or cancelling the successor. Fresh endorsement/Start remain explicit | [0204](../adr/0204-explicit-rejected-batch-take-replacement.md), [completion plan](../roadmap/2026-10-22-creator-completion-loop.md#revise-selected-takes); distinct from whole-story rebuild |
| Timing and status projection | Response-only immutable run/batch facts, scope-correct milestones and shared effective state; server observation plus monotonic display, no per-second writes/provider polls. Mutable updates/reused media do not establish progress; read failure withdraws status certainty | [0204](../adr/0204-explicit-rejected-batch-take-replacement.md), [timing contract](../roadmap/2026-10-22-creator-completion-loop.md#timing-and-status) |
| Delegated UI QA | Read-only context discovery grants no write authority. Visible project-local opt-in resets on navigation; every write independently validates exact original-runtime scope/current actor. Missing context cannot silently become human approval; portable evidence grants no execution authority | [0198 amendment](../adr/0198-delegated-disposable-qa-authority.md#native-material-handoff-and-browser-context-amendment--2026-10-22), [QA prerequisite](../roadmap/2026-10-22-creator-completion-loop.md#truthful-delegated-qa-prerequisite) |

Routine recovery exposes the exact persisted state and remaining supported action
through creator controls, rather than requiring developer/operator tools. The
separate historical local-slot retirement contract in
[0174](../adr/0174-bounded-fair-codex-exec-pool.md) is an exceptional operator
operation, not ordinary creator recovery or authority to clear uncertain outcomes.

## Verification boundary

The exact-schema rule has a separately approved narrow exception:
[0162](../adr/0162-pre-video-autopilot-authority.md) allows explicit preserving
upgrade from the immediately preceding known layout, with rows/assets/packages/
receipts and operational state retained. Restoring a prior snapshot upgrades only
a verified destination, never the original snapshot bytes; ordinary reads still
reject unsupported layouts.
This is not general compatibility, implicit migration or dispatch authority.

Reuse existing tests/receipts only while their executable inputs are unchanged.
Tests demonstrate exercised conditions, not general agreement or human acceptance.
The workbench [audit ledger](../verification/2026-10-22-workbench-spec-audit.md)
must distinguish source-confirmed behavior, retained browser proof, newly reproduced
deviation and unverified combinations. Documentation-only changes require link,
coverage and consistency checks, not rebuilding frontend assets or running full gates.
Hosted CI is optional and off without a new direct owner request under
[0199](../adr/0199-local-release-qualification.md) and AGENTS.

Ordinary departure and exclusive drainage use separate owner contracts (ADR 0218). A branch mutation already sent and owned by the workspace can continue after navigation, without cancel/replay; this exception carries no editable buffer. Freeze/snapshot/delete still join it and refuse uncertain results. Branch state/draft basis queries use read leases and never initialize absent review heads; creation owns initialization.
