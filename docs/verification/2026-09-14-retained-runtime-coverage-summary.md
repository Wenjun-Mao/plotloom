# Retained runtime behavioral coverage

This is the concise companion to the machine-checkable
[`coverage inventory`](2026-09-14-retained-runtime-coverage-inventory.json).
It compares accepted browser-parity baseline `e658057` with rejected local
retirement `f908c51`; it does not reintroduce a legacy facade or retained-data
migration.

| Disposition | Baseline test functions | Meaning |
| --- | ---: | --- |
| Migrated current contract | 255 | Behavior is asserted through a manifest-bound project store or application owner. |
| Existing equivalent | 11 | The test was migrated in place or covered by a named current assertion. |
| Truly retired contract | 35 | Shared-route/facade, generic-media-worker, or unsupported shared-store migration behavior only. |

The inventory records all 301 affected functions and the 25 individual
parameterized cases present in their six parameter decorators. Each non-retired
entry names an existing current test; each retired entry carries the approved
breaking-project-folder rationale. Run its guard with:

```sh
uv run --locked python scripts/retained_runtime_coverage_inventory.py --check
```

The follow-up direct-project regression suite restores the missing durable
generation assertions: correction cap/lineage, dispatch ordering,
reasoning-only isolation, primary and correction response recovery without a
provider replay, provider-echo secret redaction, correction-audit and
timing-fact hash rejection, and exact-repair evidence-hash rejection. The
retained project storage, image,
video, review, approval, lifecycle, snapshot, and browser suites continue to
cover their own explicit owners.

Project bootstrap coverage also asserts canonical-prefix installation,
idempotent replay and conflict, retryable same-key contention while the first
initializer owns its application lease, and recovery after that lease expires.
