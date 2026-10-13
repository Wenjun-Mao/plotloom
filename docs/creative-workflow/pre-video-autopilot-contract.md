# Pre-video autopilot implementation contract

Accepted after attended P0 review, 2026-10-12. Authority: [ADR 0162](../adr/0162-pre-video-autopilot-authority.md). Outcome, ordered delivery and progress remain in the [roadmap](../roadmap/2026-10-12-pre-video-autopilot.md); executed evidence remains in the [single receipt](../verification/2026-10-12-pre-video-autopilot.md). This contract defines required behavior, not completion evidence.

### Ownership and typed records

| Owner | Durable contents and constraints |
|---|---|
| Run | One retained run per project; policy version/hash; exact Brief revision/hash/raw source projection; frozen Cast/Art styles, language/aspect/timing/topology settings; text/image task IDs; execution pins; image/job ceilings; state/CAS revision; lifecycle and controller claim; expected current closure; material bundle and human handoff IDs. No credentials or provider writes. |
| Checkpoint | Unique `(run, operation key)`; typed owner/stage/subject; exact original job/request/package/pin; prepared/sent/unknown/delivered/adopted status, dispatch/evidence hashes and CAS revision. References existing native owners, never another queue. |
| Decision | Immutable tagged actor/scope; run/policy/checkpoint; exact subject revision/hash and upstream closure; delivery/receipt evidence; selected asset IDs/hashes and rationale. Machine scope names source/text adoption, production installation, image generation or provisional selection; it contains no video scope. |
| Provisional frame | Exact shot/scene, canonical installation/revision/hash, v3 job/unit/request/delivery, one asset/hash/geometry and frozen character-reference mapping. No human VisualIntent or review judgment. |
| Human handoff | Immutable original material hash plus genuine reviewer/notes, per-frame intent/compatibility decisions, exact reference endorsement and resulting human approval/binding/SamePersonReview IDs. Distinct from machine material identity. |

All records are project-owned, registered in the native project-table inventory
and validated as current typed contracts on ordinary open/recovery. Same-project
FKs and unique operation keys enforce identity. Polymorphic job IDs additionally
require exact owner lookups; merely matching a string is insufficient.

ProductionUnit gains an exclusive nullable human-approval/machine-decision FK
union. Existing human approvals/bindings are unchanged; machine originals use the
same canonical gate/currentness rules through explicit image-only admission.
Machine provisional frames do not appear as current reviewed keyframes. Intent
uses `ai_adopted`; presentation keeps `reviewed=false` and carries a typed
machine-adoption reference with mutually exclusive states. Shared structural
binding/projecting never substitutes for semantic or visual review.

### Commands, currentness and restart

One application-owned serial reconciler uses existing global native role
reservations. Launch preflights feasible topology, explicit style consistency,
both configured distinct specialist roles and execution pins before admission.
It freezes a finite policy and exact Brief. Source projection is a trusted
synopsis of the saved title/synopsis, with explicit Brief revision/hash origin;
the current trimming behavior must not change those bytes or invent clearance.
Use a typed Brief-origin source contract validated against the exact current
Brief in trusted persistence; require nonblank content without trimming that
origin's title/synopsis. Normal manual source normalization remains explicit.
Do not use model construction/validator bypass, silently alter historical sources
or treat a client-supplied provenance object as evidence of a Brief binding.

Prepare/check/adopt are repository-bound typed commands. Their run/claim,
lifecycle and expected closure are checked under one lifecycle writer
transaction. Nested owner reads and writes reuse that same session; the existing
owner mutation plus machine decision and checkpoint commit/rollback together.
No filesystem publication or non-idempotent native send is placed inside the
SQLite transaction. Export reconciles the original prepared request; native
reservation/send/evidence remain owned by the existing transport. Crash after
publication or send checks that identity, never allocates a replacement.

Current closure includes Brief, source/outline/map/graph, all adopted Cast/Art/
Script/storyboard revisions, bridge intent/presentation/installation and canonical
gate inputs, selected references, all required frame jobs/assets/geometry,
execution bindings and relevant manual drafts. Receipt-only ingestion retains exact candidate delivery rows without updating
creative head projections. The same owners preserve their existing head updates
for manual and authorized text adoption; receipt scope cannot mutate accepted
revisions, selections or human facts. Receipt-only ingestion is not creative adoption. Manual mutations pause/take over before content changes;
late receipt reconciliation can retain evidence but cannot overwrite edits.
Controller commands must explicitly reconcile their expected closure after each
authorized mutation. A generic lifecycle write is not permission to dispatch.

Same-host restart acquires a valid controller claim, verifies open/active project
and every frozen binding, then reconciles original jobs before continuing. Claim
expiry/process loss never releases native reservations. Paused/cancelled runs
retain project/job ownership and evidence. Portable recovery permanently records
the captured run/checkpoint IDs: acknowledgement enables inspection/manual work,
not native continuation on the destination. Settings/pin/Brief drift withdraws
automatic authority; no new run is silently admitted.

### Complete image pack and truthful review

Required images are every adopted Cast subject plus every Art environment/prop
subject, followed by every unique installed filmed shot reachable over the union
of all complete routes. Enumerate canonical shot identity, not route occurrences;
route-only nodes have no shots. Reconcile exact counts against frozen ceilings
before images. One initial output per subject/shot is the package policy; extra
or unsupported outputs are disclosed delivery blockers, not automatic competing
candidate selection. Character references condition shot jobs; Art images remain
gallery materials. Every v3 shot has an exact mapping, including a valid empty
mapping for character-free shots; absent/malformed mappings cannot bypass review.

The existing limits are nine total image attachments and eight visible-character
judgments per frame. Preflight both before image dispatch; no character omission
or review-contract weakening. Technical image admission checks exact project/
subject/job/pin/hash, valid bytes, current dependencies and frozen role. Machine
selection records these facts with AI labels; it performs no aesthetic/identity
pass and creates no human VisualIntent.

Geometry policy v2: freeze centered-cover crop+resize recipe/runtime identity at
Start, explicitly disclosed to the creator. Prepare only accepted raw first-frame
originals whose observed aspect fails the exact Brief check. Reuse bounded decode
and `center_crop_png` (EXIF transpose, RGB, LANCZOS PNG) to frozen 720×1280,
1280×720 or 1024×1024. Matching-aspect originals stay unchanged. Retain raw bytes,
native prompts/manifest/mismatch/limitations. No stretch/pad/quality heuristics,
reroll, provider call, extra generation ceiling or synthetic native job.

Typed local checkpoint evidence binds project/run/policy/claim/shot, native source
candidate/job/request/delivery/execution, raw SHA/geometry, orientation/crop recipe/
runtime hash, managed derivative SHA/geometry and immutable preparation hash.
Geometry authority may publish this derivative; selection authority separately
adopts it. Retry/restart reconciles the same checkpoint. One strict single-hop
source resolver carries source v3 identity conditioning into every review,
selection/currentness and video-admission consumer; genuine human observations
bind the derivative bytes and lineage. Missing/tampered generated evidence refuses
instead of using imported-human fallback. Whole material closure includes typed
lineage, and final review shows original and derivative separately.

Managed content-addressed bytes use shared staged exclusive publication (ADR0162):
canonical paths are absent or complete after process death. Retry keeps the same
hash and validates any existing winner strictly. Private unpublished sibling stages
remain forensic outside snapshots; cleanup never sweeps or repairs canonical bytes.
New publication requires a writable same-filesystem outputs parent and supported
native exclusive rename, with fail-closed capability/durability errors.

Confined source/output bytes must remain available and SHA-identical. A staged
snapshot database is first validated against the frozen source asset home; after
copy, validate the destination's owned bytes. Preparation does not relax native
refinement currentness: recursively validate frozen ancestor context/authority
independently of old selection position, then admit only the exact currently
selected output with current human intent/approval.

Retained v1 packages/runs remain immutable and have no v2 permission. Their
original one-generative-adaptation evidence and queued reservations remain honest;
only original receipts reconcile after policy retirement. Ordinary manually
requested ImageGen adaptation remains its separate explicit workflow. The manager
owns fresh distinct native proof after final reviewed qualification.

At one consolidated review, collect real per-frame intent/compatibility inputs
and ordered per-character pass/fail/unassessable observations with attribution.
`unassessable + authorize + reason` is uncertain authorization, never pass.
The final lifecycle transaction revalidates the whole material hash, records
genuine storyboard approval, human intents/bindings and SamePersonReview inputs
through the current owners, then appends the handoff receipt. Fail/hold/missing
inputs roll back eligibility. Endorse original reference decisions rather than
reselecting them; identical bytes with a new reference ID stale frozen shot jobs.
Human rows appended by handoff are separate from the original material hash.
No video row, request, preview or provider call is created by confirmation.
After takeover, manually completed current material may receive a new exact human
handoff through this same bundle owner; preserve the old receipt. There is no
automatic regeneration, permanent manual lockout or silent reuse of stale review.

The append-only native `v2_autopilot_handoffs` owner retains the review bundle and
all human input/result IDs; the run points to its current receipt. The review
factory resolves adopted Cast subjects through their explicit consumer identity
mappings and binds displayed story, routes, script and shot directions to the
historical typed owners. Stored Python field names and public JSON aliases are
compared through those models, without weakening source binding.

An already active genuine approval over the same canonical revision is reused
as `existing_human`, preserving its original attribution; the new receipt and
observations remain distinct. An imported/earlier-contract replacement frame
uses tagged `human_current_material` reference comparisons under server-created
handoff authority. It neither claims generator reference conditioning nor changes
ordinary manual-only admission. Shared assets retain the existing one-current-
intent-per-role contract: each occurrence must supply the same authored intent.
Manual source edits drop the code-owned exact-Brief origin assertion while
retaining the original source revision. New machine dispatch remains forbidden.

### Video guard inventory

| Boundary | Required guard |
|---|---|
| `media_video_preparation.VideoJobPreparation.prepare_video_job` | Reject machine context and absent/stale whole handoff before prompt preview, compilation, freeze, row creation or accounting; `preview_only` is no exception. |
| `project_storage.project_video.ProjectVideoRepository.assert_submit_allowed` / `video_jobs.VideoJobService.submit` | Reject before any provider preflight, including the retained shared service mode. |
| `project_storage.project_video.ProjectVideoRepository.claim_video_dispatch` | Check before application reservation, then recheck under project transaction. |
| `persistence.project.media_video.VideoJobPersistence.claim_video_dispatch` | Independent shared-owner human/scope/current-handoff admission. |
| `media_video_currentness.VideoJobCurrentness` | Whole handoff closure currentness reaches segment/review/playback consumers; unrelated adopted subjects and other frames can withdraw eligibility. |
| `media_video_end_frames.VideoEndFrames.choose` | No machine video preparation scope. Optional end-frame generation stays excluded. |
| `media_tasks.GenericMediaTaskPersistence` | Retain current prohibition; no alternative video enqueue path. |

Do not block immutable history, manual cancellation or safe known-ID outcome
reconciliation when material eligibility is withdrawn. These retain uncertain
evidence and do not grant a new dispatch. Manual-only projects retain their
existing admission behavior when no autopilot run exists.

### Preserving transition and testable invariants

Freeze the complete preceding `schema_objects` tuple from `731cfdbf`, whose
canonical SHA-256 is `ea9facef83198e8b5abdd8693923f51add1376c0b416041dbfa245b92011b825`
(75 tables). This is a source baseline, not the actual installation layout.
The manager separately inventories actual targets. Independent raw manifested
folder inventory classifies prior/current/unsupported/error; ordinary discovery
skips unsupported folders and cannot establish a rollout inventory.

The named upgrader acquires installation dispatch quiescence and exclusive
project filesystem admission, validates confinement, exact layout/identity,
review JSON, integrity/FKs/secrets and unresolved native publications, then uses
one explicit SQLite transaction. Add typed tables and rebuild ProductionUnit's
authority constraint without changing old values, IDs, references or open/closed/
archived states. Verify exact current layout, integrity/FKs and logical row
fingerprints before commit. Unknown layout and ambiguous reservations fail
closed. Idempotent current-layout rerun performs no rewrite; crash rolls back.

Snapshots must include packages/reports from typed retained creative/branch/
intent/presentation job identities. Current snapshot payload enumeration omits
`outputs/creative-handoff/jobs`; P0 reproduced eight lost files and direct-restore
refusal. Enumerate confined expected job trees and verify bytes/hashes/secrets;
retain incomplete/rejected evidence honestly without treating it as terminal.
Do not recursively trust arbitrary `outputs/` or allow symlink/foreign entries.
Extend recovery operations, lifecycle busy/publication guards and permanent
portable dispatch prohibition for autopilot. Restore immediate-prior snapshots
only after original inventory/schema/integrity verification; upgrade a private
destination, validate, then publish. Original snapshot bytes/hashes stay intact. Missing completed package trees fail
closed in current folders. If a verified immediate-prior snapshot omitted those
trees, the destination transition records the exact omitted job/manifest hashes;
this omission provenance travels with subsequent snapshots and is never inferred
from a missing current tree.
The manager owns actual-layout/cutback proof and valued-folder mutation.

Before real image integration, deterministic fake deliveries must prove atomic
adopt/checkpoint rollback, repeated start/resume, double clients, exact source
projection, all-route unique-shot/subject inventory, failed gates, missing/stale/
foreign output, shared-role occupancy, unknown send, two failed criteria,
pause/cancel/late evidence, settings/pin drift, manual takeover, same-host restart,
portable recovery and synthetic preserving upgrade/snapshot rollback. Negative
video tests must prove no provider calls, application reservations, video rows or
fake human facts before handoff. Final review must refuse every stale/missing/
failed/held dependency and preserve uncertain authorization as uncertain.
Record ownership and browser shard registration with new collected tests;
broader full qualification stays manager-owned on the stable candidate.

### Complete review and browser observation

Review every selected character-reference view (primary and complementary),
retaining the original decision ID and ordered asset IDs, hashes and dimensions.
Endorsement must match the full set consumed by identity review. Current generated
frames must remain applicable to current reference decisions even after takeover;
changing a reference withdraws old generated frames and whole-pack eligibility.
Imported current material remains explicitly manual in the gallery.

After Start/control, read the durable run without relying on navigation or a
Brief revision change. Retry transient reads without resending commands, including
when command acknowledgment is uncertain. Unknown provenance must stay unknown
in headings, guides and metadata; only exact adopted revision/hash is AI-labelled.
Canonical membership and frozen identity/source bindings do not establish human
confirmation. Phase denotes admitted active work, including a prepared image job,
and commits atomically with preparation. Complete material inventory requires a
present current installation; early review/handoff refuses without creating facts.
Read-only admission disables review mutations even if its form is already open.
