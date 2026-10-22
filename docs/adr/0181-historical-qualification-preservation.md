# ADR 0181: Historical qualification preservation

Status: Human-approved decision, implemented candidate, 2026-10-16;
independent/Root review pending.

Related: [0178](0178-capsule-plan-handoff-authority.md) owns finite pair
authority, current-allocation settlement and serial-before-parallel admission.

## Context

The retained pair failed a historical preservation guard with `retained native
group is present`. Its particular cause remains **UNKNOWN**: the evidence does
not demonstrate PID reuse or surviving original work. Historical-only checks in
`preservation.py` and `campaign_guard.py` also sampled old numeric PID/PGID
values with signal zero. Recyclable numbers do not establish original ownership,
and material preservation does not establish current process liveness.

## Decision

Historical qualification gates verify retained byte inventories, outcomes,
terminal ledger structure, matching successful receipts and material limits.
They do not resample historical numeric PID/PGID values. Their result labels
retained ledger facts separately and leaves current historical liveness
**UNKNOWN**. Original failures, cleanup limitations and sealed evidence stay
unchanged; no historical PASS or absence claim is reconstructed.

A shared private ledger check may validate data for either boundary. The
historical material entry calls only that data check. Current-allocation
`require_zero_live_original_work` additionally requires the original groups
absent. `require_successful_current_arm`, UNKNOWN capacity, receipt integrity,
admission/deadline/HALT/source/runtime fences and strict serial-before-parallel
activation remain fail-closed and unchanged. No mode flag or compatibility alias
may hide the historical/current distinction.

Known-live original owners and named current dependencies cannot be bypassed by
calling them historical. A future historical-owner liveness prerequisite must
be explicit and use identity-bound evidence under separately scoped authority.

## Alternatives and consequences

Keeping indefinite numeric-only historical probes conflates ownership and
material preservation. Skipping all historical validation or loosening current
settlement would remove valid safety gates. Both are rejected.

Fresh qualification needs its own exact source/runtime/allocation baseline and
reviewed launch. This decision authorizes neither preparation nor generation,
runtime repinning, cleanup, changed budgets, old-root mutation or Python work.

## Guardrails

Test-owned historical fixtures must pass without any old PID/PGID probe even
when synthetic numeric identities would appear present. Corrupted historical
files, outcomes, ledgers and receipts still refuse. Current live, UNKNOWN or
unsettled work and a failed serial arm still refuse. No actual historical
endpoint probes or evidence mutations belong in these checks.
