# F5-to-production/F7 seam preflight

> **Superseded as the next implementation proposal.** This assessment remains
> useful inventory evidence, but it does not define the next slice. The
> approved successor is the source-backed
> [F5-to-production canonical bridge design](2026-09-22-f5-to-production-canonical-bridge-design.md):
> a reviewable proposal followed by explicit atomic installation, not a
> standalone read-only admissibility API.

Date: 2026-09-22. Baseline: retained `main` at `a869e7c`. This is a
source-backed, read-only assessment of the next seam after the accepted U4
walkthrough. It performs no canonical installation, accepted-data edit,
provider/media call, service operation, or schema/backend implementation.

## Current U4 inventory

The retained lighthouse project
`fbb913c8-534b-4439-ba68-211e70ec743d` has current accepted F1–F5 review
inputs: graph r1, cast r1, art r1, script r2, and storyboard review r2. The
accepted F5 review is bound to the exact accepted script r2 hash and the ordered
`opening → E01`, `beacon → E02`, `dock → E03` mapping. That makes it valid
review evidence for the reader, not a production installation.

The public read-only preflight found no current F7 inputs in this project:

| Existing production/F7 input | U4 state | Consequence |
| --- | --- | --- |
| Canonical `story_bible` | missing | No canonical character/location/prop owner for production shots. |
| Canonical `scene_beats` | missing | No canonical beat IDs or scenes to which shots can bind. |
| Canonical `storyboard` | missing | No `Shot`/`ShotBeatLink`, review approval, or production-shot revision. |
| Managed assets / reviewed keyframes / selected character references | 0 / 0 / 0 | No selected visual inputs can enter image or video admission. |
| Video jobs | 0 | No media candidate, selection, or playback evidence exists. |

## Ownership and reusable contracts

The current owners are intentionally distinct:

| Concern | Current owner | Reuse boundary |
| --- | --- | --- |
| Story facts, Chinese dialogue, route consequences | Accepted F4 script and its F1/graph binding | Author-owned source facts stay authoritative; a later production mapping must not rewrite them. |
| Upstream cuts, English `frame`, timing, camera, and H3 text | Accepted F5 `storyboard-source-review` | Model/specialist review output is raw review direction only. `StoryboardReviewBinding` freezes its F4 identity and timing policy; `ordered_episode_mapping` exposes section order without creating shots. |
| Canonical production units | `StoryBible`, `SceneBeatPlan`, `Storyboard` (`Shot`, `ShotBeatLink`) | Existing F7/media code consumes these canonical entities, not F5 review JSON. |
| Character identity selection | Current accepted cast mapping plus explicit character-reference decision | F2 consumer mappings can support cast-owned reference review, but an identity-aware production image/video job requires a current canonical StoryBible character for every visible shot member. |
| Environment/prop study | Accepted art plus F3B art-reference decision | F3B is exploratory, current-art-subject evidence; it is not a selected production shot/keyframe. |
| Keyframes, media jobs, selection, playback | Existing approval, reviewed-keyframe, image/video-job, and PlayView owners | They remain unchanged and require a current approved canonical storyboard. |

Current code makes the missing seam concrete. `src/plotloom/storyboard_review_contracts.py`
persists F5 as `dict` review data and deliberately exposes only its ordered
section mapping. `src/plotloom/domain.py` defines the separate canonical
production `Shot` and `ShotBeatLink` model. `media_image_preparation.py` and
`media_video.py` require one current canonical shot, active storyboard
approval, and selected reviewed keyframe; video also freezes identity lineage.
`frontend/src/play/PlayView.tsx` refuses to play without current graph, scene
beats, and storyboard payloads. No current code maps F5 review data into those
owners, and none should silently do so.

## Material decisions before an implementation slice

1. **Canonical-authoring boundary.** Choose the owner that proposes and the
   owner that explicitly accepts the required StoryBible, SceneBeatPlan, and
   Storyboard before any F5 review field can be associated with F7 shots. F5
   review must remain an input/binding, never the installer.
2. **Mapping granularity and duration policy.** Decide whether a production
   shot represents an upstream cut, a segment, or an independently authored
   shot. Current H3 admission is qualified only for explicit 5- or 8-second
   requests; no implicit trim, pad, split, stitch, or conversion of F5’s
   2–8-second cuts or 15-second segments is allowed.
3. **Prompt ownership.** Decide the precise mapping of F5 `frame`/camera data
   into canonical `Shot` intent and the existing prompt compiler. Upstream H3
   text cannot become a direct dispatch payload, and Chinese script dialogue
   remains script-owned.
4. **Reference and approval gate.** Decide which accepted cast/art subjects
   must receive explicit current production references, who selects them, and
   when canonical storyboard approval opens keyframe/image/video work. F3B
   studies and F2 text acceptance do not imply these selections.
5. **Route/playback representation.** Decide how one shared opening and two
   endings map to canonical scenes/shots and selected media while preserving
   the graph’s route semantics. PlayView is an existing consumer, not evidence
   that a mapping already exists.

These are material product/ownership decisions, not routine implementation
details. They require director agreement before code changes.

## Smallest next implementation proposal

After those decisions, implement one **read-only F5-to-F7 admissibility
preflight** before any install or media work. It would accept explicit IDs for a
current F5 review and a chosen current canonical production candidate, then
return a typed comparison of exact bindings, section/episode order, proposed
cut-to-shot mapping, missing approved references, and duration incompatibilities.
It would not create or mutate StoryBible, SceneBeats, Storyboard, approvals,
assets, selections, jobs, or prompts.

Focused tests for that slice:

- rejects a stale/mismatched F5 script or graph binding;
- rejects duplicate, missing, or reordered cut-to-shot proposals;
- reports absent canonical stages, approval, references, and keyframes without
  synthesizing fallback data;
- proves the preflight is read-only across project stages, review state, visual
  selection, and media-job inventories; and
- preserves upstream timing as facts while reporting unsupported production
  duration mappings instead of transforming them.

Exclusions: no F5 installation, V2 projection, production-editor redesign,
provider configuration, media/image/video dispatch, reference selection,
playback change, generated prompts, compatibility layer, or historical-replay
support. A later accepted preflight would still be evidence only; canonical
authoring, reference selection, and F7 media work would remain separate slices.
