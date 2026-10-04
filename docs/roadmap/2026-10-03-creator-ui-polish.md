# Creator UI polish and self-guided workflow

Status: **scoped implementation and Chinese manual complete**, with qualified
runtime candidate `e0a4f66`. Human usability acceptance remains pending.
Prepared October 3, 2026, Toronto time, using Relay Brainstorm and Plan.
Baseline: clean retained `main` at `a6507cb734c7d8674851badf86a0ac2215cafa01`.
Approved allowance: **ten hours maximum**, starting 2026-10-04 03:57:07 UTC
(October 3, 23:57:07 Toronto); handoff by October 4, 09:57:07 Toronto /
13:57:07 UTC. Finish earlier when the full scoped outcome is verified.
Manager: `01a04525-e907-7630-9640-78790d69e8ae`; retained `main`, sole source writer.
Owner refinement: direct iteration on the normal installation is permitted
while the owner sleeps; a separate interactive test copy is not required.
The work sequence is journey-first: UI changes serve the creator's tasks.

## Outcome and continuity

Make the existing creator journey understandable from the product itself:
creators can identify their current task, required input, current result and next
action without developer narration. Establish consistent visual hierarchy across
the journey, with acceptable existing media; final-film quality is not the goal.
Prioritize friction that prevents understanding or completing the next task,
then use layout, wording and visual hierarchy to remove that friction. A visually
consistent page with a confusing handoff does not satisfy the outcome.

This is a new bounded follow-up to the completed
[E2E-first continuation](2026-10-03-e2e-first-continuation.md), informed by the
[existing usability decisions](2026-09-18-creator-workflow-usability.md).
It does not reopen their completed implementation or acceptance records.
The [normal activation receipt](../verification/2026-10-03-normal-backend-activation.md)
owns the current installation baseline: 74 tables, existing story/media preserved,
H3 disabled, and the completed media story retained in the separate 8851 copy.

Retain the current dark visual direction and primary workflow. No rebranding,
new wizard, duplicate progress authority or new generation feature is proposed.

## Evidence and diagnosis

The owner reports needing narration during the previous walkthrough and supplied
a screenshot of the unsaved Brief with advanced settings expanded. The source
inspection confirms:

- `BriefPage.tsx` gives the alternate-workflow panel neither form-card padding
  nor a defined gap after the two-column layout. Its heading/button touch edges.
- `styles.css` makes ordinary section eyebrows uppercase gold monospace, and
  the shot range a 20px bold green monospace value. Typography uses many local
  size/color rules rather than a small role-based scale.
- `Button` exposes useful action variants, but disabled styling mostly changes
  opacity and uses a wait cursor even when nothing is running. Quiet enabled and
  quiet disabled actions can look too similar.
- Brief save requires a nonempty synopsis and valid duration. Refresh/snapshot
  require a saved project; settings remain available beforehand. These valid
  restrictions need visible reasons, not relaxed guards.

These are shared presentation and workflow-explanation problems. Fix them in
shared primitives and their owning stage views; preserve state/dispatch contracts.
The shot range is **one example**, not the typography audit's boundary.

## Coverage and proposed presentation rules

Audit the actual primary journey: Brief → source/outline and branches →
characters → art/reference review → script → storyboard review → canonical
production handoff → keyframes/video/segment review → reader/player, both endings.
Include the common shell, relevant settings dialogs and alternate-workflow entry.
Secondary developer tools retain technical detail; they are not separately
redesigned, but must not break under shared styling changes.

For each stage, first map the creator's goal, prerequisites, task, expected
result, next destination and recovery/return path. Identify where the earlier
walkthrough needed narration. Use that task map to determine the prominence,
labels, grouping and guidance of controls; do not design navigation around an
inventory of internal modules. Prioritize fixes in actual journey order while
preserving useful revisiting/iteration rather than imposing a rigid waterfall.

### Typography, color and spacing

- Inventory font size/family/weight, line height, color, casing and spacing in
  the covered views. Identify additional outliers through actual screenshots,
  not just a search for the owner's examples. Keep a bounded finding list with
  screen/state, reason, owning rule and disposition.
- Use named roles for page/section headings, body, labels and supporting text;
  choose a small readable scale during implementation. Equivalent roles share
  styles. Dense technical data may differ deliberately; identifiers/code may
  retain monospace. Reader/player narrative hierarchy need not match form labels.
- Preserve meaningful warning/error/success colors. Ordinary numbers and helper
  labels should not resemble success indicators or primary actions. Replace
  conspicuous English eyebrows in Chinese creator views with useful Chinese
  headings or remove redundant labels.
- Apply consistent card insets, sibling gaps and action-row spacing in collapsed
  and expanded states. No edge-hugging heading/button or touching adjacent cards.
- Mark genuinely required fields with `*` and a concise legend plus accessible
  required information. Do not mark optional titles or whole panels as required;
  do not accidentally change validation by adding native form constraints.

### Actions and guidance

- Retain clear primary/secondary/quiet/destructive meanings. Enabled controls
  have readable contrast and visible focus/hover; disabled controls have one
  recognizable treatment across variants and no active hover treatment.
- Distinguish unavailable from busy: unavailable actions explain what is missing;
  busy actions name the operation and prevent duplicate activation. Do not rely
  only on color, opacity, cursor or hover-only tooltips for these distinctions.
- Make the recommended next action prominent in each stage, with concise
  prerequisites. Explain whether it saves a draft, generates a candidate,
  accepts/installs content, selects media, or merely navigates.
- Reuse authoritative stage/job/review state. Loading/unknown is not missing;
  generated is not accepted; selected is not final-film approval. Preserve stale,
  rejected, failed, read-only and unsaved-change behavior and recovery actions.
- Review creator-facing Chinese throughout coverage. Prefer consistent terms,
  natural instructions and concrete action verbs; put necessary technical terms
  behind explanations or technical details. Do not rewrite story/dialogue/prompts.
- Keep the supported alternate proposal workflow accessible but subordinate,
  preferably under a clearly labeled collapsed disclosure. Do not delete it or
  suggest its results are interchangeable with source-reviewed content.

## Ordered deliverables and budget

1. **Journey map and baseline (about 1 hour).** Verify normal-installation
   identity, quiet specialists and preservation baselines. Map tasks, results,
   handoffs and failure/recovery states through the covered journey; inventory
   screenshots and typography outliers alongside them. Rank findings by their
   effect on understanding/progress. Diagnose authoritative-state gaps first.
2. **Entry and guidance foundation (about 1 hour).** Make the first meaningful
   journey segment, Brief → source/outline, self-explanatory: required inputs,
   action consequences, disabled reasons and destination. Fix the supplied
   Brief findings and establish the minimal shared type/spacing/action roles
   needed here. Record stable conventions as a concise ADR; extract affected
   cohesive CSS from the already-large stylesheet before extending it.
3. **Continue in creator order (about 2.5 hours).** Work through characters,
   art/references, script, storyboard, production/keyframes/media review, then
   reader/player. At each handoff fix demonstrated task/status/next-action
   ambiguity, Chinese and relevant layout/typography together. Check return
   navigation and drafts before proceeding. Use existing state owners; a missing
   backend contract or new workflow is an escalation point, not permission to
   invent readiness. Avoid an unrelated stylesheet/application rewrite.
4. **Cross-journey consistency sweep (about 1 hour).** Revisit the complete path
   and relevant dialogs to catch residual typography, terminology and action
   inconsistencies. Ensure the shared scale works across real uses, all supplied
   examples are resolved and every audited finding has a disposition. Preserve
   intentional technical/narrative exceptions. Do not let optional decoration
   outrank an unresolved navigation or comprehension problem.
5. **Review, verification and delivery (reserve about 2.5 hours).** Obtain a
   bounded independent review of the stable implementation; fix concrete
   in-scope findings, run required gates, verify the normal installation's final
   UI assets, and produce journey-focused screenshots and an honest closeout.

These are estimates, not fixed per-phase deadlines. Reassess around hour 2 and
hour 5. Reserve the final two hours for verification/handoff; do not continue
optional refinements at the expense of unfinished required checks. If the budget
cannot cover the scope, record completed versus deferred findings and ask for a
material scope decision; elapsed time alone never establishes completion.

## Implementation entrypoints and dependencies

- Shared controls: `frontend/src/components.tsx`; shared/role-based CSS currently
  in `frontend/src/styles.css`, plus relevant existing scoped styles.
- Brief: `frontend/src/pages/BriefPage.tsx`.
- Shell/navigation: `frontend/src/app/workspace/WorkspaceController.tsx`,
  `WorkspaceViews.tsx`, `useWorkspaceNavigation.ts`.
- Stage owners: existing `SourceOutlinePage.tsx`, `CharactersPage.tsx`,
  `ScriptPanel.tsx`, `StoryboardReviewPanel.tsx`, `ProductionBridgePanel.tsx`,
  `ProductionPresentationReview.tsx` and their current media/reader consumers.
- Existing checks: `frontend/tests/app-state.test.ts`; E2E `first-save`,
  `manual-creator-entry`, `workspace-presentation`, `creator-workflow-navigation`,
  `source-outline-section-map`, `production-presentation`, `story-prototype`,
  `project-lifecycle`, `project-folder-close` and affected media-review tests.
- Build/runtime: `frontend/vite.config.ts`, `frontend/package.json`,
  `services/creator_workbench/README.md`, `.github/workflows/ci.yml`.

Reuse current components and state owners. Keep new modules cohesive and small;
split affected responsibilities when an existing large file needs more logic.
The implementer chooses exact token values and minimal module boundaries.

## Verification and observable acceptance

1. Every listed primary view has an audit disposition, and supplied Brief
   spacing/typography/required-marker/button findings are resolved. Before/after
   screenshots use comparable states and viewports, including expanded settings.
2. No unexplained typography/color outlier remains in the audited creator views;
   deliberate exceptions have a reason. Labels/help remain legible at normal
   zoom. Primary, enabled secondary, disabled and busy states are distinguishable
   without color alone; required labels are accessible and match actual rules.
3. At each stage the current task/result and next action are findable from the
   UI. Blocked actions explain the relevant prerequisite and recovery path.
   Navigation does not discard drafts or bypass review/currentness/dispatch.
4. Check 1440×900 and 1920×1080 desktop views, compact 1280px layout and a narrow
   smoke check for new shared rules: no clipping, accidental horizontal overflow
   or unreachable actions. This is not a complete mobile-product redesign.
5. Use isolated fixture projects for save/generate/approve/selection transitions,
   including missing, loading, busy, stale/rejected, error, read-only and draft
   states. These ordinary automated-test fixtures are not a separate interactive
   iteration copy. Fake-transport tests are not new real-generation evidence.
   Inspect available real data/media on normal and exercise both player routes
   in the existing fixture suite. The normal original has no installed completed
   production story: do not imply fixture route playback is a fresh real-media
   normal-installation walkthrough or transfer media just to create that claim.
6. Run focused assertions first, then frontend unit/type/build checks and the
   full unfiltered established release gate on the final candidate. Preserve
   supported assertions when labels change; no blanket skips, timeout inflation
   or removal of behavior checks to obtain a green result. Report exact tested
   revision and CI status separately from screenshots and owner acceptance.
7. Verify original data/media and completed-copy selection/review facts remain
   unchanged. The owner later tries the polished flow without step-by-step
   coaching; until then report self-guidance as implemented and checked, not
   as human usability acceptance already obtained.

## Dependent deliverable: Chinese Creator's Manual

The owner proposes a Creator's Manual after the UI stabilizes and explicitly
requires **Chinese**, because Chinese-speaking colleagues are the main users.
Write directly for those creators, without assumed developer/Codex knowledge.
Use natural Chinese and the exact finalized UI terminology; explain unavoidable
technical names rather than exposing internal English labels as instructions.

Recommended structure:

- **快速上手：完成第一个互动故事** — one worked example from an idea through
  the creator journey to its two playable endings.
- **分步创作指南** — each stage's purpose, required input, actions, expected
  result, how to tell the task is complete, and where to go next. Include reviewed
  screenshots from the stabilized UI rather than draft controls.
- **修改、回退与常见问题** — saving versus generating versus confirming versus
  selecting, revising approved work, stale/missing results, disabled actions,
  failed jobs and safe recovery. Preserve actual approval/dispatch boundaries.
- **术语与检查清单** — a short Chinese glossary and practical readiness/review
  checklists, including individual sound review where applicable.

Capture useful explanations during polish, then write and verify the manual
against the qualified UI revision. Record its applicable version/date and follow
the written steps to find missing or stale instructions. Routine next-step
guidance remains the UI's responsibility; the manual supplies onboarding,
reasoning and reference. Colleague feedback is a later human acceptance check.

The ten-hour kick-off includes this dependent deliverable after the stable UI
checkpoint. Reserve approximately two hours from the extended allowance for
Chinese authoring, screenshots and step-by-step verification. Do not write final
instructions against unstable controls or substitute the manual for UI guidance.

## Direct installation work and authorization boundary

Work serially on retained `main`, preserving unrelated changes. A stable-delta
independent review is a bounded later review, not parallel source writing.
After implementation approval, use Relay Direct for any delegated coordination;
choose native model/effort at dispatch under the repository's guide.

The owner explicitly permits working directly on the normal installation during
the planned sleeping window. Use normal port 8841 for interactive UI iteration and
inspection; do not require a separate preview/test-copy installation or a later
copy-to-normal promotion step. The checkout mount serves rebuilt static bytes
immediately, so coherent change checkpoints may be visible before the entire
pass is finished. Keep shipped assets fresh, reload after each relevant rebuild
and distinguish intermediate checks from final qualification. This permission
changes the iteration location, not the integrity or acceptance requirements.

Use normal data for non-mutating navigation/inspection. Automated fixtures own
mutating lifecycle, generation and approval tests; do not edit the owner's story
or approval state to stage demonstrations. Preserve the retained completed copy
without using it as this pass's interactive iteration environment. No new
deployment service, compatibility layer or automatic backup machinery is needed.

Normal frontend iteration and final publication were permitted for this approved
scope under the ten-hour implementation window.
No backend/schema change or restart is expected; seek direction for a
demonstrated need beyond this scope.
Do not transfer the finished story into normal, change specialist settings or
credentials, enable H3, dispatch new real text/image/video jobs, regenerate
media, change creative approvals, reset data, or remove supported workflows.

Deliver: scoped committed/pushed source and fresh static, audited finding
dispositions, stable-convention ADR, exact verification results, before/after
screenshots, a usable normal UI, the verified Chinese Creator's Manual and explicit remaining
items. Stop when the scoped checks pass and handoff is saved, or report a
concrete blocker. The active Goal owns continuation; do not create duplicate
reporting automations or infer broader production authority from the time budget.

## Completion

The [verification and finding-disposition record](../verification/2026-10-04-creator-ui-polish.md)
records the complete covered journey, supplied Brief examples, broader
typography/Chinese audit, owner-layer recovery corrections and independent
reviews. All 452 unit, 1062 Python and 138 unfiltered local browser tests passed.
Published runtime `e0a4f66` passed full remote verification and both browser
shards; normal assets and original/copy preservation checks matched exactly.
The [Chinese Creator's Manual](../creator/manual.zh-CN.md) includes reviewed
screenshots, a two-ending example and safe recovery instructions.

No original story, media or approval was changed; H3 stays disabled in normal.
The owner's uncoached attempt and Chinese-speaking colleagues' feedback remain
the human usability check. Final-film polishing and further production are
not part of this completed implementation scope.
