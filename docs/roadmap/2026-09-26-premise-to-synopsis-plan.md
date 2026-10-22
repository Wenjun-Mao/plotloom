# Premise to editable synopsis — proposed next slice

Status: assessment complete; proposal for creator review, not implementation approval.
Baseline: `d81389d` plus the retained, uncommitted walkthrough corrections.
Authority: [MVP milestones](2026-09-17-playable-mvp-milestones.md).
Observed needs: [walkthrough findings](../verification/2026-09-25-manual-creator-walkthrough-findings.md).

## Outcome and stopping condition

A creator with an idea, but no synopsis, can ask for one editable synopsis,
review it, and explicitly place it into the Brief draft. Nothing creates an
accepted source, outline, graph, script, shot or media asset automatically.
The current 雨停以后 project is not a migration or test fixture for this feature.

This planning assignment stops at a reviewed proposal. No runtime changes,
provider calls, project acceptance, service restart or automatic dispatch.

## Findings from the current implementation

| Area | Current fact | Design consequence |
|---|---|---|
| Brief entry | `BriefPage.tsx` requires nonblank synopsis to save; new projects save and continue to an editable source draft (ADR 0085). | Assistance must work before a saved project exists, without saving the premise as a fake completed synopsis. |
| Old proposal | `useRunCommands.ts:startProposal` requests canonical Bible/Graph stages (ADR 0053). | Do not relabel or invoke it for synopsis-only assistance. |
| Text transport | `generation/providers.py` provides a one-attempt adapter; bridge-intent service demonstrates prompt/schema, profile, secrets and durable unknown-outcome handling. | Reuse these lower-level boundaries, not the bridge's project/review ownership or its tables. |
| Manual creative exchange | `creative_handoff_contracts.py` supports outline, characters, art, script, storyboard. Exchange pins a `novel-{stage}` upstream skill. | Synopsis is not an existing handoff stage; adding a name alone is insufficient. |
| Planning fields | `domain.py:ProjectBrief` stores route-duration and topology targets, but no story-format or episode-count field. | Reuse the duration authority; do not imply every Brief topology control governs F1B, whose admission overrides decision/ending/join counts for its fixed binary shape. New story-format semantics need an explicit decision. |
| Source-first branches | `source_outline_contracts.py:SectionMap` requires three sections, one binary choice and two distinct endings. | Arbitrary depth/branch controls and series production are not supported by this route today. |
| Outline inputs | `project_folder_source_outline.py` freezes source material with empty input artifacts, not structured Brief scope. | Scope controls will not reliably constrain this handoff merely by existing in the Brief UI. Any new projection needs explicit binding/currentness. |
| Timing | `persistence/project/script.py` binds Brief target and graph-derived timing allocation; each complete route is capped. | Do not equate source outline `episodes × minutesPerEpisode` with playable route duration. |

## Proposed creator experience

1. Brief offers `自己写梗概` and `帮我写梗概`; manual entry remains fully usable.
2. Assistance asks for `故事想法` (required), plus existing language, genre,
   visual style and target duration. Optional constraints can describe what to
   preserve or avoid. No reviewer name, license declaration or technical job IDs.
3. `生成梗概草稿` starts exactly one text request with visible working/error state.
   Missing/disabled provider configuration leads to settings, not a fallback.
4. Show one editable result beside or above the retained input. Call it a draft,
   never an accepted story. `采用到简报` changes only the local Brief synopsis;
   preserve the author's title and all unrelated fields. Allow discard.
5. Existing explicit save/continue and source confirmation remain separate.
   For an existing project, applying the draft must not save or invalidate stages
   until the creator explicitly saves the Brief through the established path.

Candidate editing belongs to the creator. A model returns synopsis text only;
trusted code owns identity, input digest, response validation, request state and
application guards. Do not ask the model to invent approval, topology IDs,
durations, rights, jobs, or provenance. Preserve entered constraints as input;
avoid promising that schema validation proves creative fidelity.

## Scope-setting proposal and honest limits

- Reuse `targetPlaythroughSeconds`: an author-owned hard upper bound on each
  complete path in downstream production, not a promised delivered runtime,
  padding requirement or per-clip generation setting (ADR 0018).
- First supported source-first production shape remains one interactive short,
  one choice and two endings. Show that plainly instead of exposing misleading
  arbitrary branch controls on this path. Other existing workflow controls need
  not be deleted as part of this slice.
- Standalone versus series and optional total episodes are valid next needs,
  but **series production is not a supported small UI-only addition**. Recommend
  deferring selectable series scope until episode ownership, per-episode route
  duration and source-map generalization have an approved contract.
- An alternative is to allow series preferences for synopsis writing only,
  explicitly labelling downstream support unavailable. This adds a dead end;
  not recommended for the first end-to-end slice.
- Do not turn the current two upstream outline entries into two canonical
  episodes. Do not infer branch count from episode count or vice versa.

Creator decision before implementation: approve the short-only first slice,
or prioritize series support as a separately scoped contract expansion. This is
a recommendation, not a silently approved reduction of the requested options.

## Execution options

| Option | Benefit | Cost / limitation |
|---|---|---|
| Direct configured text adapter (recommended) | One action, no copy/paste; directly addresses writer's block. | Needs bounded pre-project job ownership, recovery and safe application. |
| New manual synopsis handoff | Familiar local specialist workflow. | New stage/pin/schema still required; repeats the copy/paste friction. |
| Existing Bible/Graph proposal | Already callable. | Wrong output and write boundary; reject for this feature. |

Recommended pre-project design: an application-local authoring-session identity
owns a bounded synopsis job, separate from canonical project records. Freeze the
premise, settings and input digest; retain output/provenance for recovery and
later linkage without requiring a placeholder project. Reuse current draft and
secret-management conventions where their lifetimes fit. Define retention and
explicit discard before shipping; never copy credentials into drafts or jobs.
This is a proposed new contract, not a claim that this owner already exists.

Current `draft-registry.ts` uses `sessionStorage` with a private unsaved owner;
durable authoring-draft routes in `api/project_folder.py` require a project ID.
That combination is not an established pre-project job/reopen recovery owner.
The client draft owner is only a namespace, not an authorization credential.
The proposed durable owner must define an opaque recovery/access capability,
its browser retention, revocation and discard behavior, and avoid leaking that
capability through URLs/logs. Do not mistake provider credentials for draft access.
Before committing to this design, resolve owner/storage/API, browser recovery
identity and retention in one concise ADR; verify tab-close/reopen behavior. Do not
invent a general-purpose workflow engine or bolt pre-project jobs onto bridge
intent records. Keep the service and UI modules cohesive rather than expanding
the already large workspace controller with job logic.

## Delivery order and acceptance checklist

Likely integration points: `frontend/src/pages/BriefPage.tsx` (entry), a focused
new assistance component/hook rather than embedding orchestration there,
`frontend/src/draft-registry.ts` (draft conventions), `frontend/src/api.ts`,
`src/plotloom/generation/{providers,contracts,prompts}.py` (shared text boundary),
and an explicitly owned new job contract/service/storage surface. Changes to
`ProjectBrief`, source-outline preparation and currentness are conditional on
the approved scope projection, not automatically part of synopsis assistance.

Existing regression anchors: `frontend/tests/draft-registry.test.ts`,
`frontend/e2e/manual-creator-entry.spec.ts`,
`frontend/e2e/project-folder-authoring-drafts.spec.ts`,
`frontend/e2e/synopsis-proposal.spec.ts`, `tests/generation/test_providers.py`,
and `tests/test_project_storage_source_outline_api.py`. Bridge-intent tests are
a reference for failure semantics, not a reason to reuse its domain owner.

1. **Contract checkpoint before code**
   - [ ] Creator confirms supported first-slice scope and execution option.
   - [ ] ADR specifies input/output ownership, pre-project persistence, expiry/
     discard, cancellation and unknown dispatch, and downstream scope binding.
   - [ ] Specify execution ownership: the adapter is synchronous and one-attempt;
     existing generation runs/scheduling are project-bound. Choose a bounded
     synopsis executor and define server-restart recovery before writing code.
     Request-scoped session API keys cannot be durably stored for redispatch;
     interrupted dispatched work becomes unknown unless completion is evidenced.
     Reload/reopen recovers job state, not an implicit permission to resubmit.
   - [ ] Define recovery-capability issuance/storage/revocation and local-server
     threat boundary. An arbitrary client owner ID is not authorization.
   - [ ] Decide whether structured scope forwarding to outline is included;
     if included, bind it explicitly and test stale candidates. Otherwise do not
     advertise the new preferences as enforced outline-production controls.
2. **One candidate-only request**
   - [ ] Render one bounded prompt + schema through the existing text boundary.
   - [ ] Validate nonempty bounded synopsis text; reject malformed/secret-bearing
     output without replacing existing text. No hidden correction/retry loop.
   - [ ] Freeze provider profile and use existing secret leases, safe error
     classes and usage evidence when available. Uncertain dispatch is not retried.
3. **Draft review and recovery**
   - [ ] Manual mode remains unchanged; configured assistance can run before save.
   - [ ] Late results cannot overwrite edits, a different project, or newer input.
     Older results may remain inspectable, labelled with their original input.
   - [ ] Explicit apply updates synopsis only; explicit discard preserves manual text.
   - [ ] Reload/tab reopen has documented recovery; request identity avoids duplicate
     submissions. Cancellation cannot falsely promise to stop remote computation.
4. **Verify, then creator walkthrough**
   - [ ] Unit/API tests: malformed output, empty input, provider unavailable,
     not-sent versus unknown outcome, double click, cancellation, late response,
     changed input, cross-session access and secrets excluded from persistence.
     Include unauthorized/revoked recovery capabilities and restart after dispatch
     with a session-only provider key; neither may cause a hidden repeat request.
   - [ ] Browser: blank project → idea → fake-provider candidate → edit → apply →
     explicit save → source draft; no accepted source or downstream stages created.
   - [ ] Existing project: apply without save leaves canonical revisions/currentness
     unchanged; save follows existing invalidation. Failed apply preserves text.
   - [ ] Manual path, source entry, existing proposal and draft recovery regressions.
   - [ ] Typecheck, deterministic static build, focused backend/frontend tests,
     independent review and real browser flow; Safari creator acceptance separate.
   - [ ] Live generation, if later authorized, is one bounded text trial; no media.

## Report findings to keep separate from synopsis implementation

| Finding | Verified meaning / root cause | Proposed follow-up |
|---|---|---|
| Grey S01/C01 tags | Scene/character references, not disabled state. | Names plus IDs or accessible descriptions and a legend. |
| Red 雨戏 | Upstream `/雨/` rule requires warning even for 雨停后. | Label heuristic reminders honestly; assess upstream rule change separately from H3 capability research. |
| Scene colour blocks | Position = upstream entry; grey absent; dark red primary present; orange non-primary present. | Label positions and explain colours; never imply branch-specific coverage. |
| 第1集/第2集 | Upstream organizational entries in this candidate, not actual two-episode intent. | Decide canonical story-format ownership before changing mappings; keep host caveat meanwhile. |
| Original report interaction | Creator observed working 明细表 after sandboxed script restoration. | Preserve report bytes; avoid renewed generic-reader replacement. Safari interaction acceptance still separate. |

Do not bundle these into an unrequested report redesign. All are captured in
the running findings; report markup, scripts and candidate remain unchanged here.

## Re-entry point when the creator returns

Continue reviewing current 雨停以后. Only the creator clicks acceptance. After
acceptance, inspect the branch-map screen together: shared opening → 赴约 / 回家
→ separate endings. This plan does not pre-fill, accept or install that map.

## Assessment verification

Independent GPT-5.6 Terra review found four material clarifications: fixed F1B
topology versus Brief targets, hard-cap duration wording, pre-project execution/
restart ownership, and recovery access distinct from a client draft namespace.
All were incorporated and confirmed closed on re-review. Local Markdown link
targets (48 across the plan and linked tracking documents) and `git diff --check`
passed. No runtime tests were needed or run for this documentation-only change.
No UI, service, provider or retained project state was changed. This is not
feature implementation, product acceptance, or permission to begin generation.
