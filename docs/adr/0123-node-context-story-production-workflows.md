# ADR 0123: Node context reads and actions reuse current review owners

Status: accepted within owner-approved G3/G4 scope, 2026-10-06.

## Problem

Creator node context can misleadingly reduce a package-scoped task to one node,
lose screenplay fields, or invent a shot mapping from repeated location names.
Another editing or media store would also bypass existing revision and dispatch
guards.

## Decision

Story context projects accepted F4 through its exact section/episode binding.
Every ordered scene occurrence is shown, including repeated location IDs. The
scoped editor retains the complete upstream episode JSON and submits the existing
revision/hash-bound section replacement. Dirty text remains bound to its original
section through selection, tab and mode changes; restoring retained text is
explicit. New graph drafts do not rewrite accepted screenplay or media evidence.

Preparation, dispatch, result checking, acceptance and reports reuse existing
source/script review controllers. Package actions state their whole-package scope.
There is no node-only generator or independent approval authority.
The report view refreshes on accepted revision/hash changes so the server's
current edited-script annotation appears; original specialist HTML stays intact.

Production context must read exact current bridge scene/cut coordinates and
stable installed shot IDs, then route existing shot/media controls. Missing,
uninstalled or stale provenance suspends handoff. First-install-only admission
remains explicit; reading current installed production does not authorize its
structural replacement. No action automatically dispatches, approves or selects
media.

## Alternatives and consequences

A simplified scene form was rejected because it would drop supported fields.
Index/location matching was rejected because repeated occurrences are distinct.
Duplicate node jobs and media state were rejected because they would diverge from
professional owners. Complete JSON remains a detailed editor; creator context
adds readable projections, exact navigation and explicit scope/currentness.

Guardrails exercise repeated scenes, lossless section save, dirty node/mode changes,
late/stale review results and exact current shot handoff. General post-installation
replacement and independently scoped generation remain later capabilities.
