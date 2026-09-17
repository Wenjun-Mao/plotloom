# Playable MVP milestones

Revision 1 — **Approved**, 2026-09-16. Director owns acceptance; Relay coordinates
bounded serial delivery. Current authorized implementation: checkpoint 1 only.
Later checkpoints establish direction, not blanket implementation authority.

## Product outcome

**M1:** One small playable branching story in a clean browser Play view inside
Plotloom, without navigating authoring tools to watch it.

**M2:** A user supplies a synopsis within our supported scope, reviews Plotloom's
proposals, and produces a finished, playable branching film without developer
intervention. Finished means selected audiovisual assets, coherent playable paths,
and a complete viewing experience—not perfect or cinema-quality generation.

The work is connecting, simplifying, and proving existing capabilities, not
building seven new subsystems. Cinematic realism and proposal-first authoring
remain the initial direction; detailed editing remains available.

## Checkpoints and current progress

| Checkpoint | User outcome / acceptance | Current status and gap |
| --- | --- | --- |
| 1 — M1: one playable story | Direct Play entry; explicit start, complete opening/decision, both choices/endings, restart; loading/error handling; repeat after reopen without authoring UI | Authorized next. Existing branching player and user-approved four-shot pilot work; dedicated viewing entry and integrated acceptance remain. |
| 2 — Synopsis to proposal | Minimal input produces understandable characters, setting, dramatic direction, branches/endings and production scope; optional defaults and actionable unsupported-input feedback | Planned. Existing Brief and generation are foundations, not independent-user acceptance. |
| 3 — Proposal to production-ready storyboard | Coherent scenes, beats, dialogue, sound and shots; targeted revision/recovery without unnecessary replacement of accepted work | Planned. Four-stage generation demonstrated; qualify narrative quality and user recovery across distinct stories. |
| 4 — Consistent visual package | Select/refine proposed identity references and keyframes; supplied references can be preserved; changed inputs identify affected assets | Planned. Cross-shot pilot and manual specialist handoff exist; developer-free handoff/transport and reference UX need explicit resolution for M2. |
| 5 — Reviewed audiovisual candidates | Generate alternatives, compare, regenerate, select and discard; failures/reopen are usable; audio/dialogue limitations explicit | Partial foundation accepted at `8ba34aa`: candidate workflow verified offline, H3 pilot live; complete real alternative-review journey and modest dialogue workflow remain. |
| 6 — Complete interactive film | All intended routes use selected media, missing coverage is visible, audiovisual transitions and decisions work | Planned. Small pilot proven; qualify completeness and transitions for supported story scope. No invented game-state semantics. |
| 7 — M2: independent creation and delivery | Users finish fresh contrasting stories without developer assistance and open/share the supported playable output | Planned. Qualify complete authoring/revision/recovery and settle browser delivery/hosting scope. |

Accepted baseline: clean pushed `8ba34aa`. Evidence:
[branching pilot](../verification/2026-09-16-branching-creative-pilot-receipt.md),
[native playback diagnosis](../verification/2026-09-16-terminal-video-runtime-boundary.md),
[video alternatives](../verification/2026-09-16-video-candidate-review.md).
The departure clip is user-approved with intermittent face defects, not defect-free.
Audio approval is attributed to the user; do not claim machine/audio review.
No general Alpha or arbitrary-synopsis reliability claim follows from these pilots.

## Lean delivery rules

- Begin each checkpoint with a short existing-capability/gap map, not a new audit project.
- Reuse current playback, selection and project owners. Remove superseded code and
  redundant paths in the touched slice; avoid parallel state/manifest authorities.
- Review every new abstraction for an actual current responsibility. Do not create
  frameworks for hypothetical backends, compatibility or publication features.
- Simplification is part of acceptance: record significant consolidation/removal,
  or why existing boundaries required no structural change. Fewer lines alone is
  not evidence of clarity; preserve tests for supported safety and behavior.
- Prove the smallest uncertain piece first. After two failures of the same criterion,
  reassess cause/method before another attempt. No routine confirmation between
  approved steps, and no automatic broad redesign to address an isolated failure.
- Keep this table as the single current progress tracker. Implementation, tests,
  live behavior and creative approval are separate evidence categories.

## Checkpoint 1 execution contract

Deliver a dedicated viewing entry using the existing branching player, project
API and selected media. Prefer a minimal URL/view mode in the current application
over a new app, player engine or persisted manifest. Viewing should not mount the
full editor/draft machinery just to hide it. Provide a discoverable Play action
from the project/workbench and a directly reopenable URL. Preserve authoring.

Use the retained four-shot project `4d7d4856-e407-4467-9432-3d9187b9edf8` under
`outputs/20260916T140747516355Z__4d7d4856-e407-4467-9432-3d9187b9edf8`.
All four clips already have user audiovisual acceptance. Preserve media bytes,
review lineage and selections. The accepted one-time selection schema transition
may run through normal production writable open; no manual database edits/reset.
Replacing the departure clip is not a prerequisite and is outside this slice.

Required evidence:

1. Production FastAPI/file-SQLite browser regression: direct Play entry, start,
   actual native opening and decision clips, pause/explicit A/B choice, both endings,
   restart to zero/empty history, missing-media/loading/error behavior and refresh.
2. Retained-pilot native browser proof: both paths complete from the viewing entry;
   normal close/reopen then repeat both paths. Use real ended/currentTime/error state,
   not a transient Chrome accessibility label or fabricated events. Preserve existing
   user audio attribution; no new creative approval required for unchanged clips.
3. Scoped attended independent Terra review, focused tests during work; final
   frontend unit/typecheck, production build/static freshness, full browser suite,
   locked Python and installed-wheel smoke. Retain actual logs and a small visual
   Play-view capture; avoid repeated full gates on unchanged revisions.
4. Update this row and one concise verification receipt; director accepts and pushes.

No new generation, stitching/export, hosting/authentication, timed choices,
inventory/combat/state-effect execution, generic migration system or broad
refactoring. Preserve all retained assets and unrelated user work. Existing local
runtime startup for proof is authorized; stop owned services after verification.
Escalate missing browser access, materially incompatible pilot data, or a required
scope expansion rather than weakening acceptance or silently substituting fixtures.

## M2 decisions to resolve before their checkpoint

Suggested initial envelope: roughly 1–3 minutes per path, a few meaningful choices,
2–3 endings. These are planning defaults, not hard coded limits or final acceptance.
Settle dialogue/lip-sync capability, developer-free image handoff, sharing format,
and whether state-dependent choices are needed at their owning checkpoints. Keep
stitching optional; clip-based branching is sufficient for M1. Use one fresh story
through checkpoints 2–6, then contrasting stories for M2 qualification.
