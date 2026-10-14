# 0167 — One resolved context per Storyboard owner read

Status: accepted by the owner on October 14, 2026; implemented with focused
regressions and independent read-only review. Full qualification remains
pending in the [Python follow-up](../roadmap/2026-10-14-python-context-and-workers.md).

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
