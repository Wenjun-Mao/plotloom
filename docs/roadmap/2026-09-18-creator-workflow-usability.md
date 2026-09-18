# Creator workflow usability — review plan

Status: **Draft delivery plan; walkthrough direction agreed.**
Date: 2026-09-18. Parent: [playable MVP tracker](2026-09-17-playable-mvp-milestones.md).
Implementation and generation remain paused. This plan does not dispatch work.

## Outcome and evidence

A creator can understand the story, follow its branches, inspect each creative
stage, and compare references without developer explanation or reading JSON.
This improves the authoring experience; it does not complete M2 or connect F5
review revisions to production media.

During the attended walkthrough, the user:
- Identified duplicated navigation and competing old/new workflows.
- Could understand the opening and two consequences, but could not see their
  relationship clearly in the flat report or crowded cards.
- Found mixed-language controls, explanatory prose, defaults and text boxes
  confusing; hashes and internal checkpoint labels were distracting.
- Found raw JSON in narrow cards unusable for normal review.
- Found the genuine Shuohao screenplay report clear and readable, with no
  requested content edits; requested a clearer E01 → E02/E03 relationship.
- Found the storyboard report useful, but needed “#cut” and estimated dialogue
  duration explained. Those estimates do not establish actual audio alignment.
- Preferred image-first comparison, with generation instructions available on
  demand rather than always displayed.

The first inspected project's F1–F4 reports were technical placeholders.
Do not use them to evaluate genuine upstream presentation or claim end-to-end
creative authorship. The subsequently reviewed genuine F4 report was original
candidate r1, not the later edited accepted revision.
See [F4 evidence](../verification/2026-09-18-f4-novel-script-receipt.md) and
[F5 evidence](../verification/2026-09-18-f5a-fresh-specialist-production-review-receipt.md).
Positive report feedback is not generated-media approval.

## Agreed design boundaries

- One primary navigation: source/story → characters → art → screenplay →
  storyboard → production → play. Diagnostics are secondary.
- Each stage gets a readable working area, its inputs, current result/status
  and next action. No repeated numbered navigation or parallel dense editors.
- Distinguish stages from candidate/accepted review states. Explain dependencies
  and stale results in creator language; iteration need not be a rigid waterfall.
- Reuse Shuohao report presentation and current accepted data owners. Preserve
  sandboxing. An original candidate report must never masquerade as the current
  edited revision; label versions and expose readable current content.
- Derive clickable branch maps and route-focused reading from Plotloom's existing
  canonical graph and stable section bindings. Do not introduce another graph
  authority. Inspect existing Plotloom/V1 presentation for reuse, but preserve
  the prohibition on production dependencies on Narrative-Forge runtime/data.
- Image/video candidates show large previews, names, current/alternative state
  and refinement relationships. “查看生成说明” reveals actual frozen instructions;
  separate “技术详情” contains hashes, IDs and provenance.
- Replace development disclaimers with short task-relevant guidance. Keep
  consequential warnings: stale work, irreversible deletion, pending publication,
  missing prerequisites and actual approval state.
- Say “台词—镜头对应表” and “预计朗读时长” where applicable; distinguish estimates
  from measured audio and native-H3 generation from a future TTS workflow.

## Prioritized checkpoints

| Priority | Bounded outcome | Acceptance / simplification |
| --- | --- | --- |
| U0 — settle presentation contract | Short screen map plus language/content policy, based on existing owners and genuine artifacts. No general redesign or implementation. | One navigation and explicit dependency map; identify reused components and exact duplicate UI to retire. Resolve language decision below. |
| U1 — coherent stage workspace | One task-focused stage surface; readable width; secondary diagnostics; consistent creator-facing copy and defaults. | User can locate stage, accepted result and next action unaided. No two numbered stage lists, compressed nested cards or misleading old-owner asset counts. Preserve supported Play and review/lifecycle behavior. |
| U2 — readable story and branch review | Reuse screenplay/storyboard presentation; add canonical graph context and section/route focus. Raw JSON remains optional. | User can follow opening → either ending, inspect action/dialogue and distinguish original report from current edited content. No mutation of accepted content or duplicate editable authority. |
| U3 — image-first candidate review | Character/environment/prop galleries, reusing current assets and reference owners; align existing video candidates where practical. | Compare images and identify current/alternative/parent; instructions and technical details are available but collapsed. Stale/failed/missing assets and generation-not-yet-performed remain obvious. |
| U4 — repeat the creator walkthrough | One genuine small story through available review surfaces with the user. | Capture remaining friction; user can explain the choice, review/edit locations and next production boundary without developer coaching. Technical fixture proofs do not substitute for this outcome. |

Use proportional frontend/production-browser checks, fresh static assets, and an
independent stable-delta review per implementation slice. Cover navigation,
project switches, async ownership, report isolation, revision display and retained
review actions. Do not rerun every backend suite for a text-only adjustment.
Include a realistic narrow viewport; compare layout and usability, not only test counts.

## Next proposed delivery — representative story/branch prototype

The user has approved this usability direction and a representative story/branch
prototype as the next proposed delivery. When separately dispatched, it should use
one genuine small story to make the opening → decision → two-consequence
relationship readable across the stage workspace, screenplay and storyboard views.
It must reuse the canonical graph and accepted/current content owners; it must not
create a second graph, mutate accepted content, connect F5 to production media, or
start provider/generation work.

Implementation is paused for this documentation assignment. U0 settles the
prototype's language and content policy from the pinned skills, renderers and real
artifacts; Chinese-first remains a recommendation, not a decision. The prototype
is evidence for U1/U2 presentation choices, not product or creative acceptance.

## Language decision to settle in U0

The user agreed to one language initially, including text boxes and generated
material, not just navigation. Chinese-first is the current recommendation,
**not a settled implementation choice**. Check the pinned five-stage skills,
renderers and existing authoring fields before confirming feasibility.

The proposal must cover labels, help/errors, defaults, authored/generated story
direction, reports and future specialist instructions. Preserve supplied source
language and existing accepted artifacts; do not silently translate them. For
fresh pilot material, choose one explicit content language consistently. Technical
keys and model-facing English, when genuinely necessary, remain behind optional
details. Defer a language-switch framework. Changing generation language or
prompt ownership needs a separately explicit contract, not a cosmetic text patch.

## Separate product and research tracks

**Production integration:** F5 review-only storyboards still do not create
production shots/media. U1–U4 must not conceal that missing connection. A later
bounded F7 design selects reuse/replacement of current media consumers without
reconstructing obsolete Bible/SceneBeats merely to satisfy old shapes.

**H3 optimization:** retain the user's failed dialogue review and exhausted
two-submit budget. Before another experiment, inspect official H3 guidance and
pinned Shuohao prompt alignment. Extra speech, subtitles and voice consistency
remain separate from UI work. No speculative TTS/lip-sync system.

## Authority and stop conditions

This draft records the review, not implementation approval. Keep current runtime
and reports available for the user's walkthrough; do not generate, select,
rewrite valued data, migrate old projects or delete code as part of planning.
Once approved for delivery, use Relay serial ownership and default Terra/high.
Each assignment names a small outcome and concrete removed/reused surfaces.
Escalate changes to creative authority, destructive actions, new providers,
production mapping or audio strategy; routine UI choices stay within the plan.
