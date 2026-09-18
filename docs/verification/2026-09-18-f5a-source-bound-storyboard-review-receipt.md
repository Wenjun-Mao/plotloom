# F5A source-bound storyboard-review lifecycle receipt

Date: 2026-09-18. This receipt records implementation and focused automated
verification of the F5A lifecycle. It is not a new specialist delivery, human
creative review, production admission, or media proof.

## Delivered boundary

F5A adds a distinct `storyboard-source-review` lifecycle. It starts only from a
current accepted F4 script and freezes that script revision/hash, its inherited
source/outline/section-map/graph/cast/art/timing binding, and the exact ordered
section-to-episode mapping. Its F0 manual package provides the accepted raw
`script.json`, execution-only upstream `outline.json`, cast/art context, and a
small trusted admission artifact.

The receiving owner runs the pinned `novel-storyboard` validator and accepts
only the raw `storyboard.json` plus unmodified derived `report.html` as a
source-bound **review revision**. A changed F4 script or any inherited input
makes preparation/admission/acceptance stale. Prepared publication blocks
project lifecycle transitions and explicit cancellation rejects late delivery.

F5A deliberately uses a separate route/table/API surface from the existing
canonical-shot `/storyboard-review` contract. It creates no V2 Bible or
SceneBeats projection, canonical shot, player content, selection, media prompt,
dispatch control, reference, H3 timing change, or approval.

## Baseline verification

- `uv run --locked pytest -q tests/test_project_storage_art.py` — 17 passed.
  The F5A cases cover F4 identity/mapping freeze, lifecycle blocking and late
  delivery refusal, mapping rejection before upstream validation, accepted-review
  staleness following an F4 edit, and restart-compatible project storage.
- `npm run typecheck` — passed.
- `npm run build:deterministic` — passed; refreshed the committed static bundle.

The focused lifecycle test stubs the upstream validator only for an artificial
accept/reopen state transition; production admission always invokes the pinned
validator. No gateway, ImageGen, H3, provider, database fixture, retained
project, upstream/submodule, or human creative artifact was changed.

The original baseline receipt was incomplete: prepared F5A publication was not
an explicit snapshot/recovery blocker, duration limits were left solely to the
upstream validator, and a retained stale review trapped replacement. The
correction freezes F4 caps/routes plus 2–8 second cuts and 15-second segments,
checks actual raw cuts before upstream validation, releases recovery after
cancellation, and makes recovered handoff text visible/copyable. UI responses
are ownership-guarded, so delayed load/refresh/error/busy callbacks cannot
mutate a switched or unmounted project.

The earlier independent attended Terra/high read-only review was baseline-only;
it did not establish end-to-end acceptance of the final integration delta. It
found and the coordinator
resolved two material lifecycle defects before this receipt: F5A acceptance no
longer permits client JSON to differ from the admitted candidate/report bytes,
and a ready candidate must be explicitly accepted or cancelled before another
can be prepared. The regression suite covers both guards. The follow-up review
found no remaining material issue.

## Test-first integration closeout

The preserved rejected/unpushed baseline is
`bf4cc116706ceeff0801a6e382ecef92ca61b116`. Implementation fixes are committed in
`302fb7095a52cdb29fa930386b2f324846742ecf`; the final executable/test/coverage
candidate is `ba271a6b3a9267dff4d103943339d8cbcddb82e9`. Receipt and roadmap
closeout are subsequent documentation only. Main is intentionally unpushed.

The first production FastAPI/file-SQLite browser run invoked the real receiving
validator with genuine current request packages. It demonstrated missing readable
reference fields, stale prepared re-copy, unfrozen minimum-cut params and snapshot
rejection of the original valid upstream report. A separate ready-replay run
proved stale ready replay incorrectly returned 200. Failures were retained before
fixes. The receiving owner now checks currentness before both re-copy and ready
idempotency, requires all three frozen timing params, and retains actual duration
and pinned upstream gates. The UI shows `frame`, size/camera, character/prop
reference needs, scene/beat ranges and unchanged H3 direction/dialogue.

Snapshot rejection originated in the credential scanner treating the report's
`e.key === 'Escape'` as a secret assignment. Its equality correction preserves
credential assignments, recognizable secret forms and credential-bearing URL
checks. The original report is neither rewritten nor bypassed. New regressions
cover those credential protections and 2–8 second cuts, 15 second segments,
section/route ceilings and params tampering.

The portable deterministic fixture preserves storyboard SHA-256
`50165863d45e678c28bcf794c6f9f5444b6aa45eef2caa446595dd638313578a` and matching
script/outline/cast/art/map inputs. Tests create disposable current-schema projects
through production HTTP APIs; report HTML is derived with the pinned upstream
renderer. The receiving validator runs again on refresh and acceptance without a
positive-path stub. All 22 script dialogue bindings are inspected within their
correct episodes, including shared wording in mutually exclusive endings.
Completion provenance is explicitly a deterministic fixture, not a new specialist
run, creative approval or live generation. The old invalid historical package is
not retested or rewritten.

### Executed final checks

Full commands, stdout/stderr, exit statuses and retained failures live under
`.local/relay/c01a3e43-3860-4d39-97a3-7ff55eb119ad/logs/`. The final candidate was
validated in its fresh recursive local `final-clone/`, pinned to unchanged
Shuohao `4322897e6d2bdaf66365534fd40194360c75a85f`; no source edits were made there.

| Command | Actual result | Full log |
| --- | --- | --- |
| `uv run --locked pytest -q` | 627 passed, one existing Starlette deprecation warning | `python-full-final.log` |
| `npm test` | 162 passed / 18 files | `frontend-units-final.log` |
| `npm run typecheck` | passed | `frontend-types-final-clone.log` |
| `npm run typecheck:e2e` | passed | `e2e-types-final-clone.log` |
| `npm run build:deterministic` twice in the retained source-owner checkout | identical static SHA-256 maps; committed bundle matches final clone | `build-static.log`, `build-static-repeat.log`, `static-determinism.log`, `final-clone-revision.json` |
| `uv build --wheel --out-dir dist` then `uv run --locked python scripts/smoke_installed_wheel.py dist` | fresh wheel build and fresh installed-wheel smoke passed | `wheel-build-final.log`, `wheel-smoke-final.log` |

Final focused browser command in that exact clone:
`npx playwright test --config playwright.config.ts e2e/storyboard-source-review.spec.ts e2e/storyboard-review-ownership.spec.ts --workers=1 --output=/Users/wjmao/projects/HU/plotloom/.local/relay/c01a3e43-3860-4d39-97a3-7ff55eb119ad/browser-final-clone`
— **18 passed**, actual process exit 0 (`browser-final-clone.log`). Its owned
FastAPI, Vite and offline provider processes were stopped by fixture teardown.
The committed tests cover exact prepare/reload/re-copy assignment, real delivery
and original report, explicit immutable review acceptance, restart persistence,
ready rejection/replacement, upstream staleness/replacement, cancellation/late
delivery/snapshot release, admission-file and ready-manifest params tampering, and
12 held load/copy/refresh success/error cases across A–B–A/unmount. Held requests
settle before asserting no stale assignment/error/busy mutation or refresh effect.

The first complete locked clone suite retained 626 passes / one failure in the
retirement inventory. An earlier cast-reference test had added two assertions
without refreshing its current replacement catalog. Only that current record's
hash and additional assertions were updated: all 29 prior assertions, historical
baseline entries, triggers, dispositions and review statuses remain intact. The
focused inventory/current identity test passed and the complete final suite passed.

Harness evidence is also preserved: an initial held-route URL missed Vite's proxy,
a Python helper import used the wrong package path, and a dialogue assertion
incorrectly demanded uniqueness across alternative endings. Each was diagnosed
and narrowed; none was treated as a candidate/schema failure or fixed in upstream.
The interrupted harness run remains recorded as interrupted, not passing.

[Independent attended Terra/high stable-delta review](2026-09-18-f5a-integration-delta-review.md)
found no material F5A issue and separately verified the precise inventory refresh.
It records a deferred scanner arrow-parameter false-positive absent from this
actual report. This review supersedes no creative evidence and the earlier review
remains baseline-only.

The main checkout retains its pre-existing empty `output/playwright` directories.
Its root-hygiene helper reports unexpected root `output`; the exact committed
recursive clone reports none (`worktree-discrepancy.json`). No directory deletion,
move, allowlist waiver or CI/AGENTS change was used to claim the clean-clone gates.

## Remaining proof

The historical F5 candidate hash
`50165863d45e678c28bcf794c6f9f5444b6aa45eef2caa446595dd638313578a` remains
historical evidence and was not rewritten or promoted. A fresh F5A package run,
independent attended review of its actual output, and human creative acceptance
are separate next proofs. Production integration and any variable-duration H3
decision remain out of scope.
