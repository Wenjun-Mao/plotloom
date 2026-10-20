# Unified project deletion — first source checkpoint

Scope: owner-approved one directory deletion entry and one explicit confirmation
flow, implemented in the retained `b30f/plotloom` checkout on local `main`, based
on `665d3b4d0774415e94a9cceef2c7fda72b89350c`.
[ADR 0201](../adr/0201-unified-project-deletion-preparation.md) records the contract.
This is a focused implementation checkpoint for independent review, not final
cross-layer qualification, installation, live deletion or product acceptance.

## Root causes and resulting behavior

- Two unconditional row controls delegated prerequisite discovery to failures.
  Abandonment neither cancelled paused runs nor supported empty automatic history.
  One passive server preview now selects the least-powerful supported operation.
- Pause was absent from ordinary close blockers. Final ordinary erasure now
  separately refuses every raw automatic-run state that still needs explicit stop.
  It also refuses all retained Exec attempt records: cancelled publication rows
  cannot hide UNKNOWN attempts, and terminal records still require the final
  host-owned quiescence/revocation gate rather than an earlier absence observation.
- Generic/global feedback hid exact reasons. Deletion owns project/phase feedback;
  prior and pending entries render their own progress/refusals, including a pending
  project whose manifest has already been withdrawn.
- A run revision alone can name a replacement run. Stop checks exact run ID,
  revision and consent scope in the actual lifecycle-write transaction. Both final
  erasers recheck scope under their exclusive project lease.
- An admitted draft can settle after preview. Old consent then refuses, keeps the
  project and newer local typing, and resumes existing queues. The browser fixture
  settles those edits, obtains fresh explicit consent, and successfully deletes.
- Post-stop GET would deadlock behind this client's suspended reads. The stop
  endpoint rereads preparation after its control transaction closes and returns
  that observation with its cancellation ACK. It never auto-deletes.
- Host erasure quiescence is distinct from permission to request existing exact
  cancellation. Recorded running-task fixtures cover both becoming quiescent and
  remaining blocked. Local authority cancellation never proves remote cancellation
  or process termination; unchanged host ownership predicates decide signalling.
- The running-image regression exposed text and image controllers both cancelling
  one executor attempt. Each now handles only its actual dispatch-owner domain.
  A mixed text/bridge/image/unknown-owner regression proves one cancellation per
  owned attempt and none for an unrelated owner. Host signalling code is unchanged.

The lifecycle hook is split into cohesive lifecycle/deletion owners (under 400
lines each), sharing the existing synchronous command token and draft/read barriers.
No refused or unacknowledged command triggers fallback or replay. UNKNOWN evidence,
reservations and revocation scope retain their original contracts. Acknowledged
pending-erasure retry preserves its original scope hash and exact receipt/consent.

## Small real journey and focused checks

The earliest real journey used two fresh isolated projects through production UI,
API and filesystem persistence: one idle home disappeared, fixture backend restart
returned target 404 and neighbor 200. No provider dispatch was needed. Test-owned
temporary roots/processes own cleanup; existing projects and installation data were
not inspected or mutated by this worker.

Executed with `uv run --locked --no-sync python scripts/verify.py focused`:

- `tests/test_project_deletion_preparation.py` plus exact existing reference-stop
  and queued-image-cancel cases: 16 Python cases passed; mixed owner partition,
  idle passive/no-host preview, paused ordinary refusal, run/scope/revision CAS,
  both final-scope erasers and both post-stop host outcomes are covered.
- `frontend/tests/project-lifecycle-command.test.ts`: 8 passed, including same-tick
  preparation exclusion and superseded-response retirement.
- `frontend/e2e/project-direct-delete.spec.ts` and
  `frontend/e2e/project-unified-delete.spec.ts`: 16 passed together. Real idle,
  active/archived/closed, prior-layout guarded deletion, durable retry, manual
  blocker/draft retention, stronger stale consent, late admitted draft/fresh consent,
  UNKNOWN acknowledgement and lost-stop/delete-ACK/no-replay paths are covered.
- Earlier directly affected checks passed: 10 ordinary eraser Python cases,
  7 original abandonment cases, 10 native host abandonment cases, and 5 lifecycle
  error browser cases. These are retained scoped evidence, not a new aggregate/full
  result on this checkpoint.
- Scope-bearing pending erasure retry: both original and scoped forms pass after
  manifest withdrawal and application reopen (2 Python). The affected direct-delete
  browser file passes again (11), including a scope-preserving explicitly confirmed
  pending retry whose refusal remains beside its exact pending entry.
- Final host/ordinary boundary rerun: `tests/test_project_deletion_preparation.py`
  and `tests/test_direct_project_deletion.py` pass together (22 Python), including
  the new cancelled-publication/retained-UNKNOWN ordinary-bypass regression.

Frontend and browser TypeScript checks pass. API/changed-module unused-import
checks and `git diff --check` pass. Deterministic checked assets are generated and
two production-build SHA-256 file trees compare equal. Desktop pixels were inspected
for idle consent and target-scoped partial-stop refusal at 1280×720; this does not
claim complete responsive or checked-static browser qualification.

Initial failures are retained as failures: invalid selector invocations were
refused before tests; an overly broad fixture locator matched its project title;
one fixture serialized snake_case then asserted camelCase; prior browser assertions
expected weaker revision errors/automatic scope widening. The running-task check
also exposed the actual duplicate-cancel defect described above. Each was corrected
at its owning layer and rerun with the stated focused selections.

## Boundary and handoff

Independent review and final risk-scoped qualification remain manager-owned. The
updated long lifecycle browser spec is typechecked but not executed in this source
checkpoint. There is no new full gate, hosted CI, push, provider/remote cancellation
experiment, installed-static journey, service restart, deployment or activation.
Running-worker tests use recorded production project state plus a provider-free
host-response seam; they do not establish a real OS worker termination outcome.
Actual owner projects and every live UNKNOWN reservation remain untouched.

The requested native worker settings were explicitly Sol/Medium; the effective
model/settings are unverified. No paid usage was
incurred by these provider-free fixtures; product/infrastructure/coordination time
breakdowns are unavailable. Per-run durations remain in verification output; no
aggregate timing or acceptance percentage is inferred.

## Inspectable source-checkpoint evidence

Commands below ran from the retained checkout. No filesystem logs were created
for these focused runs; their complete command/result captures remain in the
native worker conversation. Run session IDs are trace pointers, not file paths.

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_project_deletion_preparation.py \
  --pytest tests/test_direct_project_deletion.py
# Session 84980: 22 Python passed.

uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_project_deletion_preparation.py \
  --pytest tests/test_autopilot_image_safety.py::test_stop_after_reference_ingestion_preserves_terminal_owner_and_prevents_selection \
  --pytest tests/test_autopilot_exec_pool.py::test_known_queued_image_cancel_releases_proposal_and_project_lifecycle \
  --vitest tests/project-lifecycle-command.test.ts
# Session 53745: 16 Python + 8 unit passed before the final UNKNOWN addition.

uv run --locked --no-sync python scripts/verify.py focused \
  --playwright e2e/project-direct-delete.spec.ts \
  --playwright e2e/project-unified-delete.spec.ts
# Session 19651: 16 browser passed.

uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_project_abandonment.py::test_partial_erasure_retry_survives_lost_manifest_and_application_reopen \
  --playwright e2e/project-direct-delete.spec.ts
# Session 50652: 2 Python + 11 browser passed, including scope-bearing pending retry.
```

Retained screenshots are checkout-relative under `output/playwright/`:
`unified-delete-idle.png`, `unified-delete-scope_changed.png`,
`unified-delete-stop_lost_ack.png`, `unified-delete-delete_lost_ack.png`,
`prior-abandonment-entry.png`, `prior-abandonment-consent.png`,
`prior-abandonment-pending.png`, `abandonment-consent.png`, `pending-deletion.png`.
`frontend/test-results/.last-run.json` is the latest browser completion marker;
the next run may replace it. Existing `prior-catalog-bootstrap-failure2` artifacts
are not evidence from this assignment.

Two final `npm --prefix frontend run build:deterministic` runs had equal seven-file
trees captured with `rg --files src/plotloom/static | sort | xargs shasum -a 256`.
No manifest file was saved. Final source-checkpoint `workbench.js` SHA-256:
`b4955ef338bf9291f798efe2f20549098145b51d6dbd39302167befea0803c59`.

Independent source review at `c93df16b` found no actionable correctness, security
or UX findings. Root also inspected the retained idle/partial-stop/lost-ACK pixels.
The minimal follow-up removes a trailing blank line at the new deletion hook EOF
and corrects this evidence wording; executable behavior is unchanged. Root assigns
one final unfiltered established full run to this same source worker, with fresh
filesystem logs/fingerprints on the exact qualification candidate. Its result will
be recorded separately; earlier focused selections are not complete backend proof.

## Frozen full qualification and subsequent transport correction

Exactly one unfiltered `uv run --locked --no-sync python scripts/verify.py full`
ran on clean `dcd6f115688f8626b72189aedf56bbf3d274567c`. All 14 gates passed:
3,548 Python, 1,446 frontend unit and 344 browser cases; type contracts,
deterministic build/parity, allocation, wheel build and installed-wheel smoke.
Runner elapsed: 1,807.808 seconds; exit 0. Shell capture: 1,808 seconds.

Actual local artifacts are under
`.local/unified-project-deletion/dcd6f115688f8626b72189aedf56bbf3d274567c/`:
`full.log`, `command.txt`, `start.txt`, `outcome.txt`, `source-sha.txt`,
`source-tree.txt`, `git-status-before.txt`, `git-status-after.txt`,
`dependency-tool-fingerprints.sha256`, `static-before.sha256`,
`static-after.sha256`, `runtime-and-filter-preflight.txt`, `inventory-preflight.txt`.
`full.log` SHA-256 is
`780c637550e71c0be25486ec73f4847526b9b59150a735360423207286dd852d`.
Before/after tracked status is clean; static trees match. Native owner discovery
and retained assertion-replacement checks passed before dispatch. The established
runner removed its temporary wheel directory at exit: build/smoke evidence is in
the log; no surviving wheel or wheel hash is claimed.

During that frozen run, root and independent re-review found a P1 transport seam
missed by the earlier no-findings review: current-project abandonment passed a full
preview object to the API client, which spread observational members into a strict
`ProjectAbandonDeleteRequest` and would receive 422. Browser mutation mocks accepted
arbitrary bodies; backend tests selected only consent keys. The full pass therefore
remains exact-candidate software evidence, not evidence that this seam worked.

The only production correction explicitly whitelists the existing six command
members in `abandonAndDeleteProject`. Strict server admission, backend control,
persistence, host ownership and UNKNOWN/reservation semantics are unchanged. A new
API regression passes a full runtime preview (including mode/run/blockers/UNKNOWN
IDs/warnings) and checks exact serialized consent rather than relying on TS types.

Two current-layout cases reuse the existing disposable project/host fixture:
already cancelled -> abandon; paused -> genuine manual stop -> fresh preview ->
abandon. The final mutation is the actual strict API, with no POST fulfillment.
They check exact six-member request keys, 204, one stop where applicable, one host
revoke and one home erasure, unchanged original attempt evidence, target-home
absence and neighbor readback after restart. No OS termination outcome is attested.

The first background-enabled paused attempt returned genuine final 409
`project_busy: another local writer is active` after stop ACK; the already-cancelled
case passed. The exact historical holder was not proven; the controller's immediate
wake and retained cancelled-run reconciliation provide a plausible contender.
That contention is not fixed or hidden by the serialization correction. Its first
trace/video/screenshot/context are retained under
`.local/unified-project-deletion/serialization-correction-first-attempt/project-unified-delete-cur-f6de3--API-and-exact-home-erasure/`.

Root approved an explicitly controller-quiescent execution envelope for the strict
transport happy-path cases. The fixture holds the existing leader `flock` on its
own application root's `.autopilot-controller.lock` before runtime startup and
through shutdown. The real background owner cannot acquire leadership, while
manual control and exclusive project erasure retain every product admission guard.
The lifespan finally unlocks/closes the descriptor after the runtime shuts down;
process exit also closes it. Fixture evidence records the exact lock path/held
state. This neither overrides a lock guard nor models production contention as
resolved. Existing blocked/lost-ACK checks remain, and stopping never guarantees
immediate erasure.

Corrective focused command:

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --vitest tests/api.test.ts \
  --playwright e2e/project-unified-delete.spec.ts
```

The first execution passed 26 API cases and six browser cases, with the genuine
409 paused case retained as failed. Only the test-owned leader-lease envelope
changed for the next attempt. Final corrective results and source SHA are reported
with the scoped checkpoint; broad frontend/package follow-through and exact-finding
re-review remain root-owned. No second full run is started by this correction.

The first leader-lease attempt failed before mutation because Python records the
canonical `/private/var/...` path while Node's temporary root used `/var/...`.
The assertion now applies `realpath` before exact equality; no alias-tolerance or
admission change was added. Those two preflight failures remain retained under
`.local/unified-project-deletion/serialization-correction-path-preflight/`.
After that fixture-only correction all seven browser cases passed, including both
real current-layout paths. Standard per-case `strict-deletion-evidence` JSON
attachments retain actual command member sets/statuses, exact leader path/held
state, stop/cancel/revoke/erase counts, original attempt identities/states and
post-restart target/neighbor readback. Requested attachment capture reruns the same
seven-case file, rather than adding a new recorder or broad qualification.

Final corrective evidence: 26 API unit cases passed; the final seven-case browser
run passed in 37.237 seconds, including both genuine controller-quiescent strict
routes and all retained blocked/lost-ACK cases. Its complete log is
`.local/unified-project-deletion/serialization-correction-final-focused-browser.log`.
Successful proof JSON and consent pixels remain at
`output/playwright/unified-delete-current-cancelled-evidence.json`,
`output/playwright/unified-delete-current-paused-evidence.json`,
`output/playwright/unified-delete-current-cancelled.png` and
`output/playwright/unified-delete-current-paused.png`.
These files are also attached by path to their Playwright cases: body-only
attachments were not retained by the list reporter, so final capture writes the
small ignored JSON files explicitly. Both final responses are 204; the paused
case has one stop/host cancellation, the stopped case has zero; each has exactly
one revoke/erase, original attempt evidence unchanged and 404/200 post-restart
target/neighbor responses. Checked frontend assets were regenerated after the
projection correction. Exact-finding re-review and frontend/package follow-through
are pending; the earlier full result is not relabelled as a full pass on this fix.

## Composite local qualification closeout

Exact-P1 closure review passed on `bdbaf800f7a7f16695091d5f6797cd6a6bff4743`;
root inspected the actual consent JSON, paused pixels and strict-route logs. The
subsequently authorized frontend/package follow-through passed on that clean SHA:

- Established `verify.py quick`: 1,447 frontend cases across 165 files, both
  TypeScript checks, lock check and API import lint; exit 0, 12.343 seconds.
- Two `npm --prefix frontend run build:deterministic` invocations: identical
  seven-file SHA-256 trees, unchanged checked assets; every exit 0.
- `verify.py focused --playwright e2e/project-direct-delete.spec.ts --playwright
  e2e/project-lifecycle-errors.spec.ts`: all 16 affected browser cases passed,
  exit 0, 57.172 seconds. The latest seven unified cases and their exact strict
  request/status proof are reused rather than rerun again.
- `uv build --wheel --out-dir <evidence>/wheel` followed by the established
  `uv run --locked --no-sync python scripts/smoke_installed_wheel.py <evidence>/wheel`:
  both exited 0. The isolated installed-package probe passed.

Here `<evidence>` is the actual checkout-relative directory
`.local/unified-project-deletion/bdbaf800f7a7f16695091d5f6797cd6a6bff4743/final-frontend-package/`.
It retains exact command files; complete `quick.log`, `build-1.log`, `build-2.log`,
`browser.log`, `wheel-build.log`, `installed-wheel-smoke.log`; per-stage outcome
files; source/tree identity; before/after clean Git status; dependency/tool hashes;
and static before/after/two-build manifests. A separate Git boundary check proves
production backend, strict schemas, dependencies and build tools are unchanged
from full-qualified `dcd6f115`; only frontend consent projection and its generated
bundle change product behavior. No final scoped gate failed.

Unlike the earlier full runner's temporary wheel, this authorized scoped build
retains `wheel/plotloom-0.1.0-py3-none-any.whl` under that evidence directory.
Its measured SHA-256 is
`d4e2d530d164481f8ced21e05bb6f38a05bd0035a42bfb50e2d272918418eea4`;
`wheel.sha256` records the exact path and digest.

The qualified result is explicitly composite: frozen full on `dcd6f115` plus
exact-finding closure and scoped frontend/package qualification on `bdbaf800`.
It is not a new full result on the correction. This closeout changes documentation
only; no second full/backend sweep, publication, deployment, activation, real
provider operation, live-project deletion or human product/creative acceptance is
claimed. The controller-quiescent strict-route fixture and real background-enabled
409 remain distinct evidence; a supported stop does not guarantee immediate
erasure. Earlier failed runs remain failed, with their retained artifacts.

## Installed-wheel runtime acceptance

The separately authorized CLI-first desktop journey ran the retained `d4e2d530…`
wheel on source checkpoint `01b8dcfdb0c9477baeeebd4b9a1ea1ea3e8ec5b4`, in an
isolated venv/cwd/application/outputs envelope. The shipped console, host and
background controller were unmodified: no leader-lease suppression, HTTP mutation
fulfillment or host override. Sanitized settings had no credentials/native binding,
loopback provider endpoints and H3 disabled. Initial state was library-seeded,
explicitly synthetic no-dispatch provenance: one idle target, one paused-before-
first-dispatch target and one neighbor. No resume or provider dispatch was attempted.

The normal controller held its real lease and persisted a claim, advancing the
paused run from revision 2 to 3 with zero checkpoints/Exec attempts. Both actual UI
confirmations succeeded on their first deletion attempt: idle ordinary erase 204;
paused exact-run stop 200 (`cancelled`, unchanged scope, fresh `ordinary` preview),
then erase 204. There were exactly three mutation requests. Inspected 1440×1000
consent/success pixels show the distinct truthful flows. Restart readback was
target 404 / target 404 / neighbor 200, with only the neighbor home retained.
Both owned consoles shut down gracefully, the browser closed, both process IDs
disappeared, port 18887 closed and the controller lease was released.

Evidence is retained in checkout-relative
`.local/unified-project-deletion/01b8dcfdb0c9477baeeebd4b9a1ea1ea3e8ec5b4-installed-runtime-KetdCn/`:
`commands.txt`, `isolated-command.sh`, `seed.json`, `identity.json`,
`controller-before.json`, `runtime-first.log`, `runtime-restart.log`,
`restart-readback.json`, `shutdown-{first,final}.json`, `outcome.json`,
`artifact-manifest.sha256`, `browser/*{http,body,ack}.txt`, desktop PNGs and the
existing CLI `.playwright-cli/traces/` action/network/resources. The retained
evidence checker asserts exact consent members/scope, statuses/counts, readback,
package identity and settlement. Wheel member, installed file and independently
served `/v2/workbench.js` probe share SHA-256
`28c6eee0ec0c4a0c4947ee9515e75c169efc0fa00726fe9699618462c354910b`.
Browser access logs record the asset GET 200, but the trace started after loading;
no captured browser-response digest is claimed. Navigation-aborted GETs and two
before-journey setup/probe mistakes remain recorded, separate from mutation success.

This adds normal-background installed-runtime evidence for local authority stop
with no dispatched work. It does not prove UI launch, provider/worker termination,
UNKNOWN host erasure or contention resolution; earlier controller-quiescent strict
host-route and real 409 evidence retain their stated limits. No new source behavior,
test suite/full rerun, activation, publication or live-project operation occurred.
