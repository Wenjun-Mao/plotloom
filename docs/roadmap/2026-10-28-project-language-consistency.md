# Project language consistency: Chinese UI, Chinese and English content

Status: reviewed plan, ready for execution approval. Both independent planning
reviews are complete; implementation and activation have not started.
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

Existing stories and media remain their authored originals. This release does not
translate existing approved prose in place, rewrite retained reports, regenerate
old media, or add a bulk story-translation feature. Existing projects benefit from
localized application labels; new/revised creative work uses the new contract.
Proper names, deliberate foreign quotations, source excerpts and literal screen
text can remain in their authored language. This is language consistency, not a
new dramatic-quality threshold or a claim of improved storytelling.

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
service. It maps content locale to report locale (`zh`/`en`), canonical dialogue
timing profile and provider language label. Keep UI locale separate. New-work
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

For new requests, the creator reviews complete creative intent in the project
language and explicitly authorizes generation. An assistant drafts English H3
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
   add the owning policy. Implement Brief/source → Outline → report/persisted
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
executable pin check. ADR 0147 currently calls for a published pin: propose a
narrow amendment allowing local-only qualification/activation from an exact
retained Git pin, while requiring publication or explicit Git transfer before
another host can depend on it. Keep license/fork notices and reproducible resource
hashes. Do not substitute a new pin into old packages. Update stale pin instructions
in the handoff guide as part of this scope. Normal remote publication remains a
separate user request, and a push that triggers CI needs new explicit CI authority.

The present request authorizes planning and its document/review work. A later
instruction to implement this plan should cover source and owned-fork changes,
local commits, focused/full qualification, the two named disposable QA projects,
their exact prospective grants, native text/image and configured H3 work,
necessary local-only QA transcription dependencies if needed, preservation-checked
core/bridge reload/activation, single recovery refresh and scoped scratch cleanup.
These effects should be named in the final handoff so one informed execution
approval covers them. Existing task/model approvals need no renewal. No GitHub CI,
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
Assumptions: the owned fork remains locally editable, existing native/H3 services
are healthy, a local speech-inspection path is usable, and supported English audio
requires no provider replacement. Real timings from the first bilingual slice
should refine this forecast. Full English UI and old-story conversion are excluded.

Review direction after the first bilingual text installation, earlier if source
ownership/timing or translation fidelity makes the proposed workflow infeasible;
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
