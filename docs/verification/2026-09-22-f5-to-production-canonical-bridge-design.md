# F5-to-production canonical bridge design

Date: 2026-09-22. Status: implementation-ready design only; see proposed
[ADR 0079](../adr/0079-f5-production-canonical-bridge.md). Baseline: retained
`main` at `55c9a7f`. This replaces the proposed standalone admissibility
preflight with the smallest real authoring seam: immutable accepted F1–F5
inputs produce a reviewable canonical production proposal, and an author may
explicitly accept one atomic installation. It changes no code, schema, accepted
data, provider setting, media job, or playback behavior.

## Decision

Create one **F5 production-bridge proposal** owner. Trusted deterministic code
creates it from current accepted F1–F5 inputs; it does not call a model, create
a second authoring pipeline, submit a provider request, or install canonical
data while preparing. The proposal freezes source hashes and an inspectable
mapping into the existing canonical `StoryBible`, `SceneBeatPlan`, and
`Storyboard` shapes. Its only write with production consequences is a separate,
author-confirmed, compare-and-swap acceptance that installs all three stages in
one transaction.

The bridge is a new persistence owner because F5's
`StoryboardReviewPersistence` deliberately owns raw review evidence, while the
canonical-stage owner owns installed product data. Reuse the accepted
source-map graph admission pattern in
`persistence/project/source_outline.py` and the canonical transaction helpers
in `persistence/project/canonical.py`; do not overload the F5 review head,
generic handoff exchange, or storyboard approval rows. Those would either blur
review with canon, invent a second specialist process, or imply approval.

The proposal/acceptance contract is a durable ownership decision under ADR
0057: author/source facts stay F1–F5-owned until the author explicitly accepts
their canonical projection; Plotloom then owns the installed canonical revisions
and ordinary production workflow.

The first slice also corrects one underlying canonical currentness contract:
downstream invalidation must follow each installed head's recorded input
revisions and upstream readiness, not stage position alone. A source-map graph
admitted through the existing source-map path records no StoryBible input; a
new StoryBible therefore must not stale that independent F1 graph. A normally
authored graph that records a StoryBible input still becomes stale, and a
SceneBeatPlan/Storyboard whose direct or transitive input is stale still becomes
stale. This permits the bridge's existing F1 graph revision to remain current
during the three-stage atomic install without re-admitting or rewriting F4/F5
review evidence.

## User-visible flow

1. From a current accepted F5 review, the author chooses **Prepare production
   proposal** (`准备投产提案`). Its primary Chinese view lists readable source
   scenes/cuts, their canonical counterparts, every policy conflict, and the
   H3 duration status of every cut-shot. A collapsed **技术详情** panel carries
   F1–F5 hashes, source coordinates, and validator evidence; hashes are not
   the primary review surface.
2. The author inspects that proposal, including the shared opening once and
   each ending on its own graph node. Nothing is approved, selected, generated,
   or dispatched here. If an authored F4 scene occurrence contains more or
   fewer F5 cuts than the current Brief allows per canonical scene, the primary
   view says `不能安装：源场次有 N 个镜头，当前项目规则为 min–max 个` and the
   **接受并安装** control is disabled.
3. **Accept and install** (`接受并安装`) requires the displayed proposal revision
   and content hash and is enabled only when no blocking conflict remains. A
   successful result is an installed but unapproved canonical
   StoryBible/SceneBeatPlan/Storyboard. Existing canonical editing and
   storyboard approval remain the next explicit author actions.
4. Existing reference, keyframe, image, video, and playback flows follow their
   present gates. F2/F3 evidence may appear as provenance, but it never selects
   a character image, an art image, a keyframe, or a storyboard approval.

## Frozen inputs and exact mapping

The bridge persists a `BridgeInputBinding` containing the accepted F1 graph,
F2 cast, F3 art, F4 script, and F5 review revisions/content hashes, the current
project-brief hash used for required StoryBible context, plus F5's complete
inherited binding and ordered section-to-episode mapping. Preparation and
acceptance reject an input that is no longer current. The proposal also stores
the raw-coordinate and raw-content hash for every mapped source member; that
is required because upstream `sceneIndex` and beat numbers are positions, not
stable IDs.

| Frozen source | Proposed canonical target | Exact rule and ownership |
| --- | --- | --- |
| F1 graph node ID / F4 section ID | `DramaticScene.story_node_id` | Preserve the graph node ID unchanged. Each distinct F4 source-scene occurrence yields one canonical scene; a node may therefore contain several scenes only when F4 contains several distinct occurrences. The F1 start/opening node is represented once, never copied into each route. Ending scenes retain their distinct ending node IDs. This matches `branchingPreviewManifest`, which groups canonical scenes by `storyNodeId` before sequencing shots. |
| F4 episode, `sceneIndex`, and `sceneId` | one `DramaticScene` | Resolve `sceneIndex` against that exact frozen episode's script-scene occurrence. Preserve exactly one canonical scene for that occurrence, with a bridge-owned ID derived from `(sectionId, episode, sceneIndex)`. Retain `sceneId` as the location/art reference, not as the scene identity. Repeated values such as `S01` therefore do not collapse distinct occurrences, and the bridge never invents a dramatic split merely to fit a planning preference. |
| F4 resolved `flow` position | `Beat` and `DialogueCue` | Create a bridge-owned beat ID from `(canonicalSceneId, flowIndex)` and preserve the frozen flow-entry hash, action/dialogue shape, and source coordinates in proposal provenance. For a `line`, create the one canonical dialogue cue with the mapped speaker and exact text; for an `action`, use the exact action as the beat's visible event. The adapter may not infer a beat from free text. It must reject a cut range that does not resolve to a contiguous, unique set of frozen flow positions. |
| F5 `(episode, segment.id, cut ordinal)` plus review hash and raw cut hash | `Shot` and `ShotBeatLink` | This tuple is the source-cut identity; upstream cuts have no independent stable ID. Create a bridge-owned canonical shot ID from that tuple and attach it to its one resolved source scene. Map one source cut to one canonical shot because `Shot` is the smallest existing unit targeted by reviewed keyframes, video preparation, and playback sequencing. Expand the cut's declared inclusive beat range into `PRIMARY` links for every resolved beat: the V2 gate requires exactly one primary shot per beat. Preserve the original range and source-scene identity in bridge provenance. This is not a claim that a cut is one provider job. |
| F5 cut `seconds`, `size`, `camera`, `frame`, characters, and props | Canonical shot fields | Copy `seconds` exactly to `durationUnits` (integer milliseconds) and record the original number. Preparation rejects a source duration that cannot be represented as an integral number of milliseconds; it never rounds, trims, pads, splits, or stitches. Map `extreme-wide → extreme_wide`, `wide → wide`, `medium → medium`, `close → close_up`, and `extreme-close → extreme_close_up`; reject any other accepted source value. Copy camera to `cameraMovement` and `frame` verbatim to `composition`. Populate action from the resolved F4 flow and schedule its mapped dialogue cues, never by parsing H3. Carry visible characters, location, and props only after their source IDs resolve to the proposed StoryBible. Leave `visualIntent`, `motionIntent`, audio plan, state transitions, and continuity requirements empty/default only where the canonical schema permits it; do not invent a creative transformation. |
| F5 segment `h3Prompt` | Bridge evidence only | Preserve it with source hash for review and traceability. It is neither a canonical shot field nor a dispatch payload. Existing `MediaPromptCompiler` remains the only path that derives provider prompts from approved canonical data. A segment remains review grouping/evidence metadata; it never becomes a Shot or an H3 request. |
| F2 cast `consumerMappings` | Canonical StoryBible character IDs | Require the proposal to prove every visible F5/F4 cast ID resolves through its accepted one-to-one consumer mapping and that the mapped consumer ID satisfies V2 `StableId`. The mapped consumer ID is the canonical `CharacterV2.id`; the proposal copies no reference decision. Existing character-reference owners can therefore later resolve the same canonical IDs. |
| F3 art scene/prop IDs | Canonical StoryBible location/prop IDs | Preserve an accepted art ID unchanged only if it passes the current stable-ID contract and is type-compatible with the exact F4 scene/prop use. Otherwise preparation fails and requires an explicit one-to-one bridge mapping; it never guesses from display names. F3B studies are attached only as evidence, never as selected media. |

The direct field mapping above is deliberately constrained by current consumers:
`media_image_preparation.py` snapshots canonical shot fields into image work,
and `MediaPromptCompiler` derives image/video prompts from canonical data.
Putting F5's `frame` into `composition` preserves reviewed visual composition
without treating it as an upstream provider prompt. F5 H3 text remains outside
that compiler.

### Mechanical V2 completion rules

The bridge does not ask a model to fill required V2 fields. It projects the
frozen project brief's `synopsis` verbatim into both required StoryBible
`logline` and `premise`, its `genre` and `visualStyle` into their like-named
fields, and uses schema-allowed empty values for brief facts that do not exist
yet (tone, audience, narrative promise, themes, rules, and questions). F2/F3
supply the corresponding accepted entities; a missing optional source detail
also remains empty rather than being invented.
For each resolved script occurrence, the F1 node title/summary provides the
scene title/objective, the exact sum of its cuts provides its duration budget,
and empty entity-state/audioplan collections remain empty only where V2 accepts
them. An action flow entry supplies its own beat description/visible event; a
dialogue flow entry supplies its own dialogue-cue text and a mechanical
description such as `source dialogue`. A source `delivery` becomes the cue's
performance note; the bridge uses the project language and the existing
`natural` timing profile only to meet the already-versioned V2 timing contract.
If its resulting cue estimate does not fit its exact source cut, preparation
fails rather than altering timing or rephrasing dialogue. This is a projection
rule, not new creative authorship.

## Candidate and acceptance contract

The bridge head follows the established candidate lifecycle: `missing →
prepared → ready → accepted`, with `stale` and `cancelled` terminal outcomes
where appropriate. A ready proposal contains:

- immutable `BridgeInputBinding`, candidate revision, and proposal content hash;
- structurally valid V2 StoryBible, SceneBeatPlan, and Storyboard payloads,
  plus their stage-gate result;
- a source-to-canonical mapping table and per-row raw-content hashes;
- source timing and an explicit H3 profile compatibility result per canonical
  shot, plus blocking Brief-policy conflicts; and
- non-authoritative links to accepted F2/F3 evidence, without an asset,
  selection, approval, prompt, or job ID.

Preparation may retain a structurally valid but stage-gate-ineligible proposal
solely so the author can see and resolve its conflicts; it never enters an
install path. Acceptance must verify, in the same lifecycle write transaction:

1. the proposal is current and the author supplied its exact revision/hash;
2. every frozen F1–F5 input, project brief, and graph/section binding is still current;
3. the three target canonical stage heads are empty in the first slice; and
4. no Brief shot-count conflict remains; and
5. all proposed payloads and mapping invariants validate again.

It then installs StoryBible, SceneBeatPlan, and Storyboard in dependency order
using the existing canonical installation path. The retained source-map graph
stays at its current revision under the input-provenance invalidation rule above;
the transaction verifies its exact F1 hash and section identity before loading
it as the SceneBeatPlan prerequisite. It records a new
`F5ProductionBridgeAdmission` that binds the installed entity revisions/hashes
and the retained graph revision/hash to the proposal, and commits once. It does
**not** create a
`StoryboardApproval`, visual-intent record, reference decision, managed asset,
keyframe, image job, video job, provider request, or playback selection.

An edit to a frozen source input or the project brief makes the proposal stale. A later edit to an installed
canonical stage leaves its accepted bridge evidence intact but makes that
admission non-current; ordinary canonical review/approval owns the new author
revision. No stale proposal may be accepted or used to renew an approval.

## Timing and provider boundary

F5's accepted timing is source fact: each cut remains its exact 2–8-second
duration and each segment remains its review-only at-most-15-second grouping.
The current H3 adapter qualifies only explicit 5- or 8-second production
contracts. Therefore the proposal may install a 2, 3, 4, 6, or 7-second shot,
but displays it as **not dispatchable by the selected H3 profile**. It must not
alter that shot to make it dispatchable.

The bridge implementation must add a narrow check at the existing video
preparation boundary before it persists a prepared job or reserves anything:
for an active bridge admission, require requested provider duration to equal the
canonical source-cut duration and require that exact duration in the selected
profile's qualified durations. The error returns the source-cut identity,
source duration, and supported durations. This is a dispatch-time report, not
a conversion feature. It applies no trim/pad/split/stitch workaround and keeps
segment H3 text out of the request. The first bridge does not qualify a new
provider duration.

## Minimal implementation slice

One implementation slice may include only:

- typed bridge contracts, persistence rows/head, and currentness checks;
- input-provenance-based canonical invalidation, including a regression proving
  a source-map graph remains ready across a Bible install while ordinary and
  transitive dependent heads still stale;
- deterministic F1–F5-to-V2 proposal construction with the mapping and
  validation rules above, preserving one F4 scene occurrence as one canonical
  dramatic scene;
- a usable Chinese proposal page with readable scene/cut/conflict-first review,
  collapsed technical provenance, and explicit disabled/enabled
  `接受并安装` controls;
- an author-confirmed atomic install into empty canonical targets;
- bridge-admission provenance/currentness; and
- the exact-duration guard in existing video preparation, with no provider
  submission changes.

Focused tests must cover shared-opening-once/endings-distinct playback mapping;
`sceneIndex` versus `sceneId`; preservation of one source scene occurrence;
a nine-cut source occurrence shown as a blocking 2–4 Brief-policy conflict with
installation disabled; no duplicate or uncovered source flow; source-cut
identity across reordering; F2 consumer mapping and F3 ID incompatibility;
atomic rollback and compare-and-swap acceptance; no approval/media side effect;
and rejection of unsupported 2–8-second H3 dispatch before job persistence.

Excluded: generated creative content, a new specialist handoff, an F5 shot
store, automatic reference import/selection, approval, prompt passthrough,
provider capability expansion, image/video submission, new player logic,
historical replay, and migration of an existing canonical project.

## Follow-ups and migration boundary

After the bridge is stable, separately scope: canonical editor/review ergonomics;
explicit F2/F3-to-production reference decisions; F7 image/keyframe/video work
for approved shots; H3 capability qualification for any additional exact
duration; and product acceptance in PlayView. None follows implicitly from
bridge acceptance.

The first slice accepts only projects whose StoryBible, SceneBeatPlan, and
Storyboard heads are empty. That preserves existing user-valued canonical work
and makes the cutover unambiguous. It adds no automatic migration, replay, or
compatibility layer, and retires no existing manual canonical-authoring path.
After a fresh-project bridge is product-accepted, a separate decision may make
it the default route for new F1–F5 projects; existing canonical projects remain
where they are unless an explicit, project-scoped migration is authorized.

## Product-affecting policy conflict

`ProjectBrief.shotsPerSceneMin/Max` is an editable authoring/planning policy,
not an intrinsic storage maximum or a source-scene boundary: the Brief page
exposes it as a plan target, while canonical validation enforces it when a
canonical storyboard is installed. Therefore the bridge preserves one F4 scene
occurrence and reports a count outside the frozen Brief range as a blocking
conflict. It does not segment the scene or silently widen the Brief.

The only material decision for an over-budget project is whether the author
wants to explicitly revise the Brief's shot-count policy for this source. The
recommended resolution is: revise that policy through the existing Brief owner,
allow its normal currentness effects, then regenerate/reaccept the affected
upstream stages before preparing a new bridge proposal. For the retained U4
project, nine F5 cuts in each sole source scene conflict with its 2–4 plan and
cannot be installed until such an explicit author decision exists. This is not
a routine bridge implementation question. Separately, a later product decision
may qualify additional exact provider durations after evidence exists; the
bridge does not presume that outcome.

## Source basis

- ADR 0057 and ADR 0065 define F5 as source-bound review evidence rather than
  canonical production data.
- `src/plotloom/storyboard_review_contracts.py` and
  `persistence/project/storyboard_review.py` freeze the F4/F5 mapping and
  timing but do not project shots.
- `src/plotloom/canonical_schema.py` defines the V2 scene, beat, and shot
  contracts; `source_outline.py` and `canonical.py` provide the existing
  admission/transaction pattern.
- `frontend/src/branching-video-preview.tsx` groups canonical scenes by graph
  node then sequences their shots, establishing the shared-opening and distinct
  ending routing constraint.
- `media_image_preparation.py`, `media_video.py`,
  `media_character_references.py`, and `MediaPromptCompiler` establish the
  canonical approval/reference/prompt consumers.
- `video_backends/minimax_h3/adapter.py` defines the qualified 5/8-second H3
  profile contract.
