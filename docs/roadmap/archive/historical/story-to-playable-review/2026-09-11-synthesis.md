# External review synthesis — 2026-09-11

> **Archive status (2026-09-18):** Historical/supporting record retained for context and evidence; it is not an active delivery plan or a completion claim. See [the roadmap entrypoint](../../../README.md).


Status: **recommendations for discussion**, not an approved architecture amendment
or implementation authorization. The published roadmap and ADR 0026 are unchanged.

**Subsequent disposition, 2026-09-11:** the user authorized roadmap/ADR amendments.
The accepted P0 three-way boundary and adjoining-shot direction are now captured
in ADR 0026 and the roadmap; the [P0 implementation plan](../../superseded/2026-09-11-p0-imported-still-preview-plan.md)
revision 1 was subsequently approved by the user on 2026-09-11. The assessment below records the original review, not a
retroactive acceptance or implementation claim. Raw reports remain unchanged.

## Evidence and preservation

Reviewed both supplied reports. Originals remain unchanged in the user's local
Downloads directory; this note does not republish them or imply GitHub access:

| Report | Original filename | SHA-256 |
|---|---|---|
| A | Reviewer A — creative workflow and audiovisual continuity.txt | `a5dbbff902e498cc17cef7766d4e33ebbd99bcfed271cec30d81978749f7cab6` |
| B | Reviewer B — architecture boundaries and bounded delivery.md | `674df20615ec6663921c23129162cbd99c7709c7aad8db90f3c27bca22a92d7b` |

A inspected the planning packet, not implementation or creative outputs. Its
creative findings are hypotheses/editorial judgments. B reports targeted source
inspection, not execution. Both distinguish source `9afbefd` from packet
`d6e705ddb96aa1f048c5a46b9a934f89b854767b`. Local HEAD matches the packet and
`git diff 9afbefd HEAD -- src frontend` is empty. No reviewer agreement is treated
as acceptance, provider performance evidence or authority to modify code.

## Recommendation

Keep the overall direction and existing implementation. Tighten P0's authority
boundary and bring the adjoining-shot experiment forward. No full rewrite,
additional consultant round or provider platform is justified by these reports.

Three distinct paths need an explicit ADR amendment before P0:

1. Import/explore: preserve originals and provenance; keep candidates and proposed
   visual details separate from canonical narrative authority.
2. Reviewed still preview: a non-generative immutable projection of the exact
   approved storyboard, selected images, reference context and authored timing.
3. Provider production: still blocked until its complete snapshot/admission and
   task lifecycle are implemented. A preview is not a disguised production task.

The useful first deliverable stays small: import four real images, compare two
alternatives, select three consecutive shots in one scene, play a labelled still
animatic, refresh/restart and reopen it. Replacing a selection or changing the
board must preserve the old projection and mark its applicability accurately.
Three shots is the pilot fixture, not a permanent story or API constraint.

## Insight dispositions

`Use` means recommend incorporating at the stated stage, not silently accept it.

| Disposition | Insight | Action / boundary |
|---|---|---|
| Use — P0 | B: explicitly authorize reviewed still preview as well as exploration | Amend ADR 0026 and cross-reference the controlling 0012/0016 rules before implementation; retain provider hard stops |
| Use — P0 | B: reuse content-addressed byte storage, add distinct managed-asset provenance | Do not fabricate generation runs or relax text-evidence ownership; identical bytes may have different provenance records |
| Use — P0 | B: revisioned selections, owned assets and coherent frozen preview | Guard lifecycle, expected revisions and applicable Approval on the server; preserve candidates on conflict |
| Use — P0 | A: three frames should depict one dramatic moment | Use readable geography, action start/end and emotional intent, not unrelated beauty shots |
| Use — P0 | A: make proposed details visible | Separate look selection from narrative changes; support neither/keep/refine; disclose which attributes vary |
| Use — P0/P3 | A: compact continuity strip and cut replay | Derive from existing story/selected intent; unresolved additions remain proposals, not a fifth authoritative stage |
| Test — P0 | B: corrupt blobs, decoding limits, cross-project access, races and retention | Focused fixtures and one real FastAPI browser journey; no live provider needed |
| Test — P2 | A: one clip, then its neighbour before expansion | Keep first clip as technical milestone; require adjacent clips and their audio transition for cross-shot creative confidence |
| Test — P2/P3 | A: native audio sufficient for this scene | Test two distinct short cues by the same speaker, sound boundaries and the final choice hold; documentation cannot establish perceived voice consistency |
| Use — P1/P2 | B: execution, ingestion and cancellation are distinct | Do not retry generation to repair a failed download or classify monitoring exhaustion as remote failure |
| Test — P1/P2 | A/B: capability combinations, prompt expansion and duration handling | Verify the chosen endpoint, then a bounded authorized live attempt; no silent reference dropping, prompt invention or retiming |
| Use — Q | B: separately version independent qualification | Preserve legacy two-profile evidence; finish a narrow independent mode before nine-run qualification |
| Test — P4 | A/B: joins depend on depiction and runtime context | Small branch fixture; preserve differing state, interpret incoming-edge variants explicitly, never heal state to fit footage |
| Park | General asset library, reference atlases, voice library, full timeline/mixing, multi-shot batching, scripting framework, automatic ranking/GC | Reopen only for demonstrated pilot need |
| Discard | Interpret current hidden worker defects as active production incidents | The path is hard-blocked; these are future implementation risks, not reproduced live failures |
| Discard | Treat reviewer recommendations as proof of media fidelity or permission to spend | Neither reviewer generated/inspected actual pilot output |

## Claims checked locally

These checks were targeted source inspection, not runtime tests or a complete audit.

| Claim | Local evidence | Assessment |
|---|---|---|
| Still preview needs a clearer authority amendment | [ADR 0016](../../../../adr/0016-versioned-authoring-quality-gates-and-approval.md), media-boundary paragraph | Confirmed: rule explicitly includes reference bindings, not only remote calls |
| Existing byte store is reusable but imports need separate ownership | [artifacts.py](../../../../../src/plotloom/artifacts.py), `put/get`; [persistence.py](../../../../../src/plotloom/persistence.py), `add_artifact` | Confirmed: hash-addressed bytes; run/attempt lineage is required for generation evidence |
| Existing-path put does not validate existing bytes | `LocalArtifactStore.put` returns when path exists; `get` verifies hash | Confirmed source behavior; import must verify usable bytes before publishing its record; no general repair system needed |
| Legacy worker is not ready to reopen | [media_jobs.py](../../../../../src/plotloom/media_jobs.py), `_execute_task`, `_poll`, `_succeed` | Hard stop confirmed; unreachable legacy uncertainty/failure/output-URI semantics need bounded replacement before P1 |
| Legacy adapters silently constrain inputs | [media.py](../../../../../src/plotloom/media.py), `references[:4]`, `max(4, _duration(params))` | Confirmed source behavior, not validated contemporary endpoint limits |
| Join compiler is not a complete playback state engine | [join_state_values.py](../../../../../src/plotloom/join_state_values.py), `compile_join_state_value_contract` | Explicitly excludes initial-state inference/arbitrary propagation; preserves `join_variant.v1` descriptors |
| Q still requires two profiles | [alpha_acceptance.py](../../../../../src/plotloom/alpha_acceptance.py), constants, `run_alpha_acceptance`, CLI | Confirmed executable cardinality guard; not merely stale prose |

Provider facts in A's report are not newly reverified by this synthesis and are
not accepted as implementation specifications. Prior planning documentation
checks do not establish account availability or audiovisual quality. Recheck
the exact selected endpoint before relying on reference/audio combinations.

## Refinements to the reviewers' proposals

- B suggests persisting each selection and preview projection together. The
  necessary invariant is coherent admission, not building a full projection on
  every selection click. Prefer revisioned selection transactions plus an atomic
  validated capture when creating a preview, unless the final UX requires the
  stronger coupling. Exploration must remain usable before a board is approved.
- A's continuity strip should expose existing facts and selected intent. Missing
  geography/emotional facts must stay proposals; a derived UI must not quietly
  create a second continuity authority or an exhaustive new ontology.
- A's scratch dialogue reading is a cheap optional editorial experiment, not a
  requirement to build recording/TTS in P0. A manual read alongside stills suffices.
- Early native-audio trials may reveal a voice mismatch. Do not promise voice
  preservation from an endpoint's generic audio support. Keep unsupported
  constraints visible and make expansion conditional on the observed result.
- Pause-and-choose remains unchanged. Finish speech/action and sound tails before
  stopping audio/holding the frame. Persistent ambience or automatic trimming
  would be new decisions, not implicit polish.
- A's selective-framing remedy can permit genuinely compatible shared shots
  without erasing differences. When a difference matters again, its state still
  exists and needs compatible media or an explicitly authored reconciliation.

## Recommended next steps

1. Discuss/accept these bounded roadmap changes, particularly P0's three-way
   boundary and the two-shot creative test; then amend only the relevant records.
2. Write one P0 implementation brief around the four-image/three-shot journey,
   managed provenance, revisioned bindings, still projection, controlled serving
   and retention. Keep providers/qualification/story generation untouched in P0.
3. Implement P0 with one owner and focused checks, then existing stable-candidate
   gates and the actual browser journey. No new orchestration infrastructure.
4. Keep Q visibly open and separately scoped. Do not start a paid video trial or
   change frozen qualification inputs as an incidental part of P0.

This review created only this synthesis note. Originals, source and published
planning packet remain unchanged; no commit/push, generation or test acceptance
was performed. Usage/cost deltas are unavailable. This note is local, not a new
GitHub-ready consultation packet; sharing it or the originals requires an explicit
publication step and appropriate access checks.
