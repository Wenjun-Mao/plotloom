# The Last Projection: standalone H5 MVP and optional media review

## Current status

Updated: 2026-10-30. Owner: root, with one implementation/qualification owner on
`/Users/wjmao/.codex/worktrees/b30f/plotloom`, local `main` at `d77af4c4` before
this plan. Result: the [working story](2026-10-30-first-h5-story.md) and current
export/selection boundaries are inspected; both independent plan reviews are
complete and their justified finding is resolved. Implementation has not started.
This is the requested implementation plan, including Wenjun's subsequent
direction to permanently disable forced audiovisual inspection everywhere in
Plotloom. No unresolved planning decision; implementation acceptance below is
unexecuted. Next action when implementation is requested: phase 1 preflight and
the global optional-review contract slice. Planning stopping condition is met:
the reviewed plan and scope are saved. This planning request does not itself
start implementation, deployment or media generation.

## Acceptance

| Claim | Required evidence | Fresh media | Status / evidence |
|---|---|---|---|
| Optional media review throughout Plotloom | Normal non-QA project can select references/keyframes, prepare and adopt materials, generate, select/trim clips, play, reopen and export without watch/listen/quality attestations; UI, API, storage readers and generated instructions agree; restart/new-project checks preserve this behavior | No; retained valid media and transport fakes cover policy | Planned; current mandatory gates mapped below |
| Complete standalone game | Final exported ZIP unpacks outside the checkout; start → all three authored routes/endings → restart/last-choice replay and HTTP reload/Continue work with Plotloom unavailable; request audit permits only packaged files | Retained media for early slice; original media for final game | Planned |
| Lightly styled usable MVP | Desktop and 390px viewport inspection shows legible title, choices, controls, dialogue and ending cards with focus/pressed states; no blocked progression or clipped essential controls | No quality experiment | Planned; responsive viewport is not real-phone qualification |
| Faithful story and final requests | All seven draft roles and six edges mapped to project/runtime identities; exact choices, dialogue and endings retained; full final image/H3 requests compared with source, references, timing and authorized settings | Provider-free comparisons; actual production dispatch receipts also retained | Planned; frozen briefs alone do not prove final tool arguments |
| Technical validity and provenance | Selected bytes decode/play; hashes, sources, revisions, references and frame windows match; stale/wrong-source/unauthorized/concurrent selections still refuse; reopening preserves current project assets and facts | No by default | Planned |
| Original story production and future update seam | Actual Plotloom project produces this story's assets, records selection and exports them; build-side slot/source/candidate bindings survive reopening; replacing a fixture slot leaves graph/UI unchanged | Yes for the original assets the project lacks; no quality rerolls | Planned; retained unrelated clips cannot satisfy final story production |
| Local qualification and activation | Stable candidate passes applicable full local qualification, exact installed-package export, normal runtime activation and preservation/readback; refreshed single recovery restores the new selection contract; final package exercised after material repairs | No extra generation by default | Planned; hosted CI not requested and not a release gate |
| Audiovisual creative quality | No required inspection, listening, score, identity-quality verdict, creative pass or quality-based retry; accurately label unreviewed media | No | Explicitly outside this milestone |

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
   completion, ingestion, selection and export for N00/C01/E01, then play it.
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

Implementation permission is distinct from this planning request. When execution
is requested, the planned run includes ordinary project creation/source adoption,
truthful agent selections, in-scope fixes/reviews, required local tests, supported
local activation, normal recovery and scoped scratch cleanup; do not insert
routine review/selection/restart approval gates. Existing owner authorization
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
| Planning: media selection | Current contracts require AV attestations and restrict functional-only exceptions to old QA projects | Conflicts with owner instruction and truthful real-story assembly | Remove compulsory inspection globally at its owners | In this plan; not yet implemented |

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
