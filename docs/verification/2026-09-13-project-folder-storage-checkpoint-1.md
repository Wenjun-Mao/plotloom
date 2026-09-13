# Project-folder storage checkpoint 1 receipt

Date: 2026-09-13
Scope: isolated folder-storage construction only; no runtime cutover, data
archive, provider call, gateway change, merge, or push.

## Brief and result

Baseline: clean `1141269772c2303deab4a860f5f402ce54fe7a18` before the checkpoint.
The observable outcome was two independently created project homes that each
persist a brief edit and deterministic offline-provider output, then reopen
after the former shared project database is unavailable.

The root cause was ownership conflation in the retained shared repository:
canonical project state, reusable provider profiles, installation preferences,
and global accounting share one SQLite schema. The fix belongs at the storage
composition boundary, not as a downstream copy or path-relocation workaround.
`project_storage.py` therefore adds separate project and application stores;
the current runtime remains unchanged.

## Evidence

- `uv run pytest -q tests/test_project_storage.py` — 3 passed.
- The isolation/reopen test creates two homes under a temporary outputs root,
  edits/runs each one, removes a synthetic former shared database, reopens both,
  and confirms separate project databases, project-local artifacts, application
  profiles, and global accounting tables.
- The confinement test rejects traversal artifact paths and credential-shaped
  profile configuration, and rejects a symlinked hash directory before it can
  read outside the project.
- The ownership-boundary test rejects cross-project hard-linked bytes,
  mismatched run ownership injected into a project database, overlapping
  application/outputs roots, and hidden `.snapshots` directories being
  discovered as live projects.
- `uv run python -m compileall -q src/plotloom/project_storage.py` plus a
  temporary direct create/edit/run/reopen smoke completed successfully.
- The unfiltered Python suite was run in complete native groups because the
  terminal stream has a 30-second cutoff: 308 backend-core passed; 244
  generation/media/service/video passed with 9 skipped; 68 fast root tests
  passed; 13 conformance tests passed; and 23 Alpha-acceptance tests passed.
  `uv run pytest --collect-only -q` reported 665 collected tests.
- `uv build --wheel --out-dir /tmp/plotloom-project-storage-wheel` succeeded,
  and a fresh temporary virtual environment installed that wheel and created,
  ran, discovered, and reopened two isolated project homes.

No live provider or gateway was contacted. The deterministic fake is storage
evidence only and does not establish creative quality, provider dispatch, or
paid accounting behavior.

## Independent review

One independent read-only Terra review found intermediate-symlink and
cross-project-hard-link reads, overlapping composition roots, incomplete
two-project edit coverage, and missing project-run ownership validation. The
candidate now validates every artifact path component without following links,
rejects hard-linked asset files, rejects overlapping roots, ties run rows to the
singleton project identity with a foreign key plus open-time validation, and
covers the exact regressions above. The same reviewer then verified all five
remediations with no remaining findings.

## Remaining work

Checkpoint 2 must connect complete existing authoring, canonical revisions,
runs/repairs, media and review flows, drafts, lifecycle, and delayed operation
routing to a project handle. It must freeze public profile metadata into
project-owned run evidence while keeping profile selection, credentials, and
global accounting installation-owned.

Checkpoint 3 must add close, consistent snapshots, restore, integrity checks,
and recovery behavior. Checkpoint 4 must quiesce writers, preserve an exact
legacy archive/inventory, export permitted application state, change runtime
configuration to new roots, and remove redundant old working copies only after
verification. None of those actions occurred here.

Usage/cost deltas are unavailable from the existing task records.
