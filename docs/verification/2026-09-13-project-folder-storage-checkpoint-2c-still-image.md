# Project-folder storage checkpoint 2C: still/image workflow

Date: 2026-09-13
Baseline: `15c0e8d64712e3d8a1c69158e57014b151c3c28a`

## Outcome

The existing test-only project-folder workbench composition now resolves each
still/image request through its immutable manifest project ID and the one
owning `project.sqlite3`. Format 5 includes the still/image lifecycle,
character-reference/review, and manual handoff tables but excludes application
profiles, credentials, paid accounting, all video-pilot tables, and legacy
runtime data.

Managed originals and display derivatives use only `assets/<prefix>/<sha256>`
relative paths beneath the project home. Manual image/proposal packages and
deliveries use `runs/<UTC-time>__<job-id>/jobs/<job-id>/`; no configured global
exchange path is used. The project handle refuses a foreign job ID before it
can read or publish a delivery. Existing repository currentness checks retain
late, stale, and rejected delivery history without publishing a candidate.

Visual-intent and manual image-direction drafts are typed, server-CAS
`v2_authoring_drafts` rows. Their payloads include only the author-owned
direction and required exact identities, use the current storyboard revision as
the base, and reject secret-shaped values, UI blobs, foreign assets, or missing
shots. The browser’s local cache remains an unacknowledged-edit guard only.
Creating an intent or preparing a manual image job consumes the exact
acknowledged media-draft receipt in the same SQLite transaction. A stale tab
therefore cannot create a semantic record or job, and the newer draft remains
recoverable. Completion manifests are screened as a whole before any delivery,
rejection, or provenance record is written; a secret-shaped value is rejected
without persisting a delivery.
The direct media-draft capability prevents this test-only composition from
probing the installation-owned profile registry or mounting the excluded video
pilot; the retained runtime preserves its existing behavior.

## Offline evidence

Focused command:

```text
uv run pytest tests/test_project_storage.py tests/test_project_storage_image_workflow.py tests/backend_core/test_image_jobs.py -q
```

Result: `32 passed`.

The new direct-storage journey creates two fixture project homes, runs the
existing deterministic offline text fixture to obtain canonical evidence,
imports an image into only the first home, saves both media draft types,
approves/selects, prepares/copies an original P1 job, writes a fixture
completion manifest, and ingests the fixture candidate. It then selects that
candidate, prepares/copies a refinement, replaces the bound visual intent, and
proves the copied late delivery is `inapplicable`. A second project’s refresh
route returns 404 for the first project’s job. After a new
`ProjectFolderStorage` process, the original bytes and both job histories are
read from the first project home and their stored URI remains relative under
`assets/`. The fixture also proves that a stale visual-intent or image-direction
receipt cannot create its downstream record, and a completion containing a
secret-shaped prompt returns 422 with no delivery persisted.

No live ImageGen, provider, gateway, account, video, or legacy runtime call was
made. Fixture rasters prove storage and lifecycle behavior only, not creative
quality.

The final locked gates passed: `664 passed, 9 skipped` Python tests; `130`
frontend unit tests; TypeScript typecheck; regenerated static assets; and all
`30` offline Playwright journeys, including the direct project-folder
still-image restart test. `uv build --wheel` and the isolated installed-wheel
smoke check also passed for `plotloom-0.1.0-py3-none-any.whl`.

## Deferred

- Project close/quiescence, snapshots, restore, corruption-repair UI, and
  retained-runtime cutover.
- Video handoff/dispatch and global paid accounting coordination.
- Any legacy import, compatibility mode, pilot-data mutation, or provider call.
- End-user live generation validation; only manual offline delivery ingestion
  is covered here.
