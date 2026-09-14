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

Only tests whose contract was the removed shared route/facade, generic media
worker, or unsupported shared-store migration are retired. A fixture's use of
`SQLiteRepository` is not itself a retirement reason. The exact disposition of
every deleted or materially rewritten test function (including parameterized
cases) is versioned in the machine-checkable coverage inventory and checked
against the pre-retirement baseline.

### Coverage-preservation amendment (2026-09-14)

The original retirement changed the test tree too broadly: durable generation
behavior was lost together with the shared fixture even though the behavior is
still owned by manifest-bound project stores. The evidence is the diff from
`e658057` to `f908c51`, which removed 301 baseline test functions or materially
rewrote their coverage population. The durable correction belongs at the current
project/application owner test layer, not in a facade shim or storage
compatibility mode.

`docs/verification/2026-09-14-retained-runtime-coverage-inventory.json`
classifies the baseline tests as migrated current contracts, existing assertion
equivalents, or approved breaking-storage retirements. Its verifier rejects an
unclassified baseline test, a missing parameter case, a file-level default, or
a stale/missing current assertion record. It preserves each baseline trigger
and assertion expression alongside exact current test IDs, while explicitly
leaving semantic equivalence to review. The prior file-level inventory was not
accepted as final evidence because target existence did not establish matching
assertions. The restored
project-generation tests assert the two-correction cap and lineage,
dispatch-before-call, reasoning-only separation, durable primary/correction
response recovery without replay, provider-echo redaction, correction audit
hash tampering, and exact-repair evidence tampering. Existing project-folder
tests retain image/video currentness, lifecycle/review, artifact ownership,
atomic direct-video claims, seals, and installation behavior.

The coverage audit also exposed an API ownership regression: the project-folder
route no longer preserved atomic initial-stage installation or project-creation
idempotency. Project initialization now validates and installs the canonical
initial prefix in one project-database bootstrap transaction. The application
lifecycle ledger owns only the retry key, request fingerprint, and reserved
project identity; it never stores brief or stage content. Its token-bound lease
returns a retryable 503 while bootstrap is active, lets exactly one retry
recover an expired owner, and prevents a replay from opening a manifest before
the project transaction completes. Reusing a completed key returns the same
project, while divergent reuse is a 409 conflict. This restores the public
contract at its two real owners without recreating a shared repository or route
facade.

The assertion-level correction also exposed a project-folder route defect: its
local `ImageJobError` handler classified a malformed keyframe-adaptation
geometry as a 409 conflict. Geometry is an untrusted delivery validation
failure, so the handler now reserves 409 only for immutable package/delivery
identity conflicts and returns 422 for invalid geometry. The regression keeps
the rejected delivery from changing the reviewed keyframe selection.

## Rejected alternatives

- Keep `SQLiteRepository` behind a lazy root export or a forwarding facade.
- Rewire the old routes to call project-folder routes and preserve two public
  factories.
- Move the shared repository into test helpers so historical tests keep running.
- Teach project-folder storage to open or import a retained shared database.
