# ADR 0158 — Accepted-source seed for graph-command tests

Status: accepted, 2026-10-11.

## Context

The graph-command contract cases all require the same accepted source and
outline before graph drafts can be created. Their function-scoped fixture
repeated project creation and the production-shaped prepare, delivery, admit
and accept flow for every case. M0 measured 1.89s of setup across 19 cases,
while the test calls had a 0.31s median. That source/outline flow is a required
precondition for these graph-command cases, but its repeated execution is not
the behavior they assert.

## Decision

Build one disposable accepted-source seed per pytest session using the same
project storage and outline acceptance path. Register it in `tests/conftest.py`
so the graph-command fixture can consume it without importing fixtures from a
collected test module. Close its handle before snapshot use and fail if SQLite
sidecars remain. For each graph-command case, copy the complete project home
under that case's temporary output root, open the copy through
`ProjectFolderStorage.projects.open`, and close it at teardown. Keep the
function-scoped source fixture for all other graph test modules.

Move reusable source/outline builders into `tests/source_outline_fixtures.py`
and graph project/map builders into `tests/graph_authoring_fixtures.py`. Test
modules consume those cohesive helpers rather than importing fixture builders
from another collected test module. The shared `source_project` fixture keeps
its function-scoped production setup for non-command graph tests; only
`test_graph_commands.py` shadows it with the seeded-copy version.

No mutable project handle or database connection is shared. Separate test
roots also use separate application-data roots, so the seed's project ID is
never registered twice within one project registry. A regression mutates one
of two copies and confirms the other retains its original graph draft state.

## Alternatives and consequences

Rebuilding the full source/outline path per graph-command case preserved
isolation but repeated setup work unrelated to each command assertion. Sharing
one live project or database connection was rejected because cases mutate
persistent graph drafts and must remain independent. Directly inserting a
prepared outline or graph state was rejected because it would bypass the real
currentness and acceptance precondition.

The isolated copy approach retains the production-shaped accepted state and
per-case persistence while reducing measured graph-command suite wall time.
Future changes to the seed must keep it closed before copying, copy the complete
project home, reopen through the project-folder owner, and preserve the
cross-copy mutation guard. Keep seed creation global and immutable, but keep the
copying optimization scoped to graph-command cases whose repeated setup was
measured.

## Geometry-corruption consumer — October 14, 2026

The owner-approved fixture-reuse follow-up extends this pattern only to the
seven geometry-lineage ordinary-open corruption variants. Their repeated real
current-policy fake-host text/image/geometry setup is a shared precondition;
the fault mutation and full ordinary-open refusal remain per-case behavior.
The unchanged derivative-generation and restart/rollback cases keep complete
function-scoped setup. A quiet matched eleven-case pair measured 89.454s before / 38.556s after
(56.90% less complete-command wall time). This scoped one-pair result does not
establish a whole-suite gain or release qualification.

Build one real first-geometry-frame seed per pytest session, with construction
patches scoped to that build. Require an empty pending fake-host set, terminal
host statuses and persisted attempts, and no reserved/unknown/cancel-pending
native work. Close service threads/controller descriptors and every project
handle. Preserve the original logically running run and open project state:
this is fixture-only resource quiescence, not production snapshot/restore or
lifecycle-close eligibility. Copies must never dispatch or continue that run.

Freeze complete project and disposable application bytes with only scalar/path
metadata. Reject SQLite sidecars, symlinks, nonregular files and hard links;
acquire existing controller/project locks to refuse active readers/writers.
Copy the complete root physically into an absent case root. Compare inventory/
hashes and independent inodes, then instantiate fresh storage/catalog owners
and obtain a new typed view through ordinary project admission. No live handle,
parsed authority, writable asset, application state or lock inode is shared.

Completed native attempts/receipts and absolute execution provenance stay byte
identical as evidence. Do not rebind paths/identities/hashes or instantiate a
host/controller for copies. Ordinary-open asset checks use the copied admitted
database home; prove this by making the seed location unavailable. Guard sibling
and seed independence after database, asset and application mutations, distinct
project/controller locks, seed immutability and refusal of active/sidecar/link
inputs. Production validation, corruption checks and authority are unchanged.

Attended independent Sol/Medium read-only design and stable code reviews found
no actionable issues. Twenty-seven focused checks and the matched quiet pair
passed; combined full qualification remains open. Implementation evidence belongs in the existing
[Python follow-up](../roadmap/2026-10-14-python-context-and-workers.md).

## Five invalid-handoff consumers — October 14, 2026

After the geometry matched pair, the manager approved reuse for only the five
invalid-whole-handoff variants. Build a real current-policy completed pack:
two routes, six provisional frames, two selected references, `awaiting_review`,
successful terminal attempts, no pending native work and no human facts. Close
controller, DB and file resources before freezing the complete project and
application root. Preserve six zero-partial-authority assertions in each case;
compute review material and request anew after ordinary opening of its copy.

Share only the closed-root inventory/hash, physical-copy and OS-lock safeguards
with geometry. Each builder keeps its own strict state/evidence preconditions.
Never cache a parsed review/request, manufacture approval, rebind retained
attempt identity, continue copied work or weaken ordinary-open validation.
Success/withdrawal, mid-handoff rollback and takeover controls keep fresh setup.

A new positive-copy guard must accept a genuine handoff and establish video
eligibility in one disposable copy while the seed and sibling retain zero human
facts and await review. Retain physical/evidence isolation and seed-absence
checks. Run affected geometry copy guards when extracting their shared code.
Eight native cases are frozen against clean `140b4a31` in the Python plan;
new guards run separately. Handoff speed remains unmeasured until the manager
allocates a quiet matched window; final combined full qualification is separate.

The handoff implementation passed 23 focused isolation/invalid-case/ownership
checks, the three unchanged end-to-end controls and seven original geometry
corruption consumers after shared-copy extraction (33 distinct cases). An attended independent
Sol/Medium stable code review found no actionable issues and ran no checks.
The positive-copy guard proves human handoff/video eligibility only in its
copy while original seed and sibling remain machine-only. The quiet matched eight-case pair measured 99.715s before / 53.505s after
(46.34% less complete-command wall time). This scoped one-pair result preserves
the fresh controls; whole-suite speed and combined full qualification remain
open in the Python plan.

## Terminal-reconciliation accepted Script consumers — October 14

An independent Sol/Medium read-only design review supports copying only the
closed real accepted F4 Script project for 38 selected terminal-reconciliation
failure cases. Build current accepted source/outline/section map/graph, Cast,
Art and Script through `_accepted_f4_script`; require no stale accepted owners,
active candidates, autopilot/native/media work or publication blockers. Preserve
accepted candidate rows, execution pins and completed package evidence.

Freeze only the complete project home after all handles close. Share only the
reviewed pure complete-tree file validation; hold the existing project lock
exclusively through physical copying, check hashes/inodes and normal admission.
Never create a fake autopilot lock or relax the two-lock autopilot contract.
Create application state, registry/task UUIDs, dispatch roots and call lists
fresh per runtime. No active/unknown reservation or registry path is copied.
Each case still creates/exports/sends/cancels/checks its own job and preserves
all original database, package, lease and refusal invariants. Retained accepted
package bytes are evidence; fresh branch jobs generate copy-local absolute
paths. Do not rewrite any retained identity or hashes.

A separate seeded runtime fixture selects only the three recorded failure
matrices. Default `ReconciliationRuntime` and six all-stage fresh controls keep
the original full setup. Guard seed unavailability, new independent registry
identities/paths, project locks and files, mutation isolation and successful
terminal proof releasing only its own copy's reservation. Forty-four native
cases are frozen against `4f6f6804`; performance needs a later quiet pair.

The terminal-reconciliation implementation passed 47 focused failure/isolation/
ownership checks and six unchanged fresh all-stage controls (53 distinct cases).
Attended independent Sol/Medium design and stable code reviews found no
blocker/actionable finding; the reviewer ran no checks. Exact 44 native IDs
match before/after; terminal-reconciliation speed and combined full release
qualification remain open. See the Python plan for frozen refs and log hashes.

## Pending native Bridge failure consumers — October 14

An attended Sol/Medium design review supports one distinct closed seed built
through the exact original `_pending_project` nine-shot minimum/maximum path.
The 1/4-shot reconciliation seed cannot substitute for it. Require current
accepted source/outline/map/graph, Cast/Art/Script/Storyboard, no active
candidates or native/media/autopilot work, and a current noninstallable pending
proposal with reviewed presentation and blank pending intent. Preserve accepted
execution pins and completed package evidence. Freeze only the complete closed
project home; reuse the reviewed project lock/hash/inode copy safeguards.

Only 22 selected binder/delivery/pin failures consume copies. Default fixtures
and four positive/unknown-dispatch controls remain fresh. Every case recreates
application state, task UUIDs, registry, services, execution pins, native job,
export/send and any presentation author-intent update. Read proposal identity
afresh after ordinary opening; never cache parsed authority, rewrite retained
provenance or carry a reservation into a copy. Positive-copy guards must prove
real fake-native advice admission while the seed is unavailable, with independent
sibling reservations, files and locks. Performance remains unmeasured until a
quiet matched 26-case pair; see the Python plan for the frozen inventory.

Implementation passed 34 focused failures/isolation/helper/ownership checks and
the four unchanged fresh controls (38 distinct cases). Independent Sol/Medium
stable review found no actionable findings and ran no checks. Exact 26 native
IDs match. Intent/presentation positive-copy guards admit advice and derived
reports without installation while the seed is unavailable, preserving sibling
proposal/database/reservations. No performance comparison has run; frozen refs
and log hashes live in the Python plan.
