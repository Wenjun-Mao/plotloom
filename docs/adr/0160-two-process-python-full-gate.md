# ADR 0160 — Two-process Python full gate

Status: proposed, pending the exact-runner local full gate and unfiltered
hosted same-SHA qualification.

## Context

A full Python duration profile on the M0–M5 candidate passed 1,507 cases in
383.07 seconds. Its slowest 20 setup/call/teardown phases totaled 58.29 seconds
(15.2%); the longest phase was 6.72 seconds. The elapsed cost is spread across
the suite rather than dominated by one test. A bounded two-process run passed
the exact whole-file collection split, and an end-to-end run of the new runner
passed all 1,512 then-current Python cases. The broader work window also
contained main-thread UI verification, so those process timings are functional
evidence only and are not an accepted speed comparison.

The isolation audit found that test projects and session fixtures use pytest
temporary roots, project locks and spawned-process files are case-local, test
environment changes remain process-local, and the only socket listeners bind
ephemeral ports. The production style-contract and schema caches are
process-local. No test reads or writes the shared pytest cache API.

A quiet matched comparison on the Apple M5 Pro used the M0–M5 candidate
rebased to base 4566ec7 and ran the same 1,516 native cases. Serial pytest passed in 390.050 seconds of external wall
time (364.08 seconds reported by pytest). The two-process runner passed 758
cases in each worker, split across 78 and 79 files with separate basetemps, in
240.026 seconds external wall time (222.738 seconds in the runner summary).
This single pair reduced external wall time by 38.5%; it is not a repeated
median. The raw serial and worker logs are retained under the task's temporary
M5 measurement directory.

## Decision

Use two Python processes in the full local gate. First collect the unfiltered
native case IDs, reject empty, duplicate, unsafe or malformed rows, then assign
whole test files with a deterministic greedy split by collected case count.
Check that the worker file union is exact and disjoint before starting tests.
Run native collection as an owned subprocess group too. Poll
`communicate(timeout=0.25)` so both output streams keep draining while the
coordinator checks for signals; on SIGTERM, stop and reap the collector group
before returning. Each pytest worker receives a distinct `--basetemp`; disable
pytest's shared cache provider and bytecode writes. Preserve `--durations=20`,
wait for both workers, print each report separately, and fail the full step if
either worker fails. Record SIGTERM without immediately exiting, then terminate
both worker process groups, wait up to five seconds and kill any remaining
group. `finally` cleanup stops owned collection and worker processes before
closing logs and removing their temporary root on abnormal exit. SIGINT returns
130; SIGTERM returns its standard `128 + signal` status.

The runner lives in `scripts/testing/run_python_suite.py`; only `verify.py
full` uses it. Focused and module selections continue to use their native
single-process selectors. The native ownership guard remains responsible for
the exact complete-suite case inventory.

## Alternatives and consequences

Keeping pytest serial avoids process orchestration but leaves the measured
Python step on the full-gate critical path. A third-party worker plugin is not
needed for the bounded two-process plan and would add a dependency. A checked-in
static shard list would need updates whenever cases move or are added; native
collection allows the assignment to adapt while retaining exact coverage.

The measured comparison shows a material improvement for this host and
configuration, while representing one pair rather than a timing distribution.
Keep the change limited to the local full gate and two workers. The exact-runner
local full gate and unfiltered hosted same-SHA qualification remain required.
If final qualification fails or later repeated execution exposes isolation
defects, restore the serial full step and reassess the local runtime target
before broadening concurrency.

Detached collection and worker sessions prevent a signal sent only to the
coordinator from reaching its children. The coordinator records SIGTERM and
completes cleanup itself instead of allowing the default handler to exit
immediately. Cleanup tracks process-group existence independently of pytest
leader status: a leader can exit on SIGTERM while a child remains. The runner
waits up to five seconds for each group to exit, sends SIGKILL to any remaining
group, then reaps each leader before closing logs or removing temporary files.
Regressions cover SIGTERM during collection and a worker leader that exits while
its child ignores SIGTERM.

This descendant-cleanup guarantee is qualified on POSIX, matching the current
macOS developer and Ubuntu hosted-CI targets. The Windows fallback terminates
the pytest worker process itself; it does not provide process-tree containment,
so Windows cancellation safety for this full-gate runner remains unqualified.
Add and verify Windows process-tree containment before treating it as a
supported full-gate target.
