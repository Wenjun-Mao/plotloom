# Pre-video autopilot · implementation plan

Status: owner-approved implementation, 2026-10-12. Baseline inspected:
`eea34ce1294c3f8aa48d77927847381f38a51f8a`.
Decision proposal: [ADR 0162](../adr/0162-pre-video-autopilot-authority.md).

## Outcome and agreed choices

After saving 项目简报, the creator can select `一键准备视频素材`. Plotloom
coordinates the existing specialists, adopts an automatic first pass, generates
initial images and stops at one consolidated human review before video work.
The owner chose automatic text adoption/reference selection, not a recurring
review pause before images. The owner also chose the existing installation as
the rollout target, only after isolated proof and a preservation-qualified
schema upgrade. The owner subsequently approved implementing this plan through
Relay Direct, including its isolated proof, preserving upgrade and quiet
activation, and granted standing creation of separate Codex tasks. The manager
may make necessary scoped design refinements and continue while the owner is
away, recording their rationale rather than waiting for routine approval.
Voice casting, videos, new providers and destructive valued-data changes remain
excluded. Software verification is not owner creative/product acceptance.

Root cause: current generation capabilities are separate manual workflows.
The browser/user coordinates prerequisites, deliveries, adoption and selection;
human review flags then authorize downstream operations. A button macro cannot
provide durable orchestration and would misrepresent AI decisions as human
approval. The correct layer is a durable run controller plus typed, scoped
decision authority, retaining each existing owner's binding/validation rules.

## First-release scope

- Start only on a fresh, saved Brief-only project with no existing source,
  accepted creative stages, manual drafts, production, media tasks or assets.
  Resume the same autopilot run is supported; converting an existing manual
  story or automatically rebuilding it is not. The normal manual path remains.
- Materialize the exact saved title/synopsis as `SourceMaterial(kind="synopsis")`,
  bound to Brief revision/hash and marked Brief-derived. Do not generate a new
  novel, infer ownership declarations, fetch external source or replace imports.
- Adopt validated outline, branches/map/graph, cast/art, complete Script and
  storyboard, then dramatic intent and presentation. Establish current production
  data using the shared bridge/gates under explicit pre-video machine authority.
- Generate one initial character identity reference per current adopted Cast
  character, including a character not depicted in the current shot set,
  one environment/prop reference per current Art subject, and one first-frame
  candidate per installed footage-bearing shot. Provisionally select each
  technically valid candidate, with its exact dependency binding and AI label.
  Cover every branch and ending; generate once per unique shot, not per route.
  Route-only choice nodes have no film or image requirement.
- Keep first-frame appearance/identity judgment provisional until human review.
  Structural validation and the generator's reference-use notes do not prove
  visual fidelity or same-person identity. Do not fabricate human review rows.
- Environment/prop reference images remain selected gallery materials in this
  MVP; current shot jobs consume their text, not those selected image bytes.
  Character references do condition identity-aware shot jobs. Do not imply Art
  image reuse/visual continuity that the current consumer does not establish.
- Optional end-frame generation, voice/audio casting, video prompt review,
  request preview/freezing, video jobs/submission, playback/export, new providers,
  provider configuration changes and automatic aesthetic regeneration are out.
  A later manual video workflow retains its provider/quality/duration/direction
  preflights; this is a material pack, not a pre-approved video request.

The scope limits above are the approved MVP defaults. They do not
relax Brief topology, language, aspect ratio, route-time or shot-count contracts.

## Creator experience

1. At saved Brief, show `一键准备视频素材` beside the manual continuation.
   Its launch panel names the project/Brief, configured specialists, frozen
   generation policy and ceilings. State: AI adopts a first pass; no videos.
   Starting is the one explicit run authorization, not a checkbox at every stage.
2. Present a compact progress view: story structure → creative text → production
   planning → reference images → shot frames → awaiting review. Show actual
   completed/required counts, the current task and actionable blockers; avoid
   fabricated overall percentages, completion ETAs or monetary cost estimates.
3. Navigation, browser close and reload do not own execution. Running projects
   show the same run status in both workbench views. A shared project claim and
   existing specialist occupancy prevent double starts/colleague collisions.
4. Pause stops new dispatch/adoption at a safe boundary; a sent job can finish
   and its receipt is retained. Cancel prevents further automatic adoption,
   never deletes results, kills a specialist or clears an uncertain reservation.
   Resume reconciles the original tasks before taking the next permitted step.
5. At `等待你审阅`, show readable whole-story/routes and original reports,
   character/reference thumbnails, scene-grouped shot frames, AI choices,
   counts and disclosed quality/feature limitations. Detail and manual editing
   remain available; this is not another long raw-text checklist.
6. A single `确认素材，进入视频制作` action records one human handoff against
   the exact completed bundle and returns to the existing manual video controls.
   It does not prepare, preview, freeze, enqueue or send a video. Actual human
   frame/identity judgments must be recorded through a deliberately compatible
   owner: do not equate a whole-pack button with synthetic SamePersonReview facts.

Human takeover pauses the run. An edit withdraws affected completion/authority
through existing currentness rules; no background callback overwrites edits.
The first release does not autonomously regenerate edited/rejected packs.
The owner can continue manually, retaining all candidate/decision history.

## Reused pipeline and new owners

| Order | Operation | Existing authoritative seam |
|---|---|---|
| 1 | Exact Brief-derived Source | Brief/source contracts and source outline mutations |
| 2 | Outline, branches, map/graph adoption/application | Native creative packages, branch binder, source graph admission |
| 3 | Cast, Art, Script, storyboard adoption | Stage repositories and unchanged frozen delivery contracts |
| 4 | Intent, presentation, canonical installation | Native bridge tasks, span binder, production bridge/gates |
| 5 | Character and Art subject image studies/selections | Existing image proposal, exchange, managed asset and selection owners |
| 6 | All required identity-aware first frames | v3 original image jobs, managed assets, VisualIntent and shot bindings |
| 7 | Completed pack and human handoff | New exact-bundle authority, compatible human identity review owner |

Use one project-owned content graph and canonical installation, not a parallel
autopilot canon. Specialists remain delivery-only: their assignments still cannot
alter project state, choices or approval. The trusted controller adopts validated
outputs under the user's run authority and records machine provenance separately.

New cohesive modules own typed run contracts, project persistence/checkpoints,
decision scope, controller/reconciliation, API and progress/review UI. Run records
link existing job/package/pin/receipt identities; they do not duplicate the
specialist queue or store credentials. Do not hide state in bridge-intent tables,
approval notes, generic drafts or unrelated JSON to evade schema admission.

Decisions bind actor/authority, run and policy version, exact subject revision/
hash, upstream closure, job/delivery evidence, selected assets and rationale.
The authorization permits source/text adoption, production-data installation,
image generation and provisional reference/frame selection only. Every downstream
operation must request its permitted scope server-side. Current manual semantics
remain human-owned. Machine authority must be rejected by every video request,
preview/freeze/preparation/dispatch path, even if the browser calls one directly.

## Persistence and safe rollout

Current `project_storage/current_schema.py` compares the complete SQLite layout
exactly. New run/decision tables or columns affect existing project admission
even though autopilot runs only on new projects. Fresh-project-only UI gating is
not a preservation strategy; full/application Alembic is not the folder upgrade.

Design one explicit transition from the immediately preceding known layout,
under idle project/installation lifecycle admission. Verify the exact schema and
project identity before a transactional change; refuse unknown layouts. Preserve
all valued content, revision/selection history, assets, frozen packages, pins,
dispatch receipts, specialist configuration and open/closed state. Do not invent
historical AI decisions or retroactively relabel human approvals. No reset,
general historical compatibility adapter or silent upgrade on ordinary reads.

Prove preservation first on synthetic current-layout folders. Snapshot/restore
must inventory the new records and integrity/foreign-key checks. An immediate-
prior snapshot may enter an explicitly upgraded restore destination only after
its original integrity is verified; original snapshot bytes remain unchanged.
Unsupported older snapshots retain a clear refusal. Do not erase snapshot/restore
as a shortcut. The implementation approval covers necessary actual-installation
inspection and the qualified preserving upgrade/idle activation. It does not
authorize deletion/reset of valued projects, broad historical migration or
credential/provider changes. Inspect and record actual targets before mutation.

Before any activation, inventory actual folders/layouts and unresolved native
publications safely, stop new dispatch at an idle checkpoint, and establish a
tested operator recovery/cutback procedure for a failed upgrade. This scoped
upgrade safety procedure is not a product-wide automatic-backup subsystem.

## Failure, recovery and resource policy

- Freeze Brief/settings/specialist bindings/execution identity and finite image/
  job ceilings at launch. Preflight source/topology/style feasibility and configured
  native roles. Resolve an explicit contradiction rather than silently changing
  realism/animation, portrait/landscape, route time or branch structure.
- Exact subject/shot counts become available after text planning. Reconcile them
  against the launch ceiling before images; stop with a clear capacity decision
  if exceeded. No omitted branches, automatic ceiling increase or paid fallback.
  First release requests one initial image per required subject/shot, not competing
  candidate batches or an open-ended “generate until good” loop.
- Preserve current canonical validators, CAS, section bindings, timing/gate
  checks, presentation coverage and native tool/pin/hash evidence. Disclosed
  unresolved facts or a failed required gate block adoption rather than creating
  guessed placeholders. Image geometry/identity attachments must satisfy current
  admission; any existing supported adaptation requires its own counted job.
- Use an application-owned durable worker/reconciler, not browser timers,
  Playwright button automation, model-driven polling or a Codex heartbeat.
  Serialize against the existing globally shared native role reservations;
  another project's task is waiting state, not permission to rebind an assistant.
- Make reserve/prepare/send/check/adopt checkpoints idempotent and recoverable.
  Repeated Start/Resume returns the same admitted run. Crash-after-send, lost ACK,
  wake failure and unknown outcome reconcile the same job; never resend or create
  replacements to bypass ambiguity. Partial/invalid delivery is not terminal.
- On restart, reconcile durable state first. Continuing previously admitted work
  needs a valid run/lifecycle claim and exact frozen authority; restart does not
  constitute a new Start. Portable restored data requires existing recovery
  acknowledgement and cannot silently resume native dispatch on another host.
- Known failures may expose bounded retry through the original job's supported
  policy; unknown outcomes cannot. After two unsuccessful attempts at the same
  criterion, preserve evidence and reassess. No arbitrary speculative retry stack.
- Concurrent edits, source changes, settings/execution-pin drift or stale assets
  pause/withdraw the affected run. Cancelled/stale late deliveries remain evidence
  without reacquiring selection or production eligibility.

## Ordered deliverables

### P0 — Contract and feasibility proof, before implementation depends on it

Review/accept ADR 0162. Inventory the actor/scope consumers and every video
entrypoint. Resolve the exact machine decision representation and final human
identity/bundle handoff semantics; define schema transition and restart admission.
Prove whether one technically validated initial candidate can be adopted under
explicit provisional authority without a new visual adjudication subsystem.
Do not promise a semantic quality pass. Verify first-frame and reference attachment
capacity (current total maximum is nine), Brief-source projection and all-route
shot enumeration. If these require a material scope change, revise this plan first.

### P1 — Durable run authority and preservation

Implement typed project-owned run/decision/checkpoint schema and API; safe known-
layout upgrade, snapshot/recovery/lifecycle inventory; explicit pre-video scopes
and negative video guards. Add exact launch/source binding and project/run claims.
Manual workflows must retain current behavior. No specialist generation yet.

### P2 — Native text orchestration and installation

Extract/reuse cohesive prepare/send/check/adopt commands from existing owners,
without self-HTTP/UI macros. Run the frozen chain through all routes, intent and
presentation; install production data with passing gates and AI-adopted provenance.
Test the full chain with deterministic fake deliveries, including interrupted
adoption and source/conflict failures, before paid/native image integration.

### P3 — Initial image/material pack

Coordinate existing identity/Art proposals and v3 shot jobs, ingest exact deliveries
and select provisionally. Build the complete required-subject/shot inventory and
bundle hash, with no route-only or duplicate-route images. Qualify resource limits,
unknown outcomes, pause/cancel, restart and user takeover on disposable fixtures.
Do not add an Art-image production consumer or an optional end-frame generator.

### P4 — Compact progress and final review

Add the saved-Brief launch and persistent progress view, scene-grouped review,
AI labels/limitations and exact human handoff. Connect both workbench views and
normal editors without replacing them. Human identity review facts and their
per-shot outcome must remain truthful; unassessable identity cannot become pass.
The single review boundary may include real per-frame judgments without stopping
the prior automatic run at every stage. No video request is created by confirmation.

### P5 — Qualification, publication and approved quiet activation

One serial source owner implements; bounded independent contract/pixel review
precedes final gates. Run quick/focused/module checks while developing, then the
required stable-candidate local full gate for cross-layer changes, deterministic
asset parity and wheel checks. Update native ownership and browser shard coverage
without reducing the unfiltered union. CI remains manual: no hosted dispatch
without separate owner direction, and no claim of hosted exact-SHA qualification.

Use an isolated installation with fresh disposable QA projects for the smallest
real native text/ImageGen proof only after generation authority is explicit for
that implementation run. No H3 video generation is needed. Record fake versus
real delivery/UI evidence, actual submissions and available usage without invention.
Publish verified implementation per repository policy; activate normal8841 only
after authorized actual-layout preservation checks and a quiet checkpoint. Verify
both normal and Tailscale endpoints, static/runtime identity, retained story and
settings integrity and the final pre-video lock. Operator recovery must be proven
before changing actual valued folders. Owner product acceptance remains separate.

## Acceptance and stopping conditions

The isolated happy path starts at one saved Brief and reaches `等待你审阅`
without manual stage confirmations. Every required branch/ending remains in
the readable Script/graph and every unique filmed shot has a current provisional
first frame. All adopters are AI-labeled until actual human review. No voice,
video preparation/preview/job/dispatch or provider-setting write occurs.

Fault coverage includes double start/two clients, shared-role occupancy,
prepare/send/check/adopt crashes, unknown ACK, late cancelled/stale output,
service restart, portable restore, manual edits, insufficient image ceiling,
portrait geometry, missing/foreign/stale image and execution-pin drift. Confirm
immutable receipts remain and no duplicated generation or adoption is performed.

Exact human handoff is refused when any bundle dependency is missing, stale,
unreviewed where required, failed or held. Preserve the existing explicit human
`unassessable + authorize + reason` path as uncertain authorization, never as an
identity pass; autopilot itself cannot grant that exception. A valid handoff
changes eligibility only, without sending videos. Editing any dependency
withdraws that eligibility.
Manual-only projects remain usable before/after the known-layout transition;
existing story/assets/packages/receipts are preserved, not copied into QA claims.

An independent GPT-6.1 Sol / High planning review identified two ambiguities:
reference counts now explicitly include every adopted Cast character, and final
review preserves the existing human authorize-with-uncertainty contract without
mislabeling it pass. This is design review, not executable qualification.

The planning turn performed documentation work only. The later explicit launch
approval covers source/tests, isolated real text/ImageGen proof, installation
inspection/preserving upgrade/recovery, verified commit/push and eventual idle
activation. No hosted CI, voice task or video operation is included. The manager
may refine this plan to resolve demonstrated implementation/acceptance blockers
within pre-video autopilot, retaining all hard authority/preservation boundaries.

## Implementation coordination

Manager: `01a04525-e907-7630-9640-78790d69e8ae` (host-provided identity).
One Relay-registered source owner works on `codex/pre-video-autopilot` in
`/Users/wjmao/projects/HU/plotloom-worktrees/pre-video-autopilot`. This isolation
prevents partial schema/code/static changes from reaching the normal app's
read-only checkout mount. The manager does not edit concurrently with that owner.
P0 resolves feasibility before dependent source work; checkpoint blockers and
material scoped decisions use the same worker/manager route. The source owner
delivers the stable candidate and focused evidence; the manager owns independent
review, final combined qualification, main integration and approved operational
proof/activation. Worktree/task cleanup remains manager-owned after final review.

## P0 implementation checkpoint

Status: P0 approved; P1 authority/schema/recovery checkpoint implemented and
focused-verified in the isolated source worktree. The manager confirmed the
preservation refinement, separate machine/provisional owners and retained
reference identities, exact raw Brief provenance and one counted adaptation are
in scope. P2 orchestration, P3 complete images and P4 UI/human handoff remain
required before a stable candidate can be delivered.
Evidence is kept in [one receipt](../verification/2026-10-12-pre-video-autopilot.md).

The accepted [implementation contract](../creative-workflow/pre-video-autopilot-contract.md) owns the typed authority, transaction, image/geometry, human handoff, video guards and preserving transition invariants. P0 was approved to continue P1–P4 after manager rerun and independent review; see the single receipt.

## Source entrypoints

P2 source checkpoint implements the durable native text chain and canonical
installation with fake-delivery focused evidence in the single receipt. P3's
complete images and P4's truthful consolidated human review remain required;
this text checkpoint does not finish the automatic material run.

P3 source checkpoint reaches a complete typed provisional material bundle with
fake native images and all-route/all-subject evidence. Capacity, cancellation,
partial-publication, restart and one adaptation boundaries are recorded in the
same receipt. P4's consolidated genuine human review/UI remains required, followed
by the manager-owned P5 stable full/native/preservation and activation proof.

P4 source candidate adds an immutable human handoff owner, current-material
takeover review and compact launch/progress/gallery/frame UI. Scoped source,
browser, frontend, deterministic static and pixel evidence are recorded in the
single receipt; these do not establish full/native/release or creative acceptance.

The owner additionally requires a careful walkthrough of every touched feature
path after implementation and before activation. This is a manager-owned P5 gate:
use the [touched-path map](../verification/2026-10-12-pre-video-autopilot/touched-path-walkthrough.md)
on disposable QA, label deterministic fault fixtures separately from real native
transport, inspect readability/accessibility and persisted evidence, and preserve
valued stories/settings. Voice/video preparation, preview, enqueue, dispatch and
provider changes remain excluded. This deepens verification within the approved
outcome and does not introduce another source writer or unrelated redesign.

Owner follow-up explicitly requires fixing every diagnosed in-scope walkthrough
issue before activation. Keep the same source owner available: walkthrough →
root-cause contract/source correction → failed and downstream affected checks →
recheck affected walkthrough paths → preserving rollout/activation only after
all required gates pass. Reuse unaffected qualification evidence; no assertion
weakening, bypass or optional redesign. Real generated material remains awaiting
the owner's actual human review; disposable protocol judgments are labelled
software fixtures and cannot establish creative acceptance.

- Source/graph: `brief_contracts.py`, `source_outline_contracts.py`,
  `persistence/project/source_outline_mutations.py`, `source_graph_admission.py`.
- Creative owners: `cast.py`, `art.py`, `script.py`, `storyboard_review.py`,
  `api/project_folder_specialists.py` and frozen exchange/transport owners.
- Decisions: `production_bridge.py`, `production_presentation.py`, `approvals.py`,
  `media_admission.py`, `media_keyframes.py`, `media_same_person_reviews.py`,
  reference selection owners and all video admission consumers.
- Persistence: new cohesive autopilot schema/owner; `persistence/schema/__init__.py`,
  `project_storage/current_schema.py`, `project_handle.py`, `recovery_validation.py`
  and existing project lifecycle/snapshot/recovery owners.
- UI: `frontend/src/pages/BriefPage.tsx`, new progress/review
  components, workspace routes/types/API and recommended-workflow guidance.
- Evidence: extend the existing creator lifecycle acceptance playbook for this
  scope and keep one dated receipt; do not create competing acceptance ledgers.


## Ordered P5 continuation · owner-approved geometry release

First commit the independently reviewed frontend action-ownership and delivery
disclosure checkpoint with scoped frontend qualification in the single receipt.
Then the same source owner proceeds directly to the separately approved geometry
slice: freeze a new centered crop-and-resize policy at Start, retain original
bytes and native evidence, record typed local derivative lineage and carry that
lineage through every material/currentness/human/video-admission consumer.
Amend ADR 0162 and the accepted contract before implementation. The old frozen
4817 native run and its one attempted generative adaptation remain untouched;
new policy applies only to fresh runs. No weakening of aspect admission, fake
native jobs, extra generation, provider/video/voice work or owner acceptance.
Stop after a reviewed committed geometry checkpoint; the manager owns attended
review and one fresh full gate, fresh isolated native proof and preservation.


The geometry source checkpoint implements the approved v2 centered preparation
under existing typed checkpoint/decision/frame owners without a SQL layout change.
The single-hop derivative resolver, explicit snapshot source-root validation and
recursive native refinement dependency contract carry currentness into human
review and downstream admission. Source checks remain focused; old backend/full
evidence cannot qualify these changed executable inputs. After the reviewed clean
commit, hold source/dependency/config writes and test bodies for manager contract
review and one fresh exact-candidate full. New isolated native proof uses distinct
project/job/specialist identities; old paused 4817 data remains immutable. The
manager-qualified97 completed fresh native proof; its three diagnosed provenance,
early-review readiness and active-image-phase findings are released for bounded
repair, focused checks and independent review, then commit/hold for fresh full and
actual-path recheck. Native97 evidence remains bound to97; owner acceptance is pending.
