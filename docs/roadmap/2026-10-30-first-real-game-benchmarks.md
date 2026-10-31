# First original H5 game: reference review and proposed milestone

## Current status

Updated 2026-10-30. Owner: root. The bilingual functional closeout at `eae289ee`
remains accepted; reference discovery was recorded at `2bc05bfe`. Wenjun chose
**original games using the two references as benchmarks** and refined the first
milestone: assemble a standalone H5 game with designed game UI, without video
or audio quality inspection. The game must run without the Plotloom service.
Editing/regeneration/review followed by one-click asset application belongs to
the next iteration; preserve the necessary bindings in the first iteration.
Capture concrete production friction in the existing Plotloom workflow as work
proceeds. These owner requirements supersede the initial proposed creative-
quality acceptance. Story, release size and detailed implementation plan remain
open. No production implementation or generation has started. Next action:
choose the original premise and define its smallest complete assembly journey.

## First-milestone acceptance

Owner requirements below frame the next plan; none claims a completed product.
Device targets and detailed story scope will be fixed in that plan.

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| Standalone browser game | A self-contained H5 folder/ZIP loads story, UI and media independently; complete its routes with Plotloom unavailable and verify no Plotloom/API/key dependency | Retained media for package development; story assets as production requires | Required; portable package still to be built |
| Complete playable assembly | Start, play, choose, reach distinct authored endings, replay and resume through the delivered game; check correct asset bindings and basic loading/playback | Reuse unchanged assets; no quality rerolls | Required; story pending |
| Designed game presentation | Inspect the actual game shell, title, choice boxes, control states and ending screens for a coherent theme, readable layout and usable interactions | No media-quality experiment needed | Required in the first iteration |
| Video/audio creative quality | No perceptual inspection, listening, artistic grading or quality-based regeneration during this milestone; preserve known limitations honestly | No quality campaign | Explicitly deferred by owner |
| Faithful production requests | Authored source compared with complete final requests and reference identities; intended differences explained | Provider-free by default for internal changes | Reuse existing request boundaries |
| Foundation for later asset updates | Preserve the Plotloom source-to-game asset mapping and separate story/UI from physical asset files; avoid service URLs embedded as game dependencies | No extra media | Design now; full review-and-Apply workflow next iteration |
| Production learning | Record observed workflow friction, consequence and smallest useful change while producing this game | No extra generation just to populate notes | Required throughout production |

## Public references and inspected evidence

The review used ordinary desktop browser play. No account, purchase, asset
download/reuse, generation or publication was involved. Temporary research tabs
were closed; browser-local progress from
the playthroughs was retained. Root owned this cleanup. No spending or provider
resource grant was needed for the review.

### Choices of Xuanwu Gate

Official page: <https://jinmingyu.itch.io/choices-of-xuanwu-gate>.

The author describes a Simplified-Chinese historical interactive drama with
39 video scenes, 34 choices and 14 endings, about ten minutes per run. These are
**advertised totals**, not an independently completed inventory. Offline use is
also advertised; network-disconnected play was not tested.

Root played the prologue and first chapter to an early alternate ending, opened
the character codex and optional historical notes, replayed the consequential
decision through the chapter timeline, and followed the alternative into chapter
two. Reload then offered Continue (`续前缘`), which resumed chapter two.

Observed product features:

- A themed title screen immediately establishes role, conflict and historical
  setting. Short subtitled video scenes lead into in-character choice text.
- The inspected sequence includes single-option continuation as well as
  two-/three-option decisions. Do not equate every click with a distinct branch.
- The character codex showed two of six entries unlocked, with later entries
  tied to story progress. Historical notes are optional during play.
- Challenging the emperor at the end of chapter one produced a textual alternate
  outcome dossier. It explained the consequence, showed a game-reported 50%
  historical-alignment score and summarized relevant prior choices. This review
  does not certify the historical accuracy of those explanations or that score.
- The timeline groups visited scenes by chapter, exposes unexplored locations,
  and explains that returning to a prior point discards later choices in that
  run. Returning to the last major decision worked; choosing restraint then
  continued the story instead of reaching that early ending.

Useful benchmark: an identifiable world, optional context, a clear account of
why an ending occurred, and a navigable path back into the story. Its larger
advertised scale is a later growth reference. Only one early ending and the
alternative continuation were inspected; later chapters and all endings remain
outside this review.

### Elseworld: Last Call

Official page: <https://elseworld.net/en/interactive>.

At review time this URL presents one free interactive-film prologue, **Last Call**.
The English page advertises Mandarin audio, three endings and play without
sign-in. Its immediate mystery premise connects a missing sister, an impossible
telephone call and a departing train.

An attended read-only GPT-6.1 Sol / Medium reviewer completed a route through
three decision beats: question the caller, retain the key/find the locker, then
broadcast a warning. This reached ending III. Return to the last choice replayed
the preceding scene; boarding the train instead reached ending II. The discovered
count rose from one to two of three endings. Reload preserved that count, and
Continue replayed the saved finale. Root separately inspected the landing page,
continued the saved finale and viewed the second ending's presentation.

Observed product features:

- A concise premise and immediate Play action; a consistent rainy visual setting
  and close-ups give the sampled scenes a clear visual identity.
- Large numbered choices include a short reason to choose each action. A later
  decision recalls an earlier warning. Choices explicitly allow time to think.
- Some scene transitions are automatic. Controls include pause, mute, subtitles,
  transcript and theater mode. Opening the transcript paused playback; returning
  resumed it. Theater mode enlarges the film and removes surrounding navigation.
- Endings have distinct titles, outcome text, a discovery counter, last-choice
  replay and restart. Undiscovered endings remain hidden.
- The site explains that progress belongs to this browser/device and does not
  survive cleared site data or sync between devices. Reload persistence worked.

Useful benchmark: a compact, fully presented cycle from premise to decisions,
ending, replay and return visit. Two of three endings were inspected. The opening
video's DOM duration was about 12.074 seconds; this is not total story duration.
No cross-device, mobile or disconnected-network test was performed.

For both games, screenshots and natural playback were inspected. No perceptual
audio listening was performed; audio controls, subtitle text and advertised
language do not establish voice, music or mix quality.

## First iteration: assembly and game presentation

Start with **one complete original short interactive H5 game**. Use Last Call to
bound the first release and Xuanwu Gate to guide world context, consequence
explanations and later expansion. Proposed planning target: 3–5 minutes for a
first route, two or three major decision points, three distinguishable endings,
a small cast and few locations. Adjust those numbers after outlining so pacing
and causal clarity govern the work. Wenjun has not yet selected these numbers
or a genre; they are not fixed production quotas or budget grants.

Give the player a themed entry, subtitles where authored, sound controls,
designed untimed choices, ending screens, local resume and easy replay. Choices
need intentional typography, spacing, colors, framing and hover/focus/pressed
states. The title, player controls and endings should share that treatment.
Polish can remain modest. Keep the design in the game UI, independently editable
from the generated footage; it must not depend on asking a video model to draw
working controls or exact choice text. A codex or chapter map is optional when
the chosen story benefits.

The delivery boundary is a self-contained static game: HTML/CSS/JavaScript,
story data and the actual media files with portable paths. A generic static
host may serve it; the player's machine needs no Plotloom process, database,
provider credentials or generation service. Prefer a file-friendly package
whose index.html can also open directly; verify that launch path and local-save
behavior on the selected browsers before claiming it. A Plotloom preview link
does not satisfy this requirement.

The first checkpoint is an opening, decision and ending assembled in that
standalone game. Check technical integrity, loading, playback, transitions,
choice routing and game UI design. Video/audio realism, voice quality, continuity,
cinematic merit and creative listening reviews are outside this milestone.
Technical failures that prevent playback or progression still require repair.
Do not turn this distinction into a new inspection or approval process. Preserve
provenance and existing authorization contracts, using truthful functional-only
selections where applicable; no creative-quality pass is implied.

Use retained footage for player, persistence and packaging regression checks.
Produce original assets when the selected story needs them, without a quality-
tuning loop. The prior queued media-quality modularization is not a prerequisite
and is not started by this milestone. Let demonstrated assembly blockers drive
necessary Plotloom changes. Scope story generation and the implementation path
in the next plan; no new provider, hosted system or publication is initiated here.

## Next iteration: review and Apply updated assets

Owner direction: return to the Plotloom project, edit and regenerate an asset,
review the candidate, then use one Apply action to replace the corresponding
asset in the game. Updating should produce a new self-contained game package;
the running game remains independent of Plotloom.

Preserve the following small design commitments now, without building the whole
update UI in the first iteration:

- Give game nodes/choices and asset slots explicit identities. Keep story and
  presentation data separate from files; bind a slot to a selected file/version.
- Retain the build-side mapping from each slot to its Plotloom source and
  selected candidate/segment, including content identity and the playback window.
  Package only player-needed data; keep credentials and machine-specific paths
  out of the game.
- Regeneration creates a candidate. A future explicit review/Apply step chooses
  what enters the next export. Merely creating a candidate must not silently
  replace the game asset.
- Asset-only application preserves story links, game styling and node-based
  progress. Changed duration, trim or subtitle timing must be reconciled before
  applying; structural story edits are a separate update case.

This is a focused export/update seam, not a request for general bidirectional
editing of arbitrary external game code or a new asset-management framework.

## Existing seams and production learning

A bounded source inspection at `2bc05bfe` found that
`frontend/src/play/PlayView.tsx` loads project/stages/jobs/bridge through the API;
`frontend/src/branching-video-preview.tsx` plays service-served clips and renders
generic choice buttons. These are useful playback behaviors, but the inspected
surfaces do not establish a portable standalone game exporter.

`VideoCandidateSelectionRow` and `VideoSegmentRow` in
`src/plotloom/persistence/schema/project_media.py` already retain per-shot
selection revisions, source bindings, frame windows and original/derivative
hashes. Reuse those owners for mapping and export validation. Installed shot IDs
in `production_bridge_projection.py` include cut order, so do not assume they
preserve semantic identity across arbitrary structural edits. Asset-only updates
can bind the unchanged source; changed structure needs explicit reconciliation.

Keep production observations here or in this milestone's eventual implementation
plan, using a small table: **step, observed friction, effect on the game, smallest
useful change, disposition**. Record repeated manual work, unclear asset selection,
source-to-game binding problems, preview/export differences and regeneration
friction when actually encountered. Fix demonstrated in-scope blockers; queue
convenience improvements. Do not invent findings from source inspection or create
another tracking/evaluation system.

## Superseded proposal

The initial reference-review proposal included unfamiliar-player comprehension
and audiovisual creative review as first-milestone gates. Wenjun's subsequent
direction replaces those gates with functional assembly and designed game UI.
Perceptual video/audio inspection is deferred. The 3–5 minute/three-ending shape
remains an assistant proposal, not an owner-selected quota. Historical benchmark
observations above are unchanged.

## Relation to completed work

The [bilingual functional closeout](../verification/2026-10-30-language-functional-closeout.md)
remains accepted with its recorded limits and historical failures. This discovery
does not reopen its tests or change its runtime/recovery identity. Validation of
this documentation consists of source/diff and link consistency checks; no new
software qualification, generation, push or CI is required for this note.
