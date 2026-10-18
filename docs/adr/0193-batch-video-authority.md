# 0193: Frozen batch video authority

Status: implementation decision, 2026-10-18

## Problem

Per-shot H3 jobs and exact segment proposals exist, but there is no durable
all-routes batch scope, assistant directions owner or atomic video-pack decision.
Treating missing selection as missing generation risks duplicate paid work.

## Decision

The author owns saved story, approved frames, geometry choices, displayed English
directions endorsement, bounded Start and final audiovisual confirmation. The
assistant drafts complete English field renderings from exact frozen sources;
it never asserts human review. Trusted code inventories unique production shots,
binds lineage/timing/profile/backend/seeds, compiles prompts, validates manifests,
claims dispatch and validates media/proposals. One typed batch endorsement is
consumed by shared H3 preparation/dispatch readers, not fabricated per-shot notes.

The original English endorsement proves immutable source/direction/prompt facts;
its originating batch need not remain running. Fresh dispatch separately requires
the current explicitly started batch that links the exact job, its installation
grant, unchanged manifest/source/selection scope and caps. A successor may adopt
an unsubmitted job from a cancelled predecessor without rewriting its snapshot
or reviving the predecessor. A merely prepared, paused, cancelled or stale
successor confers no execution authority; an existing/unknown attempt is never
resent.

Project facts link existing jobs and unselected segment proposals. Application
ownership fences execution and fresh dispatch; copies/restores cannot inherit
that authority. Human control has a separate CAS revision from progress facts,
so observed progress cannot make Pause unusable or replay an older control intent.
Existing job accounting remains ADR 0045's durable claim-before-
transport protocol. Pause stops new submissions; known predictions remain
observable even after a cancelled batch is superseded. Cheap inspection of those
existing facts gates controller work; settled review waits do not trigger repeated
authority/media scans. Every admitted execution/reconciliation step still opens
with full authority validation. Progress counts project existing execution states;
full gallery eligibility and byte proof remain with the review owner. Explicit native window
preparation updates the latest unconfirmed batch proposal and its review CAS;
it never rewrites a completed confirmation. UNKNOWN retains reservations and never permits replacement. All
targets preflight before Start; edits fence unsent work. No automatic paid retry.

One explicit human confirmation atomically selects the full proposal set and
records an immutable versioned receipt with truthful unnamed attribution. Kept
selections are unchanged. Immutable audiovisual confirmation binds segment identity
and bytes; a later selection-CAS bump preserving that exact segment (such as
reopening a rejected alternative) does not rewrite or invalidate the receipt.
Late rejection/staleness/unreadable media rolls back
everything. Saved confirmation is distinct from subsequent refresh failures. Its successful
refresh explicitly invalidates the existing manual player read owner. Foreground
reveal intent starts at the initiating action, before asynchronous requests;
visibility/navigation invalidation cannot be undone by a late acknowledgment.
Preparation reveal intent also belongs to the exact initiating run. Initial
Start binds that identity from its acknowledgment without rearming foreground
intent; polled replacement, cancellation, takeover or staleness withdraws it.
A late command acknowledgment cannot restore withdrawn intent. Material handoff
uses a separate completion purpose so an awaiting-review poll cannot consume the
intent reserved for its saved confirmation.

## Alternatives and guardrails

Reject browser click loops, extending frozen pre-video policy, per-shot fabricated
consent, automatic selection and invented cross-database atomicity. Reuse current
Codex Exec supervision for a narrow directions preparation stage. Preserve
manual workflow and exceptional rejection reopening. Provider fakes cover all-
routes deduplication, caps, restart, contention, copies, pause, UNKNOWN, stale CAS
and whole-pack rollback before any bounded live qualification.
