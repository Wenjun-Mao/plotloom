# Project draft ownership and navigation verification

Disposable A and B retained distinct node prose and incomplete JSON through
project switching, history, node/mode navigation and explicit close/reopen.
Final UI cleanup restored both entire draft payloads to their baselines. No
content was confirmed, applied or generated. This qualifies C52 and the exercised
E19 cases, not the entire native lifecycle.

## Candidate and identified data

The owned 8871 UI proxy and matched 8872 API used a 1700×900 browser.
Checked JS SHA256:
`b9e6654517186f3c08fe50e7ab6485534992558bf5e9e1497c3ead33f4214870`.
Existing A is `965671f3-491c-4c30-ba26-03fe20463eba`.
B is `1c55b316-77f1-407b-9c3c-b934ca931631`, titled “QA A-B-A 归属恢复 2026-10-07”.
B was created through Directory → New Blank → named Brief → Save/continue.
The named owner projects and protected settings were not targets.

A began at C50 cleanup r54; B began with its eight-node seed and no saved draft.
Comparisons use the complete payload: topology, prose, choice metadata, merge
contracts, selection and field buffers, not only one field.

## Distinct pending work

| Project | Selected node | Prose | Incomplete buffers |
|---|---|---|---|
| A | QA 保留输入 | A项目独有正文，不属于B。 | Facts `{"projectA":`; entities `[{"entityId":"projectA"` |
| B | QA B 开场 | B项目独有正文，不属于A。 | Facts `{"projectB":`; entities `[{"entityId":"projectB"` |

A buffers belong to `edge-e4ccf061-1c72-5100-b088-d238e534dad2`;
B buffers belong to `edge-098658ab-ff53-5ca8-a6ce-c83afa6fd949`.
Effective fact objects and entity arrays stayed `{}` and `[]`.
Incomplete input was retained, not silently accepted as valid effects.

## Executed actions

| UI action | Exact observed result |
|---|---|
| Save distinct drafts | A r57/B r5 ACKs matched independent complete readbacks |
| Directory A → B → A | Both complete saved payloads and visible project-specific prose/buffers stayed exact |
| Browser Back → B, Forward → A | Correct prose and unchanged full saved payloads |
| Another A node and return | Other node had its own empty prose; A pending work returned intact |
| Story → Production → Story | Same selected node; author payload retained; production access remained guarded |
| Creator → Pro → Creator | Pro showed the same A prose; no copied or cross-saved draft |
| Brief → Source → Creator | Correct A title and unchanged saved A/B payloads |
| A Save/close | Close receipt lifecycle r6; graph read correctly refused `project_closed` |
| Explicit A Reopen | Open receipt lifecycle r7; complete r57 payload/prose returned unchanged |
| Type new A prose then immediately switch to B without explicit Save | Owning navigation drained A r58 ACK; independent read had “A切换前最后一次输入。” with A buffers; B stayed exactly r5 |
| Clean B through fields/Save | ACK r8 and full readback equal B's original seed |
| Clean A through fields/Save | ACK r60 and full independent readback equal A's r54 baseline |

Canonical stayed 0. Cleanup left no field buffers and retained both QA projects
and original contracts. Production navigation inspected guidance and returned;
it did not install production or dispatch media. The unsaved-before-switch case
is distinct from ordinary post-ACK navigation.

## Evidence and helper limitations

Ignored local artifact:
`output/playwright/full-lifecycle-2026-10-07/c52-project-ownership-evidence.json`.
SHA256: `d1aebcbe0f66d7a07ae6edd7c233329dd36255049de0d5061b6598c9f33c3e2b`.
It retains complete payloads, seven readback states, six receipts and thirteen
events. References deduplicate identical payloads without omitting fields.

B's first helper compared content ACK r4 against flush r5 and failed its revision
assertion. Raw r4/r5 responses and independent r5 readback were reconciled:
r4/r5 payloads equal, and the latest ACK matches the complete readback.
No save replay occurred. A combined close helper read while closed and received
the correct refusal; the successful close ACK and explicit reopen were reconciled
without repeating close. One cleanup invocation syntax error preceded dispatch.
The corrected invocation completed once; its exact r60 ACK was recovered from
the browser request log and compared to fresh full readback, not replayed.

Root directly inspected these viewport pixels for project/field ownership.
They do not show every inspector field simultaneously or prove full layout acceptance.

| Pixel | SHA256 |
|---|---|
| 64-project-b-partial-owner.png | `3b9d9959d1edec6458a7d3f0a500be54dba2997989ed5a2e2a5cd7a6a53820d2` |
| 65-project-a-partial-owner.png | `02b2008d39448d701bd6ddc1cef99ed4f95f12f22a0527d0c15b806969dfef71` |
| 66-project-a-after-b-a.png | `645c79cac665ca300112de05df2b20196aeb03540731fa862398e1411295a657` |

## Acceptance boundary

This adds C52/E19 UI and exact readback evidence, not post-install revision,
model inference, native media delivery, all-route playback or quality acceptance.
The [media repair gates](2026-10-07-media-selection-recovery.md) qualify the unchanged
software candidate. The [run profile](../roadmap/2026-10-07-full-creator-e2e-repeat.md)
retains outstanding required journeys. Full lifecycle acceptance remains PARTIAL.
