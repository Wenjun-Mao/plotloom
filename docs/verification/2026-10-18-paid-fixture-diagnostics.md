# Paid synthetic fixture: passive diagnostic correction

> Historical local artifacts in [the cleanup scope](../roadmap/2026-10-25-top-five-cleanup.md) were retired
> on 2026-10-25. References to those files are not available attachments or resumption
> instructions; recorded outcomes, limits and current project-owned media stand.

Approved scope: improve failure evidence only in the paid synthetic test boundary.
Review baseline: `01025bc8c63f41d97f7c78ba8eb8294e359a40c2`.

## Established failure and evidence limit

[Hosted run 39182416805](https://github.com/Wenjun-Mao/plotloom/actions/runs/39182416805)
finished failed: 3,297 Python passed, one failed and one teardown error. The
count assertion ran after QA/origin and sandbox/startup PID-set checks, but before
capsule and paid outcome assertions. Its message hid actual counts/outcomes.
Settlement wrote a report but exposed a generic exception; private files were
not retained by ordinary CI. The report can contain accumulated ownership
uncertainty, so the exception does not establish a live leak.

One authorized exact existing-Linux case passed: one test / 21.51s, focused
runner 23.103s. All 1,089 reviewed inputs matched before/after. Its arm64 copied
CPython 3.12.3 / Node 22.23.3 observed 59 startups and two sandbox invocations;
real validate/render passed and both settlement reports were empty. Evidence:
`.local/batch-video/linux-ci/paid-exact-once/evidence-summary.json`.
This is **non-reproduction**, not repair or hosted x64/3.12.15 qualification.

## Correction and authority

`tests/paid_outline_diagnostics.py` supplies lazy count/PID/invocation and selected
already-written outcome context. Known outcome tokens and numeric child exits
are allowlisted; arbitrary reason/error strings, commands, auth and environments
are omitted. Passive file reads refuse unsafe paths and oversized files. Each
read and the outer formatter fail closed to diagnostic-unavailable metadata,
preserving the original assertion or settlement exception.

Settlement messages summarize only the existing report: remaining identities,
error categories, observer error type, unresolved spawns/groups and direct exits.
Original predicates, order, expected counts, cleanup/probes/signals, waits and
timeouts are unchanged. Production, dependencies and ordinary CI are unchanged.
ADR 0196 and native module ownership identify the test-only boundary.

Wenjun's later explicit correction holds GitHub CI preparation, workflow drafts
and publication. Retained `AGENTS.md` now requires a new explicit request directly
from Wenjun for GitHub CI, including automatic triggers from pushes. No manager
approval or ordinary implementation/push authority substitutes. The existing
diagnostic worktree remains at `6619e729`, unchanged; no draft was advanced.
No external CI action occurred during this assignment.

## Verification and stopping condition

Run pure diagnostics plus the existing CLI runtime and owned-process contract
files on Mac and the existing owned Linux runtime after exact input sync. Include
native ownership regression checks. Do not rerun the paid success journey, full
or load suites. Independent stable review and a coherent local commit are allowed;
stop for manager review with exact input/evidence hashes. No source publication,
hosted dispatch, product fix, activation, live process/provider, owner-data or
cleanup/archival action is authorized. Results and remaining gaps follow below.

Final `verify.py focused` selections were exactly
`tests/test_paid_outline_diagnostics.py`, `tests/test_paid_outline_cli_runtime.py`,
`tests/test_paid_outline_processes.py` and
`tests/test_verification_module_ownership.py`. Mac: **48 passed / 15.17s**,
runner **19.450s**; existing non-root arm64 Linux: **48 passed / 14.22s**,
runner **19.849s**. Logs under `.local/batch-video/`:
`paid-diagnostics-contracts-mac.log` and
`linux-ci/paid-diagnostics-contracts-linux.log`. The pure diagnostic file owns
14 cases; no paid success journey ran. Native ownership discovery passed with
3,312 Python cases / 286 files; no native test bodies ran in that audit.

Targeted Ruff and whitespace checks pass. Independent AST comparison against
the review baseline proves observation assertion predicates/order unchanged and
settlement logic identical except for the two exception-message expressions;
`paid-diagnostics-contract-parity.json`. Stable independent read-only review,
requested GPT-6.1 Sol / High (effective settings unverified), found no actionable
issue and executed no tests or CI actions. Source and evidence hashes plus the
exact local diff are bound in `paid-diagnostics-candidate.json`. Hosted failure
and non-reproduction evidence remain unchanged; underlying cause, hosted
qualification and product acceptance remain unestablished.
