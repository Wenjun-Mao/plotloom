# ADR 0150: Review-bound production bridge acknowledgement

Status: implemented and independently reviewed, 2026-10-09. Focused qualification
and the final unfiltered 268-test browser sweep pass; native continuation remains open.

## Problem

The real rebuild accepted Storyboard r3 while the production panel stayed mounted.
Its GET ran only on project changes, so it retained r2's unavailable preparation
despite the server qualifying r3. A page reload exposed the correct contract.
Refreshing by remounting or adopting every read would instead lose authored intent
and presentation text. A shared read/mutation sequence could also strand busy state.

## Decision

The panel requires the accepted review's revision, content hash and independent
review status. These form a semantic read owner, separate from project identity.
Every read and callback belongs to that owner. A changed owner blocks actions in
its first render; only its successful GET acknowledges current action eligibility.
Delayed success/error, including A-B-A, cannot requalify an obsolete owner.
Admission checks the latest successful acknowledgement's exact identity and phase
synchronously. Retained callbacks cannot use a replaced acknowledgement or bypass
an in-progress read, nor dispatch twice before React renders the busy state.

The server acknowledgement and editor proposal base are separate. Clean editors
adopt fresh reads. Actual authored intent or presentation buffers retain their
original proposal/source base when the server changes; they are inspectable but
unsavable until explicit atomic adoption/disposal. Initial unassigned presentation
spans alone are not author edits. Ordinary refresh never silently resets a dirty
presentation source hash. Failed reads retain text and offer a read-only retry.
Dirty truth remains independent of accepted/read-only status. Another reader's
acceptance of the same proposal key cannot clear an unsaved presentation buffer or
its Close guard; changed server status requires explicit disposal/adoption too.

All bridge mutations, including presentation saves, share project-scoped pending
tickets in the existing project-lifecycle owner's in-memory scope. A semantic
read-owner change or actual unmount cannot release a pending POST. A promise-owned
Close writer registers at admission and unregisters only at settlement; remount
observes the same occupancy. Local text guards do not retain a captured busy flag.
When an obsolete owner settles, its project's completion epoch retires reads made
before that settlement, including delayed GET replies. The live mount must GET
the actual result before acting. A current owner's published response needs no
redundant GET. Other projects' acknowledgements remain independent.
Mutation busy ownership is independent of read sequencing. A prior owner's
settlement cannot adopt content, authorize navigation, or clear a newer operation's
busy ticket. A presentation save may advance the proposal revision and still
settle its own busy ticket. Poll reads are serialized. No remount workaround,
read-only heuristic, compatibility default, adapter or new persistence layer.

Toolbar refresh also preserves the whole existing route, including embedded
Source/Art/Script/Storyboard fragments. Dropping only its internal hash switched
the active review to Source without changing the address; inactive readers remain
inactive rather than compensating with unnecessary fetches.

## Guardrails

Mounted acceptance refresh with the exact new prepare contract; first-render
blocking; current/retained transitions; delayed reads and A-B-A; actual nonempty
intent and presentation preservation; refresh failure/retry; old child and mutation
settlement; own-save busy settlement; existing native task and installed-shot
handoffs; project change/unmount and explicit-close protection. The observed
walkthrough reload remains a temporary mitigation in its historical receipt.
