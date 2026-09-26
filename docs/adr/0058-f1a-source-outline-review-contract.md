# ADR 0058: F1A source and outline review contract

Status: Accepted, 2026-09-17.

The declaration requirement in this record is superseded by
[ADR 0085](0085-brief-to-source-entry-and-optional-declarations.md). The
review and acceptance boundaries below remain in force.

## Context

F0 can freeze and validate a Shuohao outline delivery, but deliberately does
not own author source material, candidate review, or canonical installation.
Using the legacy Brief/Bible/Graph records as a proxy would either discard
source rights/adaptation declarations or silently translate upstream
`outline.json` into a competing authoring model.

## Decision

F1A adds a project-owned source/outline review record alongside—not inside—the
legacy stage pipeline.  It has one accepted source head, one accepted outline
head, immutable historical revisions, and a separately visible candidate.
Source supports exactly `synopsis`, `imported_text`, and `existing_work`; every
route records supplied text, attribution, rights declaration, adaptation intent
and any invented additions.  These are author declarations, never legal
clearance.

The specialist owns the unmodified upstream-shaped `outline.json` candidate
and its derived HTML report.  Trusted code owns frozen handoff identity,
cross-project/source/current-outline checks, and compare-and-swap admission.
Only an explicit author acceptance may install an outline revision.  Reopen
changes review state without replacing accepted content.  Source edits retain
prior accepted evidence and make a previously installed outline explicitly
reopened; they never auto-install or erase a candidate.

A prepared specialist publication is active external work, not an inert draft:
it blocks close, archive, permanent deletion, and snapshot until the author
explicitly cancels it.  Verified completion moves it to `ready`; explicit
acceptance moves it to `accepted`; cancellation moves it to `cancelled`.
`ready`, `accepted`, and `cancelled` are terminal because the completion
manifest was admitted, canon was explicitly installed, or the frozen job was
made ineligible for delivery.  A cancelled job cannot refresh, admit a late
delivery, or be accepted.  A new source edit or replacement candidate cannot
silently orphan a prepared publication.

The record is project-local SQLite state.  Its small additive schema is created
for writable existing project folders as a compatibility-preserving migration;
no source, outline, media, or prior canonical-stage content is transformed.
The F1A UI exposes source, candidate, and accepted material distinctly.  F1B
will consume the accepted outline directly when it owns section/choice mapping;
it is out of scope here.

## Consequences and guardrails

- F1A deliberately does not map outline episodes to Plotloom graph nodes,
  generate creative content, or replace the legacy proposal pipeline.
- Delivery validation failures, stale requests, foreign project identities and
  CAS races leave accepted content unchanged.  Tests cover those conditions.
- Reports are derived candidate views, served only after the same candidate has
  passed transport and currentness admission; JSON is the accepted authority.
- The F1A shell presents an upstream-derived report as unreviewed candidate
  material. If an upstream template uses editorial language such as “signed
  off”, that label has no F1A acceptance meaning and must be disclosed before
  the raw report is opened; F1A does not rewrite a hash-bound delivery artifact
  to remove it.
- The project lifecycle scans every persisted prepared outline candidate, not
  only the current head, so a stale or replaced job remains busy while it could
  still publish.
- Rights and attribution are captured verbatim as supplied.  The product makes
  no clearance or ownership assertion from them.
