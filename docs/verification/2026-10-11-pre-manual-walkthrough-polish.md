# Pre-manual walkthrough polish receipt

Plan: [approved walkthrough polish](../roadmap/2026-10-11-pre-manual-walkthrough-polish.md).
Baseline: `ea42dba1ab29749e4342b0efd14515860559d0d7` on retained `main`.
Status: local implementation qualification and independent review are complete;
checkpoint commit is pending. This receipt does not claim owner product
acceptance or hosted qualification.

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

Checkpoint revision: pending commit.
