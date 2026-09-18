# Reviewer A — creative workflow and audiovisual continuity

> **Archive status (2026-09-18):** Historical/supporting record retained for context and evidence; it is not an active delivery plan or a completion claim. See [the roadmap entrypoint](../../../README.md).


Status: ready as a self-contained planning prompt; not dispatched. Copy the
whole document as the prompt. The roadmap is optional supporting detail, not a
substitute for the context below. Work independently of Reviewer B.

## Purpose

Help a small project choose a practical path from a story synopsis to a cinematic,
playable branching story. Your advice will revise a development roadmap, not
authorize code changes or certify quality. The costly error is building a large
technical workflow that produces inconsistent, awkward scenes or requires the
creator to become a prompt technician.

## Project and evidence boundary

Plotloom is a private local/Tailscale web workbench, primarily Chinese creative
content with English development discussion. Supplied project summaries report
four editable canonical stages: Story Bible, Story Graph (DAG with choices and
joins), Scene Beats and Storyboard. Stable DialogueCue records own spoken lines;
shots reference them. AudioPlan distinguishes ambience, effects, diegetic sound
and score. Versioned gates and explicit storyboard Approval exist.

A prior real local-LLM canary produced an editable, refresh-persistent storyboard.
Formal broader text qualification is still open. Automated tests do not establish
cinematic quality. Image/video generation and playback are not delivered yet.
These are supplied summaries, not source or creative output you have inspected.
No private story, generated sample, asset, model response or API key is supplied.

Repository discovery: https://github.com/Wenjun-Mao/plotloom
Source baseline: [`9afbefd2f82a620d79b82cd6607571057f23a6c4`](https://github.com/Wenjun-Mao/plotloom/tree/9afbefd2f82a620d79b82cd6607571057f23a6c4).
Review publication branch: `codex/m1b-alpha`, not `main`. The subsequent
documentation-only [roadmap](../../superseded/2026-09-10-story-to-playable-alpha.md) and
[proposed ADR](../../../../adr/0026-story-to-playable-product-direction.md) accompany
this prompt on GitHub. Source inspection is not required for your role; do not
pretend to have inspected inaccessible material or substitute another revision.

## Agreed direction

- Mostly start with a synopsis and no assets; support future imported character
  images, photographs and concept art, preserving originals.
- Initial look: cinematic realism. Creator mainly selects/refines proposals;
  detailed editing stays available.
- For early development, images generated in the coding conversation are imported
  as real assets. This is not a claim that Plotloom's provider integration works.
- Pilot: one protagonist, one location, three keyframes (close-up, wide, action),
  then one short audiovisual clip with a line and environmental sound.
- Deliver in-app sequential preview next, then a small playable branching story.
- At a choice, finish the node's clips, stop audio, hold the last frame, display
  choices and wait. No countdown; follow the chosen canonical edge.
- Native audio should be tried in the initial video pilot; separate TTS and
  sound mixing are later alternatives, not prerequisites.

## Proposed workflow to challenge

Offer two or three comparable visual directions, select one, build only essential
character/location references, test them in representative shots, then expand.
Record unprovided visual details as explicit proposals; story-changing additions
need canonical review. Keep candidates separate from selected references.

Allow exploratory reference design before full storyboard Approval under a
separate versioned exploration contract; production shots still require the
approved board and selected references. This amendment is proposed, not current
runtime behavior. Suggested review stops: direction, keyframe consistency, first
audiovisual performance. Avoid an approval ritual on every variation.

Sequential preview initially has simple cuts, basic transport and shot navigation,
not a professional timeline editor. Authored and measured clip durations remain
distinct. Missing media can be labelled in draft preview but not a complete story.
Proposed first branch is one decision/two outcomes; joins also need testing.

For native sound, we propose dialogue/ambience/SFX first, avoiding independent
music per clip where controllable. Voice sameness across shots is not guaranteed.

## Questions and useful output

Give an answer-first critique, then concrete revisions:

1. Where is the smallest workflow likely to fail creatively? Prioritize identity,
   performance, screen direction, action continuity, dialogue, voice and sound cuts.
2. Is the reference-first pilot the right size? Suggest a better small experiment
   if it reveals more with fewer assets or generations.
3. Which missing visual details may be safely proposed, and which require an
   explicit narrative decision? Give examples and selection UX recommendations.
4. What should the creator judge at each review stop? Supply a concise rubric
   separating fatal defects from refinements; avoid pretending taste is fully
   deterministic or measurable by one automated score.
5. What must hold across a branching join for shared media to remain believable?
   Explain one concrete counterexample and the least expensive remedy.
6. What should be deferred, removed or simplified? Address whether native audio
   is enough for the first scene without designing a full sound-production suite.

Separate practical experience/inference from verified contemporary model/API
facts. For the latter, consult primary provider documentation, cite the exact
endpoint and date accessed, and distinguish advertised capability from tested
performance. The candidate `alibaba/wan-3.0/image-to-video` is not a locked choice;
do not assume all providers expose its reference/audio modes identically.

You may challenge recommendations and surface tradeoffs in agreed choices, but
label any proposal that would change the user's direction. Do not conduct a broad
provider ranking, implement code, contact project services, generate paid media,
or claim acceptance. End with the three changes most likely to improve the first
usable result and the cheapest experiment for each material uncertainty.
