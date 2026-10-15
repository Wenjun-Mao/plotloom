# 0167 — One resolved context per Storyboard owner read

Status: accepted by the owner on October 14, 2026; implemented with focused
regressions, independent read-only review and the full local gate at `4bc1d62a`.
Measurements and separate publication/hosted status are in the
[Python follow-up](../roadmap/2026-10-14-python-context-and-workers.md).

## Problem

Storyboard context resolution calls Script's stale check, which resolves the
upstream context, and then resolves the same context again. Reading retained
accepted and replacement candidate state repeats that work. The duplication is
inside one uninterrupted owner operation, not an invitation to reuse authority
across operations. A shared SQLAlchemy session is not a snapshot guarantee.

## Decision

Extract Script's existing ordered binding comparison into a pure helper.
Storyboard resolves Script once and applies that comparison plus the existing
full-binding equality fallback. Preserve the distinct missing/unaccepted
Script, stale upstream context and stale binding diagnostics and their current
exception boundaries.

Within one Storyboard `get_state` read, resolve one base context if accepted or
candidate data exists; resolve none when both are absent. Project that base
separately into each frozen binding's cut-duration and optional render-contract
mode. An omitted historical render contract remains omitted. Retained accepted
staleness must not replace a current candidate's diagnostics.

The resolved value is local to that operation. Separate reads, mutations,
admission, dispatch, steps, commits and rollback always keep their existing
fresh resolution boundaries. Script's own state reader and Production Bridge
orchestration are not broadened by this change.

## Alternatives and consequences

Global/session caches and already-validated flags are rejected: they require
invalidation semantics and can carry stale authority across operations.
Caller-side validation bypasses or test-only stubs would hide the repeated
production work. The owner is the narrowest layer that knows which comparisons
share one read and which policies must remain independent.

Tests must preserve ordered diagnostics, all three Script error mappings,
independent accepted/candidate timing and render modes, zero/one resolution
counts, successive-read freshness and write-boundary refusal. Measure quiet
unprofiled costs before making speed claims; this decision does not establish
the complete-suite 85-percent target or change test coverage/concurrency.

## Art/Script upstream extension — October 14

The owner-approved operation-local scope also covers duplicate resolution inside
existing Art and Script `_context` calls. Art resolves Cast, then resolves it
again through `_stale`; Script resolves Art through `_stale`, then resolves Art
again. This multiplies into four Cast resolutions per normal Script context and
reaches image inventory through Storyboard/Bridge. Historical image-flow cost
guides prioritization only. Independent Sol/High design review supports this
bounded extension.

Move each Cast/Art post-resolution stale-comparison body unchanged into private
`_stale_against(session, project_id, current, binding)`. It resolves no context,
caches nothing and preserves ordered binding differences, then current Brief/
render-style checking, then section comparison. The existing field comparator
remains pure; Brief/style checks retain their actual read/error behavior. Keep
each `_stale` catch limited to its fresh `_context` call, then delegate.

Art resolves its initial Cast context before accepted-Cast readiness, compares
against that value, and retains its existing tuple/binding output. Script first
checks accepted-Art head/row and validates its frozen ArtBinding, then resolves
Art once. Only an expected error from that resolution maps to the existing
`accepted_art_not_current` diagnostic, before target validation. Comparison/style
errors stay outside that catch. Preserve the generic error's absence of a
chained resolution exception. Script still constructs its result from
`accepted.binding`; the accepted receipt owns the frozen render contract, which
is absent from Art's newly resolved base binding.

Do not coalesce `get_state` accepted/candidate comparisons, inventory's separate
owner reads, review-bundle reads, writes, transactions, admission, dispatch,
controller steps, commits or rollback. No session snapshot guarantee, global
cache, caller bypass or copied-native-resume behavior is introduced. Tests must
prove exact diagnostics/error precedence, zero/one resolution counts, preserved
frozen outputs, separate-call freshness and normal read/write refusal after
mutation. Speed and combined full qualification require separate evidence.

The extension is implemented with 32 new focused guards, 67 existing contract/
style/lifecycle regressions and four fresh downstream image/recovery/handoff
cases (103 distinct passes). Independent Sol/High design and Sol/Medium stable
code reviews found no actionable finding. Each real Art/Script context call now
resolves Cast once; separate calls and accepted/candidate evaluations stay fresh.
No speed comparison or combined full qualification has run. Frozen refs, exact
native inventory, selectors and log hashes are in the Python plan.
