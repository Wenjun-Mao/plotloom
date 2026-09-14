# Retained runtime behavioral coverage

This is the concise companion to the machine-checkable
[`coverage inventory`](2026-09-14-retained-runtime-coverage-inventory.json).
It compares accepted browser-parity baseline `e658057` with rejected local
retirement `f908c51`; it does not reintroduce a legacy facade or retained-data
migration.

The first inventory format was rejected as coverage evidence: a file-level
policy could call unrelated assertions equivalent merely because a replacement
test existed. The current inventory has one authored entry for every affected
function and each parameterized case. Every entry preserves the historical
trigger and assertion expressions from `e658057`; non-retired entries point to
an assertion catalog keyed by exact current test ID. A retirement is recorded
on the individual entry with its breaking-project-folder rationale. There are
no file-level defaults or equivalent-by-existence fallbacks.

Run its structural guard with:

```sh
uv run --locked python scripts/retained_runtime_coverage_inventory.py --check
```

The guard verifies population, exact baseline evidence, valid dispositions,
individual retirement rationales, and live replacement assertion records. It
does not decide semantic equivalence; that remains an assertion-by-assertion
review obligation.

The direct-project regressions now separately prove unavailable text admission
returns 422 with zero runs; image delivery rejects malformed, partial and hash
tampered outputs before candidate publication; final-delivery conflicts remain
409; cancellation retains a late delivery without publishing a candidate;
concurrent refresh admits one candidate; cross-project and symlinked delivery
paths are rejected; and a keyframe-adaptation geometry violation is a 422 that
does not replace the reviewed source selection. Pipeline correction, recovery,
work-unit seal, video, lifecycle, review, Alpha and conformance owners retain
their explicit assertion records in the same inventory.

Project bootstrap coverage also asserts canonical-prefix installation,
idempotent replay and conflict, retryable same-key contention while the first
initializer owns its application lease, and recovery after that lease expires.
