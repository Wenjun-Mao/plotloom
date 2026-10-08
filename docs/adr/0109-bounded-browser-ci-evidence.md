# ADR 0109: Bounded browser CI and retained failure evidence

Status: Accepted, 2026-10-03.

## Context

Release run37156656232 passed frontend, Python and distribution checks but
exhausted the single job's30-minute budget during a131-test, one-worker browser
suite. Several tests failed on both attempts. The job cancellation skipped
report uploads and prevented the detailed final failure summary. This proves
an evidence/budget defect in CI, not that the browser failures are harmless or
caused by resource contention.

## Decision

Keep manual-only CI and all existing non-browser gates. Run browser tests after
that gate in two independent runners, each with one worker and file-level
Playwright sharding. Leave test/assertion deadlines and retry policy unchanged.
Use a40-minute Playwright global deadline inside a45-minute step and55-minute
job, so ordinary suite timeout can finalize evidence before outer cancellation.
Upload each shard's report/results on success or failure unless the run was
cancelled. Both shards must pass; fail-fast is disabled to preserve other-shard
evidence. No fixture or product runtime divergence is introduced.

An optional manual `browser_grep` regex defaults to `.*`. A filtered run is
diagnostic evidence only, never the full release gate. Pass the input as a quoted
environment variable, not interpolated executable shell source. A stable
candidate still requires an unfiltered run covering the entire suite.

The approach follows [Playwright sharding](https://playwright.dev/docs/test-sharding)
and [CI guidance](https://playwright.dev/docs/ci); step/job deadlines follow
[GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Rejected alternatives and consequences

Merely extending the combined job would retain a coupled budget and hide the
underlying test failures. Increasing workers on one runner would change the
resource-contention hypothesis without evidence. Skipping failing cases or
loosening their expectations would weaken release acceptance.

Browser installation is repeated per runner. File-level shard balance can be
uneven; actual runtime and reports, not test counts, determine future tuning.
Cancellation or setup failure can still prevent browser evidence. Preserve the
failed run and diagnose concrete assertions before another full release run.

## Mutable runtime isolation amendment · 2026-10-04

Run37164168705 proves cross-test state leakage: an unresolved held native send
left the worker-scoped dispatch reservation active; another test restarted into
`outputs/after-package-conflict`, so a later test created its project there and
then reset to the fixture's original root during restart, producing a real404.
These are fixture-lifetime defects, not permission to clear production leases
or classify missing homes as temporarily available.

The whole mutable FastAPI/provider/data-root workbench is test-scoped. Normal
within-test restart and persistence assertions retain their exact roots; no
lease is released from cancellation or idle state. The shared page explicitly
depends on that workbench, so its held-route release/drain completes before
the backend is stopped. Browser contexts remain test-scoped; runner worker
count, retries and deadlines are unchanged. More setup work is an accepted
cost of isolation. A retained fixture parent still preserves requested evidence.
The fixture explicitly retains the45-second setup/teardown budget formerly
inherited by the worker fixture from the suite configuration; moving scope
does not subtract startup time from existing shorter journey budgets.
Do not restore worker sharing by introducing ad-hoc state resets or weakened
dispatch ownership; regress the scope and dependency ordering explicitly.

This uses [Playwright fixture scope and execution order](https://playwright.dev/docs/test-fixtures#execution-order).

## Setup phase evidence amendment · 2026-10-08

Local121 and145 gates timed out during workbench setup before any UI assertion.
The trace named only the outer45-second fixture, losing the interrupted setup
owner. Preserve disposable-root, port-allocation and each owned-process readiness
phase as named steps nested under that fixture. Phase URLs contain only owned
loopback origins; do not attach environment values or project/credential payloads.
Polling, startup/fixture budgets, workers, retries and cleanup ownership remain
unchanged. Successful146 focused traces qualify emitted phase identity/timing,
not failure-phase retention or a startup causal fix. An unchanged passing replay
cannot explain earlier failures. Unbounded in-flight readiness fetch and cumulative
stage budgets remain explicit follow-ups; choose repairs only after causal evidence.
