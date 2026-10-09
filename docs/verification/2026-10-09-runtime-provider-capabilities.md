# Runtime-owned provider controls — October9

Scope: E22.1/.2/.3/.5 in the [current lifecycle run](../roadmap/2026-10-07-full-creator-e2e-repeat.md).
Source candidate follows `4ac80c5`; this receipt does not close Create → Revise → Recover.

## Demonstrated cause and repair

Native authoring deliberately omits API text admission/dispatch and therefore
provider-profile routes. The workspace offered the provider settings launcher
anyway, and presented an initial form default as checked backend evidence. Its
initial profile read was incorrectly coupled to draft capability absence/failure.
Actual native8865 returned404 for that launcher; this was not a credential failure.

[ADR0144](../adr/0144-runtime-owned-workspace-capabilities.md) replaces the old
draft-only endpoint with required runtime capabilities, without an alias or fallback.
The server owns provider availability using the same composition condition as
route registration. Loading/failed reads stay unknown, with explicit read retry.
Native mode keeps assistant settings and explains that API text providers are not
enabled; it does not invent provider readiness or enable an API fallback. In API
mode, status comes from the loaded active profile rather than an unsaved form.

## Qualification

- Before implementation, both new real-composition Python regressions failed404.
  Afterward,11 focused Python checks pass: both compositions, retained runtime
  inventory, project-owned image workflow and production runtime boundaries.
- Full frontend908 checks/112 files pass, as do application/E2E types and the
  deterministic paired static build. Malformed capability responses remain unknown;
  deferred reads preserve local draft ownership and explicit retry.
- The final combined browser command passes17 tests in36.3s with no local retries:
  runtime-provider capabilities, provider profiles/settings recovery, project-folder
  authoring drafts and Close. This includes real server restart, draft CAS conflict,
  queued media draft draining, failure preservation and explicit recovery.
- Native-composition browser evidence proves no profile requests from the tested
  idle sample UI; the API-enabled failure case sends none before explicit retry,
  then exactly one catalog read when settings open. It is not an all-state zero-request
  claim: an exact frozen API run still retains its own credential/profile read contract.
- Root inspected all six final capability viewport PNGs at1700×900,1280×768,
  1280×460. Native explanation/assistant controls and failed-read retry are readable.
  At short height the sidebar is intentionally scrolled to its footer; screenshots
  do not claim the entire tall sidebar fits without scrolling.
- The retained independent reviewer inspected the stable source/tests/inventory
  delta and all six earlier same-candidate final PNGs, finding no blocker. Its model
  and effort are inherited, not independently verified; no second source writer.

Evidence is retained under
`output/playwright/native-intent-2026-10-08/runtime-capabilities/`.
The final17-test run additionally retains artifacts in
`frontend/test-results/runtime-capabilities-adjacent/` of the isolated checkout.

## Preserved failures and method corrections

The first browser run passed six existing journeys but its two new viewport checks
failed at1280×460 because they did not scroll the existing sidebar footer into view.
Actual pixels and sidebar overflow CSS identified a harness assumption, not a
product layout failure; the test now performs that real scroll before inspection.
A later retry assertion assumed one initial request, although development StrictMode
replays the effect. The test now records the settled initial count, proves no reads
from scrolling, and requires exactly one additional explicit retry. The non-StrictMode
unit still checks one initial read. After two failed acceptance attempts the cause
and method were reassessed before the successful final run.

Two existing frontend tests initially assumed provider controls without declaring
runtime capabilities. They now explicitly compose the API-enabled fixture; none of
their behavioral assertions were weakened. The inventory update changes only the
existing image-workflow function entry to the new complete capability contract and
its function-source hash.

## Remaining and deployment boundary

The candidate is isolated and not activated on normal8841. Actual native8865
activation/readback is a subsequent checkpoint, not inferred from the fixture.
The broader native UI may still offer generic API-run actions whose routes are
not composed; this is a separate owning-layer audit, not covered by hiding the
provider launcher. The sample's “Plotloom 服务：未连接” label also reflects project
loading rather than a verified server connection and remains a wording/authority lead.
Revised routes, hand-only identity semantics, report-generation context and other
applicable Creator/Pro/directory state permutations remain incomplete. No generation,
protected settings write, lease release or owner-data mutation occurred in this slice.
