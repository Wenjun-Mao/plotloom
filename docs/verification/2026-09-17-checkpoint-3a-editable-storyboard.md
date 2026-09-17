# Checkpoint 3A editable-storyboard receipt

Captured 2026-09-17 against local candidate `4e655b8`. This records the bounded
checkpoint-3A implementation and evidence. It is not director/product
acceptance, Storyboard Approval, audiovisual approval, or checkpoint-3B
qualification.

## Delivered boundary

- The reviewed-proposal action rereads canonical stage heads before it starts a
  run. Missing/stale Scene Beats requests `scene_beats` plus `storyboard`;
  current Scene Beats with missing/stale Storyboard requests `storyboard` only;
  both current reports a no-op. A non-current Bible or Graph is rejected.
- It writes none of the Brief, Bible, Graph, or unchanged drafts. It uses the
  existing pipeline, editor pages, Trace, Quarantine, exact work-unit repair,
  and rebuild owners. It adds neither an approval nor a retry/recovery policy.
- The ownership/currentness contract is [ADR 0054](../adr/0054-editable-storyboard-continuation-currentness.md).
  The short existing-capability map is
  [checkpoint-3a-storyboard-continuation-map.md](../roadmap/checkpoint-3a-storyboard-continuation-map.md).

## Automated evidence

| Check | Result |
| --- | --- |
| `npm --prefix frontend test` | 16 files, 158 tests passed. |
| frontend typecheck and E2E typecheck | passed. |
| targeted production browser: proposal continuation | passed: upstream byte/revision preservation, admission failure, Scene Beats + Storyboard range, saved Scene Beats edit/reload, Storyboard-only range, and current no-op. |
| targeted production browser: exact repair | passed: a quarantined Scene Beats shard was server-authorized, repaired exactly, and persisted after reload. |
| full serial production browser suite | 46 tests ran; one native H3 playback/restart test exceeded its 45-second timeout. Its isolated retry passed in 18 seconds. This is retained as a full-suite flake, not silently treated as a clean full-suite pass. |
| deterministic frontend build | passed and refreshed `src/plotloom/static/`; Vite retained its existing over-500kB chunk warning. |
| `uv run --locked pytest -q` | 557 passed; one FastAPI/TestClient deprecation warning. |
| wheel build and installed-wheel smoke | passed. |

An independent Terra review found the touched generation control still used a
nested ternary, prohibited by the approved scope. The candidate was changed to
explicit conditionals, rebuilt, and independently re-reviewed with no remaining
selection findings. Neither review claimed product approval.

## Bounded reference continuation

Retained checkpoint-2 evidence resolves `潮汐译信` exactly to project
`cdc51baf-ca13-4c5a-9afb-238058e6043e`, not a guessed project. Before the run,
its Bible and Graph were ready at revision 2 (Graph bound to Bible r2); Scene
Beats and Storyboard were missing at r0. The unchanged default profile was
available with the server-held credential. The one authorized continuation was
run `38d0b016-43d3-41fe-8da3-66852725b8ce` for exactly
`scene_beats, storyboard`, with no image, H3, media, profile, or environment
change.

All eight Scene Beats work units sealed. Storyboard units 1–6 accepted, but
unit 7 exhausted the frozen three-attempt correction allowance and was
quarantined for `semantic.required_entity_not_in_shot`. The server reports
exact-repair eligibility and stage rebuild eligibility; no repair was started
automatically. Atomic installation therefore left Scene Beats and Storyboard
missing at r0, while the authored Bible/Graph r2 stayed intact.

At the sealed Scene Beats level, the letter-to-reversed-tide dilemma and its
city-versus-brother consequences are causally legible, with explicit entity
states and scene-level continuity transitions. Dialogue exists with timing
units, but it is sparse and repeats the central choice formulation. Because no
Storyboard aggregate installed, shot-level continuity, dialogue/audio
performability, timing, and final storyboard gates cannot be accepted. There
is no Approval. The quarantined required-entity issue is an actionable 3B
quality/recovery gap, not a reason to relax validators or invent repair
semantics.

The owned local runtime stopped after evidence capture.
