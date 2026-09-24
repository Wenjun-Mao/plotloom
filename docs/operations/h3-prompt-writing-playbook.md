# H3 prompt-writing playbook (living draft)

Checked 2026-09-24 against MiniMax H3 commit
[`d21241f`](https://github.com/MiniMax-AI/MiniMax-H3/tree/d21241f0a4b3acbb34c97dae47fa417b7065e438).
This is a working note, not a qualified reusable repo skill. Update it after
reviewed trials; retain failed prompt/media receipts unchanged.

## Official rules used by Plotloom

- [H3 prompt-writing skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/SKILL.md): identify I2VA for one initial image; write rewritten directions in English while preserving dialogue, lyrics, and visible text in their original language.
- [Base-mode guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/.agents/skills/h3-prompt-writing/references/base-en.txt): anchor `<Picture 1>` at 0.00 seconds; use the three named fields in order; start from the actual first frame and describe continuous action. Put speaker identity and delivery outside `<d>`; put only the language tag and verbatim spoken words inside. Put ambient and physical sounds in `overall_soundscape`, and background music in `non_diegetic_music`. A camera move should read as a natural English action. Soundscape needs concrete sound, not a repetition of dialogue or music.

This playbook is limited to Plotloom's current single-image I2VA route. Do not
reuse its form for T2VA, last-frame, or full-reference modes without reading
their official guide and recording a new contract.

## Ownership and review workflow

1. Start from the current accepted shot, resolved dialogue, visible cast,
   reviewed keyframe, audio plan, provider profile, and requested duration.
   The canonical Chinese story is the content authority; the image is the
   actual first frame. Source changes invalidate the direction review.
2. Draft English provider directions for every displayed non-dialogue source
   field. An agent may draft them. A person reviews the full package once,
   checking who moves what, where, and when. Do not turn “between two sockets”
   into “inserted into a socket” or promote an inferred consequence to fact.
3. Describe voice quality and performance in English outside `<d>`. Keep the
   dialogue text and punctuation exactly as authored inside `<d>`; do not
   repeat the line in action or soundscape. Preserve original-language
   visible text only when the scene actually contains it.
4. If the canonical audio plan has no ambient or physical event, explicitly
   review a small soundscape supplement grounded in visible action. It is an
   authored provider instruction, not a source fact. Avoid invented speech,
   music, weather sound, or off-screen events. `N/A` for soundscape is reserved
   for an explicit complete-silence instruction; `N/A` for music means no
   non-diegetic score is requested.
5. Open the complete compiled-prompt preview. Check first-frame alignment,
   English instructions, source fidelity, one stable speaker ID, one intended
   dialogue block, sound roles, and exact duration/profile. The preview hash
   and current source hash must match at job preparation. Preparation freezes
   the prompt; dispatch is a separate action.
6. Review the resulting full original with sound, then any proposed playback
   segment with sound, including boundaries. Record observations separately
   from hypotheses. A technically admitted clip is still unselected until an
   explicit audiovisual decision.

### Annotated opening-shot example (generated, audiovisual review pending)

Canonical action: `沈岚把铜质熔断器放在两条并列插槽之间。`

Reviewed English action direction: `The keeper places the brass fuse between
the two parallel sockets.` This describes placement, not insertion or an
electrical outcome.

Canonical dialogue remains `<d>[Chinese] 一枚，只够一边。</d>`. The speaker's
Chinese voice anchor and performance note receive separate reviewed English
directions outside `<d>`. The soundscape supplement, if used, must describe
only a physical sound the reviewer deliberately wants from that visible move.
The [complete offline compiled prompt and source mapping](../verification/2026-09-24-h3-reviewed-directions-offline.md), not this excerpt, is the wording review artifact. The separate [C trial receipt](../verification/2026-09-24-u4-h3-reviewed-english-trial.md) records one matching live dispatch and retained media; listening remains open.

## Evidence ledger and open questions

| Status | Finding | Evidence / limit |
| --- | --- | --- |
| Observed | A contained the intended line and earlier unclear speech. | [First trial](../verification/2026-09-23-u4-real-shot-trial.md); the agent could not transcribe audio. |
| Observed | In B the director identified the extra spoken sentence as the canonical Chinese action. The stronger “only vocal utterance” soundscape condition did not resolve it. | [A/B receipt](../verification/2026-09-24-u4-h3-vocal-control-comparison.md); both originals and six-second proposals remain unselected. |
| Contract mismatch | Both trial prompts put Chinese action and voice directions outside `<d>`, contrary to the official English rewrite rule. | Exact frozen prompts in the two retained jobs; [ADR 0083](../adr/0083-h3-single-image-prompt-contract.md). |
| Hypothesis | The model treated a Chinese direction as something to speak. | The observed utterance matches source action, but this is not proof of model mechanism. |
| Unverified | Reviewed English directions may reduce the extra speech while preserving the intended line and image action. | One bounded C clip exists; human listening and visual story review are still required. |
| Observed | One reviewed-English v3 trial ingested an eight-second H.264/AAC original and an exact six-second proposed segment using the same keyframe and request controls. Both remain unselected. | [C trial receipt](../verification/2026-09-24-u4-h3-reviewed-english-trial.md); technical delivery and browser media readiness only. |
| Pending director review | Whether C omits the extra spoken action sentence, preserves intelligible intended dialogue, and visually communicates the undecided fuse placement. | Listen to C's full original and six-second proposal, including boundaries; the agent could not assess Mandarin audio. |

The vocal-control comparison instruction is retired for new trials. Historical
job B retains its exact frozen text for audit. Revisit prompt advice only after
the guide-compliant C audiovisual review; if that result
still fails, a focused external consultation can evaluate prompt and media
evidence without inventing a mechanism.

## Promotion into a repo skill

Keep this playbook as the single knowledge source. A future thin repo skill may
point to it once agents can repeat the review and one or more representative
guide-compliant trials are assessed. Promote stable rules and examples only;
leave hypotheses and failed conditions visibly labelled here.
