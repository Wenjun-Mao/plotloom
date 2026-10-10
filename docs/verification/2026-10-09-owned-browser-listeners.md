# E2E browser-fixture listener ownership

Scope: repair the demonstrated hosted fixture failure during the approved full
creator E2E run. Application/generation/fork pins and production port behavior
are unchanged. [ADR0152](../adr/0152-owned-browser-fixture-listeners.md) owns the
test-startup contract. Local qualification is complete; a fresh exact-input hosted
run remains pending. Independent code review is clear.

## Original failure and causal evidence

Run[38009336409](https://github.com/Wenjun-Mao/plotloom/actions/runs/38009336409)
uses exact executable/test head2a9364947240d5da9e8d94ae674ae37aab2e8780.
Verify job114085443411 passed1464Python/1037frontend and packaging/build gates.
Browser job114093851328 completed successfully with132passed and1flaky. Its
first Source dirty-refresh1280×768 attempt failed before the UI; retry passed.
Browser job114093851297 completed successfully at2026-10-10T01:44:28Z. Its actual
log records143PASS/zero flaky/zero failed in34.6minutes, one worker, shard1/2,
at the exact head above. No first-failure or retry entry is present. Aggregate:
**275PASS/one flaky across276tests**. The workflow is green, not a clean
first-pass gate or evidence for the later repair.

Independent artifact inspection proved duplicate role allocation: failed
`test.trace` lines16–17 show successful provider readiness at
`127.0.0.1:35937/control/status`; lines18–19 then show backend readiness at
the same port's `/openapi.json` and exact-port bind refusal. Source returned
numbers after closing each probe, allowing the next probe to reuse that address.
No external collision, lingering process or TIME_WAIT cause is needed or proved.

Retained original artifact11654871773 (`playwright-test-results-2`) and its
failed trace are under `/private/tmp/plotloom-port-artifact-review.o0X8N5`.
Shard1's log is retained there as `shard1-job-114093851297.log` (summary line1285).
The failure remains recorded separately from a passing retry. Node action
deprecations/migration, uv-build/installed-uv and the existing Starlette/httpx
warnings are separately noted maintenance warnings, not evidence for this cause.

## Repair and focused evidence

Each provider/backend/frontend now publishes an address only after binding and
retains the actual listener. Python hands that socket to Uvicorn; production
settings receive only the resulting positive exact port. The Node frontend first
binds its parent HTTP listener, then loads the ordinary Vite config/proxy through
public middleware composition with that positive port. `middlewareMode.server`
and `hmr.server` both name the owned parent, with its actual `clientPort`; the
parent is explicitly closed after Vite cleanup. This avoids locked Vite7's
default-port substitution for `listen(0)` and a frozen0 HMR fallback target.
Backend restart keeps the same exact origin/roots.
No production fallback, retry increase, sleep workaround, adapter or owner-data
mutation is introduced. Existing fixture cleanup/deadlines remain authoritative.

- Python:5new deterministic ownership cases plus14existing config/runtime cases,
  **19PASS**, one existing Starlette deprecation warning. Additional extraction,
  project-folder runtime and dependency boundaries: **20PASS**, same warning.
- Focused frontend:10new receipt cases plus3existing readiness cases,
  **13PASS**. Entire frontend: **1047PASS/126files**; both type gates pass.
- First focused browser run: **10PASS/2FAIL**. Both failures were new-test exact
  label selectors, not listener startup or product behavior. Recorded snapshots
  expose the actual textbox name; correcting only those tests to the exact
  accessible textbox role/name produces **12PASS/25.7s/zero retries**.
- The first corrected cases included exclusive live bind refusal for every role,
  distinct origins, Vite proxy/WebSocket creation, checked-static serving, saved
  project equality and browser readback after an exact-address backend restart.
  That historical run observed creation, not a connected HMR frame.
- Independent review found an introduced Vite startup defect: initialization
  with0 before direct HTTP binding froze0 into its HMR fallback. Root stopped
  the first full sweep, bound the parent before Vite initialization and attached
  both middleware and HMR to it. Fresh final focused browser checks pass
  **12tests/25.1s/zero retries**. They now wait for the actual HMR `connected`
  frame and inspect transformed `/v2/@vite/client` for the actual direct target.
  This proves connected HMR and correct generated fallback configuration, not
  execution of the fallback branch. Final independent read-only review found no
  code issue and requested the distinct parent settings/evidence wording above.
- Deterministic build, API F401 lint, wheel and installed-wheel smoke pass.
  Checked frontend bytes remain unchanged; JS SHA256 is
  `0a4fd0e721b819da4ffec7d946e0af8f7c9ae3a90e9c4d473972951ac3ace160`.
- An initial boundary command named nonexistent files; its exit4/no-tests result
  is not a PASS. Repository-discovered boundary files and the established API
  lint command produced the successful checks above.

Focused browser evidence:
`/private/tmp/plotloom-owned-listeners-focused-20261009` (failed first attempt),
`/private/tmp/plotloom-owned-listeners-focused-corrected-20261009` (first corrected),
`/private/tmp/plotloom-owned-listeners-hmr-focused-20261009` (final passing).
The first full278browser sweep was intentionally interrupted for that review
finding: **54PASS/two interrupted/222not run**, exit130. It is not a full PASS or
a new product failure. Its evidence remains at
`/private/tmp/plotloom-owned-listeners-full-browser-20261009`.
Fresh unfiltered browser gate completed **278PASS in15.4minutes**, two workers,
zero retries, exit0. All nine changed executable/test input hashes stayed identical
through the gate and were checked again after it completed. Its terminal
`.last-run.json` records `passed` and no failed test IDs. Evidence:
`/private/tmp/plotloom-owned-listeners-qualified-full-browser-20261009`.
Wheel: `/private/tmp/plotloom-owned-listeners-wheel-20261009`.

## Acceptance and preservation boundary

This is test-harness qualification, not another creative or native media run.
Normal8841 activation, the retained-owner decision, absent Scene/Prop downstream
consumer, unconfigured API intent, missing populated native Cast-relationship
evidence and unobserved E22 permutations retain their existing dispositions in
the [presentation receipt](2026-10-09-presentation-authority-qualification.md).
Neither a corrected test nor eventual hosted success closes those boundaries.
No native generation, acceptance, media selection, normal restart or owner reset
was requested by this repair.
Fresh read-only protection returns the unchanged aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
17/67 managed files in the two owner projects and three protected configurations.
The normal checkout remains clean.
