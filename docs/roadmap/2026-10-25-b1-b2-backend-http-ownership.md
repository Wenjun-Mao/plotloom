# B1–B2: Backend contracts and HTTP ownership

Status: **delivered: implemented, independently reviewed, locally qualified by
composite evidence and activated with exact preservation/readback; the single
current recovery manifest owns final source/wheel identity**.
Date: 2026-10-25. Inspected source and installed baseline:
`e3f0403e0247a4e5fc47fc8c20b8d9565fde4f64`.
Source R: `/Users/wjmao/.codex/worktrees/b30f/plotloom`, retained local main.
Installed P: `/Users/wjmao/projects/HU/plotloom`, detached installed checkout.

## Outcome, authority and scope

The owner requested a combined plan for B1 and B2 from the
[modularity audit](../verification/2026-10-25-modularity-audit.md), following the
completed G1–G5 deliveries. Establish actual backend contract and HTTP owners,
remove the observed domain/profile import cycle and duplicate protocol ownership,
and update consumers directly while preserving supported behavior.

Planning and attended independent read-only reviews completed at `16d31ee9`.
The owner then approved the combined delivery with “go ahead with Relay direct”.
That current request authorizes B1/B2 implementation, verification and scoped
activation below. Standing approval separately covers native Codex tasks and
model/effort selection; it is not being used to expand product scope.

Approved implementation scope: B1 → B2 serial internal checkpoints,
one integrated independent review and final local qualification, then quiet
activation of the affected installed backend/owned bridge with exact preservation,
readback, rollback readiness and a single current recovery refresh. Covered
engineering checkpoints would not require repeated owner approval. Completion
means the running installed product and coherent local main have the reviewed
boundaries and evidence, rather than stopping at extracted files or test totals.

Excluded: B3–B7, frontend decomposition, new product behavior, provider/model/settings
changes, migrations/resets, snapshot-version retirement, new generation or grants,
UNKNOWN clearing, live-project deletion, push and GitHub CI. Existing autosave,
explicit production adoption, optional Freeze/read-only access and creative authority
remain unchanged. No external-provider call is needed for this refactor.

## Design and alternatives

Use contract families with explicit dependency direction for B1, followed by the
existing `register_*(app, opened_project, explicit_dependencies)` route pattern for
B2. This makes the HTTP layer consume settled leaves and keeps each failure
attributable before one combined release. Concurrent B1/B2 writers would repeatedly
collide on imports and signatures; serial source ownership fits this dependency.
Independent read-only reviews can overlap useful work on stable boundaries.

A mechanical file split with a `domain.py`/`api/models.py` forwarding facade would
reduce line counts but preserve hidden ownership and the cycle. A new router,
dependency-injection or shared execution-context framework would widen the change
without solving an absent capability. Neither is recommended. File names and
small cohesive combinations remain implementer decisions, not a prescribed module
count. Target ~400 lines; architecturally review every changed owner at or above
500 and explain a retained cohesive responsibility instead of fragmenting state.

### Inspected owners

| Current file | Lines | B1/B2 responsibility |
|---|---:|---|
| `domain.py` | 1,228 | Stage/project/run/evidence/media/provider contracts, public-value validation and forwarding imports. |
| `provider_profiles.py` | 407 | Cohesive named profile versions/hashes; consumes the domain-owned URL validator. |
| `validation_storyboard.py` | 540 | Ordered gate assembly mixed with dialogue and continuity checks. |
| `api/project_folder.py` | 830 | Composition, request admission, live error mappings, project lifecycle, canonical/draft and remaining authoring routes. |
| `api/project_folder_image_jobs.py` | 463 | Shared projections, character-reference and ordinary image routes, frozen send authority. |
| `api/project_folder_media.py` | 307 | Existing media registrar, duplicate error registration and shared draft helper. |
| `api/models.py` / `api/contracts.py` | 342 / 392 | Forwarded DTOs, real HTTP helpers and duplicate protocols versus actual request contracts. |
| `api/errors.py` / `api/protocols.py` | 278 / 37 | Unwired alternate error policy with two test consumers; duplicated text/run interfaces. |

The named-profile module is not itself a required extraction: breaking its cycle
does not justify splitting its cohesive version/hash contract to meet a target.
The smaller API files are included for demonstrated ownership overlap, not size.

## B1: Contract leaves and ordered storyboard validation

### Dependency boundaries

1. **Public-value validation leaf.** Own secret-name/value rejection and public
   HTTP(S) URL validation below provider/domain/runtime/HTTP orchestration. Preserve
   name versus value checks, allowed local/loopback endpoints, URL normalization,
   invalid-port handling and rejection behavior. Here “public” means secret-free;
   this is not a new public-IP/SSRF policy. Keep typed continuity-key exemptions
   and persistence redaction at their existing authorities.
2. **Existing true owners.** Import canonical story models from `canonical_schema`,
   Brief contracts from `brief_contracts`, model-base behavior from `domain_base`,
   timing from `timeline`, and media authoring drafts from their current owner.
   Do not recreate those definitions in new leaves.
3. **Stage/canonical contracts.** Own stage names/order/status, payload selection,
   initial-stage prefix validation, revisions/heads/envelopes, drafts and canonical
   snapshots. Keep stage-specific canonical classes at their current owners.
4. **Project contracts.** Own lifecycle/operational state, nullable Brief, creation,
   duplication and directory projections. Keep `require_brief` and all state
   distinctions. A projection may consume a lower run-summary contract; core run
   contracts must not import upper project/directory projections.
5. **Run and exact-repair contracts.** Separate core statuses/runs/attempts from
   repair/reuse and progress/trace projections where they are cohesive. Keep
   `RepairSource` below the run that uses it; a repair-run creation view may consume
   `GenerationRun`, not require a reverse dependency. Preserve terminal membership,
   failure dispositions, reuse scope and durable evidence shapes.
6. **Evidence and media contracts.** Give gate/evidence, artifacts and media
   task/context families actual owners according to their consumers. Avoid making
   one replacement “common models” bucket or passing orchestration into a leaf.
7. **Provider contracts.** Legacy public configuration/settings/snapshot and the
   current named profile families retain their exact respective schemas. Put
   version dispatch above both families, using the validation leaf below both;
   remove the local import workaround and all reverse profile/domain dependency.

`domain.py` can retain one genuine responsibility or disappear. It must not remain
an import barrel or compatibility API. Redirect all production, script and test
consumers to actual owners; define each class once. Preserve class names, aliases,
defaults/default factories, validators, JSON schema identity and wire behavior.
Cold import tests should demonstrate the new direction without order-dependent
initialization. No import-time repository, runtime or HTTP side effects belong in
these leaves.

### Provider snapshot and hash invariants

- No schema version means the exact currently supported V1 snapshot; explicit
  camel/snake version 2/3 selection and precedence remain unchanged. Preserve each
  version's alias dump, defaults, omission/null behavior, refusal and hash input.
  Do not materialize named-profile defaults into a V1 snapshot.
- Preserve `PUBLIC_PROVIDER_SETTING_FIELDS`, supplied nonblank settings hashes,
  blank-hash derivation, canonical JSON sorting/separators/Unicode and current
  validator order. Preserve legacy default-only profile identity versus settings'
  active named-profile projection. Current snapshot/restore consumers justify
  these supported readers; this is not audit-only historical retention.
- Legacy text URL/model defaults are unrelated to the retired Atlas/Wan video
  execution fallback. Do not remove them or alter configured providers here.

### Storyboard gate extraction

Extract pure dialogue and continuity checks from `validation_storyboard.py` while
one assembler owns the exact version, complete input hash and ordered gate list.
Reuse `validation_state` algorithms. Helpers take explicit immutable inputs and
return ordered observations/results; no callback bag or shared mutable evaluator.

Preserve current order: identity/presence and scene order; per-scene shot bounds,
order/duration; unknown scenes; per-shot entity/state/audio and continuity
availability; beat dialogue; shot cues; cue coverage/fit/timing; coverage links;
scene/shot continuity uniqueness and sequence; beat continuity availability.
Continuity helpers must be called at the existing positions rather than grouping
all continuity gates together. Preserve IDs, severity, required/advisory status,
SKIPPED/not-applicable semantics, reasons/evidence text, stringification, order and
hash inputs including absent context. A gate remains technical evidence, never
creative approval or permission to mutate production.

## B2: HTTP owners and request lifetime

### Composition, access and errors

Keep the application factory as explicit composition and registration. Extract a
cohesive per-app request-access owner with `opened_project`, `inspected_project`
and `inspected_open_project` behavior intact. Its ContextVar is per app; GET/HEAD
read admission, mutation admission, proof scope, reset and store cleanup retain
their current exception boundaries. Directory inspection and inspection-admitted
pixel/project access remain distinct. Keep stores alive for their actual response
lifetime, including held/lazy JSON, HTML, pixel and streaming responses; do not
cache handles/proofs or close shared app storage per request. Legitimate app-level
text readiness and ephemeral credential state remain app-scoped.

Use one live HTTP-error registrar, preferably replacing `api/errors.py`'s alternate
policy with the factory's actual winning mappings. Capture the final handler table
after every existing registration first: registration precedence is behavior.
Preserve exact status/body/headers for bootstrap 503/Retry-After, busy/frozen and
revision/image conflicts, missing objects, domain/draft/storage errors and native
FastAPI validation. In particular preserve the actual minimal revision-conflict
body, delivery-cancelled 409 and current image-dispatch conflict mappings. Do not
add a broad exception catch or a new sanitization policy.

The generic registrar has two test-only consumers: identity-review refusal and
graph-safety diagnostics. Retarget their standalone fixtures to the canonical live
registrar and retain their actual refusal/body/nonmutation assertions. Removing
the unused alternate policy does not justify deleting current safety coverage.

### Route families and transaction ownership

- **Directory/lifecycle:** create/list/get, archive/restore, duplicate, permanent
  deletion, Freeze/unfreeze and snapshot operations. Retain creation fingerprint,
  reserved ID/time, lease contention, retry/resume/idempotency and raw-draft title
  projection. Lifecycle and operational state remain different contracts.
- **Canonical/drafts:** Brief/stage updates, reads and draft put/delete, with exact
  scope/entity constraints. Repository transactions still own CAS, payload equality
  and exact draft consumption. Emit `X-Plotloom-Draft-Consumed-Revision` only under
  its current successful-consumption rules; preserve absent versus empty header
  behavior, including discard responses. Keep the shared media/image draft helper
  with its genuine scope-validation responsibility, not a generic CRUD layer.
- **Other authoring reads/approvals:** cohesive run/media-task views and canonical
  storyboard review/approval registrations. Preserve `qa_command` attribution.
  Source-review routes remain a different authority and cannot install canonical
  shots, media or approvals.

Keep the method/path set, registration order, names/operation IDs, OpenAPI models,
response shapes and dependencies unchanged. No frontend API migration is needed.

### Character-reference and ordinary image owners

Separate character-reference selection/revocation/import-membership/prepare/send/
cancel/refresh from ordinary image list/copy/refresh/cancel/same-person review.
Retain existing `image_prepare.py`/`image_send.py`; move target-ID construction next
to preparation. Reuse stateless byte/hash-checked package/output/task projections
through explicit inputs. Do not merge their different acceptance/publication
rules into a generic media exchange or expand trusted H3 lookup into B5.

For **both** send paths preserve this complete sequence:
current frozen sources → configured task binding → exact package write → expected
task-ID/lane reservation → synchronous `before_send` revalidation of current and
prepared persistence authority → queue. Keep the store alive through the callback;
retain the configured send-task identity rather than substituting copy's current
task. Add route-level stale-authority refusal for each path: zero queue calls and
only the unsent reservation released. Cancellation/invalid delivery must not release
a native worker lease; accepted/inapplicable terminal evidence remains its owner.

### Actual protocol and helper ownership

Use G5's existing `text_provider_resolution.TextProviderResolver` as the single
resolver interface; do not make runtime import HTTP. `api/protocols.py` owns the
distinct HTTP run-scheduler and profile-secret capabilities. The runtime run-secret
leaser is different from a profile-secret source and must stay distinct. Remove
duplicate declarations/reexports from `api/models.py` and redirect text admission
and other real consumers. Do not revive R2's removed raw-media protocols.

Move real HTTP helpers to their actual owners: idempotency/header parsing, directory
cursors, provider projection/default construction, approval response projections.
`api/contracts.py` remains a real request-contract owner where cohesive.
`api/models.py` may disappear or retain a genuine responsibility; no forwarding facade.

## Ordered implementation and evidence

1. **Preflight/baseline.** Confirm current clean R/P, sole source writer, actual
   interpreters/platforms/dependencies, route fixtures and native ownership union.
   Last qualified totals were 4,026 Python/1,538 frontend/358 browser; recollect the
   actual native union and account for additions/moves, not log/footer counts.
   Capture compact representative before outputs: DTO schemas/defaults/aliases,
   V1/V2/V3 snapshots/hashes/refusals, URL/secret guards, complete ordered gates,
   final live handler table, routes/OpenAPI and draft/idempotency receipts.
2. **B1 checkpoint.** Establish public validation/provider dependency direction,
   then model families/direct consumers and pure gate helpers. Compare representative
   accepted/refused/missing-context outputs exactly; run focused contracts and cold
   imports. Stage legitimate new modules before tracked-source clone fixtures;
   do not weaken those fixtures to hide untracked-source failures.
3. **Early real API/persistence proof.** Before broad B2 extraction, use the actual
   app factory and disposable SQLite project storage: create a draft-only project,
   autosave incomplete Brief, read working title with canonical Brief still null,
   restart the same storage, resume the exact draft, adopt valid Brief with exact
   consumed-revision receipt, then read canonical state and empty consumed draft.
   Existing `test_working_project_autosave.py` supplies this current fixture.
4. **B2 core checkpoint.** Extract access/live errors then lifecycle/canonical/draft
   routes and real protocols/helpers. Attempt the existing real browser/API/SQLite
   autosave/restart journey immediately after this useful cut, before broad image
   work or unrelated qualification. Check Freeze reads/late-write refusal/unfreeze
   without adoption and held-response close lifetime with their existing fixtures.
5. **B2 image checkpoint.** Extract complete image families, then exercise both real
   routes through current offline package/raster-delivery fixtures, checking byte/
   hash identity, binding, refresh/publication and the two before-send races. Native
   image pin proof needs a coherent committed clean candidate: staged source alone
   is insufficient. Reuse the existing accepted-result browser fixture; no external
   provider generation or owner creative-acceptance claim is part of this evidence.
6. **Stable integrated review/qualification.** Independent read-only review checks
   actual consumer direction, preserved source/HTTP/lifetime/safety behavior and
   evidence. One qualification owner runs focused/module selections during work,
   then `uv run --locked --no-sync python scripts/verify.py full` on the stable
   combined candidate. Keep first failures failed; diagnose, run failed/affected
   and every unrun downstream gate, and reuse unchanged evidence. Repeat full only
   when changed inputs justify it. Reassess after two unsuccessful attempts at one
   criterion as repository policy requires; this is not an overall attempt budget.
   Retain the exact smoke-passing wheel using existing build/smoke tooling.
7. **Activation/closeout.** Coherent local main, quiet affected P backend/owned-bridge
   reload after live writer/queue checks, fresh preservation comparisons and actual
   readback; update the single functional recovery, concise decisions and this
   plan's results; consume temporary artifacts and archive idle attended workers.
   Stop after B1/B2. New material behavior/scope/authority requires owner agreement,
   not each covered internal milestone.

Use existing module owners/selectors expanded by `--show`, not a parallel runner.
Relevant regression anchors include provider-profile/secret contracts, storyboard
continuity/dialogue and diagnostics; project storage route/authoring/inspection,
request-proof/retained-proof tests; identity-review/graph refusal; native dispatch,
specialist settings, image delivery and image-pin tests. Browser anchors are
`project-folder-authoring-drafts`, `project-folder-close`, `project-read-close` and
`cast-reference-delivery-observation`. Keep their assertions and native case union;
update ownership entries for genuinely moved/new tests without shrinking coverage.

For parity use explicit IDs/times or compare the same retained disposable record.
Only actual typed observational fields may be excluded, with exact paths recorded.
Never recursively strip arbitrary `created_at`, `id` or `rendered_at` keys: authored
same-name values, authority fields, ordering and hashes must remain compared.
Scratch belongs under supported ignored `.local/b12`; keep compact outcomes in
this plan, not a new permanent receipt hierarchy or old-source archive.
The qualification owner owns disposable-fixture cleanup and settlement, checking
exact test-owned targets and dispatch state before supported lifecycle operations.
Preserve actionable failed evidence; never clear UNKNOWN or release native worker
leases to manufacture cleanup. Fixtures remain separate from current user projects.

## Pins, installation and preservation

API source is recursively included in the existing image-specialist pin inventory;
new API owners stay inside that coverage. If a previously pinned responsibility
moves outside a pinned root, update the inventory to its real new owner. Do not
retain an obsolete filename as attestation, add blanket source coverage or weaken
dirty/untracked/symlink/cache guards. Code changes produce a prospective new pin
without changing wire versions; old frozen requests/receipts remain immutable.
The native profile's Python-tree identity also changes: derive P's profile with
its actual launchd PATH and checked environment, never copy an R identity blindly.
No new grant/provider or optional external native qualification pair is required.

Before activation, recheck actual supported owner/queue/writer state; leave
healthy live work alone until a safe quiet window. Capture current user projects,
selected media/ranges, settings/credentials, operational state and dispatch/UNKNOWN
guards from their supported owners. Compare before/stopped/after as appropriate;
historical eight-project/26-range totals are context, not a hardcoded inventory.
Validate exact source/import/wheel/profile identities, readiness, private HTTPS,
directory/read APIs and selected playback readback. Report Mac/Linux/Python
differences honestly; local qualification is not an unrun Linux/full claim.

If activation fails, use the single existing qualified recovery for code/services,
retaining current user state; no data migration/reset or automatic data rollback.
Once readback passes, validate exact wheel, source and submodule membership before
atomically replacing that one recovery package. Do not create another archive.
Final documentation-only synchronization needs source/pin/profile identity proof,
not an unnecessary restart when executable inputs are unchanged.

Record durable dependency/authority decisions in concise ADR 0221 during
implementation, linked here; do not overload generation-specific ADR 0220
or duplicate the plan. Completion evidence must distinguish implementation, small
real journeys, final qualification, activation and agent-operated QA limitations.

## Planning review

Source-grounded independent HTTP review is complete (requested GPT-6.1 Sol / High;
effective host settings unverified). Its findings about actual live error precedence,
test-only generic consumers, request lifetime and image before-send proof are
incorporated. The manager independently checked B1 ownership/version/hash contracts,
the shared resolver and existing image pin/fixture constraints.

Independent execution-limits review is complete (requested GPT-6.1 Sol / Medium;
effective host settings unverified). It found no unnecessary approval gates,
arbitrary caps, excess serialization or restrictions on engineering judgment. Its
one handoff finding is incorporated above: the qualification owner explicitly owns
disposable-fixture cleanup and supported reservation settlement without weakening
UNKNOWN/native-worker safety. Both read-only reviewers released access; their
attended native tasks are archived. Planning made no source changes. The owner's
subsequent implementation authorization is recorded above; qualification and
activation remain to be demonstrated by actual delivery evidence.

## Implementation checkpoints (qualification owner)

Implementation decision: [ADR 0221](../adr/0221-backend-contract-and-http-ownership.md).
Sole writer/qualification worker: native `01a17632-5738-7db3-8733-d0a718042e75`,
registered with Relay to manager `01a04525-e907-7630-9640-78790d69e8ae`.
Retained R stays on local main; P/live runtime remain read-only for this worker.

- B1: removed domain forwarding; actual family leaves and direct production,
  service, script and test consumers; named profiles depend on public validation,
  with version dispatch above both provider families. Pure storyboard helpers
  return ordered observations while the assembler retains complete hash/version.
- Representative baseline (`d919e37f`) versus integrated source: exact schemas,
  defaults/aliases, V1 values/hashes, URL/secret refusals, full ordered gates with
  absent Brief context, final handler table, route order and OpenAPI match without
  observational-field exclusions. Separately replayed 23 exact accepted/refused
  V1/V2/V3 inputs against the baseline domain implementation; all match.
- Early B1 focused set: 34 passed, including real factory/SQLite incomplete-Brief
  restart and exact raw-input adoption receipts. B2 core focused: 18 passed,
  including retained request proofs and both generic-registrar safety consumers.
  These inputs were staged uncommitted cuts above `d919e37f`, not qualified commits.
- Before broad image work, real browser/API/SQLite draft autosave, stale-tab CAS,
  explicit canonical save and backend restart, plus Freeze/read JSON/HTML lifetime,
  late-write refusal and unfreeze without adoption: seven browser cases passed.
- Added one same-home incomplete-Brief→restart→complete draft→exact adoption
  journey, 14 schema/cold-import cases and both actual route before-send races.
  Their focused set passed 23. Two earlier race-test attempts failed on fixture
  context-manager misuse and UUID/string comparison respectively; both first logs
  are retained, with actual close and typed binding contracts used in the repair.
- Native ownership preflight first exposed seven collection errors from two
  missed service imports. Direct service imports were corrected; no compatibility
  layer was added. Current native union/module, offline image, clean image pin,
  independent review, final full and retained wheel results follow below.

Scratch evidence used supported ignored `.local/b12` (baseline/parity JSON and
execution logs), without permanent old-source archives or a parallel runner.
The manager consumed this task directory after reviewing the actual evidence.
No changed handwritten owner exceeds 500 lines after the substantial extraction;
large existing consumers receive only direct-import edits. Named profiles retain
their cohesive version/hash responsibility. No product provider call or owner
creative-acceptance claim is part of these offline fixtures.


## Source qualification and worker handoff — 2026-10-26

The implementation checkpoint is `6eefc82a`. Independent integrated source/safety
review found one obsolete native-image fixture composition; `1e56908e` registers
both actual image families and removes the obsolete target-helper argument. All
five original safety assertion trees remain unchanged; the exact affected safety
and new before-send selection passed seven cases. Production review is closed.

The qualification owner ran the actual locked/no-sync `scripts/verify.py full` on
clean `1e56908e`. **That first full remains failed**, exit 1 in 1,280.641s:
4,034 Python cases passed and nine failed (six specialist wake-unconfirmed cases,
three bridge-unavailable cases). Both standalone test fixtures had relied on a
route registrar implicitly installing HTTP handlers. `a3d442bc` explicitly installs
the canonical live error registrar in those fixtures; all original assertion ASTs,
case IDs and product sources are unchanged. The manager inspected the narrow fix;
the production review carries. The seven-file affected error/secret/refusal/lease
selection passed all 45 cases. This covers every originally failed case without
shrinking or rewriting their safety assertions.

One execution owner then refused any ambient full filters using the actual
`verify._validate_full_filters`, and reused the six original remaining
`verify._full_steps(...)[8:]` through `verify._run_steps`. All six passed in
688.752s: deterministic bundle, checked bundle parity, complete native browser
allocation, **358/358 browser cases** (680.564s), wheel build and isolated installed
wheel smoke. First-full frontend evidence is **1,538/1,538** cases plus type checks,
locked dependencies, media-tool readiness, API unused imports and prompt-reader
verification. No second full was run. This is complete local **composite**
qualification, not a newly green first-full result.

The current native case union is **4,043 Python / 1,538 frontend / 358 browser**;
Python adds 17 cases (ten schema fingerprints, four cold imports, two before-send
routes and one same-home Brief restart/adoption). Python native-case hash is
`90f84480abeb3b49a57ccb71713f93f7c03329a3eae56dcfcdafa25ee69a581e`.
Native ownership discovery passed. The older three-owner module body run was
explicitly cancelled (exit 130) after its successful complete union preflight;
it is **not** module-pass evidence. Its first seven import-collection failures,
the original safety-fixture failures, intermediate fixture mistakes and the
first full failure were retained through manager review. Their outcomes and
causes remain explicit here; the task logs were consumed at final closeout.

Both current image families also passed a real API/SQLite offline delivery proof
at clean `6eefc82a`: schema 3/package 6, configured binding to the qualification
worker's actual native UUID, exact package write, actual clean-source
`pin_image_specialist.py`, atomic `publish_image_completion.py`, accepted then
idempotent refresh, confined byte/hash readback and terminal settlement. The queue
CLI was mocked offline: no native message or provider generation was sent. The
retained raster SHA-256 is
`42ec6a9e52e84a7df0e5ffe11bbd18f478f2774db16d08d105f602108d4af8e5`;
actual specialist skill hash is
`76c6097e2736396762c1133ba9f3dd08bc14968fa0be5a2a42f7f97b9f907d64`.
Frozen package JSON stayed unchanged. All pinned image inputs remain byte-identical
through the later test/documentation commits. Both exact disposable projects used
fresh ordinary deletion previews, supported permanent deletion and GET 404
readback after terminal completion. Their settled fixture roots were removed;
the manager read the compact actual pin/hash records before task consumption.
No UNKNOWN reservation was cleared or native-worker lease bypassed.

Retained exact smoke-passing wheel:
`.local/current-qualified-recovery/plotloom-0.1.0-py3-none-any.whl`, SHA-256
`c73df1a3212b4c3579952871a24ed92c469090e0654d2e6021f58b01138d2af0`.
The continuation rebuilt and smoked this same retained artifact; its hash stayed
identical. New-owner ZIP readback matches source and both removed barrels are
absent. The manager independently checked all 540 packaged source/static files.
R's native Python-tree identity remains
`8f23fafc3b991c3e3925628adcebcb28811dbd48f3f8a66ead2a3871cdcda8a1`;
P must derive its actual launch-environment profile rather than copy R's profile.

Execution used macOS 27.0.1 arm64 / Python 3.12.13. No Linux/full, external-provider
or owner creative-acceptance claim is made. Product/infrastructure/coordination
wall-time splits were not separately instrumented; actual verification elapsed
values are retained above and in the logs. Hosted CI was not requested or run and
is not a release blocker. There was no push, live-project change, provider/model/
settings/grant change, deployment or recovery refresh by this worker. Source is
released to the manager after this clean local-main documentation checkpoint for
quiet activation, preservation/readback and the single recovery refresh. The
worker's native ID remains `01a17632-5738-7db3-8733-d0a718042e75`.

## Manager activation and closeout — 2026-10-26

The manager collected the actual idle handoff `c9a6fade`, independently inspected
parity probes/results, the corrected fixture diffs and actual qualification
footers, and checked all 540 wheel package members against committed source
(520 Python files, nine YAML templates; removed barrels absent). Executable,
dependency and frontend inputs match the composite-qualified `a3d442bc` candidate;
the actual failed first-full input remains `1e56908e`, not a relabelled pass.
The retained schema/OpenAPI/route/ordered-gate baseline and integrated JSON were
byte-identical: 73 schemas, 189 routes, 20 final handler names and two complete
gate evaluations, with no observational exclusions. Independent source review
also verified the actual 17 winning handler bodies and moved definition ASTs.

Fresh live checks found eight projects, 26 selected playback ranges, 82 completed
plus three settled host attempts, zero queue/slot/validator rows and five revocation
guards. Project execution rows were 13 completed/three settled; runs cancelled or
handed off, batches approved/cancelled, and all 30 video jobs ingested. No healthy
work was cancelled to make a quiet window. Supported `manage.py stop` stopped the
backend and owned launchd `bootout` unloaded the bridge. The immediate bootout
observation briefly still showed the job; a subsequent native observation proved
the label and old PID absent, without a duplicate bootout or process signal.

All 672 project tables, 14 application tables and ten host tables (including the
SQLite internal sequence), 301 persistent data files, 439 host files and four
unique protected configuration/credential files match before shutdown, while
stopped and after activation. Settings and pool limits are included in those
data/file owners. SQLite comparisons used logical schema/rows, not WAL bytes.
Mac direct read-only project access could not open these databases; the stopped
comparison used a disposable no-network/read-only inspector from the existing
image with the exact mounts/user and SQLite `mode=ro`, then removed it. No
permission repair, data migration, reset or rollback was performed.

Data semantic/file aggregate SHA-256:
`fe25190c2d011b1c110ae72352b2dfe8a5aa38ea65902c4648a0aad66faced02`.
Host/protected-state aggregate SHA-256:
`cc5388187ac64924e1ea21d3e1f6f7ffd973f158787fa25d3d6a7d7b25653224`.

Only after stopped-state equality did P check out the source handoff. Supported
`manage.py start` rebuilt the affected service and recreated healthy backend
`27e2ce22e1dc`, replacing `9a911c7f2ea1`; the fresh owned bridge PID is 59312,
replacing 55189. All 26 new owners and three existing coordinators import from
P's actual source in Linux aarch64 Python 3.12.15; native Python-tree identity
matches qualified R's `8f23fafc…` exactly. This is installed-runtime readback,
not an unrun Linux full-suite claim.

An independent P builder used actual launchd tool discovery, unchanged checked
environment and persisted pool limits. Its complete profile equals the live v8
profile, and ordinary readiness is ready. Only `validatorHash` differs from the
previous installed profile. Prospective profile hash:
`413c7118c22654486fc6209f539d78ec1eba4bf60e95846824c95d53237db0a8`;
validator hash:
`fb9afe97ae179226c28bd9f39ca3fda7702005b1771ae22620ec552e8f628666`.
Existing frozen pins, reservations and revocations remain unchanged.

All 48 exact HTTP/media readbacks match before activation: directory including
archived projects, every project and video-job read, all 26 selected 32-byte
playback ranges, HTML and four UI assets. Local/private HTTPS health returns 200;
private HTTPS HTML matches local HTML. These prove availability and preservation,
not external generation, actual audio listening or owner creative acceptance.

The single `.local/current-qualified-recovery/manifest.json` is authoritative for
final source/submodule membership, composite-qualified revision and exact retained
wheel. Its source archive and wheel are checked against committed bytes/modes
before an atomic directory exchange, then checked again; the previous functional
package stays intact until the replacement is validated. No second archive or
data backup is retained. Final documentation synchronization changes no executable
inputs and requires identity/readiness checks rather than another service restart.
Consumed task scratch was 49 files/32,824,328 bytes. The actual idle worker and
read-only reviewers are archived; both implementation/review Relay routes are
removed. No push, CI, provider/settings/grant change or UNKNOWN clearing occurred.
