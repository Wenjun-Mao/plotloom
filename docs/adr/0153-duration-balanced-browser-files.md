# ADR 0153: Duration-balanced browser files and UI-only journey boundary

Status: adopted in CI configuration, 2026-10-10; exact hosted qualification is
pending.

## Problem and evidence

Hosted run CI38009336409 selected 276 browser cases. Shard 1 completed 143
passed cases in 34.6 minutes; shard 2 completed 132 passed cases in 17.9
minutes, with one flaky case overall. Equal case counts do not balance elapsed
work. Each runner must continue to own at most one service stack at a time,
preserve the default within-file order, retain exact diagnostic `BROWSER_GREP`
selection, and leave unsharded local runs complete.

Only `creator-confirmation.spec.ts` was demonstrated to be API-in-memory: it
loads a static HTML fixture and exercises DOM consent, focus, cancel/reload,
and no-native-dialog behavior without backend or provider traffic. Other
creator-workbench journeys use their API/runtime contract.

## Decision

Partition whole E2E spec files into two explicit groups in
`frontend/e2e/browser-shard-manifest.json`. Use longest-processing-time greedy
bin packing over the 276 hosted attempt durations, summing by spec file. Two
new listener-ownership cases lack historical timings and receive the historical
5.4-second median each for this estimate. The manifest has 42 files per group;
its estimated prior case-time sums are 1,212.434s and 1,212.900s, with 122 and
156 current cases. These are planning estimates, not measured hosted wall time;
runner/setup overhead is excluded.

CI sets `BROWSER_SHARD=1` or `2`; the Playwright config selects the manifest
group through supported `testMatch` file patterns. The workflow removes
Playwright's second `--shard` partition while keeping the existing
`BROWSER_GREP` argument unchanged. `fullyParallel: false` preserves default
within-file order, and CI keeps one worker. Without `BROWSER_SHARD`, local
Playwright collection remains unfiltered and complete.

Before running browser bodies, CI executes
`frontend/scripts/check_browser_shard_manifest.mjs`. It fails closed if any
current Playwright test file is unassigned, unexpected, duplicated, or assigned
to both groups. It runs `--list` for the unsharded suite and both groups with
the same `BROWSER_GREP`, then checks exact case-ID union and zero overlap. A
diagnostic filter may select no cases on one group. After the guard proves the
unsharded selection is nonempty and the groups form the exact disjoint
partition, CI uses Playwright's public `--pass-with-no-tests` option so the
empty filtered group does not fail. The guard still rejects a globally empty
filter, and the default full-suite `.*` selection must populate both groups
before either runner is allowed to start. A one-case `1/0` diagnostic was
verified to fail without the option and exit successfully with it; no test
body ran.

The only approved Vite-only journey is the static
`creator-confirmation.spec.ts`, which imports `vite-only-fixture.ts`. That
fixture owns Vite and route draining only; it starts no FastAPI backend,
provider, or project data root. API-backed creator cases remain on the full
workbench fixture in `e2e/fixture.ts`. Expand the Vite-only boundary only when
a journey's source and network evidence prove that its API behavior is fully
in-memory and it requires no backend/provider state.

## Alternatives and guardrails

Equal-count Playwright case sharding was rejected because the hosted run was
nearly 2:1 in wall time. The runner-level `PWTEST_SHARD_WEIGHTS` option was
not adopted because it is not part of the documented public workflow contract.
Static group assignments alone were rejected without a fail-closed file and
case-coverage check. The only runner relaxation is allowing an empty shard
inside the guard-proven filtered partition; globally empty and default full
suite selections remain fail-closed. No timeout, retry, worker, API, provider,
or application contract is relaxed.

The local manifest guard passes the current 278-case unfiltered set with
122/156 cases, zero overlap, and no missing IDs. A representative
`currentness` diagnostic selects 20 cases across 14/6 with the same exact
union. These are collection checks, not runtime qualification. Run the exact
hosted workflow once after owner review; retain its results before treating the
duration estimate as confirmed.
