# 0192: Inspection and authority admission

Status: implementation decision, 2026-10-18

## Problem

Every image read reopened and fully admitted every retained review. A fresh
42-shot, five-reference project open performed 210 geometry validations and
420 artifact reads (1.29s profiled; subsequent opens 0.87s and 0.80s). The gallery
amplified this work per pixel request. This belongs to storage admission, not a
browser timeout or a weaker approval validator.

## Decision

Name two admissions: inspection checks confined regular paths, exact live SQL
schema (including WAL), project identity and lifecycle; authority additionally
validates all retained current-format evidence. Authority remains the default.
Inspection cannot attest approval, provenance or readiness. Requested media
bytes retain their content-addressed integrity checks. Use inspection for raw
asset/catalog reads, and one authority read for consolidated gallery evidence.
Writes, dispatch, approvals, snapshot/export and restore keep full admission.

There is no cross-request validity cache: SQL revisions and mtimes do not prove
asset bytes. Any bounded proof reuse must end with its exact read snapshot and
be invalidated by writes. Immutable SQL-derived scalars (canonical gate passing
and material/production closure hashes) may be reused only within the exact
request, connection, outer/nested transaction, mutation count and SQLite
data-version. This retains unchanged assertions while avoiding repeated gate
decoding and whole-closure construction for every frame. Rollback creates a new
cache identity; this SQL-only reuse does not certify file bytes. Corruption after inspection must fail authority and
requested-byte reads independently.

## Alternatives and guardrails

Reject global TTL/revision caches, gallery-only admission bypasses and relaxed
lineage checks. Preserve confinement/schema/WAL/replacement/lifecycle regressions
and out-of-band same-size asset corruption tests. Measure end-to-end gallery
readiness separately from this storage measurement.
