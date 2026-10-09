# ADR 0143: Identity-review refusal guidance

Status: Accepted, 2026-10-09.

## Problem

The revised-story native run selected a hand-only keyframe whose identity review
could not pass. H3 source reading correctly refused it, but returned generic
`invalid_transition` and English implementation prose. Still preview used a
different generic message. The review panel described only the still-preview
gate, hiding its consequence for video generation.

## Decision

Both existing admission checks raise `SamePersonReviewRequiredError`. HTTP409
exposes `same_person_review_required`, exact `shotId`/`bindingId`, a technical
description, and shared Chinese guidance naming the existing review panel.
Both API compositions use the shared transition-error serializer, preventing
composition-specific loss of the typed diagnostic.
The message describes the combined fact (no applicable passing review), not an
invented distinction between missing, failed or outdated records. Existing API
clients display the server-owned message; no exception-text matching or fallback
adapter is added. The review panel explains both blocked operations and warns
against marking unassessable identity as passed.

Admission/currentness predicates, frozen packages, stored judgments and job
dispatch are unchanged. Whether an explicitly unassessable identity may ever be
admitted is a separate unresolved product decision, not part of this copy repair.

## Guardrails

Exercise missing and failed reviews, exact refusal identities, no new preview or
video job/provider call, and successful explicit passing review. Check both H3
source-preview and video-preparation routes and still-preview refusal, including
visible desktop wording. Reject a UI-only English-text substitution, permissive
review policy, or automatic retry/approval.
