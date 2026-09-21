# Creator workflow usability — review plan

Status: **Bounded representative story/branch prototype approved; broader U1–U4 redesign remains unapproved.**
Date: 2026-09-18. Parent: [playable MVP tracker](2026-09-17-playable-mvp-milestones.md).
Only the representative U2 reader below is dispatched. Generation remains
paused; this approval does not dispatch the broader redesign.

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

The approved delivery is an isolated, read-only story-and-branch route for one
genuine small story. It must read the canonical graph and accepted F4 binding,
show one opening and two consequences, and keep the English screenplay source
unchanged under Chinese UI. This settles only the prototype's presentation
boundary; it is evidence for U1/U2 choices, not product or creative acceptance.

## Deferred whole-workflow language decision

The user agreed to one language initially, including text boxes and generated
material, not just navigation. Chinese-first is the current recommendation,
**not a settled whole-workflow implementation choice**. The bounded prototype
uses Chinese UI while preserving the retained English script verbatim. Pinned
script/storyboard renderers separately support Chinese/English report chrome;
storyboard prompt language remains independently English by default. No prompt,
source-content, or general localization change is authorized here.

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

## U2 storyboard-reader delivery receipt — 2026-09-19

**Approved boundary.** The user approved a read-only, route-focused story-reader
usability slice after the attended review: the story structure was clear; only the
detached wide-screen connector strokes were minor polish. This receipt records the
bounded presentation approval only. It does not accept creative/media output, F5A
as production input, M2, U3/F7, or a whole-workflow language change.

**Delivered surface.** `?view=story-prototype&project=<id>` now admits reading only
when the current accepted F4 script, current canonical graph, and accepted F5A
storyboard review all share the exact frozen binding. It retains canonical route and
chapter order, excludes sibling-route screenplay and F5A segments, presents chapter
→ segment → cut with source scene context where bound, cut-level estimated durations,
frame/action, camera, size, F4 dialogue, and explicit missing-image honesty. Chinese
reader chrome leaves the English source unchanged. Stored `h3Prompt` is collapsed
under “查看生成说明”; identifiers/hashes/mappings are under “技术详情”. The original
upstream report remains separately labelled in a sandboxed frame.

**Refusal and exclusions.** Missing, stale, reopened, mismatched, or incomplete
F4/F5A/graph bindings clear the reader rather than mixing retained evidence. The
surface has no save, generation, media, or production actions and creates no
SceneBeats/Bible projection. It does not modify projects, approvals, assets, or
provider state.

**Evidence.** Focused model tests cover currentness and route order. Production
FastAPI browser proof creates a disposable deterministic F4/F5A fixture, verifies
GET-only reader behavior, route filtering, collapsed prompt disclosure, stale
refusal, and screenshots at 1440 px and 768 px. Deterministic static assets were
rebuilt. The independent read-only stable-delta review outcome is recorded in the
corresponding verification receipt.

## U2 reader admission correction — 2026-09-19

The preceding storyboard-reader receipt describes the superseded combined
admission boundary and remains retained as historical evidence. The current
reader follows the amendment to ADR 0067: current accepted screenplay plus
canonical graph admits the screenplay independently; storyboard review is a
separate, exact-binding, fail-closed view. Its unavailable state does not clear
the screenplay. The reader selects one focused view at a time and retains route
and shared-opening focus across the switch. See the correction verification
receipt for the independent F4 multi-scene proof, valid storyboard route proof,
stale local refusal, and viewport evidence.

## U2 reader connector polish and attended usability acceptance — 2026-09-20

The user approved the storyboard reader's usability after the attended review:
it looks good except for the detached connector strokes in the wide branch map.
That is presentation feedback only, not creative, generated-media, F5A
production, M2, U3/F7, or language acceptance. The connector correction keeps
the canonical graph as the only route owner and changes no reader admission,
project, review, media, or provider state.

The defect was a layout-ownership problem: each destination card independently
positioned a viewport-relative stroke, so its fragments could detach from cards
and overlap the heading at wide widths. The corrected map owns one connector in
the grid track between the opening and its two explicit choices. Its trunk and
arms align to the two equal choice rows; the narrow single-column layout hides
the decorative connector rather than leaving fragments. The focused production
browser proof retains F4-only multi-scene screenplay admission, exact F5A
storyboard admission, route focus, and GET-only reading, while adding retained
1920 px visual evidence alongside the wide and narrow captures. See the
[connector-polish receipt](../verification/2026-09-20-u2-reader-connector-polish.md).

## U3 first character-reference review — 2026-09-20

**Approved boundary.** The user approved the first bounded U3 slice: a
read-only, image-first character-reference gallery over existing accepted-cast,
character-reference proposal/decision, and managed-asset owners. This approval
supersedes only the preceding *unapproved* first-U3 proposal. It does not
approve a broad U1–U4 redesign, environment/prop galleries, F7, generation,
selection, import/refresh/disposal operations, provider work, creative asset
acceptance, or a whole-workflow language change.

**Root cause and ownership note.** Existing F2B data already contains the
currentness, selected-reference, proposal, delivery, refinement-parent and
managed-asset facts a creator needs, but those facts are scattered across an
authoring panel whose controls obscure comparison. The remedy belongs in a
GET-only presentation route, not a new gallery store, cached projection, or
selection workflow. Accepted cast owns admissible subjects; reference decisions
own the selected identity reference; proposals/deliveries own candidate and
parent lineage; managed assets own image bytes. The route must represent their
states faithfully, including stale, historical, missing and failed delivery
evidence.

**Acceptance.** The gallery is cast-only: it requires no Story Bible, script,
or storyboard. It shows a large best-available image, named subjects,
alternatives, explicit selected/current/historical state, refinement links, and
separate collapsed frozen directions and technical provenance. Chinese chrome
does not translate retained source. It has no mutation callback. A focused
production FastAPI/file-SQLite browser journey proves GET-only viewing,
subject/project ownership isolation, missing/stale states, route continuity,
and wide/narrow presentation; retained technical fixtures remain clearly
non-generated layout proof, not creative evidence.

## U3 acceptance correction — 2026-09-20

The first U3 delivery receipt required a bounded correction before acceptance.
The corrected gallery preserves selected-primary ownership when its metadata or
bytes are unavailable, uses one identity-scoped error-aware presentation for
every gallery image role, invalidates held gallery reads on unmount/project
change, and makes parent lineage recognizable and focusable. These corrections
remain within the already-approved read-only U3 boundary: they create no new
owner, prompt, selection, provider call, generation, or write route. The final
receipt records fresh browser, production walkthrough, visual, and independent
post-fix review evidence; earlier review evidence is pre-fix only.

## U3 character-stage integration — 2026-09-20

**Approved workflow purpose.** A creator visits **角色** to establish a
character’s text and reusable appearance for future shots: review/accept the
cast text, compare retained appearance candidates, explicitly select an
identity reference with reviewer notes and revision protection, or prepare a
manual refinement handoff from a recognizable parent. Viewing is not a write,
does not select a candidate, refresh a delivery, or prepare a handoff.
Preparation is not provider/ImageGen dispatch.

**Exact surface change.** The standalone
`?view=character-reference-review` gallery, its duplicate stage navigation and
the duplicate `CastReferenceStudiesPanel` are retired. Their image-first
candidate/status/parent/instruction/technical presentation is reused inside the
new workspace `stage=characters` entry beside the retained `CastPanel` text
review. Selection/reviewer/notes/CAS and proposal prepare/copy/refresh/cancel
reuse existing F2B APIs and semantics. Art, source, screenplay, storyboard and
Play are excluded.

**Acceptance boundary.** Accepted cast admits actions. Reopened or stale cast
keeps retained evidence visible but supplies actionable refusal rather than new
work. Candidate, selected decision, historical, missing and failed evidence
remain distinct; asset failures and parent lineage preserve the prior U3
ownership guarantees. Fixture evidence does not substitute for the pending
human creator walkthrough acceptance.

## U3 cast synchronization correction — 2026-09-20

The integrated Characters workspace now owns the current cast session shared by
F2A text review and F2B image-reference actions. Accept/reopen/save invalidate
image authority before their requests dispatch, retain evidence in a
non-actionable transition state, and refresh current image directions/decisions
only under the resulting session. This is a currentness correction inside the
approved U3 surface, not new generation, selection semantics, API/schema work,
or broader U1–U4 approval. The technical receipt records guard-sensitive
deferred-operation tests, browser coverage, deterministic static freshness and
the independent-review/re-review trail. Attended creator-usability acceptance
remains pending.

## U3 live-session closeout — 2026-09-20

**Approved step and deliverable.** Close the three confirmed Characters session
defects only: live ownership for initial/refresh gallery reads, live ownership
for image actions, and a fresh same-subject local session after cast
accept/reopen/save. The deliverable is the bounded `stage=characters` correction,
focused unit/browser regressions, regenerated static assets, ADR 0071 amendment,
and updated integration receipt.

**Evidence and exclusions.** Prior captured-value tests did not establish a
live read boundary, and prior same-subject coverage did not prove local busy/draft
reset. The replacement evidence holds an old refresh through reopen/save and
releases its success and rejection only after r2 is current; it separately proves
pending-prepare → reopen → save creates usable empty controls and dispatches the
next action. The browser proof drives accept → reopen → save on the production
fixture. Backend/API/provider/persistence/data work, UI redesign, generation,
creative acceptance, and a restart of the retained port-49072 preview remain
excluded. Human creator-usability acceptance is still pending.

## U3 Characters usability correction — 2026-09-20

**Approved step and deliverable.** Correct the retained `stage=characters`
workspace presentation after the U3 session closeout: one primary stage
navigation; context and inspector status in a closed accessible technical
disclosure; readable accepted cast text with explicit edit and separate manual
new-proposal actions; and unambiguous, separate image-selection and
parent-based-adjustment tasks. The deliverable includes focused browser layout
and interaction assertions, regenerated static assets, the ADR 0071 amendment,
and the integration receipt.

**Evidence and exclusions.** The shell’s duplicated 01–05 context navigation,
always-open diagnostics, hash-first accepted cast, and mixed selection/refinement
form were observed presentation defects. This correction removes no access to
technical context and changes no API, schema, persistence, provider, generation,
selection CAS, reviewer/notes, asset, cast-session, or other stage contract.
It does not approve creative/media output or replace the pending attended creator
walkthrough.

## P1.5 native specialist loop — 2026-09-21

**Approved step and deliverable.** Prove one smallest real end-to-end image
loop: a current frozen image job is sent from Plotloom to one persistent native
Codex image specialist, one real ImageGen result is delivered through the
existing validation/currentness owner, and it appears in the gallery without
manual assignment copying or refresh. [ADR 0074](../adr/0074-native-codex-image-specialist-dispatch.md)
defines this runtime boundary.

**Evidence, exclusions, and stop condition.** The specialist task ID and
dispatch reservation are host-local, not canonical data. `codex queue` receipt
is only transport evidence; it never proves ImageGen or delivery. One in-flight
job and at most one real ImageGen submission are permitted. H3 and Qwen remain
disabled and excluded; no auto-selection, provider registry, queue framework,
gallery redesign, or new media owner is authorized. Stop after one accepted,
unselected, hash-valid gallery candidate with retained package/result evidence,
or report the bounded native-transport blocker without a speculative fallback.

**Trial receipt — incomplete.** The one allowed native ImageGen submission
completed but its result did not reach the gallery. The specialist/package
contract exposed an empty-reference attestation mismatch; the root contract is
corrected, but current immutable-package verification properly rejects the
already-exported package as a template conflict. The result, package, and
cleanup refusal remain preserved in the disposable ignored project. No retry,
selection, creative acceptance, H3, or Qwen fallback is authorized. See the
[truthful receipt](../verification/2026-09-21-native-codex-image-specialist-loop.md).
