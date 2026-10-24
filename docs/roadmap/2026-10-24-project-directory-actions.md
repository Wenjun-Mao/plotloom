# State-aware project directory actions

Approved implementation scope, 2026-10-24. Source baseline: `87d949de`.

## Root cause

`ProjectDirectoryDialog` branches only on closed/archive state and uses current
identity only in its subtitle. It projects save/exit semantics onto every active
row. The global command/read lock is not project activity. The existing lifecycle
owner supports safe noncurrent Close, while force exit actually leaves only the
current workspace. This is a frontend projection/command-ownership contract fix;
backend admission and persistence remain unchanged.

## Approved outcome and plan

1. Current project alone offers Save-and-close / Exit workspace. Other rows expose
   explicit Open / Reopen / Restore. Management copying/archive/noncurrent Close/
   deletion stays available through accessible 更多 where applicable.
2. Explain verified latest-run activity and disable ordinary Close/archive for
   known nonterminal pipeline work. Latest-run absence/terminal status does not
   establish idle: native media occupancy is not completely disclosed by this API.
   Preserve backend refusal feedback, deletion preview, exact title confirmation,
   draft/read guards and single owned command admission. Do not invent capabilities.
3. Add permanent units/browser checks and update ADR 0113, product/engineering
   baseline and acceptance playbook. Use an in-flow disclosure so short desktops
   can scroll to every command; Escape/outside/action/navigation dismiss safely.

## Smallest real outcome

Two fresh disposable projects A/B in the existing isolated browser fixture, zero
provider calls: current A has save/exit, B has Open and management Close; expand
More by keyboard, perform safe noncurrent Close and Reopen, and read back state.
Fixture owns roots/process settlement and cleanup. Extend to archived and unknown
reads and positive nonterminal summary facts; capture 1280×768, 1280×460 and
1700×900 pixels. Existing eight valued projects and both UNKNOWN holds are excluded.

## Ownership, qualification and stopping condition

Sole worker writes source/docs/tests and executes qualification. Root reviews a
stable candidate, owns live Safari and any preservation-checked frontend-only
activation. Focused checks and the small UI slice precede independent review.
After stable review: unfiltered frontend units, both typechecks, deterministic
isolated builds/tree equality, checked-static refresh, affected whole browser
files and pixel inspection. Reuse unchanged backend evidence after actual-diff
boundary review. No backend/API/auth/schema/dependency changes, real providers,
service restart, broad full suite, push or CI. Stop with coherent local main
commit and retained evidence; activation and human acceptance remain separate.

## Execution status

Implementation and independent review are complete, including the three P2
repairs and the narrowly reviewed two-row keyboard-focus follow-up. Final local
frontend qualification passes: 1,512 units, both typechecks, identical complete
seven-file static trees/formal refresh, 28 refreshed browser cases plus 52
explicitly reused distinct cases from the prior 79-pass run, and direct pixels
at all three desktop sizes. The [receipt](../verification/2026-10-24-project-directory-actions.md)
retains original failures, exact commands/manifests, red-to-green proof and limits.

The coherent scoped executable checkpoint `4c6db5ff` is preserved on retained
`main` and activated in the clean detached installed checkout. Root verified all
seven served assets against the qualified manifest and inspected the actual new
directory in native Safari. Fresh before/after captures preserve all eight
projects, complete application/host rows, settings and both UNKNOWN holds exactly;
container and bridge identities are unchanged. No restart, real provider call,
push or CI. The receipt records activation, probe correction and honest native
coverage; owner personal acceptance remains separate. Native worker/reviewer
finals were collected and the completed assignments closed after review.
