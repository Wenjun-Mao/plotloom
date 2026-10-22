# Explicit unassessable identity review — scoped software receipt

Retained checkout `/private/tmp/plotloom-one-story-rebuild.gfnqlc`, branch
`codex/one-current-story-rebuild`, clean base
`ff7bcb6a38a389fbf4bd2132c5fd509c3df20d29`. This is the scoped software
checkpoint for owner-accepted [ADR0146](../adr/0146-explicit-unassessable-identity-review.md).
Manager source/pixel review and isolated activation are closed below; native
acceptance remains a separate gate. Requested worker settings were Sol High; effective
settings are unverified. Relay registration succeeded before source work.

## Cause and contract

The persistence predicate previously classified every non-PASS as noncurrent,
and latest-review lookup searched backward for any current row. That conflated
source dependencies with authorization and could revive an older PASS after a
newer exact-binding refusal. The owning domain/persistence contract now keeps
source `current`, latest applicable exact-binding decision and
`productionEligible` separate. Every involved character must pass or explicitly
authorize unassessable identity with a framing/accepted-uncertainty rationale.
FAIL/HOLD and missing fields fail closed. PASS/FAIL comparison shapes and all
old rows remain intact; no migration, adapter or automatic FAIL conversion.

New previews/videos freeze the latest eligible immutable review ID. A later
refusal or replacement review disables already-frozen older media; their
manifests/snapshots stay unchanged and a newer approval never rebinds them.
Video source `inputStatus` remains current after a review-only refusal while
`productionEligible`/`current` are false. Source/reference/Cast/image/binding
changes independently stale the review and media. Tampered video request
snapshots fail integrity even when a valid review exists.

The form begins with blank judgments and a separately blank production choice.
It names authorized uncertainty without claiming identity passed. The browser
also exposed an owning draft-reset defect: temporary media read withdrawal and
new GET object identity cleared authored comparison fields. The final reset
uses a successfully read exact project/shot/binding/frozen-identity basis;
unchanged refresh preserves authored observations while unavailable reads
continue to block operations. A changed target resets comparisons.

## Executed checks

- `uv run pytest tests/test_project_storage_image_identity_contracts.py
  tests/test_same_person_review_contract.py tests/test_identity_review_refusal.py
  tests/test_frozen_video_integrity.py tests/test_project_storage_video.py
  tests/test_retained_runtime_coverage_inventory.py -q`: **96 PASS**,24.53s,
  one existing Starlette deprecation warning. Real offline API transitions cover
  old PASS preview/video → newer FAIL/HOLD → explicit unassessable authorization
  → newer HOLD, preserving each frozen ID and receipt. Provider preflight/upload/
  submit counts remain zero. Mixed-character eligibility, missing/blank choice/
  rationale, Cast/reference/candidate hash/binding/storyboard staleness, and
  request-hash tampering are covered.
- `npm run typecheck`: PASS. `npm test`: **951 PASS**,116 files,4.17s.
  New form/policy cases cover untouched judgments, uncertainty without a
  production choice or reason, HOLD/authorize controls, truthful uncertainty
  wording and latest refusal without older-PASS fallback.
- `npm run test:e2e -- e2e/image-jobs.spec.ts --workers=1`: E2E TypeScript PASS;
  **1 PASS**,22.0s. The full existing image preparation/send/fixture-ingestion/
  refinement/staleness journey now includes missing/failed identity refusal,
  untouched controls, explicit HOLD, authorized unassessable, a newer FAIL,
  frozen preview-ID preservation and restored explicit PASS. Real disposable
  project-folder runtime + Vite + retained-asset/offline delivery fixtures;
  no native image/video generation and no real provider dispatch.
- Temporary production build:
  `npm run build -- --outDir /private/tmp/plotloom-unassessable-review-build`: PASS,
  existing large-chunk warning. Candidate `workbench.js` SHA256
  `b407af7c2723ab39471506dc6eaa0a048bddb8c510ab431e58958744cdefaab8`.
  Served checked static was untouched; its SHA256 remains
  `d47c0844c23d3c37515d54205e1c2c19b999298c899445964d9dad4a5c53b01a`.
- `git diff --check`: PASS. New domain modules are cohesive and below400 lines;
  review types were extracted from the oversized central frontend types file.

Pixels are preserved under
`output/playwright/2026-10-09-explicit-unassessable-identity-review/`:
`unassessable-choice-{1700x900,1280x768,1280x460}.png` and
`unassessable-authorized-{1700x900,1280x768,1280x460}.png`.
Writer directly inspected all six viewport captures: explicit choice/rationale,
truthful latest authorization, retained FAIL/HOLD history and record control
fit the supported desktop layouts; short desktop scroll exposes the necessary
actions. Refusal and existing comparison captures are also retained. These
fixture pixels make no claim about Opening2 observability or artistic quality.

Initial browser attempts exposed the draft reset; an object-basis-only correction
still reset on temporary read withdrawal. The final fix treats unknown reads
as unknown and resets only after ready changed authority. The next run passed
the new sequence but exposed an old test-helper ACK race: `当前复核` already
matched a previous decision. The helper now awaits the actual201 response and
its exact immutable ID before comparing images; the complete final journey
passes. No product tolerance or timeout increase was added.

The inventory check initially failed because the existing image-identity test's
setup/trigger gained frame-grid H3 and transition coverage. Exactly its authored
`source_sha256` changed to
`cb6360be5b10479dd853fb144814c7eb52cf4d9733243ab5f0488e177f6ada65`;
existing assertion strings, baseline, dispositions and checker are unchanged.
The refreshed inventory passes in the final96-test gate. Added helper assertions
extend rather than replace the original identity/reference regression.

## Manager source and pixel review — October9,15:06UTC

After the writer explicitly released source ownership, the manager independently
reviewed the domain/API, latest-applicable review lookup, frozen preview/video
admission and UI draft/authorization paths. No blocking source finding remains
in this scoped slice. All six saved desktop captures were directly inspected:
choice fields and uncertainty rationale fit their scrolled views; the three
authorized-state captures separately show the truthful status/history and full
record control, including1280×460. This is fixture visual evidence, not native
hand-only-shot or creative acceptance.

Separate manager reruns passed the same96 Python checks in22.02s,19 targeted
frontend checks and the complete image browser journey in21.9s, including its
E2E typecheck. The manager browser artifacts are outside the source tree at
`/private/tmp/plotloom-identity-manager-review-browser`. The native read-only
diagnostics left all eight API-domain hashes and all42 assets unchanged; eight
image jobs remain delivered, seven video jobs ingested, and the specialist/run
owners are idle. Normal8841 remains unchanged.

At the idle boundary the manager stopped only isolated8865/8866, then rebuilt
checked static sequentially. Its JS hash equals the independently reviewed
temporary production build (`b407af7c…defaab8`); the separate ordinary frontend
typecheck also passes. This is a branch checkpoint, not normal-service activation
or a new combined full gate. No native write or generation followed the build.

An unrelated branch-task remount defect was demonstrated with browser-only
interception and zero backend writes: cancellation ownership disappears on
Source→Brief→Source and the completed cancellation leaves an obsolete visible
task. It is a separate follow-up, not a failure of the identity candidate or a
completed repair. Broader gates and native execution remain open below.

## Manager isolated activation — October9

Committed software checkpoint `dbd91b026d356575eb593a5300eff597584146e5`
is loaded on isolated8865/8866. Python source and served JS
`b407af7c2723ab39471506dc6eaa0a048bddb8c510ab431e58958744cdefaab8`
match the reviewed build. Native OpenAPI exposes `pass`/`fail`/`unassessable`.
Opening2's immutable old FAIL remains unchanged; activation does not authorize it.
No provider dispatch followed this activation. All42 asset hashes, eight delivered
image jobs and seven ingested video jobs remained exact; owners were idle.
Normal8841 remained unchanged. This is isolated served-build qualification,
not native authorization, playback, normal-service release or a combined full gate.

The subsequent owned-renderer adoption makes old Art r2 and its dependent
production stale under their existing hash contracts. That distinct source
requalification is tracked in the [fork receipt](2026-10-09-owned-renderer-fork.md),
not silently repaired by rebinding this identity decision or retained media.

## Original worker limits and handoff

This closes the bounded software implementation and scoped independent review.
The baseline full1,418 Python/945 frontend/264 browser checkpoint is historical;
this slice does not claim a new full Python or unfiltered browser run, wheel/
installed smoke, native activation or the whole Create → Revise → Recover goal.
The manager owns final candidate review, build/static activation and service
identity verification, then a fresh native Opening2 review and exactly one
frozen H3 request/playback under the accepted policy. Opening2's old FAIL and
all native/owner/protected media, projects, settings and credentials were
untouched. No service restart, specialist/provider dispatch, renderer fork,
commit, push or merge was performed. Source writer handoff is released after
this stable receipt; no further source edits are planned by this worker.
