# Completed CLI/Python main integration — October 17, 2026

> Historical local artifacts in [the cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md) were retired
> on 2026-10-25. References to those files are not available attachments or resumption
> instructions; recorded outcomes, limits and current project-owned media stand.

## Scope and tested identity

The owner requested parking optimization and speculative image batching, merging
completed work to `main`, pushing, then conducting a joint manual walkthrough.

Tested merge: `09791c2068fce4326fd85593ece145162ed87f6c`.
Tree: `adaaf10229859e5328135a4ddd797c5c53fe5171`.
Parents: Python checkpoint `52b61d0c1f30532d249d57d96bfb7963cb59c4db`
and previous local main `91871f4b01b0742aa99e0b3fb2b4e0aeb53f49ef`.
The Python lineage includes CLI documentation checkpoint
`e3dc802cef837e1f0a2f3f5071ecff7fcb140ef8`.

Integration retains current strict/retained Outline and profile-slot contracts,
main's nonduplicate RunView projection and canonical validation derivations, and
both exact-decimal numeric safety and frozen F5 cut/segment limits. The RunView
decision is renumbered [ADR 0186](../adr/0186-run-view-local-checkpoint-evidence.md)
to avoid the independently introduced planned-dialogue ADR 0179.

## Verification

One full invocation ran on the clean tested merge, without an observation harness
or injected Python/UV overrides:

```sh
uv run --locked --no-sync python scripts/verify.py full
```

All fourteen steps passed, with natural exit 0 in **1,267.774 seconds**:

- Locked dependencies, media probes, API import checks and archived prompt reader.
- **1,381 frontend cases**, frontend types and deterministic production build.
- **3,078 Python cases / 261 files**, default two workers, exhaustive and disjoint
  assignments with validated completions: 1,651 and 1,427 passed.
- Checked production-bundle parity, unfiltered browser allocation and **319 browser
  cases**, including browser type checks.
- Wheel build and installed-wheel smoke.

Original native handle `5175` closed naturally: `ce3312` to `7ffcf3`, exit 0.
The historical full log was recorded at
`.local/release-cli-python-main-20261017/full.log`, SHA-256
`9341611caf670ed8d95eb805b529366f07a68d1c34e4b791bd982cdfc9f835bc`.
Deprecation, color-environment, bundle-size and build-tool compatibility warnings
were reported; none was converted into a skip or waived failure.

Before the full run, 172 distinct focused cases, ownership inventory, quick
verification and scoped Ruff/diff checks passed. The first focused run's failures
are retained: an imported fixture dependency was not exposed, two arithmetic
stress fixtures contradicted the restored frozen limits, and an older spy counted
independent Outline schema validation as duplicate artifact encoding. Corrections
were confined to those test assumptions; production validation remained strict.
Independent static review found no remaining actionable integration blocker.

## Historical integration boundaries and subsequent retirement

The older unaccepted candidate and private stack-census work were excluded from
this merge. The census implementation remained mechanism-unqualified, with a
`Census.invalidate` fault-sink defect. The owner subsequently approved discarding
that prototype and the obsolete private execution roots under the
[top-five cleanup](../roadmap/2026-10-25-top-five-cleanup.md). Earlier preservation
and hold language is superseded for those retired roots; original failed/unknown
remote outcomes are not converted to successes or settlements by local deletion.
Current functional revocation guards remain outside that cleanup. The existing
installation-reader proposal ref is retained temporarily for its separate
accept/reject decision, without preserving the old checkout.

The subsequent closeout changes documentation only; executable bytes remain those
of the tested merge. Hosted CI was not dispatched. No live app restart, provider
generation, canonical adoption or creative/product acceptance was performed.
Python optimization and image batching remain parked; the 151.73295-second
Python target remains open. This full gate is software qualification, not a new
benchmark or a claim of global process silence or historical cleanup.
