# 0179 — RunView-local checkpoint evidence

Status: owner-authorized October 15, 2026; implementation, 99 focused checks and
Root's independent stable-candidate review accepted (audits `ab9aaa`, `04ac6c`,
`baaf6e`). Functional acceptance only; no measured gain or new whole/release qualification.
Tracked in the [Python speed track](../roadmap/2026-10-14-python-context-and-workers.md).

## Problem and evidence

`AutopilotPersistence.view_in_session` validates and serializes each loaded
checkpoint's evidence for the public checkpoint list. Its activity projection
then validates the same in-memory evidence again. The intervening attempt SELECT
does not refresh or mutate those checkpoint rows. The evidence and nested geometry
validators check supplied data without mutating the source or consulting ambient
authority. This duplicated typed construction belongs to view composition.
No timing improvement has been measured or inferred from this duplication.

## Decision

One RunView construction owns a private projection containing the canonical public
checkpoint list and typed (loaded row, validated evidence) pairs. Validate then dump
each row before proceeding to the next row. Both public checkpoints and activities
consume that projection; there is no raw/unchecked activity alternative. Discard
all projections on return or error. Each later view constructs its own projections.
Consumers must not mutate the validated evidence or checkpoint rows. Changes to
validator side effects, serialization or intervening mutation require reassessment.

Preserve checkpoint/frame SELECTs and their order, material closure and flushes,
policy validation before checkpoint parsing, per-row parse/dump interleaving,
fresh attempt SELECT and snapshot validation after checkpoint serialization,
and frame validation after activity construction. Keep existing transaction,
ordinary-open, corruption, claim and following-read boundaries and exact public
fields/serialization. The SQL remains fresh; projection reuse adds no snapshot
guarantee or host/process observation.

## Rejected alternatives and guardrails

Do not coalesce closure calls: command before/after checks cross writes; receipt
segments cover disjoint tables; production/full closures have different authority.
Review-bundle closure reads can cross independently visible commits under an
ordinary read lease. No session/global cache, cross-view retention, weaker
checkpoint projection, caller validation flag or model construction bypass applies.

Focused guards must delegate real validation/serialization, cover every loaded
checkpoint including no-job/geometry rows, preserve output and failure order,
and prove successive, failed and reentrant views cannot share derivations.
Reuse activity, claim freshness/rollback, ordinary-open corruption, geometry
lineage and receipt freshness owners. Functional checks establish no performance,
whole-suite, release, hosted-CI or product acceptance claim.
