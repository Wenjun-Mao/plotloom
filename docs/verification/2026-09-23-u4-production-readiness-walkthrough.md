# U4 retained-copy production-readiness walkthrough — 2026-09-23

## Boundary and verdict

This is a **read-only diagnosis**, not a production or creative acceptance. I
inspected the isolated U4 copy at `127.0.0.1:8822`, project
`fbb913c8-534b-4439-ba68-211e70ec743d`, through its live API and browser UI.
No project, approval, reference, asset, keyframe, job, provider, selection, or
playback state was changed. The original U4 project was not touched. The
[shot-policy receipt](2026-09-23-advisory-shot-policy-u4.md) retains the setup
and policy decision; [ADR 0079](../adr/0079-f5-production-canonical-bridge.md)
retains the bridge ownership contract.

The accepted bridge proposal is current, installable, and installed: r2,
`e22ef5e5ee815781c3836d04e8b56715fe034aca80c38011e4575f301da6d7b1`,
three scenes and 27 cuts. Canonical Story Bible, Scene Beats, and Storyboard
are each ready at r1. This proves the source-to-canonical data handoff, not
production readiness. The first creator-facing gap is the accepted bridge's
missing actionable handoff into a *specific* canonical shot: it supplies only
a generic next-step sentence. The harder downstream contract block is that
26 exact 6-second F5 cuts cannot be prepared as current H3 jobs, which admit
only 5 or 8 seconds. Silent retiming would violate the bridge-owned duration
contract; this requires a separately approved source or provider decision.

## Exact installed-cut inventory

The bridge proposal's `sectionId`, `episode`, `sceneIndex`, `shotId`, `seconds`,
and `source.{segmentIndex,segmentSceneIndex,cutIndex}` were read from
`GET /api/v2/projects/{id}/production-bridge` and compared with the canonical
shot list and its millisecond durations in `GET /stages` and the workbench.
Here `seg/scene/cut` are the source F5 coordinates within each section; the
middle column is the canonical section/episode/scene coordinate. There are
26 × 6 s and one × 8 s, totaling 164 seconds across the three mutually
exclusive routes (not a single playback path).

| Canonical shot ID | Canonical section/episode/scene | F5 source seg/scene/cut | Exact duration |
| --- | --- | --- | --- |
| opening-s1-c1 | opening/1/1 | 1/1/1 | 6 s |
| opening-s1-c2 | opening/1/1 | 1/1/2 | 6 s |
| opening-s1-c3 | opening/1/1 | 2/1/1 | 6 s |
| opening-s1-c4 | opening/1/1 | 2/1/2 | 6 s |
| opening-s1-c5 | opening/1/1 | 3/1/1 | 6 s |
| opening-s1-c6 | opening/1/1 | 3/1/2 | 6 s |
| opening-s1-c7 | opening/1/1 | 4/1/1 | 6 s |
| opening-s1-c8 | opening/1/1 | 4/1/2 | 6 s |
| opening-s1-c9 | opening/1/1 | 5/1/1 | 6 s |
| beacon-s1-c1 | beacon/2/1 | 1/1/1 | 6 s |
| beacon-s1-c2 | beacon/2/1 | 1/1/2 | 6 s |
| beacon-s1-c3 | beacon/2/1 | 2/1/1 | 6 s |
| beacon-s1-c4 | beacon/2/1 | 2/1/2 | 6 s |
| beacon-s1-c5 | beacon/2/1 | 3/1/1 | 6 s |
| beacon-s1-c6 | beacon/2/1 | 3/1/2 | 6 s |
| beacon-s1-c7 | beacon/2/1 | 4/1/1 | 6 s |
| beacon-s1-c8 | beacon/2/1 | 4/1/2 | 6 s |
| beacon-s1-c9 | beacon/2/1 | 5/1/1 | 6 s |
| dock-s1-c1 | dock/3/1 | 1/1/1 | 6 s |
| dock-s1-c2 | dock/3/1 | 1/1/2 | 6 s |
| dock-s1-c3 | dock/3/1 | 2/1/1 | 6 s |
| dock-s1-c4 | dock/3/1 | 2/1/2 | 6 s |
| dock-s1-c5 | dock/3/1 | 3/1/1 | 6 s |
| dock-s1-c6 | dock/3/1 | 3/1/2 | 6 s |
| dock-s1-c7 | dock/3/1 | 4/1/1 | 6 s |
| dock-s1-c8 | dock/3/1 | 4/1/2 | 8 s |
| dock-s1-c9 | dock/3/1 | 5/1/1 | 6 s |

The shot-policy advisory is three nine-cut scenes against the original
2–4-shot Brief, but is explicitly nonblocking in this copy. It must not be
reinterpreted as a media-duration waiver or an implicit creative approval.

## Actual creator path and ownership

At `stage=source#storyboard-review`, the accepted proposal shows the scene
and cut list and says that storyboard review, reference choice, keyframes and
media preparation remain. It does **not** offer a direct canonical-workbench
action, selected shot, or readiness state. The creator can manually expand
“编辑与工具” and choose “分镜工作台” (`stage=storyboard`); the workbench opens with
`opening-s1-c1` selected and displays its 6000 ms duration and canonical
character/location/prop IDs. The source bridge's F2/F3 IDs resolve to the
canonical C01–C03, S01–S03 and P01–P02 records; they are semantic references,
not chosen visual references or media.

The canonical storyboard review head is ready r1; all 904 information gates
pass and three advisory warnings are not applicable. It has **no active
Approval or decisions**. The UI's “批准当前分镜” is disabled until a reviewer
label is supplied; no approval was attempted. The same workbench owns explicit
character identity-reference selection, imported stills, image-job preparation,
reviewed keyframe selection, video-job preparation, candidate selection, and
route playback. In this copy, character-reference decisions, art-reference
decisions, managed assets, visual intents, image jobs, still previews, media
tasks, video jobs and selected keyframes are all empty. The media controls
state the relevant prerequisites and are disabled. The branch preview names
missing shots and does not synthesize or skip them. Thus neither route has
selected playable media.

The preview reports `video-backend.enabled=false` with
`h3_video_not_configured`; no provider call can be made there. Independently,
the checked-in H3 catalog has qualified durations `{5: 124 frames, 8: 192
frames}`. The video UI takes a catalog-qualified duration, while the persisted
bridge-owned shot guard requires the requested duration to equal the exact F5
cut seconds before any video job is created. Once ordinary approval/keyframe
prerequisites and backend configuration exist, all 26 six-second shots would
still fail that contract; only `dock-s1-c8` matches the current 8-second
catalog. This is a genuine source-to-provider compatibility conflict, not a
reason to pad, trim, or silently change the accepted shot data.

## One bounded next implementation slice

**Candidate, not authorization:** add a read-only, shot-specific handoff from
the accepted bridge into the existing canonical storyboard/media workbench,
with an explicit preparation-status summary for the selected bridge-owned
shot. The summary should show its exact F5 source coordinate and duration,
active storyboard Approval, selected identity/art references and keyframe,
media/backend availability, and whether its duration belongs to the currently
qualified H3 set. Link to the existing owner and its first blocking action;
do not create a parallel approval or media workflow. A browser regression
should cover the accepted `opening-s1-c1` navigation and distinguish missing
approval/reference/keyframe/backend from the exact-duration conflict. This
slice stops at honest, navigable readiness; it does not approve creative work,
select assets, retime F5, dispatch providers, or prove playback.

Before any video-production assignment, the director must separately choose
between a newly qualified exact 6-second provider contract and a newly
reviewed F5 source revision whose cut durations fit the qualified catalog.
Neither is implied by bridge confirmation or by this diagnosis. Native
audiovisual quality, voice consistency, selected-media continuity and actual
viewer playback remain unaccepted F6/F7 work even after a duration decision.
