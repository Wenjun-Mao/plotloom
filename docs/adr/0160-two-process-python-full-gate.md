# ADR 0160 — Two-process Python full gate

Status: proposed, pending a quiet-window performance comparison and final M5 qualification.

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

## Decision

Use two Python processes in the full local gate. First collect the unfiltered
native case IDs, reject empty, duplicate, unsafe or malformed rows, then assign
whole test files with a deterministic greedy split by collected case count.
Check that the worker file union is exact and disjoint before starting tests.
Each pytest process receives a distinct `--basetemp`; disable pytest's shared
cache provider and bytecode writes. Preserve `--durations=20`, wait for both
workers, print each report separately, and fail the full step if either worker
fails. On interruption, terminate both worker process groups.

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

The process split can contend for CPU and file-system bandwidth, so speedup is
not assumed. The existing timing samples are exploratory; M5 must repeat a
matched serial and two-process comparison after the manager's main-thread work
is quiet. If the quiet comparison fails to show material improvement or
repeated execution exposes isolation defects, restore the serial full step and
reassess the local runtime target before broadening concurrency.
