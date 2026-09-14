# ADR 0048: Retire the shared-repository runtime

## Status

Accepted, 2026-09-14.

## Context

ADR 0046 made `build_runtime_app` the sole shipped project-folder composition,
and the production browser parity receipt confirmed every retained journey uses
it. The post-parity caller inventory still found an unreachable shared
`SQLiteRepository` facade, old FastAPI route composition, root-package aliases,
and qualification/media tooling that instantiated the facade directly. That
left a second source runtime with project and application state combined in one
database even though production does not select it.

The failure is ownership, not a missing import guard: adding another lazy import
or compatibility shim would preserve a selectable shared composition and let
tools exercise contracts that production no longer owns. Project content,
canonical state, runs, media and evidence belong to one `ProjectStore` per
project folder. Public profile selection and accounting belong to the
installation application store. Credentials remain outside both.

## Decision

Remove the shared facade, its old application factory/route modules, the
`SQLiteRepository` and `create_app` public aliases, and the orphaned generic
media runner in the same breaking source release. Do not retain an import
forwarder, test copy, storage switch, or migration path for the retired
runtime.

Conformance and Alpha now read enabled, secret-free text profile snapshots from
the current application database through a read-only transaction. They create
only disposable `ProjectFolderStorage` roots and run the normal
`ProjectGenerationRepository`/`PipelineEngine`/`LifecycleJobRunner` path. Each
sample owns its project-local artifact evidence; receipts and blinded review
packs retain their existing public-field and unblinding boundaries.

The old generic media-task worker is retired rather than rehomed because it has
no production caller and its raw media-task protocol is not a project-folder
capability. Current image publication remains owned by `ProjectMediaRepository`;
direct video dispatch and accounting remain owned by their project and
application owners. The source-only retirement does not import retained
projects, alter `.env`, switch local retained data, or change provider/gateway
state.

## Consequences

The replacement tests execute qualification against current application
profiles and disposable project folders, retain secret-safe receipt and review
invariants, and assert that no retired module or public alias is importable.
The wheel smoke rejects any retired module packaged into a distribution and
blocks it during runtime startup and recovery.

The old shared-route and shared-repository test suites are retired as historical
mode tests, not treated as current product coverage. Their current product
journeys are covered by the project-folder runtime, recovery, media, video, and
browser suites; the precise disposition is recorded in the retirement receipt.

## Rejected alternatives

- Keep `SQLiteRepository` behind a lazy root export or a forwarding facade.
- Rewire the old routes to call project-folder routes and preserve two public
  factories.
- Move the shared repository into test helpers so historical tests keep running.
- Teach project-folder storage to open or import a retained shared database.
