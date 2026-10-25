# Browser fixture contract repair — 2026-10-15

> Local QA artifact references below are historical; the [2026-10-25 cleanup](../roadmap/2026-10-25-top-five-cleanup.md)
> retires their storage, replay/launch/cutback instructions and preservation holds.
> Recorded outcomes and limits remain; current ADR/API contracts still apply.

## Causes and repair boundary

The full gate on `6863fd91cc4d1700cf10b54f7c6b68d68a251fe5` ended
with 280 browser passes and 39 failures. Thirty-eight shared one fixture error:
English F4 dialogue inherited the demo Brief's Chinese spoken language, causing
real F5 preparation to refuse capacity before the intended browser operation.
The remaining creator test read authoritative state before its final save
receipt. The retained trace shows that final PUT successfully persisted both
literal strings; it does not demonstrate lost product data.

The six-file repair changes browser fixtures, assertions and their owning README:

- Default this English fixture's spoken language to `en`, before caller overrides.
  Keep initial stages, delivery writer, upstream renderer and server admission.
- Change exactly 22 Storyboard dialogue labels to English. Text, cuts, durations,
  beat ownership, rates, budgets and full authored routes stay unchanged.
  Current candidate SHA-256 is
  `c3961f73e063aeb361ec44c8a86d8215d6b0f118bd608e867a2b60d60923eb63`;
  the README preserves the original predecessor hash as historical evidence.
- Check frozen timing language/input bytes, accepted Script revision/hash, timing
  limits, and full routes including the route-only decision. Both positive
  dialogue assertions and the provably effective removal negative remain real.
- Require candidate POST 201 before the existing intercepted 503/read-retry test.
- Hold only the exact final graph PUT before forwarding it, prove Save disabled,
  then await its real receipt and UI completion before comparing the authoritative
  draft's revision/payload. Preserve literal DOM, topology, Escape zero-write and
  no-generation assertions; release, settle and unregister the exact route.

No production/UI/schema/upstream/adapter/dependency/runner/ownership change is
included. The fixture README captures language ownership and save acknowledgement
rules. Existing production contracts are unchanged; no new ADR is required.

## Executed scoped checks

- `npm --prefix frontend run typecheck`: passed, handle 19738, exit 0.
- `npm --prefix frontend run typecheck:e2e`: passed, handle 69985, exit 0.
- `uv run --locked --no-sync python -B scripts/verify.py focused --playwright
  e2e/storyboard-source-review.spec.ts --playwright e2e/source-review-currentness.spec.ts
  --playwright e2e/creator-workbench-text.spec.ts`: **22 passed**, 56.579 seconds
  at the runner, handle 77307, exit 0. Whole files, no retries or ambient filters;
  locked offline/no-sync environment. Original handles were attended to exit.
- `git diff --check`: passed. All 95 qualified F5 source input hashes match the
  original native proof. The exact six-file diff leaves backend, Vitest, shipped
  frontend/bundle and package inputs unchanged. No asset rebuild is needed for
  browser test inputs.

Evidence is retained under ignored
`.local/native-proof/browser-rca-6863fd91-20261015/`: `focused-browser.log`
(SHA-256 `b8a2bad7800f7a3aeaeee453770b01f35cad8006cdb1085817e21d925f5fab64`),
both typecheck logs, `implementation-boundary.json`,
`implementation-preservation-audit.json`, and `focused-artifact-manifest.json`.
All 41 PNG captures were copied into `focused-artifacts/` before future runs.
Desktop pixel inspection covered the literal creator viewport, failed-read retry
state and retained stale review at 1280×768; these support the existing assertions.

Original 39 failure directories (176 artifacts), original full log, 394 historical
file pins and 2,587 files in six historical roots were rehashed unchanged. No real
credentials were read; historical source/profile labels remain their original ones.

## Qualification limits

Independent stable code/wording review found no required corrections (completed
turn `01a13dcb-6841-7391-b9d1-235bb5e88bea`, read-only static review). The manager
also reviewed the complete diff, focused log and desktop captures without further
findings, and owns the later unfiltered browser gate. Prior 6863 Python (2,367), Vitest (1,381),
bundle and separately completed wheel/smoke evidence remains tied to its unchanged
input bytes; the failed original full invocation remains failed. No full rerun,
new native preflight, campaign preparation, provider generation, push, merge,
hosted CI or product acceptance is established here.
