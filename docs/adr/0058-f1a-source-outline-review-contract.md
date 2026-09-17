# ADR 0058: F1A source and outline review contract

Status: Accepted, 2026-09-17.

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
- Rights and attribution are captured verbatim as supplied.  The product makes
  no clearance or ownership assertion from them.
