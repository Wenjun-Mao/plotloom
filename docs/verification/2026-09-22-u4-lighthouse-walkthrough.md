# U4 retained lighthouse walkthrough

## Scope and identity

- Project: `暴风灯塔` (`fbb913c8-534b-4439-ba68-211e70ec743d`)
- Isolated persisted root:
  `.local/relay/u4-lighthouse-walkthrough/`
- Agent-authored Chinese development source:
  `暴风灯塔：一条供电线`
  (`4fd3df018e95dde36573e71f317ab19bf64b3aea63a58595d15619dbe13bdab9`)
- Authority recorded by the project is agent-authored source and
  agent-reviewed technical acceptance. It is **not** human creative approval.

The accepted graph has one shared opening and two explicit routes:

1. `点亮灯塔，引导海燕进港` → a safe reef route for the fishing boat;
   the near-shore evacuation loses light and the medicine box remains at the
   warehouse.
2. `点亮码头，护送近岸撤离` → a safe route for evacuees and the ambulance;
   the boat loses its beacon and waits beyond the storm until dawn.

## Accepted current-contract chain

| Stage | Revision | Content hash |
| --- | ---: | --- |
| F1 outline | 1 | `c30b6304db4de192407f001c85d151207f9e43e624ce45d8f105479c5668cc6c` |
| F1 section map | 1 | `12d68596eb3c68190dc2dbceea383255b13fb3c9300c5963c0b1fd480dc6146a` |
| graph | 1 | `049ee4ed12d507553ff545065b49c6d8865882c3f3bb4bef6eceed794e440071` |
| F2 cast | 1 | `b3d2c70428f724851f52fbd34d2597552919c5f5471d69f402bc6962c40fe61b` |
| F3 art references | 1 | `0298cd9b6b6fe7ef0ca79d20986d5b56765b0fe2b1970ef43e8cc39d31d55fae` |
| F4 script | 2 | `f983ec6e22936fbdf8625db4f0e45fa5176221e93bff05def436cc54d86e9b1e` |
| F5 storyboard review | 2 | `bddc4717ee3cfa3858bee3b116d2e3a0fe7a18bae381f6ac87d4b0af10097934` |

F5 delivery is retained at
`.local/relay/u4-lighthouse-walkthrough/outputs/20260922T165155656597Z__fbb913c8-534b-4439-ba68-211e70ec743d/outputs/creative-handoff/jobs/ch_56f07c3cb22641fba27267943921c977/delivery/`.
It contains a validated, review-only upstream storyboard and report; it does
not contain generated images, video, media prompts, or installed product shots.

## Specialist execution provenance

The Chinese source and each candidate were agent-authored development content.
The following are nevertheless actual executions of the pinned local
`plotloom-shuohao-specialist.v1` package-request, validator, renderer, and
completion-receipt flow—not mock deliveries or claims of human creative work.
Each listed `delivery/completion.json` records code revision
`e625fc4d4d5dd5d871895ccb3d6850f6fbf84882`, specialist-skill hash
`cfe747470c05ea2de54a1c67ae9855343bd190a35a97caf7e005a45318c6faa8`,
and upstream revision `4322897e6d2bdaf66365534fd40194360c75a85f`. The
upstream skill hash is stage-specific and is recorded below.
The receipts intentionally report `model` and `reasoningEffort` as `null`:
there is no external-model telemetry to claim.
Every relative delivery path in the table is rooted at
`.local/relay/u4-lighthouse-walkthrough/outputs/20260922T165155656597Z__fbb913c8-534b-4439-ba68-211e70ec743d/outputs/creative-handoff/jobs/`.

| Deliverable | Specialist job / retained delivery | Upstream skill hash |
| --- | --- | --- |
| F1 outline and section map | `ch_5359cd306cd84354af805ec10f03c648/delivery/` | `e611c46f54513ae200eff525fc83ef16e7b0531a84ab6a456923d7c534988dde` |
| F2 cast | `ch_c97e6e10ce0741c78b9165891ce49101/delivery/` | `4ea2fbbdfa31cde78da6f038c27e6ec4758efe4bcf322a5099b72dae3d0e4da0` |
| F3 art references | `ch_5099cb49e6164cabbb8863caa611180a/delivery/` | `2e3ec7fa9223f85395b661822ef009822f3865b413e4fd649642488f2b78b222` |
| F4 accepted script r2 (R3 delivery) | `ch_bfbebaace45c4c9b926a859dbebf0921/delivery/` | `5e653561304e51593a6bd0c36d134fe7076b6352883752912085d312e1e12b7c` |
| F5 accepted storyboard review r2 | `ch_56f07c3cb22641fba27267943921c977/delivery/` | `5e7a52d78cbb1fc74826313e7c290cdcfa70e80d110c4b1250f1b365bcbf66d5` |

## Reopen and inspect

Start the isolated instance from the repository root. It does not reuse or
restart the existing services on ports 8795 or 8796.

```sh
mkdir -p .local/relay/u4-lighthouse-walkthrough/outputs \
  .local/relay/u4-lighthouse-walkthrough/application \
  .local/relay/u4-lighthouse-walkthrough/logs
PORT=8804 \
PLOTLOOM_OUTPUTS_DIR="$PWD/.local/relay/u4-lighthouse-walkthrough/outputs" \
PLOTLOOM_APPLICATION_DATA_DIR="$PWD/.local/relay/u4-lighthouse-walkthrough/application" \
PLOTLOOM_ENABLE_H3_GATEWAY=false \
uv run plotloom
```

Discover the retained project through
`http://127.0.0.1:8804/api/v2/projects?status=all`, then open:

```text
http://127.0.0.1:8804/v2/?view=story-prototype&project=fbb913c8-534b-4439-ba68-211e70ec743d
```

When finished, first identify the listener with
`lsof -nP -iTCP:8804 -sTCP:LISTEN` and confirm it is the isolated U4 process;
then stop only that verified PID with `kill <pid>`. Do not stop the unrelated
8795/8796 listeners.

## Verification and known correction

- The pinned `novel-storyboard validate` passed: 3 episodes, 15 segments,
  27 cuts, 164 seconds against the 180-second target, with complete beat,
  dialogue, timing, H3, and upstream-reference checks.
- The public F5 review admission accepted the exact F4 script binding and
  reports no stale reasons.
- The isolated 8804 process was stopped, restarted with the command above, and
  the project plus accepted F5 review r2 were rediscovered through the public
  API without restoring an ad-hoc backup.
- An independent read-only re-review of the corrected r2 chain found no
  blockers: episode 2 retains only the beacon outcome and episode 3 retains
  only the dock outcome under the current accepted binding.
- The production-shaped reader was inspected at 1440px and 1920px in both
  screenplay and storyboard modes, including both route choices. Screenshots
  are intentionally untracked in `output/playwright/`.
- The browser console only reported the expected sandbox refusal to execute
  script inside the optional raw-report iframe; the reader and its bound
  screenplay/storyboard content remained available.

The first F4 delivery passed the upstream script validator but was rejected by
the product contract because it lacked Plotloom `sectionBindings`. It was
cancelled and preserved as rejected evidence. F4 R2 added the required binding,
but an independent review then identified that its episode 3 content still
described the beacon outcome while the frozen map bound it to the dock outcome.
F4 R3 (accepted script r2) makes the beacon and dock endings distinct; F5 R2
is the fresh accepted review bound to that script. No compatibility layer or
product code change was added.

## Reader content boundary

The pinned upstream `novel-storyboard` schema defines `cuts[].frame` as an
English keyframe/image prompt. The accepted F5 file therefore supplies that
field in English; the accepted F4 script separately retains the Chinese action
and dialogue. There is no author-owned Chinese shot-description field in this
review contract for the reader to have dropped. The reader now labels the
retained field as `上游画面提示（原样）`; it neither translates nor expands the
frozen schema. A future product requirement for author-owned Chinese shot
descriptions would need an explicit new schema and approval contract.

The remaining review is human creative acceptance of the authored story; this
receipt deliberately does not claim it.
