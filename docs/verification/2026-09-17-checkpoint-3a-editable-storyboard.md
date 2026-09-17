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
| retained full serial production browser suite | 46 tests ran; the selected-pair test exhausted its own 45-second budget. The retained trace shows native playback completed, restart/reload began at +37.88s, reload itself completed in 75ms, route-selector hydration took 4.40s, and the post-restart player visibility check was still pending at the deadline; the `GET video-jobs` began only after teardown at +45.23s. The isolated run passed in 18.1s. This is test-budget exhaustion from combining independent contracts, not a stalled API or a clean full-suite pass. |
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

## Follow-up: prospective entity-presence correction and one current continuation

The retained run above remains frozen evidence and was not edited or repaired.
Its `semantic.required_entity_not_in_shot` failures were valid: required state
membership is shot depiction, while the missing brother and mailed letter are
world/continuity facts. The demonstrated fault was the correction contract: it
gave the model a generic add-or-delete instruction without source-bound
same-shot membership, action, or composition context.

The prospective correction records that context in
`RequiredEntityPresenceRepairFact`; its directive prefers deleting an
off-screen requirement and permits membership only when the shot actually
depicts the entity. The strict membership validator is unchanged. [ADR
0055](../adr/0055-storyboard-required-entity-presence-correction.md) records
the ownership boundary. New primary and correction prompt identities are
versioned; no old prompt, plan, hash, or retry evidence was rewritten.

Focused regression covers the off-screen brother/mailed-prop case, a genuinely
depicted state, strict rejection, directive evidence, and rejection-source
provenance. An independent Terra read-only review reported no findings.

### Current-contract continuation

The supported path was a fresh pipeline continuation, not exact repair: run
`d8fa2bc5-102f-409b-a8cb-851789a573a4` requested only `scene_beats` and
`storyboard` from the unchanged default local profile. Its immutable snapshot
retained Bible r2 hash `8c1db99d…a7859f6` and Graph r2 hash
`b5e7ad75…9176a4d5`. It sealed all 8 Scene Beats and all 8 Storyboard units,
then atomically installed Scene Beats r1 (8 scenes, 16 beats, 15 dialogue
cues) and Storyboard r1 (15 shots). One Scene Beats primary response failed
`semantic.continuity_beat_sequence_mismatch`; the existing visible bounded
correction succeeded. There were no quarantines and no further dispatch.

Storyboard r1 has 43 required entity states and none is outside same-shot
membership. Gate set `storyboard.v2` passed all 508 results. It has no active
Approval and no approval decisions. The scene progression carries the letter,
branch choice, city/brother consequences, join, and two endings through
editable fields; dialogue is nevertheless sparse and repeats the central
choice/apology. This is engineering evidence only, not human creative
acceptance or checkpoint-3B qualification.

### Follow-up verification

| Check | Result |
| --- | --- |
| focused generation contract tests | 49 passed |
| `uv run --locked pytest -q` | 559 passed; one existing FastAPI/TestClient deprecation warning |
| frontend unit and typecheck | 158 tests passed; typecheck passed |
| deterministic frontend build/static freshness | passed; existing over-500 kB Vite warning remains |
| retained full serial production browser suite | 45/46 passed; the timeout was caused by the preceding combined native-playback and restart-persistence test budget, not by `GET video-jobs` itself. |
| isolated `video-pilot` diagnostic | passed in 18.1s; this does not establish a playback failure |
| wheel build and installed-wheel smoke | passed |

Logs and live API evidence are retained under the Relay assignment scratch
directory. The owned runtime was stopped after evidence capture.

### Checkpoint-closeout test rationale

Native selected-pair progression/final hold and file-SQLite restart persistence
remain separate, meaningful production contracts. The retained timeout combined
both after the same costly fixture setup, so the test process reached its
per-test deadline while the post-restart page was still hydrating; Playwright
then closed the request context before the final API assertion could start.
The tests are therefore split without increasing the global timeout, adding a
retry, removing an assertion, or changing playback behavior. The native test
retains real media progression, restart, and final-hold checks. The persistence
test retains selected-ID, exact byte-range, reload, and backend-restart checks.
The preserved original trace and serial log, plus the serial traced
`video-pilot.spec.ts` repeat-each-three evidence, are kept in the checkpoint
closeout Relay scratch directory. This is engineering verification only; it
does not change Storyboard Approval or checkpoint-3B status.

### Checkpoint-closeout verification

The presence-repair extraction preserves the original full
`StoryboardFragmentOutput` parse before its narrow fact projection; malformed
fragments fail closed and cannot mint a repair fact. `work_units` re-exports
the moved fragment models and fact, so its current correction union and public
imports remain intact. An independent Terra read-only review found no P1/P2
findings after this check.

| Check | Result |
| --- | --- |
| focused generation/continuity/work-unit contracts | 94 passed |
| locked Python suite | 559 passed; one existing FastAPI/TestClient deprecation warning |
| frontend units, TypeScript and E2E typecheck | 158 unit tests passed; both typechecks passed |
| deterministic frontend build/static freshness | passed; existing over-500 kB Vite chunk warning remains |
| selected-pair serial traced reproduction | two split tests × three repeats passed; six retained traces, with no failure attachments |
| full single-worker production browser suite | 47 passed in 8.3 minutes |
| wheel and installed-wheel smoke | passed; wheel SHA-256 `07c9840388df4eeae0bd0b8f4012c2d98efb13f2c1f7665d60e44f915e618146` |
