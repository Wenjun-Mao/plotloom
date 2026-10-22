# 0171 — Historical Python timings are scheduling predictions

Status: accepted for the owner's October 14 scheduling preapproval, after an
independent read-only design review. Implementation, 141 affected focused checks
and independent stable code review are complete. Full local qualification and
fresh timing remain pending in the [Python plan](../roadmap/2026-10-14-python-context-and-workers.md).

## Root cause

ADR 0160 discarded every duration weight after any executable or native-case
change. That conflated captured-run provenance with prediction eligibility:
ordinary development could require an extra complete run solely to restore
balanced scheduling. The retained 1,911-case capture had 302s/779s of phase
work under case-count allocation versus predicted 540s/540s by duration.
Fresh native collection, exact current file assignment and ADR 0168's worker
case-ID completion already own execution coverage independently of weights.

## Decision

Keep schema 1 and all captured fingerprints immutable. Validate every row,
including removed files, before considering reuse. Require the same host/Python
fingerprint; mismatch falls back explicitly to case counts. Missing history,
empty rows or no overlapping current file paths also use that fallback.

For overlapping files, retain a historical total when the case count matches;
otherwise scale it by current/historical case count. Estimate each new file
from its current count times the median historical per-case duration among
overlapping files. Removed files do not enter the estimator or assignments.
Keep the deterministic greedy whole-file algorithm and tie-breaking.

Report `duration` only when all captured fingerprints, file coverage and counts
match; otherwise report `historical-duration`, every mismatch reason and the
retained/scaled/estimated/ignored file counts. Both are predictions, not fresh
performance measurements. Never rewrite provenance just to make weights current.
Validate finite aggregate history, positive finite estimates and finite total
predicted work; arithmetic overflow or underflow fails explicitly rather than
silently choosing another algorithm.

## Consequences and alternatives

This supersedes only ADR 0160's strict duration-freshness eligibility clause.
Current native IDs remain the sole selection authority. Exact/disjoint file
coverage, completion proofs, genuine tests, isolated roots, filter refusal,
failure propagation, process cleanup and the release default of two do not
change. Count scaling and the median are approximate; poor estimates can hurt
balance but cannot qualify missing tests. The already balanced 578.639s run is
not a promised speedup baseline, and this does not establish the 85% target.

Reject dropping coverage guards, automatically promoting weights, per-file
source hashes, new orchestration and a warm-up run on every edit. Guard source
and inventory drift, changed counts, new/removed files, host mismatch, malformed
rows even when unused, numerical extremes and deterministic exact coverage.
Keep scheduling tests in their own owner and verify the real runner's historic
reporting and refusal of old case-ID completion proofs. Fresh full qualification
records actual wall time; no hosted CI or live activation is authorized.
