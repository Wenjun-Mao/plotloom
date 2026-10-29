# Project language consistency: Chinese UI, Chinese and English content

Status: finalized and explicitly authorized for end-to-end implementation on
2026-10-28. Both languages completed all eight native text stages and installation
at389bf861; Chinese UI and the affected manual/browser regressions passed. Candidate
C's full local run failed78Python cases. The scoped fixture, native lifecycle,
capacity and authored-composition bridge repairs have independent review closure
and exact integration. D4's real English Continue then hit two checker metadata
failures; the strict schema/instruction follow-up is reviewed and integrated.
Next prove the original Chinese Continue under the new pin, then regenerate a
compatible English replacement fixture. Full final qualification, activation and
image/H3/media acceptance remain open.
Source inspected: main `9de44e189a4295ce763afe514aab3f300434fc3f`;
owned Shuohao gitlink `4f9b2128c82adf623f594ba714c97d0afcfc16a2`.

## Outcome and owner decisions

A creator can use Plotloom's consistent Chinese interface to produce either a
Chinese or an English story. Newly authored outlines, branches, character/art
descriptions, scripts, storyboards, intent/presentation explanations and standalone
reports follow that project's language through persisted installation and playable
media. Internal instructions and stable data identities use their required language.

The owner approved these four boundaries on 2026-10-28:

| Layer | Agreed responsibility |
| --- | --- |
| Application interface | A personal interface-language preference, independent of the story |
| Creative content | The project's chosen language throughout readable creative material |
| Standalone reports and exports | The project's language, including document headings |
| Internal instructions and data | Provider-appropriate language and stable identities, with readable explanations |

The owner's explicit first-delivery choice is **Chinese UI first; both content
languages**. This release supplies coherent Chinese application chrome and both
Simplified Chinese (`zh-CN`) and English (`en-US`) project workflows. It creates the
separation needed by a later English interface; it does not expose a nonfunctional
English UI switch or require a full English application catalogue now. Sol/medium
remains the text-generation default, as explicitly reaffirmed by the owner.

The owner also explicitly chose **assistant translation checking; creator intent
review** for video production. The assistant drafts and checks required English
provider directions; the creator reviews project-language intent and authorizes
generation. The record must attribute the translation check to the assistant,
without claiming the creator personally reviewed English.

The owner subsequently agreed to make **creative description versus provider
adaptation** the architectural boundary for this work. The creative description
is the source of truth; each provider receives derived instructions. The creator
reviews a complete actionable production brief in the project language, rather
than a high-level intent summary that omits actual requested effects.

Existing stories and media remain their authored originals. This release does not
translate existing approved prose in place, rewrite retained reports, regenerate
old media, or add a bulk story-translation feature. Existing projects benefit from
localized application labels; new/revised creative work uses the new contract.
Proper names, deliberate foreign quotations, source excerpts and literal screen
text can remain in their authored language. This is language consistency, not a
new dramatic-quality threshold or a claim of improved storytelling.

## Architectural boundary and bounded modularization

The production brief is a coherent read projection of the existing authoritative
story, shot, dialogue, presentation, reference and timing owners. It covers what
the audience should see/hear: action and order, performance, camera, continuity,
exact speech and visible words, material references, sound and relevant constraints.
It is not a second independently editable story or another persistence authority.
Edits return to the existing owning field; the brief refreshes from that source.

Provider adapters consume this source-bound brief plus explicit generation settings
and produce derived requests. Provider vocabulary, prompt format, language and
capability handling stay at that boundary. Use deterministic compilation for exact
fields/structure and bounded assistant transformation for prose requiring semantic
adaptation. Existing image and H3 integrations are the concrete targets; provider
switching UI, a plugin framework and hypothetical backends are outside scope.

An adapter cannot silently add a creative fact, remove a requirement, substitute
dialogue, or change the story to fit its capabilities. If it cannot represent a
requirement faithfully, surface the exact conflict in the project language. A
necessary creative change goes to the owning creative field for review; approved
discretion already expressed in the brief remains available. Routine faithful
wording/formatting does not create another human approval checkpoint. Provider
settings with user-visible effects are part of the generation review, not hidden
inside translation. Technical details expose the exact submitted request.

The owner accepted the following three supporting extractions together with the
creative/provider boundary, and agreed to keep broader refactoring outside this
iteration. These organize the planned language work without adding new features:

| Boundary | Why it belongs in this iteration | Limit |
| --- | --- | --- |
| Language policy | One owner maps content/report locales and selects applicable timing rules; UI preference is independent and adapters own provider-specific language labels | Two content languages and the current Chinese UI; no general translation service |
| Presentation labels and creative data | UI/report labels, placeholders and formatted diagnostics cannot become saved story values; readable prose cannot be replaced by raw machine prompts | Feature-owned helpers/read projections around touched consumers, not a renderer or frontend rewrite |
| Dialogue timing policy and provider limits | Language-sensitive speech estimates belong to trusted timing; provider cut capacity is a separate constraint checked against it | Extract/reconcile the changed timing rules and consumers, preserving route authority; no new pacing engine |

Verification and authorization also keep distinct responsibilities within the
existing lifecycle: structural validation, semantic adaptation fidelity, creator
generation authorization and generated-media inspection each establish different
facts. Reuse existing admission/review/job mechanisms and typed results; do not
build a new approval engine, queue, event system or universal review framework.

Add focused boundary tests: formatting/adaptation cannot write creative state;
lossy or unsupported adaptation is reported before dispatch; a creative edit
invalidates derived requests/checks; changing only UI presentation does not;
and a valid prompt/translation never labels the generated video accepted. Reuse
an existing verified adaptation only while its exact source, adapter contract,
settings and compiled request remain current. No second live provider or extra
generation campaign is required to test these boundaries.

Stop extraction when each changed responsibility has one clear owner and can be
tested without unrelated subsystems. Defer unrelated oversized-file cleanup,
microservices, a general provider registry, a complete renderer replacement, full
English UI, bulk translation and general story-quality/pacing work. If a broader
refactor is claimed necessary, first identify the concrete dependency blocking
the existing bilingual journey and make the smallest justified change.

## Current findings and ownership

| Finding | Owning source / implication |
| --- | --- |
| Brief offers `zh-CN`/`en-US`; schema accepts any string | `frontend/src/pages/BriefPage.tsx`, `src/plotloom/brief_contracts.py`, `working_inputs.py`: define supported new-work locales explicitly |
| No shared bilingual UI framework; Chinese timestamps and HTML | `frontend/index.html`, `frontend/src/ui-time.ts`, page components: centralize current Chinese copy at cohesive owners, not a wholesale frontend rewrite |
| English report/content assumptions differ | `outline_preparation.py`, `outline_report_metadata.py`, `persistence/project/script.py`: Script currently forces `lang=en`; Outline separates `zh/en` metadata from content locale |
| Native intent forces Chinese; native report languages are fixed | `native_bridge_intent_service.py`, `prompt_templates/production_bridge_intent.yaml`, `native_bridge_*_contract.py`, `video_directions_contract.py`, `scripts/branch_suggestion.py` |
| Timing selection uses exact language then wildcard | `canonical_schema.py`, `production_dialogue_timing.py`: saved `en-US` currently misses explicit `en` timing rules; this is a confirmed inconsistency, not evidence all English generation fails |
| Upstream Script/F5 timing has its own text assumptions | Owned `novel-script.mjs` / `novel-storyboard.mjs`: 4.5 non-whitespace characters/sec defaults and Script's 35-character line limit do not vary with report language |
| Display strings sometimes are stored semantic values | `DirectionPresets.tsx`, `scene-beats-editor.ts`, owned Art `scale`: preserve stored meaning/IDs; translate display/instruction projections deliberately |
| Some English provider prose doubles as the readable shot description | `storyboard_brief_style.py` and owned F5 require English `cut.frame`; Art image prompts also require English: give readable descriptions a project-language owner rather than relabeling these prompts |
| H3 requires English non-dialogue directions | `video_backends/minimax_h3/directions.py`, `video_contracts.py`, `video_batch_contracts.py`, `video_batch_basis.py`, `delegated_qa_video.py`: changing ordinary review requires a truthful new authority contract |
| Existing original reports are isolated immutable HTML | `StaticReportReader.tsx`, owned report producers: fix new report producers; do not translate retained HTML on load |

The eight native text operations are owned by `autopilot_launch.CREATIVE_STAGES`:
Outline, Branches, Characters, Art, Script, Storyboard, Bridge Intent and Bridge
Presentation. Manual stage entry and native automation must consume the same
language contract. Fake-host compact fixtures are useful tests, not real generation
evidence. Source paths in this plan are relative to the repository root.

## A. One language contract, with explicit field ownership

Add a small cohesive language-policy owner, rather than a general translation
service. It maps content locale to report locale (`zh`/`en`) and selects the canonical
dialogue timing profile. Each provider adapter converts the canonical locale to its
own required language label; core policy contains no provider vocabulary. Keep UI
locale separate. New-work
validation gives a Chinese actionable error for unsupported language choices;
reading an existing project must not silently relabel or rewrite it.

Freeze the project locale, report locale and language-policy/timing version with
the source settings in every relevant request. Include these inputs in existing
request/currentness identities. A UI preference never changes a request hash,
approved content, or a generation job. A project-language edit follows the existing
explicit Brief apply/currentness path: show affected work, retain old results,
and require fresh dependent generation/approval as already applicable. Reopening,
restoring drafts and importing content must not default an English project to Chinese.

Classify fields at their actual schema/preparation owners:

- Human-readable authored prose, action, dialogue, notes, choice text and creative
  explanations follow the project language.
- Report headings, units and semantic enum labels follow the report language.
  English reports need readable English gate/failure summaries too.
- Stable JSON keys, IDs, paths, hashes, schema enums and technical diagnostic codes
  retain their identities. A Chinese stored Art scale enum may display as English.
- Exact source quotations, span coordinates, proper names, intentional foreign
  speech and literal visible text retain source ownership. Do not translate text
  and leave its old offsets/hashes attached. Deliberate exceptions must be explicit
  source facts or author directions, not inferred from accidental model output.
- Provider instructions retain their required language. English provider fields
  are technical content even inside a Chinese report and are disclosed as such.

Deterministic checks enforce metadata, complete field coverage and language
identity. Unicode/word-count heuristics may surface suspicious prose but cannot
certify language fidelity or reject legitimate names/quotes by themselves. Use a
bounded content-language check of the complete candidate against its classified
fields before adoption; integrate failures with existing typed corrective jobs,
without rewriting candidates in a renderer or silently translating on receipt.

Resolve preset defaults without changing saved creative facts: existing group/value
semantics remain authoritative, known built-ins get localized derived wording,
and custom authored text remains source material. Remove behavior that branches
on a translated label. All newly persisted creative defaults derive from the project:
working title, entity name, scene title, shot title, narrator and cue language.
Chinese application placeholders/help are separate from saved creative values.
Cover `BriefPage.tsx`, `bible-editor.ts`, `scene-beats-editor.ts` and
`storyboard-editor.ts`; keep already saved author values intact. Verify English
manual creation, save, draft recovery and reopen for these defaults, alongside
generated work. UI fallback labels must not leak into canon or exported titles.

During implementation, update the owning product/engineering specifications and
spec map, creator guidance and a concise language ADR. Keep this roadmap as the
execution owner; the ADR records the boundary decisions and rationale. Allocate
its number from the then-current repository to avoid another ADR collision.

## B. Text generation, reports and timing

Update primary instructions, response schemas, binder/receiving checks, renderers
and correction guidance together. Remove forced-English Script report metadata
and forced-Chinese intent prose. Carry the exact project/report locale through all
eight operations, supported manual entry, and automation. English source material
may be adapted to Chinese and vice versa when that is the saved author intent;
literal source excerpts stay visibly identified as source, not generated prose.

Change owned Shuohao stage instructions/validators/renderers at their source.
Resolve fields with two responsibilities explicitly. In particular, F5 `cut.frame`
currently doubles as the readable composition and an English image prompt. Give
the project-language composition its own authoritative authored field and derive
the provider rendering from it, bound to the source; do the same wherever a raw
Art/Cast provider prompt substitutes for a readable description. Choose field names
after tracing consumers, then change the upstream shape, prompt, validator,
canonical bridge, readers and image handoff together. Provider-English requirements
belong to the provider field, not to the creator-facing description. Avoid two
independently editable descriptions that can disagree. New report primary prose
must use the project-language owner, with machine prompts in labeled technical
detail. Include new CN/EN examples proving the displayed composition and final
media source describe the same image; translating a heading alone cannot pass.

Use existing `zh/en` dictionaries where available and add missing success/failure
labels. Maintain license notices and locally copyable skill boundaries; no HTML
replacement overlay, new competing stage schema, or shared import that breaks
standalone skill use. Keep new report language deterministic from the frozen
request, and reject candidate metadata that conflicts with it.

Give both supported content locales explicit timing rules. Remove `en-US`'s
accidental wildcard selection. Reconcile upstream Script/Storyboard estimators,
line limits, canonical minima and cut/route constraints using one frozen policy;
the model cannot choose a faster speaking rate to satisfy a gate. Keep quoted or
intentionally multilingual lines explicit instead of selecting a rate from UI
language. Calibrate English word/character treatment on short real utterances,
then freeze the chosen estimator and explain its limitations. Chinese regression
cases must retain sensible bounds. This is a timing-consistency repair, not a
general pacing/story-quality redesign.

Affected source owners include `persistence/project/{cast,art,script,storyboard_review}.py`,
`scripts/script_receiving.py`, `scripts/storyboard-receiving.mjs`, native bridge
services/contracts, `script_dialogue_compatibility.py`, `codex_exec_resources.py`
and their pinned stage instructions. Export only through existing supported
document/media paths; adding new formats is outside scope. Raw project JSON keeps
its technical keys and source originals.

## C. Consistent Chinese creator interface

Cover Creator and Professional, project directory/Brief/source, stage editors and
readers, generation/status/recovery, media review, settings, and player controls.
Application controls/help/errors remain Chinese even for an English project;
creative prose and standalone report document chrome remain English for that project.
Translate exposed labels such as Episode, Source scene, Beats and Reference needs,
plus size/camera/scale labels, using stable semantic mappings. Keep brand/model
names and useful standard units. Move exact raw diagnostics into technical detail
beside a readable Chinese explanation and next action.

Use feature-owned wording modules and a small explicit application-locale boundary.
Do not build a runtime translation provider, two application copies, or an English
catalogue populated with placeholders. Add a regression check for untranslated
normal product copy with documented exceptions; this supplements rendered review.
Check loading, empty, ready, failed, stale, frozen and unsupported states, not just
the successful happy path. A complete inventory of supported surfaces belongs in
the implementation's existing verification record, not a new tracking subsystem.

## D. Provider directions and truthful review

For new requests, the creator reviews the complete actionable production brief
defined above, in the project language, and explicitly authorizes generation.
This includes the provider settings with visible effects; an abbreviated intent
summary is insufficient. An assistant drafts English H3
directions and a separate bounded semantic check compares all fields against the
exact original sources, checking actions, identities, positions, sound roles,
negation, completeness and preservation of dialogue/visible text. A schema-valid
translation alone is not a fidelity pass. Use a distinct native checking invocation
with original sources and the complete candidate, rather than the drafter's own
completion claim. Record actual checking provenance and findings.

Bind source, translated fields, checking result and final compiled prompt to the
same immutable request. Edits to any relevant source, translation or supplement
invalidate its check and authorization. Show the project-language material as the
normal review surface; retain exact provider instructions in technical detail.
An English project also receives a fidelity check of the provider rewrite.
All creative decisions in that rewrite must be represented by the reviewed brief
or its explicit permitted discretion. A newly invented decision returns to the
creative owner; an assistant's translation check cannot authorize it.

Replace new-work `reviewedEnglish=true` / `whole-batch-english.v1` claims with a
versioned distinction between creator intent authorization and assistant translation
verification. Do not attribute the assistant's English review to the creator.
Update single-shot and batch start, resume/replacement, preparation/dispatch guards,
QA attribution and final receipt comparisons consistently. Keep real creator
authorization and delegated QA distinct; technical translation checking is not
creative acceptance or dispatch consent. A rejected translation returns an
actionable candidate for the existing correction/review path, with no video sent.
Retained frozen jobs/receipts keep their original bytes and stated authority;
do not manufacture new translation checks for old media.

This is a narrow use of the existing native text execution mechanism, not another
provider or a generic multi-agent translation platform. Document the actual draft
and check roles and disclose AI semantic-review limits. The owner's approval of
this workflow does not label an uninspected translation as checked.

## Execution order and early real outcomes

1. **Preflight and capability probe.** Confirm clean source/owned-fork identity,
   current native Sol/medium dispatch, source pins, installed package, supported
   schemas and runtime/provider readiness. Inventory two new QA homes and exact
   grant needs before media work. Check an available local method for inspecting
   actual clip speech early. Prefer actual listening when supported; a local-only
   transcription tool may support language/wording checks without adding a product
   service or cloud provider. Test it against known Chinese/English speech before
   using its output as evidence. Document perceptual limits; headers, waveforms and
   intended scripts alone do not prove spoken language. Do not change Voice Lab
   presets or add voice cloning to solve a separate product problem.
2. **Language foundation and first vertical slice.** Record the language ADR and
   the creative/adaptation boundary; add the owning language policy. Implement
   Brief/source → Outline → report/persisted
   readback first in both languages. Use two small new original stories with the
   same simple branch shape. Perform the real native operations after focused
   contracts pass, before broad frontend translation or final qualification.
3. **Finish the text path.** Continue those same projects through all eight native
   stages, install canon, reopen and inspect current API/readers. Resolve owned
   upstream language/timing contracts jointly. Review the direction after this
   real result: both languages must have coherent writing/reports and sensible
   dialogue capacity before investing in broad media. Internal review passes
   continue the authorized run without a new routine owner approval.
4. **Complete Chinese UI and media review.** Implement C and the settled D across
   existing manual and batch surfaces. Inspect all supported view/state families.
   Verify translation rejection, source changes, stale grants and duplicate-submit
   refusal on focused fixtures before spending on videos.
5. **Small real media journey.** Use the same two QA projects, each with one shared
   opening, one choice and two endings. Aim for approximately 20 seconds per route
   and three unique ten-second windows per project; adjust shot scheduling to valid
   authored content rather than fabricate durations. Include a short ordinary line
   in each story language, a deliberate proper-name/quoted exception, and exact
   visible text with its existing supported presentation treatment. Check that
   provider English directions never become unwanted spoken/visible text. Generate
   and select necessary keyframes/refs and H3 clips through Plotloom, actually play
   both routes per language, pause at the choice and restart/replay. Inspect a real
   standalone report and existing export outside the workbench.
6. **Integrated qualification, activation and closeout.** One owner qualifies the
   stable code/fork/package candidate; independent review checks the diff and real
   evidence. Activate quietly only under the later execution approval, preserving
   current projects/settings/claims/UNKNOWN/H5 assets and the single recovery.
   Verify installed language behavior/readback and existing playback. Retain useful
   bilingual examples, concise evidence and source commits; retire only identified
   disposable scratch/runtimes after quiescence. Report actual limitations and any
   remaining creator acceptance separately.

The initial media shape is roughly six unique clips plus necessary references;
this is a forecast, not an invented aggregate spending cap. Use the smallest useful
experiments, finite project scope and existing provider/account rules. Existing
frozen finite grants remain enforced; use new exact grants for these QA projects.
Do not expand an old grant or clear UNKNOWN holds. Diagnose failed attempts and
use the existing bounded correction/replacement mechanisms. After two unsuccessful
attempts at the same criterion, reassess the cause/method as AGENTS requires;
that is a diagnostic checkpoint, not automatic abandonment or an owner question.

## Evidence required for completion

| Claim | Required evidence; passing tests alone is insufficient |
| --- | --- |
| Both content languages work | All eight operations in each fresh project, complete prose/field review, native installation, reopen and API readback; exact project/report locale retained |
| Language boundaries hold | Source quotes/names/IDs preserved, report headings match project, application chrome stays Chinese, new cue defaults and presets work; ordinary language mismatch caught without translating approved source silently |
| Manual authoring stays in project language | English manual creation/save/draft recovery/reopen covers working title, entity, scene, shot and narrator defaults; Chinese UI placeholders are never saved as creative prose |
| Readable descriptions own media meaning | New CN/EN shot and Art/Cast examples expose project-language composition/descriptions, preserve separately bound provider instructions and use the same intended facts for image/video generation |
| Change/currentness safety | Locale change during prepared work refuses stale adoption/dispatch; UI-only display changes never stale creative work; saved draft/reopen retains chosen language; old projects remain readable |
| English timing is deliberate | Explicit `en-US` rule, upstream/canonical agreement, frozen estimator, short/long/boundary dialogue tests in both languages, actual speech fit in selected windows |
| Provider translation is trustworthy within stated limits | Complete source/field coverage, independently checked translation, real omission/negation/extra-speech failure fixtures, changed-input invalidation, truthful actors, exact dispatch prompt |
| Creative/provider responsibilities remain separate | Complete project-language production brief represents requested effects; adapter writes cannot change creative owners; unsupported requirements produce readable conflicts; creative changes return to source review; no media acceptance inferred from translation checks |
| Chinese UI is consistent | Rendered Creator/Pro and every inventoried normal surface/state at supported desktop sizes; English reports and English creative content remain readable inside Chinese chrome |
| Playable media is language-consistent | Four actual route plays plus choice/restart, exact window inspection, actual audio language/wording evidence and native-audio limitations; no claim of personal creative approval |
| Installed release preserves valued work | Qualified package/pins, installed fresh-project readback, current-project/media/settings/grant/uncertainty preservation, recoverable rollback and idle cleanup |

Speech transcription is evidence of recognized words/language, not proof of natural
performance, lip-sync, mix quality or human listening. If no usable speech inspection
method is available, continue text/UI/software qualification but explicitly leave
spoken-language/media acceptance incomplete; resolve that concrete capability gap
before claiming the complete end-to-end outcome. Do not conceal it behind audio
track presence or a reviewer boolean.

Use `quick`, exact `focused` selectors and reviewed `module` coverage during
development. Extend language/report/Brief/currentness/draft and H3/batch tests at
their existing owners, including upstream selftests and frontend/browser cases.
Examples: `test_outline_report_*`, `test_art_script_operation_context.py`,
`test_script_dialogue_compatibility.py`, `test_f5_dialogue_timing.py`, native
bridge intent/presentation and resource-pin tests, plus affected media authority
tests. Derive exact selectors from `scripts/testing/module-ownership.json` at
execution. This is a cross-layer contract change: one stable final `full` local
qualification and exact installed-wheel checks are required. Keep failed runs
failed, reuse unchanged evidence and target repairs causally. GitHub CI is off.

## Source organization, installation and permissions

Default to one serial source owner in the retained checkout. Native reviews are
read-only and attended. Separate task/model choices already have standing owner
approval; choose them at dispatch under Relay. Do not mutate global model defaults.

Review responsibilities before substantial edits above 400 lines. Current large
owners include `canonical_schema.py` (505), `SceneBeatsPage.tsx` (1,267), owned
`novel-script.mjs` (1,091) and `novel-storyboard.mjs` (1,835). Put new language,
timing and localized report responsibilities in cohesive modules; extract only
responsibilities changed by this work. Keep copied upstream skills usable alone.
If substantial edits leave a file above 500 lines, explain its remaining cohesion
or why further extraction is outside this bounded change.

The owned fork requires local commits, then a committed parent gitlink before
native packages can freeze the new clean pin. No remote push is required by the
executable pin check. ADR 0147 currently calls for a published pin: during this
implementation, amend it narrowly to allow local-only qualification/activation from an exact
retained Git pin, while requiring publication or explicit Git transfer before
another host can depend on it. Keep license/fork notices and reproducible resource
hashes. Do not substitute a new pin into old packages. Update stale pin instructions
in the handoff guide as part of this scope. Normal remote publication remains a
separate user request, and a push that triggers CI needs new explicit CI authority.

The owner's subsequent instruction, "Go and implement the plan E2E with Relay
Direct," authorizes source and owned-fork changes, local commits, focused/full
qualification, the two disposable QA projects identified during preflight,
their exact prospective grants, native text/image and configured H3 work,
necessary local-only QA transcription dependencies if needed, preservation-checked
core/bridge reload/activation, single recovery refresh and scoped scratch cleanup.
The owner explicitly encourages parallel Codex tasks/subagents and separate task
coordinators so the director remains available. Standing task/model/reasoning
selection authority under Relay Direct is reaffirmed. Use best judgment on
in-scope implementation and QA decisions while the owner is unavailable; record
only consequential decisions in this plan or its existing verification record
for later review. Routine checkpoints, causal repairs and covered activation
continue without renewed permission. Existing task/model approvals need no renewal. No GitHub CI,
main/fork push, new paid provider, current-story translation/deletion, Voice Lab
reconfiguration, broad startup repair or unrelated quality work is included.

Use current lifecycle/quiescence operations. Verify rollback on disposable data
before activation, especially any new review/persistence representation. Preserve
the nine current projects and existing immutable media/evidence; no automatic
backup collection or old-runtime graveyard. Refresh the one functional recovery
only when a new installed candidate warrants it. The manager owns cleanup and
collects actual worker/reviewer finals before releasing their access.

## Forecast and review points

Initial estimate: **18–30 hours of active implementation/review**, plus roughly
**3–8 hours of native generation, media and qualification waiting**, some overlap
possible. This is about 3–5 working days of combined effort, not a deadline.
The architectural refinement and supporting extractions organize the same scope;
they do not add new providers, a second live campaign or another release milestone.
Assumptions: the owned fork remains locally editable, existing native/H3 services
are healthy, a local speech-inspection path is usable, and supported English audio
requires no provider replacement. Real timings from the first bilingual slice
should refine this forecast. Full English UI and old-story conversion are excluded.

Review direction after the first bilingual text installation, earlier if source
ownership/timing or translation fidelity makes the agreed workflow infeasible;
then review the stable integrated candidate. Ordinary implementation choices,
causal repair and truthful QA selections are delegated within the approved run.
Provider changes, destructive valued-data conversion, a broader feature scope or
an unavailable capability necessary for the promised outcome require a concrete
decision rather than silent weakening of acceptance.

## Planning reviews

The independent outcome/completeness review (requested Sol/xhigh) found that all
generated QA paths could pass while English manual additions saved Chinese default
titles/names. Section A and completion evidence now explicitly cover those manual
defaults, save/recovery/reopen and separation from UI placeholders. No extra media
run or owner decision is needed for that repair.

Root's additional source check found that F5 English `cut.frame` also supplies the
readable composition. Section B now requires explicit authored-description versus
provider-rendering ownership, with matching consumers and real evidence. The
outcome reviewer's focused recheck passed both amendments with no remaining findings.

The separate avoidable-restrictions reviewer (requested Sol/medium) found no
actionable restrictions. It checked continued internal review/repair authority,
forecast versus budget limits, the real ADR 0147 publication conflict, planning-only
authorization and necessary audio/attribution safeguards. No success or evidence
criteria changed after that review, so another outcome recheck is unnecessary.

Both reviewers were independent, read-only native agents with fresh context;
their actual finals were collected. Requested model/effort selectors are recorded
above; effective host settings were not independently verified. No implementation
starts from a planning review pass alone.

The later owner-approved creative/adaptation boundary now explicitly defines the
complete production brief, adapter write/semantic limits and three bounded
supporting extractions. The outcome reviewer (requested Sol/xhigh) passed the
focused amendment review with no findings. The execution-restrictions reviewer
(requested Sol/medium) also passed with no findings, including the clarification
that provider-specific language labels belong to adapters, not core language
policy. That clarification changes no success criteria and needs no additional
outcome review. Both actual finals were collected; the original reviews remain
the baseline. No provider, campaign, framework or execution approval was added.

## Final implementation handoff

The owner has settled the product direction and bounded modularization scope and
has explicitly instructed Relay Direct to implement it end to end. There are no
unanswered product-design questions in this plan. Carry this exact plan into
execution without repeating brainstorming or asking again for standing task/model
permissions. The authorized execution envelope above includes
source/owned-fork changes, the two disposable bilingual QA projects and exact
grants, configured native/image/H3 generation, local qualification, scoped activation,
recovery refresh and cleanup. Publication and CI remain outside that envelope.

Start with the named capability probes and bilingual vertical slice. Technical
uncertainty about speech inspection, timing or provider fidelity is resolved there
and reported honestly against the existing completion criteria. Finalization only
records the agreed scope and makes the previously reviewed technical choices
definite; it changes no outcome, evidence requirement or execution permission and
therefore needs no additional review round.

## Execution ownership

Director: native chat `01a04525-e907-7630-9640-78790d69e8ae`.
Retained source and integration checkout: `/Users/wjmao/.codex/worktrees/b30f/plotloom`
on `main`. Installed runtime: `/Users/wjmao/projects/HU/plotloom`; do not use its
startup working directory as an implementation checkout. The coordinator records
its actual native ID, reporting route and concrete work ownership after dispatch.
The director releases source writes to the coordinator then performs independent
checkpoint/final review without concurrent source edits.

Use parallelism where ownership is clear: attended read-only analysis/reviews and
independent tasks may overlap; implementation workers need explicit nonoverlapping
ownership or isolated checkouts with coordinator-owned integration. Preserve one
owner for shared contracts, Git/index operations, qualification and live activation.
Native subagents follow Relay's attended read-only rule. The coordinator may manage
ordinary Codex executor tasks and chooses supported explicit settings under Direct.
Register Relay reporting at each level before work, collect actual results, and
retire child assignments only after review and quiescence. The director owns final
coordinator acceptance/archival and reporting-route retirement.

### Execution checkpoint — 2026-10-28

Coordinator `01a184ec-5035-7542-a6e1-869dbdc84660` registered Relay reporting to the
director before implementation (route `7b6a4bdb-2210-41ba-ab16-6bd7a6854094`).
Clean retained source was `d2e3c26d` on `main`; installed runtime remains untouched.
The coordinator owns integration, shared language/timing contracts, Git/index,
live QA, qualification and activation. Three isolated, explicitly configured
executor chats use Relay Deliver with reporting registered before source writes:

| Assignment | Actual chat / checkout | Requested model / effort | Write boundary |
| --- | --- | --- | --- |
| Chinese UI and manual defaults | `01a184ed-83ee-72d0-80ec-00ee7216a10f`, worktree `adaa/plotloom` | Sol / Medium | `frontend/**` |
| Production brief and truthful adaptation authority | `01a184ee-5afd-75f3-a9ff-9d3683569d27`, worktree `9d86/plotloom` | Sol / High | D backend contracts/lifecycle and tests |
| Owned stage languages/descriptions/timing | `01a184ef-94b5-7653-a030-b193c1665e94`, worktree `448f/plotloom` | Sol / Medium | isolated owned fork only |
| Complete candidate language review | `01a18501-c083-77c0-9d27-d16a90e65c6b`, worktree `f4b3/plotloom` | Sol / High | narrow native checking/adoption/correction owners and tests |

Native read-only attended support used requested Sol/Medium for upstream mapping
and Luna/Max for runtime/speech preflight. Actual returned findings are inspected;
effective host model settings are not independently verified. No parallel worker
owns Git/index or live dispatch. Isolated fork baseline is exact `4f9b2128` with
its own submodule Git directory, initialized from the retained local source.

Smallest real outcome remains two new original projects, one per locale, with
one shared opening/choice/two endings, native Sol/Medium Outline/report/install
and reopen before broad qualification. Coordinator owns settlement and eventual
retention/cleanup. Media uses exact new grants after text evidence; existing
grants and UNKNOWN remain untouched. Local speech-method preflight found macOS
English/Chinese voices and ffmpeg, but no installed speech-recognition package;
short local synthetic calibration is in progress and cannot prove H3 speech.

Consequential shape choice: authored F5 `cut.composition` is separate from
English derived `cut.frame`; Art lighting/state items gain authored `description`.
Existing Cast appearance and Art summary remain their creative owners. The
language policy freezes content/report locale and timing identity in existing
request artifacts. D uses distinct native draft/check invocations and a complete
read-only production brief, with separate generation authorization. ADR 0224
records ownership before implementation. Tests and real outcomes will be recorded
in the existing verification area; no completion/activation claim is made here.

The [implementation evidence](../verification/2026-10-28-project-language-consistency.md)
now owns actual preflight/check results and retained failures. Fork follow-up is
integrated at exact local `f3beafdc3561949a25d61e5c5c4fe38d516d4521`; parent `main`
gitlink checkpoint is `f36ebd3c0d58aaf259057dede12cedf1788f5f78`. The fork worker's
actual final reports nine selftest suites/1,426 passes; exact copied bytes and
coordinator targeted checks were inspected. No fork/main publication or CI ran.
The full implementation remains unqualified and the installed checkout untouched.

## Approved execution-policy simplification — 2026-10-28

The owner explicitly approved removing dedicated forensic/no-dispatch recovery and
adopting configurable automatic retries, default one retry after the initial attempt.
ADR 0225 owns the current contract. The unactivated recovery expansion is withdrawn;
its focused/review evidence remains historical, not an activation promise.

Use distinct existing job/attempt identities and retained current-attempt lineage.
Confirm worker/CLI/validator ownership is stopped before retrying or releasing local
capacity. Remote UNKNOWN and possible costs remain truthful but do not retain shared
execution slots after positive local stop. Preserve original finite generation
permissions/budgets; cancellation stays cancelled, nonretryable authorization or
configuration errors stop, and exhaustion fails the affected job with an actionable
manual retry. Independent work continues. Fix benign clock.sleep parsing at its
normal owner rather than treating the reproducible parser defect as a retry strategy.

The existing Sol/High worker `01a18518-a761-7db1-a5c7-daf04dc3d484`, worktree `8f80`,
now owns the bounded retry/local-capacity/root-cause implementation against a seeded
integrated A/D source. Coordinator owns docs, integration, Git, qualification and
live application; frontend and offline-fixture workers retain separate ownership.
Do not add a generic retry engine or deployment framework. Preserve every normal home (16 at the latest read-only inventory) and current H5 exports. Release only positively stopped LOCAL occupancy of the
two old holds; never automatically retry/resume the old H5 run or resolve its remote
outcomes without facts.

Sequence: complete coherent A/D/UI/retry freeze; real native bilingual Outline and
all-eight installation/readback; focused checks, one stable full candidate gate,
exact-wheel checks and independent review; supported activation and exact old local
slot release; sequential real images/H3 and four route plays; installed language/
playback/preservation readback and closeout. Software qualification, activation,
slot application, media evidence and final acceptance stay distinct. No routine
owner approval is required within this now-approved assignment. No push or CI.

### Native checkpoint reassessment

At local `708a56b8`, actual Chinese Outline delivery exposed incomplete classifier
coverage of upstream-permitted extension fields. Conservative v2 review at
`f387b87d` then exposed copied machine enums/identities being treated as authored
prose, and a real spawn_intent ACK being projected as UNKNOWN. Two unsuccessful
Outline checkpoints triggered method reassessment. ADRs 0224/0225 now bind optional
machine echoes to exact original sources, preserve semantic checking of authored
prose, and separate authenticated ACK from claim with safe pending reconciliation.
All retained native attempts completed, no candidate adopted, no images/H3 sent.
Use the final reviewed current-contract repair for the next original QA fixture;
retain failed frozen evidence and do not substitute new policies into old runs.
The verification record owns exact jobs, results, source revisions and causal tests.


### Cast and preservation reassessment — 2026-10-29

Real bilingual Outline and Branches adoption reached 2/8 in each latest original
QA fixture at `4bda2275`. Cast exposed disagreement between primary receiving and
semantic ownership of frozen machine markers/metadata. After preserving failures
and proving exact native processes absent, the existing Sol/High checking worker
was reseeded from the coordinator candidate for one request-aware ownership repair
and retained-proof corrections. Coordinator remains the only integration/live owner.
The verification record retains the actual standalone canonical-span pass, Cast
failures and three read-only installed-data regressions. Finish the smallest Cast
proof before regenerating the original pair through all eight stages; no frozen
old run is rewritten or resumed under changed source. Preserve all 16 normal homes,
including valued 苏棠 and the two preexisting incomplete homes. All remaining
qualification, activation, media, playback and cleanup criteria remain unchanged.


### Provider-literal reassessment — 2026-10-29

At local `0fd56878`, a fresh English run passed and adopted Outline, Branches and
Cast with the repaired exact metadata owner. Art then exposed an English-provider
gate that rejects the author's required visible 安. The single correction removed
that character from all provider fields and passed language checking, but was
paused before adoption because this is not source fidelity. Both active runs are
now paused, all 12 exact native attempts have no worker/CLI process group or
validator, and the isolated runtime is stopped. Failed and corrected evidence
remains unchanged; normal runtime/data, images and H3 remain untouched.

ADR 0224 records the bounded provider-literal decision before implementation. The
same Sol/High worker owns parent code and the isolated owned Cast/Art/F5 fork for
exact source/span roles, English residual gates, complete existing native semantic
checking including omission, render/receiver parity and Art exact style metadata.
Coordinator owns docs, integration, independent review, local commits and live QA.
No new provider, translation engine, stage, checker framework or approval flow is
in scope. Next smallest real proof is the identical English fixture through Art
creation/check/adoption, preserving exact lettering in submitted prompt bytes;
then finish both all-eight installations and the remaining approved sequence.


The bounded literal/discovery, retained-proof and selected-playback/choice repairs
now have independent review closure. Production source and owned fork are frozen;
the tests-only handoff-fixture update is integrated with verified hashes. Quick,
deterministic asset checks and the affected fixture evidence passed. Commit the complete candidate before the new English-through-Art
journey and keep HEAD stable through native stages, since Bridge freezes it. The
verification record owns exact patches, checks and limits; no activation or media
completion is implied.


At candidate `82a54bdb`, the fresh English Outline and its one automatic retry
failed on a missing sandbox read permission for the new transitive literal helper.
After two failures, generation is paused and all exact native owners are absent.
The next smallest action is a no-provider sandbox dependency proof and bounded
resource repair, then the English-through-Art journey. Retained failed attempts
remain original; no activation, image/H3 or expanded generation campaign occurred.


The exact resource repair passed independent review, six focused cases and a
coordinator actual macOS sandbox positive/negative import probe with networking
disabled. Resume the product path after its local commit; no more supporting
framework or broad qualification is needed before the next native attempt.


At `67f028fb`, English Outline primary validation/render completed. Both checking
attempts then failed on exact owned helper reads in the policy-hash binder. The
run is paused and all native owners are absent. Audit and prove the full checker
validate/render dependency closure under the real sandbox before another drafting
call; keep this causal repair bounded to resources and focused tests. The created
Chinese original fixture has no run and can freeze the repaired envelope later.


The complete checker validate/render path now passes on exact temporary copies
of genuine checker output inside the production macOS sandbox, with networking
disabled and original failed evidence unchanged. The conditional three-file read
closure has independent review and21 focused passes. Commit the repair and return
to the original English-through-Art proof; retain the unlaunched Chinese fixture
for subsequent all-eight qualification.


At84cbd706 the actual primary and checker validate/render paths both completed.
The checker returned genuine uncertainty solely on12 opaque IDs in an unsupported
routePlan shape encouraged by the parent prompt. An independent source diagnosis
found no product consumer beyond partial echo classification; Branches already
owns graph output. ADR0224 now records the smallest repair before implementation:
retire routePlan from new Outline candidates, align prompt/versioned constraints/
typed primary receiving, retain existing authored explanations and exact topology
guidance, and preserve old uncertain proof without reclassification. No blanket
classifier exemption or topology framework is authorized. Both exact native owners
are absent and the runtime is stopped. Coordinator owns docs/integration; the same
worker receives the bounded production repair after freezing the separate reader
fixture delta. The next product proof remains the original English through Art.


At54105858 English Outline and Branches passed and adopted (2/8), with an inspected
English Outline report inside Chinese chrome and source 安 retained. Cast primary
delivered, but both checker attempts failed the existing authored-only coverage
exception rule by placing one literal exception on image.sheet/provider_technical.
Their literalReview already owns those facts. After two failures the run is paused
and every native owner is absent. Align the frozen response schema and prompt
with that existing restriction before another native run; do not normalize old
results or weaken binding. ADR0224 records the channel owner before implementation.

### Current native text checkpoint at 389bf861

Both original fixtures have completed all eight native stages and persisted current
canon: EN e1894d73-7c75-4481-9f4a-84ab9f0a4c0b and ZH
2458559c-b6cf-4d98-9921-bd169e2b6769. Root inspected both reopened Script/Storyboard
readers, route selections and retained literals, then restarted the isolated runtime
and verified exact installation/head hashes unchanged and both runs paused. All35
native attempts are terminal: EN has8primary/8passed checks plus1failed Script
checker and its bounded successful replacement; ZH has9primary/9completed checks
including1genuine Cast reject followed by a correction confined to source notes.
No images/H3 requests occurred. The original failed/rejected evidence stays original.

Current-contract browser fixture closure now has all14 affected reader cases
covered by11unchanged passes and targeted2+1passes, with real explicit current-snapshot
language checking before UI confirmation. Test-only synthetic proof is byte-bound;
its request-scoped profile closes host dispatch and preserves unrelated paths.
The first full local gate against389bf861/fork35fac266 plus the retained
test-only delta fingerprint22b079c0fa4186fa82fefdb88459e16f15ec400b611b9861b3a9dc867a24f64b
failed after2093.664s. Frontend1675 and both type checks passed; Python workers
reported170failed/2159passed/58errors and153failed/2162passed/73errors. These are
retained failures, not qualification. Close shared current-contract fixture
prerequisites and the demonstrated owning-Git verifier defect with focused checks
before qualifying the stable repaired candidate. The frozen73-file backend
fixture delta and three bounded production repairs now have independent review
closure and exact root integration hashes. A further native retry read-projection
defect must expose pending local-stop/stopped states truthfully; its bounded
ADR0225 follow-up preserves all execution guards and the original attempt.

Before changing the native source identity, cancel the two fully adopted paused
runs under389bf861 and require their supported continuation contexts to be eligible.
Read-only previews and independent source review found11reusable operations in
each original home; cancellation was their sole blocker. Preserve all original
receipts, the rejected Cast ancestor and failed English checker. After the stable
source checkpoint, full qualification, exact shipping wheel, normal activation
and exact old LOCAL-slot release, use supported Continue in those same homes with
fresh exact CAS identities, current Sol/Medium execution and explicit prospective
null aggregate budgets. It must inherit the adopted text rather than repeat it.
Freeze that successor source/fork/HEAD through native image bundle completion.
Use the existing controller process lease and supported step/control operations
to admit the first required reference only, then pause new admission while that
exact attempt finishes. Inspect the actual image and persisted delivery before
advancing the remaining inventory; keep any UNKNOWN reservation intact. This
small batch boundary does not change the prospective aggregate budget. Then
complete sequential real images/H3, four route plays, export,
preservation/recovery and closeout. CI/push are not requested; hosted CI is not a
release blocker.

### Candidate C failures and derived-presentation repair — 2026-10-29

Candidate C is local main `8193c3ff1486f0ff75d263903f07da4e33865052`, fork
`35fac2661d70c6c017f1c4a61360d0e74c732497`. Its root-owned full local gate
finished failed after2447.696s: frontend1675 and both type checks passed; Python
reported78failed/4728passed with no setup errors. Bundle parity, browser and exact
wheel qualification were not reached. The original full failures remain retained.
The same sole source worker has a separately frozen34-file fixture follow-up;
67of the78 original cases pass focused selections, while11 retain demonstrated
production blockers. Independent review owns that stable test patch.

The authorized causal repairs are: structurally retain exact raw/bridge deliveries
before independent language checking, including paused receipt-only continuation;
include the actual transitive local rule imports in style-cache identities without
changing derived contract output; and persist exact typed known-unadmitted capacity
evidence per attempt, consuming it before another admission RPC. Global run blockers
cannot authorize redispatch, and UNKNOWN/lost acknowledgements remain protected.
ADR0224/0225/0154 were amended before source edits.

The small provider-brief preview also exposed a real ownership error: presentation
preparation binds English provider `cut.frame` instead of authored
`cut.composition`. Correct that source, its exact coordinates and primary prompt;
display version2 must render composition and accepted Cast/reference-role prose
without hiding appearance or treating primary/complementary as camera angles.
Unknown fields still block. A read-only normal-data inventory found no new-contract
production briefs in52job snapshots or44targets across15legacy-v1 batches, so this
unactivated display change requires no persisted normal-data rewrite.

The preceding promise to inherit all11operations is superseded only for the
demonstrated complete frame-bound presentation in these two disposable homes.
Use one shared Continue preview/write predicate: require the unchanged accepted
raw F5, exact complete source inventory/current installation and zero dependent
media/reference/frame/bundle/handoff authority. The new child inherits7source/raw
operations and rebuilds exactly bridge.prepare, bridge-intent,
bridge-presentation and installation. Preserve every parent checkpoint/proof and
all original raw content. Already composition-bound proposals keep ordinary11
inheritance; mixed/malformed/replaced bindings refuse. No reset or generic replay
layer is authorized.

After focused contracts and independent stable-source review, commit the coherent
repair locally before native execution. First continue the original English home
under current Sol/Medium with prospective null aggregate budgets, run only the
existing text prefix, and pause after fresh installation. Prove new composition
coordinates, faithful canonical content, unchanged raw6/source hashes, unchanged
parent proofs and fresh-runtime readback; then repeat Chinese. This smallest real
repair journey precedes another broad qualification. It admits no images. Freeze
the resulting source/fork through the later image bundle. Final full local checks,
exact shipping wheel, normal activation, two exact old LOCAL-slot releases, real
images/H3/route/export evidence and final preservation/cleanup remain required.

Disposable recovery checks have established old-format save/restore/reopen with
the old installed wheel and current-format restore with the candidate-C wheel plus
the supported source runtime. The old wheel correctly refuses new retry authority;
do not erase that field or claim backward execution support. The current-format
save causes only expected manual-takeover operational metadata in the restored
cancelled run; frozen authorities/canon/receipts remain exact. Standalone wheel
Cast reading lacks source rule files and is not qualified. Keep the original one
qualified recovery unchanged until its qualified replacement is proven.

Qualification sequencing follows the original small-real-media-before-final-gate
order above. The two exact native QA grants require observed image bundle hashes,
so their source entries cannot be completed before image generation. After the
corrected native text checkpoint, freeze its source through the two original
isolated image bundles, then record the two exact new grants and finish the small
H3/audio/routes/export journey under focused safety checks. Qualify the resulting
stable final source/wheel once and activate normal8841 only after that gate and
preservation checks pass. The earlier checkpoint's normal-activation-before-image
ordering is superseded; the isolated private ledger has zero slots and does not
require touching normal's two old holds to prove its first image. Apply those exact
normal LOCAL releases as part of qualified activation, preserving their UNKNOWN
evidence. This avoids qualifying an intermediate candidate before its required
bundle-bound authority exists. It changes no scope, budget, provider or acceptance
requirement; source repairs invalidate only affected evidence as documented.

### D4 real checker failure and compatible fixture — 2026-10-29

Root committed the reviewed77-file checkpoint asd4cb63f8. Quick passed13.343s;
the exact source-identity case passed3.99s. The original English home's supported
Continue inherited exact7raw operations and produced a new native intent candidate.
Its independent checker and one configured retry both failed trusted validation:
they labeled lettering not_relevant/not_applicable while attaching nonempty
incidental occurrences. This is a contradictory metadata combination, not missing
author text or a semantic rejection. Both failed attempts remain failed. After
two failures, root stopped and diagnosed the exact frozen packages offline.

The prospective schema/instruction repair expresses the existing binder relation;
it does not weaken validation, rewrite outputs or increase retry allowance.
Independent review closed its3-file delta, with33discovery and55affected contract
cases passing. An unrelated exploratory system-python3/Xcode error is retained;
it did not cause the checked-Python binder failure and no infrastructure repair is
needed for this journey.

The successful but unadopted intent primary cannot be silently upgraded to a new
source pin. Independent lifecycle review found no supported reject/withdraw route
that would make it eligible for automatic Continue. Root cancelled only this new
English child underD4, preserving the completed primary, two failed checks, raw
work, original parent and canonical heads. Do not add discard/replay machinery or
fake a primary failure to rescue this disposable fixture. Use the still-compatible
original Chinese parent's7-operation Continue first under the repaired committed
source. Then create one replacement ORIGINAL disposable English project from the
same approved Brief through ordinary creation and regenerate its8native stages;
copy no canon, database rows, grants or prior native proof. Record its exact ID
before dispatch and use it with the Chinese home for the two eventual exact media
QA grants. The old English home remains retained failure/preservation evidence.
This fixture replacement changes no product outcome, story source, provider,
budget default or acceptance requirement. Both real corrected text installations
remain prerequisites for images; all final qualification/activation work stays open.
