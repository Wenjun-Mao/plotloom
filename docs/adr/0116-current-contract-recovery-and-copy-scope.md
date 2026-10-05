# 0116 Current-contract recovery and duplicate scope

Status: Owner approved, 2026-10-04. See the six-repair roadmap assignment.

## Problem

UI availability predicates collapsed retained evidence into unavailable transitions:
Outline cancellation kept its first candidate but hid preparation; stale bridge
proposals hid pre-install refresh; temporary project reads forced draft disposal;
failed choice reads looked indefinitely pending. Directory Copy hid its actual
canonical-prefix boundary. These are state/admission contracts, not generation or
creative-acceptance problems.

## Decision

Expose explicit preparation after Outline cancellation using confirmed Source;
keep old records/pins and independent send/accept/terminal reconciliation. Bridge
state exposes `hasInstallation` independently of source currentness. Fresh proposals
are limited to before first installation, refused during queued/dispatched/unknown
intent execution, and require new current intent/presentation review. Local edits
must be copied and explicitly abandoned before fresh preparation. Never replace
installed canonical heads; retain the empty-head first-install guard and history.

Browser author drafts distinguish temporary failed reads, project-authority 404,
and confirmed archival. An auxiliary endpoint failure does not prove deletion.
All retained content remains inspectable as read-only JSON with project/scope/base
revision, copy/export and keep-for-retry. Keeping authorizes navigation and retains
sessionStorage; it does not apply a draft or unblock writes to an unverified target.
Only a successful exact project aggregate clears unverified recovery state. Before
restoring, read project and stage authority again and require active ownership and
the exact base revision. Changed versions use the existing explicit conflict flow;
archived/deleted targets stay unwritable. Writes retain existing CAS. Export is a
text recovery artifact, not an import promise or full-project clone.

Directory duplication explicitly confirms Brief plus the contiguous ready canonical
prefix. Show the returned `copiedThrough`/`omittedStages` receipt, including excluded
source-review work, media, approvals and browser drafts. Idempotency/revisions and
original preservation remain unchanged; no approval transfers.

Choice reads expose loading, failed and stale/mismatched ownership. Read-only retry
belongs to current playback/media/route/source identity; project changes, superseded
attempts and unmount invalidate old responses. Choices remain gated by exact edge
ownership, current installed storyboard and node completion.

## Alternatives and consequences

Automatic resend/accept, draft deletion on generic failure, silent merging, full
creator-project cloning, post-install replacement and allowing unverified choices
were rejected. Recovery is explicit and bounded to existing owners. No new provider,
acceptance authority, routing, snapshot restore or Chinese manual changes.

## Guardrails

Positive recovery and refusal/race tests cover first cancelled outline, stale
pre-install proposal with local edits, temporary/missing/archived drafts with keep
and exact revalidation, actual copy receipts and failed/stale choice retry. These
fixture checks do not establish human usability or live media acceptance.
