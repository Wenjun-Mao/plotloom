# F6 dialogue prompt — offline corrective fixture proof

Date: 2026-09-18. This is technical/test-only pre-submit evidence, not
audiovisual qualification, human creative approval, selection, gateway upload,
provider call, reservation, submit, poll, or authorization for a new live
dispatch.

## Root cause and ownership

The retained first live attempt at `19c477a` remains unchanged. Its
[`submission-summary.json`](../../.local/relay/e7f90144-3860-491b-9926-87f055df4e58/submission-summary.json)
froze generic shot values (`交代选择`, `角色握紧信件。`, `稳定推进`),
`dialogueCues: []`, and `audioPlan.events: []`. The required line and audio
directions were never authored, so no gateway override, TTS, retry, or
post-process belongs in the correction.

`VideoJobService._prompt` projects only frozen `resolvedContext.dialogueCues`
and `shot.audioPlan.events` ([source](../../src/plotloom/video_jobs.py)). The
normal preparation owner freezes those with reviewed keyframe and identity
lineage ([source](../../src/plotloom/persistence/project/media_video.py)); the
adapter validates and carries its frozen request ([source](../../src/plotloom/video_backends/minimax_h3/adapter.py)).

## Offline result

The ignored reusable script
`.local/relay/d23c878c-9e28-456e-b7df-91082ada8352/f6_offline_prompt_proof.py`
created a new disposable fixture `6f92168d-bc0a-4996-860f-47f266215291` using
the normal canonical, technical-gate, managed-keyframe, identity, and
video-preparation owners. Its approvals explicitly say technical/test-only,
not human or creative approval. It preserved the lawful F2B C01/Lin Che source
hash `1fb4700c73834b81c2ea3f64d6754cc0b24ba1bfcb472d8993161d2d7a2f2e0d`.
The local managed-asset persistence did not cross the HTTP import route or a
provider/gateway upload. The failed fixture, output, accounting, and old roots
were not changed.

The frozen canonical fixture has one visible C01 / Lin Che dialogue cue,
`我在这里。`, and one `ambience` event: `quiet room tone; no narration; no
music`, 0–8000 ms. Its normal unsubmitted preparation produced:

| Field | Value |
| --- | --- |
| Job | `vj_ab02f778d76344ebae02ca1c8026a209` — prepared only |
| Snapshot / request hash | `67d845307a30dcd78411503c49f7f9cfac696f5d6761c5e6941a2f9bc72515d9` / `c91b6583870452b9799d58a7b5e08f19535cf75759ba395f83eca728ac26d0f9` |
| Compiled payload hash | `47f3fe30237b5f38448acf40687ab3142dc9e8a51f498f6ce4e6269845a9334e` |
| Profile / aspect | `minimax_h3_fp8_turbo4_portrait_576x1024_v1` / `cover_center_crop` |
| Timing | 8 seconds, 192 frames, 24 fps |

The actual payload contains exactly one `Dialogue` entry: `speaker=C01` saying
`我在这里。`, and the stated ambient-audio entry. The line also appears once in
the action instruction as visual reinforcement; it is not a second dialogue
cue. The same assertion recompiles the preserved generic snapshot
(`9331cd…5e145` / `820ec…2777b`) and fails on exactly `line`, `speaker`,
`roomTone`, `noNarration`, and `noMusic`. `offline-proof.json` records source,
snapshot, request, and compiled-payload hashes plus both outcomes.

## Independent review and status

An independent Terra/high read-only review passed the source-to-payload
correspondence: current source hashes matched the artifact; the actual request
has the stated profile/aspect/timing; and the old generic snapshot has empty
dialogue/audio collections. It confirmed zero H3/gateway operations, uploads,
reservations, submissions, and provider polls. The script locally polls only
its deterministic fixture pipeline; its H3 transport fails closed if an
operation is attempted. The run-3 command log completed, and its in-process
fixture dispatcher closed with the client.

**Not ready for live dispatch.** The proof closes the authoring/compiler gap
only. It does not establish audible words, speaker identity, lip sync, room
tone quality, or absence of music/narration in generated media. Any live work
still needs separate authority and must inspect this frozen compiler payload
before submission.
