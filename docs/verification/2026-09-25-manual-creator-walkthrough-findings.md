# Manual creator walkthrough — running findings

Status: fixes deployed for a fresh manual walkthrough; director acceptance pending.

## Authorized fresh-start reset

Approved copy follow-up (2026-09-26): `保存接受的来源` becomes
`确认改编内容`, with helper text explaining that content and creative direction
will guide the outline, but confirmation itself does not start generation.
This changes presentation only; persistence and explicit acceptance are unchanged.

Follow-up deployment (2026-09-26): the manager inspected the contextual single
Brief action, reran `app-state` and `m1b1-app-contract` (46 tests passed), and
rebuilt the deterministic shipped bundle. HTTP-served `workbench.js` matched
the local bundle SHA-256 `1dacda9f30b33a8d9d7d843ed6e2e2a04aec624443fa31701a4d3ace63726bf8`.
No restart, Safari reload or project write was performed. Worker evidence reports
221 unit tests and 18 focused browser tests passing; three broader media-draft
close cases failed and remain an unclassified verification gap. The director's
Safari replay remains pending. The reporting watchdog is paused.

Both 8841 walkthrough projects (`54d6631f-8317-4f1c-a472-c9298ef93a50`
and internal rehearsal `8c5e9071-4a6d-40d2-992e-e17ec5fd2e75`) were moved to
`/Users/wjmao/.Trash/plotloom-8841-walkthrough-reset-20260926/outputs` after
explicit director confirmation. They remain recoverable. Application settings,
this log, repository history and earlier media work were preserved.

The shipped static build passed and the isolated server restarted as PID 83754.
The project-list API returns an empty list. A new browser tab visibly opens at
`从一个项目开始`; no project was created. The browser tool exposed no old tab,
and direct storage removal was unsupported: this verifies a fresh session with
no recovered draft, not deletion of inaccessible prior-tab session storage.
The reporting watchdog is paused while the director resumes.

## Scope and working agreement

### Next-work queue agreed during outline review — 2026-09-26

Documentation-only assessment while the creator is away:
[proposed synopsis slice and consolidated report follow-ups](../roadmap/2026-09-26-premise-to-synopsis-plan.md).
No feature implementation or provider execution is authorized by that proposal.

- [ ] First finish the creator's review of the current 雨停以后 outline. The
  creator observed the browser check showing `明细表` works; this is not
  creative acceptance. Continue the walkthrough without restarting or regenerating.
- [ ] Next implementation slice: `帮我写故事梗概`, turning a premise into an
  editable synopsis proposal, with explicit confirmation rather than auto-acceptance.
- [ ] Alongside synopsis assistance, clarify scope: standalone short versus
  series, target duration, optional episode count and branching preferences.
  Episodes, branches and endings must remain distinct concepts; inspect existing
  contracts before adding controls or a second source of authority.
- [ ] Continue outline → branches → script → shots through the manual
  walkthrough, retaining review checkpoints and capturing actual friction before
  expanding automation. Do not implement the entire pipeline upfront.

Current instruction is to record this queue and continue the walkthrough, not
start feature implementation. Current project: `ee271b49-f384-414c-9711-452ee6333b84`;
outline handoff: `ch_ee6740b0fa7f4e7b91cc31185bb3e692`. Last verified candidate
state is ready and unaccepted. The creator owns the acceptance decision.

### Director replay checkpoint — 2026-09-26

The director clicked `保存并继续到来源` in Safari. Screenshot
`/var/folders/ys/g3nd6nfx2xd9wmw053lg109m0000gn/T/codex-clipboard-57a34129-5186-4620-9bbe-daa765d33632.png`
shows the named project, Source view, carried-over title/synopsis, and no
attribution/rights form fields. Source is still explicitly unsaved. This is
visual confirmation of the entry transition, not source acceptance or generation.
Remaining visible usability observations for later review: `改编意图` has no
required-field indicator or explanation for an original synopsis; the unsaved
form sits under `已接受的来源`; candidate copy still exposes `specialist handoff`
and `revision` terminology. No additional implementation is authorized by
these observations alone.

The director creates a project from scratch through the real UI at
`http://127.0.0.1:8841/v2/`. The project is titled **雨停以后**. Its project ID
has not yet been recorded here. The separately assembled internal rehearsal
is not this user project and is not evidence of an unassisted creator journey.

Capture findings during the walkthrough; investigate root causes before fixing.
Do not change served UI, restart the service, fill forms, or make acceptance or
selection decisions on the director's behalf during the active walkthrough.

## Findings

### Outline confirmation wording

Creator found `显式接受此候选` unnatural. Agreed replacement:
`确认使用此大纲`, with `确认后，将以这份大纲继续设计分支和剧本；不会自动生成后续内容。`
This changes copy only; acceptance API, revision guards and creator ownership
remain unchanged. Verification uses the isolated source-outline browser journey,
not acceptance of the retained 雨停以后 project.

### Report label comprehension — 2026-09-26

- Scene-card occurrence strips also lack a legend: positions represent upstream
  entries, grey means absent, dark red means present for a primary scene, orange
  means present for a non-primary scene. Colours are unrelated to warning severity
  or approval. Creator needed explanation; record labelled positions/legend as
  follow-up, without changing the current candidate or report.

- Creator could not infer why S01/C01 are grey but 雨戏 is red, or why the
  second entry has only grey labels. These are entity references versus a
  generation-warning label, not approval/disabled states. A legend or readable
  scene/character names would make the distinction clearer; capture only for now.
- Delivered JSON explicitly has `warnings: ["雨戏"]` for entry 1 and an empty
  warnings list for entry 2. Absence of a warning is not proof of low difficulty.
  The source says rain has stopped, so the broad 雨戏 label needs creative review:
  do not silently infer active rainfall or alter the immutable candidate.
- Root cause traced subsequently: upstream `novel-outline.mjs` defines
  `雨戏: /雨/`; its risk-flag gate requires matching warnings in the candidate.
  Thus 雨停后 also triggers this intentionally overinclusive keyword rule.
  Rendering only colours supplied warnings; this is not H3 capability evidence
  or a calibrated difficulty judgment. Future review should distinguish heuristic
  reminders from model-specific, evidence-backed production risks.

### W01 — Starting workflow requires external explanation

- **Observed:** The Brief page prominently offers `生成故事提案`. The assistant
  instructed the director to avoid it, save the Brief, and navigate to
  `来源与大纲` because that button enters a different, older workflow.
- **Director feedback:** This explanation should not be necessary.
- **Impact:** The apparent primary action does not guide the intended journey;
  the director cannot determine the next step from the product alone.
- **Follow-up:** Investigate the entry/action ownership and post-save guidance.
  The supported next action must be discoverable in the UI without chat-only
  instructions. No route retirement or replacement is decided by this note.
- **Status:** Implemented in source, not yet deployed to 8841 or director-verified.
  A new project's Brief has only `保存并继续到来源`; a saved project's Brief has
  only `保存修改` and stays on Brief after saving. The existing proposal action
  remains visibly secondary, with context-appropriate guidance. Isolated
  browser tests verify both actions, including no second unsaved-draft prompt
  after first save.

### W02 — Adjacent Brief controls have inconsistent heights

- **Observed:** In the director's screenshot, the `语言` and `画幅` selects are
  substantially shorter than the adjacent `目标游玩时长（秒）` number input.
- **Impact:** Same-row controls look inconsistent and poorly aligned.
- **Follow-up:** Inspect shared select/input styling and actual browser rendering;
  align control heights without forcing helper text into the control itself.
  The shared CSS only set `min-height`, allowing the native number control to
  expand beyond the select height in the supplied browser screenshot.
- **Status:** Explicit 40px control height implemented; isolated Chromium
  checks at 1440px and 1920px pass. The director's browser must still confirm
  after preview deployment; headless Chromium did not reproduce the original
  80px number-input rendering before the CSS change.

### W03 — Brief title and synopsis do not carry into source entry

- **Observed:** After navigating to `来源与大纲`, the director confirmed that
  both title and source text were empty despite entering them in the Brief.
- **Impact:** The intended synopsis-to-source journey requires duplicate typing
  or copying, with no explanation of the relationship between the two records.
- **Follow-up:** Offer the existing Brief as an editable starting draft when no
  source exists; never silently accept it or overwrite an existing source/draft.
  Exact implementation remains to be designed and verified.
- **Status:** Implemented in source, not yet deployed or director-verified.
  An isolated browser test confirms new unsaved Source draft prefill from a
  saved Brief, no accepted Source revision before explicit Save, no overwrite
  of a dirty draft on Refresh, and no replacement of existing Source content.

### W04 — Remove attribution and rights declaration form requirements

- **Director decision:** Remove `归属 / 署名声明` and `使用权或许可声明`;
  these are unwanted overhead in this workflow.
- **Verified original blocker:** `SourceOutlinePage.tsx` required both nonblank
  fields in `canSave`; `SourceMaterial` in `source_outline_contracts.py` also
  requires nonempty strings. Leaving them blank currently cannot proceed.
- **Follow-up:** Change the form and underlying source contract together, inspect
  downstream handoff consumers, and record the durable decision. Do not hide
  the fields while fabricating declarations, and do not erase existing values
  merely to remove new-entry requirements.
- **Status:** Implemented in source, not yet deployed or director-verified.
  Both fields are absent from the form and optional in the backend contract;
  no placeholder claims are made. Historical values remain readable and
  survive UI edits. An isolated API test verifies declaration-free Source save
  and a handoff package with null metadata and a no-inference instruction.

## Current checkpoint

The latest screenshot shows the named project in the sidebar and the populated
Brief (30-second target). The director's accompanying phrase about clicking
`保存简报` is ambiguous; the screenshot alone does not verify persistence.
The director has now entered `来源与大纲`; its title and source text are blank.
Source has not been saved. Required declarations conflict with the director's
requested workflow; do not ask for invented declarations to get past this gate.
No generation or creative acceptance is inferred from saving a Brief.

## Isolated implementation checkpoint

The candidate decision is [ADR 0085](../adr/0085-brief-to-source-entry-and-optional-declarations.md).
Checks on isolated projects: 40 focused Python source/cast/art tests passed;
221 frontend unit tests passed; six creator-entry browser tests passed;
and two affected source/Close browser journeys passed. The W01 action-label
follow-up passed an 18-test focused browser batch covering new and saved Brief
behavior, teaching-sample first save, idempotent retry, source entry,
lifecycle, and layout. A production frontend
bundle was staged at `.local/creator-walkthrough/static-candidate/` without
touching the served static directory. The 8841 service and director's project
have not been modified. Independent review found a Brief target mismatch:
Script preparation requires at least three seconds, so the candidate UI now
enforces that lower bound while retaining read compatibility for older stored
Briefs. Manager-controlled deployment and resumed hands-on walkthrough remain
pending.

## Evidence supplied by the director

- Control-height screenshot:
  `/var/folders/ys/g3nd6nfx2xd9wmw053lg109m0000gn/T/codex-clipboard-201d7a11-0afd-4eb2-bd02-0e83e7ef599d.png`
- Populated Brief/sidebar screenshot:
  `/var/folders/ys/g3nd6nfx2xd9wmw053lg109m0000gn/T/codex-clipboard-d8e72985-f423-4377-a2fb-36cbba0a619a.png`
- Empty source fields screenshot:
  `/var/folders/ys/g3nd6nfx2xd9wmw053lg109m0000gn/T/codex-clipboard-a11cf1be-7064-4b16-9120-ef4bf1e58664.png`

These are original temporary screenshot locations, not durable copied artifacts.

## W05 — Complete outline task copying (2026-09-26)

The creator prepared `ch_ee6740b0fa7f4e7b91cc31185bb3e692` for 雨停以后,
then needed external explanation and an extra sentence to execute the handoff.
Requested correction: one-click copy of the entire task, including instructions
to deliver only a candidate and validation evidence, without accepting or
altering confirmed content. Chinese task prose is preferred; technical paths
and identifiers remain unchanged. Inspection also found that assignment text
was held only in page memory and disappeared on reload.

The bounded correction adds complete-task copying and read-only recovery of
the same prepared package; no generation, source edit, or acceptance is included.

Verification: 12 source API/exchange tests and 224 frontend tests passed;
typecheck, deterministic static build and whitespace checks passed. Independent
review found an adjacent unscoped refresh callback; project-session guards were
added and re-review found no remaining blocker in this delta. Playwright CLI
opened the current prepared job in a separate Chromium session, copied the task
successfully, and recovered it after reload. Safari clipboard behavior remains
for the director to verify. The 8841 server was restarted on the same outputs
root; the existing source hash and prepared job identity were retained.

Remaining observation, not fixed by W05: the accepted-outline card says
“候选可审核” while the actual candidate is still prepared/waiting for delivery.
This label must not be taken as evidence that generation has run.

## W06 — Preview unavailable on delivery refresh (2026-09-26)

The director returned with completed outline/report/receipt files and Safari
showed “请求未完成 / Load failed”. Diagnosis: no listener on 8841 and curl
connection refused; the three delivery files existed. This was preview
availability, not an observed delivery-validation rejection. The previously
terminal-owned server was gone; the exact exit cause was not established.

Restarted the same server/root as a detached session (PID 51954, parent PID 1),
without a LaunchAgent or login item. HTTP 200 and project GET passed after the
launcher exited. Log: `.local/creator-walkthrough/server.log`. This is a local
preview mitigation, not automatic restart supervision; durable preview lifecycle
and a more useful disconnected-state message remain follow-ups. Source r1 hash
and prepared job identity were unchanged. No delivery refresh, acceptance or
generation was performed by the manager; the director can retry delivery refresh.

## W07 — Candidate report too small to read (2026-09-26)

Historical checkpoint: inline-preview and script restrictions below were
superseded by the interactive report follow-up at the end of this log.

The director opened the HTML outline report, but its iframe was constrained to
one of three columns and a 320px minimum height. Added “展开阅读大纲” to open
the same sandboxed report in a viewport-sized reading dialog (96vw, capped at
1600px; 94dvh). Closing or Escape returns to the review card; no acceptance
control or mutation is introduced inside the dialog. The existing inline
preview remains available. Focus/readonly/sandbox regression test, typecheck
and static build passed. Chromium measured 1229×677 at a 1280×720 viewport;
Safari verification remains with the director. Report script-block messages
are expected under the unchanged sandbox, not a reason to allow scripts.

## W08 — Inactive report controls and story-format ambiguity (2026-09-26)

The director clicked 明细表 with no result. The delivered report implements
tabs with JavaScript click listeners, while both the report response CSP and
iframe sandbox prohibit scripts. Thus a static-only embedding exposes controls
that cannot work; the larger reader did not resolve this product mismatch.
Proposed correction: a trusted Plotloom reader rendering validated outline data,
with working local display controls; retain the original report as evidence.
Do not simply grant generated report scripts application-origin privileges.

The director also proposed automatic synopsis drafting and optional episode
count. These are discussion items, not implementation approval. Recommend
editable, explicitly adopted synopsis suggestions that never overwrite confirmed
story text; distinguish idea expansion before authoring from summary of an
existing outline. Episode count should apply to a serial format, not every
interactive short. This candidate's params.episodes=2 represents two 15-second
structural segments according to its adaptation.risks explanation, with mutually
exclusive endings in the second segment. “总集数 2” is therefore misleading for
the current single-short intent; do not infer two actual episodes or two endings
from this counter alone.

### W08 implementation checkpoint

Historical implementation, subsequently superseded by the creator-approved
interactive original report. This describes evidence from that earlier candidate,
not the currently served reader.

Implemented the primary reader using admitted outline JSON rather than HTML
scripts ([ADR 0086](../adr/0086-trusted-outline-candidate-reader.md)). Overview
and detail buttons work; complete data including unknown fields is shown as
escaped text. Upstream episodes use neutral structural-entry labels and a
duration/branch interpretation caveat. Original HTML remains sandboxed technical
evidence, explicitly marked as noninteractive. Candidate files were not edited.

Verification: 225 frontend tests, typecheck, deterministic build, whitespace
check and independent delta review passed. Playwright CLI on the retained
candidate checked scrolling at 1440×900, switched to a two-row detail table,
checked 1920×1080, and verified Escape restores focus to 展开阅读大纲.
Screenshot: `output/playwright/trusted-outline-details-1920.png`.
Safari and director usability acceptance remain pending. No model call or
candidate acceptance was performed. Prior walkthrough changes remain in the
same uncommitted worktree; the earlier broad media-draft E2E verification gap
is not closed by these focused reader checks.
## 2026-09-26 interactive report follow-up

Creator approved restoring the original report instead of the generic JSON
reader. The original HTML now runs inline scripts inside an opaque-origin
sandbox; JSON remains the fallback. ADR 0086 records the revised boundary and
residual risks. Downloads remain restricted; no acceptance or generation occurs.

Verification: 225 frontend tests, TypeScript, deterministic build and four
source-outline API tests passed. In headed Chromium, 明细表 became active;
parent-document and localStorage reads raised SecurityError, popup creation
returned null, and API fetch was blocked by CSP. Browser console errors from
these deliberate probes are expected. Safari is not covered by this check.

## Repository cleanup and commit verification — 2026-09-26

Root `output/`, `test-results/` and `.gates.jsonl` are ignored local preview,
browser evidence and gate-log artifacts. Files remain on disk; checked static
assets, tests, ADRs, findings and plans stay versioned. No specialist branch was
merged and no retained project or provider state was changed.

Fresh checks: `uv run --locked pytest -q` passed 764 tests; frontend unit tests
passed 225; app/E2E TypeScript checks, deterministic build, API F401 lint,
lockfile check, wheel build and installed-wheel smoke passed. Changed-flow
browser selection initially passed 28/31: the three media-close tests tried to
edit controls hidden by the current preparation/keyframe disclosures and used
retired stage navigation. Only test interactions were corrected; all eight
close-flow tests then passed, retaining close/reopen/restart and durable-draft
assertions. Together these runs cover all 31 selected cases; the separate
checked-static smoke passed both cases. This closes the previously unclassified
three-case media-close gap, not every unselected E2E journey.

Independent review and follow-up test-delta review found no remaining blocker.
Markdown local link targets and diff whitespace checks passed. Existing build
chunk-size and Starlette/httpx deprecation warnings remain; full browser-suite
and Safari replay were not run. CI remains manually triggered; pushing does not
itself establish remote CI success or creative acceptance.

## Branch-map manual walkthrough — 2026-09-26

- After the creator confirmed outline r1, the branch form still contained
  generic IDs/titles and empty summaries, question and outcomes. The creator
  manually reconstructed the accepted outline using assistant guidance.
  Follow-up: propose an editable branch structure from the confirmed outline,
  with explicit review before saving/installing; do not silently adopt it.
- The creator filled the opening, two mutually exclusive endings and route
  fields. Screenshot evidence shows route 1 points to 赴约 and route 2 to 回家;
  it does not yet establish a saved map or installed graph.
- Layout finding: 后果 is a multiline textarea while 抵达结局 is a dropdown.
  Different heights are appropriate; the creator identifies their side-by-side
  arrangement as a layout choice rather than identical-control sizing failure.
  Review top alignment/field grouping without stretching the dropdown to match
  the textarea. This is a recorded follow-up, not an implemented fix.
- The creator confirmed that the one-choice/two-ending restriction needs
  explicit explanation. It is a current branch-map contract limitation, not
  merely a default UI layout or a general storytelling rule. Near-term UI
  follow-up: disclose this supported structure before branch entry. Future
  scope controls should support configurable branching only alongside matching
  schema, validation and compilation changes (including additional endings,
  successive choices and reconnecting branches). Agreement records direction,
  not authorization to implement that expanded contract during this walkthrough.
