# Native test module ownership

Run the ownership check with:

    uv run --locked --no-sync python scripts/testing/check_module_ownership.py

The guard performs pytest collect-only, Vitest list and Playwright list. It
does not execute test bodies. It refuses ambient selectors and fails when a
native test file is missing from the map, a mapped file collects no cases, a
source test file collects zero cases, a file has multiple owners, or the
module case union differs from the complete native inventory.

scripts/testing/module-ownership.json is the reviewed source of truth. Each
test file belongs to exactly one module and the guard expands all native case
rows under that owner. support_dependencies records the runner configuration,
global setup, fixtures and helpers used by each suite, including the product
modules that consume cross-domain helpers. Support dependencies document
selection closure; they do not create duplicate test ownership.

Run selected owners through the existing verification runner:

    uv run --locked --no-sync python scripts/verify.py module --module graph --depth contract

`contract` runs pytest and Vitest owners, `browser` runs Playwright owners, and
`complete` runs every nonempty suite owned by the selected modules. Multiple
`--module` arguments make one deduplicated union. The manifest's
`required_complete_gates` assigns build/package gates to their owning module;
those gates run only at `complete` depth. The current verification-tooling
owner requires the lock check, static bundle build/parity, browser allocation
guard and wheel build/smoke.

Every module execution runs the native ownership guard before selected test
bodies and refuses ambient filters. Use `--show` to review owner rationale,
file selectors, shared dependencies, required and omitted checks, and exact
commands without running them. A module result is scoped development evidence;
it is not the full release gate.

Vitest's list JSON does not expose row identity beyond file and title for some
parameterized cases. When multiple discovered rows share those fields, the
guard preserves the native list order and adds an occurrence number and total
to each normalized ID. It keeps all rows and their multiplicity, though the
parameter values themselves are not present in the native listing.

The module ownership guard is distinct from test execution and from the
quick, focused, module and full verification tiers. Module selection does not
infer scope from changed files; the implementer maps changed owners and
consumers to the reviewed manifest.
