# ADR 0030: Character-reference decisions and cross-shot review

## Status

Accepted for P1.5 implementation, 2026-09-12. Visual qualification remains a
separate acceptance gate; this decision does not authorize video.

## Context

P1's resolved image context mixed scene membership, dialogue speakers and
required entity states. A same-shot `parent_output` could guide refinement, but
neither it nor textual character anchors identified the same person across
separate original jobs. Repeating a name in a prompt would be a downstream
workaround, not an identity contract.

## Decision

Use a project-owned, append-only character-reference decision for each stable
canonical character ID. A decision names one primary managed asset and up to two
complementary managed assets, freezes their original hashes and an
identity-relevant character-context hash, and is created/revoked with optimistic
revision checks. Replacing or revoking a decision never rewrites old decisions,
jobs, deliveries, assets, reviews or previews.

Character-reference proposals are a distinct story-first target. They freeze a
saved Story Bible character and visual direction and use the existing manual
exchange, but carry no invented Shot, storyboard Approval, reviewed keyframe, or
automatic reference selection authority. Their candidates are ordinary
project-scoped imported assets until a creator explicitly selects one.

Identity-aware image jobs are request schema v3. Trusted code derives visible
characters exclusively from `Shot.characterIds`, then freezes each character's
reference-decision ID/revision, role-mapped asset hashes and bytes as
`character_identity:<characterId>`. `parent_output` remains a distinct
refinement role and cannot supersede identity or canonical shot state. Missing
references fail admission; character-free shots remain valid without a reference.
V2 requests and manifests retain their historic projection and behavior.

The specialist must view every role-mapped identity reference and truthfully
attest the exact viewed hashes plus executor code/skill provenance in a v2
delivery manifest. This attestation is delivery evidence, not a claim of
automatic visual fidelity. Package and delivery validation fails closed on
tampering, missing role/hash attestations, or unsupported version contracts.

A selected v3 generated keyframe with visible characters requires a recorded
human same-person review before it can enter a still preview. The review binds
the selected keyframe to exact frozen decision revisions and image hashes,
separates identity judgment from shot state, and has no face-recognition or
Approval authority. Replacing/revoking a reference, changing relevant character
context, replacing the selected keyframe, or invalidating its ordinary storyboard
dependencies makes the job/review/preview inapplicable while preserving history.

## Consequences and guardrails

- The browser may choose managed project assets and author review notes; it may
  not submit reference hashes, canonical character data, a prompt, a path, or an
  Approval substitute.
- Managed assets remain project scoped. Existing media deletion guards and
  immutable delivery history continue to protect referenced bytes.
- The P1.5 specialist procedure is repository scoped in
  `.agents/skills/plotloom-image-specialist`; it receives a frozen package, not
  story authority or permission to edit Plotloom.
- Automated checks cover decision concurrency/isolation, proposal authority,
  exact role mapping, off-screen exclusion, delivery tampering/currentness and
  review-dependent preview admission. A real three-shot visual comparison is
  still required before claiming cross-shot consistency works in practice.

## Alternatives rejected

- Prompt-only character names or a generic `VisualIntent`: they are neither
  stable role-mapped image bytes nor an explicit creator decision.
- Reusing the last shot's output as identity: it conflates shot-specific state
  and composition with durable identity and fails for separate originals.
- Automatic proposal adoption or face-recognition scoring: both bypass explicit
  creator review and do not fit Plotloom's canonical-authority model.
- A new media service or external image API: outside P1.5's bounded manual,
  built-in-ImageGen workflow.
