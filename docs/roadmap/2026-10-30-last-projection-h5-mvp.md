# The Last Projection: standalone H5 MVP and optional media review

## Current status

Updated: 2026-10-31. **The authorized original standalone H5 MVP is complete.**
The original 15-shot game has all three routes and endings, exact source text,
truthful unreviewed selections, normal-install export and functional recovery.
Compulsory audiovisual quality review is removed globally under ADR 0226;
technical integrity, source fidelity and dispatch authority remain required.
Media quality is unreviewed. M2 edit/regenerate/Apply and creative polish remain
separate work. No hosted CI, push or public hosting was requested or performed.

**Player sound follow-up, 2026-10-31.** Wenjun reported that sound reverted to
mute while playing the delivered game. Root owns this player-only repair,
browser verification and cleanup of its disposable export project.

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| Sound follows the player's choice | Open the original game, change sound with either control, advance a clip and reopen. Check volume, mute and the game button together. | No, reuse the 15 original clips | Passed on local files in WebKit 26.5 and Chromium 151. Sound on and 35% volume survived native clip ends, a choice, and reload/Continue. Intentional mute and storage-denied playback also passed. |
| Corrected delivery | Play the fixed standalone export and compare every archive member with the original | No | Delivered. Only `player.js` changed. The unpacked game retains its path and progress key. The new sibling ZIP is `the-last-projection-sound-fix.zip`, SHA-256 `331eea9c72eef7c7d850d3ee28cdf84dab1a2f0ec0b67058071aed0cfe82d39d`. |

The previous game reproduced the failure in WebKit: unmuting through the
native control at 35% volume yielded a muted next clip at 100%. Sound and
volume now live on one persistent video element. The corrected delivery
restored the same clip and time after reload and allowed Play to recover from
a simulated autoplay refusal. The focused tests, quick tier (1,715 frontend
cases and both type checks), deterministic assets and independent source review
passed. The full local gate on `3dfe8490` passed 5,084 Python and 366 browser
cases, deterministic assets and installed-wheel smoke. Retained evidence is
in `.local/player-sound/`.

**In-frame choices follow-up.** Both decisions now hold the final image of
the preceding clip and show clickable options over it. The choice opens as
the clip ends. Back and Continue use the actual visited route to find its last
frame. The second choice's two labels stay inside the picture on desktop and
at 390 px. The updated unpacked game is at the original address and the
sibling `the-last-projection-choices.zip` includes both player fixes.

| Claim | Required evidence | Fresh media | Status |
|---|---|---|---|
| Both decisions appear in frame | Natural clip ends, clickable buttons within the picture, resume and back on the actual path | No | Passed in WebKit and Chromium using the real game |
| Existing game and save still work | Same story and progress identity, sound on in the next branch, archive member comparison | No | Passed. Only `player.js` and `player.css` differ from the sound-fixed ZIP. |

The confirmed ZIP SHA-256 is
`14839aa6e9ea5c548fc0134c1721cf65c67fe3ff5650c191502d2849f76711b0`.
The diff from `3dfe8490` changes standalone presentation, its focused browser
DOM regression, test ownership and documentation. The player still consumes
the same exported graph, media, stored progress and audio settings. APIs,
source-to-request bindings, project storage, admission, provider behavior,
dependencies, build procedure and wheel resource paths are unchanged. Root
owns the disposable export and browser checks. Focused player tests (11),
the unfiltered frontend suite (1,716), both type checks, two identical builds,
the real API export regression and an exact wheel-to-delivery asset comparison
passed. Both decision layouts were inspected. Independent review found no
material issue. This is scoped frontend qualification on top of the completed
sound gate. Evidence is in `.local/player-choices/`.

The [final receipt](../verification/2026-10-31-last-projection-functional-closeout.md)
owns artifact paths, exact revisions, executed evidence, production learning and
limitations. Source/runtime checkpoint: `3e23eec5` (runtime code `e0f00881`, plus
QA test-fixture repairs). The following closeout commit changes documentation
only. Normal installation is activated on that checkpoint; all 17 previous homes
are preserved, with the completed story restored as the eighteenth through the
supported operation. Its HTTP export is byte-identical to the delivered ZIP.
The single qualified recovery handle is refreshed and proven. Disposable copied
projects/environments and owned test browsers/server are retired; the original
valued production home, snapshots and evidence are retained.

Final local qualification is **composite**, not a successful full invocation:
the `e0f00881` full run passed 5,077 Python cases and failed two obsolete QA
fixture expectations. The test-only `3e23eec5` repair passed seven focused cases,
including independent QA scope guards. All authoritative downstream full steps
then passed, including 366 unfiltered browser cases, deterministic assets/parity,
wheel build and installed smoke. Earlier failed/interrupted runs remain failed.
The exact wheel also restores all 15 clips, exports, snapshots, closes and
reopens without source-checkout reads or provider calls.

Journey: original N00 → C01 → E01, and N00 → C01 → N10 → C02 → E02/E03.
Runtime: activated normal Plotloom plus an exported static game outside the
checkout. Functional HTTP tests used Chromium/WebKit with Plotloom denied;
ordinary Safari file opening covered the complete short route. Desktop/390px
layout inspection passed. The original H3 work used 15 jobs / 161 requested
seconds under its prospective normal-production authority, without quality
rerolls or new provider experiments. Coordinator owns cleanup. No next action
is required for this milestone; the downloadable game is ready for owner use.

Superseded next-step descriptions in earlier receipts are historical. The
approved scope and implementation method below remain the retained plan.

## Acceptance

| Claim | Required evidence | Fresh media | Status / evidence |
|---|---|---|---|
| Optional media review throughout Plotloom | Normal/QA selection, adoption, generation, trim, playback, reopen/export without fabricated watch/listen/quality attestations; technical/source guards retained | No extra generation for policy | Complete: affected contracts, full frontend/types, normal original production, installed recovery and unfiltered browser evidence |
| Complete standalone game | Outside-checkout ZIP; all routes/endings, restart/last-choice, HTTP Continue; packaged-only network with Plotloom unavailable | Original production media | Complete: Chromium and WebKit all 15 clips/all three routes; Safari local-file complete E01 route; storage-denied E01/reload |
| Lightly styled usable MVP | Legible desktop and 390px title, dialogue, choices, controls and endings; no essential clipping | No quality experiment | Complete: pixel inspection, width/scroll-width and control-size readbacks; no real-phone claim |
| Faithful story and final requests | Seven source roles/six edges; exact 19 dialogue lines, four labels, three endings; actual image arguments/H3 receipts and settings compared | Production receipts | Complete: native F1–F8 checks, literal ImageGen calls/ref hashes, exact gateway prompts/input digests and private source-to-build map; erroneous image request retained unselected |
| Technical validity and provenance | Selected media decode/hash/window/currentness; unsafe/tampered/unauthorized inputs refuse; portable reopening retains facts | No extra generation | Complete: all 15 decoded in each HTTP engine, exact selected bytes, focused authority regressions and installed 15-clip restore/save/close/reopen |
| Original story production and future update seam | Actual project selects/exports original media; private slot/source/candidate bindings retained; fixture slot replacement preserves graph/UI | Original missing assets only | Complete: 15 selected real H3 clips, private immutable build receipt and source-to-build map; M2 Apply remains excluded |
| Local qualification, activation and recovery | All applicable local gates, exact installed export, preservation and single recovery proof | No extra generation | Complete through composite closure on `3e23eec5`; normal export exact; prior 17 homes and UNKNOWN facts unchanged; source extraction/native preparation and exact-wheel recovery passed |
| Audiovisual creative quality | Record only judgments actually made | No | Unreviewed, explicitly outside this milestone |

## Outcome and settled boundaries

Deliver **《放映室最后一夜》 / The Last Projection** as a self-contained static
browser game, produced through Plotloom. It is a viable prototype with simple
consistent styling, not a polished release. The [benchmark decision](2026-10-30-first-real-game-benchmarks.md)
and story remain authoritative; this plan owns implementation and completion.
Use the first story draft without another writing competition. Chinese story/UI
is the implementation default, with the existing English synopsis for discussion.

- Two characters, one projection room, N00/C01/N10/C02/E01/E02/E03, six edges,
  three endings. Choice nodes may be represented differently internally only
  with an explicit lossless mapping. No hidden state or additional branches.
- First real slice: **N00 → C01 → E01 → Restart**. Then both C02 endings.
  Five media-bearing roles are an inventory, not five jobs: dialogue and current
  provider clip limits determine the necessary shots. Do not truncate dialogue
  or pad the story to a target runtime. The draft's 1–2 minutes is an estimate.
- Title/start, pause, mute, readable authored dialogue/subtitles, untimed choices,
  distinct ending cards, restart, return to last choice and local Continue.
  Use restrained dark framing, a warm accent and legible panels. No codex,
  chapter map, accounts, analytics, online saves or custom graphics requirement.
- The game bundles HTML/CSS/JavaScript, story/presentation data and all media.
  No Plotloom process, provider, database, credentials, CDN or remote font is
  needed by the player. A preview inside Plotloom is insufficient.
- Later edit/regenerate/review/Apply is **M2**, not part of this implementation.
  Preserve its asset binding seam now. Optional future review must not turn
  back into a compulsory inspection gate.

## 1. Remove compulsory inspection at the contract owners

Make **media quality review optional by the current product contract globally**.
Do not introduce project allowlists, opt-out expiry, per-run waivers or a second
mandatory "functional review" form. Removing the compulsory condition is the
durable default across new projects, existing projects, restarts and exports;
an environment switch that must be kept set is insufficient. No new settings
framework is needed. Optional viewing, listening, notes and explicit judgments
may remain available, but their absence cannot prevent normal production/use.

Before source changes, add a superseding ADR separating these responsibilities:

| Responsibility | Owner / invariant |
|---|---|
| Story, intended content, choice text and source-to-request fidelity | Authoritative source and explicit adoption; no silent rewrite by the provider adapter |
| Candidate selection / use | Actual operator chooses exact source-bound bytes and trim; this is not a statement that someone watched, heard or approved quality |
| Technical eligibility | Trusted code validates provenance, decoding, dimensions, duration/windows, revision/currentness and dispatch authority |
| Optional quality judgments | Only record judgments actually made, with truthful actor and scope; not prerequisites for generation, currentness, adoption, playback or export |

The inspected owners below are the initial change map. Trace callers and tests
to find equivalent conditions; do not blindly delete every symbol named review.

| Surface | Current owners | Planned change |
|---|---|---|
| Video selection and trim | `video_batch_contracts.py`, `video_batch_review.py`, `delegated_qa_contracts.py`, `persistence/project/media_video_segments.py`; frontend `features/video-batch/VideoBatchReview.tsx` | Replace mandatory AV observations/true attestations with exact technical selection facts and truthful actor attribution; optional notes remain separate |
| Keyframe use | `persistence/project/media_keyframes.py`, `persistence/project/media_admission.py` | Remove compatibility prose/bulk-review eligibility; retain asset/shot/intent/source/selection bindings |
| Same-person quality gate | `persistence/project/media_video_preparation.py`, `persistence/project/media_video_currentness.py`, `persistence/project/media_keyframes.py` | Remove subjective identity-review prerequisite for H3, still preview and currentness; retain reference lineage/currentness and optional same-person judgments |
| Material adoption/continuation | `autopilot_handoff_contracts.py`, `persistence/project/autopilot_handoff.py`, `project_storage/handoff_validation.py`; frontend `features/autopilot/MaterialReview.tsx`, `contracts.ts`, `AutopilotWorkspace.tsx`, `ContinuationAction.tsx` | Continue with an explicitly selected complete technical inventory; no compulsory human endorsement, observation/comparison prose or fake creator approval |
| Persistence/reopen/export | `project_storage/video_batch_validation.py`, `handoff_validation.py`, `autopilot_validation.py`, selection/segment readers | Current readers accept truthful unreviewed selections; preserve current asset usability and historical facts without reimposing retired gates |
| Task guidance and documentation | `autopilot_brief_style.py`, `autopilot_geometry_preparation.py`, `codex_exec_prompts.py`, image specialist instructions, creator/development docs | Remove product-owned compulsory inspection instructions; align UI labels, schemas, forms and generated briefs with optional review |

Backend paths above are under `src/plotloom/`; frontend paths are under
`frontend/src/`. Character
reference/art proposal selections already have useful technical provenance
contracts; remove compulsory endorsements layered on them, not their bindings.
Source/presentation acceptance and final-request semantics are not generated-
media inspection. Keep those owners intact unless a demonstrated integration
change requires a narrow, documented update.

Use a new current selection/handoff schema instead of reinterpreting old
`whole-pack-video-native-audio.v1` receipts. Preserve existing assets, selections,
observations and rejections exactly as facts. Choose the smallest one-time data
transition/current read projection that preserves valued project state; do not
maintain obsolete executable review workflows or fabricate missing evidence.
A recorded rejection does not silently become a quality pass; deliberate
reselection is permitted without a new compulsory review. Inspect any mixed
"review + authorization" field before removing it: retain authority separately.
Retire obsolete positive/negative tests only where their contract is retired.
Reconcile current guidance in ADRs 0030/0143/0191/0193/0198 through the new ADR;
historical results and frozen finite grants remain unchanged.

No false human identity, blanket `True` flags, unnamed reviewer or recycled QA
grant is allowed. Use existing agent adoption paths where applicable; if the
normal story workflow has only a human-attributed command, add the smallest
truthful operator attribution needed for this authorized workflow. This real
story is not one of the old disposable QA projects.

## 2. Build a portable exporter and small player

The current `frontend/src/play/PlayView.tsx`, `branching-video-preview.tsx` and
`useBridgeChoiceRead.ts` depend on project APIs and service media URLs. Reuse
their graph/selection rules where cohesive; do not package the workbench and
pretend it is independent. A separate small player entry uses the existing
frontend dependencies/build system with a relative, file-friendly bundle.
Keep generated workbench assets fresh and make both output targets deterministic
without one cleaning the other's directory.

Add cohesive export contract/projection/packaging owners, using the selected
media and playback storage owners in `persistence/schema/project_media.py`,
`project_storage/project_video.py` and
`api/project_folder_video.py`. Expose a normal project Export action backed by
the product API; the user should not need an ad hoc packaging script.

- Snapshot a consistent project/production/selection revision. Resolve selected
  original or derivative bytes, validate hashes and frame windows, and refuse
  stale or concurrent changes rather than mixing revisions in one package.
- Freeze validated story graph, runtime choices, authored dialogue/endcards and
  asset slots into a versioned player manifest. Obtain wording from project-owned
  source/presentation data. If intro/endcard/dialogue timing lacks a suitable
  field, add that narrow project-owned presentation contract; never hardcode a
  second story in the player or manually copy it around export validation.
- Package only public player data, HTML/CSS/JS and relative media. Escape authored
  text as data; prevent unsafe paths and external URL dependencies. Do not expose
  grants, private filesystem paths, prompts with private metadata or credentials.
- Retain a separate build-side map: stable logical game/node/edge/slot identity
  → source/canon/production identity → shot → selected job/segment/revision →
  hash and playback window. Installed shot IDs include cut order; they are not
  assumed stable across structural edits. Separate story revision from asset
  version so a later asset-only update need not discard node-based progress.
- Export atomically to a new download/artifact, preserving source files. Missing
  or broken selected bytes produce an actionable error, not a successful ZIP.
  The initial M2 seam check replaces a retained fixture slot and re-exports,
  proving story/UI separation; it does not build the future Apply interface.

Use bundled classic JavaScript/embedded story data if needed for direct file
opening; avoid runtime JSON fetch/module/CORS assumptions on `file:`. Primary
qualified launch is a generic static HTTP origin in desktop Chromium and WebKit;
also exercise direct `index.html` opening in an available Mac browser and report
the exact browser/result. This does not require stopping the user's normal
Plotloom service: run with its addresses unavailable in an isolated test context.

Start media after a player gesture and expose a usable Play fallback after a
blocked play promise ([browser autoplay behavior](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay)).
Required persistent Continue is on the static HTTP origin. Guard storage access;
if denied/unavailable, keep the game playable in-session and explain that
progress cannot be saved. `file:` storage behavior is browser-dependent, so do
not promise universal file-mode persistent saves ([localStorage behavior](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)).
Invalidate or safely reset incompatible/corrupt saves without preventing Start.
Retry last choice from its saved branch point and discard the abandoned suffix.

## 3. Prove the small journey, then produce the original game

1. **Preflight and contract slice.** Inspect current dependency/source identity,
   interpreter, service/catalog readiness and existing tests. Add the ADR and
   remove compulsory inspection across owning contracts. Test a normal non-QA
   fixture with valid unreviewed retained media through the previously blocked
   paths. Verify absent inspection fields do not become implied quality passes.
2. **Provider-free standalone slice.** Through real project UI/API/persistence,
   export retained media for one opening, two choices and an ending. Unzip on an
   isolated origin; play, choose, end, replay, reload and reopen the project.
   Inspect game UI pixels and network requests. This proves software behavior;
   it does not prove original-story generation or media quality.
3. **Direction checkpoint.** Review whether global optionality and export work
   without manual receipt editing or a packaging rescue. Fix demonstrated
   product blockers. Continue automatically within scope; this internal review
   is not another owner approval gate.
4. **Create the real Plotloom project.** Import the working story through the
   supported source/outline/section-map/canon flow, then production presentation
   and storyboard. Freeze the explicit node/edge mapping and source wording.
   Resolve dialogue timing/shot expansion before live dispatch. Preserve every
   authored line in player text; native audio is not used as the only carrier
   of required story information. No speech transcription/quality grader is
   required. Record any necessary structural adaptation without inventing story.
5. **Produce the first real slice.** Use Codex ImageGen for needed references/
   keyframes and the owner's H3 gateway for native-audio video. Select technically
   valid returned assets without visual/audio quality inspection. Use a current
   supported landscape profile from the catalogue; exact model/settings become
   part of the frozen production record. Exercise actual final-request capture,
   completion, ingestion and selection for N00/C01/E01, then attempt the normal
   Plotloom player and export. Both current surfaces require every installed
   shot; retain their incomplete-inventory refusals and check the selected
   clips technically. The earlier instruction to play/export this partial route
   is superseded as a plan-method gap. Complete branching playback and standalone
   export follow the remaining seven original shots in step 6.
6. **Complete the story.** Produce only the missing N10/E02/E03 inventory and
   assemble all routes. Authored dialogue, choices and endings remain real UI
   text, not generated lettering. Native audio is retained when technically
   available as required by the selected profile; no new TTS/music pipeline.
   Reuse good technical assets; no rerolls for beauty, acting, voice, identity
   consistency, lip-sync or cinematic quality.
7. **Qualify, activate and deliver.** Review the stable diff, resolve findings,
   run final local qualification, verify the exact installed package and activate
   through existing supported deployment/recovery procedures. Refresh and prove
   the existing single qualified recovery handle as described below. Export the real
   game from that installed runtime and exercise its final archive independently.
   Retain the project/assets/mapping, record limitations, and clean only identified
   temporary test artifacts. Preserve a coherent local `main` checkpoint.

For each expensive production attempt, record here the inventory/acceptance gap,
why retained assets cannot fill it, changed inputs, expected information and
finite stopping condition. For original content, the gap is its absent assets
and actual production integration, not an unmeasured creative quality target.
Unknown dispatch is reconciled through the supported operation; never clear it
or submit duplicates to move forward. After two unsuccessful attempts at the
same criterion, retain evidence and reassess cause/method before another attempt;
this is not an invented two-attempt budget or an automatic permission gate.

## Original production attempts

The first fresh-media acceptance gap is the original story's missing character
reference assets, under the original-production row. Retained unrelated people
cannot satisfy the adopted C01/C02 identities or prove this source's production
integration. Inputs are the newly adopted F2 cast revision 1, live-action style,
exact separate character identities and the frozen reference proposals. Expected
information: whether built-in ImageGen can produce, publish and ingest technically
valid original references through the current native package contract. Stop each
job after its first technically valid result; no visual-quality verdict, beauty
retry or identity-quality pass is requested. Required input viewing does not
establish output quality. C01 was sent once through the normal Plotloom native
queue, delivered, ingested and selected without a quality verdict. Its redundant
staging cleanup initially refused mode 0755; after exact task-directory ownership,
identity and hash checks, that directory alone became private (0700) and the
bounded helper removed the redundant staged file. The initial refusal is retained.
C02 was then sent once through the same serial native queue. These two jobs do not
claim final game assets, H3 integration or creative acceptance.

## Verification, ownership and operational boundaries

One source owner writes and one execution owner runs qualification. Use focused
contract tests while developing; retain meaningful regression coverage for the
new optionality, actor attribution, rejected/stale assets, currentness, revisions,
save behavior and portable export. Read-only reviewers inspect a stable diff and
retained evidence, without automatically repeating expensive checks.

Starting focused owners include video batch review/adoption/recovery, handoff
attribution/source ownership, autopilot/bulk material adoption, same-person
contracts, keyframe acceptance and character-reference selection; frontend owners
include material/autopilot review, reference provenance and same-person
presentation. Adapt retired-contract tests instead of preserving obsolete gates.
Add exporter/player tests to existing module ownership and browser shard manifests.
Offline tests fail on unexpected live submission. Prove technical refusals still
work alongside successful unreviewed paths; test optional observations remain
accurate and distinct from selection. Generated specialist briefs are testable
outputs, not merely documentation to edit by search.

Use `uv run --locked --no-sync python scripts/verify.py focused` with explicit
changed-contract selectors, `quick` for general feedback, and reviewed module
selections where useful. After the early real slice and stable final candidate,
run `uv run --locked --no-sync python scripts/verify.py full`: changes span APIs,
persistence, runtime and package contracts, so frontend-only qualification is
insufficient. One owner records revision/envelope, selected checks and failures.
After a repair, rerun failed/downstream affected checks; reuse unchanged evidence
as the repository policy permits. Verify the installed wheel includes the player
bundle and exports outside the checkout. Do not run full after routine edits.

Final product evidence must come from the delivered game archive with the
Plotloom endpoints denied/unavailable, not from a fixture or development server.
Require all routes, readable full source text, chosen asset hashes, replay, HTTP
resume, storage-denied behavior and no undeclared network request. Functional
browser playback means decoding/progression/control checks, not listening or
judging footage. UI pixel inspection covers layout and controls only. Claim
direct-file and browser coverage exactly as exercised, not all-browser support.

Wenjun explicitly authorized this plan E2E with Relay Direct on 2026-10-30, after
the two independent plan reviews. The authorized run includes ordinary project creation/source adoption,
truthful agent selections, in-scope fixes/reviews, required local tests, supported
local activation, normal recovery and scoped scratch cleanup; do not insert
routine review/selection/restart approval gates. He reaffirmed standing approval
for separate Codex tasks and model/reasoning choices under Relay Direct,
encouraged parallel work and delegated ordinary implementation decisions while
unavailable. Record only material decisions in this plan for the final E2E review;
do not block routine in-scope work waiting for answers. Native selector rules
still apply, and material changes outside this agreed scope remain distinct.
Existing owner authorization
already covers Codex ImageGen and the H3 gateway for development/test generation,
with no invented cumulative cap. Preserve existing frozen grants/provider limits
and native tool confirmations. Other paid providers, material outcome expansion,
public hosting, deleting valued data or changing unresolved remote reservations
are not covered. No credential may enter project state, logs or the public game.
Do not bypass tool-required reference viewing; it is not a media-quality pass.

GitHub CI remains off. No workflow preparation/dispatch, push known to trigger
CI, or substitute automation without Wenjun's new explicit request. Hosted CI
is neither requested nor a release blocker. Leave a local `main` checkpoint and
report publication separately. Refresh the existing single
`.local/current-qualified-recovery/manifest.json` to the final qualified source,
pinned fork and exact wheel, following the [existing closeout](../verification/2026-10-30-language-functional-closeout.md).
Prove extraction/native preparation and exact-wheel snapshot restore, save,
close and reopen using truthful unreviewed selections. Check selected bytes,
prior observations/rejections and UNKNOWN/authority facts remain intact without
dispatch. Replace the previous handle only after this proof. Recovery must not
silently reinstall compulsory inspection or lose the new selection contract.
No new backup/provisioning framework, infrastructure campaign or unrelated refactor.
Review cohesion before substantial edits to files above 400 lines; extract a
new responsibility from an oversized owner only when that improves the boundary.

## Estimate and review points

Forecast: **20–36 active engineering hours**, including global contract cleanup,
export/player work, story assembly, review fixes, final local qualification,
activation and cleanup; approximately **3–8 additional hours of provider/check
waiting**, some overlapping active work. This is roughly 3–6 working days, not
a deadline or budget. Assumptions: existing services remain usable, the compact
story only needs normal shot expansion, and no unrelated infrastructure repair.
Re-estimate after the provider-free slice if the contract transition or packaging
proves materially larger; elapsed estimate alone is not a reason to stop.

Direction review follows the provider-free slice; final independent review follows
the stable complete candidate. Bring review forward for lost project assets,
untruthful attribution, unresolved dispatch, unavoidable service dependency or
an adaptation that changes the story/outcome. Fix ordinary defects within scope;
obtain user direction only for material changes to the agreed result or authority.

## Plan review and production learning

Plan review 1 (outcome/completeness): independent GPT-6.1 Sol / Xhigh found one
bounded gap: recovery could remain pinned to the old compulsory-review contract.
Resolved by requiring refresh and restore/readback proof for the existing single
recovery handle. No other blocking findings.
Plan review 2 (avoidable execution restrictions): a separate GPT-6.1 Sol / Medium
reviewed the corrected plan and found no unnecessary restriction or missing
decision. No outcome/evidence assumption changed, so no first-review recheck is
needed. Neither review is a human sign-off gate. Documentation validation:
diff/whitespace checks and local-link resolution; no software suite, generation,
activation, push or CI was run for this plan.

| Production step | Observed friction | Effect | Smallest useful change | Disposition |
|---|---|---|---|---|
| Planning: media selection | Old contracts required AV attestations and restricted functional-only exceptions to old QA projects | Conflicted with owner instruction and truthful real-story assembly | Remove compulsory inspection globally at its owners | Implemented under ADR 0226; normal original-project selections executed without quality attestations |
| Video batch selection | Old final selection bundled AV observations and four unconditional `True` claims with source/window choice | A technically valid unreviewed candidate could not be selected | Version selection receipts separately and keep optional judgments out of admission | Implemented; first original H3 window selected with Codex attribution and no quality claims |
| Normal H3 Start | The old request could only identify an unnamed creator or a bounded QA actor | Would misattribute this real-story agent operation | Add explicit source-bound Codex operator ownership | ADR 0230 implemented/reviewed; first real gateway job carries this operator; fresh full gate passed |
| Conversation still request | A model-owned actual prompt released hand contact and put down the card before the authored N10 branch | Published candidate could not support a faithful source-to-request claim | Clarify current state in the author-owned target direction and create one fresh immutable job | Old candidate retained unselected; corrected request and literal call audited/selected; no pixel judgment |
| Early eight-shot route | Normal player and exporter both require complete installed-graph media inventory | Eight-shot route cannot be played in the existing complete-graph surface while seven other slots are absent | Retain supported refusals, verify selected first-route clips, then finish full inventory | Complete: all 15 selected and all three standalone routes exercised; no partial-player/export feature, altered graph or fabricated media |
| Known-ID H3 retrieval | A successful 362-frame gateway output initially stayed `retrieve_needed` with a generic retrieval/probe error | Batch progression paused while retaining the known prediction and original outcome | Read exact output/hash and transport/adapter/probe evidence, then reconcile the same ID through the ordinary public service | Same output ingested, frozen batch resumed; first cause remains unproven, no replacement generation or source fix claimed |

Add actual production observations as encountered. Fix blockers to this outcome;
queue convenience/polish separately. Test totals, generated clips and worker
reports cannot substitute for a final playable package or prove creative quality.

## Historical scope

The initial benchmark proposal's creative-quality gate was superseded by the
owner's MVP instruction. During planning, a narrow prototype-selection exception
was considered; the owner's subsequent global-disable instruction supersedes it.
The previously queued quality-modularization work is not started here. Existing
quality failures remain failed and unreviewed media remains unreviewed. The
completed bilingual functional closeout and its recorded runtime/recovery identity
remain historical evidence, not qualification of this new implementation.
