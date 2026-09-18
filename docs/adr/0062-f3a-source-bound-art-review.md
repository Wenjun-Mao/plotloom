# ADR 0062: F3A source-bound art review

Status: Accepted, 2026-09-18.

## Context

F2B provides a current accepted cast seam, but it does not own locations,
narrative props, environment assets, or an upstream `novel-art` review record.
The pinned art skill can validate and render a useful `art.json`; delivery alone
must not claim images, selected assets, creative acceptance, or currentness.

## Decision

F3A adds one project-owned art candidate and accepted-revision owner. A proposal
freezes exact accepted source, outline, F1B map, installed graph, accepted cast,
and stable section IDs. The specialist owns upstream-shaped `art.json` and its
derived report; the author explicitly accepts under CAS, may reopen and text-edit
the accepted JSON, and may save only while scene and prop IDs remain stable.
Trusted code owns immutable revisions, package pin/hash checks, currentness,
late/cancelled-delivery refusal, and lifecycle blocking for a prepared handoff.
F3A is a project-folder format-9 boundary: format-8 folders are explicitly
reset-required and rejected at manifest admission, before any repository SQL is
opened. There is no automatic migration or fallback. The upstream pinned
`novel-art` validator owns art-shape and quality gates; Plotloom owns only the
thin `sectionUsage` projection, which must cover exactly the frozen F1B section
IDs and reference only declared scene/prop IDs.

The upstream episode-shaped `usage` remains a report field only. Plotloom adds a
thin `sectionUsage` projection with existing F1B IDs; it does not fabricate
episodes, hooks, or a second graph. Reports are sandboxed derived views. F3A is
text-first: no ImageGen, H3, managed asset, selection, or image-currentness
claim is introduced.

## Consequences

- Any source/outline/map/graph/cast revision or hash change stales art and
  prevents installation; reopening a cast also prevents new art preparation.
- Candidate text may be reviewed before images, and cancel/replacement remains
  user reachable. A prepared art publication blocks close and snapshot through
  the established project lifecycle guard.
- `cinematic realism` is inherited author direction. Upstream `realistic` is
  accurately described as semi-realistic painterly; F3B must qualify real
  environment/prop references before a rendering-style decision or asset claim.
- Reloading a prepared handoff re-copies its same frozen package rather than
  creating another candidate. Accepted art remains readable with its report;
  if author edits make that report historical, the report says so explicitly.
