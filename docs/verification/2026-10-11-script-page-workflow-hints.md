# Script-page state-based workflow hints

Qualified candidate: the main commit containing this receipt, against trusted
`62f031337d2711e6d5e76017a676487420d002b4`. Contract: ADR 0155.

## Cause and scope

The Script page's guide still selected hard-coded review advice although its
owning panel correctly reported no candidate. A route is not evidence that a
script exists. The guide now observes that panel's existing active read,
operation and unsaved-chapter state, without another API request. Project,
revision and activation tokens reject obsolete observations. Loading/failure,
busy operations and dirty drafts precede concrete prepare, review/confirm and
continue instructions. Review-page mutations update advice without a reload.

Independent review caught a second identity distinction: an active replacement
candidate retains the old accepted script even when the new candidate is
current. Candidate staleness and lifecycle therefore precede old accepted
evidence status; a fresh replacement must not receive a false basis-change
warning. Old retained evidence still cannot enable Continue.

Actual diff review: advisory frontend context/projection, one ScriptPanel
reporter, wiring, tests, ADR, roadmap and regenerated JS. Backend, APIs/schemas,
request payloads, persistence, admission, auth, provider/prompt behavior,
dependencies, build tooling and package contracts are unchanged. The browser
manifest registers the new regression in required hosted coverage without
filtering or reducing it. Existing mutation/read/draft guards remain unchanged.
Use risk-scoped local frontend qualification; no new approval or generation
behavior and no newly claimed backend qualification.

## Executed verification

- Initial focused units: **72 passed**, five files (recommended-script-workflow,
  script-workflow-observation, recommended-workflow, script-panel-ownership and
  review-activation), 1.961s total. Final two changed-file unit selections:
  **17 passed**, including current/stale replacement cases.
- Final `verify.py quick`: **1,181 passed**, 141 frontend files, both type checks,
  locked dependencies and API F401 lint; 11.056s total.
- Affected browser selections: recommended-script-workflow (2),
  recommended-workflow-guide (3), creator-workbench-production (3).
  Seven initially passed; one new test failed because an exact label locator
  did not match the chapter dropdown. The observed accessible combobox name
  identifies it correctly. Corrected selection plus replacement regression:
  **2 passed**, 9.498s focused total (including 17 units). All **8 unique affected
  browser cases passed** across those runs; unchanged passing selections were
  reused, not described as rerun after the pure Script hint correction.
- Native disposable projects covered missing/prepared/delivered/accepted and
  fresh replacement states, reopened dirty/discard, held/failed/retry reads.
  No specialist dispatch or media generation; runs remained empty. Unit coverage
  retains page re-entry, project A/B/A isolation and no duplicate Script read.
- Desktop screenshots generated at 1280x460, 1280x768 and 1700x900; short and wide
  views inspected: concrete prepare control, readable sticky guide, no clipping
  or horizontal overflow. Evidence is under `frontend/test-results/`.
- Unfiltered browser shard manifest check: **86 specs, 287 cases**, shard
  assignment 124/163, no overlap or missing cases.
- Two final deterministic seven-file builds matched sorted path/hash tree
  SHA-256 `e031d50cfbb8ad7ed8a53a20a464ad954ce91843e1ca9059484c5bb1bb3f0efc`;
  JS `d2d03a247a53cc6c0cbba92e96ea2578aa717082ac2bc2a3e48785c9df8626fb`.
  Existing large-chunk warning remains.
- Independent read-only review requested GPT-6.1 Sol / Medium; replacement
  finding resolved and regression fixture corrected to native `candidate_ready`.
  Effective host settings were not independently exposed. Reviewer ran focused
  units, not browsers/full qualification. No remaining actionable findings.

No full Python suite or unfiltered browser execution launched for this bounded
frontend update. Required combined-candidate/full/timing/hosted qualification
remains with the isolated modular-verification owner; local frontend checks are
not full-release success or creative acceptance. Normal8841, Safari and the
owner's story were not operated; refreshing the owner browser remains manual.
