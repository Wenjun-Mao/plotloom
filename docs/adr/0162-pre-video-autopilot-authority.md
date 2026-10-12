# 0162 — Pre-video autopilot decisions are machine-owned and scoped

Status: accepted for implementation, 2026-10-12; not implemented. The owner selected automatic
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
