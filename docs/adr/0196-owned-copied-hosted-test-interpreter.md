# ADR 0196: Owned copied interpreter for hosted tests

Date: 2026-10-18

Status: manager-approved; scoped verification only. See the
[checkpoint](../verification/2026-10-18-owned-test-runtime.md).

## Problem

The capsule helper correctly refuses group/other-writable QA binaries. Two
hosted proof cases stop at that guard before launch. The exact runner image's
provisioning source makes `/opt` recursively writable, including its Python
toolcache. Direct hosted binary metadata was initially unavailable; this was a
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
are refused. Python tests explicitly enter through `.venv/bin/python`.

QA pins continue to describe the genuine runtime; no pin is invented or
rewritten to bypass admission. Production guards, QA defaults, interpreter
source/cache permissions and dependencies do not change. Qualification method,
selection and budgets belong to ADR 0160. Local environment setup is unchanged.

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

## Synthetic CLI launch boundary

Hosted diagnostic 39175064170 directly observed the selected 3.12.15/x64 source
at 0777, unchanged, and three one-link owned 0755 copies with identical bytes.
Its complete 154-case inventory ran: 152 passed, two paid cases failed before
Node validation importing `dotenv`. The generated fake CLI used `env python3`,
which does not inherit pytest's explicit interpreter selection. Its exact remote
interpreter path was not captured. A local private PATH control selects a genuine
Python with `-I -S`, proves the missing dependency, and reproduces the boundary.

Bind this synthetic Python CLI to the **raw absolute QA entrypoint**, preserving
its venv launch path. Validate before wrapper creation or allocation: nonempty,
absolute, no NUL or Unicode whitespace, and at most **127 UTF-8 encoded bytes
including `#!` and the terminating newline**. Unsupported paths are refused.
Do not resolve to a base binary, fall back to PATH, or install ambient packages.
A shell trampoline is rejected: its exec changes argv after Popen, racing the
supervisor's immediate process-identity capture. Supporting other path forms
needs a separately verified fixture launch design.

Small stdlib-only startup support writes exclusive PID-scoped observations
before project imports and checks real QA entrypoint/physical executable,
prefix/physical base, implementation and major/minor. Raw prefixes and exact
patch version are observations, not invented QA fields. Successful sandbox
imports produce separate exclusive records: copied application/supervisor
origins and genuine `dotenv` from the checked environment. Import failure must
leave its startup record intact. These are synthetic observations, not a new
production authority or receipt framework. Existing spawn journals and empty
owned-process settlement remain required.

Valid and invalid-candidate journeys prepend a private, demonstrably dependency-
free ambient Python while preserving PATH's tail, reset its marker, and require
that the CLI never selects it. Every sandbox invocation must match startup and
import facts. Real Node validate/render output and hash assertions, invalid
missing-params/no-receipt/no-retry assertions, production filters/guards and QA
defaults/pins remain intact. Duplicate refusal after a terminal first outcome
does not itself prove successful first delivery. Preserve the failed hosted
diagnostic unchanged; local correction does not establish hosted acceptance.
