# Reliable creative workflow: five-step delivery contract

Revision 1 — **Approved**, 2026-09-15.

## Outcome and authority

Deliver a reliable two-shot creative workflow, then a small pause-and-choose
branching story. The creator primarily selects and refines proposals, with detailed
editing available. Initial visual target: cinematic realism.

This is the authoritative current delivery plan. The director owns scope and
acceptance; coordinators own bounded implementation. Approval of this plan is not
permission to bypass a user pause, unresolved source ownership, or unsafe data
operations. This documentation checkpoint starts no implementation assignment.

The five steps below are ordered. Supporting work must serve the current step or a
demonstrated blocker. Technical breakdown may change within scope; material changes
to outcome, acceptance, risk or authority require user agreement and a new revision.

## Current baseline

Read-only reconciliation at `57c28f7`: working tree clean; local main matched the
locally recorded origin/main. This observation did not fetch, run product suites,
or independently requalify live services.

- Project-folder runtime, durable drafts, close/reopen, snapshot/restore and
  project-owned generation/media lifecycle are implemented. The old shared
  repository facade is removed, but coverage-preservation acceptance is incomplete.
- The historical regression inventory records 3 verified and 323 pending entries.
  Pending means unresolved disposition, not necessarily missing behavior or a bug.
- H3 V4 direct creation is implemented. The [live-canary receipt](../verification/2026-09-15-h3-unified-contract-live-canaries.md)
  records gateway T2V and start/end I2V success, not Plotloom creative acceptance.
  Plotloom authoring still uses its approved five-second I2V path.
- The controlled retained-data archive/settings/configuration switch is not
  established as complete by the storage roadmap. Verify actual state before acting.
- Earlier unaccepted source commits are now ancestors of pushed main following the
  separate H3 work. Being pushed does not settle their acceptance gaps.

## Delivery and acceptance

| Step | Deliverable | Acceptance evidence | Exclusions |
| --- | --- | --- | --- |
| 1. Reconcile current state | One accurate roadmap and concise durable local policy | Current code, recorded evidence, pending acceptance and historical claims distinguished; one progress table | No new tracker framework or duplicate status documents |
| 2. Close verification debt | Trustworthy coverage of current generation, authoring/control, media and qualification contracts | Missing scenarios ported to explicit owners; equivalent assertions cited precisely; genuinely obsolete contracts justified; focused review and stable executable gates | No numeric test-count target, blanket mappings, legacy facade restoration or broad redesign |
| 3. Finish storage transition | Safe archived old working sets and usable project-local storage configuration | Quiesced writers; exact inventory, verified backups, preserved settings/accounting/credential sources; reopen and restore without old paths | No guessed project-content migration, compatibility layer or retention automation |
| 4. Prove two-shot creation | One protagonist, one short scene, two reviewed adjoining clips in Plotloom | Synopsis → storyboard → consistent keyframes → H3 clips → sequential playback → close/reopen/restore; retained lineage and genuine audiovisual review | No general media platform, T2V authoring UI, broad duration controls or additional backends |
| 5. Add pause-and-choose | Small playable branching audiovisual sequence | Node sequence ends and holds its last frame; explicit choices follow the selected edge; tested ending/replay/navigation behavior | No timed choices, implicit default choices, full video editor or broad story-scale expansion |

### Step 2: close contracts, not inventory rows

Use four groups: generation; authoring/control; media; qualification tools.
For each, identify required current behaviors, inspect existing tests, directly port
missing scenarios and retire only individually obsolete contracts. Preserve original
fault triggers and required/forbidden outcomes; a happy-path test is not equivalent
to a failure-boundary test. Existing tests may cover multiple old cases when their
assertions genuinely do so. Unresolved mappings stay pending.

Include the H3 V4 test changes in media review, especially queueing, restart,
dispatch uncertainty and retention. Gateway canaries do not substitute for these
failure-path checks. Do not reintroduce removed public routes to preserve old fixtures.

Run focused checks during implementation, an independent scoped review on stable
work, and broader gates proportional to the changed contracts. Use the established
locked Python, frontend, browser and installed-wheel checks; record actual commands
and gaps. Do not repeat the entire suite after every small test edit. Before step 3,
all required current contract groups need a defensible disposition and stable gates.

### Steps 3–5: protect data and demonstrate the product

Step 3 follows the [storage plan](project-folder-storage-plan.md)'s operational
boundaries. Reconcile changes made by other owners first. Preserve exact archives,
credentials and accounting identities; do not infer authority to delete unrelated
files or modify gateway storage. Escalate ambiguous targets or irreversible choices.

Step 4 starts with a small fixed story and reviewed inputs, not a wide batch.
Assess identity, action continuity, dialogue/voice, motion and audio across the cut.
Track presence of audio separately from audiovisual suitability. Use observed clip
duration for playback without silently rewriting authoritative story timing.
Director/reviewer performs routine checks; ask the user only for material creative
choices or judgments that cannot be established from available evidence.

Step 5 builds on that usable sequential workflow. Keep the broader
[product-direction ADR](../adr/0026-story-to-playable-product-direction.md) and
[historical Alpha roadmap](story-to-playable-alpha.md) as context, not authorization
for deferred features. Two-shot or branching acceptance is not automatically formal
M1-C quality qualification; retain that distinction in reports.

## Execution and drift controls

- Assignment brief: step, concrete outcome, evidence, exclusions, stopping condition.
- New finding: current blocker, deferred follow-up, or proposed direction change.
  Only demonstrated in-scope blockers expand the immediate task.
- After two unsuccessful attempts at one criterion, stop repeating the approach.
  Record root cause, proposed method change and a smaller observable outcome before
  another dispatch. No automatic new coordinator/audit cycle.
- Update the table below after accepted checkpoints. Record implementation,
  verification and acceptance separately. Partial commits are preserved but do not
  turn their parent milestone green.
- No routine user confirmation between authorized steps; user pauses still override
  continuation. Material tradeoffs and plan changes return to the user.

## Progress — single current tracker

| Step | Status | Evidence | Remaining blocker | Next action |
| --- | --- | --- | --- | --- |
| 1 | Documented; director documentation checks complete | This revision; local AGENTS consolidation; current entrypoint | None for documentation; no product requalification claimed | Resume step 2 only when implementation is authorized |
| 2 | Complete — all four current contract groups director-accepted and pushed; media safety closeout `889d19f` accepted | [Coverage summary](../verification/2026-09-14-retained-runtime-coverage-summary.md); accepted three-scenario slice `01874da`; [generation receipt](../verification/2026-09-15-step-2-generation-contracts.md); [authoring/control receipt](../verification/2026-09-15-step-2-authoring-control-contracts.md); [qualification-tools receipt](../verification/2026-09-15-step-2-qualification-contracts.md); [media/H3 receipt](../verification/2026-09-15-step-2-media-h3-contracts.md) | Historical pending inventory rows remain unresolved by design; this does not claim Alpha, live, or creative qualification | Use the accepted current-contract baseline for the separately controlled storage transition |
| 3 | Preflight complete — no cutover performed | [Storage plan](project-folder-storage-plan.md), implemented recovery contracts, and [read-only preflight](../verification/2026-09-15-step-3-storage-preflight.md) | Director must resolve legacy profile/selection and pilot-accounting export, then establish writer quiescence and verified archive evidence | Run one controlled archive/configuration transition only after those blockers are resolved |
| 4 | Partial prerequisites implemented; not accepted | Image/reference workflows; [H3 canaries](../verification/2026-09-15-h3-unified-contract-live-canaries.md) | Current end-to-end creative and storage proof | Deliver and review the fixed two-shot journey |
| 5 | Planned | ADR 0026 pause-and-choose direction | Accepted sequential workflow | Implement the small branching player after step 4 |

## Deferred

T2V authoring controls, broader duration/end-frame controls, new backend expansion,
automatic image-specialist transport, seven-day cleanup, full editing/mixing,
timed choices and general collaboration are not prerequisites for this sequence.
Existing gateway capabilities and exploration evidence remain intact.
