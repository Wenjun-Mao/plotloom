# ADR 0090: Separate character descriptions from review notes

Status: accepted, 2026-09-26

## Evidence and ownership

The retained 林遥 candidate mixes source qualifications and performance direction
into appearance and temperament. Upstream `novel-characters/references/profile-pass.md`
rules 1 and 4 explicitly require inline inference labels. ADR 0089's lossless
presentation cannot solve this authoring contract mismatch.

The specialist proposes descriptions and qualifications; the author reviews,
edits and accepts them. Trusted code validates structure, identity and frozen
context, not the truth of a creative inference.

## Decision

New character requests freeze `inputs/cast-writing-contract.json`. Each character
adds `reviewNotes: { sourceNotes: string, performanceGuidance: string }` (empty
strings allowed). Source notes identify the relevant field/detail and distinguish
source facts, inferences and proposed production choices. Performance guidance
holds scene-specific acting instructions. Descriptive fields remain descriptions;
verbatim evidence remains unchanged. This explicit Plotloom instruction overrides
the upstream inline-annotation placement, not its requirement to disclose inference.

Admission requires the extension when the frozen request specifies it. Acceptance
and reopened saves preserve that requirement; any supplied extension is validated.
Semantic separation is a specialist/reviewer responsibility: no keyword scrubber
or purported semantic validator. The editor exposes both note fields separately.

Do not change old frozen packages or delivered evidence. The current valued
candidate can be explicitly edited and given notes before acceptance; no automatic
migration or cleanup. ADR 0089's narrow lossless display remains only for existing
inline annotations. The original upstream report remains a technical artifact;
Plotloom review displays the extension, which the upstream renderer does not know.

## Alternatives and guardrails

Reject broader regex stripping: it can destroy meaning and conceal provenance.
Reject editing pinned upstream instructions or historic request projections:
that breaks frozen execution identity. Freeze the new instructions in the request.
Tests cover required/optional structure, author-save preservation, unchanged old
request projection and editable/read-only review. No creative acceptance, media
generation or performance-prompt consumption is introduced here.
