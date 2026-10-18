# ADR 0196: Owned copied interpreter for hosted tests

Date: 2026-10-18

Status: manager-approved; locally scoped verification only. See the
[checkpoint](../verification/2026-10-18-owned-test-runtime.md).

## Problem

The capsule helper correctly refuses group/other-writable QA binaries. Two
hosted proof cases stop at that guard before launch. The exact runner image's
provisioning source makes `/opt` recursively writable, including its Python
toolcache. Direct hosted binary metadata was not captured; this explains a
supported cause, not all original quiet-suite failure markers. A local owned
interpreter reproduces both refusals at 0777 and both passes at 0755.

## Decision

Hosted verification and browser jobs provision a fresh project `.venv` using
the selected CPython 3.12's standard `venv --copies --without-pip`, then populate
it with `uv sync --all-groups --frozen`. A small shared test-tooling script checks
the actual copied executables before and after sync and subsequent ordinary
`uv run`: owned regular one-link files, exact source bytes, safe executable
modes, stable identities/config/aliases, and genuine subprocess executable,
resolve, prefix, physical base-prefix, implementation, exact version and
architecture. Raw base-prefix aliases are retained; their resolved directory
must match the source and the new venv's raw facts must remain unchanged.
Only newly created, verified owned copies may have group/other write bits
removed. Existing destinations and ambient interpreter-selection overrides
are refused. Python tests use `.venv/bin/python -m pytest` explicitly.

QA pins continue to describe the genuine runtime; no pin is invented or
rewritten to bypass admission. Production guards, QA defaults, interpreter
source/cache permissions, dependencies, suite selections, parallelism and
budgets do not change. Local development environment setup is unchanged.

Entrypoint in a fresh checkout: `python scripts/testing/provision_test_venv.py`.
It refuses an existing `.venv` and emits JSON stages with source/copy facts,
configuration and runtime observations in the job log. Failed candidates remain
for diagnosis; the helper does not remove or retry them.

## Alternatives and consequences

Reject chmod of the shared cached interpreter: it mutates the source runtime
and obscures ownership. Reject relaxed file checks or alternate QA metadata:
they weaken the contract being tested. A separate Python installation adds
unnecessary runtime selection and disk use. Three standard executable copies
cost some disk space; frozen dependencies use uv's existing cache rather than a
copied dependency tree. Failure retains the candidate for diagnosis, without
automatic environment replacement or retry.
The copied executables still load the selected base runtime's libraries and
standard library; this is not an independently installed or wholly immutable
Python distribution.

Focused copy/refusal, hash/config/alias drift and workflow contracts protect
this boundary. Native Node capsule and paid-entry cases must pass through the
resulting interpreter. Local proof is not hosted acceptance or a solution to
the separate serial-suite runtime-budget concern.
