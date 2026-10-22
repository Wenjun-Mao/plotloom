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
activation/readback is recorded below, not inferred from the fixture.
The broader native UI may still offer generic API-run actions whose routes are
not composed; this is a separate owning-layer audit, not covered by hiding the
provider launcher. The sample's “Plotloom 服务：未连接” label also reflects project
loading rather than a verified server connection and remains a wording/authority lead.
Revised routes, hand-only identity semantics, report-generation context and other
applicable Creator/Pro/directory state permutations remain incomplete. No generation,
protected settings write, lease release or owner-data mutation occurred in this slice.

## Actual native checkpoint

Root approved the stable isolated source checkpoint `814264e`. Before stopping
owned8865/PID52578, the registry reported busy:false/activeTasks:[], runs were empty,
all8 image jobs delivered and all7 videos ingested. The initial restart omitted the
prior process-only H3 catalog override and failed before application startup. The
same launcher/data/configuration then started PID89080 with explicit
`VIDEO_PROVIDER=minimax_h3_gateway VIDEO_MODEL=minimax_h3_gateway_catalog_v7`;
no protected environment file was edited. Health is200 and H3 remains enabled/v7.

All8 domain response hashes and all42 managed asset path/hash entries match the
pre-restart state; project content2/lifecycle5/active and job counts stay exact.
The retired endpoint returns404, the new endpoint explicitly reports native API
profiles false, and served JS equals checked SHA256
`429b3c4f7134d0d00dcbd5df583fe01bd4b0eb6c22bbfbcab27c2e0e2c529444`.

The actual loaded native Source page makes17 API GETs during the qualified
reload/read/desktop-scroll exercise, zero unsupported profile requests and zero
API mutations. Provider launcher is absent and assistant settings remains visible.
Root directly inspected `inspected-native-{size}.png` at all three desktop sizes;
the complete footer explanation and button are visible after real sidebar scroll.
`native-runtime-checkpoint.json` records exact preservation/readback evidence.

Two preliminary actual-native capture sets are not acceptance evidence:
`actual-native-1700x900.png` captured before project loading finished, and
`qualified-native-1280x768.png` scrolled only the button, clipping the explanation.
After these two failures, capture ownership was reassessed: require exact loaded
source title and the entire footer bounding box within the viewport, then inspect
pixels. No layout patch or relaxed geometry was used to make a harness pass.
Independent review directly inspected all three final native PNGs and preservation
JSON, finding no footer clipping/overlap or misleading capability claim. It identified
the JSON's preliminary screenshot-prefix reference; root reconciled it to the
`inspected-native` files and explicitly excluded both preliminary capture failures.
This is separate from its already closed fixture/source review. Normal8841 remains
unchanged; broader API-run controls and the full lifecycle goal remain open.

## Generic API-run controls — reviewed extension

The next native audit reproduced an enabled “运行所选阶段” and guidance to start
an API run, although that runtime deliberately omits those routes. The same
assumption affected Brief generation, repair/rebuild and retained-run loading;
the Brief callback could save before its unsupported execution request failed.
Before-fix actual-native Trace pixels are retained as
`native-api-trace-before-{size}.png` under the run's native evidence directory.

ADR0144 now assigns the complete profile/execution/progress/trace route group to
one required `apiTextPipeline` capability, replacing the unpublished profile-only
field without an alias. Every generic command checks admission before reads,
credentials or mutations, including before Brief saving. Native retained runs
remain readable summaries, without polling, auto-resume or missing-route reads.
Unknown reads stay unknown with explicit retry; native specialist flows remain.

The stable source passes923 frontend checks,10 focused Python checks, both
typechecks and11 browser journeys. Root independently reran67 command/loader/
session/presentation checks and directly inspected all six retained failed/running
summary PNGs at the three supported desktop sizes. Independent source/test/pixel
review found no actionable issue; its suspected late-capability race was checked
against the loader's synchronous capability ref and cleared. These summaries are
controlled browser responses against the real native composition, not new native
run-lifecycle evidence. The full backend gate is still running at this checkpoint.

The generic API extension was committed at772c78b and activated through an idle-only
restart of owned8865/8866 with the same H3v7 process override. Its actual Trace,
Brief and repair reading exercise made13 GETs, zero unsupported profile/detail reads
and zero mutations. Root inspected ten native viewport captures across all three
desktop sizes; served JS SHA256 was
`a59d6a5b85586933a8525db08d8a04bb7450aa7d24a5f856d8d358e25cea7c59`.
All eight domain responses and42 managed asset path/hash entries remained exact;
the specialist registry was idle and runs empty. The earlier814 checkpoint JSON
remains historical evidence, not rewritten to imply this newer activation.

The772 full Python run finished1417 PASS/1 stale coverage-catalog FAIL. An exact
one-function-hash/one-assertion update preserved all37 assertions and the checker;
four focused tests and independent review passed. The fresh full rerun now passes
**1,418 tests**, with one existing Starlette warning. Later Trace/Brief wording and
graph/directory read recovery are a separate reviewed candidate whose native
after-activation checks remain pending. Normal8841 is unchanged; wider lifecycle
acceptance remains incomplete.
