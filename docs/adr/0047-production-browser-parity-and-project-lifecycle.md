# ADR 0047: Production browser parity and project-folder lifecycle

## Status

Accepted, 2026-09-14.

## Context

ADR 0046 made the project-folder composition the shipped runtime, but retained
browser journeys could still choose a legacy FastAPI/shared-SQLite fixture.
That hid three production gaps: project-folder routes did not own archive,
restore, duplicate, or permanent deletion; its error surface did not preserve
structured domain issues; and an acknowledged durable draft was not retained
as the CAS source for the author's next edit.

## Decision

All retained browser journeys start `build_runtime_app` with separate temporary
project and application roots. The only video provider seam is the typed
offline MiniMax-H3 transport composed through the production factory. Browser
tests never select a persistence mode, old app factory, Wan adapter, or
synthetic native media completion event.

Project-folder lifecycle is owned at its natural boundaries. A project SQLite
database owns archive/restore and canonical-prefix duplication. The
installation SQLite ledger owns duplicate idempotency key, immutable target
identity, and the copied-prefix receipt, but never project content. A replay
reads that reserved target and receipt instead of re-evaluating mutable source
content. Permanent deletion requires an archived project, current lifecycle
revision, exact title, no managed media, and an exclusive project lease. Both
archival and deletion reuse the close boundary: no nonterminal run, media task,
video job, manual image publication, or character-reference publication may
cross the lifecycle transition. Only then may deletion erase that one project
home and discard its application-side run index and duplicate records.

The project-folder API preserves the existing public lifecycle and validation
response semantics, including `project_managed_assets_present` and structured
`domain_validation` issues. The browser's durable-draft map remains the source
of the next expected draft revision after acknowledgement until an exact
canonical save consumes that server receipt.

## Consequences

The browser suite is an integration proof of the shipped runtime rather than a
parallel legacy storage implementation. H3 owns production browser-video
coverage; historical Wan behavior remains backend-only and is not selected by
browser configuration. Existing retained shared-repository callers are not
migrated by this decision; their exact retirement inventory accompanies the
cutover verification receipt.

## Rejected alternatives

- Keep a selectable legacy fixture or recreate its `create_app` compatibility
  shim around production routes.
- Put duplicate project content or lifecycle state into the installation
  database, or generate a fresh duplicate on idempotent replay.
- Delete a project with managed media and leave orphaned immutable bytes.
- Archive or delete while a nonterminal external publication could still
  deliver bytes into that project home.
- Downgrade project-folder domain failures to generic authoring errors.
- Let a fresh local edit restart an existing server draft's CAS chain at zero.
