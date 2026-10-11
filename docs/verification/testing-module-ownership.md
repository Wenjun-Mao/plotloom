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

Vitest's list JSON does not expose row identity beyond file and title for some
parameterized cases. When multiple discovered rows share those fields, the
guard preserves the native list order and adds an occurrence number and total
to each normalized ID. It keeps all rows and their multiplicity, though the
parameter values themselves are not present in the native listing.

The module ownership guard is distinct from test execution and from the
existing quick, focused and full verification tiers. M2 will add named
module execution with explicit dependency expansion; this metadata does not
infer selection from changed files.
