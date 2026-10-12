# Pre-video autopilot · single evidence receipt

Status: **P1 committed at `fd549395`, preservation correction at `b3b01fb6`;
P2 text orchestration locally verified, P3–P4 required**. No full autopilot happy path, product acceptance, valued
installation upgrade or live activation is claimed. Scope and stopping boundary are in the
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

## Remaining gates and precise next action

Current next action: the manager approved P0 and received P1 (`fd549395`). The
existing registered source owner continues P2–P4 in the same checkout. P2
deterministic full-chain faults precede P3 image integration; P4 adds compact UI
and truthful human handoff. Add collected tests to
native ownership and browser allocation with no reduction of current case union.

Source owner will deliver the stable candidate and scoped quick/focused/module,
browser/pixel, deterministic asset evidence in this same receipt. Manager owns
independent final review, the single stable `uv run --locked --no-sync python
scripts/verify.py full` qualification, packaging, real isolated native text/ImageGen
proof, actual installation inventory/upgrade/cutback, main integration/push and
quiet normal/Tailscale activation. Hosted CI remains excluded. No full suite,
browser/pixel acceptance, real generation, valued schema transition or final
human material handoff has been executed at P0.

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
