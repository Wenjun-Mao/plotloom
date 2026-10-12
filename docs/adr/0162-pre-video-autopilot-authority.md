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

## P0 implementation contract · 2026-10-12 review checkpoint

The [P0 checkpoint](../roadmap/2026-10-12-pre-video-autopilot.md#p0-implementation-checkpoint)
and [receipt](../verification/2026-10-12-pre-video-autopilot.md) settle the
following design, pending the manager's attended review before dependent writes.
This is contract design and baseline seam evidence, not implemented authority.

- A project retains one MVP run, with typed checkpoints, immutable decisions and
  provisional frame bindings. Machine decisions never enter the human approval
  ledger, `ReviewedShotBinding` or `SamePersonReview`. Text-stage adoption retains
  each current owner and appends machine provenance in the same transaction.
- A production unit has exactly one authority: a human approval FK or a machine
  decision FK. Its snapshot records the actual tagged authority, never a machine
  ID disguised as `approvalId`. Machine admission is explicit and image-only;
  currentness and dispatch permission are separate queries. Installed machine
  material can remain inspectable/current when automatic dispatch has stopped.
- Intent adds `ai_adopted`; presentation adds a typed machine-adoption reference
  while `reviewed` remains false. Human review and machine adoption are mutually
  exclusive. The structural span binder and canonical gates are shared, without
  claiming human semantic or visual fidelity. Final bundle review endorses the
  retained machine records instead of rewriting their original provenance.
- Trusted orchestration commands carry a typed run/lifecycle/claim and exact
  closure. A repository-bound command transaction reuses one session for owner
  reads and writes, so adoption and its decision/checkpoint commit together.
  Public manual mutations have no machine context and pause/take over the run;
  no browser body or reviewer string can manufacture controller authority.
- Human handoff records actual per-frame VisualIntent, compatibility and identity
  inputs through existing owners, and endorses the original reference decision
  IDs. Re-selecting identical reference bytes would invalidate frozen identity
  mappings. The material hash is separate from the human approval/binding/review
  IDs appended by handoff, preventing self-invalidation.
  Manual takeover can later produce a fresh exact handoff from manually completed
  current material, preserving the old receipt without automatic regeneration.
- Video guards apply to preview, preparation/freezing, enqueue and dispatch,
  before provider preflight or application accounting reservation. They validate
  the whole material/handoff closure, including unrelated adopted subjects and
  other shots. Receipt/history reads, safe known-ID reconciliation and cancellation
  retain their evidence-preserving behavior after eligibility is withdrawn.
- Keep the existing nine-attachment and eight-character-review limits. A shot
  that cannot satisfy both is a disclosed capacity blocker before image dispatch,
  never a reason to omit a visible character or fabricate a review.
- Exact Brief projection needs typed Brief-derived origin and preservation of the
  saved title/synopsis bytes; ordinary SourceMaterial normalization currently
  trims them. No attribution or rights declaration is inferred.

The preceding layout has 75 project tables and canonical `schema_objects` hash
`ea9facef83198e8b5abdd8693923f51add1376c0b416041dbfa245b92011b825`
at `731cfdbf`. Freeze the complete tuple as upgrade authority before source
metadata changes; this baseline is not an actual-installation inventory. The
explicit transition must rebuild the production-unit authority constraint as
well as add autopilot tables, preserving every old row/ID and operational state.
Normal reads still refuse prior/unknown layouts. Verified immediate-prior
snapshots upgrade only their private restore destination; captured native run
identities remain permanently non-dispatchable after portable acknowledgement.

P0 reproduced a pre-existing snapshot defect: eight retained native creative
package/delivery files were omitted, and direct closed-folder restore rejected
their directory. Extend the confined inventory from typed retained job/request/
pin identities; do not recursively accept arbitrary `outputs/`. Include archival
packages, reports and incomplete/invalid evidence with honest publication state,
bounded safe paths, hashes and secret scanning. Such evidence cannot settle a
native lease or grant selection. Ordinary discovery hides unsupported folders,
so the upgrader needs independent manifest/raw-layout inventory.

First-frame originals must satisfy the saved Brief aspect before completed-pack
admission. A mismatched original may use at most one separately counted existing
image-adaptation job, with a tagged machine-provisional source replacing the
current human-only source requirement. Settle the technically valid original job
through its normal owner, preserve the mismatched original as evidence and
exclude it from required-frame completion. A second incompatible output blocks.
Freeze image target geometry at launch,
without video preview or provider calls; retain original bytes and both jobs.
Capacity exhaustion or invalid adaptation blocks completion. No implicit crop,
hidden retry or guarantee of native ImageGen geometry is introduced. This source
union and geometry refinement require attended P0 review before implementation;
the real isolated proof remains the manager's later gate.
