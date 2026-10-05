# Creator UI batch for the next walkthrough

Status: **implementation in progress; owner approved Brief-driven topology expansion before qualification**.
Approved October 4, 2026, Toronto time. Baseline: retained clean `main` at
`a5f353835b9d6e6834da862205d89925ae1e17bf`.

The owner has approved implementing the accumulated creator-UI batch through
Relay Direct before starting a new-project walkthrough. Normal-service downtime
and direct installation work are permitted. This is a new assignment, not a
reopening of the completed first UI-polish pass or six contract repairs.
There is no new time budget or unattended Goal specified.

## Outcome

A creator can start a new project and follow the existing supported journey
without developer narration or manually reconstructing choices already present
in the outline. At every stage, the UI makes the current task, result, required
review, next action and recovery path understandable. Existing acceptable media
and the dark visual direction remain; final-film quality is not the target.

The agreed observations and examples are in the manager's local
`.local/creator-ux-batch-2026-10-04/notes.md`. This tracked plan now owns the
approved scope and progress. The prior
[UI-polish plan](2026-10-03-creator-ui-polish.md) records already completed work;
do not count those fixes again. The
[contract-repair receipt](../verification/2026-10-04-current-contract-repairs.md)
records the activated safety and recovery baseline.

## Scope and observable requirements

### Brief presets

Offer grouped multi-select presets for 类型 and 视觉风格, visible removable
selections, custom additions and optional detail text. A small useful starting
vocabulary is sufficient: distinguish subject/background from narrative genre,
and representation from art treatment and color/light. Preserve optionality and
intentional mixing; do not silently choose or overwrite a main style.

Selections, custom text and details must survive saving and reopening and reach
the relevant story/visual generation inputs consistently. Diagnose the current
nullable text fields and consumers before choosing a minimal durable contract.
Do not reverse-engineer selections through brittle text splitting or discard
existing user-authored free text. No global preset administration is requested.

### Assistant waiting and result recovery

Build on the existing shared result-check mechanism, which already polls under
certain conditions. Show a persistent accessible waiting indicator, accurate
task title, last successful check and secondary manual check. Queue acknowledgement
is not proof of active execution; unknown dispatch must remain explicit.

Use sequential checks, bounded transient-error backoff, and clear actionable
integrity/identity errors. Isolate late responses across project/task changes,
throttle hidden pages and refresh safely on return. Delivery should become ready
for review without manual checking; it must never become automatically accepted.
Do not duplicate sends or release native reservations through cancellation,
timeouts or apparent inactivity. Cover the shared outline, character, art, script
and storyboard actions first; inspect other controllers for presentation
consistency without inventing a unified generation backend.

### Outline reading and revision intent

Keep a large readable report entry permanently available on the accepted outline,
bound to that accepted revision and its original candidate. Preparing or
cancelling another candidate must not remove it. Label accepted versus candidate
reports correctly. Retain report sandboxing and a read-only structured fallback
when the exact accepted version has no HTML report.

Replace the misleading 重新打开，不替换内容 wording with controls that explain
reading versus starting another revision/generation cycle. Resolve the return
path after an accidentally started revision so retained valid content remains
usable through an explicit, revision-checked action. Cancelling a task alone
must not be presented as undoing the revision or stopping native execution.
This batch does not authorize a new direct outline editor or a separate
assistant-feedback editing workflow; do not show controls implying those exist.

### Proposed branches rather than empty route forms

Provide a complete editable draft from the accepted outline: all code-planned story nodes, playback questions, option labels, subsequent story and target links.
The creator reviews, optionally edits and explicitly confirms it. Manual entry
remains an option, not the mandatory default path. Existing accepted outlines
must have a supported way to obtain the draft without regenerating the whole
outline. Do not overwrite an existing map or unsaved local edits.

Use a validated structured suggestion contract, not prose splitting, hardcoded
sample text or treating upstream episodes as executable route nodes. The worker
may choose an integrated structured delivery or a dedicated native suggestion
task after checking prompt, schema, binder and validator ownership. Document
that decision before changing the contract. Model-authored suggestions remain
advisory; trusted code owns identity/currentness/topology validation and the
creator owns adoption. Keep explicit sending and confirmation and frozen inputs.
Ambiguity must produce an understandable proposal or focused clarification,
not a silent route installation or unexplained blank form.

Present this as 剧情分支与结局, explaining that viewers choose the protagonist's
next action during playback. Use clear labels such as 播放时显示的问题,
选项 A／B, 选择后的剧情 and 对应结局. Manage internal IDs automatically and keep
them in technical details. The October 4 owner update supersedes the binary pilot limit: Brief structural settings own the complete Source workflow, including multiple decisions, variable options/endings and requested reconvergence where feasible. Plan topology before binding prose, using the trusted graph planner; reject infeasible combinations without altering them. Count actual viewer choices along each complete playthrough. Label choice buttons 选项 and whole start-to-ending journeys 播放路线. Add accessible Chinese hover/focus/tap help for these settings.

### Consistency through the remaining journey

Continue through characters, art/references, script, storyboard, production
handoff, media review, reader and player. Fix demonstrated next-step ambiguity,
Chinese wording and presentation inconsistencies in their owning views/shared
primitives. Audit typography beyond the earlier 每场分镜 example: equivalent
roles should share a readable scale; technical and narrative exceptions may be
intentional. Check card spacing and enabled, disabled, busy and destructive
actions, with visible unavailable reasons and keyboard focus.

This is a bounded journey improvement, not a new wizard, rebrand or wholesale
application rewrite. Preserve already delivered Home, lifecycle, required-marker,
spacing and safety behavior. Do not rewrite story content as UI copy cleanup.

## Sequence and source ownership

1. Capture the current installation/project preservation baseline and a concise
   journey finding list. Identify author/model/trusted-code ownership for the
   preset and branch contracts before implementing them.
2. Implement Brief presets and their end-to-end input contract.
3. Implement shared waiting/check/recovery feedback.
4. Complete accepted-report access, revision/return clarity and the structured
   outline-to-branch review path.
5. Finish the later-stage consistency pass and a fresh-project browser walkthrough.
6. Obtain independent review on a stable candidate, address concrete in-scope
   findings, qualify release gates, publish and activate the normal installation.

Use one retained-checkout source owner. The manager does not edit while the
worker writes. Read-only review can proceed on a stable candidate; reviewers
must not change source. Update this plan with actual progress and evidence, not
additional overlapping plans. A material scope expansion requires an owner
decision; engineering choices within the approved outcomes belong to the worker.

Entrypoints include `BriefPage.tsx`, `SourceOutlinePage.tsx`, `OutlineReport.tsx`,
`SectionMapPanel.tsx`, `features/specialists/SpecialistTaskActions.tsx`, their
project API/persistence/prompt/schema owners, shared controls/scoped styles,
stage guidance and downstream reader/player consumers. Follow existing module
boundaries and split oversized responsibilities when extending them.

## Verification and installation

- Cover preset round-trip/custom text and downstream inputs; polling to delivery,
  transient recovery, integrity rejection and late responses; accepted reports
  after acceptance/new candidates/cancellation/reload; revision return; branch
  draft generation, explicit adoption, stale basis and dirty-map protection.
- Verify a fresh-project path and both current route outcomes with disposable
  fixtures. Deterministic transport proves integration, not live model quality.
  If a bounded live native-text fixture is needed, identify its scope and actual
  evidence; do not use owner projects or silently accept their content.
- Check desktop 1440 and 1920 widths, compact 1280 and a narrow-screen smoke
  case. Include normal, waiting, error, empty, accepted, stale and dirty states;
  verify keyboard access, reduced-motion behavior and dialogs.
- Run focused checks, then the established full unfiltered local release gate
  on the final candidate, with fresh bundled frontend assets. Do not weaken or
  skip supported tests to obtain a pass. Record exact revisions and CI status.
- Before service interruption, check project-specific native ownership and
  preserve active/uncertain work. Use the supported creator-workbench lifecycle
  commands. Downtime does not authorize cancelling jobs, deleting projects,
  resetting current assets, replacing credentials or disturbing the 8851 copy.
- Preserve normal projects 雨停以后 and 风里的纸飞机, accepted revisions, media,
  settings and drafts. Capture and compare current state around activation;
  separate intentional schema changes from unintended loss. Do not rewrite old
  evidence to make it appear compliant with a new generation contract.
- Publish verified scoped changes on `main` without force-pushing. Activate and
  verify normal 8841 before the handoff; retain existing H3 configuration. Record
  implementation, executed checks, activation and remaining human acceptance
  separately in a concise verification receipt linked here and from the index.

## Exclusions and completion

Do not update the Chinese Creator's Manual yet. Relay documentation duplication
is a separate captured follow-up. Full project cloning, self-service recovery
redesign, production replacement after installation,
new paid providers and final-film polishing are not part of this batch.

Stop with a reviewed, verified, published and activated candidate satisfying all
required scope, ready for the owner's new walkthrough. If a required item is
blocked, report the concrete authority/contract gap and completed versus pending
work rather than claiming the batch complete. Human usability acceptance occurs
when the owner tries the new walkthrough; test counts alone do not establish it.

## Progress

- Manager consolidated the approved observations and boundaries into this plan.
- Worker registered Relay route and captured both normal projects; no unresolved native ownership; normal 8841 stopped through the supported lifecycle. 8851 remains untouched.
- Implemented structured Brief directions, sequential assistant checks, accepted-report reading and explicit revision return; focused frontend checks passed. Branch advisory task first drafted under the original binary scope; now being extended before qualification.
- Owner authorized the deeper Brief-driven topology contract, variable options/endings, multiple decisions, reconvergence and accessible setting help. The earlier binary limitation and broader-topology exclusion are superseded for this flow. ADR 0118 owns the extension; retained accepted evidence and installed production are preserved.
- Added visible same-project Brief navigation and draft-gated return to Source. Structural edits preserve confirmed source/outline evidence while invalidating dependent proposals; the fresh-project browser checks cover editing settings, stale rejection and a new frozen proposal.
- Independent review found implicit continuation forks and a receiving-capacity mismatch. Planner v2 makes each viewer choice explicit and searches within the receiving option bound without rewriting author settings. Focused topology, branch and full downstream integration checks pass.
- V1 剧情树 was investigated read-only by the manager as a product reference: zoom/pan/fullscreen, node/media details, shot expansion and display-only dragging. Its useful taste is a shared spatial overview of reconvergence. Existing Plotloom canonical GraphPage already has graph navigation; reader route cards repeat shared nodes. Open follow-up: whether a creator-facing overview should reuse the accepted canonical graph. This reference does not authorize a new graph editor in this batch or production imports from V1.
- Full release gates, independent stable review, publication and activation remain pending.
