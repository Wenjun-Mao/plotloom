# Checkpoint 3B contrasting-story qualification receipt

Started 2026-09-17 from local `main` revision
`3b8d8a0d7ef2f2e3f037b710c1c4acd04c6d8698`. This is a bounded runtime
qualification record, not Storyboard Approval, human creative approval, or
checkpoint-3 acceptance. It uses the current production runtime and its existing
default local text profile without changing credentials, profiles, environment,
source, frontend assets, or provider settings.

## Frozen input before the first request

| Field | Frozen value |
| --- | --- |
| Working title | `旧修表铺的最后一天` |
| Chinese synopsis | `在母亲留下的老街小修表铺即将被买家收购的最后一天，姐姐林晓岚坚持卖店偿还债务并搬离旧城，弟弟林远坚持保留修表铺完成母亲未竟的承诺。两人整理柜台时发现一只母亲未完成的旧怀表；表盖里的订单纸条让他们想起：林远曾答应一位等候多年的顾客，在母亲去世后亲手修好这只表。买家傍晚到店签约，姐弟必须在期限前决定出售店铺、带着怀表离开，还是暂缓交易共同完成修复。选择要让姐弟各自承担清晰后果，两个结局分别呈现卖出与留下后的关系和责任。` |
| Genre and visual direction | `家庭现实主义剧情`; `自然光、克制写实、老街小修表铺` |
| Language, aspect, target duration | Simplified Chinese; 16:9; 180 seconds |
| Existing structure defaults | 2 decisions per path; 2 endings; node budget 8; maximum out-degree 3; desired merges 1; 1–4 shots per scene |

The premise is grounded and dialogue-led: two adult siblings disagree under a
buyer deadline; the unfinished watch anchors a promise already made by one
sibling. It contains no supernatural element. The first request has not yet
been sent at this point.

## Runtime journey and revision evidence

The current accepted local runtime was launched with `uv run --locked plotloom`
and exercised in the attended browser UI. The fresh project is
`700648eb-cfc8-4de0-8fab-f40bad86a4d4` (`旧修表铺的最后一天`). No project,
provider, or database values were edited outside that UI.

| Step | Run / resulting revision | Evidence |
| --- | --- | --- |
| Normal proposal (once) | `d97bdcc9-11de-475e-b75b-234052cce5fe`; Bible r1 `18a824db33cd62d56d3335a7d2c32ae04f3db71bafd518fe3ef88f2902aa5d4a`; Graph r1 `d8c6f87caabeb192a85b4e69d9af685358386310f895d1a4f3cc7e5adfdd8860` | Succeeded. It established the buyer deadline, the debt-versus-promise conflict, and two stated end states. The graph used its existing bounded correction policy; no manual retry was made. |
| Normal downstream continuation (once) | `bcbcea07-cd65-405a-b320-9a455dc1a977`; Scene Beats r1 `9d768cb5295ddc86014866dcc9ca81202771684558aad5df0a30911884dbbac1`; Storyboard r1 `69b4c9f3f891cf6bcb95822bd120acdec3d528b99435be7f887be656adc5b046` | Succeeded. It produced 9 scenes, 18 beats, 16 dialogue cues, and the initial Storyboard. Existing bounded corrections on Scene Beat 2 and 5 were accepted by the runtime; no additional run was initiated. |
| Normal shot authoring and reopen | Storyboard r2 (later stale) `6bf7687493393a48e4391fb5908c2963c3146ef7cedf5f41a6456f6ac551b877` | In the Storyboard editor, shot `6671905a-7947-5550-82aa-058768bad124` was edited and saved, then the page was reloaded. The saved action and composition were visibly present after reload. |
| Canonical dialogue authoring | Scene Beats r2 `30fec0a9653cb73d85b2967dd34194d0933ae96bc9f898a3ae44cd34cf622001` | In Scene Beats, cue `5cf9415d-5806-5854-85ae-53e068cf6aa3` was changed from `买家下午五点就到，我们必须决定。` to `买家下午五点就到，债主今天也在催，我们必须决定。`, and saved at 10,000 duration units. Scene Beats became ready and Storyboard became stale. |
| Explicit Storyboard-only rebuild (once) | `1ffd5d61-250a-4283-a456-e9a2a6947262`; Storyboard r3 `91b2bb9d34da5c1f5c6d53f198370eb9a7a79753e3925193994210cd9d6690e6` | The UI rebuild dialog selected only Storyboard. The run snapshot records Bible r1, Graph r1, Scene Beats r2, and only Storyboard stale because Scene Beats changed. All 9 Storyboard work units succeeded on their primary attempt. |

The initial two attempted dialogue saves correctly failed their canonical timing
validation: the expanded line's retained 4,160-unit duration, then 6,000 units,
were below the language/delivery minimum. The cause was an author-owned duration
that no longer matched the edited text, not an invalid validator. Declaring a
sufficient 10,000-unit duration fixed the contract at the correct layer; no
validator bypass or correction machinery was added.

For preservation, a canonical API projection of the other 15 dialogue cues
(identity, beat, order, speaker, voice-over, text, language, delivery,
performance notes, and duration) had the same SHA-256 before and after the cue
edit: `e592a68beeccf7090d473d1b49bd6208e3a0b2980109743c2b162f3280c7c34f`.
The frozen rebuild input also shows Bible and Graph stayed at r1 and Scene Beats
at r2; only Storyboard was regenerated.

## Final runtime state and mechanical gates

| Stage | Final state |
| --- | --- |
| Story Bible | r1 ready — `18a824db33cd62d56d3335a7d2c32ae04f3db71bafd518fe3ef88f2902aa5d4a` |
| Story Graph | r1 ready — `d8c6f87caabeb192a85b4e69d9af685358386310f895d1a4f3cc7e5adfdd8860` |
| Scene Beats | r2 ready — `30fec0a9653cb73d85b2967dd34194d0933ae96bc9f898a3ae44cd34cf622001` |
| Storyboard | r3 ready, consuming Bible r1 / Graph r1 / Scene Beats r2 — `91b2bb9d34da5c1f5c6d53f198370eb9a7a79753e3925193994210cd9d6690e6` |

The final Storyboard review reported 490 required `storyboard.v2` gates passed,
0 failed, and no active Approval or approval decision. It contains 12 shots.
Those structural results establish schema consistency only; they do not establish
creative quality, audio execution, playthrough quality, or human acceptance.

## Quality review and material gap

An attended independent, read-only Terra review examined the final current
candidate and did not modify runtime data, settings, UI, or repository files.
It found the following, which prevents creative qualification:

- **P1 — causal choice and prop continuity:** the early sell path joins the
  shared final choice with little persistent state. Its sell ending then begins
  with an already repaired watch and an arriving customer, although that branch
  declined repair and has no on-screen repair bridge. The smallest product fix is
  to retain the early decision state across the join, or add the missing repair
  causal beat before that hand-off.
- **Withdrawn — dialogue/audio-plan mismatch:** this was not a mechanical
  defect. `cueIds` own speech scheduling, and the cited cue totals fit their
  shots (10,720/10,720 and 6,420/18,000 units). Ambient/foley audio plans need
  not duplicate dialogue. The unnamed silent customer is likewise not a
  mechanical contract violation.
- **P2 — repeated middle conflict:** `夕阳下的对峙` and `立场的固化`
  restate the phone-versus-watch disagreement with little new consequence before
  the final choice. The sell signing/hand-off and keep torn-contract/watch
  close-up are stronger endpoints; the middle needs causal advancement.
- **Withdrawn — untracked payoff character:** the silent/offscreen customer is
  not a mechanical contract violation. Whether to author that payoff character
  more explicitly remains a creative-quality question, not a gate failure.

The normal shot edit was successfully saved and visible after reload. The later
permitted **stage-level** Storyboard rebuild intentionally replaced the stage;
r1→r2 changed only the targeted shot and the other 12 shots were byte-identical.
The rebuild's granularity is a product limitation, not unexpected data loss or
a claim of shot-local regeneration.

## Boundary, verification, and disposition

This slice used exactly one proposal, one downstream continuation, one normal
shot save/reload, one canonical Dialogue Cue edit, and one explicit
Storyboard-only rebuild. It generated no media and changed no source, frontend
asset, profile, environment, credential, provider setting, reset, or Approval.
The owned local runtime was stopped after evidence collection.

Documentation-only verification is proportionate here: `git diff --check` was
run after the receipt and tracker update. No executable regression suite was run,
because no product code changed. This receipt is a diagnosis and evidence record,
not a request to broaden scope or repair the uncovered defects.

**Disposition:** mechanical stage gates and the upstream stale/rebuild boundary
are demonstrated, but checkpoint 3B is **not quality-qualified** and checkpoint
3 remains unaccepted. A later separately authorized correction should address the
P1 causal-state/repair bridge first, then re-evaluate repetition and the
product-level choice of rebuild granularity.
