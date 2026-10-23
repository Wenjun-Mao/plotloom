# Specification reconciliation and owner review

Baseline: `8d3b259a`, 2026-10-22. These are documentation/intent dispositions,
not permission to repair code. Clear supersession is recorded; uncertainty is
not silently normalized to current implementation.

## Owner review required

| Question | Conflicting or incomplete sources | Suggestion, reasoning and trade-off — not adopted |
| --- | --- | --- |
| Sidebar height basis | Original October 6 plan says approximately 85% of viewport; ADR 0122 says 85% viewport clamped to workspace below toolbar; C45 says about 85% of visible height | Keep the ADR's `0.85 × full viewport` target, then clamp to usable workspace. This follows the more precise geometry clause and preserves reachability as toolbar/guide height changes. Trade-off: short windows use available space rather than a uniform 85% of usable workspace; the formulas can differ. Centre/clamp, internal scrolling, no 500px cap and side-by-side short-desktop layout remain agreed regardless. |
| Professional visual-state persistence | October 6 plan preserves existing Pro canvas behavior; ADR 0121 retires independent canonical-shaped editing; C28 shares node selection; C48 permits Pro positioning without changing structure. No explicit position/zoom lifetime is stated | Preserve per-project visual state across Creator↔Pro switches during the current project session; reset on project change/reload initially. This avoids losing technical context during ordinary navigation without durable authored layout or migration. Trade-off: reopening loses custom layout; durable browser-private preferences improve that at the cost of explicit lifetime/versioning work. This is a proposed clarification, not a finding that reload persistence is missing. |

Sources: [approved plan](../roadmap/2026-10-06-graph-centred-creator-workbench.md#approved-reference-and-product-boundaries),
[ADR 0122](../adr/0122-creator-workspace-presentation.md),
[ADR 0121](../adr/0121-current-source-graph-authoring.md),
[C28/C45/C48](../creative-workflow/graph-workbench-acceptance.md).
Audit other unambiguous clauses independently; these questions do not invalidate
the whole baseline. Current code is evidence of an implementation choice, not
proof that the owner selected that choice.

## Resolved by explicit scoped supersession

| Older wording | Current controlling clause | Preserve |
| --- | --- | --- |
| First-install-only / general replacement excluded in the October 6 plan and ADRs 0079/0118/0121/0123 | [0138](../adr/0138-one-current-story-explicit-rebuild.md) explicitly supersedes first-install-only, enabling same-project reviewed rebuild | Source/CAS/currentness/dispatch guards, retained assets and separate fresh approval; not silent replacement |
| Shared canonical fallback reader originally used by both modes | October 22 [0122 amendment](../adr/0122-creator-workspace-presentation.md#workspace-presentation-is-independent-of-write-authority-2026-10-22) and current C02/C03/C28/C45 | Shared topology/fields; distinct Creator side inspector and Pro technical shell; no new write authority |
| Narrow stacking/touch qualification in ADR 0119 | October 6 approved workbench desktop boundary / ADR 0122 / C47 | No new narrow/mobile authoring scope; unrelated readers/media retain their own contracts |
| Old mandatory hosted CI or old capability-matrix authority | [0199](../adr/0199-local-release-qualification.md), current AGENTS and [ADR discovery guidance](../adr/README.md) | Historical failures remain failed; optional CI requires direct request; roadmap owns current approved scope |

## Different layers, not contradictions

- “Confirm once” is atomic immutable-preview application, not a prohibition on
  the distinct edit-dialog → preview consent stages in C53, nor a merger of draft
  Save / content Confirm / route Apply. Preparation owns temporary dismissal.
- Advisory guidance never mutates automatically. Separately approved automation
  may dispatch under its own frozen run/grant; that does not make navigation or
  an ordinary save implicit generation authority.
- A record marked proposed, candidate, in progress or separately qualified is not
  made accepted/current/shipped by appearing in the catalogue. Inspect exact
  clause adoption and its later receipt; uncertainty stays explicit.
- Architecture provenance is historical because its README explicitly says so;
  no owner decision is needed to stop calling it a fresh dependency map.

Unindexed ADRs and duplicate numbering are discovery defects, not proof of
product disagreement. The catalogue addresses discovery without renumbering the
two distinct `0040` records or inventing a missing `0164`.
