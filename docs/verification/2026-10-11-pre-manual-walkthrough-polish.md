# Pre-manual walkthrough polish receipt

Plan: [approved walkthrough polish](../roadmap/2026-10-11-pre-manual-walkthrough-polish.md).
Baseline: `ea42dba1ab29749e4342b0efd14515860559d0d7` on retained `main`.
Status: implementation, local verification, independent review, and the
ownership-manifest follow-up are complete. The browser locator-contract repair
has passed the manager's attended independent review with no remaining
actionable findings and is ready to commit. This receipt does not claim owner
product acceptance or exact-SHA hosted qualification for that repair.

## Root cause and bounded change

The portrait walkthrough found two presentation inconsistencies. A ready Script
candidate had no product-owned readable view of its complete chapters, and the
Creator's selected-node reader showed only one chapter through a different
presentation. Source also duplicated the filming checkbox/help markup used by
the two graph views. The durable fix belongs in the frontend reading layer:
reuse `sectionEpisode` and each object's frozen binding in a shared read-only
Script renderer, and use one accessible checkbox/help component while leaving
each owner's change handler and draft/confirm/apply controls in place.

The independent review also found that the selected-node and full accepted
Script regions shared an accessible name in the same panel. The selected-node
reader now includes its section in the name, with a regression assertion that
both labels coexist distinctly.

Candidate, current accepted, edited accepted, and retained evidence remain
distinct. The reader preserves stored text and repeated scene occurrences,
labels planned timing, identifies route-only nodes without inventing footage,
and exposes the raw binding and JSON. The original sandboxed report remains
historical evidence. Component/browser checks observed no write from reading,
viewport changes, or disclosure expansion.

No backend/API schema or payload, persistence, admission, auth, provider/prompt,
dependency, build-tool, or package contract changed. The revision exercise used
the existing fixture API and visible Brief UI; it did not modify either valued
project or send a provider request.

## Aspect-ratio revision evidence

Isolated fixture project `3288486e-7459-4ebb-b1ef-127632258b46` began at 9:16
with current accepted Source, Cast, Art, Script, Storyboard-source review and
canonical stages; one synthetic selected video and segment were also current.
Saving 16:9 through Brief advanced the project revision from 1 to 2.

- The accepted section map stayed current with the same SHA-256
  `c5d8e04eecf7358079c55834529b63a1185c468830ee5898bd6b9cb1c76d54db`; live
  graph admission became stale because the canonical graph was stale.
- Cast and Art became stale through installed-graph currentness; Script became
  stale through accepted Art; storyboard-source review became stale through
  accepted Script. All four canonical heads remained at revision 1 and reported
  the changed Brief dependency.
- The shot approval was withdrawn from active use while its decision record
  remained inspectable. The ingested video remained retained with stale inputs,
  ineligible/current/selected all false. Its segment remained preview-eligible
  but stale and unselected; selected playback returned 404.
- Original video bytes remained SHA-256
  `fa1ae74f35cd0dbfb22a9195003c275e550ad6cd7f3d1380264b4ef8e79cb1f3`; segment
  bytes remained SHA-256
  `9db2ca070c77bec620130338cb4494bb1a7058aa99c66d8e708349b11810eb49`. Their
  retained preview endpoints remained readable, and reload preserved the stale
  state and both hashes.
- Captured Brief writes were only `PUT /authoring-drafts` and `PATCH /projects`.
  No review, video, segment, keyframe, acceptance, selection, or generation
  mutation occurred during the ratio edit.
- Source showed its existing `应用到故事路线` action as available. Script
  directed the user back to Art before preparing again; Storyboard directed the
  user back to Script. No recovery action, ratio revert, approval replay, or
  regeneration was run, so no recovery outcome is inferred.

Full API snapshots, recovery-page text/control state, and hashes are preserved
at `/tmp/plotloom-pre-manual-walkthrough-2026-10-11/plotloom-e2e-bKB4bc/evidence/aspect-ratio-currentness.json`.
Fifteen supported-desktop captures are preserved at
`/tmp/plotloom-pre-manual-walkthrough-2026-10-11/evidence/ui-screenshots/`.
The isolated fixture root is `/tmp/plotloom-pre-manual-walkthrough-2026-10-11/plotloom-e2e-bKB4bc`.

## Local qualification

- Focused Vitest: 8 selected files, 54 tests passed (`script-projection`,
  `script-content-review`, `script-panel-ownership`,
  `script-workflow-observation`, `accepted-review-presentation`,
  `graph-presentation`, `section-map-panel-actions`,
  `recommended-script-workflow`). After the accessibility-name repair,
  `accepted-review-presentation.test.ts` passed 7/7 tests.
- `uv run --locked --no-sync python scripts/verify.py quick`: passed; 150 files,
  1,274 tests, frontend typecheck and e2e typecheck. Lock check and API unused
  import check also passed. Quick explicitly does not cover backend integration,
  browser, archived-reader, bundle parity, wheel, or installed-wheel gates.
- Six affected browser specs passed 13 tests: Script static report, recommended
  Script workflow, Source section map, Creator workbench filming controls,
  production rebuild, and aspect-ratio currentness. After refining only the
  Source screenshot scroll position to avoid the sticky workflow banner, the
  Source spec and e2e typecheck passed again (1 test).
- Two serialized `npm --prefix frontend run build:deterministic` builds passed.
  Their sorted SHA-256 manifests matched for all seven files under
  `src/plotloom/static/`; manifests are preserved at
  `/tmp/plotloom-static-final-first.sha256` and
  `/tmp/plotloom-static-final-second.sha256`. The rebuilt `workbench.js` hash is
  `5c0e0a7d43ad4eb68d17ed324a8fdba3923ffa223ab5fe17ffdd32cae807deac`. Vite
  reported its existing large-chunk advisory; both builds succeeded.
- Direct pixel inspection covered Script candidate, Source help, Creator and
  Professional help, and stale Script guidance at 1280×460, 1280×768, and
  1700×900. The revised Source captures show the full checkbox below sticky
  chrome. Text wraps, disclosures remain available, and no horizontal overflow
  or clipping was observed; long Script views remain vertically scrollable.

Independent read-only review: GPT-6 Luna / Max. One concrete duplicate-name
finding was fixed and covered as above; no other actionable findings. Reviewer
made no edits and ran no tests.

## Remaining gates and preservation

This is scoped local frontend qualification, not full local release qualification
or product acceptance. The owner-led manual walkthrough and manager-owned exact-
revision push/hosted-CI decision remain separate. No push or hosted CI run was
performed here. The portrait and landscape projects, settings, approvals,
originals, and selected clips were not accessed or changed. The test-only
project and synthetic media remain labelled at the local fixture path above.

Implementation and generated-asset checkpoint: `ddec07ce16ae7937e51e21981273f3f164fed68a`.
The ownership-manifest follow-up in this receipt is included in the current
checkpoint.

## Ownership-manifest follow-up

The manager's pre-publication check found two missing exact-file owners and an
unassigned browser spec. The native ownership guard maps each test source file
once and then compares the complete native case union; the browser allocation
guard separately requires every whole spec to appear in exactly one shard.
The quick and explicitly selected test runs used for the implementation do not
run these two collection guards, so their success did not establish manifest
coverage.

Added `script-content-review.test.ts` to the `creative-production` Vitest owner
and `aspect-ratio-currentness.spec.ts` to the `story-authoring` Playwright owner.
The aspect-ratio journey is owned by Story Authoring because it changes the
Brief's aspect ratio and verifies its downstream currentness consequences.
Assigned the whole new browser spec to shard 2, the smallest current allocation
at 70 of 296 collected cases; the other groups have 84, 71, and 71. The new
spec adds one case, bringing all four groups to 71–84. No existing spec
assignment changed.

The edited aspect-ratio spec imports `frontend/e2e/f5a-fixture.ts`; that shared
fixture dependency already lists `story-authoring` among its consumers. The new
Script component unit test imports no shared test fixture. No support-dependency
consumer set needed to change.

Collection-only verification: `uv run --locked --no-sync python
scripts/testing/check_module_ownership.py` passed with the complete native
pytest/Vitest/Playwright case union and no test bodies executed: 1,542 pytest
cases across 158 files, 1,274 Vitest cases across 150 files, and 297 Playwright
cases across 90 files. The unfiltered browser shard allocation guard
(`BROWSER_GREP='.*' node scripts/check_browser_shard_manifest.mjs`, from
`frontend/`) also passed with all 90 specs and 297 cases assigned once, zero
overlap or missing cases, and shard case counts 84/71/71/71. These are
collection results, not a browser runtime run or hosted qualification.

## Browser locator-contract correction

The original hosted run [38190104589](https://github.com/Wenjun-Mao/plotloom/actions/runs/38190104589)
failed at exact SHA `7c2718b4969c9da9483eb9af0f9fbe2e84f15f25`. `verify` and
browser shards 1 and 2 passed; browser shards 3 and 4 failed in the browser
regression step. Browser 3 had four failures in
`source-review-currentness.spec.ts`: two used a retired Script disclosure
label, and two selected both an outer retained-draft region and its nested
reader because the accessible-name match was not exact. Browser 4 had one
failure in `creator-workbench-story.spec.ts`: a panel-wide occurrence count
expected two selected-node scenes but included six scenes from both the
selected-node and whole-Script readers.

The local reproduction used
`npm --prefix frontend run test:e2e -- --workers=1 e2e/source-review-currentness.spec.ts e2e/creator-workbench-story.spec.ts`
and reproduced those locator-contract failures. The application behavior was
correct: the reader now exposes an object-specific frozen-binding/raw-JSON
disclosure and distinct nested regions. The repair targets the exact accepted
reader and disclosure, makes the retained-draft accessible-name match exact,
and scopes selected-node versus whole-Script occurrence counts separately.

After those changes, the two complete specs passed: 17 cases total (14 in
`source-review-currentness.spec.ts`, three in
`creator-workbench-story.spec.ts`) in 63.321 seconds, exit code 0. The
`test:e2e` command also completed its E2E TypeScript check. This full run was
before the reviewer refinement below; its source-review spec and the two
unchanged Creator cases remain applicable to the current diff.

The attended reviewer found one remaining coverage gap: clicking each selected
scene's first summary opened raw scene JSON, so subsequent text checks could
pass without proving that readable action/dialogue text rendered. The test now
leaves those disclosures closed and checks the exact ordered visible flow text
inside each selected-node occurrence using `data-flow-order`, deriving the
expected arrays from the accepted opening episode. It retains the original
“One cable. Two places need it.” and cable-across-the-desk assertions at their
specific scene and flow positions. The latest targeted run,
`npm --prefix frontend run test:e2e -- --workers=1 e2e/creator-workbench-story.spec.ts --grep "node Story retains every scene"`,
completed its E2E TypeScript check successfully before Playwright. Playwright's
summary was `1 passed (4.7s)`; the full command exited 0 in 6.576 seconds. The
latest Playwright `.last-run.json` records `status: passed`. The manager's
attended independent follow-up review found no remaining actionable findings.

The prior exact-SHA hosted run does not qualify the corrected test candidate.
No hosted CI was dispatched. The reviewed test-only correction and this receipt
are ready for the scoped checkpoint commit.
