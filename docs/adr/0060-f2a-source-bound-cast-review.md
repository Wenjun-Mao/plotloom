# ADR 0060: F2A source-bound cast review

Status: Accepted, 2026-09-18.

## Context

F1B establishes the sole accepted source/outline/section routing context. The
pinned `novel-characters` skill emits useful upstream-shaped `cast.json` and an
HTML report, but neither output can become Plotloom authority by delivery alone.
The legacy Story Bible currently owns character keys for reference/media work;
requiring it before a new cast can be reviewed would retain a competing proposal
route and makes F2 depend on obsolete generation.

## Decision

F2A adds a focused project-owned cast review record. A candidate freezes exact
source, outline, current section-map, and installed canonical graph revisions/hashes
plus the three stable section IDs. The specialist owns the unmodified upstream-shaped `cast.json` and
derived report; the author explicitly accepts the candidate under CAS. Trusted
code owns package provenance, narrow structural checks (object, stable unique
character IDs), currentness, persistence, and late/cancelled-delivery refusal.
The binding and its CAS checks read these records in the same transaction snapshot;
a current section map alone is not evidence that its graph remains installed.

The accepted payload is one cast authority. Its explicit `castCharacterId` to
`consumerCharacterId` mapping is the thin seam for existing character-reference
and media consumers; it creates no Bible, reference selection, asset, image, or
voice-consistency evidence. IDs are not silently inferred from legacy Bible
records. F2B may consume this seam for identity work after its own acceptance.

Reports are sandboxed read-only views and never a second editable authority.
The ordinary review surface presents motivation, appearance, and voice direction
from the proposal, while explicit acceptance remains separate from human
creative approval.

## Consequences and guardrails

- Changes to accepted source, outline, section map, or stable section context
  visibly stale a cast and reject prepared/late delivery; they never rewrite it.
- A prepared cast blocks close/snapshot just like F1A until cancelled or
  terminal, reusing the existing lifecycle rule rather than a parallel runner.
- No old Bible generation is needed to prepare or accept F2A. No image/media or
  text-direction-as-voice proof is performed in this slice.
