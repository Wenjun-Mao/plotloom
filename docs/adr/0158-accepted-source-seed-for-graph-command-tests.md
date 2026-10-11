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
