# Pre-video autopilot · single evidence receipt

Original October 12 baseline: **Implemented, locally qualified, walked through
and activated on the existing installation (Toronto), executable b6f0525d.**
The exact927 full plus b6 scoped frontend qualification, real native97 proof,
final b6 retained-pack recheck and actual-valued preserving rollout are recorded
below. Hosted CI was not dispatched; owner creative acceptance remains separate
and pending. Earlier failed/pending checkpoints below are historical, not the
current release status. Scope and stopping boundary are in the
[approved plan](../roadmap/2026-10-12-pre-video-autopilot.md#p0-implementation-checkpoint)
and [ADR 0162](../adr/0162-pre-video-autopilot-authority.md).

The owner-approved UX/Brief-style and creator-confirmation follow-up is now
technically closed out on executable source `ee7ec8de` and activated on the
existing installation. Combined local software qualification, real frozen-package
delivery and preserving activation are recorded in the final manager section.
Publication is the next manager operation. Hosted CI and owner creative acceptance
remain separate and unconfirmed. The original completed valued run retains its
frozen `c771cdd6` policy and jobs, awaiting genuine human review; it was not
converted to the new executor.

## Revision and authority

- Production source/test baseline: `731cfdbfb0d9139254e30c34c2a8e7669a98ddba`.
- Sole writer checkout: `/Users/wjmao/projects/HU/plotloom-worktrees/pre-video-autopilot`,
  branch `codex/pre-video-autopilot`; main and owner data stayed untouched during
  implementation. The manager later performed the approved rollout below.
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

## P5 blocking shared-publication repair · parent 421c7533

Manager preserving review found a P2 crash gap before starting fresh full.
The shared `_OwnedArtifactStore.put` used `_write_new_file` to create the final
SHA path and then write in place. A disposable child killed by actual SIGKILL
inside that primitive's partial write left17 of31000bytes at canonical SHA
`58683f2e884a0edc2c60da9dba72425120250f2fc4c63e2b4b3aa4acafc9ce68`;
actual SHA `eba5f936a815a72a8e6ff3571a08a43be20d13f16ea91ad0d1ef447d633d5a13`.
Same-identity retry raised storage corruption and preserved those bytes. The
ordinary exception handler cannot run after process death. Reproduction root
`/var/folders/ys/g3nd6nfx2xd9wmw053lg109m0000gn/T/plotloom-publication-actual-before-ueni6vz_`
and `.local/publication-repair/actual-before.json` remain disposable evidence.

The manager approved the protocol after primary SDK/API review; ADR0162 was
amended before code. `artifact_publication.py` now owns confined descriptor-relative
staging and durability; `exclusive_rename.py` implements one no-overwrite contract
using macOS renameatx_np/RENAME_EXCL and Linux renameat2/RENAME_NOREPLACE. No dependency
change, replace fallback, link/unlink window or repair of corrupt canonical bytes.
An admitted parent hosts a fresh0700 private sibling directory; full single-linked
staged bytes are fsynced and verified before promotion. Existing/racing winners
must pass regular/single-link/inode/size/SHA checks. Destination prefix, assets,
project and outputs-parent directories are synced before the caller records metadata.
Live cleanup removes only this invocation's identified file and exact empty
directory; retained descriptors prevent inode-number reuse during cleanup. Altered,
foreign or interrupted stages stay forensic outside portable payload and discovery.

Runtime prerequisites are explicit: writable outputs parent, same filesystem and
native exclusive rename. Permission, unsupported flags/API, real EXDEV or sync
failure refuse; no parent chmod, alternate root or deployment/provider changes.
Existing read-only inspection still writes nothing. `_write_new_file` remains under
its other private package owners; the demonstrated content-addressed gap is fixed
at the shared managed owner. Raw/derivative hashes and database layout stay unchanged.

Verification on the final source inputs (ignored detailed logs under
`.local/publication-repair/`, qualification input hashes retained there):

- Shared25 cases passed in `resource-repair-final.log`: actual SIGKILL partial/before/after
  promotion, same-identity retry, retained old stages, two-process native race,
  single link, file/ancestor sync before metadata; unchanged valid/corrupt/foreign
  files, hard links, symlinks, dangling links, directories/FIFOs, foreign parents,
  altered staging and read-only/expected-hash refusal. Capability/permission/EXDEV
  failure injection never selects a fallback. Final inspection demonstrated an
  exception-only descriptor leak: actual test-owned entry disappearance raised
  FileNotFoundError before handle construction and left the opened FD alive.
  `descriptor-before.log` preserves the failed regression. Validation/writing
  helpers now close descriptors in `finally` and use `closefd=False`; the original
  staged FD stays stack-owned while only the writer uses a duplicate. Final fault
  regression confirms closure. No relaxation of identity or byte checks.
- True geometry-controller crash cases passed3/3 together with shared25 in27.75s,
  `resource-repair-final.log`. SQLite import/checkpoint rollback, same output hash,
  one eventual derivative/checkpoint/frame, unchanged native jobs/candidates/send
  lists and raw bytes, prior stage preservation and snapshot after retry. Initial
  uniform-frame fixtures reused an already-published reference hash and correctly
  never reached I/O: failed diagnostic runs are retained, not counted as passes.
  The corrected marked frame asserts its canonical identity is absent before fault.
- The earlier stable artifact/geometry union passed51 in218.22s,
  `artifact-geometry-final.log`, before the exception-only FD correction. After
  that correction, refresh all25 shared and3 crash cases plus the six affected
  geometry consumer cases: original preservation/no native increment, concurrent
  preparation, transaction/selection restart, snapshot and full derivative human
  handoff/withdrawal passed6 in93.39s (`geometry-consumers-final.log`). Unchanged recipe, v1 authority,
  missing/tampered lineage, stopped-run and aspect branches retain their prior
  scoped evidence; the correction only changes descriptor ownership on exceptions.
- Shared/manual/refinement/recovery focused selection refreshed42 in7.92s;
  `preservation-final.log`: exact storage-confinement/secret-profile case,
  `backend_core/test_artifacts.py`, complete `test_project_storage_recovery.py`,
  `test_autopilot_recovery.py`, `test_project_storage_image_workflow.py` and
  `test_image_source_lineage.py`. No production provider operations.
- Real Linux native probe passed on existing bookworm image20bf47acac0a in a fresh
  disposable container, no network/build/install/mount or live-container operation.
  Actual renameat2, partial/before/after SIGKILL retry, native competing winner,
  single-link bytes, sync calls before metadata and six corrupt/foreign refusals.
  `linux-native.json` binds all three final source hashes; no mocked Linux API.
  Host macOS tests use actual renameatx_np. These establish process-death/native
  protocol behavior, not a physical power-loss/filesystem recovery experiment.
- One independent bounded stable publication review by the existing persistence
  reviewer closed with no actionable findings. Read-only, no reviewer test execution;
  platform result evidence remains source-owned. The same review reopened only for
  the concrete FD-ownership finding and closed with no remaining issues. Effective
  model unverified; no second broad independent review or coding delegation.
- New tests registered to story-authoring/project-lifecycle. Complete native
  ownership discovery passed1767 pytest/175files,1361 units/156files and316
  browser/92specs; no test bodies. Module `--show` only prints its plan.
  No full/module bodies or equivalent collection of release gates ran.
- Final wheel SHA256
  `38f8a7d8d6d00702d345683243e7adf1ce45be749b789688eadd25441d67cffe`;
  installed-wheel smoke passed. Three changed Python and seven static members
  byte-match sources. Static SHA256 remains
  `4c5bd2da740221f2f8cf7f2e24fb0d65690be86182340d6587fb6d28c65da770`.
  Prior1361-unit/type/browser/pixel/deterministic-static evidence is reused because
  no frontend/static/request/provider/prompt inputs changed in this repair. The
  previous wheel316a and interim publication wheel8f9190 are superseded. Targeted
  Ruff and diff checks pass.

Final-source focused selections passed **76 executed cases** (28 publication/crash,
42 preservation and6 geometry consumers); earlier51 union remains recorded with
its resource-correction boundary. Checks bind final source hashes in the local
qualification inputs; the source commit is reported by the normal Relay final.
Hold all source, dependency/config writes and test bodies again for manager attended review and
one fresh exact-candidate full. Full/hosted CI, preservation/release/activation and
distinct fresh native proof remain separate manager gates. This repair performs
no old-QA operation, provider generation, main merge/push or live activation and
does not establish owner creative acceptance.

## P5 manager-qualified native97 and three released path repairs · parent 97e6eeb0

The manager's exact97 full passed: **1767 Python,1361 frontend,316 unfiltered
browser cases**, deterministic static/parity and installed-wheel smoke;
`output/playwright/pre-video-p5/full-97e6eeb0.log`, final1389.775s exit0.
This qualifies97, not the changed repair candidate below.

Manager fresh native97 proof finished against a distinct disposable project
`6920b255-080d-4e32-a0c5-83d9c31d489f`, run
`b41a3522-4b6d-4bba-8ec8-0ffac45c92d8`: all8 text and7 image jobs completed,
**exactly7 actual ImageGen calls**, four references and three unique route frames.
Every original941×1672 remains preserved beside a distinct typed720×1280
derivative. Final state `awaiting_review`, revision76, `material-review`, no
handoff; registry15 completed jobs, no leases, both specialists idle. The manager
stopped only isolated workbench/bridge9951/9952 with clean exit0. Live main/runtime
remains731cfdbf; source worker performed no native, provider or live operation.

Native evidence is bound to97: `native97-observation-images-complete.json`,
`native97-managed-assets.json`, `native97-imagegen-calls.json` and the native review
captures under `output/playwright/pre-video-p5/`. Actual native-pack recovery
`native97-recovery-proof.json` records snapshot148 files including DB,147 retained
non-DB files, portable restore and resume/claim refusal. Original DB SHA256
`36708adede61ef9f9976ec6046d5e5f308cb513cacf3e45055af5ca739cee69a` stayed unchanged.
Approval, VisualIntent, reviewed binding, SamePerson, handoff and video rows remain
zero. This is complete technical native-pack/recovery evidence, **not visual owner
acceptance**. `preservation-97.json` separately records a disposable prior-layout
fixture with11 retained files/row hash, post-DDL rollback, idempotent rerun, portable
restore and old-runtime cutback; it is not a valued-owner-project rollout.
`linux-bind-publication-97e6eeb0.json` provides manager native Linux publication
evidence on a bind filesystem; shared publication source is unchanged by this slice.
The old4817 paused run, package/policy/pin and queued reservation remain historical.

The actual walkthrough found three bounded current-contract defects, retained in
`native97-provenance-finding.json`, `native97-early-review-finding.json` and
`native97-phase-finding.json`. Manager released repairs only after every frozen
job settled. Root-cause notes and final implementation:

- Reference/installed panels inferred human confirmation from canonical accepted
  state or membership. Those owners admit machine adoption too. Current Cast/Art
  headings now reuse exact operation/revision/hash provenance; subject membership,
  frozen Cast and installed-source descriptions use neutral binding wording.
  Existing genuine reviewer/judgment labels and unknown/error/manual/read-only
  actions remain under their original owners. Five diagnosed presentation owners
  only; no broader prose, action, schema, API or payload redesign.
- `initial_inventory` short-circuited correctly before Cast/Art existed, then
  dereferenced optional `installation.status` once both existed, yielding500 during
  normal pre-installation stages. Its shared readiness guard now explicitly requires
  a present current installation before material loading, preserving the existing
  InvalidTransition409 and current manual/takeover completion semantics. Running
  handoff retains its stronger stop-first refusal; no UI or endpoint exception bypass.
- Image phase stayed `references` while the first frame was prepared/sent; selection
  changed it only afterward. Text preparation already records active phase. Image
  preparation now commits `first-frames`/`references` with its admitted prepared
  checkpoint inside the existing IMAGE transaction. Failure rolls back phase and
  preparation together; waiting/pause/restart keep the exact job and dispatch state.
  No extra checkpoint, native job, generation, counter or selection permission.

ADR0162 and the current contract capture these semantics; the roadmap and touched
map identify the released slice and mark the old v1 no-crop/adaptation row explicitly
historical. No SQLite layout, credential/auth, dependency/build tooling, provider/
prompt, request/response schema or admission/selection/handoff ownership changed.
The backend readiness and persisted phase behavior changed, so this combined slice
requires a fresh manager full gate; frontend qualification cannot substitute for it.

Scoped source evidence in ignored `.local/native97-repair/`:

- New backend focused12 cases passed29.95s: absent/outdated installation with either
  limit mode; real early GET409 across Source/Cast/Art/Script/storyboard/native bridge
  stages with byte-identical project/run and unchanged dispatch lists; running and
  taken-over incomplete handoff refusals; phase prepared/sent/delivered/waiting/pause/
  restart and injected transaction rollback/no phantom native job.
- Final expanded backend **focused62 cases passed392.86s**, runner414.829s,
  `backend-consumers.log`: full new readiness/phase owners, existing
  `test_autopilot_images.py`, `test_autopilot_image_safety.py`,
  `test_autopilot_authority.py`, `test_autopilot_late_receipts.py`; explicit handoff
  takeover/unassessable authorization, manual-import replacement/fresh handoff,
  complete multiview reference endorsement; both geometry transaction/selection
  restart cases. This supersedes the first12-case evidence for their final inputs.
- Focused presentation30 cases passed in1.018s: exact AI/manual/unreadable/mismatched
  hash/revision headings, neutral membership/current/frozen Cast metadata, real
  reviewer/judgment preservation and no preparation/selection/control writes.
- Quick **1368 units/157 files and both type checks** passed13.586s. Initial test
  harness failures (incorrect API spy name and incomplete typed frozen-Cast fixture)
  were corrected; production assertions or types were not weakened.
- Eight affected browser journeys passed20.232s: whole `autopilot-guidance`,
  `creator-reading-states`, `cast-reference-revision`, `reference-gallery-layout`.
  Existing manual reading/revision/full frozen-reference checks stay intact. The
  amended guidance case asserts local AI labels and unknown first-frame provenance
  before selection, with real retained stage reads and a labelled actor GET fixture,
  zero navigation writes and no actual native dispatch. Separate capture rerun
  retains desktop1440×900/600 character, Art and phase pixels in
  `.local/native97-repair/pixels/`; inspected headings are readable and unclipped.
- Two independent bounded read-only reviews closed with no actionable findings:
  authority reviewer for readiness/phase and persistence reviewer for presentation.
  No delegated edits or checks; prior requested Sol/High and Sol/Medium settings
  were retained, effective host settings unverified.
- Native ownership discovery only:1779 pytest/177files,1368 units/157files,
  316 browser/92specs. New tests registered; no unfiltered test bodies executed.
- Two deterministic builds match seven static files, sorted manifest SHA256
  `0ba396bbac866bd51f6efafadd5be007380d72767f435d730a6ad585e421e121`.
  Installed-wheel smoke passed; wheel SHA256
  `c90efe9ef6a2ad93fefb70c58fd3d4c5e2ab719bc1ba527e7caffd312e17b41a`.
  Both changed Python and all seven static archive members byte-match sources.
  The normal existing large-chunk build notice remains; no optional splitting or
  warning suppression was added. Targeted Ruff and diff checks pass.

Stop at one clean reviewed source checkpoint and restore all source/dependency/
configuration/documentation writes and test holds. Manager owns fresh exact-candidate
full, actual-path recheck, preserving rollout/release/activation and any main merge/
push. Native97 evidence remains bound to97; post-repair qualification and visual
owner acceptance remain pending. Source worker ran no full/equivalent release-gate
union, real generation, nativeQA operation, hosted CI, merge/push or live activation.

### Manager full at 927 and retained-pack Art caption follow-up

The manager's fresh full passed on exact source `927d6d815a70214351ab92ce8bf89f7528f5fd3c`:
**1779 Python cases/177 files, 1368 frontend cases/157 files and 316 unfiltered
browser cases/92 specs**, plus deterministic bundle/parity and installed-wheel
smoke. `VERIFY_SUMMARY` reports1513.238s total and972.198s for Python in
`output/playwright/pre-video-p5/full-927d6d81.log`. This full qualifies927; the
caption-only follow-up below uses the scoped frontend qualification recorded here.

The manager then reloaded the retained native97 pack with runtime927. Its run
remained `awaiting_review` / `material-review`; the controller claim advanced76 to77
on restart and stayed77 through the browser recheck. Policy, checkpoints, frames,
review bundle (`61fe7c1c043480b85e3a81bd43f235e1759865b6dcebb409bb173bda65d7e76e`)
and review fields were unchanged; the server log had zero mutating HTTP requests.
The snapshot showed `AI 已采用美术设定 r1` beside the unconditional preparation
caption `此选择用于新的美术任务，不会修改已确认的角色设定或图片。` The Cast
was AI-adopted and carried no human confirmation. See
`native927-recheck-proof.json` and `native927-reloaded-art-snapshot.txt:119` under
`output/playwright/pre-video-p5/`. Native generation remains bound to97, and human
visual acceptance is still pending.

The bounded repair changes that helper to `此选择用于新的美术任务，不会修改角色设定或图片。`
in `frontend/src/pages/ArtPanel.tsx`. The existing `autopilot-guidance` journey now
checks the AI-adoption context and neutral preparation wording, rejects the old
confirmation phrase, and retains its zero-write / no-run assertions. Its fresh
1440x900 preparation capture is
`.local/native927-caption/pixels/native927-caption-art-preparation-1440x900.png`;
the caption is readable in context with the AI-adopted heading. Generated delivery
changed only `src/plotloom/static/workbench.js`.

The actual diff contains this presentation sentence, its existing browser journey,
the generated bundle and this receipt. Backend/API requests and responses,
persistence, prompts, admission, auth, provider behavior, dependencies, package
metadata and package contracts are unchanged from927. No human-confirmation state
or action was added or altered.

Scoped qualification passed: `verify.py quick` ran all1368 frontend cases across
157 files plus both frontend and E2E type checks; focused Playwright ran the single
`e2e/autopilot-guidance.spec.ts` case and passed. Two deterministic builds produced
the same seven-file static SHA256 manifest (sorted relative path, NUL, per-file
SHA256, newline)
`f3728c7484a1480d6f5b8b311e451faf62ceaaed8ce67350eba8f205f3deb5d2`; the changed
`workbench.js` hash is `d589679ae2ed3b92a0e0dfcdcc31fbea7bd8d5788b70446ad7990d045a526dd5`.
A fresh wheel build and installed-wheel smoke passed (`plotloom-0.1.0-py3-none-any.whl`,
SHA256 `b0054a62c55f07e71c383cd1860a9cf7a597137e75255bd431f488d66025648f`). One
independent bounded read-only review reported no actionable findings. The caption
follow-up did not rerun full or perform native generation; manager owns the final
actual-path recheck and release decision.

## Manager closeout · actual-valued activation at b6

### Final source and native-path qualification

The manager independently reviewed the four-file caption change at
`b6f0525da5c19d572aa64946bad8339fe2f44c7e`. It changes no backend, API/payload,
persistence, authority, prompt/provider, dependency, configuration or packaging
contract. Reuse the exact927 full above and b6's scoped frontend/package gates;
no equivalent full suite was repeated for this sentence.

The retained native97 project `6920b255-080d-4e32-a0c5-83d9c31d489f` was restarted
under b6 in the isolated9951 runtime, then stopped cleanly. The legitimate
controller claim advanced run revision77 to78; it remained `awaiting_review` /
`material-review`, with the same policy,22 checkpoints,4 references,3 frames,
2 routes and review bundle
`61fe7c1c043480b85e3a81bd43f235e1759865b6dcebb409bb173bda65d7e76e`.
The native deliveries remain evidence at97 (8 text and7 ImageGen jobs), not new
generation or exact-b6 native dispatch. All17 review text fields,3 judgments and
4 endorsement checkboxes remained blank; human handoff was disabled. No human
facts or video operations were supplied. The manager inspected the final
[Art caption capture](2026-10-12-pre-video-autopilot/native-b6-art-1440x900.png)
beside its AI-adopted heading and found no remaining caption defect.

### Actual-valued preservation and cutback

After verifying native idle, the manager stopped both the Docker workbench and
the Mac bridge LaunchAgent. Raw inventory found8 project folders:4 exact
immediate-prior layouts eligible and idle, and4 historically unsupported layouts.
The actual application registry had57 jobs, each matched to exactly one retained
completed receipt with matching task/job identity; no unknown or inflight work.
The four older folders were not migrated, reset or newly made available.

A private complete capture retained1379 entries,12 committed SQLite databases,
all8 folders and hidden snapshots, application/settings/dispatch state, old
source731 and image, and private deployment/credential controls. Capture used
existing noncreating project locks followed by the registry idle guard. Two
bounded independent helper reviews closed; the first caught a possible lock-file
creation before inventory, removed before capture. Guarded receipt identity,
captured-root confinement and original control hashes/modes were also checked.

The copy rehearsal ran in network-disabled Docker, with only copied data at the
original absolute paths, read-only source and no bridge/credentials/provider.
The first container launches failed before execution because a nested data
mountpoint was below read-only source. Mounting only the required `src/` subtree
resolved that harness arrangement; no product/schema checks were bypassed.
Loaded module hashes matched the intended current and old source exports.

Executed proof:

- [Upgrade rehearsal](2026-10-12-pre-video-autopilot/valued-rehearsal-b6.json):
  injected post-DDL failure rolled back; all4 upgrades passed; current-runtime
  readback, old-column row equality, empty new tables and idempotent second
  upgrade passed. Application/unsupported DBs and all non-schema files were unchanged.
- [Old-runtime cutback](2026-10-12-pre-video-autopilot/valued-cutback-731.json):
  source731/old image directly reopened all4 supported identities read-only;
  the same4 unsupported folders refused; all12 committed DB hashes were unchanged.
- [Actual live upgrade](2026-10-12-pre-video-autopilot/valued-upgrade-b6.json):
  exact same pre-upgrade logical DB hash
  `060000407bf24d711a88b85de03ee2e6d34288dc1fe9357b91646e41c3db7405`,
  explicit four-project allowlist, both service owners still stopped, successful
  rehearsal and cutback receipts verified. All old rows, operational states,
  retained payloads, native records and unsupported folders preserved.

The complete private cutback directory was moved intact from temporary staging
to `~/Library/Application Support/Plotloom/recovery/pre-video-autopilot-b6f0525d-20261012/`
(mode0700), with controls0600. It includes the immutable raw/committed backup,
old source, copy proofs and operator tools/procedure. It is intentionally not
committed. Old image `plotloom-cutback:731cfdbf` is retained. Cutback uses a fresh
complete working copy and the old source/image, never SQL downgrades or deletion
of failed state. No live cutback was necessary.

### Activated runtime and boundaries

The manager fast-forwarded clean main731 to b6 and used the established
`uv run --locked --no-sync python services/creator_workbench/manage.py start`.
It rebuilt/recreated the workbench, restored the bridge and passed health checks.
Activated image is
`sha256:bf13cf64601f0ab26905d099f2c3ee3ed5aeee7e2edf4566739fe99fb38ffe2c`.
Docker image build/dependency/configuration inputs are unchanged from the prior image;
the runtime consumes the new mounted source and qualified assets.

[Post-activation proof](2026-10-12-pre-video-autopilot/activation-b6.json) checks
both `http://127.0.0.1:8841` and `https://plotloom.tail6040ad.ts.net`: healthy,
controller blocker null,4 preserved project summaries with unchanged open/closed
states, and exact SHA256 match for all7 static files. All old project/application
rows and retained payloads are unchanged. New run/human-fact tables are empty;
the native count remains57 and no dispatch is active. The sole new non-schema
runtime file is the empty application `.autopilot-controller.lock`. Deployment
configuration, bridge definition, token and H3 configuration hashes are unchanged.
The manager inspected the [live1440x900 homepage](2026-10-12-pre-video-autopilot/activation-home-1440x900.png);
the browser had0 console warnings/errors. The owner's browser was not reloaded.
An attended independent read-only closeout audit compared these claims with the
retained proofs and found no concrete issue before documentation publication.

This closes implementation, local qualification, native technical demonstration,
walkthrough repairs and preserving activation. It does not claim hosted CI,
owner visual acceptance, voice casting, video generation or creative-quality
approval. Fresh saved Brief-only projects can start `一键准备视频素材`; existing
manual stories remain manual. Native97 stays an isolated review candidate. The
separate85-percent Python-performance roadmap edit remains unstaged and outside
this release; performance implementation has not started.

# Owner-approved UX correction follow-up (implementation in isolated worktree)

Approved outcomes: a post-save visible choice with zero implicit dispatch;
Brief-authoritative visual direction for autopilot only; and compact, truthful
run status that stays discoverable during navigation. Root causes and
preservation boundary are recorded in the [roadmap](../roadmap/2026-10-12-pre-video-autopilot.md#owner-approved-ux-correction-follow-up--2026-10-12).

Completed isolated evidence (2026-10-13):

- `story-authoring` module contract: ownership preflight passed; 251 pytest and
  268 Vitest cases passed; frontend typecheck passed. The broader unfiltered
  frontend suite passed 1,374 tests, and both frontend and E2E typechecks
  passed.
- Focused Playwright runs passed 18 workflow/autopilot cases and two checked
  static-bundle cases. Visual inspection covered 390x844 collapsed/expanded,
  1280x460 compact, and 1700x900 expanded views. The global graph stylesheet
  had imposed `min-width:1280px` on every route; removing that shell-wide rule
  fixed the mobile Brief overflow. Mobile toolbar actions now scroll in one
  row, while the workflow guide stays compact and exposes its next-step detail
  inside the expanded guide.
- Two deterministic builds produced matching sorted SHA-256 manifests, and
  the generated bundle is included in this candidate. `git diff --check`
  passed. The independent read-only review's P2 finding on stale selected
  image counts after cancel/takeover was fixed and re-reviewed with no further
  findings.
- After that review, focused verification passed four geometry cases (retained
  v2/current v3 policy assertion, current v3 derivative creation, and v3
  geometry through review), 25 autopilot Vitest cases and all 18 relevant
  browser cases. The unfiltered frontend suite was rerun: 1,374 tests passed;
  frontend and E2E typechecks passed. Two fresh deterministic builds again
  matched; checked-static smoke passed both cases. The isolated wheel build and
  installed-wheel smoke also passed.
- The scoped Python run emitted one non-failing Starlette `httpx` deprecation
  warning. The Story-authoring module run took 20 minutes; this is module-scoped
  evidence, not the full release gate. Hosted CI, full qualification, product
  acceptance and activation remain manager-owned and are not claimed.

Preservation incident: while this isolated work was in progress, the separate
Python-speedup worker's `e9e67847` became `main` and `origin/main`. The
production checkout was restored to detached `c771cdd6`; its HEAD and files
were left untouched. This candidate remained based on the verified
`c771cdd67eb8fd0925cdfe772c46ed85eeb51657`. The owner run resumed from r86 to
r87 without resending its job; no Python-speedup files or changes were brought
into this candidate.

### Frozen Brief instruction repair (2026-10-13)

A read-only review of the first saved-Brief receiving instructions found two
contract defects: Cast was told to emit a Markdown file outside the exact
candidate/report/completion inventory accepted by `CreativeHandoffExchange`,
and a shared ownership sentence prohibited Cast from authoring its assigned
candidate. The root cause was the instruction layer combining both stages'
ownership and render outputs; downstream exchange validation correctly
rejected the extra artifact. The v2 receiving contract now emits only the
supported HTML report, names Cast and Art ownership separately, and explicitly
keeps Art's accepted Cast input read-only. It still overrides only preset
selection/defaults, preset bundles and preset-specific commands; pinned skill
files and unrelated validator gates are unchanged.

Focused validation passed 14 cases covering frozen commands, stage ownership,
real upstream Cast/Art candidates, execution of the generated commands, exact
three-file exchange inventory and `read_delivery` acceptance. Ruff checks for
the changed Python modules passed. The isolated wheel build and installed-wheel
smoke passed. Frontend, browser, static assets and full qualification were not
rerun because this repair changes only Python instruction generation, tests and
the ADR; their prior evidence above remains scoped to the unchanged inputs.
`git diff --check` passed. An independent read-only review of this repair delta
found no issues. The scoped repair delta is committed on the isolated candidate; see the task report for its revision.

Retained visual evidence from the prior UX qualification is available at
`/tmp/plotloom-final-visual-review/autopilot-review-long-bloc-f659e--narrow-and-short-viewports/long-blocker-1440x900.png`,
`/tmp/plotloom-final-visual-review/autopilot-review-long-bloc-f659e--narrow-and-short-viewports/long-blocker-390x600.png`,
and `frontend/test-results/recommended-workflow-guide-a5382-draft-navigation-protection/`
(including the 1280x460, 1280x768, 1700x900 and 390x844 collapsed/expanded
captures). Those artifacts are review evidence, not product-owner acceptance.

### Creator Brief first-save navigation assertion repair (2026-10-13)

The three failures in `creator-ui-polish.spec.ts` came from an obsolete test
assumption: first-save now intentionally keeps the user on the saved Brief and
presents automatic/manual choices, while the test still expected immediate
navigation to Source. The product flow is correct; this is a stale navigation
assertion, not a product regression. The test retains the direct Save click and
expanded diagnostics, checks the saved Brief and both choices at 1440, 1920 and
1280 px, verifies no autopilot, legacy pipeline, rebuild or specialist-send
POST occurs, explicitly chooses `继续手动创作`, checks dispatch remains absent,
and then runs all existing Source accessibility/layout assertions.

Focused `verify.py focused --playwright e2e/creator-ui-polish.spec.ts` passed all
three width cases and its E2E typecheck. A standalone
`npm --prefix frontend run typecheck:e2e` also passed. `git diff --check` passed.
This test-only delta leaves generated frontend assets unchanged. Manager-owned
unfiltered browser requalification remains pending. The first independent review
found that two dispatch endpoint families were missing from the guard. The
listener now includes generic specialist-task and image-job sends; the three
focused cases and E2E typecheck passed again. Independent re-review found no further issues.

### Manager combined qualification and actual-path follow-up · 2026-10-13

The manager integrated the reviewed UX and receiving-contract candidate
`bab49f54` with the already qualified Python speedup `e9e67847`, corrected
documentation `31c6a209`, and the separately approved queued CLI-worker plan.
The only merge conflict was roadmap-index text; both entries were retained.
This produced clean `7954069ac3f375299d039b2ae846c38cc5e9dc27`.
Manual specialist skill/adapter bytes and the pinned submodule remained unchanged.

The initial full invocation failed in preflight because this new checkout lacked
the archived prompt-reader's locked `jsdom` prerequisite. No product tests ran.
After installing that existing locked dependency tree, the full invocation at
795 passed lock/tools/import checks, archived reader, 1,374 frontend tests,
frontend typecheck, 1,793 Python cases, deterministic bundle/parity and complete
browser allocation. Python used two workers and **case-count fallback** because
the native inventory changed; its step took 653.935 seconds. This is not a
duration-packing measurement or a matched speedup benchmark.

The browser step passed 314 of 317 cases and failed only the three obsolete
first-save navigation expectations documented above. Full returned exit1 at
1,171.282 seconds; that failed run is retained, not relabelled a pass. Reviewed
test-only repair `2a7cfe4a` was integrated as
`477e7df9b97687cadaa78fa0e5e17cc4864c24e7`, with product, dependency, config and
generated asset inputs unchanged. The manager reused those passed inputs and
ran the exact failed/downstream full steps: unfiltered browser allocation,
**all317 browser cases**, wheel build and fresh installed-wheel smoke passed.
That continuation returned exit0 in 505.989 seconds. This closes the combined
local gate through documented evidence reuse; it is not a new full invocation
with a zero exit at477. Both frontend and E2E type contracts are qualified.

Logs remain under private `/tmp/plotloom-ux-release-gates.cILc2m/`:
`full-7954069a.log`, `full-7954069a-retry.log` and
`browser-and-package-477e7df9.log`. The locked frontend installation reported one
existing high-severity dependency advisory; no dependency upgrade or security
qualification is claimed by this UX work.

#### Disposable browser walkthrough

A real isolated project-folder runtime created and saved a fresh Brief. Save
stayed on Brief and offered automatic/manual choices without generation. The
expanded launch showed the exact 2D animation, watercolor, low-saturation and
free-text direction, without an independent preset. Retained captures are in
the receipt's [UX evidence folder](2026-10-12-pre-video-autopilot/ux-release/).

The progress portion used controlled browser-only responses, not generation.
The first interceptor incorrectly omitted `/start`; that request reached only
the unconfigured disposable backend and received409, producing no run or send.
An exact-route correction returned the simulated201. One Start was intercepted,
zero control/send requests occurred, and the transient starting/duplicate-submit
guard was observed. After route navigation and long scroll, the progress strip
remained visible at1440x900,390x844 and390x600 with no page-level horizontal
overflow. The mobile toolbar intentionally scrolls horizontally. Reduced-motion
emulation disabled spinner animation. The manager inspected the saved-choice,
Brief-style and scrolled desktop/mobile captures. The owned browser/runtime
were stopped; no owner browser or normal service was touched.

#### Real native receiving-contract proof

At frozen477, a separate installation and newly created disposable identities
ran the real registry → shim → authenticated host bridge → native queue path.
The production controller was stepped explicitly without an application
lifespan/background worker and stopped immediately after Art adoption. Exactly
four unique native text jobs—outline, branches, Cast and Art—were AI-adopted.
The canary's owned native `turn_context` confirms GPT-6.1 Sol / Medium; original
model-self-reported manifest fields remain untouched. No Plotloom image/video
dispatch or human approval was made, and the QA run remains paused at r20.

Both Cast and Art retained the exact author direction and emitted English
2D-watercolor/low-saturation machine prompts with the saved-Brief markers. They
used the v2 override and exact three-file delivery inventory; immutable request,
output/report/manifest hashes, pins and all four completed native receipts were
checked. This demonstrates actual instruction following and technical adoption,
not image fidelity, identity, rights, voice casting or creative acceptance.

After successful Art adoption, the first evidence collector wrongly called the
current waiting-delivery branch getter. Its refusal was correct. The service
had already paused, and unconditional cleanup released only the private runtime.
Read-only recovery used the retained terminal-request owner and verified package
paths, checked unchanged private database state and completed receipts, and
dispatched nothing. No job was repeated or receipt rewritten.

Before and after this proof, the actual owner run remained r229 awaiting_review,
with the same complete review response/bundle hash
`d12d5388e23bcfd3fad83360fe834292f5e7e6832fad4de5a8721db7af2cd62a`.
The earlier copied valued-project proof at795 also preserved all437 payload
files and logical database rows, returning identical28 frames/5 references.
Original production source stayed detachedc771 and clean throughout.

Final all-project idle admission, durable recovery/cutback capture, safe-idle
activation and post-activation source/static/state readback remain manager-owned
pending gates. No hosted CI was dispatched. The CLI pool remains queued behind
this technical closeout; owner visual/creative acceptance is not fabricated.

#### Downstream saved-Brief contract finding · activation held

Before activation, manager source tracing and an independent read-only review
found that F5A Storyboard still instructs and directly invokes the unchanged
pinned preset validator. At477, the receiving request has no saved-Brief style
override. Both delivery admission and acceptance invoke the pinned entrypoint.
A read-only call to its real `gateReport` with the upstream example cloned in
memory rejects `style=saved-brief`; omitting style selects `realistic` and its
`cinematic film still` phrase. No file, project, receipt or dispatch was changed
by that diagnostic.

This is an actual receiving/admission mismatch, not an aesthetic quality claim:
the forced frame direction is copied into canonical composition and the frozen
first-frame image request. The four-stage native proof above intentionally ended
after Art and therefore does not close this downstream path. Script has no
separate preset gate in the inspected path, and image preparation carries the
Brief direction, but neither resolves a conflicting Storyboard frame phrase.

The bounded correction belongs at Plotloom's F5A saved-Brief receiving contract:
freeze the inherited authoritative direction and adapter identity, use matching
validate/render instructions and server admission, preserve non-style upstream
gates and the manual preset path, and test downstream composition/image inputs.
Amend ADR0163 and qualify the changed contracts before activation. The same UX
source owner receives this repair; no competing writer or CLI pool starts.
Production remains clean detachedc771; the valued r229 run and its review bundle
remain unchanged. Activation/recovery execution and later-stage native proof are
still pending.

### F5A saved-Brief receiving/admission checkpoint (2026-10-13)

The released source owner fast-forwarded the clean `2a7cfe4a` isolated checkout
onto `362eab5f`, preserving its history and the existing Relay route. The F5A
root cause above is addressed in a new Plotloom-owned receiving contract and
neutral adapter. Code freezes the exact accepted Art contract/direction and
adapter/upstream identities into the F5A binding and immutable request; the
model authors English frames/H3 descriptions with neutral authority markers.
The same generated command pair and server admission call the new adapter.
All unrelated pinned upstream gates remain active. Its markers establish
membership, while semantic fidelity remains human-reviewed. Manual preset
requests and historical bindings keep their prior path and serialized absence
of the new field. No database migration or retained evidence rewrite occurs.

An installation regression exposed a currentness consumer mismatch: the bridge
had compared the new binding against a base F4 context with no F5A field. F5A
now owns current-context resolution in the frozen binding's mode, and both
currentness and the bridge use it. The required diagnostic field is assigned
an explicit owner and a localized frontend label; its optional binding type is
mirrored in TypeScript. Generated assets were refreshed for this label change.

Executed scoped evidence:

- Focused F5A/contract, timing, typed diagnostics and bridge checks: 55 pytest
  cases passed. These include real upstream example validate/render command
  execution and exact candidate/report/completion exchange inventory for a
  non-preset Chinese direction and empty direction; server admission/acceptance;
  ordinary reopen, late/superseded currentness, historical binding preservation;
  and an actual disposable installation-to-image-request snapshot trace retaining
  the supplied frame exactly, with no injected preset phrase.
- Focused existing Cast/Art/F4 and Brief-style checks: 27 pytest cases passed.
  The existing minimal Cast fixture was completed only for its new Brief-mode
  use; no upstream gate was relaxed. The real upstream storyboard example is
  paired with its exact E01 script scope, rather than claiming coverage of the
  six-episode script example. One initial disposable completion template still
  contained its placeholder code revision; fixture provenance was corrected.
- Focused review UI tests: 26 Vitest cases passed. The unfiltered frontend
  suite passed 1,375 cases across 157 files, and both typechecks passed. Two
  deterministic builds had identical sorted SHA-256 trees. Their manifests are
  `/tmp/plotloom-f5-brief-static-first.sha256` and
  `/tmp/plotloom-f5-brief-static-second.sha256`.
- The new diagnostic browser case passed at 1440x900 and 390x600; both
  checked-static bundle cases passed. The browser test checks default collapsed
  technical detail, then preserves its expanded state while resizing; same-URL
  navigation had initially retained the disclosure, invalidating the test's
  reset assumption. Pixel inspection confirmed readable label/detail and no
  horizontal overflow. Retained captures are
  [desktop](2026-10-12-pre-video-autopilot/ux-release/f5-brief-diagnostic-1440x900.png)
  and [narrow](2026-10-12-pre-video-autopilot/ux-release/f5-brief-diagnostic-390x600.png).
- The locked-dependency check, native module ownership preflight, Ruff checks
  for the new Python modules/fixtures and affected owner imports, final wheel
  build and installed-wheel smoke passed. The new tests are registered to the
  existing project-lifecycle owner. The wheel at
  `/tmp/plotloom-f5-brief-final-wheel-20261013` proves packaging/runtime startup;
  it does not exercise F5A specialist execution, which uses repository-local
  adapters and pinned files as do the existing specialist paths.
- A stable independent read-only review (requested GPT-6.1 Sol/Medium;
  effective host setting unverified) found no actionable issues. It ran no
  checks independently. The Python checks retained the existing non-failing
  Starlette `httpx` deprecation warning; builds retained the non-failing chunk
  size advisory.

This is a committed implementation checkpoint once its revision is reported
through Relay. Worker source/dependency/configuration/test bodies then remain
held. The manager owns fresh exact-candidate full qualification, a new distinct
actual-path native proof, preservation and activation. No worker native, live,
CI, main integration, push, CLI-pool work or owner-story mutation was performed.
The original valued r229 run, detached c771 source and private477 QA were not
opened, rebound, rewritten or resumed by this worker.

### Hosted browser shard allocation repair (2026-10-13)

The full run on base `15af8f6b` stopped at the Python gate because
`tests/test_ci_browser_contract.py` discovered the new
`storyboard-brief-diagnostic.spec.ts` file but the hosted whole-file manifest
did not assign it. The spec was already registered to its native module owner.
The correction adds that spec once to shard 3; no existing shard assignment or
coverage assertion changed.

Scoped verification on the resulting candidate:

- `uv run --locked --no-sync python scripts/verify.py focused --pytest tests/test_ci_browser_contract.py` — 5 passed.
- With ambient selectors cleared and `BROWSER_GREP='.*'`,
  `node scripts/check_browser_shard_manifest.mjs` — 93 specs and 318 selected
  cases across shards 84/72/72/90; zero overlap or missing cases, with the
  full browser selection preserved. This is collection/allocation evidence;
  browser test bodies were not run.

Only the shard manifest and this receipt changed. The full release run remains
incomplete at its earlier failure; no native, hosted CI, activation, or broader
qualification was performed in this repair.

### Native ImageGen identity binding repair checkpoint (2026-10-13)

This is a source-only repair in the isolated worktree
`/Users/wjmao/.codex/worktrees/8ef5/plotloom`, based on
`9b914daa591288ef39cc1f67af6e1a5470f8796d` (parent
`15af8f6ba224d22ce4c6d97dd91c1026635cc043`). The manager's offline native proof
recorded ImageGen output ID `exec-101f61ef-ab1c-4dcf-a6bc-702e4bc8a81e` in
`toolEvidence.taskId`, while the frozen native Codex task UUID was
`01a1357a-249d-7e73-81fa-5e337d7bdfe5`. Existing receiving checks correctly
require the dispatched native UUID; the package, skill and manifest had not
carried that identity separately from the ImageGen execution ID.

ADR 0074 now defines the transport-only binding and its two explicit modes:
configured dispatch carries its exact UUID, and manual copy binds to the
current task. New packages use version 6, preflight `p1.5-pin.v2`, execution
contract `codex_specialist.v3`, and schema-v3 completion manifests with separate
`nativeTaskId` and `imageGenExecutionId`. The preflight validates `CODEX_THREAD_ID`
and writes the native UUID to the executor pin before generation. The new
publisher validates binding, pin/provenance, distinct IDs, output inventory and
hashes before publishing `completion.json` once. Existing schema-v1/v2 manifests
remain readable; receivers continue to require an exact native-task match.

Focused implementation checks on this candidate:

- `uv run --locked --no-sync python scripts/verify.py focused` with explicit
  selectors for `test_image_job_exchange_contracts.py`,
  `test_publish_image_completion.py`, `test_pin_image_specialist.py`,
  `test_specialist_settings.py`, `test_image_terminal_settlement.py`,
  `test_project_storage_image_identity_contracts.py`, and
  `test_project_storage_image_delivery_contracts.py`: **95 passed**, one
  existing Starlette/httpx deprecation warning.
- `python -m compileall` for the changed Plotloom modules, pin/publisher scripts
  and focused tests passed. `git diff --check` passed.
- Targeted Ruff passed for the pin script, new publisher, package projection and
  publisher tests. A broader Ruff invocation over all touched existing modules
  remains unclean with import-order and related style findings; no broad
  autoformat was applied.
- Native ownership discovery passed with 1,825 pytest cases, 1,375 Vitest cases
  and 318 Playwright cases inventoried. `shared-provider-dispatch --depth
  contract --show` confirmed the registered owner union; no module union or
  broader suite was executed.

The first focused run exposed two integration gaps and closed them: package
creation did not forward the binding to its post-write package verification,
and terminal-proof package verification omitted the bound dispatch identity.
The generated pin/publish commands were also corrected to point at the Plotloom
checkout rather than the exchange directory. Regression cases cover these
paths, configured/manual bindings, missing or mismatched IDs, and refusal before
the final marker.

An independent read-only review found a P2 race where the publisher could remove
`completion-draft.json` after directory listing but before the reader stats it.
The delivery inventory now tolerates disappearance only for that known staging
file; other missing entries and symlinks remain rejected, and the final expected
inventory comparison stays strict. A deterministic regression removes the
listed draft before `stat` and confirms the valid published delivery is accepted.
`verify.py focused --pytest tests/test_image_job_exchange_contracts.py` passed
all 14 tests after the repair; focused Ruff, `git diff --check`, and compileall
also passed. The reviewer rechecked the final race fix with no further findings
in a static review. The broader implementation suite results above remain the
separate focused evidence for the other touched contracts.

The scoped source commit is recorded in the isolated worktree for manager review.
No native proof, ImageGen generation, resend/rebind,
QA/live project/package/pin/output or manager-owned receipt mutation, service or
provider operation, full gate, CI, activation, merge or push occurred in this
source checkpoint. The manager retains all such gates and final product/release
acceptance.

### Full-gate fixture and retained-coverage repair (2026-10-13)

The manager's full local gate on base `2ec62c70fdd84e53e4cd9825e4722c4ea392bda7`
exited 1 after 729.606 seconds: 1,828 passed and 10 failed. Its captured log is
`/tmp/plotloom-ux-release-gates.cILc2m/full-2ec62c70.log` (SHA-256
`f1807ae29ac5c019ca64656dea973aa05601e05c1fba41833da0f39cbc50d616`). Frontend
tests and type checks passed in that run; it did not reach browser, deterministic
build, or wheel checks. I reproduced the ten reported failures with focused
selectors on the unchanged base before changing fixtures or the inventory.

The failures came from stale test contracts, not a demonstrated product defect.
The Art delivery fixture still emitted a schema-v2 `taskId` manifest and an old
pin even though packages now freeze package-v6 native-task binding and schema-v3
identity. The project-folder dispatch safety double did not implement the
current typed binding method, and its terminal manifest double lacked the
canonical payload method. The retained coverage catalog also had stale source
hashes/package-version assertions and listed only a geometry rejection check,
without a positive exact-geometry acceptance case. These fixtures and
assertions are now aligned with the current contract; the rejection baseline
remains recorded and a separate acceptance test checks frozen source identity,
output geometry, accepted derivative role, and unchanged selected source.
Shared project-folder image-test setup moved to
`tests/project_folder_image_delivery_fixtures.py`, leaving the original test file
at 447 lines.

Scoped verification on the repaired candidate:

- `uv run --locked --no-sync python scripts/verify.py focused` with explicit
  selectors for the Art fixture consumers, project-folder dispatch safety,
  retained coverage inventory, image identity/delivery/workflow and exact
  keyframe acceptance, image exchange, specialist settings, and terminal
  settlement passed **97 tests**, with one existing Starlette/httpx deprecation
  warning.
- `uv run --locked --no-sync python scripts/verify.py module --module
  media-lifecycle --depth contract --show` confirmed the new acceptance test is
  in the owner union and that the module declares no additional required gates;
  this was discovery only, not a module test run. The extracted shared fixture
  helper is registered under the same module's support dependencies. After
  adding that registry entry, `verify.py focused --pytest
  tests/test_verification_module_ownership.py` passed all 7 tests and module
  planning confirmed both paths.
- Targeted Ruff `F,I` checks on the five changed Python test/fixture files,
  compileall for all five changed Python files, and `git diff --check` passed.
  The retained inventory selector passed as part of the focused run.
- Independent read-only review found no correctness or scope findings. It noted
  that the extracted helper was missing from `support_dependencies`; that
  registry entry was added and checked after review. Effective model/effort
  settings were unverified.

No full-suite rerun, browser, build, wheel, CI, native dispatch, live/QA state,
provider action, activation, merge, or push was performed for this repair. The
failed full gate and its downstream release qualification remain with the
manager; this receipt records only the bounded fixture/coverage repair evidence.

### Browser delivery fixture identity repair (2026-10-13)

The manager's qualification of source commit `d721bc682e8287163c11ac766b00111b71c52504`
is preserved as failed: log
`/tmp/plotloom-d721-qualification.pEznDx/qualification.log` (SHA-256
`1259331147372bdb7a786684a18b901ad97dadd60b3702c58a2978ee959eb278`), exit 1.
It reported 104 affected Python/ownership checks passed, deterministic build and
checked parity passed, the unfiltered guard found 93 specs/318 cases, and E2E
typecheck passed. The unfiltered browser run had **308 passed and 10 failed** in
475.852 seconds. Wheel/package build-smoke was not reached. The manager's
copied valued-readback evidence at
`/tmp/plotloom-d721-qualification.pEznDx/copied-valued-readback.json` passed
with 437 files, 28 frames, 5 references, revision 229, bundle and database
readback; the original `c771` project remained unchanged. This is manager-owned
evidence, not a reproduction or live operation in this source repair.

The ten browser failures shared a stale test-writer contract. Current copied
packages are v6 and freeze `p1.5-pin.v2` / `codex_specialist.v3` / specialist
skill v4. Several Art, Cast and image-job writers still emitted old executor
pins, skill v3 and schema-v2 `toolEvidence.taskId`; a package-version assertion
also expected v5. The receiver correctly rejected those fixtures before the
journey assertions. This affected Art F3B reference delivery, Cast revision,
three Characters delivery-observation cases, three Cast reference-study cases,
the main image-jobs journey, and expanded reference-gallery directions.

The shared test-only writer in `frontend/e2e/fixtures/image-delivery.ts` now
reads each frozen package request, checks package version, request identity,
preflight and binding, uses the configured task UUID or a deterministic
current-task fixture UUID, and writes a matching executor pin plus a schema-v3
manifest with a distinct ImageGen execution ID. Retained image bytes and
limitations are explicitly identified as offline fixtures with no ImageGen
call. Art and Cast fixtures pass the exact returned package path; the duplicate
Cast-studies writer now uses the shared Cast fixture. The image-job fixture uses
the new writer for package v6 and keeps its pre-v6 offline projection intact.
The package-version assertion now expects v6. Existing partial, invalid,
cancellation, restart, reference-use and no-generation assertions were retained.
The shared helper and its consumers are registered in native ownership.

Scoped verification on the repaired candidate:

- `npm --prefix frontend run typecheck:e2e` passed; the focused Playwright runner
  also performed this check before its test bodies.
- `uv run --locked --no-sync python scripts/verify.py focused --playwright`
  with selectors `e2e/art-review.spec.ts`,
  `e2e/cast-reference-revision.spec.ts`,
  `e2e/cast-reference-delivery-observation.spec.ts`,
  `e2e/cast-reference-studies.spec.ts`, `e2e/image-jobs.spec.ts`, and
  `e2e/reference-gallery-layout.spec.ts` passed **26 tests** in 65.616 seconds.
- `BROWSER_GREP='.*' node frontend/scripts/check_browser_shard_manifest.mjs`
  verified 93 specs and 318 cases across shards 84/72/72/90, with zero overlap
  or missing cases.
- Focused module-ownership and retained-coverage inventory selectors passed
  **8 tests**. Module browser planning for `media-lifecycle` and
  `creative-production` included all six specs and the new shared helper;
  planning did not run extra browser bodies. `git diff --check` passed.
- Independent read-only review at requested GPT-6 Luna / Max found no
  actionable issue. The review checked source and diff only; it ran no tests or
  builds, inspected no UI/live/QA state, and could not verify effective
  host settings.

No product admission code, pins, skills, dependency, provider, live/QA artifact,
or prior run state was changed. No full or equivalent broad qualification,
deterministic build, wheel/package smoke, native operation, activation, merge or
push was performed. The manager owns all subsequent release qualification and
native/preservation work.

### Legacy image receipt reconciliation follow-up (2026-10-13)

Manager review of the source checkpoint found that autopilot's late-receipt
ingestion read `nativeTaskId` unconditionally. Retained schema-v1/v2 manifests
carry the native Codex identity in `taskId`, so a valid schema-v2 receipt with
the historical `p1.5-pin.v1` / `codex_specialist.v2` contract was rejected before
ingestion even though the persistence checkpoint validator already understood
both schemas.

`ImageDeliveryManifest.native_task_identity` now resolves only the identity field
owned by the manifest schema: the typed UUID for schema v3 and legacy `taskId`
for schemas v1/v2. Ingestion and persisted checkpoint validation share this
property, then continue to compare the result exactly with the frozen task UUID.
There is no ImageGen execution-ID fallback.

Focused regression coverage creates schema-v2 late receipts under the historical
pin and execution contract, then reconciles them after both cancellation and
takeover, with and without controller restart. It verifies unchanged package and
delivery bytes, frozen policy and job/request identities, an `inapplicable`
retained delivery with no candidate rows or adoption, successful exact dispatch
reservation settlement, and persisted checkpoint validation. Wrong UUID and
`exec-*` legacy task IDs remain rejected with their reservations held.

`uv run --locked --no-sync python scripts/verify.py focused` with selectors for
`test_autopilot_late_receipts.py`, `test_autopilot_image_safety.py`, and
`test_image_job_exchange_contracts.py` passed **41 tests**, with one existing
Starlette/httpx deprecation warning. Focused F-rule Ruff, compileall for the
changed modules and tests, and `git diff --check` passed. The first narrow test
attempt found a missing fixture import; after correcting it, the complete
selected set passed. A bounded independent read-only review, requested as
GPT-6.1 Sol / Medium, found no actionable issues. The reviewer could not verify
host-effective model or effort settings. Restart coverage recreates the
autopilot service while retaining the test registry; it does not exercise a
separate process or fresh registry restart.

### Unnamed creator confirmation · 2026-10-13

Owner-approved implementation revision
`65af67acf4cbc550294df8be0ad9f6577f2c5795`, parent
`4d216ec8a7be59e593f2f8b0ccf0c2e7c30bbe6d`, is a bounded source checkpoint.
The checks below exercised the source tree committed at this revision; no
executable input changed after the passing checks. This receipt closeout changes
documentation only. Independent read-only review requested GPT-6.1 Sol / Medium
and found no actionable in-scope finding; effective host settings were unverified.
The reviewer inspected source/diff, not UI/live state, and executed no checks.
The manager independently reviewed exact `65af67acf4cbc550294df8be0ad9f6577f2c5795`
and closed with no actionable findings, including unchanged NOT NULL SQL layout,
retained-v1 hashes, truthful attribution and unchanged manual/video guards.

Root cause: the final review form and `HumanHandoffRequest` required a typed name
and whole-pack prose, while shared approval/SamePerson writers required a name.
A supplied name is not authentication (ADR0162); those fields added paperwork
beyond the exact material choices and actual frame/character observations.
The owner approved removing the name and making the overall comment optional.
ADR0162, the accepted contract and approved roadmap step were amended before
implementation; stable ordinary-Chinese creator guidance is captured there.

Current requests have no reviewer field. Blank/omitted comments are absent;
nonblank comments retain their exact authored bytes. New `pre-video.handoff.v2`
receipts record explicit `unnamed_creator` attribution and exact material choices.
Shared writers admit the typed attribution only under HANDOFF authority and store
no name as an empty reviewer string in the unchanged SQL layout. Readbacks label
the attribution explicitly; ordinary-open/recovery rejects unnamed facts without
validated v2 receipt links. Manual named-review requests retain their requirements.
Retained v1 receipts use a separate read-only parser, preserving original bytes
and hashes. A fresh confirmation reuses a genuine existing approval without
changing its name/note. No actor or positive comment is invented.

The UI removes the name input, labels the comment `备注（可选）`, uses ordinary
reference-confirmation wording with accessible subject names and full image sets,
and offers `查看生成信息`. The footer explains saved choices and the later separate
workspace action for manual video work. Required individual decisions, uncertainty
hold/authorize, read-only behavior, currentness/CAS, retry/draft retention and
machine/video denial remain. Raw generator limitations and evidence are unchanged.

Executed scoped evidence:

- `verify.py focused` first checked handoff and SamePerson contracts: **27 Python
  tests passed**. The initial new UI test failed because it assumed Field's control
  was nested inside its label; using the associated control corrected the harness.
- Initial new confirmation fixtures had **9 passed / 3 failed**: a fabricated
  controller claim was correctly refused, and lifecycle writes correctly caused
  takeover during synthetic historical setup. The fixtures were corrected;
  product admission was not weakened. The follow-up focused new-confirmation and
  five valid machine-scope selectors passed **18 Python / 27 Vitest tests**.
- Final `uv run --locked --no-sync python scripts/verify.py module --module
  story-authoring --depth contract` passed **279 Python / 269 Vitest tests**,
  frontend typecheck and complete native ownership preflight. This includes no-name/
  no-comment API handoff, exact optional text, manual-name refusals, failed/held/
  missing/stale decisions, rollback, current and synthetic retained-v1 recovery,
  and preservation of an existing named approval on fresh recovered confirmation.
- Focused shared-consumer selectors `test_project_storage_image_identity_contracts`,
  `test_project_storage_current_schema`, `test_autopilot_schema_upgrade`,
  `test_autopilot_recovery`, `test_same_person_review_contract`,
  `test_verification_module_ownership`, `test_retained_runtime_coverage_inventory`
  passed **95 Python tests**. Vitest `human-review-attribution`,
  `same-person-presentation`, `storyboard-workflow-observation` passed **16 tests**.
- Both frontend type checks passed. Focused Playwright `e2e/autopilot-review.spec.ts`
  passed **14 cases**; `e2e/shipped-static.spec.ts` passed **2 cases**. A separate
  one-case replay retained desktop captures, without changing source or inventory.
- Native discovery retained **1,855 Python cases / 182 files**, **1,377 Vitest
  cases / 158 files**, and **318 Playwright cases / 93 specs**, with valid owners.
  These are discovery counts, not claims that all test bodies passed.
- Two deterministic frontend builds produced identical seven-file SHA-256 trees;
  tree-list digest `a2f986d5f61191d55fc92fd009d76942c789f4d864090efaa12ff5319d428362`.
  Generated `workbench.js` SHA-256 is
  `e4b418264800791b4f5167002b5748bf142bb470184bb4aab616b0c8d79c9b78`.
  Targeted F-rule Ruff, new-file import checks, compileall and diff checks passed.

Direct desktop pixel inspection covered the gallery, required frame observations
and optional-comment/footer states at 1280×720. Four retained captures are in
`/tmp/plotloom-creator-confirmation-pixels.uE519F`; capture-list SHA-256 is
`4387c0fcd3c1a0d1c993fe7948440ffff6176b59c11827eb3458e591ef6a0d1f`.
The observed command/result summary is retained at
`/tmp/plotloom-creator-confirmation-verification-summary.log`; it is a concise
record of observed results, not a full stdout transcript. Deterministic hash
manifests are `/tmp/plotloom-creator-confirmation-static-first.sha256` and
`/tmp/plotloom-creator-confirmation-static-second.sha256`; pixel hashes are in
`/tmp/plotloom-creator-confirmation-pixel-captures.sha256`.
The original and retained captures show readable controls, raw limitations,
explicit subject endorsements and the separate-video-work wording. This is local
fixture UI evidence, not valued-project or creative/media acceptance. Non-failing
Starlette/httpx, browser color-environment and large-chunk advisories remain.

The manager's `2ec62c70` full gate remains failed **1,828 / 10** on its base;
the `d721bc68` continuation has **104 Python passed**, then **308 / 10 failed**
of 318 browser cases; the `4d216ec8` worker checkpoint has **26 affected browser /
8 metadata tests passed**, not full qualification. None is relabelled by this
source checkpoint. Fresh full/local/browser/wheel, native/preservation and hosted
CI remain manager-owned and pending. This worker performed no full or equivalent
release collection, real generation, live/QA operation, activation, merge or push.
The valued Moon story and retained c771 installation were left aside without
close/delete/cancel/replay/rebind operations. The source checkout and Relay route
remain retained; after the committed receipt closeout the worker holds all edits
and checks for the next explicit brief.

### Brief browser admission response ownership · 2026-10-13

Test-only implementation revision
`fb20881e98e83d852f5c71b07db81f7350150627`, parent
`02bb91d95c76607410ddbe5ac5a94a61e78d8c01`, repairs the existing
`manual-creator-entry.spec.ts` unchanged-restored-Brief journey. Product code,
API contracts, generated assets and valued project state are unchanged.

The manager's full gate on `02bb91d9` passed 1,855 Python tests, 1,377 frontend
tests, type checks, build and browser allocation, then failed one browser case:
317 passed / 1 failed. The wheel step was not reached. Preserved evidence:

- `/tmp/plotloom-final-qualification.AByRor/full-gate.log`, SHA-256
  `efaccbaaa10380d775d33ac1642718f744a8ee64158822c9a3e37fffb79a63cb`.
- `/tmp/plotloom-final-qualification.AByRor/browser-failure-02bb91d9.tar.gz`,
  SHA-256 `325dbe90a5ef6a7850d4d79b8445314c50a82d0cd52611f52ef826d2a6a3b5fb`.
- The failed case's archived `trace.zip`, SHA-256
  `939eb9f36def30452fa9128474b75a004bd1862e834ea1bfc164e7c1fe7c9372`.

Root cause: visibility did not establish initial admission readiness. In the
original trace, visibility completed at monotonic time `201469.634` while the
initial GET, started at `201386.495`, remained pending. The first mutation
waiter armed at `201470.444` consumed that initial eligible response at
`201481.948`, before the title fill completed at `201494.525` and the PUT at
`202238.527`. The actual post-mutation GET at `202258.404` returned ineligible,
and the product disabled its control correctly. The defect belongs in browser
test response ownership; no product admission defect was demonstrated.

The test now arms the initial GET before navigation, asserts its eligible state
and canonical revision, and waits for the enabled control before arming the
first mutation waiter. Each edit asserts the exact PUT payload, revision and
receipt, then consumes a generic GET and requires ineligibility and disabled UI
before the next edit. It does not filter responses by the desired eligibility.
Reload, restored draft, exact DELETE body and consumed-revision header,
unchanged canonical data and revision, connected editor, stable URL and absence
of autopilot launch remain checked. The request ledger covers both PUTs and the
DELETE from initial navigation. No sleeps, retries, timeout increase or product
stub was introduced.

Executed verification against the committed test source:

- Smallest case: `npm --prefix frontend run test:e2e --
  e2e/manual-creator-entry.spec.ts --grep "unchanged restored Brief save
  refreshes launch admission in place after exact draft cleanup"
  --output=/tmp/plotloom-brief-admission-repair.GLm2w4/failed-case`:
  **1 passed**, including wrapper E2E typecheck.
- Focused tier: `uv run --locked --no-sync python scripts/verify.py focused
  --playwright e2e/manual-creator-entry.spec.ts`: **10 passed**, including
  wrapper E2E typecheck.
- `BROWSER_GREP='.*' node frontend/scripts/check_browser_shard_manifest.mjs`:
  **93 specs / 318 cases**, shard counts **84 / 72 / 72 / 90**, zero missing
  cases or overlap. This is inventory evidence, not execution of all cases.
- `git diff --check`: passed.
- Independent read-only review requested GPT-6 Luna / Max: no actionable
  findings. Effective host model and effort settings remain unverified.

Logs are under `/tmp/plotloom-brief-admission-repair.GLm2w4`:
`failed-case.log` SHA-256
`a9abf97c16cdfb1b8295d48851483a483b4e6a97eebabac90803c0b44f5ee0e2`;
`manual-creator-entry.log` SHA-256
`d71722eae8ce913f09ceda904f7c57578c293bf2384cc187361ea1b286fcbb32`;
`allocation.log` SHA-256
`c683931031d65593106d3a62689fde8e54cd8e58e36ec94e39460f157515d2a5`.
The focused runner refused a line-number selector before executing any check;
the smallest case therefore used the established npm wrapper and name selector,
followed by the supported whole-file focused selector.

The original full gate remains failed on its original source. This scoped pass
does not establish full release qualification or product acceptance. Remaining
qualification, wheel, native/preservation proof and hosted CI belong to the
manager. The worker holds after commit; no full rerun, real generation, live/QA
operation, activation, merge or push occurred. Checkout and Relay route remain
retained.

## Manager technical closeout · UX, Brief style and creator confirmation

Qualified executable source: `ee7ec8de845fdb96c28ad46bd1dfef9158c551ab`,
tree `58b0c53b1facaf3b0751a51bc5a185bbea7d4796`. The last executable delta is
test-only `fb20881e`; `ee7ec8de` adds its receipt. The pinned submodule remains
`4f9b2128c82adf623f594ba714c97d0afcfc16a2`. First-pass Python scheduling
`e9e67847` and corrected documentation `31c6a209` are ancestors of this candidate.
The optional 85-percent stretch candidate is not integrated or a predecessor.

### Combined local software qualification

The original `02bb91d9` full run remains **failed**, with its one diagnosed
browser response-ownership failure and wheel not reached. Its unchanged-input
passing evidence is reused: **1,855 Python / 1,377 Vitest tests**, both type
checks, deterministic frontend build/parity and the complete browser inventory.
Python used two whole-file case-count workers and took **941.756 seconds**;
this is not a matched speed comparison to earlier suites.

After the reviewed `fb20881e` test-only repair, the manager reran the failed and
downstream gates without filters: **318 browser cases passed**, E2E typecheck,
93-spec allocation and wheel build/installed-wheel smoke passed. The continuation
exited zero in **489.009 seconds**; browser execution took **481.506 seconds**.
No product, dependency or configuration input to the reused passes changed.
The combined local candidate is qualified; no original failed run is relabelled.

Evidence in `/tmp/plotloom-final-qualification.AByRor`:

- `full-gate-result.json`: SHA-256
  `fa410dd1efa5c99052e86252fca0eb3bdf35e8df0dee178c630b7b46b1504c2c`.
- `continuation-result.json`: SHA-256
  `cbc58fb5cfb4124d54557efbea44092f9b021c47174ac05d70e03dec668960aa`.
- `continuation.log`: SHA-256
  `18ed18133b77b142ef469babf4896e7023ad127b08d8fe4b942b6e3f59bf9a9a`.

### Actual native delivery and visual boundaries

Disposable project `0a3b23ee-1ba8-486a-b648-1502450654a9` used the production
adapter and exact frozen packages: **8 real text jobs and 5 real ImageGen jobs**
were delivered and adopted. Complete readback passed for four code-owned nodes,
three filmed scenes, two routes, two references and three unique required frames,
with exact currentness, pins, delivery inventory, hashes and derivative lineage.
All six human/video fact tables remained empty. Final state was awaiting review.

The original operator proof remains **failed**: its four-filmed-scene assertion
conflicted with the already-frozen three-footage/one-route-only topology. Separate
complete frozen-contract readback passed; the four-filmed prose requirement was
not satisfied and is not promoted into semantic or creative acceptance.

Five attempt-owned typed native ImageGen completion events matched native PNG
bytes, declared output hashes and distinct native-task/execution identities.
CLI stdout was not treated as provenance. A separately retained manual inspection
of exact calls and reference bindings found both reference jobs unconditioned and
the three frame calls conditioned on the canonical Cast reference. Typed events
did not independently establish reference-argument ingestion or character identity.
The first image needed same-job, non-generating metadata recovery after the worker
discarded its successful ImageGen return shape; no duplicate generation occurred.
Consequently this proof is not a wholly unattended executor claim.

Manager pixel inspection of all five original PNGs found the Brief's pale
watercolor/pencil/paper direction, rather than the old live-photo preset. Frames
are opening pauses, not proof of the later scripted actions. Exploratory Art
geometry limitations remain disclosed. No aesthetic reroll, video or voice was
generated, and no creator endorsement or image-identity approval was invented.

Evidence in `/tmp/plotloom-final-native.H4hd05`:

- Failed `native-full-proof.json`: SHA-256
  `80952ce65b42604d205fb5bfc42225e4b745dc48580192b5b1ca83946fe825e2`.
- `completed-native-readback.json`: SHA-256
  `f98cb67b16c21b61acbd52e9a7d144d3649da911860141127b84222048e1a3c3`.
- `typed-native-image-proof.json`: SHA-256
  `6abb69a7d93a3fb55db5723b743440ea0d9e7caf551609d07f49f6a2732f91eb`.
- `manual-reference-argument-reconciliation.json`: SHA-256
  `b354c0fc715edb60817c918b75b4e7631b4ee42c0fc2b910229c1d34582cfda2`.
- `manager-pixel-observations.md`: SHA-256
  `edc87a39d0eda3902620cbfa619446aaa04216b668e2cc3c6b38f40923af23ca`.

### Preserving actual activation

The Moon run `568f2b11-5552-44f8-aa86-7008c37ab2c7` had finished generation
before the safe-idle operation. The two normal service owners were stopped only
after exclusive project leases, registry idle and unchanged logical/payload state
were checked. The owner-only recovery directory
`/Users/wjmao/Library/Application Support/Plotloom/recovery/autopilot-ux-c771-20261013`
retains **2,246 raw entries**, all **13 verified committed database copies**, source
and pinned-submodule archives and verified Git bundles, protected controls and the
old Docker image. Its manifest SHA-256 is
`2558e274b04ca656310ee67e7ba005e311eb272f9602b94a0d1976640caaa12b`.
Manual cutback preserves newer data separately; no SQL downgrade or deletion is
authorized. No second capture, migration or restart was used to repair evidence.

The clean live checkout was switched detached to `ee7ec8de`; the established
`uv run --locked --no-sync python services/creator_workbench/manage.py start`
completed successfully. The normal Docker/LaunchAgent path is healthy. Readback
confirmed exact runtime receiving contracts, all seven shipped static hashes,
mounts and matching loopback/Tailscale project/run/review APIs.

The original literal database-immutability verification remains **failed**.
The existing controller reacquired its process ownership claim on startup,
changing exactly `claim`, `revision` **229 → 230**, and `updated_at` on the one
Moon run. A separately reviewed read-only reconciliation passed: all schema and
79 other Moon tables match, the other 12 databases match, and all other run cells,
frozen policy, jobs, human facts and payloads match. The new UUIDv4 claim and UTC
timestamp fall within the 90-second container-start window. API differences are
only that revision/timestamp and the review's matching `runRevision`.
This is a real CAS revision change, not whole-database or full-run immutability.

The Moon story remains awaiting review with unchanged bundle SHA-256
`d12d5388e23bcfd3fad83360fe834292f5e7e6832fad4de5a8721db7af2cd62a`.
Its 28 frames, five references, 437 payloads and all 98 existing registry jobs
were preserved, with zero new dispatches or human facts. Credentials, settings
and controls match. Nothing was cancelled, replayed, regenerated or rebound.

Private evidence retains the failed copied-helper physical-equality check (its
comparison locals were not saved), the separate existing-copy logical/payload
compatibility pass, two failed preflight observations, and the failed literal
activation check. None is silently waived or relabelled. Named historical idle
profiles were restricted to four exact already-unavailable IDs, exact old schema
and empty intent/attempt/work-unit tables; historical accepted/ready creative
candidates remain present. Unknown layouts/statuses still refuse admission.

The one new verify-only execution exited zero. `ux-activation-proof.json` SHA-256
is `893033954ff9d63cffd77187fbf2d0ad900d2dc7576bab52b0f12e560cff3ec1`;
`activation-v4-verify-execution.jsonl` SHA-256 is
`be382b6464962771776429fcaae04663b423fd79d3e0515a341a08fdf260c506`.
Independent read-only review closed the narrow claim reconciliation, including
eight synthetic guards and stored-naive-UTC normalization. Requested reviewer
settings were Sol/High; effective settings remain unverified.

### Release and next assignment boundary

This records technical closeout and releases the preceding source/heavy-check
windows for the approved separate CLI assignment. Publication follows the fresh
remote-divergence check. No hosted CI was manually dispatched; exact-SHA hosted
qualification remains unconfirmed. Genuine creator review remains pending and
does not indefinitely block isolated CLI implementation. Future CLI activation
requires its own qualification and safe-idle gate; the Moon run must not convert.

Optional Python speed candidate `ce8bebdc` remains isolated and unintegrated.
Twelve valid, unprofiled fresh-child samples in three paired AB/BA/AB rounds used
two unchanged full-scale cases (27 frames / 29 images). Median external wall
seconds were **20.3597 → 16.7391 (17.783%)** for handoff and
**48.8861 → 37.8970 (22.479%)** for complete images. All pairs are retained under
`/tmp/plotloom-python85-phase1.qDMEYA/matched-unprofiled-g2obdbim`;
results SHA-256 `a448942676f603bc6b455c5a0eae394d587fb340a6d2da3472fe89be0d365af0`,
raw pairs SHA-256 `534f10fbc3c75341c44556f4f071907fd0588b01c7ecb64305d95ef9664a2438`.
The rejected pre-collection serialization attempt is excluded, not a timing
sample. These are subset measurements with host/cache/order limits, not a
whole-suite or 85-percent result. Full qualification and integration remain open.

## Serial Codex Exec synthetic patch boundary · 2026-10-14

Scoped native evidence for the built-in patch path only; it does **not** establish a
general filesystem boundary. One synthetic CLI turn ran at source `7c9d74a1956861d2d393638e875d5e4a2137d5f5`,
CLI `0.162.0-alpha.17.2`, model `gpt-6.1-sol` / medium, profile
`c291e28504980c8d6c6f39178f66d2d7386174c9db0da7c7edf8cecfa270682a`.
The production permission/environment builders were used; reproduced argv SHA-256
is `500d836696d3e3271841acdfce15d97f8f9da9fec9c5e2b093e3c8d6c024818b`.

The typed session records a successful read of the package control, one successful
built-in patch in delivery, and separate attempted patches to an outside absolute
path, a traversal target and a delivery symlink. Each outside patch result reports
`Operation not permitted`; all three outside sentinels and the symlink target kept
their pre-run SHA-256 values. Exit code was 0, the exact turn completed, and the
owned process group exited. The captured stream passes strict parsing with the
probe's 16 MiB line and total limits.

At this first probe, package-write denial was not attempted; the unchanged package
file alone did not prove that case. A later, separately released turn covers it
below. The initial raw result labels itself inconclusive because the harness
supplied a 50 MiB event limit with a 16 MiB total limit; the captured stream was
reconciled with valid 16 MiB/16 MiB limits without another CLI call.

Private evidence: `.local/native-proof/patch-boundary-7c9d74a1/reconciliation.json`
(SHA-256 `a3391f0105d0ac24beba63d67c8c488dd47394195548bf3ab0752f6519c0a422`),
original `result.json` (SHA-256
`1e345192a60414f7d65f730f0783615e3e102cd38337539f4702e280b9832298`),
`stdout.jsonl` (SHA-256
`63f5968e3302431a22c3388affe34d9faf2ef2c4317cfc7c1a4478cfa0f4691e`),
and `stderr.log` (SHA-256
`2df3061a9290049849d88a9eea0b62169a786ee2b0d1bd6f71b323604bb4d766`)
in the same ignored root.
Exact CLI session `01a138b3-1d95-76b1-97eb-81c48130c2c5` is
`/Users/wjmao/.codex/sessions/2026/10/14/rollout-2026-10-14T00-37-05-01a138b3-1d95-76b1-97eb-81c48130c2c5.jsonl`
(SHA-256 `a8b4abb73243983fb13e285d02528dd65e4614470ebbdd102e3d2ca094de4f1e`).
No implementation source or tests changed; only this receipt was appended. No
ImageGen call or creative canary ran.

## Serial Codex Exec package-write refusal · 2026-10-14

A separate native CLI turn at the same source and profile read a synthetic package
sentinel successfully, then made one built-in `tools.apply_patch` attempt against
that same readable sentinel. Its paired `custom_tool_call_output` says the patch
was rejected because it was "writing outside of the project" under "user approval
settings". The sentinel SHA-256 remained
`80fa977775da36dc66fdf80b4e6c0c636a4c93a024e204b77a09f21c1cac279c`; there were no
file-change events. The bounded stream strictly parsed, the turn completed with
exit 0, and the owned process group exited. The manager accepted this scoped
built-in patch package-write refusal case.

The observed denial is at the built-in tool/project-approval boundary. It does not
isolate the lower-level filesystem permission map from the project-root approval
gate and does not establish general shell or operating-system write behavior.
Together with the delivery success and outside absolute, traversal, and symlink
denials above, this qualifies only the tested built-in patch path. ImageGen
reference pre-read remains a separate, unqualified boundary.

Private evidence: `.local/native-proof/package-write-7c9d74a1/reconciliation.json`
(SHA-256 `c9836e2b34598ffaedb5f673fbb1a4069c215d4fac9394a14df2f10eb1e747da`),
`stdout.jsonl` (SHA-256
`5f56cd1d2fabb22289829bc6efa93bbefb7d7e360fff429e1badb826369dea19`), and
`stderr.log` (SHA-256
`b2bdea4ed8441e26433ed1a2152884feda187b170252cfc666bd756338f2005f`). Exact CLI
session `01a138ba-6fea-7ef2-9b18-aae6b7c51cb1` has SHA-256
`e0c6d4abbfdc4150405949bcc7a20e76b266c1c22c9c2e8fe08b0b193edb7346`. The matching
attempted call and result are included in `reconciliation.json`.

## ImageGen reference pre-read · prepared, not executed · 2026-10-14

No ImageGen call, provider dispatch, or generated image was made in preparing this
plan. The source/profile-bound image-domain invocation was assembled with the
production permission and environment builders. Profile hash is
`c291e28504980c8d6c6f39178f66d2d7386174c9db0da7c7edf8cecfa270682a`; the current
`codex_exec_supervisor_process.py` file SHA-256 is
`fb2035c83dcdc58fea9d9b030233513af9fdb5314954a5bc28e4bcc0b6c0a761`. The
production-built filesystem config SHA-256 is
`5876f2c818ef467757f4edab360d89cf5aab411366f770f5a1cbca401db1d156`; the mirrored
image-branch argv SHA-256 is
`dc4ccd0f7a27cfc9de0384c5e183d657e0bf512b6fccf88b89f54c1eaf041f9e`. The package
is read-only, delivery is writable, the outside reference has no path grant under
the root-deny policy, network is disabled, and the image-generation feature is
enabled. The image-domain environment omits source-root and `PYTHONPATH` entries.

The current connected outer-runtime callable is `image_gen__imagegen`, with this
exposed argument schema:

```text
prompt: string (required)
referenced_image_paths: string[] | null (optional)
transparent_background: boolean (optional)
num_last_images_to_include: number | null (optional)
```

Do not combine `referenced_image_paths` with `num_last_images_to_include`. The
local `codex debug prompt-input` output has no tool schema, so this records the
currently connected runtime declaration and does not claim that the local CLI
printed its internal native-tool schema. Plotloom's Codex Exec prompt/parser source
contract uses `images` as the literal reference-path list instead. The pinned
CLI's native tool schema remains unobserved; a future native run must capture and
inspect its actual typed call arguments and paired result. The machine plan records
these as separate schema surfaces.

The fresh ignored fixture root is
`.local/native-proof/image-preread-7c9d74a1/`. It contains a valid synthetic 512 ×
512 RGB PNG at `outputs/synthetic-project/jobs/ij_7c9d74a1imageprereadcontrol01/package/references/allowed-control.png`
(297,411 bytes; SHA-256
`62288ef413751389d27aa795aa2063e3e318357a679c9af9c49f51ac740945ab`) and a
same-sized outside-package PNG at `outside-reference.png` (297,402 bytes; SHA-256
`41f5efb374e391e7c671bda3c8cfcff0ac409cd4c88f966cea61ac7705c679c2`). The frozen
synthetic request inventory names only the allowed package reference. Both images
were checked for PNG chunk CRCs and successfully decompressed to the expected
512 × 512 RGB byte count.

The prepared sequence allows at most one outside-reference negative call and, only
after a proven local pre-read denial plus a separate manager release, one allowed
control call. Automatic retries are zero; current authorization, dispatches, and
outputs are all zero. Reserve one output for each future call. If the negative
call dispatches or produces an image, stop without running the positive control;
the maximum generated images across the sequence is one.

The negative case passes only if the exact typed call names the outside path once,
its paired result explicitly identifies a local file-read or permission refusal
for that path before provider submission, and the exact CLI session contains no
`image_gen.generation` extension/event, remote operation ID, `savedPath`, or
generated image. Inspect both bounded stdout JSONL and the exact session because
stdout alone can omit extension records. Both fixture hashes and the owned process
group must also verify. A generic failure, any provider-dispatch evidence, any
generated output, a fixture change, or an unattempted/refused call is a stop result
and is not evidence of pre-read denial. There are no retries.

The machine-readable plan, exact argument candidates, package inventory, fixture
metadata, and source/config/argv hashes are in
`.local/native-proof/image-preread-7c9d74a1/plan.json` (SHA-256
`619dfca606b5cc01bd46b78f8107a34af0e4f0c96a9c6071e9c56132d3831e1f`). It is
preparation evidence only; execution remains held for manager review and a separate
native authorization.

### Reference-view contract finding and proposal

Static source review found a contract mismatch. Frozen image package instructions
require viewing each `character_identity` reference before generation and require
viewing `parent_output` for character-reference proposals. The pinned profile
unconditionally disables `view_image`, and the current session adapter records
ImageGen calls/events but no typed local view operation. The delivery builder then
sets `viewedReferenceHashes` from frozen `character_identity` references and writes
that those bytes were supplied to built-in ImageGen. The generation receipt proves
which references were attached to ImageGen; it does not prove a separate local
viewing action. The project binder compares the resulting hash set to required
identity hashes without checking view evidence. ADR 0165 currently says no frozen
workflow needs local image attachment, which conflicts with those current package
instructions. This is the root cause: prompt, enabled-tool profile, telemetry
evidence, and delivery semantics disagree about whether the reference was viewed.

The proposed resolution is to preserve the viewing obligation and qualify an
image-domain-only `view_image` capability while keeping it disabled for text work.
After manager review of the contract and a revised profile, first inspect the
pinned child CLI's tools metadata API for the exact `view_image` callable schema,
if it exposes one. A model description or the outer app-session schema is not
schema evidence for the child CLI. If metadata is unavailable, capture the exact
schema from a released native view operation. Then use the production
package-read/delivery-write/root-deny filesystem profile to probe one allowed
package reference plus outside absolute, traversal, and symlink-escape paths, with
no ImageGen call. Any outside success, missing case, ambiguous error, or unbound
result is a stop and leaves the reference unviewed. A successful allowed call must
bind the exact frozen package path and pre-read content hash.

If those probes establish an exact typed call/result contract, add separate
trusted reference-read evidence to the host receipt. Derive
`viewedReferenceHashes` only from successful validated local reads; keep
`CodexExecImageEvidence.referenceHashes` as the distinct list of inputs attached to
ImageGen. Cover every role whose prompt requires viewing, including
`character_identity` and `parent_output`; explicitly settle `source_keyframe` and
other reference roles before implementation. Do not infer visual understanding
from a path read or generation attachment; any model-authored identity notes remain
a separate untrusted statement. Amend ADR 0165 and the affected reference-use
contract before source edits.

This proposal is not implemented or accepted. The exact CLI reports the
`view_image` feature as stable and the current profile disables it, but no allowed
or denied native `view_image` call has been observed. The previous built-in patch
probe does not qualify `view_image` confinement. The current connected callable's
`referenced_image_paths` field also does not establish the Codex Exec CLI's
`images` argument or native `view_image` schema. If a future exact schema and
path/result binding cannot be established, keep the workflow fail-closed rather
than claiming a reference was viewed.

The proposed probe order is: at most four no-provider `view_image` boundary calls
(one allowed package read and three denials), then at most one ImageGen
outside-reference pre-read call, then at most one allowed ImageGen control after
its own manager release. Total proposed native tool calls are at most six, with
zero automatic retries and at most one generated image across the ImageGen phases.
Current authorization, dispatches, and generated outputs remain zero.

### Diagnostic child-runtime metadata probe · 2026-10-14

One separately released, diagnostic-only native CLI session used the same pinned
image-domain profile and production permission/environment builders, with the sole
argv difference `--enable view_image`. Its runtime metadata query found no
`view_image` entry in child `ALL_TOOLS`; the `image_gen__imagegen` entry contained
only `name` and `description`, with no argument schema. Because no child-runtime
`view_image` callable/argument shape was exposed, the allowed-package case was
missing. The session stopped before any `view_image` call; no path was guessed and
no retry or alternate metadata route was attempted.

The exact session had one metadata `exec` call/result, zero `view_image` calls, zero
ImageGen calls, no `image_gen.generation` event, and no `savedPath`. It ended with
`turn.completed`, exit 0, in 13.413 seconds; the owned process group exited. The
valid synthetic package PNG, outside PNG, package tree, empty delivery tree, and
precreated symlink were unchanged. This result is
`inconclusive_missing_child_runtime_view_image`, not a view boundary pass. It does
not show whether a separate direct CLI-native feature call exists outside
`ALL_TOOLS`.

The diagnostic variant reused profile hash
`c291e28504980c8d6c6f39178f66d2d7386174c9db0da7c7edf8cecfa270682a`, CLI
`0.162.0-alpha.17.2`, `gpt-6.1-sol` / medium, and production image-domain argv plus
the single `view_image` enable flag (argv SHA-256
`d6f6182d4c04c81a859b8636e1bdef300fa10699463950ae372c891fc1640b99`). It was a
diagnostic variant, not a newly qualified production profile.

Private evidence: `.local/native-proof/view-image-diagnostic-7c9d74a1/reconciliation.json`
(SHA-256 `e593a6f97c7c8d8a54c82e7409c04f6bcbdbe8cf08f76448977a02b8edc50137`),
`result.json` (SHA-256
`e6e9eb08f92a078ab669c321d83a51466c8d0f5411e38974339ded1fa6f78e0b`), and the
single session `01a138c6-653b-7b60-b3a2-fed7caf890f0` at
`/Users/wjmao/.codex/sessions/2026/10/14/rollout-2026-10-14T00-58-08-01a138c6-653b-7b60-b3a2-fed7caf890f0.jsonl`
(SHA-256 `9bc9fa80019fd2003277caedd6499f2334411f4ef2411b0b9c35086e82382256`).
The bounded stdout SHA-256 is
`9f96dcab1e88dc24fc530e8fbf2f706344bde56f31f75946ee38d89a02eaad2a`; stderr was
empty. No source implementation, tests, or provider dispatch ran.

### Append-only correction: revised view-image loader probe · 2026-10-14

The preceding diagnostic metadata conclusion is superseded. Its argv disabled and
then enabled `view_image`, so the missing tool entry did not show that the pinned
child lacked the callable. The corrected diagnostic omitted `view_image` from the
disabled list and enabled it once. `features list` reported both `view_image` and
`image_generation` stable and true. Child `ALL_TOOLS` exposed `view_image` and
`image_gen__imagegen`; each entry's callable declaration is embedded in its
description, rather than a separate schema field. The recorded declarations are
in the private reconciliation. The image-generation declaration includes
`referenced_image_paths`, while current source telemetry accepts `images`; resolve
that contract before any production ImageGen dispatch.

One diagnostic session made four typed `view_image` calls: the allowed synthetic
package PNG, then outside absolute, traversal, and symlink aliases. The allowed
call returned a 14,523-byte PNG data URL with MIME `application/octet-stream`
(output SHA-256
`0fae758f849f2f598ee99999d175dbcbb1aecaa7c89aa8d41b59deba60d2e005`). All three
outside calls returned `Operation not permitted (os error 1)`. Fixture hashes,
package tree, symlink, and empty delivery tree remained unchanged. This is scoped
path-loader allow/deny evidence for the diagnostic profile only; production still
disables `view_image`.

The allowed result does not qualify model-visible image delivery. The harness
checked `result.image_url.startsWith("data:image/")`, but the returned MIME was
`application/octet-stream`; that branch therefore emitted the result object as
text and did not call `image(result.image_url)`. The session separately contains
native `ImageView` item `exec-0690c237-db6e-465b-927a-d1817a8c5a67` for the exact
allowed file URL, but the paired `exec` output contains no `input_image` part.
A later MIME-agnostic base64 check confirmed returned PNG bytes; it does not prove
that the model received image pixels. Keep the visual-reference requirement
unqualified until a released probe verifies a real image content block end to end.

No ImageGen call, provider dispatch, generation extension, or `savedPath` occurred.
The session was `01a138cb-c1bd-7db1-bdb6-5a355363ba4c`, CLI
`0.162.0-alpha.17.2`, `gpt-6.1-sol` / medium, 87.764 seconds, exit 0, with owned
process-group cleanup proven. Its source/profile hashes and typed call/result
pairing are retained in `.local/native-proof/view-image-diagnostic-revised-7c9d74a1/reconciliation.json`
(SHA-256 `3977aa3de427237c4e33481b46212df429de22200916973c02dfde84966ca244`).
The original session output and earlier reconciliation remain unchanged.

### Append-only correction: truncated view output · 2026-10-14

A later inspection of the paired `exec` output found
`Warning: truncated output (original token count: 99296)`. The 14,523 decoded
bytes and SHA-256 recorded in the preceding correction are only the captured PNG
prefix; they are not the complete `view_image` output length or identity, and they
do not show that the viewer transformed the source. The frozen source fixture's
independent hash remains `2f2cb5d3172b3d3757a635bd30226d14f29c50df97016ae1c13c244a065f10e`.
The exact `ImageView` event and three path-specific permission denials remain
valid scoped loader evidence. No `input_image` block was present in the paired
`exec` result, so model-visible pixels remain unqualified.

Private append-only correction:
`.local/native-proof/view-image-diagnostic-revised-7c9d74a1/reconciliation-correction.json`
(SHA-256 `ae8a676a030c996388dd47fe5ff87ccdf58aa9a7fc1f67341aca0855c44a5270`).
The original session and CLI result were not changed; do not use the earlier
captured-prefix hash as a complete returned-image identity.

### Source candidate verification: complete reference raster decoding · 2026-10-14

Independent review found that Pillow 11.3.0 `Image.verify()` could accept a
reference-view result without decoding complete raster pixels: PNG container
and CRC checks do not establish complete scanlines, while the base JPEG
verifier only closes the stream. The source validator now preserves byte and
pixel bounds, verifies the container, reopens the bytes and calls `load()` to
decode pixels, and fails closed if `ImageFile.LOAD_TRUNCATED_IMAGES` is enabled.
This keeps `viewedReferenceHashes` tied to complete image content in the exact
paired `input_image` block.

Regression cases cover the CRC-valid but incomplete PNG raster, a JPEG ending
after a valid scan header without scan data, and Pillow's permissive truncated
image setting. The independent read-only follow-up review found no further
issues in the decoder, fixtures, or ADR wording.

Local evidence for the reviewed source candidate: `verify.py focused
--pytest tests/test_codex_exec_telemetry.py` passed all 22 tests; targeted Ruff
on `codex_exec_tool_source.py` and `test_codex_exec_telemetry.py` passed;
`git diff --check` passed. `verify.py quick` passed locked dependency, API
unused-import, all 1,377 frontend unit tests, and frontend/browser-fixture type
checks. Quick excludes Python integration, browser execution, bundle parity,
wheel and installed-wheel smoke. No full gate or provider/native dispatch ran
for this source candidate; those remain under manager review.
