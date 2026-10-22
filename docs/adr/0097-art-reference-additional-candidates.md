# ADR 0097 — Revise requirements as another art-reference candidate

Status: accepted, 2026-10-02.

## Problem

The art-reference UI treats every current non-cancelled proposal as a frozen
request. That correctly protects dispatched instructions, but also hides new
preparation after delivery. A creator cannot try another image without going
outside the normal UI, although persistence already supports multiple proposals
for one accepted scene or prop.

## Decision

A current delivered proposal exposes **修改要求，再生成一张**. This opens a new
local requirements draft seeded from that proposal's frozen requirements; it
does not edit its request or use its image as an image-edit input. Drafts and
revision mode belong to the accepted-art session, subject and source proposal.
Subject navigation preserves that subject's draft; changing project or accepted
art clears drafts. A different latest proposal cannot inherit revision mode.

Preparing uses the existing new-proposal endpoint. Sending remains a separate
explicit action, with the existing one-inflight/unknown-outcome protections.
Prepared/exported jobs do not expose this additional-candidate action. Cancelling
the local edit issues no API mutation. Existing images, accepted art and reference
decisions remain unchanged; new delivery never selects itself. The gallery's
existing thumbnail and comparison controls include both old and new candidates.

The author owns the new render-direction overlay, accepted art still owns the
subject and style, and trusted code freezes a new job identity. No model prompt,
schema, image-edit contract or backend ownership changes.

## Alternatives and guardrails

Do not unlock the old request, cancel a completed job, reopen art canon, resend
an old assignment, or silently replace the selected image. True image refinement
is a separate contract, not implied by this requirements-based regeneration.
Verify draft isolation, cancellation, readonly/inflight gating, old candidate and
selection retention, explicit preparation/send and post-delivery comparison.
