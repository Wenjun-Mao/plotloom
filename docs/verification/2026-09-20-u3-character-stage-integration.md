# U3 Characters-stage integration — technical verification receipt

Date: 2026-09-20. Scope: accepted cast text review and F2B image-reference
review only. This is technical evidence, not creative approval or the pending
attended creator-usability acceptance.

## Root cause and delivered boundary

The standalone gallery made image comparison readable but gave the creator no
coherent task because its selection/refinement decisions were elsewhere. The
new `stage=characters` workspace entry keeps F2A cast review and the reused
image-first F2B view in one hierarchy. It retires the standalone gallery route,
its duplicate creator navigation and `CastReferenceStudiesPanel`; it does not
change the API, schema, asset, proposal, decision, Art, screenplay, storyboard
or Play owners.

Viewing calls only GET owners. Explicit image-adjacent controls retain existing
selection CAS/reviewer/notes and prepare/copy/refresh/cancel requests. Prepare
is a manual handoff, not provider dispatch. Stale/reopened cast disables new
work while retaining evidence, and selected/current candidate/historical/missing
and failed states remain differentiated.

## Executed checks

- `npm test` — 19 files / 169 tests passed.
- `npm run typecheck` and `npm run typecheck:e2e` — passed.
- `npx playwright test e2e/cast-reference-studies.spec.ts --config playwright.config.ts`
  — 4 production FastAPI/file-SQLite scenarios passed: original → refinement →
  selection across reload/restart; prepare/export/cancel and late inapplicable
  delivery; stale cast and held operation ownership; delayed project-read
  invalidation.
- `npm run build:deterministic` and `git diff --exit-code -- src/plotloom/static`
  — passed; built frontend assets are fresh.

## Walkthrough environment

A separate H3-disabled production service is retained at
`http://127.0.0.1:49072/v2/`, using only
`.local/relay/ef469f97-f8f0-4cf0-8d63-6b67e4c9638a/characters-walkthrough/`
for application data and outputs. Fixture project
`e31b1149-edb6-4611-b76c-accd4210fc22` was created through the production API,
then uses a labelled retained P0 raster as its selected technical reference and
a prepared-then-cancelled refinement. It visibly demonstrates current selected,
failed delivery, cancelled handoff and recognizable parent lineage. No provider
or ImageGen call was made. The previously director-owned preview and its
persisted roots were not modified.

## Cast synchronization and mutation-session correction — 2026-09-20

**Root cause.** `CharactersPage` mounted `CastPanel` and the image review as
independent readers. A cast accept/reopen/save refreshed only the text panel, so
the gallery could retain obsolete admission and direction data. Separately, the
gallery acquired its refresh owner only after a mutation completed; an
abort-ignoring old completion could therefore write fields or start a read in a
new project, subject, or cast session.

**Correction.** The workspace now owns the cast read and a monotonic session.
Cast accept/reopen/save invalidates it before dispatch and makes retained images
non-actionable while the cast transition is pending. Returned cast state drives
both panels, and the gallery performs a guarded refresh of its own current
decisions/directions. Each image action captures project/cast/subject plus an
operation owner before dispatch. Only a matching completion may reset drafts,
show an assignment/error, change busy state, or refresh. Unmount, project and
subject changes, cast transitions, and abort-ignoring late results are refused.
No API, schema, provider, persistence, selection CAS, reviewer/notes, or layout
contract changed. ADR 0071 records this React ownership boundary.

**Executed checks.**

- `npm test` — 19 files / 172 tests passed. The focused gallery unit set now
  includes seven cases, including abort-ignoring deferred success after reopen,
  stale copied-assignment refusal during an in-flight reopen, and old-subject
  rejection refusal.
- `npm run typecheck` and `npm run typecheck:e2e` — passed.
- `npx playwright test e2e/cast-reference-studies.spec.ts --config playwright.config.ts --reporter=line`
  — 4 passed.
- `npx playwright test e2e/story-prototype.spec.ts --config playwright.config.ts --reporter=line`
  — 3 passed after the workspace navigation change.
- `npm run build:deterministic` twice produced identical SHA-256 hashes for
  `workbench.js`, `workbench.css`, and `index.html`; the regenerated
  `workbench.js` is included with this correction. Vite emitted its existing
  >500 kB chunk advisory only.

**Independent review.** A Terra/high read-only review of the initial stable
delta found two P1 currentness gaps: local result setters preceded their session
guard, and cast authority was invalidated only after a cast response. The
correction moved those setters beneath the captured per-operation guard and
introduced pre-dispatch workspace invalidation; the new deferred tests are
guard-sensitive to both gaps. A final re-review of the corrected delta is
recorded below before closeout.

**Walkthrough service.** The retained H3-disabled preview and fixture roots at
port 49072 were not restarted or otherwise modified by this correction. Human
creator-usability acceptance remains pending; the technical fixture is not a
creative or media-acceptance claim.

**Final independent re-review.** Terra/high re-review found and then verified a
single P2 correction: the session-change GET refresh now catches failures and
surfaces them only while both its captured cast session and read owner still
match. The final read-only verdict was **no findings**.

## Live session ownership closeout — 2026-09-20

**Prior-proof limit and root cause.** The prior correction's refresh comparison
used the render closure's `castSession` on both sides. It was not a live owner
check; a pre-transition refresh could still commit old values or an old rejection
after the same subject reached a newer accepted cast revision. Its read owner
also changed only on project changes. Separately, `SubjectGallery` keyed only by
subject ID, so an invalidated pending operation correctly suppressed its late
completion but left the retained same-subject controls busy with old drafts.

**Delivered correction.** `CharactersPage` owns a monotonic live session ref
and advances it before accept/reopen/save dispatch. The gallery uses one live
read path for initial loads, session loads, and mutation refreshes; each read
requires its captured session and unique read owner to remain current before
data or errors publish. A subject gallery is keyed by cast session plus subject,
which resets reviewer-notes/direction/parent/assignment/busy/error state for the
new same-subject session. Mutations retain their project/cast/subject/operation
guard before dispatch and before every local effect. No backend, API, provider,
persistence, CAS, reviewer/notes, asset, or creative contract changed.

**New evidence.** Focused unit tests first failed on the prior implementation,
then passed with 12 gallery cases. They hold an initial gallery read across
reopen/save, separately commit notes and assert the selection request dispatches,
then hold a mutation-triggered refresh over reopen/save; settle r2 before
releasing old success or rejection; and prove old r91 data/error cannot render.
A pending prepare → reopen → save test verifies fresh enabled
controls, absent stale drafts, ignored old assignment, and a dispatched next
prepare; a held selection rejection after that same transition cannot surface an
old mutation error. The added production FastAPI/file-SQLite browser test drives browser
cast accept → reopen → save and verifies gallery r1 → read-only reopened →
editable r2. The retained port-49072 preview was unreachable with no listener
at this run, so it was not restarted or modified; its roots remain untouched.

**Pending.** The recorded checks are technical verification only. Human
creator-usability acceptance remains pending, and no creative or media outcome
is accepted by these fixtures.

**Independent final review.** A Terra/high read-only review of the stable delta
found no P0/P1 defects and identified one P2 evidence gap: no late image-mutation
rejection after reopen → save. The added focused selection regression holds that
request, settles r2, then rejects it and proves no stale error appears. The
narrow Terra/high re-review found **no findings**. It did not run checks or alter
source; the executions listed here remain the delivery evidence.
