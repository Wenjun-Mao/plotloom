# Playable MVP milestones

Revision 3 — **Approved**, 2026-09-17. Director owns acceptance; Relay coordinates
bounded serial delivery. M1, checkpoint 2, and checkpoint 3A engineering delivery are accepted; next is checkpoint 3B qualification, under the user's instruction to continue without routine confirmations.
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
| 1 — M1: one playable story | Direct Play entry; explicit start, complete opening/decision, both choices/endings, restart; loading/error handling; repeat after reopen without authoring UI | Director-accepted at `6941f2e`. Dedicated Play URL reuses existing player and canonical data; both retained-pilot paths completed before/after reopen. [Receipt](../verification/2026-09-16-m1-playable-story-view.md). M2 remains planned, not accepted. |
| 2 — Synopsis to proposal | Minimal input produces understandable characters, setting, dramatic direction, branches/endings and production scope; optional defaults and actionable unsupported-input feedback | Director-accepted at `6e3ad75`; offline gates and fresh local-profile proposal/refinement/reload trial passed. Engineering acceptance, not human creative approval or arbitrary-synopsis qualification. [Receipt](../verification/2026-09-17-checkpoint-2-synopsis-proposal.md). |
| 3 — Proposal to production-ready storyboard | Coherent scenes, beats, dialogue, sound and shots; targeted revision/recovery without unnecessary replacement of accepted work | 3A engineering delivery director-accepted at `77cc4b4`: retained r2 Bible/Graph unchanged; 8 Scene Beats and 8 Storyboard units installed as r1; 508 gates passed; full browser suite 47/47. 3B's contrasting-story runtime qualification demonstrated structural gates and the upstream stale/rebuild boundary, and found a P1 choice/prop continuity gap plus repetition. The audio finding was withdrawn: cue IDs own speech and the cited durations fit; stage-level rebuild granularity is intentional rather than unexpected authored-shot loss. The prospective typed Graph-to-Scene-Beats entry-state correction is accepted at `0083e62` and requalified by one isolated exact-prefix continuation: direct entry states now agree, but the author content still drops sell-path causality at the join, jumps to a repaired-watch handoff, and repeats the pressure confrontation. A later two-request, docs-only causal-conflict experiment is **complete but not accepted**: its reduced A/B input did not state the needed temporal relation, so both valid `no_conflict` results are not detector evidence. The authorized full-prompt action/state realization experiment is also **complete but not accepted**: both structurally valid direct outputs re-established the already-repaired watch; treatment added a consequential contract decision but retained that defect and a scene-entry ordering mismatch. The recorded compact semantic experiment is a narrow positive only: its two four-field outputs avoided another watch-repair event and supplied branch consequence, but they lack the author-owned scene/beat/continuity inputs required by the existing parser/binder/validator; free-text `resulting_facts` remain non-canonical, and the Bible does not establish that `继续营业` conflicts with entry `修复中`. Its bounded two-call expansion continuation is structurally and independently reviewed as coherent: each full fragment preserves the typed entry state, avoids another watch repair, and realizes contract deferral, risk, and reconciliation; it is hybrid/offline evidence only and proposes, but does not authorize or implement, one selected existing-work-unit integration slice. The bounded Shuohao/Terra screenplay reuse trial is **complete but not accepted**: its 28.6-second rendered endpoint preserves the repaired-watch entry state where the retained Qwen candidate re-repairs it, but the upstream episode contract truthfully fails the absent hook/cliff and the review finds the audiovisual consequence thin. It recommends evaluating a thin complete-linear-episode adapter rather than resuming custom two-phase integration; no integration is authorized. Checkpoint 3B therefore remains **not quality-qualified**; checkpoint 3 remains unaccepted, with no Approval or human creative acceptance inferred. [3A receipt](../verification/2026-09-17-checkpoint-3a-editable-storyboard.md); [3B receipt](../verification/2026-09-17-checkpoint-3b-contrasting-story-qualification.md); [typed-entry requalification](../verification/2026-09-17-checkpoint-3b-typed-entry-requalification.md); [causal-conflict experiment](../verification/2026-09-17-checkpoint-3b-causal-conflict-experiment.md); [action/state realization experiment](../verification/2026-09-17-checkpoint-3b-action-state-realization-experiment.md); [compact mapping receipt](../verification/2026-09-17-checkpoint-3b-compact-semantic-scene-beats-mapping.md); [semantic-plan expansion receipt](../verification/2026-09-17-checkpoint-3b-semantic-plan-scene-beats-expansion.md); [Shuohao screenplay reuse trial](../verification/2026-09-17-shuohao-screenplay-reuse-trial.md). |
| 4 — Consistent visual package | Select/refine proposed identity references and keyframes; supplied references can be preserved; changed inputs identify affected assets | Planned. Cross-shot pilot and manual specialist handoff exist; developer-free handoff/transport and reference UX need explicit resolution for M2. |
| 5 — Reviewed audiovisual candidates | Generate alternatives, compare, regenerate, select and discard; failures/reopen are usable; audio/dialogue limitations explicit | Partial foundation accepted at `8ba34aa`: candidate workflow verified offline, H3 pilot live; complete real alternative-review journey and modest dialogue workflow remain. |
| 6 — Complete interactive film | All intended routes use selected media, missing coverage is visible, audiovisual transitions and decisions work | Planned. Small pilot proven; qualify completeness and transitions for supported story scope. No invented game-state semantics. |
| 7 — M2: independent creation and delivery | Users finish fresh contrasting stories without developer assistance and open/share the supported playable output | Planned. Qualify complete authoring/revision/recovery and settle browser delivery/hosting scope. |

**3B tracker correction — Shuohao trial:** The `23985ce` receipt's Shuohao
clause is superseded as flawed projection evidence: it wrongly treated contract
tearing and sale deferral as pre-entry. The corrected bounded rerun is complete
but not accepted: a frozen verbatim-state-versus-summary projection, one native
Terra High 30-second draft, and an independent read-only review keep the watch
already repaired and realize tearing/deferral in scene narrative. Upstream
truthfully fails only the source-absent hook/cliff and hook-claim gates. This
demonstrates workflow-plus-model feasibility, not causal superiority over Qwen.
It permits only future thin adapter investigation for bounded terminal or
complete linear excerpts—never custom two-phase resumption or integration
authorization. Checkpoint 3B remains not quality-qualified; checkpoint 3 and
human Approval remain unaccepted.

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

## Checkpoint 2 execution contract

User explicitly authorized continuation after trying M1: "I tried it, it worked
as expected." Director stopped the trial runtime; retained project stays intact.

Deliver the smallest understandable synopsis-to-proposal flow. Synopsis is the
required creative input; a working title and current supported production defaults
can be supplied and clearly labeled for editing. Expose advanced settings without
requiring users to understand DAG budgets. Do not silently override explicit input.

First map existing Brief, Bible, Graph and stage-generation owners briefly. Prefer
a review composition over their canonical data and existing editors, not a second
proposal database or new orchestration engine. Generate only what the proposal
needs; do not auto-generate scenes, shots or media before the user chooses to
continue. Show characters, setting, dramatic premise/direction, understandable
branch consequences/endings and the proposed production scope. Distinguish actual
derived counts from estimated timing; do not promise provider cost or exact runtime.

The user can refine the proposal, save it, reopen it, and explicitly accept/continue
to later storyboard work using existing canonical save/currentness boundaries.
Proposal acceptance is not storyboard Gate/Approval or audiovisual approval.
Do not introduce a new approval framework. Show concrete input/planning/provider
errors and useful next actions; do not invent a general semantic classifier for
every unsupported synopsis. Changes cannot silently overwrite accepted downstream
work or bypass existing stale-stage behavior.

Evidence: production FastAPI browser journey from a new synopsis to generated
proposal, edit/save/reload, explicit continuation boundary, and actionable failure;
test optional defaults vs explicit values and stage scope. One bounded real active
local text-profile trial on a fresh project demonstrates that the proposal is
understandable and faithful; record technical/creative limitations honestly. No
ImageGen/H3 calls or existing-pilot mutations are needed. Text endpoint/profile
changes are excluded; if unavailable, preserve offline delivery but report live
acceptance pending, not success. Two failed attempts at one criterion trigger
reassessment rather than repeated dispatch.

Keep implementation modular without unnecessary wrapper layers; remove replaced
paths within the slice. Attended independent Terra review, focused checks first,
then final locked Python, frontend units/typechecks/build/static freshness,
production browser suite and installed-wheel smoke. Update this tracker and one
receipt; director accepts/pushes. Record a concise ADR only for a new durable
contract. No broader editor redesign, new backend, media work, CI overhaul, storage
compatibility framework or change to M1 playback. Later checkpoints remain gated.

## Checkpoint 3A — reviewed proposal to editable storyboard

Start with the reference proposal `潮汐译信` from checkpoint 2 (resolve its exact
project ID from retained evidence, never guess). Map the current Scene Beats,
Storyboard editors, generation controls, gates and repair actions briefly, then
deliver the smallest usable continuation through those existing owners.

From a current reviewed Bible/Graph, provide an explicit action to generate only
the missing/stale Scene Beats and Storyboard range. Preserve current authored
upstream payloads/revisions; never save unchanged inputs merely to trigger a run.
Current Scene Beats with stale Storyboard requests Storyboard only; both current
means no implicit replacement. Surface progress, actionable validation/quarantine
and existing sanctioned exact-repair/rebuild controls without a parallel job system.
Do not create automatic retries beyond current frozen execution policy.

The result must be reviewable/editable through existing fields for scenes, beats,
dialogue, audio and shots, with required gate failures visible and linked to their
owners where existing facilities permit. Explain derived timing and dialogue's
single authority. No new media, automatic Approval, timeline, schema redesign,
generic migration or new creative-repair algorithm. Preserve retained pilots.

Regression evidence: production browser journey from current proposal to generated
editable storyboard; save/reload a normal edit; prove exact upstream content/revision
preservation, minimal requested stages and no-op when ready; exercise one offline
failure and existing authorized recovery path. Use actual production static output.
Run one bounded local-profile continuation of the reference story, review narrative
causality/continuity/performability and gate results, and document flaws honestly.
One additional contrasting story and broader targeted-revision qualification remain
checkpoint 3B; do not mark all of checkpoint 3 complete from this slice alone.

Use attended Terra independent review, focused checks then final locked Python,
frontend units/typecheck/build/static, browser and installed-wheel gates. Fix only
demonstrated in-scope blockers, with two-failure reassessment. Remove duplication
within touched generation controls; use explicit conditionals rather than nested
ternaries. No broad refactoring or further proof of already accepted media playback.
Keep a single receipt and update this tracker. Director accepts/pushes, then proceeds
to 3B after evaluating the actual gaps, without routine user confirmation.

## Checkpoint 3B — contrasting story and targeted revision qualification

Use the accepted current runtime, not a new generation subsystem. Create one
fresh project with a grounded, dialogue-led family dilemma, contrasting with
`潮汐译信`: two adult siblings must decide whether to sell their late mother's
small repair shop before a buyer's deadline; an unfinished repair reveals a
promise one sibling made. Keep the story small, with two meaningful endings,
clear choice consequences, and no supernatural premise. Freeze the exact Chinese
synopsis and existing supported structure settings in the receipt before running.

First use the normal synopsis/proposal and explicit storyboard-continuation
workflow. Run at most one initial proposal and one downstream continuation with
their existing bounded corrections. A failure is evidence: diagnose before any
additional run; do not silently retry, bypass gates, or edit the database.
Preserve all older projects, provider settings, and valued assets.

Review the resulting text for causal choices and distinct endings, character and
prop continuity, actionable shot composition, dialogue attribution/performance,
audio/timing fit, and needless repetition. Cite concrete scenes/shots/cues and
separate schema/gate success from creative judgment. Use an attended independent
Terra review; it is an engineering creative review, not human Approval.

Demonstrate targeted authoring through existing editors: save/reload one shot's
action/composition improvement without changing other shots or upstream content;
then edit one Dialogue Cue in Scene Beats, verify canonical single-source dialogue
and downstream staleness, and explicitly regenerate only Storyboard once if
needed. Preserve Brief/Bible/Graph, and prove unrelated Scene Beats/cues unchanged.
Do not promise shot-local model regeneration if the current product only supports
stage-level rebuild: report that actual granularity and any authored-shot loss
as a product limitation rather than silently claiming preservation.

This first 3B slice is qualification, not speculative source changes. Deliver a
receipt and tracker update with exact revisions/hashes, UI save/reopen evidence,
quality findings, and any smallest proposed fix. No media generation, profile/env
changes, new Approval, resets, broad refactor, or new repair machinery. Stop on a
material gap and return a diagnosis instead of enlarging scope. Two failures of
the same criterion require reassessment. Stop owned services. Docs-only checks
are proportionate; executable regression suites become required if a later
separately bounded correction changes product code. Director accepts and pushes.

### Prospective typed-edge prompt agreement — 2026-09-17

The bounded follow-up found a prompt-contract gap, not a new 3B creative-quality
finding: current Graph admission already rejects unsupported partial or
conflicting typed direct-edge states, while the Graph and immutable content-fill
prompts did not state that cross-edge requirement.  The prospective templates now
separate generic `stateEffects` join variance from typed `entityStateEffects` and
require each affected entity to be either omitted by every direct incoming edge
or assigned the same state by each of them.  Incompatible narrative content must
be reconciled upstream; it must not be fabricated, erased merely for validation,
or solved by topology change.  ADR 0056 records owner boundaries; the schema is
unchanged because it cannot encode the cross-edge relation.  Retained 3B data,
plans, snapshots, and historical evidence remain untouched.  See
`docs/verification/2026-09-17-graph-typed-join-prompt-agreement.md`; this is a
small engineering correction, not checkpoint-3B quality acceptance.

## M2 decisions to resolve before their checkpoint

Suggested initial envelope: roughly 1–3 minutes per path, a few meaningful choices,
2–3 endings. These are planning defaults, not hard coded limits or final acceptance.
Settle dialogue/lip-sync capability, developer-free image handoff, sharing format,
and whether state-dependent choices are needed at their owning checkpoints. Keep
stitching optional; clip-based branching is sufficient for M1. Use one fresh story
through checkpoints 2–6, then contrasting stories for M2 qualification.
