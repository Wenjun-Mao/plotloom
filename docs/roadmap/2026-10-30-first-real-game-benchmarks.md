# First original H5 game: reference review and proposed milestone

## Current status

Updated 2026-10-30. Owner: root. Baseline: clean local `main` at `eae289ee`,
with the bilingual functional closeout accepted. Wenjun selected the two games
below as first-product benchmarks and clarified: **original games using these
as benchmarks**. The public-game review is complete. The first story, release
size and delivery plan are still to be selected; the proposed scope below is
the assistant's recommendation. This is discovery, with no production work or
media generation started. Next action: choose the original premise and outline
its smallest complete player journey, then plan its production and delivery.

## Proposed product acceptance

These rows frame the next plan; they do not claim that the first product exists.

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| A complete original browser game | A clean-session player opens the delivered H5 artifact, reaches an ending, replays a different route and resumes after reopening; desktop and phone checks | Retained media for player development; original assets for the finished story | Proposed milestone |
| A story whose choices matter | Unfamiliar playtesters understand the goal and stakes, identify a consequence of their choice and distinguish the endings without a walkthrough | Story/branch read-through first | Original premise pending |
| A coherent audiovisual experience | Review the actual assembled scenes for character/prop continuity, readable authored words, pacing, transitions, speech and sound; include direct listening | Original production media after story scope is chosen | New product quality acceptance pending |
| Faithful production requests | Authored source compared with complete final requests and reference identities; intended differences explained | Provider-free by default for internal changes | Reuse existing request boundaries |
| Repeatable delivery through Plotloom | Retain the original project, reviewed selections and export; reopen and reproduce the player package through documented supported steps | No extra media for unchanged packaging/reopening | Product-specific path to be planned |

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

## Recommended first-release shape

Start with **one complete original short interactive film**. Use Last Call to
bound the first release and Xuanwu Gate to guide world context, consequence
explanations and later expansion. Proposed planning target: 3–5 minutes for a
first route, two or three major decision points, three distinguishable endings,
a small cast and few locations. Adjust those numbers after outlining so pacing
and causal clarity govern the work. Wenjun has not yet selected these numbers
or a genre; they are not fixed production quotas or budget grants.

Give the player a themed entry, clear subtitles, sound controls, legible untimed
choices, a satisfying ending, local resume and easy replay. Deliver a standalone
H5 experience accessible from a link. Keep exact interface/subtitle wording
author-controlled. Add a codex or chapter map when the chosen story benefits;
they are optional first-release scope.

Use the existing Plotloom functional foundation and retain the separation
between software correctness, request fidelity and creative quality. Known QA
media limitations remain recorded; finished original scenes need their own
product judgment. Let this story's demonstrated needs prioritize the queued
media-quality work. Defer architectural work that does not unblock that outcome.

The first production checkpoint should be one representative opening, decision
and ending assembled in the intended player, assessed for actual comprehension
and presentation before scaling the remaining branches. Use retained footage
for player/persistence regressions. Original story production and any quality
experiment get explicit story-specific scope and stopping criteria in the next
plan, using existing provider/dispatch contracts.

No new framework, hosting/account system, full English authoring interface,
large content library, model trial or broad quality-generation campaign is part
of this reference review. Story selection, target audience, presentation language,
release destination and final creative acceptance remain to be settled as part
of product design. Public release is not initiated by this document.

## Relation to completed work

The [bilingual functional closeout](../verification/2026-10-30-language-functional-closeout.md)
remains accepted with its recorded limits and historical failures. This discovery
does not reopen its tests or change its runtime/recovery identity. Validation of
this documentation consists of source/diff and link consistency checks; no new
software qualification, generation, push or CI is required for this note.
