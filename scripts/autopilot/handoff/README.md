# Bounded CLI handoff capsule

This workflow implements [ADR 0178](../../../docs/adr/0178-capsule-plan-handoff-authority.md). The capsule verifies its actual internal
function source and canonical plan against an independent anchor. The trusted
tiny outer invocation supplies `tools, planText, anchorText, anchorSha` once and
awaits the result. This is not whole-body/caller/host attestation or enforcement
against arbitrary code deliberately bypassing the verifier.

`capsule.mjs` is an offline template, not an immediately runnable operator body.
`../handoff_bundle.py` binds exactly four literal source-root tokens and the QA
pin hash, copies the current fixed source closure into a fresh empty owner-0700
directory, writes owner-0600 source controls and refuses overwrite/stale bytes.
The resulting capsule contains one literal file URI. No plan selects a module.
After sealing, no writer may modify B. Import pre/post checks cannot establish
atomic import integrity or cached-module provenance by themselves.

Source files belong in immutable B. Mutable runtime roots begin with only
`phase.json`; owner/check receipts live outside them. JS and Python use fixed
registries for `B/proof_launch.py` / `B/proof_receiver.py` and the real
`B/paid_launch.py` / `B/paid_receiver.py`. `handoff_plan.py` produces strict v3
descriptor/plan/anchor DATA from the sealed bundle, with no target execution.
The proof kind cannot substitute for `paid_outline_once` allocation authority.
The old missing-paid-entry refusal remains historical evidence; the current real
entry's genuine paid qualification is still OPEN.

`paid_outline_prepare.py` requires caller-allocated empty private roots, explicit
Brief/launch policy inputs and QA file pin. It uses the real project owners to
prepare source/Outline and reserve the actual attempt, then pauses. It creates
no dispatch. Seal its canonical returned allocation in B before producing phase,
plan and independently approved anchor. No operator allocation values or launch
release are supplied by this source implementation or its tests.

The allocation binds actual committed source and independent workflow/profile
closure, exact disposable catalog/home/database identities, paused run and claim
revision edges, frozen policy/Brief/material/package/validator identities, and the
persisted one-attempt supervisor namespace. QA is separate from the checked
validator environment. `paid_outline_run.py` consumes only after genuine committed
attendance and a late source/deadline gate at the core consume boundary. It polls
only that attempt, validates the typed receipt/delivery, and pauses at HOLD without
adoption, images, continuation or retries. A failed pause is reported as unacknowledged;
it is never converted into a successful HOLD. Witness provider/production flags stay false.

Repository regressions create fresh pinned bundles from current source; no
retained `.local` packet is needed:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_cli_handoff_capsule.py \
  --pytest tests/test_cli_handoff_receiver.py
```

The Node suite is invoked by the first pytest owner with isolated fake tools.
Its receipts are pre-reserved 0600 before the writer starts, and full TAP/stderr,
exact command/exit/source pins are retained in the pytest fixture root. The
Python owner uses the actual shared receiver and immutable import origins.
All fixture records/process rows/handles are labeled synthetic evidence. They
do not prove a real launch, process observation or handoff.

Paid source regressions use `tests/test_paid_outline_handoff.py`, with lifecycle
guards in `tests/test_paid_outline_processes.py`. They create a separate committed
fixture checkout and metadata-only Python identity. Outline validation/rendering
executes the real frozen Node commands through the external CLI stand-in and
preserves real results; this is not Mac sandbox or provider qualification. Exact
spawn identities and descendant journals own teardown. Missing ownership retains
UNKNOWN evidence and fails settlement rather than claiming the machine is quiet.

The operator bundle is a different, separately allocated root. Its no-work host
capability check uses `authority=capability_check`; this action cannot create
intent or call native dispatch. Record actual fixed import/export/source and
cache observations separately from the first-use/no-concurrent-writer assumptions.
This branch performs two sequential real helper capability actions through one
awaited capsule. Each independently rechecks the same source authority; both
capability results and per-action verification diagnostics are returned. Evaluation
IDs must be nonempty, but matching IDs are not authority and differing IDs alone
are not source drift. No generic action-sequence entrypoint exists. B01's first
capability pass and later constant-ID observation failure remain historical;
neither qualifies the revised two-action path or attests host cache behavior.
No genuine native proof or provider/paid work is released by source or tests.

Keep the original receiver monotonic deadline, exclusive intent, final singleton
marker checks, payload readback then empty commit, original/observation handle
separation and possibly-committed UNKNOWN/no-retry semantics. Parent qualification
still needs genuine natural terminal and phase/admission reconciliation.
