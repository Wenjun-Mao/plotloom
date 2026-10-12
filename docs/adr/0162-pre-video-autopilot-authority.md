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
