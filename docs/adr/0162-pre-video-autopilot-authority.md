# 0162 — Pre-video autopilot decisions are machine-owned and scoped

Status: accepted for implementation, 2026-10-12; source implementation present, release gates pending. The owner selected automatic
first-pass adoption with one final human review, and existing-app rollout after
isolated proof, then approved implementing the [plan](../roadmap/2026-10-12-pre-video-autopilot.md)
through Relay Direct with scoped design discretion. Its operational gates and
exclusions remain explicit; acceptance of this decision is not completion proof.

## Problem

Current specialists return candidates, while the creator separately adopts
upstream content, installs production and selects references/keyframes. Intent
saves claim `author_saved`, presentation confirmation claims `reviewed`, the
approval ledger is human-owned, and those approvals can admit videos. Chaining
the endpoints or using reviewer="AI" would falsely record human review and give
a pre-video run more authority than its launch granted.

The feature also needs durable run/checkpoint identity. Current project-folder
admission compares the exact SQLite layout, so adding typed records requires
an explicit preserving schema transition even if new runs start on new projects.

## Decision

Keep one project-owned content/canonical authority. Add cohesive typed autopilot
run, checkpoint and decision records that link existing frozen jobs, packages,
execution pins and receipts. Existing specialists remain delivery-only; a trusted
controller adopts validated output under an exact user-authorized run policy.
Do not add a parallel canon, another specialist queue or disguised state blobs.

Represent machine adoption separately from human review. Bind actor, run/policy,
artifact revision/hash, upstream closure, delivery and selected assets. Use
operation scopes at shared domain admission: pre-video authority can adopt text,
install production data, generate images and select working references/frames.
It cannot prepare, preview, freeze, enqueue or dispatch a video. Every consumer
must check scope server-side; UI hiding and reviewer strings are not authority.
Manual mode retains its author-owned confirmation semantics (ADRs 0100/0161).

The completed material pack binds the full current dependency closure and every
required unique footage shot across all branches. AI-adopted material is labeled
and inspectable, not claimed semantically or visually human-approved. A separate
human handoff binds that exact bundle and records genuine required identity/frame
judgments through a deliberately compatible owner. It must not synthesize human
SamePersonReview rows from a generic whole-pack acknowledgement. Confirmation
only changes eligibility for later manual video work; no video is created.

Resume/recovery reconcile existing job identities and exact launch authority
before continuing. Unknown dispatch and cancellation never release leases or
authorize replacements without existing terminal proof. User edits/takeover
withdraw affected completion rather than being overwritten by late callbacks.

Provide a named explicit upgrade from the immediately preceding known project
layout, qualified on disposable folders before valued installation use. Preserve
all rows/assets/packages/receipts and operational states; no history backfill or
reset. Ordinary reads retain exact-layout rejection. Restoring an immediate-prior
snapshot may upgrade a verified destination, never mutate its original bytes.
Unknown older schemas remain refused; this is not general historical support.

## Alternatives and consequences

- A UI macro leaves execution browser-owned, mislabels human decisions and cannot
  safely recover unknown sends. It is rejected.
- A parallel run-owned canon duplicates stage/currentness/asset installation
  machinery without an established requirement. It is rejected for this MVP.
- Saving run state in unrelated JSON avoids schema work by hiding ownership and
  portability, not by satisfying durability. It is rejected.
- Fully autonomous video generation is a different authority/cost scope and is
  excluded, as are voice casting and new provider integrations.

The first release uses one technically validated initial image per subject/shot,
provisionally adopted without an invented visual-quality pass. Optional ending
frames and Art-image conditioning of shot jobs remain excluded; selected Art
images are gallery materials under ADR 0078. Known constraints and judgments
remain visible in the final human review. Required frame/identity semantics,
typed scope propagation, schema transition and lifecycle recovery must be settled
in plan P0 before dependent implementation; no broad bypasses are permitted.

## P0 implementation contract · approved 2026-10-12

Attended manager review approved the [implementation contract](../creative-workflow/pre-video-autopilot-contract.md), informed by independent authority/preservation reviews and disposable baseline probes in the [single receipt](../verification/2026-10-12-pre-video-autopilot.md). Detailed ownership and guard invariants live there; ordered delivery remains in the roadmap.

Machine authority remains separate from human approvals/review facts. Production units use an exclusive authority union, and provisional frames retain immutable provenance. The human handoff endorses original reference IDs and records genuine per-frame judgments atomically, without video operations. Manual takeover can later create a fresh human handoff from completed current material.

P0 reproduced three contract gaps: source trimming conflicts with exact saved-Brief projection; reviewed-only adaptation sources cannot support machine-provisional geometry; and snapshot inventory omits retained native creative packages/reports. Resolve these at their source, image-authority and evidence-inventory owners. Permit one counted adaptation, preserving a mismatched original as evidence; incompatible second output blocks. Do not fake review, implicitly crop or infer native geometry capability.

Freeze the immediately prior 75-table exact layout (canonical hash `ea9facef83198e8b5abdd8693923f51add1376c0b416041dbfa245b92011b825`) in the installed project-storage package before metadata changes. Actual targets require independent raw-layout inventory; catalog discovery is insufficient. Preserve prior rows and original snapshot bytes; portable captured native identities never regain dispatch authority through acknowledgement.

This decision is approved implementation authority, not delivered behavior, real generation proof or preserving-upgrade qualification.

Receipt reconciliation uses the existing candidate owners but leaves creative
head projections unchanged. It may retain exact job/manifest/output evidence;
accepted revisions, reference selections and human facts require their distinct
command scopes. Checkpoint updates use CAS and monotonic dispatch transitions.


### P2 complete-intent bound refinement

A disposable valid two-choice/three-ending/join chain requires 66 exact scene and
beat intent targets. Its context is 44,914 bytes, but the prior shared 64-target
limit rejected preparation after six successful source jobs. Raise the shared
current intent target bound to 128 while retaining the 60,000 canonical-context byte bound and
800 characters per target. Trusted code still owns every target ID, source binding
and exact cardinality; models own suggestion text only. The primary native
contract, API response schema, binder and validator share this finite ceiling.
Do not drop targets, split the frozen job or special-case autopilot. Existing
frozen job response min/max counts and source/pin identities are retained, not
rewritten. General-route and over-ceiling tests guard this change.

Atomic initial package publication prevents a prepared job from becoming
unexportable after a partial write. Serialize publication with a confined empty
per-job filesystem lock, stage request-derived bytes privately, fsync and rename
once. Only identified unpublished static subsets that match the exact frozen
recipe are disposable. Published packages/deliveries are never repaired or
removed. Recovery preserves the original package bytes and the harmless lock;
this publication lock grants no native dispatch or continuation authority.

The application controller isolates known filesystem/database failures by project;
it preserves frozen operation identities and native reservations, blocks safely
through a fresh session, and continues unrelated projects. When failure recording
is unavailable, quarantine that project until the blocker is durable. Known
controller lease/discovery refusals remain supervised and inspectable. A restart
or Resume never interprets storage failure as proof that dispatch did not occur.

### P3 material and execution admission

Enumerate every adopted Cast/Art subject and unique reachable filmed shot before
images; bind that inventory and the completed bundle to historical native owners.
Freeze original requested geometry and exact image execution revision/skill in
the request. One tagged machine-provisional source may receive one counted
adaptation; no human intent/review fields are borrowed or fabricated.

Receipt state is transport evidence. Explicit image/reference cancellation is
an authority withdrawal and participates in the material closure independently
of other job status changes. Receipt scope may retain stopped-job evidence, but
selection and completed-bundle admission separately recheck current applicability.
Run Cancel/Takeover preserves delivered proposals instead of invoking cancellation
owners that only accept unfinished states. Existing partial delivery/execution
publication blocks a new native send at its final admission boundary; lack of
completion cannot establish lack of execution. Retained candidate asset/hash/
filename/role must match the exact original manifest output.

Image static packages use descriptor-confined private publication, fsync and one
rename. Reclaim only named unpublished request-derived subsets/prefixes, after
verifying their whole recipe; never repair published packages or deliveries.
Atomic exclusive lock-file creation followed by reopening the existing no-follow
file closes the observed concurrent-creation refusal. This lock owns static
publication, not native dispatch. Split package projection from the oversized
delivery exchange and keep all executable publication owners in the native pin.

### P4 human review owner

#### Owner-approved creator confirmation refinement · 2026-10-13

The mandatory typed name and whole-pack essay duplicated the actual reference,
frame and character decisions. A typed name is not authentication. The owner
approved removing the name and making the overall comment optional. A new
`pre-video.handoff.v2` receipt records explicit `unnamed_creator` attribution,
the exact material bundle and individual decisions; it never invents a person
or a positive review statement. Blank/omitted comments are absent; nonblank
comments retain their authored bytes. No authenticated actor is currently known.

Shared approval and SamePerson writers accept a typed unnamed-confirmation
value only under trusted HANDOFF scope. The existing non-null reviewer columns
encode this as the empty string (absence of a name, never a placeholder person).
Read projections explicitly label `unnamed_creator`; ordinary-open/recovery
requires those unnamed facts to belong to a validated v2 handoff receipt.
Manual review requests still require their existing nonblank reviewer strings.
This avoids SQL layout changes and a preserving upgrade unrelated to the outcome.
Nulling columns, inserting a guessed name, and weakening shared manual validation
are rejected. Existing named approval attribution is retained when reused.

Retained `pre-video.handoff.v1` receipts have a separate read-only typed parser;
their observations, rows, packages and hashes are never rewritten. New requests
cannot submit a reviewer or machine authority. Exact endorsements, actual frame
and character observations, uncertainty decisions, currentness/CAS, atomicity
and video denial remain required. Confirmation saves choices and enables later
manual video work; closing the dialog does not navigate or dispatch a video.

The current automatic bundle is machine evidence and cannot grant video authority.
A separate append-only `v2_autopilot_handoffs` owner retains the exact current
review bundle, human attribution, explicit reference endorsements, authored
frame intent/compatibility and ordered SamePerson observations, together with
native approval, intent, binding and review IDs. One lifecycle transaction checks
currentness and creates all facts, or rolls back. A run stores only the current
receipt pointer; edits withdraw eligibility without changing historical receipts.
The unshipped migration and exact named prior-layout transition include this
owner; no intermediate development layout is supported or silently upgraded.

After takeover, the review factory reads current canonical subjects/references
and current manually reviewed bindings, rather than requiring the old automatic
freeze. Imported or earlier-contract frames use an explicitly tagged human
comparison mapping at the SamePerson owner under handoff authority; it makes no
generator-conditioning claim and changes no ordinary manual-only admission.
Original AI reference decisions and production-unit authority remain unchanged.
No handoff operation calls video preparation, preview, freezing or dispatch.

A later handoff over the same approved canonical revision reuses its exact active
human approval, labelled `existing_human`, while creating a fresh material receipt
and observations. Native approval forbids consecutive duplicate approvals; fake
revocation/approval churn would misstate the author's decision history. Original
approval attribution is retained, separate from the new handoff's unnamed creator confirmation.

The review receipt retains the complete ordered asset set of each selected
character-reference decision: primary plus up to two complementary views, with
original hashes and dimensions. One endorsement covers that exact original
decision, matching the SamePerson consumer; displaying only its primary image
would authorize unseen material. Current review also checks generated-frame
applicability against current references after takeover. Reselection withdraws
old generated frames and eligibility, without rewriting historical receipts.

Browser observation reconciles every command response, including an uncertain
response, through a fresh durable read. Transient read failures retry observation
only; they never replay Start or control commands. An uncertain handoff response
rereads the durable run; confirmation stays disabled until that read succeeds.
Close a committed handoff form, retain authored inputs when it did not commit,
and never replay confirmation automatically. Completed runs remain observed
while their workspace is open: reference/frame changes can withdraw eligibility
without changing Brief. Unreadable currentness hides the manual video entrance.
Missing or failed provenance is labelled unknown across accepted-stage headers
and guidance, including the accepted outline candidate header. Exact adopted
revision/hash establishes AI origin; confirmed manual semantics require known
current provenance. Read-only state reaches an already-open human review form.

### P5 startup admission correction

Controller discovery and failure recording first inspect without creating locks
or changing SQLite journal mode. Only open, active folders with an executable
autopilot identity can acquire editing admission; recheck those facts under the
opened handle before claiming or recording failure. Closed/manual-only folders
remain observation-only, including startup. Catching closed admission after an
editable open is too late because lease creation already changes the folder.

Compose the application-owned controller/lifespan at the project-folder app root.
Generic specialist route registration requires only its declared route owners;
it does not implicitly require application storage or start a background service.
Use native-queue-only transport mocks so real Git pin checks remain authoritative.
These corrections preserve strict closed-folder, frozen-pin and lock-order tests;
no tolerance, platform exception or cleanup bypass is introduced.

Controller eligibility is a named persistence-owned check over the stored run
state and permanent portable exclusion. A completed `handed_off` identity stays
terminal even if independent material drift makes its UI view `stale`; the claim
owner also refuses it. Paused, cancelled and taken-over runs retain existing
receipt-only reconciliation. Ordinary human reference/frame edits already persist
takeover; the independent closure-drift regression is an explicitly injected
fault over a real completed fixture pack, not evidence of UI redispatch.

Captured portable identity refusal precedes local completed-handoff refusal at
the claim owner. Recovery's permanent no-resumption contract remains the dominant
reason even when the captured run had completed human review. Both states still
deny claims; the original portable diagnostic and regression remain unchanged.

### P5 observation and runtime ownership

An unchanged Brief save may delete its exact durable draft without changing the
canonical Brief revision. The authoring persistence owner publishes a
project-bound observation version only after validating that draft-consumption
receipt and current workspace operation. Launch admission uses that version and
the Brief revision to reread the server, aborting superseded reads. Dirty/saving
timing, optimistic eligibility, revision bumps, editor remounts and command replay
are rejected: admission belongs to the server and cleanup belongs to authoring.

Serialize controller start/close and worker publication under a lifecycle lock;
serialize exact descriptor acquisition/release separately. The worker's final
release cannot need the lifecycle lock while close joins it. Overlapping app
lifespans are runtime owners: the first starts the worker and the final owner
stops it. Direct start/close and no-thread lease cleanup retain their semantics.
Do not hide descriptor errors or substitute a timed join for owned shutdown.

Passive controller discovery/inspection holds real shared project OS leases.
Per-project in-process arbitration lets admitted passive observations finish
before an explicit exclusive transition and blocks new passive admission while
that transition is pending. Ordinary foreground handles and native durable work
still refuse unsafe transitions through the existing OS/domain admission. This
adds no retries, fixed sleeps, lockless SQLite reads, persistent files or weaker
cross-process locks. Registry lookup stays manifest-only so transition admission
does not recursively create another passive observation.

Event-gated regressions prove worker publication, exact single descriptor close,
overlapping lifespans, real discovery/inspection holders, late passive blocking
and foreground refusal. Closed-WAL/retained-lock and DELETE/absent-lock byte
preservation remain separate cases. Source-bound review text retains its frozen
Script revision and review hash even after the current Script changes.

### P5 acknowledged draft mutations invalidate admission observation

Actual walkthrough after passing full qualification showed a remaining owner
gap: an edit/revert could leave a durable Brief draft while payload equality
cleared `dirty`, re-enabling a launch backed by an older eligible GET. A successful
PUT receipt changes admission even when canonical Brief and local payload match.

Use the shared project/operation-bound authoring observation callback for owned
durable PUT acknowledgments, exact canonical consumption, recovery and close-time
discard, and graph recovery performed by this authoring owner. Publish only for
the current operation and matching receipt identity; failed, mismatched and
superseded receipts do not advance the current workspace observation. Local-only
discard and server-buffer restoration have no mutation event; restoration that
schedules a PUT uses the normal acknowledgment owner. Creating a different project
already changes read identity.

Launch displays eligibility only from a server response bound to its current
project/Brief/observation key. A newer mutation makes the older result unknown
immediately while the fresh GET is pending; aborted superseded GETs cannot restore
it. Dirty/saving fields retain editor/action semantics but cannot establish read
currentness. Preserve the mounted form, authored settings and unchanged canonical
revision through withdrawal and exact no-op cleanup. No polling or command replay
is added. This frontend observation correction leaves server admission, mutation
requests and persistence contracts unchanged.

### P5 automatic guidance and immutable delivery disclosure

Native97 exposed three current-contract gaps. Canonical accepted status/membership
does not prove human review: reference headings use exact adoption provenance,
while frozen identity/source metadata describes bindings neutrally. Shared inventory
readiness requires a present current installation; incomplete review/handoff reads
refuse through the existing domain error without mutation. Phase describes admitted
active work: commit image phase with its prepared checkpoint in the same transaction,
before dispatch/selection. Failed preparation cannot advance phase. No schema,
authority, payload, selection or dispatch-identity changes are implied.

The actual source/characters walkthrough showed dominant manual Next instructions
alongside an active automatic owner; delivery limitations were retained but absent
from the consolidated review. Present the observed automatic phase and one final
human review through shared guidance, while keeping manual actions/read-only
report controls under their existing owners. Unknown observation is not proof of
an automatic run. Adoption wording requires the exact operation/revision/hash;
intent adoption cannot establish presentation adoption. Branch provenance follows
the current admitted section-map-to-graph link because its checkpoint records the
installed graph, not the map. Unresolved provenance stays explicit.

Read delivery declarations from existing managed asset and native owner GETs.
Bind project, asset/original hash, owner kind/ID, role, accepted receipt and
manifest identities; preserve limitations verbatim and distinguish an explicit
empty declaration from unavailable evidence. Display adaptation and retained
original independently without judging improvement. Abort obsolete project/bundle
reads; retry only observation and preserve authored review inputs. These reads do
not alter handoff payloads, admission, prompt/provider or geometry contracts.

### P5 new-policy deterministic first-frame geometry · approved before code

Real native proof at frozen 4817 produced 941×1672 twice for a 720×1280 target.
The exact aspect gate correctly refused both. Semantic generation cannot promise
pixel geometry; another generative retry would repeat the wrong mechanism. The
owner explicitly approved centered crop+resize with raw originals retained and
one final human review. This changes only fresh launch policy to pre-video.v2.
Existing v1 evidence is readable/reconcilable but does not gain new preparation
permission; no old job, reservation, pin, report or policy is rewritten.

Freeze the deterministic recipe and runtime identity at Start. Only a technically
accepted raw original failing exact Brief aspect is prepared, using the existing
EXIF-transposed RGB centered-cover LANCZOS PNG transform at frozen dimensions.
Matching-aspect originals remain original selections. No stretch, padding,
face/quality heuristics, reroll, image provider or native ceiling increment.

A typed geometry-preparation field on the existing immutable checkpoint owner
records local authority/claim, project/run/policy/shot, exact native candidate/job/
request/delivery/execution identity, raw SHA/geometry, EXIF orientation, crop box,
recipe/runtime hashes and new managed output SHA/geometry. It is not a native
job/candidate/manifest. Preparation and provisional selection have separate exact
scopes and decisions. An adopted local checkpoint is idempotently selected after
restart; transactions/unique checkpoint identity serialize competing attempts.
Content-addressed publication retains originals even when a transaction fails.
No new SQLite table/layout or historical schema transition is needed.

One strict single-hop resolver binds native outputs and these managed derivatives
through immutable typed checkpoint evidence. Generic provenance extras cannot
establish derivative authority. Use the resolver for provisional/open/recovery,
review bundle, human selection, SamePerson mapping and reviewed admission for all
later video/preview consumers. Derivatives retain source v3 conditioning while
human judgments bind derivative bytes and typed lineage. Generated or derivative
sources with missing evidence must fail, never fall through to imported-human
mapping. Material closure and review receipts bind the derivative lineage hash.
Original/adapted UI evidence stays distinct, including dimensions, crop recipe,
source identities and original limitations; preparation makes no quality claim.


Geometry byte identity is checked through the confined content-addressed asset
store on ordinary open and every shared lineage consumer. Snapshot stages its DB
first: that initial validation receives the frozen source asset home explicitly;
destination validation uses copied assets. Missing/changed source or output is a
refusal, not a transient imported source. Canonical JSON hashing lives in a small
dependency-free contract module (persistence reexports the identical function),
so standalone transform imports cannot cycle through repository composition.

Refinement currentness distinguishes immutable generated-source context from
selection position. Before selection the frozen parent must remain selected;
once that delivered job's exact output is genuinely selected, it supersedes the
parent. Still validate every ancestor's authority, intent/presentation, references
and cancellation with a cycle guard; historical ancestors need not remain selected.
Current selected bindings independently require exact latest intent, presentation,
approval and native/derivative lineage. Reject both the self-invalidating parent-
selection rule and an immediate-parent-only state check. Ordinary raw earlier-
schema HANDOFF comparisons remain explicitly human-current-material; strict source
resolution precedes this classification, and derivatives/V3 missing mappings can
never take that path.

### Shared managed-blob publication · crash repair approved before code

The existing O_EXCL write creates the canonical SHA path before writing its bytes.
SIGKILL during that actual write leaves a truncated canonical blob; SQLite rollback
cannot remove it, and strict same-identity retry correctly refuses it. Fix the
shared artifact owner, not geometry retry or canonical corruption checks.

Write and fsync a fresh single-linked file in a private0700 directory beside its
admitted project, outside the portable project payload. Publish using one native
atomic exclusive rename: macOS renameatx_np/RENAME_EXCL or Linux renameat2/
RENAME_NOREPLACE. Never replace, link/unlink, repair a canonical blob, or fall back
to weaker semantics. A racing existing destination must pass the same confined
regular-file, single-link, size and SHA checks. Fsync the destination directory
and its new ancestors before caller metadata commits. Retry after writer death
uses the same content identity: the canonical path is absent or complete.

This requires a writable outputs parent, same-filesystem staging and native
exclusive-rename support. Fail closed on unsupported capability, EXDEV, permission
or durability failures; do not change roots, permissions or deployment settings.
Descriptor-relative operations reject symlink traversal and bind stage/canonical
identities. Live cleanup may remove only this invocation's identified unpublished
file and its exact empty private directory. Interrupted or altered stages remain
forensic siblings: never sweep, adopt or put them into snapshots. This intentionally
retains bounded crash debris rather than risking foreign-file deletion. Existing
read-only inspections and valid/foreign/corrupt artifacts retain their contracts.
Prove actual partial-write death, promotion boundaries, same-hash races and strict
preservation on disposable data; native platform evidence remains separately scoped.
