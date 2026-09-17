# Checkpoint 3B action/state realization experiment receipt

This is one bounded, disposable Scene Beats authoring experiment. It is not a
production gate, implementation change, schema or validator decision,
Storyboard Approval, human creative approval, or checkpoint 3B acceptance.

## Diagnosis and boundary

The previous causal-conflict receipt is corrected as evidence: its reduced A
input said that the siblings repaired the watch but did not state that repair
occurred after the supplied entry state. Its two `no_conflict` responses
therefore neither established a hard upstream contradiction nor model
incapability.

The actual retained defect is in accepted Scene Beats candidate
`174b27c4-e95a-4ff7-b9cf-6c8c6f250001`, beat
`b523bcf6-0205-5e42-b0cc-b61d7577d84c`. It describes `共同修复怀表`, gives
the purpose `展示姐弟合作修复怀表的过程`, and gives the immediate result
`怀表恢复功能，承诺得以履行。`; its entry and exit both already declare
`prop_pocket_watch=已修复`, with an empty continuity delta. The downstream
Storyboard copied that repair action. This is an author-realization/content
defect, not evidence that the typed direct-entry compiler failed.

The sell-path/join predecessor-context problem remains deferred. No canonical
project, source, provider profile, application configuration, production run,
scene, watch state, media item, or Approval changed.

## Frozen two-request design

Both direct requests replayed the complete primary Scene Beats prompt from
artifact `c749d5ca-b5d0-4551-a7fa-0a378202336c` in retained trace
`.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/trace-final.json`, including
its original messages and embedded `scene_beats.fragment.v13` schema. This is
a disposable direct transport exercise, not a historical pipeline replay.

The baseline payload was byte-for-byte the saved message pair. The treatment
changed only the final user message by appending one generic action/state
coherence paragraph: entry facts hold before the first beat; observable event,
purpose, and immediate result must not establish an already-true state without
a sourced new cause; a valid change stays in one beat; and the continuation
must be consequential rather than merely repeat labels. The paragraph names no
watch, character, story-specific resolution, or desired action.

The frozen request hashes were:

| Variant | Request SHA-256 | Direct provider request | Usage |
| --- | --- | --- | --- |
| Baseline | `12dacac187c1eea786542076bd951a25c8e7d3dfb0403190769411c18e2a6d79` | `chatcmpl-JPHHr6zkBaKaFn1d4il1ChG3wA9Evyjn` | 6,523 input / 2,128 output tokens |
| Treatment | `170fa69d65afba60527c4bb87e38be8f7d6627e5ae7f9496e3287dbb74a6d887` | `chatcmpl-HbMhGtlKV1NtQeCrCFZrRGNDkIAI64p7` | 6,612 input / 2,304 output tokens |

Current default profile v11/hash
`6f0e6d29521b4d19b2bf1e8dd7410de72355390e20d916289b8d8ad6e9567473`
exactly matched the retained source profile. Both used that unchanged approved
profile: `qwen3527b`, `final_only_v1`, temperature 0.2, 8,192 Scene Beats
tokens, `chat_template_kwargs.enable_thinking=false`, and existing 10-second
connect/600-second attempt limits. Credentials were obtained through an
ephemeral one-use lease and are absent from retained evidence.

Before either call, the complete secret-free payloads, their hashes, exact
message diff, profile comparison, and evaluation rubric were frozen in ignored
`.local/relay/3b-realization-experiment/`. Exactly one completed direct call
was made for each variant; there were no retries, corrections, prompt-tuning
calls, or provider-state writes.

## Offline validation and blinded review

Both final responses were valid JSON and passed the current owner’s
`SceneBeatsFragmentOutput` schema model offline: one scene, two beats, and two
dialogue cues each. That is shape validation only; the isolated experiment did
not build or install a canonical plan, so no output status was treated as a
content pass.

An independent attended Terra review received the secret-free outputs as
anonymous cases A/B and their rubric before their variant mapping. It found:

- Case A (then revealed as baseline) has a consequential contract-tearing
  action, but describes the watch as `刚刚修好`, says it `重新开始走动`, and
  records `完成修复` despite the already-repaired entry state. It fails the
  substantive coherence criterion.
- Case B (then revealed as treatment) adds a real contract-tearing transition
  and consequent debt decision, but its scene entry note says the scene starts
  after the tearing while beat 1 performs that action. Beat 2 still says the
  already-repaired watch `重新开始走动` without a sourced new cause. It also
  fails the substantive coherence criterion.

Thus both variants pass shape but fail the predeclared provisional content
standard. The treatment is not a success: it improves one consequential
continuation while retaining the resolved-watch restatement and introducing a
separate scene-entry ordering mismatch. One stochastic pair cannot prove a
causal effect or general reliability.

## Disposition

Tracker state: **experiment complete; checkpoint 3B remains not accepted**.
No automatic prompt integration, production gate, schema/validator/template
change, or manual Scene Beats/Storyboard repair follows from this result. No
third call is authorized in this experiment. A later, separately authorized
study may evaluate a more specific contract-level authoring change, but must
first define its changed ownership and acceptance criteria; this receipt is
negative evidence for the generic paragraph alone.

The retained local evidence includes frozen payloads, hashes, sanitized response
envelopes, model-level offline shape reports, and the anonymous review pack in
`.local/relay/3b-realization-experiment/`. It contains no credential or
canonical project mutation.
