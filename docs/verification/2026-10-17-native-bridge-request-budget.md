# Native bridge request budget correction — October 17, 2026

> Only QA artifacts listed in the [2026-10-25 cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md)
> were retired. References to those artifacts describe historical
> runs, not available files or current launch/recovery instructions.
> Recorded outcomes and limits stand.

## Root cause and owning contract

The real walkthrough reached Bridge Intent with seven scenes, 35 cuts and 42
intent targets. Its complete source/target envelope was 74,043 canonical UTF-8
bytes, above the native 60,000-byte ceiling inherited from API inference. The
narrower API projection was 61,149 bytes. The following native Presentation
envelope was already 250,535 bytes, above 180,000, before saved intent suggestions.
Those are intentional complete source facts and trusted bindings, not an oversized
model response. Removing repeated nodes or empty prior wording would not solve it.

Implementation: `5f90e37fa1b4ef68fbb8338e7cfeab945071e5e1`.
[ADR 0188](../adr/0188-native-bridge-request-budget.md) defines the shared finite
native contract: measure the complete serialized `CreativeHandoffRequest`, not
only a selected context field, against an inclusive **1,048,576-byte** bound before
execution-pin lookup, enqueue or package publication. The complete projected
requests measured 77,195 bytes for Intent and 256,226 for Presentation before
intent suggestions. These were read-only constructions, not model executions.

Generated package metadata and pinned resources are outside that logical request
budget. Bridge package JSON producer/reader bounds are separately **2,000,000
bytes per file**, with publication refusal before writing an oversized file;
other creative stages retain 1,000,000. Both native executor backends round-trip
exactly-at-limit logical requests with generated metadata.

API prompt evidence remains independently capped at 60,000 bytes. Target/source
counts, Unicode span coverage, source/coordinate/hash binding, response schemas,
freshness, provenance, permissions and human/machine review separation remain
unchanged. No author evidence is truncated. A finite admission/storage bound is
not a guarantee of model context capacity, execution time or semantic fidelity.

## Regression and release verification

Two expected-red cases failed at the original native ceilings. The affected
focused union passed **67 cases**; consumer checks passed **89**; the subsequent
package-exchange/native union passed **92**; and the corrected metadata
prepublication assertion passed its **two exact cases**. These selections overlap
and must not be added as distinct cases. The 20 new budget cases cover both
stages, exact below/equal/above UTF-8 boundaries, complete field accounting,
pre-dispatch refusal, unchanged API limits, metadata bounds and both native
package backends. Scoped Ruff F/I, whitespace and module ownership checks passed.
Independent read-only review found no blocking findings, including the separate
package-reader correction.

One unchanged `uv run --locked --no-sync python scripts/verify.py full` invocation
passed on clean implementation `5f90e37f`: **all 14 steps**, **3,120 Python cases
across 262 files**, **1,381 frontend cases** and **319 browser cases**. The gate
included both type checks, deterministic bundle/parity, browser shard coverage,
wheel build/installed-wheel smoke, media probes, dependencies, API imports and
archive-reader checks. Python workers passed 1,602 and 1,518 cases; their reports
recorded one and four warnings respectively. Total gate elapsed: **1,311.148s**.

Original native session `45351` closed naturally, `f5bd2c` → `9ec6ab`, exit 0.
Full-log SHA-256:
`7f8757581fffc4951810a436c6096d25cc4777ea341dd337a074dfb02eb44e94`.
The log is retained privately at
`.local/outline-instruction-startup-20261017/bridge-budget-full.log`, with the
diagnosis and measured facts in `.local/bridge-request-budget-20261017/rca.json`.
These pointers record technical evidence, not a project recovery archive.

## Installation and walkthrough boundary

This establishes complete local software qualification, not hosted CI success,
a performance gain, native generation completion or creative acceptance. The
documentation-only closeout does not change the tested executable bytes.

The old blocked run has a single frozen authority binding its completed attempts
to earlier source. There is no supported source/profile rebase: do not rewrite
its policy, receipts, pins or checkpoints. The owner instead explicitly selected
permanent disposal of that project/run without an archive and a fresh manual
end-to-end walkthrough from the same saved Brief. Only the exact idle project
may be deleted through its normal lifecycle guard; no unrelated data is in scope.

Activate the qualified source in the same installation, preserving existing
configuration and credentials, after confirming no unresolved native execution.
Then use ordinary explicit prepare/send/delivery/review/adopt actions, not
autopilot. Record Codex reviews as Codex, never as human creative confirmation.
Actual new-stage execution, media review and route playback remain to be observed.
Python optimization, speculative batching and the broader Goal remain paused.
