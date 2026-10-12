# Pre-manual walkthrough polish

Status: APPROVED — owner authorized implementation through Relay Direct on
October 11, 2026. One serial worker on the retained Plotloom checkout owns edits.
Baseline inspected: clean main `ea42dba1ab29749e4342b0efd14515860559d0d7`.
The preceding planning pass made documentation changes only. The approval covers
the bounded execution below; it does not broaden the excluded live operations.

## Outcome and evidence

Prepare the next owner-led walkthrough by removing two demonstrated reading/
wording inconsistencies, then performing one bounded revision/currentness check.
This is not another full creative production run or a final-film commission.

The completed [portrait ledger](../verification/2026-10-11-portrait-creator-walkthrough.md)
records that Script candidate reading requires raw JSON and Source's shooting
checkbox differs from the shared graph views. It also explicitly leaves
format-change invalidation unexercised. That last item is an evidence gap, not
a diagnosed current defect. Preserve the completed portrait and landscape
projects, their approvals, settings, originals and selected clips.

## Chosen design

### 1. Readable current Script and candidate review

Provide a product-owned read-only view of the exact Script JSON being reviewed:
chapters, scenes, scene context, actions and speaker/dialogue/delivery in their
stored order. Cover the ready candidate and current/retained accepted version;
reuse the same rendering primitives in the Creator's selected-node reader.

- Identify candidate versus accepted revision versus retained/outdated evidence.
  A candidate is not labelled confirmed or assigned an invented accepted revision.
- Use each displayed object's own frozen binding. Do not infer chapter mapping
  from array position, current graph titles or a different accepted revision.
- Keep original action/dialogue text unchanged. Display authored chapter timing
  as planned footage, not final runtime; mutually exclusive endings are not added.
- Route-only nodes are explicitly identified as controls without filmed scenes.
  Do not fabricate scenes, episodes or footage for them.
- Keep raw JSON available in a secondary technical disclosure, including fields
  not promoted into the readable view. Preserve repeated scene occurrences.
- Missing/ambiguous/incomplete bindings display a clear mismatch with the
  original data inspectable. Never silently drop a bad chapter, guess linkage,
  repair the payload or make reader success an approval/preparation bypass.
- Long text, Chinese content and speaker labels remain readable without clipping.
  Treat content as text, not executable HTML.
- Preserve the independently sandboxed original delivery report. It is historical
  delivery evidence and may differ from the current accepted JSON after edits.
  Do not relabel the original report as the current Script or rewrite its bytes.
- Reading, expanding or closing the view causes no write, acceptance, application,
  generation or dirty-draft transition. Existing JSON section editing and its
  save/reopen/currentness rules remain unchanged.

Reuse `sectionEpisode` and the existing scene presentation where their contracts
fit. Extract cohesive pure/read-only components rather than casting a candidate
to `AcceptedScriptRevision` or adding more responsibilities to `ScriptPanel`.
No new authoring UI, schema/parser compatibility layer or renderer dependency.

Alternatives: relying only on the archived static report would leave later
accepted edits unclear; changing the pinned specialist renderer would disturb
generation and still not establish current accepted authority. Choose the local
read-only reader under [ADR 0064](../adr/0064-f4-section-bound-upstream-script.md),
[ADR 0126](../adr/0126-static-script-report-presentation.md) and
[ADR 0132](../adr/0132-creator-ui-reading-boundaries.md). Amend an existing ADR
only if implementation introduces a durable reading contract beyond this reuse.

### 2. One shooting-checkbox presentation across all views

Use `此节点需要拍摄` and one shared accessible explanation in Source and both
graph views, retaining decision-versus-join playback wording:

- Checked: requires Script scenes, storyboard and video; footage counts toward
  the complete route. Decision footage plays before its question/options; join
  footage plays before continuing.
- Unchecked: route control only, without its own footage.
- Edits remain drafts until confirmed/applied and do not generate media.
- Name step 5/6 for timing/revision/re-review and step 6/6 for affected playback
  checks. The route ceiling does not automatically increase.

Extract the existing label/help presentation into a small shared component or
helper. Keep each owner’s mutation handler, `topologyOrigin`, disable rules,
explicit `footageMode`, exact links and save/confirm/apply authority unchanged.
Only decisions/joins expose the checkbox; no new choice for required footage
roles. Maintain [ADR 0120](../adr/0120-explicit-node-footage-mode.md).

### 3. Bounded revision/currentness exercise

After the UI candidate is stable, establish a fresh, clearly labelled test-only
project in the isolated fixture runtime, with current approved sources and
selected synthetic media. Use current public fixture/UI/API paths, not a raw
copy of either valued project's database or media authority.

Change only the saved aspect ratio from 9:16 to 16:9 through the Brief UI. Capture
the baseline and acknowledged change, then follow the existing owners through
Source, Script, Storyboard, shot media and playback:

- The current Brief persistence conservatively stales canonical stages for an
  aspect-ratio change; explicit section-map head invalidation names structural
  settings instead. Script depends on the graph/review chain, not a direct
  aspect-ratio binding field. Distinguish stored map status, live graph admission
  and downstream review eligibility; do not invent a direct-cause message or
  assume they share one status. Inspect this seam before preparing the probe.
- Before asserting outcomes, enumerate which existing frozen bindings actually
  include the changed Brief setting. Do not demand invented blanket invalidation.
- Affected candidates/reviews/production/media must not be falsely described as
  current or usable. Guidance must name the next real control from known state.
- Old media, decisions and artifacts remain inspectable and byte-preserved;
  changed format must not crop/rewrite a retained original.
- No automatic provider request, new generation, approval or selection occurs.
  Existing independent stages are not falsely promoted by a read or page switch.
- Reload/re-entry retains the truthful invalid state. Changing the setting back
  must not be assumed to restore approvals without the existing contract proving it.

Reuse the fixture lifecycle and selected-media patterns from existing tests;
synthetic transport is not native H3 quality or real creative acceptance.
Stop after preservation, stale/currentness and concrete recovery guidance are
verified. Do not rebuild the full story or regenerate clips to complete this check.
If a defect is demonstrated, preserve evidence and identify its contract owner;
only bounded repairs within this approved outcome continue. Cross-layer/schema/
generation changes require a scope review before implementation.

## Ordered deliverables and relevant files

1. Confirm the actual Script shape/binding and state matrix, then extract the
   reader and add focused regression coverage.
   - `frontend/src/pages/ScriptPanel.tsx`
   - `frontend/src/features/graph/ScriptEpisodeView.tsx`
   - `frontend/src/features/graph/scriptProjection.ts`
   - New cohesive Script reader components beside the existing readers.
2. Extract/reuse filming presentation and apply it to Source.
   - `frontend/src/features/graph/GraphNodeDetails.tsx`
   - `frontend/src/pages/SourceStructureEditor.tsx`
   - Shared six-step references remain authoritative.
3. Inspect supported-desktop reading and perform the isolated revision exercise.
   - `frontend/src/pages/BriefPage.tsx` is an exercised consumer, not a pre-approved
     code-change target.
   - Extend the permanent [lifecycle playbook](../creative-workflow/graph-workbench-acceptance.md)
     only for genuinely missing reusable checks; do not create another checklist.
4. Review the stable candidate independently, qualify proportionately, publish
   under the repository delivery contract, and record one dated verification
   receipt linked here. Then hand off the next owner manual pass.

One implementation/source owner; no parallel writers. A bounded independent
review uses native GPT-6 Luna / Max; escalate only for demonstrated ambiguity.
Implementation coordination uses Relay Direct only after owner approval.

## Acceptance and verification

Observable acceptance:

- A user can review every ready-candidate and accepted chapter's scenes/actions/
  dialogue without reading JSON, while exact raw data remains accessible.
- Candidate, current accepted, edited accepted and retained evidence are visibly
  distinct. Duplicate scene IDs do not collapse separate occurrences; route-only
  controls do not create footage. Missing/read-failed/stale states remain truthful.
- Source/Creator/Professional have the same checkbox name, accessible description
  and decision/join semantics; exact mutation payload and disabled behavior match
  the baseline.
- Reading-only actions produce zero mutating API calls. Existing acceptance,
  section editing/draft recovery and original-report security still work.
- The aspect-revision exercise proves affected eligibility withdrawal and
  preservation without silent generation, and reports any unexercised recovery.
- At 1280×460, 1280×768 and 1700×900, headings, long scenes, disclosures and help
  fit without clipping or horizontal overflow. Mobile editor support is excluded.

Start with the smallest explicit unit/component selections:
`script-projection.test.ts`, the new reader tests, `script-panel-ownership.test.ts`,
`script-workflow-observation.test.ts`, `accepted-review-presentation.test.ts`,
`graph-presentation.test.ts` and focused Source-control coverage. Add assertions
rather than weakening existing checks.

Affected browser regressions include `script-static-report.spec.ts`,
`recommended-script-workflow.spec.ts`, `source-outline-section-map.spec.ts`,
the filming-control cases in `creator-workbench-operations.spec.ts` and
`production-rebuild.spec.ts`. Use the real fixture/backend for writes; choose
the exact additional revision test after binding ownership is established.
`source-review-currentness.spec.ts` and `review-seam-currentness.spec.ts` are
existing upstream-edit guards, not prior aspect-change qualification.
Inspect screenshots directly and preserve state/byte/request evidence.

Review the actual diff against the baseline before claiming bounded frontend
scope. If APIs/payloads, persistence, admission, auth, provider/prompt behavior,
dependencies, package and build contracts remain unchanged, follow
[ADR 0156](../adr/0156-risk-scoped-local-qualification.md): `verify.py quick`
(unfiltered frontend units and both type checks), explicit affected browser
selectors, two serialized deterministic builds with seven-file hash comparison,
supported-desktop pixels and independent review. Regenerate checked static assets.
Do not repeat the full local Python suite for presentation-only work or this
planning document. Material contract changes/uncertain impact trigger the
existing full gate with an explicit reason.

After the final executable revision is stable, perform one separate unfiltered
hosted CI qualification on that exact pushed revision, not an intermediate polish
commit. Check whether equivalent exact-SHA evidence already exists first. CI is
manual-dispatch only; no current-head run is inferred from a push or older green
run. Report local qualification, hosted qualification and owner acceptance separately.

## Authority, operational limits and recovery

The owner approval covers source edits, owned fixture builds/tests, read-only
supported-desktop inspection, the isolated test-project revision, safe publication
and one exact-revision unfiltered CI dispatch. It does not authorize normal8841 restart,
valued-project edits, live provider jobs, staging deletion or an archive retry.

No new paid provider, permissions/security change, data migration or destructive
cleanup. Do not wire Art room/prop references into generation, redesign Script
authoring, repair the leave-ending film or claim human audio review in this scope.
Known artistic/reference limitations remain explicit in the portrait ledger.

For a failed UI candidate, stop promotion, retain the failing evidence and make
a targeted source correction; if already published, use a scoped revert rather
than hard-resetting user work. Never roll back either valued project's data or
copy old approvals to make the revision check pass. Leave the isolated test
project labelled as evidence; no deletion is needed for completion.

Plan completion: this single approved plan is saved and reviewed for handoff.
Implementation completion later requires the acceptance/qualification above,
an honest remaining-gap record, and the preserved manual-walkthrough handoff.
