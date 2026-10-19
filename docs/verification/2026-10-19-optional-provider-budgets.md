# Optional aggregate provider budgets: first source checkpoint

Date: October 19, 2026. Source owner: Relay worker
`01a15548-2c38-7bc0-a701-1e5d99e34d98`; manager
`01a04525-e907-7630-9640-78790d69e8ae`.

Retained checkout `/Users/wjmao/.codex/worktrees/b30f/plotloom`, clean baseline
`211808c02f3f8a9fbdbd64bf2a3dc701dcb36617`, local `main`. This receipt accompanies
the scoped candidate commit; no installation or publication is implied.
Native dispatch requested `gpt-6.1-sol / medium`, as confirmed by the manager;
effective settings remain unverified. No code-writing subworkers were created.

## Change and safety boundary

[ADR 0200](../adr/0200-optional-aggregate-provider-budgets.md) records the owning
contract: omitted/new default or explicit null aggregate limits mean unlimited;
explicit finite integers retain enforcement without artificial upper ceilings.
The [approved batch plan](../roadmap/2026-10-18-batch-video-production.md#approved-prospective-aggregate-budget-implementation-october-19)
records the finite task outcome, exclusions and review stopping condition.

Launch request/policy, batch setup/inventory, early/full image admission, job
capacity, persistence reservations, continuation lifetime accounting, batch
cumulative dispatch, QA scope containment and portable validators all use the
nullable meaning. Prospective source-owned QA authority supports either cap
independently null. No new scope/enrollment is added; the initial exact QA scope
still has 2 submissions / 10 seconds and its golden hash is unchanged. Finite
scope refuses null/larger batch caps; finite batch still constrains uncapped QA.
Failed and UNKNOWN claims count, and unsettled work blocks another submission
even with null budgets. H3 per-request profiles/durations, structural limits,
concurrency, one-attempt/idempotency, pause/cancel, scope/attribution, accounting
and Atlas Wan's separate paid ledger remain unchanged.

Both launch/setup forms default to explicit Unlimited, keep blank/invalid finite
input un-submittable, reset drafts on project change, and show actual frozen
caps on readback. New batch setup also resets to Unlimited; continuation carries
the explicitly selected existing policy. Checked static assets were rebuilt.
The local module ownership manifest adds the two new test-file owners so native
discovery remains complete; no CI/release workflow changed.

## Small provider-free real local journey

The existing temporary six-target batch fixture is the smallest supported batch
fixture reused here; there is no source-owned live project or new runner.
Playwright used the real local UI, FastAPI setup/control/read routes and project
persistence. New Unlimited setup serialized both limits as null; reload retained
the same manifest hash. A second setup with 1 job / 5 requested seconds retained
those exact values/hash after reload and refused the six-target/30-second
inventory before English authorization or dispatch. The final video-job list was
empty. No provider output or creative acceptance is claimed. Fixture teardown
owns the temporary roots/processes; no actual installation service was operated.

Inspected desktop captures at 1280×768 show both Unlimited selects and the frozen
finite summary/blocker. These captures and command logs are retained locally in
[the local evidence folder](../../.local/batch-video/optional-provider-budgets/)
(ignored, no secrets).
The other existing browser regression cases use synthetic provider transport;
their media results are software evidence only.

## Executed verification

Environment: macOS arm64, retained `.venv` Python 3.12.13 selected via
`uv run --locked --no-sync`, uv 0.13.1, Node v24.18.0. Evidence is local on this
envelope; no Linux/hosted or installed-package claim.

All focused commands use `uv run --locked --no-sync python scripts/verify.py focused`
with the explicit selectors below (Vitest/Playwright paths are frontend-relative).

| Selection | Result |
| --- | --- |
| `--pytest tests/test_autopilot_images.py --pytest tests/test_autopilot_early_reference_limits.py --pytest tests/test_video_batch.py --pytest tests/test_delegated_qa.py --vitest tests/autopilot-review.test.ts` | 61 Python + 27 UI passed |
| `--pytest tests/test_provider_budgets.py --pytest tests/test_autopilot_continuation.py --pytest tests/test_autopilot_exec_pool.py --pytest tests/test_video_batch_recovery.py` | 93 Python passed (69 budget cases at that point) |
| `--pytest tests/test_autopilot_profile_transactions.py --pytest tests/test_autopilot_policy_decoding.py` | 34 Python passed |
| Final `--pytest tests/test_provider_budgets.py --vitest tests/provider-budgets.test.ts` | 71 Python + 16 UI passed; includes later independent finite batch preflight and autopilot project-reset cases |
| `--vitest tests/provider-budgets.test.ts --vitest tests/delegated-qa-attribution.test.ts` | Earlier 20 UI passed; final budget file subsequently expanded as above |
| `--playwright e2e/video-batch.spec.ts --playwright e2e/autopilot-review.spec.ts` | 24 browser cases passed |

`quick` passed locked dependencies, API unused imports, all 1,443 frontend cases
then present and both type checks. The final added autopilot-reset case passed
in the focused 16-case file; unchanged unit evidence was reused. The native
ownership discovery guard passed: 3,512 Python / 1,444 Vitest / 339 Playwright
case IDs, without executing test bodies.

Two `npm --prefix frontend run build:deterministic` runs produced identical
SHA-256 static trees: `fd3c890b624063003a3677d8bb227913a165d014b6956fe245d9d3d5357b9ff6`.
After improving the finite screenshot's scroll position, the exact provider-free
case was rerun with `npm --prefix frontend run test:e2e -- e2e/video-batch.spec.ts:88`:
1 passed, both updated captures inspected. `git diff --check` passed.

Retained diagnosis: an initial focused request used the wrong frontend-relative
Vitest path and was refused before execution. A new synthetic cumulative test
initially inserted FK-only claims before their job rows; 4 fixture failures,
65 passes. Explicit job-before-claim flush order fixed the fixture, after which
all expanded cases passed. No production guard/assertion was weakened. Existing
Starlette/jsdom warnings and Vite chunk-size warnings were non-failing.
An additional F401 check of changed Python owners found an already-unused
`sha256` import in batch inventory; removing that import made the check pass.

## Stopping point and remaining work

Implementation and focused source verification are complete for independent
stable diff review. Full local qualification, installed-package checks and
activation remain for the manager's later explicit qualification-owner follow-up;
no full or full-equivalent campaign ran. Hosted CI is optional and was not
requested/run. No live provider call, live grant binding, live queue mutation, owner
approval, installation/restart/deployment, push or network publication occurred.
The active installation and legacy checkout were not used for runtime/API work
or writes. Real provider E2E and creative acceptance are separate.

Known durations: initial focused wrapper 132.360 s, downstream wrapper 65.105 s,
policy wrapper 13.192 s, final focused wrapper 18.058 s, quick 14.186 s, affected
browser wrapper 69.419 s, targeted pixel case run 6.5 s. Some checks overlapped;
product/infrastructure/coordination wall times and usage/cost deltas are
unavailable. Paid provider spend for this assignment is zero (no live calls).

## Independent-review correction: explicit frozen budget members

The manager's stable review of `f1f86c80` found that changing a frozen policy's
omitted-member defaults from finite to null could silently widen an unchanged,
matching-hash raw payload. The analogous batch reader used the request model's
defaults for frozen setup. Raw hashing proves bytes, not omitted-field authority;
the fix belongs at frozen admission rather than a runtime budget workaround.

`LaunchPolicy` now requires both nullable caps for every supported version;
`LaunchRequest` still defaults omissions to null, and the existing builder freezes
both explicitly. The portable batch reader requires both canonical budget keys
before decoding setup; new `BatchSetup` requests still default to null and the
existing inventory builder serializes both. Ambiguous omissions fail through the
existing corruption contract with a missing-field cause. No compatibility
defaults, migration, retained-data rewrite or finite-scope change was added.
Four synthetic policy builders now state their null authority explicitly.
ADR 0200 distinguishes new-request defaults from explicit frozen authority.

New regressions cover omission of either/both frozen members with a matching raw
hash, all policy versions 1–4, unchanged explicit finite/null admission and hashes,
portable batch refusal and no evidence rewrite. `tests/test_provider_budgets.py`
passes 94 cases through `verify.py focused --pytest tests/test_provider_budgets.py`
(19.395 s wrapper). A second `verify.py focused` run passed 118 cases with these
explicit selections (53.441 s wrapper):

```text
--pytest tests/test_autopilot_policy_decoding.py
--pytest tests/test_autopilot_profile_bindings.py
--pytest tests/test_autopilot_authority.py
--pytest tests/test_autopilot_view_checkpoints.py
--pytest tests/test_delegated_qa.py
--pytest tests/test_video_batch.py
```

Both use `uv run --locked --no-sync python scripts/verify.py focused` in retained
R. Logs remain in the same ignored local evidence folder, under
`correction-budget-focused.log` and `correction-admission-focused.log`.
`git diff --check` also passed. Existing Starlette deprecation warnings were
non-failing; neither correction selection failed.

This correction changes no frontend or assets; prior deterministic-build/UI
evidence remains unchanged. Full qualification and activation are still held for
the manager's exact-finding re-review. Requested settings remain
`gpt-6.1-sol / medium`, effective unverified; no additional authority is exercised.
