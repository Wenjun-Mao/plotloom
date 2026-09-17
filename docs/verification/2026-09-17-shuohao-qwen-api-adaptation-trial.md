# Shuohao/Qwen screenplay API-adaptation trial

This is one bounded, disposable comparison trial. It is not native execution
of the upstream skill, a Plotloom integration, a production-code/schema/template
change, a canonical-data mutation, Approval, creative acceptance, reliability
evidence, or checkpoint 3B acceptance.

## Question and frozen boundary

Can the current approved default Qwen profile produce a source-faithful,
reviewable 30-second screenplay in the upstream `novel-script` format when the
skill is supplied as a direct API prompt? The answer is narrowly yes for this
one corrected terminal excerpt, after two bounded corrective calls. It does
not show that a native skill runtime was used or that this result is superior
to either Terra or Plotloom.

Primary source is artifact `c749d5ca-b5d0-4551-a7fa-0a378202336c` in
`.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/trace-final.json`. The
frozen projection and seed came unchanged from
`.local/relay/shuohao-source-correction/run/`. They keep only four facts as
pre-entry typed state: both siblings are `坚定`, the shop is `修复中`, and the
pocket watch is `已修复`. The target summary instead owns the scene narrative:
tear the **shop-sale** contract, defer that transaction, complete the customer
promise, and leave debt risk and buyer dissatisfaction as consequences.

Accordingly, the author was forbidden to infer a physical shop repair from
`修复中`, to repair/restart the watch, or to substitute selling/delivering the
watch for selling the shop. This terminal source has no grounded opening hook,
next-episode cliff, or `hookBeat`; all three fields remain absent rather than
being invented.

The unchanged reference checkout is
`/Users/wjmao/projects/HU/reference-repos/shuohao-skills` at
`4322897e6d2bdaf66365534fd40194360c75a85f`. The complete
`skills/novel-script/SKILL.md` and its required `script-pass.md` and
`schema.md` references were supplied to Qwen. The Qwen request used the
upstream screenplay JSON shape—not Plotloom fragments, storyboard fields, or
the two-cue cap.

## Frozen calls and retained evidence

Ignored evidence under `.local/relay/shuohao-qwen-trial/` holds every request,
sanitized provider envelope, candidate, upstream output, rendered screenplay,
and report. `frozen-request.json` records the source-file hashes, public
profile snapshot, full secret-free primary request, request hash
`5c45f63bcc407a73c7222aa30983e53bf363cf2c705c1ae120293bc65c569990`, and
rubric hash `a53471e78fa33f416d529d5b5e1ffdac11b00540b31bdbf788a1a2579fb5ee46`.
It used the current default `qwen3527b` profile (hash
`20fba78c781d3139ecff71008e288daa078f833c04aa19a6b6f4c9e34c22ff95`):
temperature 0.2, 8,192 output tokens, compatible-v1, no request extension,
and provider-default reasoning. Credentials were only leased to the existing
OpenAI-compatible provider client and never recorded.

| Call | Frozen request | Provider request ID | Input / output tokens | Result |
| --- | --- | --- | --- | --- |
| Primary | `5c45f…6990` | `chatcmpl-5joMuIxWpnZxxfuaQtx4sRMBguDjkJ7E` | 6,876 / 499 | Valid JSON but 21.6s, below the 25.5s lower bound. |
| Correction 1 | `ab2f0…94cd` | `chatcmpl-igGTJbenQIOv9jeNHNLoZcpW73vz9H06` | 7,504 / 613 | Corrected duration to 27.44s; source-fidelity review then found missing buyer consequence and ambiguous shop-sale deferral. |
| Correction 2 | `f443f…4854` | `chatcmpl-o9R3XcRSPpNb5kEBmx8uZz5Pr2pcmoo2` | 7,677 / 623 | Final 28.78s candidate. |

The first correction responded only to the actionable duration failure. The
second responded to the independent concrete source-fidelity finding, not the
expected hook/cliff failures. There was no fourth call, profile/configuration
change, unknown-outcome replay, manual creative edit, agent runtime, or
provider other than the existing Qwen client. An initial local path check
wrongly resolved a fallback DeepSeek profile; it was detected before dispatch,
preserved as ignored preflight evidence, and replaced by a new frozen Qwen
request. No request was sent under that incorrect profile.

## Final candidate and checks

The final candidate opens by tearing a `卖店合同`, then says `这店，今天不卖。交易
暂缓。`; an off-screen buyer complains, debt remains unresolved, and the already
repaired watch is only handled between the siblings. This explicitly separates
the shop decision from the watch. It neither restarts the watch nor infers a
sign, renovation, or physical repair from the shop-state label.

The unmodified upstream commands ran against `candidate-03.json` with the
unchanged projected `outline.json`, `art.json`, and `cast.json`:

| Check | Result |
| --- | --- |
| `validate … --outline … --art …` | Exit 1 only for source-absent hook/cliff and missing `hookBeat`; duration, line length, speakers, action, beats, and source references pass. |
| `checkup` | Same two expected failures; it explicitly warns that its no-argument mode skips optional reference checks. |
| `render --md` | Pass; final screenplay retained as ignored `qwen-script-03.md`. |
| `render --html --cast` | Pass; final review report retained as ignored `qwen-script-report-03.html`. |

The rendered screenplay estimates 28.78 seconds, within the upstream 30-second
±15% range. It has six action beats and five attributed dialogue lines.

An independent attended Terra read-only review first found the missing buyer
consequence and ambiguity in candidate 02. It then reviewed candidate 03
against only the corrected projection and upstream writing/schema rules and
found no concrete source-projection blocker: repaired watch/no restart, explicit
deferred shop sale, buyer dissatisfaction, debt consequence, and the
shop-versus-watch distinction all pass. Its narrow non-blocking craft note is
that some action beats combine multiple ordinary moments, whereas
`script-pass.md` prefers one action per beat. The actions remain common and
filmable; the note is not a deterministic gate failure or creative Approval.

## Comparison and disposition

| Candidate | Model and format/context | Narrow observation |
| --- | --- | --- |
| Corrected Shuohao/Terra trial | Native attended Terra High; upstream screenplay format; 30.0s | Keeps the repaired watch and explicitly realizes the shop decision, buyer, debt, and customer delivery. |
| This Qwen trial | Current default Qwen API adaptation; full upstream instructions/schema/seed; 28.78s | After two bounded corrections, also keeps the repaired watch and realizes shop deferral, buyer dissatisfaction, and debt. |
| Retained Plotloom ending | Qwen runtime with Plotloom Scene-Beats/Storyboard fragment contracts, including its profile and cue-capacity context | The retained candidate accepts structurally but re-repairs/restarts a watch that is already repaired at direct entry. |

These are not matched causal experiments: their model paths, profiles, output
formats, prompt context, validation contracts, and dialogue/cue constraints
differ. One sample does not establish reliability or causal superiority for
Terra, Qwen, Shuohao, or Plotloom.

The only recommended next step is a separately approved investigation of a
thin, reusable screenplay-specialist API adapter for selected linear excerpts
and a complete source-grounded episode. It could replace the experimental
custom two-phase compact-semantic-to-full-fragment authoring machinery for this
screenplay use case, while leaving Plotloom responsible for graph entry states,
canonical binding, staleness, routing, storyboard, and audio ownership. No such
adapter is authorized here; custom two-phase integration remains paused.

## Scope and verification

This delivery changed only this receipt and the 3B tracker entry. No production
source, templates, schemas, profiles, environment, media, Approval state,
canonical or retained project data, reference checkout, or external skill
installation changed. The final repository check is `git diff --check`; no
broad suite is warranted for this docs-and-ignored-evidence trial.
