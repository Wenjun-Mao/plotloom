# Shuohao screenplay reuse trial — retained 3B keep ending

This is one bounded, disposable, source-first feasibility trial. It is not a
Plotloom integration, a production-code change, canonical data mutation,
Approval, human creative acceptance, or evidence that Shuohao is better than
Qwen. Checkpoint 3B remains unaccepted.

## Result

The upstream `novel-script` workflow can turn a small, transparently projected
terminal route into a reviewable screenplay with useful deterministic checks
and a rendered report. It is a promising *authoring-adapter* candidate, not a
drop-in replacement for Plotloom's interactive pipeline. The actual result is
a coherent but thin 28.6-second endpoint excerpt. Its four dialogue lines and
six ordinary visual actions retain the decision consequence (debt risk and
fulfilling the customer promise) without repairing the watch again.

The final upstream check has one deliberate failure: an excerpt that begins
after the choice and has no following episode has no source-grounded opening
hook or ending cliffhanger. We did not manufacture either. The report HTML and
Markdown were still rendered for review, but the Markdown header mechanically
claims that empty hook text is "兑现" through `hookBeat`; that display is not
evidence of a hook. The checkup is the authoritative deterministic result.

## Frozen inputs and provenance

The retained source is primary Scene Beats prompt artifact
`c749d5ca-b5d0-4551-a7fa-0a378202336c` in
`.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/trace-final.json`. Its
target is `结局：留下店铺`; the chosen edge is `撕毁合同，留下店铺`. Before
entry, the contract is already torn, the sale is deferred, the shop is
`修复中`, the pocket watch is `已修复`, the siblings are `坚定`, and debt risk,
buyer dissatisfaction, and reconciliation remain consequences. The source
summary says the customer promise has been fulfilled; the trial therefore does
not depict a repair or a restart.

The untouched reference checkout was
`/Users/wjmao/projects/HU/reference-repos/shuohao-skills` at
`4322897e6d2bdaf66365534fd40194360c75a85f` (Apache-2.0). Its complete
`skills/novel-script/SKILL.md`, `references/script-pass.md`,
`references/schema.md`, and relevant `novel-script.mjs` CLI implementation
were read before use. A read-only `git fetch --dry-run origin` advertised
upstream `main` at `7ebef4f`; this trial intentionally used the supplied clean
checkout revision and did not fetch, alter it, install a skill, or copy its
source into Plotloom.

`project-source.mjs` in ignored
`.local/relay/shuohao-comparison/` deterministically extracted only the two
characters, shop, watch, selected route, exact direct-entry states, target
summary, and 30,000-unit allocation from that artifact. It projected them as
the upstream `outline.json`, `art.json`, and `cast.json` ID vocabulary:
`C01`/`C02`, `S01`, and `P01`. Thirty seconds is source-projected from the
frozen allocation, not an authorial duration choice. The upstream-required
`hook` and `suspense` fields are empty because this endpoint supplies neither;
the source's already-true route decision is not recast as a new hook.

## Actual workflow and evidence

The unmodified upstream commands seeded, validated, checked, and rendered the
trial. The artifacts, including the Terra High author's raw response, draft
revisions, command output, Markdown screenplay, and HTML report, are ignored
local evidence at `.local/relay/shuohao-comparison/run/`.

1. `seed outline.json --eps 1` yielded one empty 30-second episode skeleton.
2. A native Terra High author received only the seed-derived facts and the
   upstream screenplay constraints; it was not shown either prior compact or
   expanded Plotloom answer. It authored one 10-beat, one-scene draft.
3. Draft 0 failed two upstream gates: the truthful missing hook/cliff and a
   mechanical action-prose failure caused by quotation marks around a sign.
   Revision 1 removed only those quotation marks. It did not change story
   facts, then passed the other nine gates. No second content revision or
   unbounded loop occurred.
4. `render --md` and `render --html --cast` produced a readable screenplay and
   report. `scripts/selftest.mjs` passed all 154 upstream assertions.

| Deterministic gate at revision 1 | Result |
| --- | --- |
| 30-second duration, line length, speaker, action, and upstream refs | pass |
| Hook opening claim location | mechanically pass but semantically inapplicable with empty hook |
| Hook and cliff on paper | fail, intentionally and transparently |
| Upstream validation | fail with exactly that one gate |

## Comparison and review

The identical retained Plotloom ending candidate is artifact
`174b27c4-e95a-4ff7-b9cf-6c8c6f250001` from the same prompt attempt. Its
validator accepted a 30-second Scene Beats fragment, but its second beat says
the siblings repair the watch and its action says the second hand starts again,
despite the direct-entry contract already setting the watch to `已修复`.
The Shuohao/Terra excerpt instead checks an already-running watch and prepares
it for delivery. This is a source-fidelity improvement in this one comparison,
not evidence that the skill alone outperforms Qwen: the retained candidate used
the Qwen runtime and Plotloom fragment contract, whereas this trial used a
native Terra High author following Shuohao instructions.

No Qwen same-profile trial was made. There is no existing same-profile agent
runtime for native execution of the Shuohao workflow, and constructing one is
out of scope. A direct current-profile chat call would be an API adaptation,
not native skill execution, and would confound the bounded comparison.

An independent attended Terra read-only review inspected the source artifact,
projection, final script, render, deterministic output, retained Plotloom
candidate, and expansion receipt. It found the excerpt coherent and faithful
to the post-choice state, and confirmed it does not re-repair the watch. It
also found concrete limitations: buyer dissatisfaction is not visible or
spoken, the joint repair happens only off-screen, the audiovisual palette is
mostly object handling and a final look at the door, and the rendered hook
label overstates an empty source field. It blocks any claim that this is a
validator-ready complete episode or creative approval, not this bounded reuse
finding.

## Reuse recommendation

**Do not resume the custom two-phase integration.** First evaluate a small,
separately authorized adapter slice only if a user needs screenplay authoring
for a *complete* linear episode.

| Category | Finding |
| --- | --- |
| Directly reusable | Outline-to-seed projection, structured action/dialogue screenplay shape, duration/line/speaker/action/reference gates, Markdown/HTML reviewer report, and role-oriented line book. |
| Thin adapter needed | Plotloom-ID-to-outline/art/cast projection; explicit linear-excerpt mode that disables rather than falsely satisfies hook/cliff gates; a report that omits empty-hook fulfillment language; tracked source attribution and output quarantine. |
| Interactive-only gap | Graph direct-entry/join contracts, typed state validation, canonical IDs/binding, stage staleness, route selection, and Plotloom's storyboard/audio ownership remain Plotloom responsibilities. |
| Likely removable complexity if an adapter is accepted | The experimental compact-semantic-to-full-fragment expansion path may be unnecessary for screenplay authoring. This is not authorization to remove it or any current production behavior. |

The screenplay's thinness also argues against treating a passing structural
shape as a quality gate. A future complete-episode trial would need an actual
source hook, an actual ending rather than a terminal excerpt, and separately
reviewed audiovisual consequence; it must not fill those gaps by invention.

## Checks and scope

Executed: upstream `validate` and `checkup` for both drafts; upstream Markdown
and HTML render for revision 1; upstream `selftest.mjs` (154 assertions); and
the repository docs-only `git diff --check`. No provider/media call,
credential/profile/config change, canonical/project write, Approval, retained
data change, production source change, or reference-checkout write occurred.
