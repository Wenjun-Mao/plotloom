# Creator workflow usability — review plan

Status: **U2 is complete; the bounded U3 Characters appearance workspace is
accepted; the separate U3 environment/prop F3B review and explicit
reference-choice usability slices are delivered; and the bounded U1a
creator-navigation shell, source-owner presentation correction, and compact
secondary-tool presentation are accepted at `94cf165`. U4 is limited to
one genuine coherent-story walkthrough and received connected read-only
usability acceptance at `a869e7c`; broader redesign remains unapproved.**
Date: 2026-09-18; current summary updated 2026-09-22. Parent: [playable MVP tracker](2026-09-17-playable-mvp-milestones.md).

**Current summary.** U3 acceptance is limited to the Characters workspace:
cancel-edit safety, truthful imported appearances, large-image inspection, and
any explicit two-to-four image comparison on 1440px and 1920px desktop review.
The separate F3B environment/prop slice reuses accepted art and existing
reference-proposal lifecycle. Its explicit current-subject reference choice was
reported by the creator to work well and is recorded at `729cb94`; that is
bounded presentation usability acceptance only, not creative/media output,
production consumption, or portable-simulator persistence evidence.
The previous authorized ImageGen proof is complete; no further provider call is
authorized by this record. Video, F2/F7 creative or media acceptance, and
imported-image refinement remain separate.

**U1a implementation record — 2026-09-22.** The dispatched navigation-only
slice adds one creator-facing sidebar sequence, project-scoped source fragments
(`source`, `art`, `script`, and `storyboard-review`), a folded **编辑与工具**
home for all retained legacy editors, and a compact reader return to the script
owner. It deliberately keeps source-bound **分镜评审** separate from the legacy
**镜头与媒体工作台**. The hash is part of the route contract: direct fresh load,
same-page clicks, Back/Forward, and project switches retain the requested
owner; source panels defer scrolling until their own project and the required
preceding embedded owners have settled. No API,
readiness aggregation, owner state, lifecycle, provider, generation, media, or
production behavior changed. `frontend/e2e/u1a-workflow-navigation-demo.html`
is a permanent, explicitly local no-API walkthrough fixture, not evidence about
any user project or persistence. Director review remains the product-acceptance
gate; this record does not authorize retiring an editor or route.

**U1a presentation correction — 2026-09-22.** The initial fragment contract
only scrolled the aggregate source page, so 美术参考, 剧本, and 分镜评审 retained
the unrelated 来源与小说大纲 heading and source form. The corrected contract keeps
the existing source, Art, Script, and F5A owners mounted for local-draft
continuity, but exposes exactly one full-width, native-`hidden` subview at a
time. Each accepted fragment now supplies its own matching `h1`; hidden owner
content is neither visible nor focusable/announced. Owner reads stay
independent: a failed aggregate source read cannot suppress an Art, Script, or
F5A loading, missing, stale, archived, or error state. The obsolete
owner-settlement/anchor-scroll sequencing was removed. This does not add a
route, API, store, generation action, or acceptance claim; direct fragment,
Back/Forward, invalid-fragment fallback, project reset, and same-stage draft
preservation remain required regression behavior.

**Creator and tool-heading convention — 2026-09-22.** The approved cleanup
gives each visible creator workspace and secondary tool one concise sidebar
label and the same single `h1`. The top bar holds project status and actions
rather than another stage number/title, and the sidebar omits repeated
ordinals and subtitles. Creator navigation keeps unused sidebar space after
its compact heading-and-link content; the folded tools and footer remain
reachable. Short task guidance stays below the heading; the source rights
caveat stays beside its declaration field. This is presentation-only and
preserves every owner, route, session, draft, error, lifecycle, and approval
contract.

**U1 navigation acceptance and U4 preflight — 2026-09-22.** Director accepted
the bounded navigation and heading/sidebar presentation at `94cf165`. It
remains a presentation acceptance only: source-bound F5A review is distinct
from the legacy shot/media workbench, and neither is creative/media approval
or a production consumer. The original U4 preflight found no retained current
same-story project in the local no-API U1a fixture or retained U3 technical
fixtures; neither was repurposed. That prerequisite was subsequently met by
the authorized isolated lighthouse project. The director inspected its
connected reader and accepted the U4 usability scope at `a869e7c`; see the
[U4 receipt](../verification/2026-09-22-u4-lighthouse-walkthrough.md). This
does not install production data or make a creative/media/production claim;
the next F5-to-production/F7 work remains the separate
[assessment](../verification/2026-09-22-f5-to-production-preflight.md).

**Historical 2026-09-18 dispatch status.** At this plan's creation, only the
representative U2 reader was dispatched and generation was paused. That
historical constraint did not authorize the later bounded U3 work recorded
below, and it does not erase its stated exclusions.

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
The original narrow-viewport expectation is historical planning guidance; the
current U3 desktop policy uses 1440px and 1920px visual acceptance, while
retaining inexpensive responsive behavior without a narrow-viewport gate.

## Completed U0/U1 navigation and workflow assessment — 2026-09-22

**Historical assessment boundary.** This source-backed documentation slice
defined the later accepted U1a navigation change; it was never approval to
redesign or remove a workflow. It records the screens and owners that informed
that bounded implementation. It did not create a new stage, API, projection,
persistence state, production storyboard, or media owner. The observed F3B
reference-choice usability acceptance at `729cb94` is included only as a
bounded creator-facing presentation result.

### Current screen and ownership map

| Creator task | Current entry and owner | Current result/status and next action | Safe navigation and missing behavior |
| --- | --- | --- | --- |
| Source, outline, and admitted route map | `?project=<id>&stage=source` → `SourceOutlinePage` and `SectionMapPanel` | Source, outline candidate, accepted outline, map, and graph admission each retain their own revision/currentness. The panel offers save, manual specialist handoff, refresh/accept/cancel, map save, and explicit graph install only when its owner permits it. | This is the current source-bound entry. Without a saved project, the workspace truthfully asks the creator to save it first; no empty source route is invented. |
| Characters and identity references | `?project=<id>&stage=characters` → `CharactersPage`, `CastPanel`, and `CharacterReferenceReviewPanel` | Current cast state owns the next action; accepted cast enables browse/compare/select or a prepared manual proposal, while stale/reopened cast suspends image actions. | Link directly only with a project ID. Its existing missing state says that an accepted cast is required and does not invent subjects or example imagery. |
| Accepted art and environment/prop references | The `ArtPanel` and shared `ArtReferenceGallery` are embedded in the source page; there is no separate Art route. | Accepted `art.json` owns the scene/prop subject list. F3B proposal state owns prepare/copy/refresh/cancel; the append-only decision owner marks one current candidate as “当前参考图” or retains stale history. `729cb94` moves counters to folded technical detail. | Keep `stage=source` as the safe entry until a future implementation adds stable in-page targets. Missing accepted art or candidates remains a truthful local state, not a redirect to Characters or the legacy Bible. |
| Accepted screenplay | `ScriptPanel` is embedded in the source page; the read-only route reader is `?view=story-prototype&project=<id>`. | F4 owns candidate, accepted/reopened, section editing, and report state. The reader consumes only a current accepted script bound to the current graph and exposes no save/generation action. | The reader refuses a missing, stale, or mismatched script with its owner-specific explanation. It must not silently show a historical script or fall through to another route. |
| Source-bound storyboard review | `StoryboardReviewPanel` is embedded in the source page; matching evidence is optionally readable in `view=story-prototype`. | F5A owns its raw review candidate, acceptance, binding, and report. It is review evidence only: it neither creates Plotloom shots nor makes a production or media decision. | The reader shows F5A only when the accepted review matches the exact current F4/graph binding; otherwise it leaves the current screenplay readable and labels the storyboard unavailable. |
| Existing shot/media workbench | `?project=<id>&stage=storyboard` → `StoryboardPage` | This is the existing editable Plotloom storyboard/shot/media surface with its own scene-beat and media task inputs. It is not an F5A projection or F5A acceptance destination. | Do not route an F5A review CTA here, synthesize shots from F5A, or treat its presence as production readiness. Its own prerequisites and stale state remain authoritative. |
| Play | `?view=play&project=<id>` → `PlayView` | Existing canonical graph, scene beats, storyboard, and selected jobs drive the view. It already reports when those payloads are missing. | Preserve the current top-bar link and return link. A future workflow nav may show it, but must not claim playability before `PlayView` can load its required current payloads. |
| Legacy authoring and diagnostics | Workspace sidebar `brief`, `bible`, `graph`, `beats`, `trace`, and `quarantine` | These are still real existing authoring, inspection, repair, and diagnostic surfaces. They are not the source-bound review sequence and must not be relabelled as F1–F5 acceptance. | Keep direct routes working while they remain owners. Trace and quarantine belong under secondary technical navigation, not the creator’s primary progress path. |

### Smallest coherent integration brief for a later U1 slice

1. Present one creator-facing sequence: **来源与大纲 → 角色 → 美术参考 →
   剧本 → 分镜评审 → 播放**. Reuse `stage=source` for its embedded F1/F3/F4/F5
   owners and `stage=characters` for F2; do not add a new Art, Script, or F5
   route merely to make this sequence look linear.
2. Give every primary destination a project-scoped link and a short owner-local
   status/next-action summary. The navigation shell must not issue parallel
   lifecycle reads or synthesize a global “current” state: `SourceOutlinePage`,
   `CharactersPage`, `ArtPanel`, `ScriptPanel`, `StoryboardReviewPanel`,
   `StoryPrototypePage`, and `PlayView` remain the authorities for their own
   readiness and errors.
3. Add stable in-page targets to the embedded source panels only when U1 is
   dispatched. Until then, `stage=source` is the only truthful direct entry to
   source, art, script, and F5A review. A missing prerequisite must keep the
   creator at the named owner with its existing explanation—never redirect to a
   later stage or substitute retained history.
4. Keep **分镜评审** distinct from the existing **镜头与媒体工作台**. The former
   links to/readies `StoryboardReviewPanel` and the binding-gated reader; the
   latter remains `stage=storyboard`. No navigation change may add an F5A →
   production conversion, SceneBeats/Bible projection, or H3 dispatch.
5. Make the route-focused reader a secondary read-only destination after the
   script. It may expose its current refusal state, but it must not masquerade
   as a canonical editor or promise that its optional F5A tab is production
   material. Keep Play separate and equally honest about unavailable payloads.

### Exact duplicate/obsolete presentation to retire only in that U1 slice

- Retire `CreatorStageNavigation` in `StoryPrototypePage` as a second workflow
  map. It currently points “分镜” to the legacy `stage=storyboard` workbench
  even though the page reads F5A review evidence. Replace it with a compact
  back-to-workflow affordance once the primary navigation can carry the same
  project context.
- Remove the sidebar’s primary-progress treatment of **项目简报、故事圣经、剧情
  DAG、场景节拍、分镜工作台** after their supported owner links have been placed
  deliberately in the creator flow. Do not delete the routes, editors, or their
  tests in that navigation-only slice; move diagnostics (`运行轨迹` and `隔离修复`)
  to secondary technical navigation instead.
- Remove the source page’s inherited numeric/internal pipeline labels from
  creator-facing headings when the one primary sequence supplies orientation:
  “F1A · Project-owned review”, “01 · Accepted source”, “02 · Candidate only”,
  “03 · Accepted outline”, “04 · Reviewed section map”, “06 · F3A”, “07 · F4”,
  and “08 · F5A”. Preserve the descriptive headings, current-state labels, and
  folded technical detail; the change is presentation only.

**U1a stop condition.** The authorized shell is now implemented: it reuses
current routes and readiness checks and adds no data, acceptance, production,
provider, or Play payload behavior. Focused unit/browser checks cover direct
links, missing/stale owner-local rendering, reader/F5A versus legacy-workbench
separation, and project containment; the static bundle and 1440px/1920px local
fixture are reviewed before director inspection. Stop after this shell. A
decision to retire legacy authoring routes or define production ownership
remains material and requires separate approval.

## Historical U2 delivery proposal — representative story/branch prototype

The user approved this usability direction and a representative story/branch
prototype as the then-next proposed delivery. When separately dispatched, it should use
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
loop: a current frozen accepted-cast character-reference proposal is sent from
Characters to one persistent native Codex image specialist, one real ImageGen
result is delivered through the existing validation/currentness owner, and it
appears in the gallery without manual assignment copying or refresh.
[ADR 0074](../adr/0074-native-codex-image-specialist-dispatch.md) defines this
runtime boundary.

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

**Corrected accepted-cast path — deterministic evidence only.** The actual
Characters proposal route now reuses the native transport: create freezes the
accepted-cast package, **发送给 specialist** performs the one explicit queue
attempt, and the Characters gallery observes validated delivery without
auto-selection. Browser evidence uses only a deterministic completion fixture;
it does not spend another ImageGen submission. A new bounded live trial remains
blocked pending explicit authorization after the final preflight.

**Dispatch-safety correction.** Product cancellation and package conflict do
not prove the native task stopped, and the supported queue CLI offers no
receipt identity proving that a nonzero exit did not accept a message. Those
states therefore retain the one-worker host lease; only terminal delivery
handling releases it. Codex `thread/read` `idle` does not identify a queued
message and may occur before an accepted queue request begins, so it cannot
release this lease. The deterministic Characters browser coverage verifies
partial-to-final admission, final-invalid persistence, and refreshed
`package_conflict` state stopping further automatic polling.

**Live technical proof — 2026-09-21.** One authorized real ImageGen
Characters refinement was sent exactly once from the browser after validating
the accepted cast, frozen parent hash, isolated H3-disabled runtime, prior
terminal task evidence, and empty current native lease. The specialist's
preflight passed; its schema-valid completion was automatically admitted as an
unselected 1672×941 candidate and released the matching lease. The existing
cast/reference decision stayed at r1. Desktop and 390px inspection exposed a
separate, unremediated observer defect: repeated polls during normal delivery
publication persist repeated `delivery_partial` rejections and clutter the
gallery. This evidence closes the one-submit technical proof but does not
constitute creator-usability acceptance; no retry, manual refresh, selection,
or cleanup is authorized by this step.

**In-scope publication correction — 2026-09-21.** The live trial demonstrated
that the observer persisted every normal output-before-manifest poll as a
rejection. The durable contract now treats `completion.json` as the one final
publication marker: any pre-marker staging state remains pending and creates no
history; post-marker manifest, integrity, and currentness faults remain durable
rejections with explicit final-publication provenance. Existing live rows are
preserved without inference or rewrite: because the old schema lacks that
provenance, the gallery groups those phase-unknown partial observations in a
closed audit disclosure, while genuine newly recorded final failures remain
visible. Focused backend and automatic Characters browser checks prove multiple
pending polls → one accepted candidate, a final-invalid rejection, and an
explicit post-marker `delivery_partial` rejection. Static assets are refreshed.
The real generated candidate is also verified through project-managed asset
serving, independent of staging.

## U3 unified Appearance workspace — 2026-09-21

**Approved step and deliverable.** Replace the disconnected Characters
selection, adjustment, and candidate blocks with one image-first Appearance
workspace. It has a large viewed image with enlarge access, recognizable
thumbnails, practical two-image comparison, and unambiguous labels for the
viewed image versus the selected identity reference. Selection appears beside
the viewed image. One ideas field has two explicit modes: **基于当前图片修改**
freezes the viewed image as the parent, while **尝试全新方案** uses no parent.
The existing native proposal dispatch/observation path remains the only send
and delivery path; returned candidates join the gallery unselected.

**Contract change and evidence.** Reviewer and rationale are not required for
this creator stage. The selection request/domain contract must own that change;
the browser must not invent hidden reviewer or reason values. Existing
decisions, proposals, failed deliveries, selection version/currentness checks,
accepted-cast session guards, and cancellation safety remain retained. Completed,
cancelled, and attempted proposals must communicate their true state and cannot
offer a Send action that only fails. Focused browser flows cover
select/create/send/observe behavior, draft and session isolation, comparison and
enlarge behavior using retained images and deterministic fixtures.

**Desktop acceptance and deferred responsive polish — 2026-09-21.** This
creator review is desktop-first: 1440px and 1920px are visual acceptance
viewports. Smaller desktop windows and phone/narrow-screen polish are deferred:
preserve inexpensive existing responsive behavior, but do not make 1280px or
mobile screenshots completion gates for U3. Lifecycle, currentness, and session
regression coverage remain required independent of viewport.

**Exclusions and stop condition.** No new media generation, provider/settings
platform work, H3/Qwen integration, new media owner, or unrelated stage redesign
is authorized. Technical instructions and provenance stay available in folded
detail. Stop for a material scope or contract tradeoff; otherwise deliver the
small cohesive workspace, regenerated static assets, independent stable-delta
review, and a fresh local production preview for attended creator inspection.

**U3 cancellation and multi-comparison receipt — 2026-09-21.** Reopening cast
text is confirmed as a durable authority suspension, not a local editor mode.
The bounded correction adds a CAS-protected cancellation transition that
restores the prior accepted revision without a save or revision increment only
while its upstream binding remains current; a changed binding remains stale and
unavailable. Appearance comparison is now an explicit local set of any two to
four candidates, while retained gallery size remains unrestricted. The
five-image browser proof runs only in an isolated fake runtime with mocked
ImageGen delivery evidence: it validates UI/state behavior, not a persistent
production delivery, and does not replace live ImageGen evidence. Truthful
managed imports are project-scoped and not gallery candidates; a character-owned
import membership is an unapproved product seam. Focused storage and browser
paths cover cancellation, stale non-revival, arbitrary non-adjacent 2/3/4
comparison, fourth-cap replacement, no implicit selection, and cast-session
reset. Desktop inspection is limited to 1440 and 1920.

**Approved import-to-character extension — 2026-09-21.** Reuse the truthful
managed-image importer and its origin/rights provenance. Add only a
character-owned imported-appearance membership bound to a current accepted cast
subject; it creates browseable unselected options, not a decision or generated
delivery. Verify import provenance/currentness, no automatic selection, session
isolation, 2–4 comparison, cancellation, and one retained production-backed
fixture with existing lawful files. No provider or generated-delivery evidence
is authorized.

## U3 Characters usability acceptance — 2026-09-21

**Accepted scope.** The attended creator review accepted the bounded
`stage=characters` workspace for cancel-edit safety, truthful imports, large
image/zoom inspection, and arbitrary explicit two-, three-, or four-image
comparison at desktop 1440px and 1920px. The clean retained inspection fixture
is project `24519b81-47b1-4237-b27f-6ec568bd5407`; it contains five labelled,
distinct imported assets with declared `unknown` rights. The earlier
nine-membership project remains historical evidence, not a handoff fixture.

**Evidence.** Commit
`a54251dd139f672622918e196b0df642633c4d67` binds the post-upload membership
step to the live project/cast session. Its focused browser coverage proves five
browser imports, zoom, two-to-four comparison with a disabled fifth, explicit
selection, reload/restart, cancel-reopen safety, and no stale membership attach
after a held project or cast-session change. The committed static bundle is
fresh for that source change.

**Boundaries.** An imported image can be browsed, compared, enlarged, or
explicitly selected, but is not a specialist-delivery candidate and cannot be
an adjustment parent. This is an explicit unsupported product boundary, not a
creative rejection. This acceptance does not accept all U3 surfaces, any
environment/prop workspace, video, F2/F7 creative or media output, or a new
provider call. The previous authorized ImageGen proof is complete; no further
generation is authorized by this acceptance record.

## U3 environment/prop image-first F3B review — 2026-09-21

**Approved step and deliverable.** Replace the old compact F3B grid in the
existing `stage=source` ArtPanel, in place, with one image-first environment or
prop review workspace. The existing ArtPanel remains the only entry; it spans
the Source grid for a usable desktop canvas rather than creating a workspace,
route, or navigation stage. A creator chooses a stable accepted-art subject,
views and zooms an available candidate, browses an unrestricted same-subject
gallery, and locally compares any two, three, or four candidates. The fourth
cap blocks a fifth until one is removed. Technical provenance, IDs, rights, and
dimensions stay folded.

**Ownership and lifecycle.** Accepted `art.json` owns the stable `scene`/`prop`
subjects and its revision/content hash. The existing F3B proposal, delivery,
managed-asset, provenance, currentness, prepare/copy/refresh/cancel APIs, and
project/session guards remain the sole owners of their respective state. The
surface only presents them: it shows missing, cancelled, changed/stale,
rejected, awaiting-delivery, and current truthfully. It does not create a new
generator, store, selection/import membership, refinement parent, or creative
acceptance. Copy continues to mean the existing manual handoff, not provider
dispatch.

**Evidence and stopping condition.** Focused browser coverage proves the
preexisting F3B current → restart → art-reopen/stale → cancel-release lifecycle,
same-document held A→B→A project response containment, and an explicitly
mocked, read-only five-candidate browser response for arbitrary 2/3/4 comparison
and cap replacement. The mock response writes no delivery manifest or tool
attestation and is not creative evidence. The portable loopback fixture at
`/v2/e2e/f3b-mock-demo.html` reuses the same gallery with distinct static SVG
A–E cards for separate scene and prop subjects; its source and exact local
startup are documented in `frontend/README.md`. It is visibly mock/read-only,
has no production route or data write, and is the 1440px/1920px presentation
proof. No genuine retained five-candidate F3B set exists, so no creative
preview is claimed. Stop at this presentation/lifecycle reuse slice; video,
selection/import/refinement, generation/provider work, production acceptance,
and broader redesign remain excluded.

## F3B explicit subject-reference decision — 2026-09-22

**Approved step and deliverable.** Add the smallest durable creator choice for
a current accepted-art scene or prop: explicitly choose or replace one current,
same-subject F3B candidate as its reference. The deliverable retains the Art
Panel entry and its browse/zoom/2–4 comparison, adds an obvious chosen-reference
state and truthful next step, and records ADR 0078 before implementation.

**Scope and stop condition.** The decision freezes art/subject/currentness and
managed-asset identity under CAS. It is not a creative/media/production
approval, F5/F7 consumer, shot/keyframe install, import membership, refinement
parent, generator, provider call, or general approval framework. Preserve
historical stale decisions; stop and seek direction for any reset that would
lose valued project discovery. Verify choice/replacement/no-auto-choice,
currentness/CAS/restart/reopen/session containment, static assets, desktop
1440/1920, and an independent stable-delta review. A portable explicit-mock
demo may prove interaction only and must never claim generated evidence.

**Preview evidence.** The separate
`/v2/e2e/f3b-reference-decision-demo.html` loopback route reuses the gallery
with inline static SVG data URLs and tab-local React state. It visibly proves
scene/prop choose, replacement, viewed-versus-current labeling, and permanent
stale history after a simulated art change at 1440px and 1920px. It makes no
project/API or provider request and hides every study action. The retained
read-only F3B gallery URL remains unchanged; backend regression, not this
simulator, is the persistence/restart evidence.

**2026-09-22 bounded presentation follow-up.** The creator reported that the
reference choice works well. The shared production/simulator gallery now calls
out the selected image as "当前参考图" and keeps the reference revision, decision
ID, and asset ID inside collapsed technical details. This is usability
acceptance for that narrow presentation only; it does not accept creative/media
content, a production consumer, or the portable simulator as persistence proof.
