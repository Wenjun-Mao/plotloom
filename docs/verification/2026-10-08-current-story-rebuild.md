# Current story rebuild qualification

Status: isolated implementation and full software qualification complete.
Native Create → Revise → Recover remains partial. This candidate
has not replaced normal 8841 or changed its projects, media or protected settings.

The owner selected one current story with explicit rebuild. The implementation
follows [ADR 0138](../adr/0138-one-current-story-explicit-rebuild.md) and adds
E12.1–E12.4 to the existing acceptance playbook. Worktree:
`/private/tmp/plotloom-one-story-rebuild.gfnqlc`, branch
`codex/one-current-story-rebuild`. Backend commit `9e79463` and schema cleanup
`32d0bdf` precede root-owned integration/freshness commit `ea26b9b`.
The branch is pushed through `2e54cdf`, which merges only newer main documentation;
all 862 qualified executable/test/config/static inputs remain identical. Main and
normal 8841 remain on the earlier qualified service. This is a recoverable candidate
checkpoint, not a main release or completed native acceptance.

## Repairs and boundaries

- Replacing production now uses an exact proposal, source and canonical-target
  contract. Confirming/applying graph changes can stale an installed story;
  rebuilding requires fresh intent/presentation review and Storyboard approval.
- Pending proposals and installed content have separate authority. Preparing a
  proposal does not replace the installed cuts or borrow their runtime choices.
  Canonical replacement and source-owned Bible rebind are atomic; unchanged authored
  graph identity can remain valid without rewriting older accepted evidence.
- Independent review found that a canonical target change during review was
  rejected by acceptance but not exposed as stale, leaving no UI recovery path.
  Pending freshness now includes the replacement target in reads, author saves,
  inference dispatch and late adoption. Fresh preparation is available again.
- Pixel/control inspection then found stale intent fields still editable despite
  server refusal. They are now disabled while retained local text remains available
  for copying or explicit discard. Wording names both story and production changes,
  rather than incorrectly directing every target-only change back through source review.
- Historical schema transitions and automatic backfills were removed. Current
  creation, open, close/reopen, snapshot and restore use exact current-schema and
  project-identity checks. Unsupported folders are rejected before admission;
  no compatibility reader or migration was added. SQLite validation reads committed
  WAL state and may maintain WAL/SHM sidecars; database/manifest preservation is
  not a claim of byte-identical directories.
- Source/graph changes refuse unresolved publication work without clearing it.
  Revised tests exercise refusal, unchanged state, explicit cancellation or delivery,
  subsequent source edits and rejection of old adoption. Existing current jobs and
  unknown-dispatch safeguards are not bypassed to obtain a passing run.

## Executed verification

- Target-freshness regression: 3 passed. Publication/branch/independent-process
  lifecycle checks: 20 passed. Current-schema/runtime checks: 38 passed; separate
  lifecycle/recovery checks: 33 passed.
- Full current frontend suite: 813 passed across 104 files. Application and browser
  type checks, lock check, touched-source Ruff F checks, compile and diff checks pass.
- Final unfiltered browser gate: 240 passed in 6.8 minutes, without retries.
  It includes checked-static desktop controls, pending-publication refusal and
  the new same-project rebuild journey (32.2 seconds).
- Full stable Python suite: 1,347 passed in 682.02 seconds, with the existing
  Starlette/httpx deprecation warning. No product Python changed during that run.
- Creator service/bridge/launcher checks: 47 passed in 12.98 seconds using the
  documented `uv run --locked python -m pytest` invocation. A prior console-entry
  invocation failed collection because its import path omitted the local `tests`
  package; no product or test source was changed to resolve that command error.
- Real browser current-schema fixture: stale target → fresh proposal → fresh complete
  presentation and author-intent review → accepted replacement → old approval inactive
  → fresh approval → reload → installed-story graph edit applied and production stale.
  The final focused run passed in 29.5 seconds. Deterministic source fixtures and
  zero generation runs make this software acceptance, not native creative/media proof.
- Existing handoff, presentation and creator-production browser cases passed
  separately. The new case captures stale state at 1700×900, 1280×768 and 1280×460;
  no document-width overflow. Root directly inspected the final wording frames
  at all three sizes. The short-height frame shows the installed summary; the
  preparation action is below the fold and remains reachable by page scrolling.
- Independent read-only review found no remaining P1/P2 issue. It verified 50
  focused Python tests, 54 frontend tests and all 30 panel tests after the final
  stale-editor guards. Review is not native acceptance.

Artifacts: `output/playwright/current-story-rebuild-2026-10-08/` retains the
failed attempts and passing screenshots. The two production builds are identical
across all seven static members; the existing large-chunk warning is unchanged.
The wheel installed and passed its smoke check outside the checkout. Wheel SHA256:
`e873fa95b76db8bd23fa2029139d9557d29b42c5edc8493a6b32a925a61dbdee`.
The final unfiltered 240-test browser run passes. Its 862 source/test/config
and static inputs were unchanged before and after the run, fingerprint
`791c377130f1c49b32c38d7348abfa6c3195347657b325f7bf251cce6c186f67`;
the complete result directory is retained under `final-browser-gate/`.
Publication and deployment remain separate from these local results.

## Failed attempts and corrected method

The first new browser attempt waited for the backend-origin URL even though the
browser used the frontend proxy. The waiter now checks the exact API pathname
and method. The second expected a generic missing-approval label; the correctly
rendered historical-approval label is now asserted explicitly. Neither failure
was resolved by changing the product to satisfy an incorrect expected result.

An earlier Python run overlapped the schema module rename and returned 1321 passed,
four failed: one transient import failure and three fixtures expecting source/graph
mutation during pending publication. That run is diagnostic, not stable qualification.
The focused replacements test the new refusal and explicit resolution without
removing stale/late-adoption coverage. Their first draft compared a prepare-return
timestamp to a SQLite-decoded value; pre/post persisted-state equality now proves
nonmutation and all 20 focused checks pass.

A subsequent 240-test browser run retained 236 passes and four failures. Three
checked-static cases loaded the old bundle because root started the suite before
rebuilding it; the matching source-served cases passed. Rebuilding in the isolated
checkout resolved all three focused desktop checks without changing product code.
The first build command also used the wrong Vite working directory and failed
before the correct frontend-directory paired builds succeeded. Neither operation
changed the live service.

The fourth browser failure was another fixture expecting a map change during a
pending Cast publication. Its replacement checks refusal, unchanged saved map,
explicit UI cancellation, successful revision and rejection of a late delivery.
The first replacement expected a delivery-level 409; the current API instead
revokes cancelled request authority before reading a delivery and returns 404.
The final six-case currentness suite passes, preserving ready-Cast and
prepared/ready-Script stale-authority tests. No refusal was bypassed or softened.

## Remaining native and deployment work

The [native Codex intent checkpoint](2026-10-08-native-bridge-intent.md) records
the implemented candidate-only capability, author-review and dispatch fixes,
and its separate software and actual-native acceptance status.

### Profile-owned credential delta

After the full rebuild gate, the encountered default-profile compatibility
fallback was removed under ADR0139. Default and named text profiles resolve only
their own namespaced server key; image/video credentials and protected settings
were not changed. Independent read-only review found no blocking issue.
The 36 focused profile/config/extraction/runtime-capability tests pass, as do
touched-source Ruff F and diff checks. A freshly built wheel passed installed
smoke outside the checkout. The first smoke invocation mistakenly supplied a
wheel file rather than its directory; the corrected invocation passed without
source changes. The earlier 1,347-Python total predates this bounded delta;
unchanged frontend and browser evidence is reused rather than claimed rerun.

Create a fresh current-schema disposable baseline after the candidate is committed
and fully qualified, then revise that SAME completed project. Do not initialize
new authority by rewriting retained receipts or copying old approvals. Current
native multishot, revised all-route playback, reference consumption, configured
intent inference and the remaining whole-product state matrix are still open.
Normal 8841 remains on the earlier qualified executable until a safe matching
backend/static/data cutover is verified. No new generation or specialist dispatch
was performed during this implementation checkpoint.

The final read-only normal-service check returned healthy and no active specialist
tasks. Both protected projects and three protected settings still match aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
(Wind 17 managed files, Rain 67). No main-checkout source or live data was changed.
