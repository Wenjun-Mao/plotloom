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
main and UI input. It is not current qualification.

Unfiltered [hosted run 38143271232](https://github.com/Wenjun-Mao/plotloom/actions/runs/38143271232)
passed on exact `606626d32d7fc099986c90292e0a76e015c142c0`, with
`browser_grep=.*`: verification and all four browser shard jobs succeeded.
The manager independently read back the exact SHA and all job conclusions.
This qualifies the integrated M0-M5 and that UI revision, not later source or
runtime configuration changes.

Read-only worker cleanup inspection found a clean worktree with no nonignored
untracked files or unique ignored evidence. Ignored items are reproducible
dependencies and caches plus `.last-run.json`; durable receipts are tracked.
Its managed attachment identity is
`/Users/wjmao/.codex/worktrees/verification-health/plotloom`, attached to the
worker task. After qualification, the worker deinitialized the clean pinned
submodule without force and requested recoverable archival. The app returned
`queued`, without a status identifier. Subsequent readbacks still showed the
checkout and active attachment; archival is not confirmed. Preserve the pushed
branch, do not manually delete the checkout or duplicate the ambiguous queued
operation, and do not touch other checkouts.

Windows process-tree containment remains unqualified. Current cancellation
guarantees are POSIX-only (macOS and Ubuntu). This software qualification is not
owner walkthrough or final-media acceptance.

## Latest combined qualification — October 11

The later H3 deployment and media-guide source was independently reviewed,
committed and pushed at exact
`d59bcdab17af8f4850b082cf832ad12537946583`. One combined local full gate passed
in 721.842s, exit 0: 1,542 Python cases / 158 files, 1,226 Vitest cases / 149
files and 294 unfiltered Playwright cases / 89 specs. Both type checks, lock,
API lint, archived reader, deterministic bundle/parity, native ownership,
four-shard union/disjointness and installed-wheel smoke passed. The Python
workers each passed 771 disjoint cases; browser allocation was 83/70/70/71.

The single unfiltered [hosted run 38146928907](https://github.com/Wenjun-Mao/plotloom/actions/runs/38146928907)
passed `verify` and all four browser jobs on that exact SHA, independently
read back by the manager. It ran 14:22:43Z–14:40:57Z (18m14s). This qualifies
the current integrated runtime code, unlike the older hosted checkpoints above.
Main integration, code publication and qualification are complete. The final
receipt publication changes documentation only and does not relabel this CI
run as qualification of its later documentation SHA.

At the latest read-only cleanup check (15:31Z), the worker was idle and its
attachment `01a12b36-adc4-70b1-8932-2c2c8bd6883e` still referenced the existing,
Git-registered checkout at `e8767b9`. No archive operation status or recovery
endpoint was exposed. The queued recoverable archive remains unconfirmed;
the pushed clean branch and checkout are preserved. Do not claim cleanup
completed or retry an ambiguous archive by manually deleting its target.
