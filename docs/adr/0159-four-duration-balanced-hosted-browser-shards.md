# ADR 0159 — Four duration-balanced hosted browser shards

Status: accepted, 2026-10-11.

## Context

The hosted browser job used two whole-spec groups with one Playwright worker per
runner. The latest carried-over run on 7da7b6e spent 31.18 and 26.28 minutes in
the browser regression steps. The per-spec durations include retries and
inter-case setup and teardown time, so they provide a practical allocation
signal but do not isolate test-body time or establish a controlled speedup.
Greedy duration packing of the 85 specs into four groups estimates 14.35–14.41
minutes per group.

## Decision

Use four whole-spec hosted browser shards with one worker per runner. Assign
specs through the checked manifest, currently balanced at 22/21/21/21 specs.
Keep fail-fast disabled, existing retry and timeout settings, full reports and
the same-SHA verify/browser jobs. Do not add runner infrastructure or alter
fixture ownership.

The allocation guard discovers the unfiltered native Playwright case set and
each configured shard through Playwright list mode. It fails on an empty
full-suite shard, overlap, missing or unexpected cases, stale or duplicate
spec assignments, and preserves diagnostic BROWSER_GREP selection. The four
shard IDs are part of the CI and Playwright configuration contract.

The first unfiltered hosted run of this candidate is both the bounded four-shard
probe and the M5 hosted qualification. Do not launch a separate probe. If
measured results materially contradict the estimate, review the allocation
before accepting the change.

## Alternatives and consequences

Keeping two groups avoids additional runner concurrency but preserves the
observed long browser critical path and leaves the measured imbalance
unaddressed. Python full-suite parallelism is a separate local-gate decision
recorded in ADR 0160; it shortens the Python step and does not replace balancing
the hosted browser step. Splitting files or cases would increase assignment
churn and weaken within-spec ordering.

The exact local manifest guard proves coverage and disjointness, not hosted
runtime or runner availability. Four runners use more concurrent standard
capacity than two. Future allocation updates must use fresh per-spec durations
and preserve the native exact-union guard. The unfiltered hosted result remains
the acceptance evidence.
