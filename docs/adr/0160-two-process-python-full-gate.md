# ADR 0160 — Two-process Python full gate

Status: accepted. The exact-runner integrated local full gate passed on
`038b468` on 2026-10-11, and unfiltered hosted run `38143271232` passed on
`606626d32d7fc099986c90292e0a76e015c142c0`. See the verification receipt
for results and the later UI-only evidence scope. Worktree archival remains a
separate cleanup checkpoint and does not expand platform qualification.

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

Use two Python processes in the full local and hosted gates. First collect the
unfiltered native case IDs, reject empty, duplicate, unsafe or malformed rows, then assign
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

The runner lives in `scripts/testing/run_python_suite.py`; `verify.py full`
and the ordinary hosted Python step use it. Focused and module selections
continue to use their native single-process selectors. The native ownership guard remains responsible for
the exact complete-suite case inventory.

## Alternatives and consequences

Keeping pytest serial avoids process orchestration but leaves the measured
Python step on the full-gate critical path. A third-party worker plugin is not
needed for the bounded two-process plan and would add a dependency. A checked-in
static shard list would need updates whenever cases move or are added; native
collection allows the assignment to adapt while retaining exact coverage.

The measured comparison shows a material improvement for this host and
configuration, while representing one pair rather than a timing distribution.
Keep the change limited to full qualification and two workers. The exact-runner
local full gate and unfiltered hosted same-SHA qualification remain required.
If final qualification fails or later repeated execution exposes isolation
defects, restore the serial full step and reassess the local runtime target
before broadening concurrency.

## Hosted qualification scope — 2026-10-18

The original growing serial hosted gate stopped at its 45-minute bound while
still advancing. Later copied-runtime diagnostic 39175064170 passed genuine
hosted 3.12.15/x64 source/copy setup and the exact 154 affected cases completed
with two distinct fake-CLI dependency-boundary failures (ADR 0196). These facts
do not establish the full serial budget's cause or promise a speed improvement.

Manager approval extends the existing runner to ordinary hosted qualification:
`.venv/bin/python scripts/testing/run_python_suite.py`, with its unchanged default
**two** workers and existing **45-minute step / 55-minute job** bounds. Reuse the
owned copied test environment. Do not change scheduler, plugins, timing data or
worker implementation. Historical weights remain prediction only, with explicit
host-mismatch fallback under ADR 0171; no timing manifest is forced into use.

Native unfiltered collection, exact whole-file cover, worker completion proofs,
separate basetemps, ambient-filter refusal, failure propagation and POSIX group
cleanup remain required. The same-SHA frontend, bundle, packaging, wheel smoke
and complete browser gates remain unfiltered and separate. Local focused runner
contracts are preparatory evidence; full local and hosted release qualification
are still required and require separate execution authority for this checkpoint.
No higher concurrency, filter, timeout increase or measured speed guarantee is
part of this decision.

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

## Duration-aware whole-file allocation

The strict freshness eligibility below is superseded by
[ADR 0171](0171-historical-python-scheduling-predictions.md): same-host historical
rows may predict current scheduling with explicit provenance, never execution
coverage or new performance evidence. The original capture contract remains.

The full runner may use a checked-in duration manifest only when it covers the
exact native case fingerprint and every collected test file and parameter row,
and its source, configuration, fixture, Python and host fingerprints match the
current run. Complete rows record setup, call and teardown durations. The
timing plugin emits rows only for a successful complete worker run; failed or
interrupted runs produce an incomplete run marker and cannot be promoted as
timing evidence.

Manifest rows are validated before workers start. Duplicate keys or paths,
unsafe paths, missing or extra files, mismatched row counts, negative or
nonfinite phase totals, and out-of-range numbers are rejected. A well-formed
but stale or incomplete manifest uses deterministic whole-suite case-count
allocation with an explicit fallback reason. Native collection remains the
sole selection authority, and exact union/disjointness, two workers, isolated
temporary roots, ambient-filter refusal, failure propagation and process
cleanup remain unchanged. Timing capture itself does not write the manifest or
other repository files; reviewed weights are promoted separately.

The host fingerprint includes the machine name, platform, architecture,
processor and Python implementation/version. The input fingerprint hashes
Python and non-Python files under the source, testing support and test trees,
root Python configuration and the initialized Shuohao submodule working tree.

## Owned-leader zombie race correction

On 2026-10-12, two running owned workers reproduced a cleanup race: after
SIGTERM, the last `Popen.poll()` still returned running, but the group contained
only its own leader as a zombie. SIG0 returned EPERM. Reaping that owned child
then probing again returned ESRCH; metadata confirmed no remaining group members.
This differs from probing an already-reaped empty group, which returned ESRCH.

The first bounded correction used one nonblocking poll before retry. Full
qualification at `ec2f00c6` still failed at the first probe: exit was not yet
observable through that poll. The final `Popen` representation was captured after
test cleanup, so it did not establish the child's state at the denied probe.

Keep standalone group observation strict. The shutdown coordinator alone owns
successful TERM admission and one existing deadline. On a denied probe after
successful TERM, wait/reap the exact owned child within the remaining shared
grace, then reprobe the kernel. Only ESRCH establishes absence; a successful probe
means descendants may remain. Child timeout, persistent denial or initial TERM
denial stays exceptional without KILL of an unresolved denied group. Do not add a
fresh deadline, fixed sleep, platform exception or foreign process scan.

Tests cover delayed exit after a still-running poll, surviving descendants,
timeout/persistent/initial denial, vanished TERM groups and shared two-group
deadline exhaustion. Existing actual two-worker and descendant integrations
remain intact in a cohesive cleanup test owner. This is scoped evidence, not a
full-gate pass or an absolute guarantee against PGID reuse.
