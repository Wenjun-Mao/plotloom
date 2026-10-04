# Journey-first creator UI polish: verification and finding dispositions

Status: scoped implementation and Chinese manual complete. All local release
gates and full remote CI passed for published runtime candidate `e0a4f66`.
Not human usability or creative acceptance.
Scope: [approved plan](../roadmap/2026-10-03-creator-ui-polish.md), ten-hour Goal
window, direct normal-installation iteration and Chinese manual after stable UI.
Contract: [ADR 0111](../adr/0111-journey-first-creator-presentation.md).

## Baseline and preservation

Normal 8841 and its native specialists were healthy/idle at preflight. The
existing read-only capture helper wrote
`.local/unattended-2026-10-02/evidence/manager-ui-polish-preflight-original.json`:
74 table projections, 67 managed file hashes and 7 API projections, exactly equal
to the authorized normal-activation after-capture. The retained copy's 17 jobs,
12 selected/current segments and review identities were separately read as a
preservation baseline, not used as the interactive iteration environment.
The initial source is `a6507cb734c7d8674851badf86a0ac2215cafa01`.

After the live walkthrough, `manager-ui-polish-final-original.json` exactly
matched the preflight capture (`cmp` passed). The retained copy's final job/
selection/review projection also exactly matched its baseline. No media was
transferred. The original retains accepted source, outline, branches, cast and
art, but no current accepted Script or installed completed production story.
These facts were not changed to stage screenshots or demonstrate later steps.

Current normal public endpoints report `/api/v2/video-backend`:
`enabled=false`, `reason=h3_video_not_configured`, and
`/api/v2/video-pilot-budget`: `configured=false`, no attempts. No provider,
credential, assistant configuration, creative acceptance or dispatch was changed.

An actual normal unsaved Brief with expanded settings was captured as
`.local/creator-ui-polish-2026-10-04/brief-before.jpg`. Creating that client draft
and expanding controls did not save a project, dispatch a job or change content.

## Audited journey and dispositions

| View / finding | Owner-layer change | Verification status |
| --- | --- | --- |
| Brief: edge-touching legacy panel/button, missing sibling gap | Shared insets/gaps; accessible collapsed alternate workflow | Built normal expanded/collapsed views and four viewport fixtures checked |
| Brief: English required banner, unexplained disabled save | Genuine per-field `*`, accessible required flags and adjacent prerequisite; title remains optional | Unit/save/navigation checks and actual blank Brief checked |
| Brief: green oversized shot range, mixed labels | Shared type roles, ordinary range value and natural Chinese settings | Expanded normal screenshot and 1440/1920/1280/390px fixtures checked |
| Shell: disabled/quiet/primary confusion and unexplained project tools | Neutral dashed disabled state; separate announced busy operation; visible prerequisite | Shared-control unit assertions and normal shell checked |
| Shell: expanded diagnostics intercept Save | Diagnostics in normal flow; expanded toolbar scrolls with page | Durable-draft regressions and four viewport real Save clicks pass |
| Legacy generation succeeds without a current visible candidate | Run observer setup is live after StrictMode replay; real unmount and route-currentness still refuse late results | Four new regression cases failed before fix and pass after; independent 46-test follow-up passes |
| Trace → repair loses live progress; empty list claims validation success | Same-project active-run observation starts under the destination epoch; empty projection describes absence, not success | Three active-status and empty-copy regressions fail before fix and pass after; terminal/other-project/pending-selection guards checked |
| Source: unmarked adaptation intent and unclear sequence | Required labels; owner-derived current task and next-step guide | Source/save/navigation fixtures and actual accepted Source checked |
| Branches: tiny accent legends and unmarked required text | Shared label roles; eleven required text fields marked; stable/default IDs explained | Section-map assertions and source/branch fixture checked |
| Characters: failed read remains spinner | Cast error/retry; no dependent appearance spinner after failed cast read | Failure/retry assertions and navigation fixture checked |
| Cast/Art/Script: old accepted head hides current task | Stale/reopened/prepared/ready work and retained dirty-buffer recovery precede accepted summary | Combined-state assertions, discard guard and review-seam fixtures checked |
| Characters → Art → Script → Storyboard handoffs | Existing owner-derived readiness and guarded navigation | Available live handoffs checked; missing normal Script remains blocked; draft/navigation fixtures pass |
| Character/art reference typography and ambiguous labels | Shared gallery/legend/support roles, Chinese instructions, browse versus selection consequences | Normal Characters/Art and reference/image fixtures checked |
| Storyboard: review confused with production | Current review guide explains separate review acceptance and production proposal | Owner-currentness assertions/fixtures checked; no duplicate progress authority |
| Production: next shot hidden in inventory | Current valid installed proposal exposes first shot; other shots retained | Admitted/stale bridge fixtures and exact disclosure locator checked |
| Image/keyframes: English labels and conflated acceptance | Chinese task/delivery labels; original/refinement/adaptation distinct; one-of intent and required source refs explained | Image/imported-still fixtures and presentation assertions checked |
| Same-person review: unclear required fields/reviewer identity | Four real required inputs, explicit verdicts, truthful Codex versus human identity | Required/provenance assertions pass; no approval authority relaxed |
| Video: historical selection contradicts next action | Shared current-job/current-selected-segment predicate plus authored duration; stale/rejected recovery | Video/segment assertions and retained fake-H3 fixture checked |
| Reader/player: loading called unavailable; no fatal-read return/retry | Loading/missing/failed distinction and project-scoped read-only return/retry | Unit/fixture checks and actual missing normal reader/player retry/return checked |
| Settings: default fieldset and tiny accent typography | Consistent insets, muted form legends and readable helpers | Built assistant settings inspected; no settings saved |

The audit extends beyond the shot-range example to cast legends, gallery
headings/metadata, branch legends, toolbar/sidebar metadata, settings,
image/keyframe review and reader navigation. Equivalent roles share
`creator-ui.css`: page 26–36px, section 18px, body 14px, label 13px, support 12px.
Technical IDs, code/JSON, provider protocol names and retained job-state
identifiers are deliberate technical exceptions. Narrative reading retains its
reading hierarchy. Warning/error/success colors still describe actual state.

The existing below-820px collapsed sidebar/footer is retained. The 390px check
is a shared-layout smoke test, not a redesigned mobile product. Actual normal
data covers only available original stages; mutating/late-stage fixtures and
fake transports are not new real-generation or listening evidence.

## Root-cause corrections and independent review

The first unfiltered browser run reported 131 passed / 7 failed. Traces are
preserved in `.local/creator-ui-polish-2026-10-04/gate-one-evidence/`.

- Absolute-positioned expanded diagnostics intercepted Save. The owning toolbar
  now uses normal layout; the tests still exercise actual clicks and draft saves.
- The bridge disclosure's text also appeared in a guide sentence. Its test now
  targets the exact disclosure, retaining the handoff and authority assertions.
- Legacy proposal tests assumed an always-expanded entry and English copy. They
  now open the supported disclosure and assert current Chinese labels, retaining
  generation, acceptance, rejection and currentness checks.

All seven original failures passed in focused verification. A new viewport test
then incorrectly expected a connected-server label on an unsaved project. It
now checks the actual open disclosure and waiting-to-edit draft status; no
product workaround was added. All four viewport cases pass. No skip, assertion
removal or timeout inflation was used to obtain these results.

The second full gate reported 137 passed / 1 failed. Its preserved
`legacy-post-generation-second-gate.trace.zip` showed a successful run but an
early aggregate with missing stages and no command-observer progress reads.
`useRunSession` set its disposal flag in StrictMode cleanup but never reset it
on replayed setup. The observer now resets during setup and refuses held
progress, final reloads and errors after real unmount. Four new lifecycle tests
failed before the correction and pass after it. No generation is resubmitted
to recover observation; route epochs and dispatch rules remain unchanged.

The subsequent three-repeat diagnostic caught a separate test assumption in
two cases: it opened the legacy disclosure while a preceding task was still
busy, before final canonical refresh remounted the revision-keyed Brief. The
test now waits for the normal enabled generation action before opening the
disclosure. `legacy-title-save-observation.trace.zip` preserves the evidence;
assertions and timeouts remain unchanged. All twelve cases in the final
three-repeat diagnostic passed. Repetition is not the full release gate;
final unfiltered qualification must still pass.

The third full gate also reported 137 passed / 1 failed, this time in exact
work-unit repair. `exact-repair-live-observer.trace.zip` showed that navigation
from trace to quarantine correctly refused the old route's held progress but
did not start a destination-route observer. The backend run was already
quarantined with an eligible failed unit; the UI retained its earlier running
projection. Same-project active-run navigation now reads that existing run
under the new epoch when no aggregate load or pending trace selection owns the
transition. It never resumes/resubmits a run, and terminal/other-project runs
are excluded. An empty quarantine list no longer implies all outputs passed.
Three active-status checks and the empty-copy check failed before the fix;
74 focused tests and TypeScript passed after it. No repair authority, stale
response checks or browser assertion timeout was weakened.

An attended read-only GPT-6.1 Sol / Medium review found three concrete issues:
legacy Brief generation lacked its read-only guard, stale Cast tasks could lead
the guide, and retained dirty Art buffers could get misleading continuation
instructions. Root corrected the owning predicates and added regression checks.
The stable follow-up found no actionable issues. A final material-delta review
independently passed 36 tests in four suites with no findings; it did not certify
live playback, final creative quality or human acceptance.

A bounded observer-delta follow-up by the same read-only GPT-6.1 Sol / Medium
reviewer found no actionable issues and independently passed 46 lifecycle/App
tests. It confirmed that observation changed without resubmitting runs or
altering dispatch authority. The App suite emitted an existing list-key warning.

The independent navigation-delta follow-up found no actionable issues and
passed 25 navigation/loading, creator-presentation and observer-lifecycle tests
across three files. It confirmed aggregate-load ownership and exclusions for
pending selections, other projects and terminal runs; no runtime writes occurred.

## Chinese manual and screenshots

[Plotloom 创作者手册](../creator/manual.zh-CN.md) uses a small worked example,
exact UI actions, completion checks, safe recovery and a handoff checklist.
Draft/save, prepare, dispatch, confirm candidates, select media and final
creative acceptance remain distinct. It neither requires H3 activation nor
invents retrieval/retry for an unknown dispatch. Reference images not yet used
automatically by production are described explicitly.

Three reviewed normal-installation images are included in
`docs/creator/screenshots/`: blank unsaved Brief and existing accepted Source/
Characters, each 1440×900. The extended comparable owner-example view is
`.local/creator-ui-polish-2026-10-04/brief-expanded-final-1440.jpg`, 1440×1245.
These states are labeled and do not imply a completed normal media story.

The manual was read against current controls and the available live handoffs.
An attended GPT-6 Luna / Max review found ambiguous H3 configuration wording
and unavailable retrieval for unknown outcomes; both were corrected. Follow-up
confirmed the substantive fixes and requested the literal `outcome_unknown`
state alongside its Chinese gloss; root source-checked and added that match.
All 39 local links in the manual, creator entrypoint and docs index resolve.
The last comparable Brief review also aligned the manual's generic guide
description with its actual heading, “从故事想法开始”, rather than claiming
every page literally says “本步指引”. No controls or runtime behavior changed.
Native file-panel preview was requested; the app returned `queued`, so this
receipt does not claim the owner has seen it. Colleague feedback remains human
acceptance, not a completed check here.

## Checks and delivery

| Check | Actual result |
| --- | --- |
| Frontend unit suite | 452 passed across 60 files, including observer lifecycle and navigation handoff coverage |
| TypeScript | Passed |
| Production frontend build | Passed; existing large-chunk warning retained |
| Checked versus served normal assets | All three changed bundles' SHA-256 values match exactly |
| Python suite | 1062 passed; one existing Starlette/httpx deprecation warning |
| API unused imports | Passed |
| Archived prompt reader verification | Passed |
| Wheel build and installed-wheel smoke | Passed outside the source checkout |
| Whitespace check | Passed |
| Focused browser findings / viewport additions | Seven original failures and four viewport cases passed |
| Navigation-delta repeated browser check | 21 passed: exact repair and Brief workflow, each repeated three times |
| Final full unfiltered local browser gate | 138 passed in 14.6 minutes against frozen navigation-delta source/static |
| Full remote CI on pushed runtime candidate | Passed on `e0a4f66`; verify and both 69-test browser shards succeeded |

Current normal bundle SHA-256:

- `workbench.js`: `695f60c1aae80f0adc5ea8842d70f69ad7c0a8706a6264dd29663390fbb56464`
- `workbench.css`: `758746974ac33af6f69c4e33e972511a175c80cf2a4f2ffe59400a076ddfd8b0`
- `workbench2.css`: `2242e2412f14b42edfe85d7e65df987193125233c7664f6ed360e2747a998d86`

The final local command was `npm --prefix frontend run test:e2e -- --workers=1
--grep='.*' --global-timeout=2400000`. It passed without filtering out tests,
skips, weakened behavior assertions or timeout increases. The final locked
Python rerun passed 1062 tests in 328.61 seconds. The normal served assets and
preservation capture were checked again after the last live reload; all matched.

## Published qualification and remaining acceptance

Runtime and manual candidate `e0a4f66c5e2eecbbcbd19da595fc456a6531eb70` was
committed and pushed to `origin/main` with a clean checkout and no divergence.
[Full CI run 37182786670](https://github.com/Wenjun-Mao/plotloom/actions/runs/37182786670)
used `browser_grep=.*`; all jobs passed, with the last completing at
2026-10-04 07:00:48 UTC.
Verification took 13m9s; browser shards passed 69 tests each, for all 138 tests.
The remote Python suite passed 1062 tests with the existing deprecation warning;
the installed-wheel smoke and checked-bundle guard passed. CI's platform
deprecation notices did not skip or replace any checks. No workflow changed.

This documentation closeout changes no runtime or static bytes. The normal
installation serves the qualified assets directly from the checkout; no
backend restart or media transfer was needed. The final pushed documentation
revision and its own full CI result are reported in the manager's handoff.

The scoped implementation/manual outcome is complete. The owner's later
uncoached walkthrough and colleagues' manual use remain human acceptance.
Further film-quality improvement, real generation and installing the completed
copy into normal remain separate work, not implied by this UI qualification.
