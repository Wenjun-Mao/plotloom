# Pre-video autopilot · single evidence receipt

Status: **P5 full failed/interrupted; terminal admission and reproduced cleanup
race repairs in focused verification. Native/preservation/walkthrough/activation remain pending**. No owner creative
acceptance, valued installation upgrade or live activation is claimed. Scope and stopping boundary are in the
[approved plan](../roadmap/2026-10-12-pre-video-autopilot.md#p0-implementation-checkpoint)
and [ADR 0162](../adr/0162-pre-video-autopilot-authority.md).

## Revision and authority

- Production source/test baseline: `731cfdbfb0d9139254e30c34c2a8e7669a98ddba`.
- Sole writer checkout: `/Users/wjmao/projects/HU/plotloom-worktrees/pre-video-autopilot`,
  branch `codex/pre-video-autopilot`; retained main/source and owner data untouched.
- Source owner native ID: `01a12e81-53b6-7321-a0ef-adf4cad02b18`; confirmed Relay
  registration to manager `01a04525-e907-7630-9640-78790d69e8ae`, route
  `f91e617c-2925-4962-826d-5dcc14450566`.
- The manager explicitly requested return of this high-risk P0 checkpoint before
  schema/authority writes. Source-byte preservation and one counted adaptation
  were confirmed within scope through native follow-up. This return is a review
  boundary, not an unsupported blocker or completion of the implementation.
- Only prerequisites initialized: locked `uv sync --all-groups --frozen` and pinned
  `third_party/shuohao-skills` at `4f9b2128c82adf623f594ba714c97d0afcfc16a2`.
  Frontend prerequisites subsequently installed from the checked lockfile for
  quick feedback; no service operations or hosted dispatch.

## Historical P0 executed evidence

All commands below ran from the isolation checkout. The focused native runner
completed **76 passed**, one existing Starlette/httpx deprecation warning,
`VERIFY_SUMMARY tier=focused elapsed_seconds=15.028 exit_code=0`.

```sh
uv run --locked --no-sync python scripts/verify.py focused \
  --pytest tests/test_project_storage_current_schema.py \
  --pytest tests/test_project_storage_source_outline.py \
  --pytest tests/test_project_storage_image_identity_contracts.py \
  --pytest tests/test_project_storage_image_delivery_contracts.py \
  --pytest tests/test_same_person_review_contract.py
uv run --locked --no-sync python scripts/autopilot/p0_probe.py
```

The [disposable probe](../../scripts/autopilot/p0_probe.py) refuses production
source/tests differing from the baseline, uses temporary offline fixtures and
prints its observations; its secondary output is ignored
`.local/autopilot-p0/receipt.json`. It makes **zero native/provider submissions**.
Its manual bridge fixture is baseline owner evidence, not an automatic run.

| Observation | Actual result and implication |
|---|---|
| Exact preceding layout | 75 tables; SHA-256 of canonical `schema_objects` = `ea9facef83198e8b5abdd8693923f51add1376c0b416041dbfa245b92011b825`. Complete tuple frozen in [prior-layout JSON](2026-10-12-pre-video-autopilot-prior-layout.json), file SHA-256 `6f9e4a4e544796dfd429b26d7c3fba8bc929e9b9739335ff2c297b706b18a86e`. It is source-derived; actual rollout targets remain manager-owned inventory. |
| Source projection | Current `SourceMaterial` trims title/text whitespace. Exact Brief origin must preserve raw saved bytes with normal validation, without rights invention or historical rewrite. |
| Geometry | Exact cross multiplication accepts 720×1280 and 1080×1920 as 9:16; rejects 1024×1536. Accepts 1280×720 as 16:9; rejects 1536×1024. Existing focused adaptation test passed exact role/geometry rejection and source-selection preservation. No real tool output geometry proved. |
| Identity capacity | Current request schema maximum is eight comparisons; nine-character request is rejected. Source image preparation permits nine total attachments. Pre-dispatch capacity must satisfy both. |
| All-route enumeration | Offline current-owner fixture: two complete routes, 27 unique shots, 36 route shot occurrences; every shot reachable, IDs unique, route-only `choose` excluded from scenes/frames. Never generate per route occurrence. |
| Snapshot defect | Disposable accepted-outline snapshot omitted all eight retained package/delivery files: request, assignment, completion template, two frozen inputs, outline, report and completion. Closed direct-folder restore refused `recovery tree contains an unexpected directory`. |

The snapshot defect originates in `recovery_validation.payload_paths`, which
enumerates known media `runs/` but not `outputs/creative-handoff/jobs`; the strict
tree validator then rejects that unowned directory. The fix belongs in typed
project evidence inventory/recovery, not in permissive tree validation or an
autopilot-only copy workaround. Original evidence and refusal remain in the probe.

Initial scratch-probe executions failed on test-package import resolution and
then on treating string `footage_mode` as an enum. The diagnostic corrected its
entrypoint path and comparison; production contracts/assertions were not weakened.
The final tracked probe passed with the frozen layout and added geometry/capacity
assertions. No implementation failure is reported fixed by these corrections.

## Independent reviews and resolved decisions

Attended read-only native subagents returned complete results before this source
owner's Stop final: requested GPT-6.1 Sol / High for authority/identity, and
GPT-6.1 Sol / Medium for preservation/restart. Effective settings were not verified
by the host. Neither subagent edited files, ran tests or accessed live data.

Their concrete findings are incorporated into P0/ADR: exclusive production-unit
authority; machine intent/presentation distinct from human flags; image currentness
separate from dispatch; original reference IDs endorsed rather than replaced;
material hash separated from resulting human IDs; coherent nested transaction
reads/writes; guards before provider preflight and application reservation;
whole-pack withdrawal; independent raw-layout inventory; retained creative
snapshot evidence; and permanent portable native non-resumption.

The checkpoint specifies one counted adaptation from a typed machine-provisional
source, excludes a mismatched original from completion, and preserves normal job
settlement. Second incompatible output blocks. It does not promise a semantic
quality pass or claim a new visual adjudication subsystem.

## Historical P0 continuation boundary

P0 delivery proposed P1–P4 source implementation and focused evidence, with native
ownership/browser allocation preserved. The manager retained independent final
review, one stable full gate, packaging, real isolated native text/ImageGen proof,
valued upgrade/cutback, main integration/push and idle activation. P0 itself had
no browser/pixel, real generation, valued transition or human-handoff evidence.
Later executed checkpoints and remaining P5 gates are recorded below.

## Attended P0 approval · baseline evidence

The manager approved continuation at checkpoint `72b85537a30f17b7430b89495a480e1cb0ea7e33`. Independent rerun: the same five focused pytest files passed **76 tests**, `VERIFY_SUMMARY focused elapsed_seconds=14.064 exit_code=0`; P0 probe reproduced the source/geometry/capacity/route and recovery facts; `git show --check` clean; production source/tests/frontend/services/dependencies unchanged from `731cfdbf`. A manager-attended GPT-6.1 Sol / High read-only review reported no blocking contract finding. These are baseline/contract evidence, not implementation acceptance.

Required follow-ups: use `ProjectVideoRepository.assert_submit_allowed` (called by `ProjectVideoService.submit`), move cohesive details from the near-limit roadmap to the linked implementation contract, and ship the frozen prior layout inside the actual installed package owner. The manager's initial live inventory is independently held evidence and is not a source-owner upgrade qualification or final quiescence snapshot.


## P1 authority / schema / preserving recovery checkpoint

Implemented only in the named isolated source worktree after P0 approval. New
native project tables own one run, CAS/monotonic checkpoints, immutable machine
decisions and provisional frames. Existing owner commands share one repository
transaction; machine image units have an exclusive human/machine FK union.
Human intent/presentation/Brief and frame-review owners reject machine commands;
video prepare/preview/claim/submit guard before any provider or reservation.
Exact saved-Brief source provenance retains raw title/synopsis bytes. Native
checkpoint/frame facts resolve real project-owned request/pin/delivery/assets;
receipt-only ingestion retains candidate evidence without creative-head adoption.

The packaged frozen prior layout supports an explicit idle transactional upgrade;
old-column fingerprints, integrity/FKs and confined retained-file hashes are
verified before commit. Ordinary reads remain exact. Snapshots retain all eight
creative fixture files; missing completed trees fail closed. A separately
verified prior-snapshot omission is recorded explicitly on the upgraded private
destination. Original snapshot bytes remain unchanged. Captured portable run
identities cannot resume or reclaim dispatch after recovery acknowledgement.

Root-cause fixes from attended review: prevent dispatch-state regression with CAS
and a monotonic transition graph; bind evidence to native owners rather than JSON
shape; keep human-only owners outside machine scope; distinguish unexported/prior
omitted trees from lost current final evidence; validate retained filesystem
bytes before schema mutation and after its final hook. Exact historical source
binding and explicit v3 character mappings are additionally validated. The same
attended GPT-6.1 Sol / High reviewer found no remaining defects in the final
bounded corrections; effective host model settings remain unverified. This is
not independent final product/release review.

Executed final P1 focused selection (no full gate):
`tests/test_autopilot_authority.py`, `tests/test_autopilot_schema_upgrade.py`,
`tests/test_autopilot_recovery.py`, `tests/test_project_storage_current_schema.py`,
`tests/test_project_storage_source_outline.py`,
`tests/test_project_storage_image_workflow.py`,
`tests/test_project_storage_video_submission.py`,
`tests/test_project_storage_recovery.py`, `tests/test_project_storage_cast.py`,
`tests/test_project_storage_art.py`, `tests/test_project_storage_script.py`,
`tests/test_project_storage_storyboard_review.py`.
**133 passed**, one existing Starlette/httpx deprecation warning; focused runner
`elapsed_seconds=34.642 exit_code=0`. New tests are in native module ownership.
Unused-import check on new authority/recovery modules/tests and `git diff --check`
passed. Disposable Alembic head upgrade succeeded. `uv build --wheel` succeeded;
the wheel includes `plotloom/project_storage/schema_layouts/pre_autopilot.json`.

P2–P4 remain required: durable full-chain controller/native-role integration,
complete subject/all-route image pack and one counted adaptation, consolidated
truthful human review/UI and exact final handoff. No frontend build/browser/pixel,
full qualification, real native dispatch, live schema upgrade, service activation,
CI, video operation, main merge or push is represented by this checkpoint.


### Manager-attended P1 preserving-package correction

The independent exact-`fd549395` manager review found that final delivery members
were mandatory but frozen package members were only an allowlist. The shared
retained-evidence inventory now requires `package/request.json`,
`COPY_ASSIGNMENT.txt`, completion template and every declared input for completed
jobs. Missing package directories and each member fail snapshot and schema-upgrade
admission. Unexported requests and the explicitly recorded verified prior-snapshot
whole-job omission remain distinct; no package bytes are reconstructed or rewritten.

Focused upgrade/recovery selection: **31 passed**, runner
`elapsed_seconds=8.864 exit_code=0`. Added completed branches-package portability
regression: **1 passed**, runner `elapsed_seconds=1.701 exit_code=0`; original
location-sensitive assignment bytes and all package hashes survive restore.
This correction also removes four extra blank EOFs and makes the receipt's current
status distinguish historical P0 evidence from committed P1 and ongoing P2–P4.
Final staged and committed additions are checked with `git diff --cached --check`
and `git show --check`; ordinary diff checks alone do not cover untracked additions.

The manager's same GPT-6.1 Sol / High reviewer closed this correction at exact
`b3b01fb6a5e948f01b4cf6463750292c2e2c47fc`, with no remaining bounded finding.
The manager inspected committed coverage and clean `git show --check`; this was
committed-code review, not an independent runtime rerun or full release gate.

### P2 text orchestration checkpoint

One application-owned controller now prepares, sends, reconciles and atomically
adopts six native text stages plus native intent/presentation and installs the
canonical bundle. Existing owners remain authoritative. Fake deliveries traverse
the real package/schema/binder/gate owners: eight unique sends, eleven checkpoints,
zero human approvals/intents/bindings/SamePerson reviews and zero video rows.
The general two-choice/three-ending/join case installs six complete routes,
54 cuts and all 66 intent targets. Images and final human review remain required.

Root causes addressed: typed presentation spans previously serialized identically
but reopened as a different model type; the shared binder now constructs domain
spans. A valid general topology exceeded the shared 64-target intent bound;
manager-approved shared 128 targets retain exact binding and the 60,000-byte cap.
Interrupted static export previously stranded a prepared identity; atomic confined
publication now reuses only the original request. Final dispatch uses current
TEXT/INSTALL authority and frozen pins under reservation, with both task IDs
checked under the registry lock. Receipt scope cannot grant a new send.

Storage failure handling isolates OSError/SQLAlchemy failures to the project,
reopens a clean session to persist an actionable blocker and quarantines the
project until recording succeeds. Unrelated projects continue. Unsafe controller
lease refusal and discovery failure remain supervised with a readable global
blocker, without granting a claim. Existing uncertain jobs/reservations remain.

Executed focused evidence (fake native transport, no real dispatch):
- Native intent/presentation, production bridge/intent, creative exchange,
  specialist settings, autopilot authority/text: **110 passed**, runner 84.313s.
- Text controller plus authority and final-send/background storage isolation:
  **44 passed**, runner 31.364s after the final send correction.
- UTF-8 byte cap and exact 128/129 target coverage: **2 passed**, runner 3.559s.
- Start API idempotency and forged-authority refusal: **1 passed**, runner 1.745s.
- Unsafe controller admission supervision: **1 passed**, runner 1.643s.
- Static orphan subset/foreign-byte refusal: **2 passed**, runner 1.457s.

The first quick run passed lock/API-import checks but failed before frontend tests
because the isolated checkout lacked Vitest. Install the checked frontend lockfile
and reran the failed/downstream quick feedback: **quick passed**, runner 10.937s,
151 frontend files / 1,284 unit tests and both type checks. No assertions were weakened.
Locked npm installation reported its existing audit/install-script warnings; no
dependency versions, lockfiles or build policy were changed.
Existing Starlette/httpx deprecation warning remains. Ownership includes the new
text/safety cases. P3/P4, deterministic frontend assets/browser/pixels and manager
P5 full/native/preservation/activation qualification remain outstanding.

### Manager P2 late-receipt corrections

Manager-attended review at `aa677b6768c68f6fb90fcee19b9f948dd2d58c26`
found two concrete gaps. Shared bridge response retention ignored the real
`outcome_unknown` send state; it now retains exact response evidence without
advancing proposal heads, allowing normal native settlement during pause/hold.
Every text receipt/adoption path now uses one frozen-code-revision gate, including
inactive reconciliation and resumed/restarted adoption of already retained rows.
Foreign receipts remain on disk without adoption/checkpoint-completion authority.

Focused late-receipt/text selection: **22 passed**, runner 26.616s. Four bridge
intent/presentation unknown-ack pause/blocked cases settle without proposal/human
edits, then resume the same job without a send. Running, paused, blocked and
retained-receipt restart cases all refuse foreign code revisions. Initial repair
checks exposed two owner-read constraints (receipt-only request scope, and branch
request getter restricted to prepared candidates); the final gate reads exact
retained requests under EVIDENCE before separately revalidating adoption authority.
Evidence logs remain under ignored `.local/`; no owner guard was weakened.

Manager independently reran schema-upgrade/recovery at exact `aa677b67`:
**32 passed**, focused runner 8.408s, clean before/after and committed diff. Empty
confined publication locks and original package bytes survive preservation. This
is cross-phase recovery evidence; manager P2 acceptance remains open pending its
bounded correction re-review. No runtime/native/full acceptance is inferred.

Manager's same GPT-6.1 Sol / High reviewer closed both P2 late-receipt findings
at exact `94c38931c1b2b4ff50e280695e3b8162f64613a0`; committed diff clean.
This is read-only code/coverage review, not an independent 22-test runtime rerun.

### P3 complete initial material checkpoint

The application-owned image reconciler enumerates every adopted Cast character,
every Art environment/prop and every unique reachable filmed shot over complete
routes, with no route-only or duplicate-route jobs. The small complete fake run
uses **29 image jobs: 27 first frames plus two references**, over two routes,
then publishes a typed exact bundle in `awaiting_review`. It creates zero human
approval/intent/binding/SamePerson/video rows. Unfilmed Cast and Art prop gallery
coverage is separately verified. Image/job minima are checked before image jobs;
each optional single geometry adaptation consumes its own frozen capacity.

Image preparation freezes the launch revision/skill and original requested
geometry. Existing native transport/package/delivery owners remain authoritative.
Technically valid mismatched originals settle normally and retain their assets;
one tagged `machine_provisional` source can receive an exact frozen-dimension
adaptation. A second incompatible output blocks with its files/reservation retained.
Extra outputs settle their valid technical receipt but block automatic selection;
no competing choice, crop, aesthetic judgment or provider fallback is inferred.

Typed inventory/bundle validation binds historical accepted subject and canonical
owners, exact native manifest/pin/output filename/hash/role, candidate/asset IDs,
reference decision IDs and provisional frame selection/generation decisions.
Current selection and bundle admission separately recheck native applicability.
Image/reference cancellation participates in the material closure as authority
withdrawal; other receipt status changes remain transport evidence. Paused valid
receipt import reconciles only a previously current closure; it cannot conceal
manual drift. Cancel/Takeover preserves delivered proposal evidence, and native
send refuses any existing delivery/execution staging at final reservation admission.

Static image package publication is descriptor-confined, staged, fsynced and
renamed once; interrupted prefixes matching only the named frozen recipe may be
reclaimed. The oversized exchange is split into package and delivery owners,
both retained in the native execution pin. The concurrent test first exposed an
ancestor mkdir race, then a separate lock creation refusal: a finite local probe
observed ENOENT on concurrent O_CREAT even while the live descriptor/lock existed.
Atomic exclusive creation plus reopening the existing no-follow lock fixes that
boundary for image and creative publication. Foreign bytes remain untouched.
The background supervisor also records unexpected owner failures without replay
and continues unaffected projects; logs contain exception type only.

Executed source/fake-only evidence (one existing Starlette warning):
- Initial complete image pack: **1 passed**, focused runner 39.024s.
- Ten controller cases including complete pack, limits, late delivery, restart,
  extra output and adaptation passed in the broader 88.534s run; its separate
  concurrent publication case failed and was diagnosed as described above.
- Cancellation/partial-publication/manifest-edge fixes plus dispatcher:
  **19 passed**, focused runner 61.950s.
- Final complete pack/adaptations plus manual delivery contract:
  **13 passed**, focused runner 64.264s.
- All-subject gallery including unfilmed Cast/Art prop: **1 passed**, runner 9.723s.
- Final receipt/dispatch-boundary cases plus atomic publication:
  **9 passed**, runner 25.863s.
- Atomic publication plus creative orphan subset/foreign checks:
  **6 passed**, runner 2.322s after the concurrency root fix.
- Background storage/unexpected-failure isolation plus pin boundaries:
  **25 passed**, runner 9.885s.
- Shared image delivery/identity/pin/publication run: 36 passed with the one
  concurrent failure; only failed/downstream cases were rerun after diagnosis.

Initial fake-output directories and the added prop's render sentence were
corrected to satisfy the existing protocol/style gates; validators were not
weakened. Development missing-import failures were diagnosed and corrected at
the extracted/currentness modules; focused checks and Ruff F checks then passed.
The attended P3 source review returned four concrete findings, all covered by
the 19-case correction run; its bounded re-review closed at exact `8b069d8d97b299b32d9f9e04f5fa22d66887c5da`:
no concrete remaining defects in the four corrections, read-only, no test rerun.
The manager's separate same-revision read-only image/material review found no
blocking/high-risk issue and independently ran package publication, image pin
and delivery contracts: **36 passed**, focused runner 15.012s. No native/product
acceptance follows from either review. P4 evidence below is separate.


## P4 source human handoff and compact UI candidate

A fifth native append-only owner, `v2_autopilot_handoffs`, binds the exact current
review bundle, actual human attribution/observations/reference endorsements,
and native approval, intent, reviewed-binding and SamePerson IDs. The unshipped
migration and exact named prior-layout transition include it; intermediate
working layouts are not supported. Run pointers cannot substitute a JSON claim
for native human evidence. Video eligibility validates the retained receipt and
whole current closure before existing video owners may proceed; confirmation
creates no video job/request or provider operation.

Current review reads complete canonical routes, current Cast/Art references and
current frames, including a manually imported replacement after takeover.
Cast subject IDs resolve through their explicit consumer mappings. Existing
human approval over the same canonical revision is reused with its original
attribution and a distinct new receipt. Tagged human-current-material comparison
context supports non-v3 imports without claiming generator conditioning or
changing ordinary manual-only admission. Shared assets keep one current authored
intent per role. Original machine references, units, intent/presentation flags
and history remain machine-origin evidence.

The Brief launch checks current fresh-data admission on entry, exact saved
content, configured specialists, common Cast/Art style and finite ceilings.
Both workbench views share app-owned progress, safe controls and the consolidated
story/routes/Script/reports/reference/frame review. Frame intent/compatibility,
identity/state observations, reviewer and notes start blank. Unassessable identity
needs a separate authorize decision and reason; character-free frames contribute
no fake pass. Exact adopted revision/hash gets an AI label; whole human review is
separate. Manual source edits remove the trusted exact-Brief assertion from the
new authored input, preserving the original revision.

Executed source/fixture evidence:

- Initial handoff/authority/named upgrade selections: **39 passed**, focused
  runner 303.966s; initial exact handoff alone 1 passed, 42.653s.
- Expanded handoff, authority, upgrade, recovery and SamePerson selections:
  **72 passed**, focused runner 467.488s. These include five whole-pack negative
  paths (missing frame, failed identity, held uncertainty, wrong asset and missing
  reference) and current-contract preservation; later readback display binding
  was strengthened and its downstream positive paths rerun as below.
- Final API/current native handoff, explicit uncertainty after takeover,
  imported-frame fresh handoff plus snapshot/restore/permanent non-resumption,
  and injected mid-transaction rollback: **4 passed**, focused runner 212.155s.
  Exact selectors are the four named positive/rollback cases in
  `tests/test_autopilot_handoff.py`. The fixture verifies machine units retain
  null human approval, old receipts remain unchanged and video rows stay zero.
- SamePerson plus initial manual/rollback run had 16 passed and one manual
  assertion failure (wrong assumed frame order). After correcting that fixture,
  the existing approval owner exposed duplicate-approval rejection. The durable
  `existing_human` reuse described above fixed it; corrected manual case passed
  in 52.556s before the final portable case above.
- Strengthened canonical display binding exposed stored Python names vs public
  JSON aliases. Its nine-case attempt had 1 failed/4 passed and was interrupted
  to avoid continuing against cached stale validator code (runner exit 2).
  The exact retained failing receipt passed read-only through the corrected
  typed normalization; the four affected positive/rollback cases then passed.
  Receipt bytes, validators and release coverage were not bypassed or weakened.
- Frontend unfiltered unit suite: **152 files / 1,288 tests passed** (final run
  6.72s); both frontend and E2E type checks passed. Focused new UI units: 4 passed,
  runner 0.910s. Late-project reads cannot display another project's run.
- Explicit affected browser files: `autopilot-review.spec.ts`, `first-save.spec.ts`,
  `manual-creator-entry.spec.ts`, `source-entry-settings.spec.ts`,
  `navigation-shell.spec.ts`: **26 passed**, focused runner 34.001s. Final launch
  admission/current manual-path and whole review refinements reran the affected
  autopilot/manual-entry files: **11 passed**, runner 22.355s.
- One initial browser field locator incorrectly matched the required marker in
  raw label text. Its 3 passed/1 failed run was corrected to the exact textbox
  accessible name; all four new browser cases passed (runner 4.609s), then the
  broader/final selections above passed. No product assertion was removed.
- Two final deterministic builds produced the same SHA-256 tree over **7 files**:
  tree digest `961862f2a819404d5685c91074934b3c8c3d50f1a170ca9983cb2952ac437095`.
  Generated assets are refreshed. Existing Vite large-chunk warning remains.
- Native test-owner discovery passed (no test bodies executed); current browser
  allocation passed: **91 specs / 303 cases**, no overlap/missing cases. New
  pytest/Vitest/browser files are registered in story-authoring. Module selection
  was expanded with `--show`; no module/full result is claimed from that plan.
- Ruff F checks and working diff checks passed. One existing Starlette/httpx
  deprecation warning accompanies Python checks.

Desktop pixel inspection used a disposable UI owner and local SVG thumbnails,
not ImageGen output: [whole story](2026-10-12-pre-video-autopilot/whole-review-desktop.png),
[reference gallery](2026-10-12-pre-video-autopilot/reference-gallery-desktop.png),
[frame observations](2026-10-12-pre-video-autopilot/frame-observations-desktop.png).
The final pictures show readable labels, contained uncropped display images,
scene/shot context, blank observations and separate identity decisions. They
prove software presentation only. Test opinions are explicit fixtures, not owner
creative acceptance. Tests ran in the isolated candidate working tree before its
source commit; exact-revision full/native qualification remains the manager's P5.

The additional owner-required careful walkthrough is a **P5 pre-activation gate**.
Its [touched-path map and disposable entrypoints](2026-10-12-pre-video-autopilot/touched-path-walkthrough.md)
cover the whole feature, ordinary manual flows, UI readability/accessibility and
persisted evidence. Manager labels real-native and deterministic fault results
separately. Source owner has not run full, contacted real native/media providers,
operated live services, upgraded valued data, merged/pushed main or claimed hosted
CI/product acceptance. The manager retains those scoped P5 responsibilities.

### P4 bounded review corrections

Initial P4 source checkpoint: `74d1dd857bf1be3753cb68cc63b7cebd9d4185b2`.
The source authority reviewer found omitted complementary character-reference
views and a false human-origin fallback. Manager-attended UI review additionally
found fresh Start never restarted polling, transient GET failure stopped it, and
dominant storyboard headings/guidance contradicted AI metadata. The manager's
separate backend review found no scoped blocker; that code-only result did not
qualify the changed complementary-view contract. Corrections require re-review.

Root causes and final behavior: the bundle previously represented only primary
assets while identity consumers used the complete decision. It now retains and
displays every selected view with original IDs/hashes/dimensions and endorses
the unchanged decision. Generated-frame applicability is rechecked against
current references after takeover; reselection withdraws old frames/eligibility
without altering receipts. Polling now explicitly reconciles command outcomes
and retries failed reads without replaying writes. Loading/failed provenance
remains unknown in headers, guides and metadata. Current manually imported frames
are labelled manual. An already-open review obeys read-only admission.

Executed correction evidence in the isolated working tree:

- Exact current API handoff, imported replacement/portable receipt and early
  takeover with primary plus two complementary views: **3 passed**, focused
  runner 134.906s. Original decision IDs and existing genuine approval survive;
  manually completed imported frames need no automatic bundle or extra dispatch.
- Reference reselection withdraws generated frames and preserves old receipt:
  **1 passed**, focused runner 47.393s.
- Final new UI selection: **13 passed**, focused runner 0.769s; final unfiltered
  frontend **152 files / 1,297 tests passed**, 6.45s. Both type checks passed.
- Broader UI selection (`autopilot-review`, storyboard ownership/source review,
  manual entry): 31 passed/1 fresh-progress fixture failure. Its fixture returned
  revision 12 after revision 14; correction returns monotonic revision 15 and
  preserves the client's stale-read guard. Final affected autopilot browser
  file: **6 passed**, focused runner 29.390s. This includes fresh no-run Start
  through review without navigation and transient read retry with one Start.
- Native owner discovery: **1,692 pytest cases / 169 files**; no bodies executed.
  Browser allocation: **91 specs / 305 cases**, zero missing/overlap cases.
- Two deterministic builds: identical **7-file** SHA-256 tree,
  `d66c553fc1252d9c3a7c8ae83b68d5e1649ece8f73d425f3592f0ab1390b56fd`.
  Refreshed desktop pictures above were inspected: all selected reference views,
  readable grouped labels/original links, current directions and blank judgments.
  Ruff F and diff checks passed; existing Vite/Starlette warnings remain.

Required continuation: same source owner handles diagnosed P5 issues, reruns
failed/downstream affected checks and rechecks affected walkthrough paths before
activation. Manager holds full/native/preservation/live work until this stable
correction is re-reviewed. Actual generated bundles remain awaiting owner human
review; labelled disposable protocol judgments do not grant creative acceptance.

Further exact-`dfb544d9` reviews closed full reference/currentness, Start/control,
storyboard and read-only findings, but found accepted-outline candidate and outer
Characters guide labels, lost handoff acknowledgment, and completed-run material
observation gaps. The bounded follow-up uses shared exact provenance, observes
completed runs, hides video entrance when currentness is unreadable, and
reconciles handoff by reads only. Committed results close the form; uncommitted
results retain authored inputs through read-only reconciliation. Another client's
receipt is observed without inventing this client's review or replaying its POST.
Final focused UI: **40 passed** (three files, runner 1.032s); unfiltered frontend
**152 files / 1,306 passed**, 6.30s, both types passed. Initial new browser attempt
and its already-running repeat each had 7 passed/1 failed: completed-frame
details were collapsed, so the value locator could not see the retained input.
Reassessed the interaction, reopened that section and kept strict value/disabled/
single-write assertions. Final affected browser result is recorded below.
Native discovery remains 1,692 pytest/169 files; browser allocation is now
91 specs/307 cases with no omissions/overlap. Two builds match seven files,
SHA-256 tree `d158bad2a6c332f6ddc6c8abfc82183b9e65c813c6241a8240e235902d379746`.
Backend evidence is reused because this follow-up changes only UI observation,
labels/tests/static assets/docs; API payloads and persistence are unchanged.

Final affected browser selection: **8 passed**, focused runner 32.711s, including
committed/uncommitted handoff acknowledgment recovery and retained authored values.

Same source authority reviewer closed both residuals and the additional lifecycle/
Characters findings at exact `a80428b1dffc3fafae7fa3a060ea19860529feb0`: no remaining
concrete defect in its bounded read-only diff review. No independent runtime run
or P5/creative acceptance is inferred. This final receipt update changes docs only.

Manager's same UI reviewer also closed all four residuals at exact `a80428b1`;
prior bounded backend review remains applicable to unchanged backend inputs.
The reviewed executable-source checkpoint is `a80428b1dffc3fafae7fa3a060ea19860529feb0`.
`dfbe1d1d42d6f9b3045afd07c792532aa9b63039` and this subsequent checkpoint change
receipt documentation only; they are distinct Git revisions. Manager must bind
P5 full qualification and any native execution pins to its actual chosen HEAD,
without relabelling earlier evidence. Source/dependency/configuration writes
are held for P5; same task/branch/Relay route remain available for diagnosed fixes.

### P5 failed gate and bounded repairs

Manager ran the full gate at exact `b1d09fa33aca95f89f8164ac4d8f66a96583c188`.
It ended exit 1 after 816.967s: Python worker 2 reported **14 failed / 832 passed**
in 420.76s. Manager deliberately SIGTERM'd unfinished worker 1 after the failures
were known; its incomplete result is not qualification. Supervisor cleanup raised
EPERM at `os.killpg(process.pid, 0)`. Manager confirmed no full/pytest workers
remained. Runner removed temporary logs; failures remain in the tool transcript.
No native generation occurred. Disposable QA server 9941 was stopped before edits.
The write hold was released explicitly for these diagnosed corrections only.

Closed startup failed because controller editing admission created a folder lock
before checking lifecycle/run existence. Controller progress and failure recording
now inspect read-only first and recheck under editing admission before writes.
Twelve route fixtures exposed background-runtime registration inside generic
specialist routes; composition now belongs to the application root. Route fixtures
implement the current frozen-pin/publication seam. The lock-order fixture returned
`offline` for Git pin checks as well as queueing; it now intercepts native queue
only. Original closed bytes/lock, transport, currentness and lock-order assertions
remain. Three added cases cover open manual, closed manual and closed run folders,
including failure recording, with no editable open, lock or WAL/SHM creation.

Driver source is unchanged. Root and source reaped-group diagnostics returned
ESRCH, not EPERM. A tiny disposable actual two-file/two-worker suite completed
normally, exit 0, in 0.264s, with both reports and cleanup. Nine runner regressions
include SIGTERM during collection/worker execution and real descendant cleanup.
This supports normal supervisor completion in the observed case; it does not
explain the earlier EPERM or qualify the real full suite. Never interpret denied
signal permission as absent processes or silently bypass cleanup.

Initial narrow repair selection passed **26 tests**, focused runner 6.854s.
An earlier local test insertion caused a collection SyntaxError and was restored
without removing existing assertions; an expanded attempt used a nonexistent API
selector and was refused before test bodies. The corrected affected selection is
recorded below. No full, native/provider, live, valued-data, CI or main operation
was performed by the source owner during repairs. Frontend/static/dependency
inputs are unchanged; their scoped evidence remains applicable, while changed
backend inputs require manager-owned requalification at the new stable revision.

Final affected focused selection: the complete runtime-boundary, project-specialist
ownership, specialist-route, controller-safety and Python-suite-runner files,
plus `test_start_api_retains_one_policy_and_refuses_browser_authority_fields`:
**72 passed**, runner 50.891s. Native owner discovery passed: **1,695 pytest cases /
169 files**, no bodies executed by discovery. Ruff F and working/staged/commit
diff checks pass; one existing Starlette/httpx warning remains. This is a repair
checkpoint, not a passed full gate or completed P5 walkthrough.

### P5 terminal-state and cleanup-race follow-up

Source review of `a366d404` found controller eligibility depended on projected
currentness rather than persisted completion. Manager stopped its fresh full
after 56.275s: frontend 1,306 tests/types passed, backend interrupted before
results. No source writes raced it; manager verified all workers absent and then
released bounded repairs. Full stdout is retained in ignored manager QA output;
SIGTERM cleanup again raised EPERM, with stderr in the manager tool transcript.

Persistence now owns `controller_execution_eligible`; stored `handed_off` and
portable identities cannot resume, and claim independently refuses completed
handoff. Paused/cancelled/taken-over receipt-only behavior stays intact. The first
enhanced pack test failed its assumption that ordinary reference reselection left
`handed_off` unchanged (37 other checks passed); it actually persists takeover.
The corrected real-pack test explicitly injects independent asset metadata drift
outside a human command, verifies durable handoff→stale projection, and proves no
editable open, claim change or native calls. It then retains ordinary reference
withdrawal assertions. No UI redispatch is claimed from this fault fixture.

The controlled two-running-worker diagnostic reproduced EPERM with an owned
UID-501 zombie-only group after SIGTERM, before `Popen` had reaped its leader.
The narrow driver fix reaps the exact owned child after a denied SIG0 probe and
reprobes only when exit is known. Only ESRCH proves absence; live/unknown or
persistent denial still raises. The corrected run observed EPERM→reap→ESRCH for
both PIDs 98671/98672, return codes -15, with no surviving members. Original and
corrected metadata are preserved in
[owned-worker diagnostic](2026-10-12-pre-video-autopilot/owned-worker-cleanup-diagnostic.json).
ADR 0160 records the cause, unchanged descendant cleanup and denial contract.

Focused handoff/controller/recovery/runner selection: **52 passed**, 79.799s;
runner-specific first selection: **13 passed**, 1.859s, before the actual paired
termination case was added to the final selection. Native ownership preflight:
**1,700 pytest cases / 169 files**; Ruff F and diff checks pass. Frontend/static,
dependencies, schema and request payloads are unchanged. Exact stable full/native
requalification and both reviews remain manager-coordinated; no new full/native,
live, valued-data, provider, hosted CI or main operation was performed by source.

Downstream late-receipt/authority, process-lease-before-claim and verification
driver contract selection: **46 passed**, focused runner 25.738s. This retains
inactive receipt-only and portable exclusion coverage. Existing Starlette/httpx
warning remains. Review closure is reported against the exact committed source,
without a subsequent receipt-only write during manager qualification.

### P5 concluded `ec2f00c6` failure and deadline-owned repair

Manager's full at `ec2f00c6dc635cbaa6badabe934a680f9a91a723` concluded exit 1 after
971.842s. Worker 1: **849 passed / 1 failed**, 944.71s; worker 2: **849 passed /
1 failed**, 369.93s. Frontend 1,306 tests/types passed; downstream full stages did
not run. Authoritative full output remains in ignored manager QA output
`output/playwright/pre-video-p5/full-ec2f00c6.log`. Isolated QA server 11093 and
browser stopped; native sends remained zero and valued/main data unchanged.

The real paired-worker test raised the first-probe EPERM while the helper's
nonblocking poll still returned running; its displayed return code was rendered
after test cleanup. Exact kernel membership at that failure remains unobserved.
Root's independent read-only review agreed with the branch diagnosis and the
bounded coordinator contract. Standalone `_process_group_exists` is strict again.
Only the shutdown coordinator, after successful TERM, waits for the exact owned
child within the remaining original deadline and reprobes. Timeout/persistent or
initial denial still fails, with no escalation of an unresolved denied group.
No blanket ignore, fixed sleep, new grace period, platform branch or process scan.

The portable-restored handoff test failed because the newly added local completion
guard hid the existing portable refusal. Portable identity now takes precedence;
every original eligibility, receipt, no-resumption and diagnostic assertion stays.
The unchanged affected handoff case and initial runner selection passed **20
tests**, focused runner 59.149s. Final downstream runner/cleanup, verify driver,
module ownership, recovery and authority selection passed **80 tests**, 12.876s.

Cleanup cases now live in `test_python_suite_cleanup.py`, sharing one runner loader
with the collection/coordinator tests. Original real pair/descendant assertions
are rehomed unchanged; obsolete standalone recovery cases are replaced by strict
observation and coordinator-specific regressions. Coverage includes delayed exit,
survivors, child timeout, persistent/initial denial, missing original groups and
two-group shared deadline exhaustion. Native ownership preflight passed **1,706
pytest cases / 170 files**. Ruff F and diff checks pass; existing Starlette warning
remains. Frontend/static/dependency/schema/request inputs are unchanged. No source
full/native/live/hosted CI/push occurred; full/native/walkthrough/activation remain
manager-owned and pending against the next reviewed stable revision.

### P5 concluded `17e62bc2` failure and combined repair

Manager's full at `17e62bc23c5d288a6cffb45d78d390da3344918f` concluded exit 1
after **1,392.272s**. Python **1,706 passed** with a new unhandled controller
thread EBADF warning; that warning is a failure to qualify safe ownership.
Frontend **1,306 passed**, both types/build parity/shard coverage passed, then
browser **305 passed / 2 failed**, 501.769s. Wheel/smoke did not run. Authoritative
output is manager-owned ignored `output/playwright/pre-video-p5/full-17e62bc2.log`,
with browser evidence under `browser-failures-17e62bc2/` in the same QA root.
The isolated QA server/browser stopped; source did not touch that QA project.

The combined candidate repair addresses four demonstrated boundaries:

- Edit/revert/restored Brief draft deletion correctly leaves Brief r1 unchanged,
  but launch observation had no invalidation after draft cleanup. Authoring now
  publishes a project-bound observation version only after validating the exact
  consumed draft revision and current operation. Launch rereads the authoritative
  server and aborts superseded reads. No dirty/saving dependency, revision bump,
  Save remount/navigation, optimistic eligibility or Start replay.
- Concurrent start publication before `Thread.start()` returns could produce two
  workers while tracking only one. Concurrent descriptor release independently
  reproduced EBADF. Separate lifecycle and descriptor locks establish one worker
  and exact single release; overlapping lifespans retain it until the final owner
  exits. The existing unbounded owned join remains; no EBADF suppression.
- Controller discovery and `_step` inspection each acquire a real shared lease
  on a normally closed retained-lock folder. Event-gated pre-fix captures proved
  PID **7007**, thread **plotloom-pre-video-controller**, site **discover**, FD
  **12**; and PID **7007**, thread **passive-inspect_0**, site **inspect**, FD **12**.
  The controlled reopen failed at both sites. Per-project observation admission
  now waits for admitted passive reads and prevents new passive reads while an
  explicit exclusive transition is pending, retaining the actual OS leases and
  genuine writer/native refusal. The original full Cast holder is not identified
  by these controlled captures; no retrospective PID/site claim is made.
- Creator review intentionally displays the frozen “来源剧本” provenance. Its
  old wording assertion was stale. The repaired test retains the entire binding,
  exact review revision/hash and frozen Script revision, proves current Script
  revision/hash differ, and preserves stale/no-F4/no-auto-media assertions. The
  trailing displayed hash belongs to the review, not its bound Script.

Five event-gated pre-fix runtime cases failed; all five passed after the repair.
Two added guards prove late passive blocking and genuine foreground shared-holder
refusal. The normal closed-WAL/retained-lock whole file-byte tree remains unchanged
through discovery, step and failure observation; old DELETE/absent-lock/no-sidecar
assertions remain. Ignored `.local/p5-runtime-race-gated-before.log` and
`.local/p5-passive-holder-evidence.log` retain controlled evidence.

Executed source checks on this combined candidate, against `17e62bc2`:

- Focused runtime/controller/original concurrent ingest/project-storage batch:
  **43 passed**, runner 40.626s. Final runtime/observation guard batch: **29
  passed**, runner 29.401s. Authority/recovery/native storyboard blocker/app
  runtime-boundary batch: **46 passed**, runner 15.564s.
- Original image-ingest concurrency case plus seven runtime cases: **8 passed**
  with actual pytest `-W error::pytest.PytestUnhandledThreadExceptionWarning`,
  1.62s. An earlier `PYTHONWARNINGS` module setting was rejected and supplied no
  warning-enforcement evidence. Existing Starlette deprecation remains.
- `quick`: **1,308 frontend tests / 152 files**, both type checks and required
  quick checks passed, runner 13.014s. Focused admission/provenance unit owner
  also passed before the unfiltered quick suite.
- Both previously failing full browser specs passed all **14** cases in the
  three-spec batch; that batch had 21 passes and one new test assertion failure.
  The new no-op test first expected a query parameter instead of the actual
  DELETE body/header. Its next attempt captured the older restoration GET. Trace
  showed false GET, exact draft r2 DELETE 204, then true GET at Brief r1. After
  reassessing the wait boundary, restoration observation is awaited before Save.
  Final whole manual-creator spec: **8 passed**, runner 29.344s, including exact
  body/header, unchanged canonical response and connected editor, fresh true GET,
  no canonical/Start writes or run. No production workaround was added.
- Affected autopilot-review/first-save browser specs: **12 passed**, runner
  32.164s. All **34 distinct selected browser cases** now have passing evidence;
  this is scoped evidence, not an unfiltered browser/full pass.
- Two deterministic builds: identical **7-file** SHA-256 tree
  `58f7a4f9b19e40a8fb08c77d393a585b191e701daee3da19e773beb0b20f9b56`.
  Generated static assets refreshed. Desktop Brief screenshot inspected: CTA and
  authoring fields are readable; retained at
  `.local/p5-pixels/unchanged-brief-admission.png`.
- Native ownership preflight: **1,714 pytest cases / 171 files**; new runtime
  owner registered. Browser allocation: **91 specs / 308 cases**, shards
  **84/72/71/81**, no missing/overlap. Ruff F and diff checks pass; a pre-existing
  unused local `media` in the touched lifecycle module was removed, with no
  admission behavior change.

Both attended independent source/test/config reviews closed without actionable
findings. ADR 0162 and the same touched-path map record the repaired ownership
contracts and next walkthroughs. No source full/native/provider/live/valued-data,
hosted CI/merge/push operation was run. After the reviewed clean checkpoint, all
source/test/docs writes and source checks hold for manager's exact-revision review
and fresh full qualification. Native capability proof, preservation/cutback,
release/activation and owner creative acceptance remain separate pending gates.

### P5 passed `efee445c` full and positive-draft observation repair

Manager reports full qualification at
`efee445c181f2b5361e065d4ab17832418ee5762` **passed**, exit 0, **1,365.207s**:
**1,714 Python** (two workers of 857; only existing Starlette deprecation, no
unhandled controller warning), **1,308 frontend**, **308 browser**, both type
checks, deterministic static/parity, allocation, wheel and installed smoke. Full
log: manager-owned `output/playwright/pre-video-p5/full-efee445c.log`.
Previously failing Cast/Creator cases passed. Disposable current-efee preserving
upgrade/rollback/idempotence/forward portable/actual old-731-runtime committed
backup cutback also passed with **11 retained files**; evidence is manager-owned
`preservation-efee445c.json`, root `/tmp/plotloom-p5-preservation-efee-9B3mxU`.
The first helper invocation failed solely for missing PYTHONPATH before fixture
creation; its separate import-failed log remains historical failed evidence.
These were manager operations, not source executions.

Passing full did not authorize activation: the actual manager walkthrough found
cached Start enabled after exact title edit/revert and two acknowledged durable
draft PUTs. Server eligibility was correctly false at Brief r1, but no new launch
GET followed requests 49/50. Autosave owned successful receipts without notifying
admission observation; payload equality only cleared the editor's dirty flag.
The earlier exact no-op cleanup path had independently passed. No Start/native
send or canonical write occurred. Manager evidence: traces
`.playwright-cli/traces/trace-1791837735733.{trace,network}` and
`edit-revert-stale-start-efee-{1440x900,scrolled}.png` under the same ignored QA
root. Manager cleaned the exact second draft through ordinary Save: drafts empty,
run null, canonical response SHA-256 unchanged
`549ecd9863fd8f8851609752b6b3940ca10d2265220628e7e92341bf8689d979`.
QA browser closed and server session 72610/PID 33509 shut down gracefully, exit 0.
Source did not touch that QA project or preservation root.

The bounded frontend correction shares `observeAuthoringMutation` at the authoring
owner. Matching current-operation durable PUT acknowledgments and validated
consumption/discard receipts advance its project-bound observation version;
recovery and close-time discard and same-owner graph recovery use that callback.
Local-only operations do not manufacture server mutations. Existing late source
acknowledgments retain their evidence but cannot refresh a newer project/operation.
Recovery mismatches/failures remain unconfirmed. Launch visibility requires an
authoritative response for the current project/Brief/observation key, withdrawing
older eligibility while a new GET is pending and ignoring aborted old responses.
No dirty/saving dependency, canonical revision bump, polling, Save remount/reload/
navigation, optimistic eligibility or Start replay.

Risk-scoped qualification reviewed the actual diff against trusted `efee445c`,
including the added unit file: frontend observer/hooks, launch presentation,
tests, their ownership metadata, generated `workbench.js` and these documents.
Backend executable source, API/response schemas and request payloads, database
persistence/operational admission/auth, generation/provider/prompt contracts,
dependencies/lockfiles, build tooling and package code/configuration are unchanged.
Existing requests keep their endpoints and bodies; new behavior publishes owned
receipt observations and reads eligibility. The static package payload changes,
so it is rebuilt and checked below. Passed efee backend/preservation evidence has
unchanged code/dependency/configuration inputs; manager decides reuse. This is
frontend qualification, not a new exact-SHA full pass or native/product acceptance.

Executed source qualification for this bounded repair:

- Minimal autosave/graph-read/autopilot unit owners: **36 passed**, runner 0.865s;
  separate exact recovery/close receipt owner: **6 passed**. Checks cover pending
  receipts, late project/operation ACKs, mismatch/failure/superseded discard and
  immediate withdrawal of previously eligible launch during a fresh read.
- Final `quick`: **1,318 frontend tests / 153 files**, both type checks and quick
  gates passed, runner 13.023s. The first quick attempt passed units but rejected
  partial typed session casts in the new test harness; complete typed stubs now
  fail explicitly if an excluded canonical command is invoked. No production
  contract was weakened to fix that fixture.
- Whole manual-creator spec: **10 passed**, runner 32.749s. At 1440×900 and
  1440×600, fresh true → each actual PUT200/false GET → edit/revert still false →
  exact r2 DELETE204/header2 → true GET at unchanged Brief r1. Same URL/editor,
  canonical response unchanged, run null; exactly two PUTs and one DELETE, no
  Start/send/canonical writes. Only specialist availability metadata is mocked.
  Existing restored-draft/no-op/manual-material assertions remain. Its first
  run had 9 passes/one wait failure from an older restoration GET; each prior
  observation is now drained before the cleanup read, without a production
  workaround. Final additional action-scroll captures: whole spec **10 passed**,
  runner 33.744s.
- Affected whole browser specs `autopilot-review`, `project-folder-authoring-drafts`,
  `project-read-close`, `project-save-force-close`, `draft-recovery-presentation`
  and `navigation-shell`: **32 passed**, runner 79.062s. Together with manual
  entry, **42 distinct selected cases** have passing evidence. This is scoped
  browser evidence; no source full gate ran.
- Desktop and short-viewport withdrawal/restoration/Start screenshots inspected
  at 1440×900 and 1440×600. Start remains reachable by scrolling and text/actions
  are readable. Six captures retained in `.local/p5-positive-draft-pixels/`.
- Two serialized deterministic builds: identical **7-file** SHA-256 tree
  `55814d2f388bdf21e5973cbd96bdfcf993a05645e2df7094ca3395129e2ac215`.
  All seven packaged static members match those source hashes. New wheel SHA-256:
  `e64fa2ef994129a2ec8684328de9eca33aead69caeec48d1ab1fca02f603741e`;
  `uv build --wheel` and `scripts/smoke_installed_wheel.py` passed in disposable
  package/environment roots, without a source fallback or provider/native work.
- Native ownership discovery passed without test bodies; Python union unchanged
  at **1,714 cases / 171 files**. New unit owner registered; browser allocation
  **91 specs / 310 cases**, shards **84/72/71/83**, no missing/overlap. Diff checks
  pass. No dependencies, model defaults or active task settings changed.

Both bounded source reviews closed without actionable findings; final additions
remain in the same ADR, receipt and walkthrough. After the clean reviewed commit,
all writes/test bodies hold for manager review and repeat actual-path inspection.
No source full/native/live/valued-data/hosted CI/merge/push occurred. Native
capability proof, preservation reuse decision, release/activation and owner
creative acceptance remain manager-owned separate gates.


## P5 frontend guidance / delivery disclosure checkpoint · parent 4817e741

Root cause: source/characters showed manual preparation instructions while a known
run owned automation, and the final review omitted immutable declared limitations.
Shared guidance now states actual phase, one whole human review and manual-save
takeover without changing action ownership. Exact operation/revision/hash labels
cover outline, current admitted branches, Cast/Art/Script/Storyboard and bridge;
report reads stay enabled and non-mutating. Unknown run reads do not assert an
automatic producer; intent-only adoption never labels presentation adopted.

Four existing read-only GETs bind every displayed generated asset to its exact
project/hash, owner kind/ID, candidate role, accepted delivery and manifest.
Limitations stay verbatim. Explicit empty declarations, unavailable evidence and
unlinked provenance remain distinct. Retained original and adapted outputs show
separate dimensions/declarations/identities without an improvement claim.
Cancellation/project/bundle guards and explicit retry preserve authored inputs;
no extra polling or mutations were introduced. Two independent source reviews
closed the concrete unknown/adoption/candidate-owner findings; neither ran checks.

Risk scope reviewed against parent `4817e741c959a968994469ce889d86d81e27b4de`:
backend source outside generated static is unchanged; client request URLs,
payloads, server schemas, persistence, admission/auth, prompts/providers, geometry,
dependencies and build/package code are unchanged. The client only adds AbortSignal
to existing asset GET and describes fields already returned by the server. Test
ownership/shard manifests register new coverage; they do not filter required gates.
Earlier efee445c full/preservation evidence stays historical with unchanged backend
inputs; the manager decides reuse. No full gate at this frontend checkpoint.

Executed source-owner evidence:
- `verify.py quick`: 156 files / **1355 units**, both type checks, exit 0,
  16.909s; `.local/p5-frontend-quick-final.log`. Initial quick caught a new role
  union typing error after all units passed; typed comparison corrected, no
  assertions weakened. Focused provenance tests preceded the unfiltered quick.
- `verify.py focused`: **41 browser cases**, 65.102s exit 0 across exact specs
  `autopilot-guidance`, `autopilot-review`, `creator-workflow-navigation`,
  `source-entry-settings`, `recommended-{cast,art,script,storyboard}-workflow`,
  `production-presentation`, `production-bridge-review-refresh`.
  `.local/p5-frontend-browser-final.log`; no native generation or provider calls.
- Native ownership discovery only: 1714 pytest/171 files, 1355 units/156 files,
  314 browser/92 files; no Python test bodies. Shards **84/72/71/87**, no overlap
  or missing cases. `.local/p5-frontend-ownership-final.log`, `p5-frontend-shards.log`.
- Four 1440×900/600 disclosure screenshots inspected: readable declarations,
  wrapped identity hashes, distinct original/adaptation and intact review inputs;
  `.local/p5-disclosure-pixels/`. Scroll access remains intact at 600px height.
- Two serialized deterministic builds match all seven static files; sorted manifest
  SHA256 `f2f15c5225bd475ed890043dd8119c37c7f789a9240f46ac339540ae46cdd992`.

- Wheel SHA256 `b9381b5341e5befb4eaca659915b56b89701d59a1bcbe7a95539c7777cb0977c`;
  installed-wheel smoke passed, all seven archive static members byte-match the
  working tree. `.local/p5-frontend-wheel-smoke.log`. Diff checks pass.

Manager-owned old native proof remains **partial**, paused at revision 64 after
both 941×1672 original and its one native adaptation missed frozen 720×1280.
No completion or creative acceptance is implied. The existing run/package/policy,
originals/blocker/reservation/pins and upstream report bytes were untouched.
Owner approved centered crop+resize with retained originals and final human review
as a **new policy**; it is not implemented by this frontend checkpoint or permission
to reinterpret old evidence. Next is that separately bounded geometry slice;
manager full/native/preservation/release/activation and owner acceptance remain.


## P5 attended frontend review and v2 geometry source checkpoint · parent 3e2833d3

Manager attended review accepted exact frontend `3e2833d3bddaa5e0e2220f01c88ceb6134bc6056`
against 4817 as scoped frontend evidence. Manager verified retained quick/types/41
browser logs, committed wheel/static bytes, diff scope and all four desktop pixels;
independent committed-object review found no concrete defect. No manager test bodies
were rerun and this established no full/native/activation or creative acceptance.

Owner approved centered crop+resize with originals retained. Real original and its
one generative adaptation both produced941×1672 for720×1280: semantic generation
was the wrong geometry mechanism; exact admission was correct. Before code, ADR0162
and the accepted contract were amended. Fresh policy `plotloom.pre-video.v2` freezes
recipe/runtime and discloses preparation at Start. Existing v1 remains immutable
and readable/reconcilable without new start/resume/preparation authority. Ordinary
manual ImageGen adaptation remains explicit and exact raw adaptation rejection
remains covered. Old native jobs/receipts/counts/reservation are not reinterpreted.

Only accepted raw first-frame originals failing exact Brief aspect get a bounded
EXIF/RGB centered-cover LANCZOS PNG derivative at the frozen target. Matching aspect
preserves original bytes/dimensions. Typed `GeometryPreparation` links existing
checkpoint/decision/frame owners: project/run/policy/claim/shot, source native
candidate/job/request/delivery/execution, raw SHA/geometry, orientation/crop recipe/
runtime hashes and managed output SHA/geometry. Local preparation scope and exact
selection scope are separate. There is no native derivative job/candidate/manifest,
provider call, reservation or extra generation count, and no SQLite layout change.

The strict single-hop resolver drives provisional/open/recovery/review/human
selection/SamePerson/shared reviewed admission. Material closure and human receipts
bind preparation hash. Source V3 conditioning survives; actual human observations
bind derivative bytes and lineage. Unknown/tampered generated evidence cannot become
an unrelated imported-human fallback. Genuine earlier-schema raw HANDOFF context
remains a supported explicit boundary after native evidence resolution.

Reviews found and closed an introduced shared-refinement regression: requiring the
frozen parent to stay selected after adopting its output invalidated that output.
Separate frozen intent/presentation/approval from current selection; recursively
validate every generated ancestor's context, authority, references and cancellation,
with a cycle guard. Before adoption require the current parent; afterward require
this delivered job's exact selected output. Actual A→B→C selection/next-refinement
cases retain eligibility, then withdraw after cancelling A or replacing A's intent.
Both independent geometry source reviews and authority correction rechecks closed
without remaining actionable findings; reviewers did not execute checks.

Development diagnosis also closed two implementation gaps: a standalone contract
hash import cycled through persistence composition, and missing geometry bytes were
not detected by relational open validation. Canonical JSON hashing now has a small
pure owner with unchanged serialization/reexport; geometry lineage checks confined
content-addressed raw/output bytes. Snapshot stages DB first, so pre-copy validation
uses the explicitly frozen source asset root; copied destination validation uses
its own assets. A controller advance stops after one geometry operation before
another native preparation. Crash fixtures preserve actual RuntimeError behavior
and acquire the real process lease on restart; guards/assertions were not weakened.

Final source-owner executed qualification:
- **Focused54 Python cases**, exit0,291.950s runner /280.03s pytest:
  `test_autopilot_geometry.py` (23), `test_image_source_lineage.py` (2),
  `test_project_storage_image_workflow.py`, exact manual adaptation case in
  `test_project_storage_image_delivery_contracts.py`,
  `test_project_storage_image_identity_contracts.py`,
  `test_same_person_review_contract.py`, `test_autopilot_image_safety.py`.
  `.local/p5-geometry-source-final.log`. Includes three target sizes, EXIF,
  matching aspect, no-dispatch/count, concurrency/idempotence, transaction/selection
  interruption/restart, seven tamper/missing guards, stopped runs, portable partial
  snapshot and genuine derivative handoff/eligibility withdrawal.
- **Focused49 preservation/authority cases**, exit0,77.740s:
  `test_autopilot_recovery.py`, `test_autopilot_schema_upgrade.py`,
  `test_autopilot_authority.py`, exact manual-import replacement/handoff case.
  `.local/p5-geometry-preservation-focused.log`. This is scoped regression evidence,
  not manager valued-folder upgrade/cutback qualification.
- Earlier focused5 lifecycle/reselection cases passed,143.084s:
  transaction+selection restarts, portable snapshot, reference reselection for raw
  and one derivative. Three also reran in final54. The later refinement correction
  changes the reviewed-parent branch; the reference check over raw originals stays
  unchanged. `.local/p5-geometry-lifecycle-final.log`.
- Final retired-policy boundary refinement: repository resume and all six new
  machine command scopes refuse v1; EVIDENCE/HANDOFF remain permitted. A new
  disposable-v1 domain case plus `test_autopilot_authority.py` and
  `test_autopilot_late_receipts.py` passed **25 cases**, exit0,20.309s;
  `.local/p5-geometry-policy-boundary-final.log`. Geometry owner now has24 cases.
  This last guard changes only v1 refusal; the v2 branch exercised by final54
  stays unchanged, so its evidence is reused. Wheel was rebuilt after the guard.
- **Quick1361 units /156 files**, both type checks, exit0,12.943s;
  `.local/p5-geometry-quick.log`. Exact disclosure/review42 units and whole review
  **13 browser cases**, exit0,34.986s; `.local/p5-geometry-ui-focused.log`.
- **Four affected real-backend browser journeys**, exit0,31.029s:
  `image-jobs`, `aspect-ratio-currentness`, `project-folder-still-image-workflow`,
  `autopilot-guidance`; `.local/p5-geometry-browser-consumers.log`. Generation,
  media/clip rows and provider behavior are deterministic test-owned fixtures;
  there were no live/native provider operations. Two geometry desktop captures
  inspected at1440×900/600 in `.local/p5-geometry-pixels/`, preserving authored inputs.
- Native discovery only:1739 pytest /173 files,1361 units /156 files,
  316 browser /92 specs. Shards84/72/71/89, zero overlap/missing cases.
  `.local/p5-geometry-ownership-final.log`, `p5-geometry-shards.log`. New owners
  registered; discovery ran no Python bodies and does not replace release gates.
- Two serialized deterministic builds match seven static files; sorted manifest
  SHA256 `4c5bd2da740221f2f8cf7f2e24fb0d65690be86182340d6587fb6d28c65da770`.
  Final wheel SHA256 `316a661bb258fe8963241e2b419e8221deb89ed5fc997dcdc479f00a5325ba73`;
  installed-wheel smoke passed. Seven static and all25 changed Python archive
  members byte-match working sources. `.local/p5-geometry-wheel-smoke-final.log`.
  Earlier wheel `0bb38a2850e6cba1eeab4d2b3577350925536eb0f14604355727a8d0b063682e`
  predates the final v1 domain guard and is superseded, not qualified as current. Diff checks pass.

Actual retained native-byte mechanical proof (no adoption/dispatch): copy from
`ij_de3437cdc57a47e48715d8e5cadf8401`, candidate
`80b4a0d6-4a40-4a03-aa3b-b7901d6e0b40`, raw941×1672 SHA256
`30f3a733e973371a38f3fcd4fa4f47ef9081da240b7dbfe215cc70636a339be7`
produced exact720×1280 SHA256
`1f36e3318d68549ae96e70db10fd3c9bf4d6934673ac8a7023911fce36c5d1c8`.
Recipe crop box `[0.25,0,940.75,1672]`; only ignored copies in
`.local/p5-retained-native-original/` were written. Before/after old source and QA DB
hashes were actually compared and stayed equal; the proof retained boolean DB
preservation, not explicit DB digest values. No retrospective pre-hash is invented.
An additional immutable read-only SQLite validation accepted existing v1 contracts
at actual paused revision64 without changing DB bytes. Manager independently hashed
copies/source, observed dimensions and viewed both. The near-aspect center trim
showed no observed loss of person/hands/stone/plate in that mechanical inspection;
this is not an identity/quality pass, new native delivery or whole-pack review.

This cross-layer slice changes executable contract/currentness/recovery inputs:
earlier backend/full evidence cannot qualify it. After the clean reviewed source
commit, hold all source/dependency/config writes and test bodies for manager
attended contract review and **one fresh exact-candidate full**, then distinct
fresh native proof/preservation/release/activation gates. No source full, hosted
CI, main merge/push, live activation or provider/video/voice generation occurred.
Old4817 QA/project/run/package/policy/pins/blocker/queued reservation remain retained
and **partial**; owner creative acceptance is still pending.
