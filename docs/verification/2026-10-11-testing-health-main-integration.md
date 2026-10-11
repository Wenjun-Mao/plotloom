# M0-M5 main integration qualification

Owner authority: continue integration, qualification, publication and recoverable
cleanup, alongside the separate owner walkthrough. Worker source:
`e8767b9d24942f47d1b57a8dcbdd680a45de4804`, pushed clean on
`codex/testing-health-m0-m5`. Non-destructive main merge:
`038b46850e5a4f2b31d7a251d56eff5fe6af0cf5`.

## Integrated local full

On exact `038b468`,
`uv run --locked --no-sync python scripts/verify.py full` passed:
`VERIFY_SUMMARY tier=full elapsed_seconds=711.499 exit_code=0`.

- 1,518 Python cases, 157 whole files, two disjoint workers of 759 cases each.
- 1,201 frontend unit cases / 145 files and both type checks.
- 292 unfiltered browser cases, 475.784s.
- Lock, probe tools, API F401, archived prompt reader, deterministic build/parity,
  native ownership, four-shard coverage, wheel build and installed-wheel smoke.

Independent integration review found no actionable issues and passed 42 tooling
tests plus native inventory/ownership reconciliation. The later bounded
Storyboard-guide frontend delta qualifies through ADR 0156; see
[its receipt](2026-10-11-storyboard-production-workflow-hints.md). It does not
invalidate unchanged Python/package inputs or authorize an unnecessary full
rerun. Latest native inventory is 1,518 Python / 1,214 Vitest / 294 browser
cases; four browser shards are 83/70/70/71, without gaps or overlap.

## Hosted and cleanup checkpoint

The older green hosted run `38113104300` is pinned to `5d007935`, before this
main and UI input. It is not current qualification. Publish the reviewed main
candidate, dispatch one unfiltered workflow with `browser_grep=.*`, and consume
that exact-SHA result before completing the hosted qualification checkpoint.

Read-only worker cleanup inspection found a clean worktree with no nonignored
untracked files or unique ignored evidence. Ignored items are reproducible
dependencies and caches plus `.last-run.json`; durable receipts are tracked.
Its managed attachment identity is
`/Users/wjmao/.codex/worktrees/verification-health/plotloom`, attached to the
worker task. Archive recoverably through that task after qualification; preserve
the pushed branch and do not touch other checkouts. No archive has happened yet.

Windows process-tree containment remains unqualified. Current cancellation
guarantees are POSIX-only (macOS and Ubuntu). This software qualification is not
owner walkthrough or final-media acceptance.
