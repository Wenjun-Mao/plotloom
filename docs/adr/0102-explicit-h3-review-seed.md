# ADR 0102: Explicit seed in H3 direction review

Status: Accepted

## Context

A controlled phone-text experiment needs to reuse a rejected take's seed while
changing its reviewed first frame. The backend already freezes an explicit
seed, but the UI only generated and displayed one. Changing both image and
seed silently would weaken the comparison; API-only preparation would leave
the creator workflow incomplete.

## Decision

The shared H3 direction-review UI exposes an editable decimal seed. It retains
the random default, accepts zero through JavaScript's maximum safe integer,
and rejects blank, signed, fractional, exponential or lossy values before API
requests. The API's wider integer range is unchanged; the browser deliberately
admits only integers its existing numeric JSON contract can represent exactly.

Seed is part of the reviewed source snapshot, not a late dispatch override.
Editing it clears sources, English drafts, consent and compiled preview, and
rotates the idempotency key. Read, preview and freeze use the same explicit
seed/key. Pending operations lock editing; source/project identity changes
still discard late responses. Freeze remains separate from submission.

## Consequences and guardrails

- Users can reproduce a seed without replaying or altering retained jobs.
- No automatic resubmission, provider change, precision coercion or backend
  validation weakening is introduced.
- Unit tests cover exact reuse, boundaries, invalid input, review/key
  invalidation and pending identity changes; a browser regression checks the
  prepared payload and persisted snapshot.
- Same seed is a comparison control, not a promise of identical rendering or
  creative acceptance. Other changed inputs must still be disclosed.
